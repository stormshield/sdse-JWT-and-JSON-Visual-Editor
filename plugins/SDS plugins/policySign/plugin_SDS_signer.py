
import os
import json
import re
import base64
import traceback
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from datetime import datetime, timezone
import sys
import getpass
import shutil
import secrets
import tempfile
from typing import Dict, Optional

# Try imports
MISSING_DEPS = []

# Defaults for optional deps (for type checkers)
jwt = None
Encoding = None
PrivateFormat = None
NoEncryption = None
load_key_and_certificates = None

try:
    import jwt
except ImportError:
    MISSING_DEPS.append("pyjwt")

try:
    from cryptography.hazmat.primitives.serialization import Encoding, PrivateFormat, NoEncryption
    from cryptography.hazmat.primitives.serialization.pkcs12 import load_key_and_certificates
    from cryptography.hazmat.backends import default_backend
    from cryptography import x509
except ImportError:
    MISSING_DEPS.append("cryptography")

def duplicate_json_file(original_path, dest_folder):
    os.makedirs(dest_folder, exist_ok=True)
    name, ext = os.path.splitext(os.path.basename(original_path))
    # Remove previous signed suffix if present to avoid duplication
    if "-signed-" in name:
        name = name.split("-signed-")[0]
    timestamp = datetime.now().strftime("%d%m%y-%H%M")
    copy_path = os.path.join(dest_folder, f"{name}-signed-{timestamp}.json")
    shutil.copy2(original_path, copy_path)
    return copy_path

def extract_certificates_from_json(json_file_path, output_folder):
    os.makedirs(output_folder, exist_ok=True)
    with open(json_file_path, "r", encoding="utf-8") as file:
        data = json.load(file)
    certs = data.get("certificateData", [])
    saved_files = []
    for cert_info in certs:
        cert_id = cert_info.get("id", "unknown")
        cert_data = cert_info.get("data")
        if not cert_data:
            continue
        try:
            cert_bytes = base64.b64decode(cert_data)
            cert_path = os.path.join(output_folder, f"{cert_id}.cer")
            with open(cert_path, "wb") as f:
                f.write(cert_bytes)
            saved_files.append(cert_path)
        except Exception as e:
            print(f"Erreur extraction certificat {cert_id}: {e}")
    return saved_files

def load_private_key_from_p12(p12_file_path, password):
    if load_key_and_certificates is None:
        raise RuntimeError("cryptography is required to load P12")
    with open(p12_file_path, "rb") as file:
        p12_data = file.read()
    password_bytes = password.encode("utf-8") if password else None
    private_key, certificate, additional_certificates = load_key_and_certificates(p12_data, password_bytes)
    return private_key, certificate, additional_certificates

def private_key_to_pem(private_key):
    if Encoding is None or PrivateFormat is None or NoEncryption is None:
        raise RuntimeError("cryptography is required to export private key")
    return private_key.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption())

def cert_to_x5c_list(main_cert, additional_certs):
    if main_cert is None:
        return None
    if Encoding is None:
        raise RuntimeError("cryptography is required to export certificates")
    x5c_list = [base64.b64encode(main_cert.public_bytes(Encoding.DER)).decode("ascii")]
    if additional_certs:
        x5c_list += [base64.b64encode(cert.public_bytes(Encoding.DER)).decode("ascii") for cert in additional_certs]
    return x5c_list

def save_cert_to_cer(main_cert, p12_file_path, output_folder):
    try:
        if main_cert is None:
            return None
        if Encoding is None:
            raise RuntimeError("cryptography is required to export certificates")
        os.makedirs(output_folder, exist_ok=True)
        cert_path = os.path.join(output_folder, "admin_policy.cer")
        with open(cert_path, "wb") as f:
            f.write(main_cert.public_bytes(Encoding.DER))
        return cert_path
    except Exception:
        return None

def sign_json_file(json_file_path, pem_key, headers=None, algorithm="RS256"):
    if jwt is None:
        raise RuntimeError("pyjwt is required to sign JSON")
    with open(json_file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    token = jwt.encode(
        payload=data,
        key=pem_key,
        algorithm=algorithm,
        headers=headers or {}
    )
    return token.decode("utf-8") if isinstance(token, bytes) else token

def update_policy_date_in_file(json_file_path):
    try:
        with open(json_file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        now_iso = datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')
        updated = False
        for key in ("date", "policyDate"):
            if key in data:
                data[key] = now_iso
                updated = True
        if updated:
            with open(json_file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        return updated
    except Exception:
        return False


# ------------------------------------------------------------------------------
# Plugin Implementation
# ------------------------------------------------------------------------------

import sys

import importlib.util

def get_plugin_resource_path(relative_path):
    """
    Get absolute path to plugin resource, works for dev and for PyInstaller.
    Similar to the main app's resource_path but for plugin directory.
    """
    # First, try to use the directory where this file actually is
    current_dir = os.path.dirname(os.path.abspath(__file__))
    dev_path = os.path.join(current_dir, relative_path)
    
    # In development mode, this will exist
    if os.path.exists(dev_path):
        return dev_path
    
    # In PyInstaller, try _MEIPASS
    try:
        base_path = getattr(sys, "_MEIPASS", None)
        if base_path is None:
            raise AttributeError("_MEIPASS not set")
        # Try multiple possible locations in case of directory structure changes
        possible_paths = [
            os.path.join(base_path, "plugins", "SDS plugins", "policySign", relative_path),
            os.path.join(base_path, "plugins", "SDS_plugins", "policySign", relative_path),
            os.path.join(base_path, relative_path)
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
                
        # If none exist, return the first attempt
        return possible_paths[0]
    except Exception:
        # Fallback to development path
        return dev_path

# Allow importing local modules even if directory structure has spaces or is not a valid package
try:
    lang_path = get_plugin_resource_path("languages.json")
    if os.path.exists(lang_path):
        with open(lang_path, "r", encoding="utf-8") as f:
            translations = json.load(f)
    else:
        translations = {}
        print(f"Plugin SDS Signer: languages.json not found at {lang_path}")
except Exception as e:
    print(f"Plugin SDS Signer: Could not load languages.json: {e}")
    import traceback
    traceback.print_exc()
    translations = {}

class Plugin:
    def __init__(self, app):
        self.app = app
        print("Plugin SDS Signer: Loaded")
        
        # Load translations
        self.translations = translations
        self.current_menu_label = None


    def t(self, key, *args):
        lang = getattr(self.app, "current_language", "en")
        
        # Try to read from settings.json if app.current_language is not reliable or we want to force check
        # However, usually app.current_language is already set from settings. 
        # But if the user wants to ensure it follows settings explicitly:
        try:
             settings_path = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "settings.json")
             if os.path.exists(settings_path):
                 with open(settings_path, "r", encoding="utf-8") as f:
                     settings = json.load(f)
                     lang = settings.get("language", lang)
        except Exception:
            pass

        text = self.translations.get(lang, self.translations["en"]).get(key, key)
        if args:
            try:
                return text.format(*args)
            except:
                return text
        return text

    def register(self):
        pass

    def on_event(self, event_name, data):
        if event_name == "ui_ready":
            self.register_menu()
        elif event_name == "language_changed":
            self.update_menu_language()

    def register_menu(self):
        # Add menu item to Tools menu
        try:
            tools_menu = self.app.tools_menu
            tools_menu.add_separator()
            
            label = self.t("menu_signer")
            self.current_menu_label = label
            
            tools_menu.add_command(label=label, command=self.open_signer)
            print("Plugin SDS Signer: Added to menu")
        except Exception as e:
            print(f"Plugin SDS Signer: Error registering menu: {e}")

    def update_menu_language(self):
        if self.current_menu_label is None:
            return

        try:
            tools_menu = self.app.tools_menu
            new_label = self.t("menu_signer")
            if new_label == self.current_menu_label:
                return

            last_index = tools_menu.index('end')
            if last_index is None:
                return

            for i in range(last_index + 1):
                try:
                    # Tkinter menu item configuration access
                    item_label = tools_menu.entrycget(i, "label")
                    if item_label == self.current_menu_label:
                        tools_menu.entryconfig(i, label=new_label)
                        self.current_menu_label = new_label
                        break
                except Exception:
                    continue
        except Exception as e:
            print(f"Plugin SDS Signer: Error updating menu language: {e}")

    def open_signer(self):

        SignerWindow(self.app, self)

# ------------------------------------------------------------------------------
# Signer Window Class
# ------------------------------------------------------------------------------

class SignerWindow:
    def __init__(self, main_app, plugin):
        self.main_app = main_app
        self.plugin = plugin
        self.root = tk.Toplevel(main_app)
        self.root.title(self.plugin.t("window_title"))
        self.root.transient(main_app)  # Establishes parent-child relationship for focus/stacking
        
        # Center the window
        window_width = 745
        window_height = 560 # Increased height for new layout
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width // 2) - (window_width // 2)
        y = (screen_height // 2) - (window_height // 2)
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
        # State variables
        self.p12_file_path = None
        self.json_files_paths = []

        self.p12_label_text = tk.StringVar(value=self.plugin.t("no_p12_selected"))
        self.extract_certs_var = tk.BooleanVar(value=False)

        self.create_ui()

        # Bring to front and force focus
        self.root.lift()
        self.root.focus_force()
        # Optionally, focus the password entry or the first interactive element
        self.p12_password_entry.focus_set()

    def create_ui(self):
        main_frame = tk.Frame(self.root, padx=10, pady=10)
        main_frame.pack(fill="both", expand=True)

        # === 1. Signer Group ===
        signer_frame = ttk.LabelFrame(main_frame, text=self.plugin.t("group_signer"), padding=(10, 5))
        signer_frame.pack(fill="x", pady=(0, 10))

        # P12 File Selection
        tk.Label(signer_frame, text=self.plugin.t("signer_label")).grid(row=0, column=0, sticky="w", padx=(0, 5))
        
        self.p12_entry = tk.Entry(signer_frame, textvariable=self.p12_label_text, state="readonly", width=50)
        self.p12_entry.grid(row=0, column=1, sticky="ew", padx=(0, 5))
        
        ttk.Button(signer_frame, text="...", width=4, command=self.select_p12_file).grid(row=0, column=2, sticky="w")
        
        # Password
        tk.Label(signer_frame, text=self.plugin.t("password_label")).grid(row=1, column=0, sticky="w", padx=(0, 5), pady=(5, 0))
        
        pwd_container = tk.Frame(signer_frame)
        pwd_container.grid(row=1, column=1, sticky="w", pady=(5, 0))
        
        self.p12_password_entry = tk.Entry(pwd_container, show="*", width=30)
        self.p12_password_entry.pack(side="left", fill="x", expand=True)
        
        self.show_pwd_btn = tk.Button(pwd_container, text="👁", width=3, command=self.toggle_password_visibility)
        self.show_pwd_btn.pack(side="left", padx=(5, 0))

        signer_frame.columnconfigure(1, weight=1)


        # === 2. Source Group ===
        source_frame = ttk.LabelFrame(main_frame, text=self.plugin.t("group_source"), padding=(10, 5))
        source_frame.pack(fill="x", pady=(0, 10))

        tk.Label(source_frame, text=self.plugin.t("using_editor_content"), font=("TkDefaultFont", 9, "italic")).pack(anchor="w")


        # === 3. Output Parameters Group ===
        output_frame = ttk.LabelFrame(main_frame, text=self.plugin.t("group_output"), padding=(10, 5))
        output_frame.pack(fill="x", pady=(0, 10))

        # Output Filename
        tk.Label(output_frame, text=self.plugin.t("output_name_label")).grid(row=0, column=0, sticky="w", padx=(0, 5))
        self.output_filename_entry = tk.Entry(output_frame, width=40)
        self.output_filename_entry.insert(0, "policy.jwt")
        self.output_filename_entry.grid(row=0, column=1, sticky="w", pady=2)

        # Algorithm
        tk.Label(output_frame, text=self.plugin.t("algorithm_label")).grid(row=1, column=0, sticky="w", padx=(0, 5))
        self.algorithm_choice = ttk.Combobox(output_frame, values=["RS256", "PS256"], state="readonly", width=10)
        self.algorithm_choice.set("RS256")
        self.algorithm_choice.grid(row=1, column=1, sticky="w", pady=2)

        # Extract Certs
        tk.Checkbutton(output_frame, text=self.plugin.t("extract_certs"), variable=self.extract_certs_var).grid(row=2, column=0, columnspan=2, sticky="w", pady=(5, 0))


        # === 4. Actions & Logs ===
        action_frame = tk.Frame(main_frame)
        action_frame.pack(fill="both", expand=True)

        ttk.Button(action_frame, text=self.plugin.t("sign_button"), command=self.apply_modifications_and_sign).pack(pady=(5, 10))

        # Log area with scrollbar
        log_frame = tk.Frame(action_frame)
        log_frame.pack(fill="both", expand=True)
        
        scrollbar = ttk.Scrollbar(log_frame)
        scrollbar.pack(side="right", fill="y")
        
        self.log_area = tk.Text(log_frame, height=8, state="disabled", yscrollcommand=scrollbar.set)
        self.log_area.pack(side="left", fill="both", expand=True)
        
        scrollbar.config(command=self.log_area.yview)

    def log_message(self, *messages):
        message = " ".join(str(m) for m in messages)
        self.log_area.config(state="normal")
        self.log_area.insert("end", message + "\n")
        self.log_area.see("end")
        self.log_area.config(state="disabled")

    def select_p12_file(self):
        path = filedialog.askopenfilename(
            parent=self.root,
            title=self.plugin.t("select_p12_title"),
            filetypes=[("P12/PFX", "*.p12 *.pfx")],
            initialdir=os.getcwd()
        )
        if path:
            self.p12_file_path = path
            self.p12_label_text.set(path)
            self.log_message(self.plugin.t("cert_saved_main", path)) # Re-using key but logic is just selection here

    def toggle_password_visibility(self):
        current_show = self.p12_password_entry.cget('show')
        if current_show == '*':
            self.p12_password_entry.config(show='')
        else:
            self.p12_password_entry.config(show='*')



    def prompt_for_p12_password(self):
        pwd_win = tk.Toplevel(self.root)
        pwd_win.title("Password")
        pwd_win.resizable(False, False)
        pwd_win.grab_set()

        tk.Label(pwd_win, text="Password P12:").grid(row=0, column=0, columnspan=2, padx=8, pady=(8,0))
        pwd_entry = tk.Entry(pwd_win, show="*", width=30)
        pwd_entry.grid(row=1, column=0, columnspan=2, padx=8, pady=(4,8))
        pwd_entry.focus_set()

        result: Dict[str, Optional[str]] = {"password": None}

        def on_ok():
            result["password"] = pwd_entry.get()
            pwd_win.destroy()

        def on_cancel():
            result["password"] = None
            pwd_win.destroy()

        tk.Button(pwd_win, text="OK", width=10, command=on_ok).grid(row=2, column=0, padx=8, pady=(0,8))
        tk.Button(pwd_win, text="Cancel", width=10, command=on_cancel).grid(row=2, column=1, padx=8, pady=(0,8))

        pwd_win.bind("<Return>", lambda e: on_ok())
        pwd_win.bind("<Escape>", lambda e: on_cancel())

        self.root.wait_window(pwd_win)
        return result["password"]

    def create_install_bat_localized(self, output_folder, output_filename, cert_path):
        # We need a custom version of create_install_bat that uses the plugin's translations
        # because the original one uses a global get_text which we don't have here.
        # But we can just use the provided create_install_bat and ignore translation inside the bat file generation
        # or implement it here.
        
        cert_basename = os.path.basename(cert_path) if cert_path else "admin_policy.cer"
        bat_path = os.path.join(output_folder, "install-policy.bat")
        
        # Using localized strings from plugin
        content = (
            f"set /p ans={self.plugin.t('bat_copy_policy_prompt')}\n"
            'if /I "%ans%"=="n" (\n'
            f"    echo {self.plugin.t('bat_policy_not_copied')}\n"
            ") else (\n"
            f'    copy /Y "%~dp0\\{output_filename}" "C:\\ProgramData\\Stormshield\\Stormshield Data Security\\" >nul\n'
            f"    echo {self.plugin.t('bat_policy_copied')}\n"
            ")\n"
            f"set /p ans={self.plugin.t('bat_copy_cert_prompt', cert_basename)}\n"
            'if /I "%ans%"=="y" (\n'
            f'    copy /Y "%~dp0\\{cert_basename}" "C:\\Program Files\\Arkoon\\Security BOX\\" >nul\n'
            f"    echo {self.plugin.t('bat_cert_copied')}\n"
            ") else (\n"
            f"    echo {self.plugin.t('bat_cert_not_copied')}\n"
            ")\n"
            "\n:: Arrêt du processus Kernel\n"
            "taskkill /f /im sbkrnl.exe\n"
        )
        try:
            with open(bat_path, "w", encoding="mbcs", newline="\r\n") as f:
                f.write(content)
            return bat_path
        except Exception:
            return None

    def apply_modifications_and_sign(self):
        if MISSING_DEPS:
            messagebox.showerror("Error", f"Missing dependencies: {', '.join(MISSING_DEPS)}.\nPlease install them to use this feature.", parent=self.root)
            return

        if not self.p12_file_path:
            messagebox.showerror("Error", self.plugin.t("error_no_p12"), parent=self.root)
            return
        
        # Get content from editor
        editor_content = self.main_app.text.get("1.0", "end-1c")
        if not editor_content.strip():
             messagebox.showerror("Error", "Editor is empty / L'éditeur est vide", parent=self.root)
             return

        # Determine output directory base
        if self.main_app.current_jwt_path:
            output_base_dir = os.path.dirname(self.main_app.current_jwt_path)
            base_name = os.path.basename(self.main_app.current_jwt_path)
            if not os.path.splitext(base_name)[1]:
                base_name += ".json"
        else:
            output_base_dir = os.path.join(os.path.expanduser("~"), "Desktop")
            base_name = "policy.json"

        # Create temp directory
        temp_dir = tempfile.mkdtemp()
        temp_file_path = os.path.join(temp_dir, base_name)
        
        try:
            with open(temp_file_path, "w", encoding="utf-8") as f:
                f.write(editor_content)
            
            self.json_files_paths = [temp_file_path]
        except Exception as e:
            messagebox.showerror("Error", f"Failed to write temp file: {e}", parent=self.root)
            return

        
        try:
            self.log_message(self.plugin.t("loading_p12"))
            pwd = self.p12_password_entry.get() or ""
            if not pwd:
                pwd = self.prompt_for_p12_password()
                if pwd is None:
                    self.log_message(self.plugin.t("sign_cancelled"))
                    return
                self.p12_password_entry.delete(0, tk.END)
                self.p12_password_entry.insert(0, pwd)
                
            private_key, cert, additional_certs = load_private_key_from_p12(self.p12_file_path, pwd)
            pem_key = private_key_to_pem(private_key)
            x5c_list = cert_to_x5c_list(cert, additional_certs)
            jwt_headers = {"x5c": x5c_list} if x5c_list else {}
        except Exception as e:
            error_trace = traceback.format_exc()
            messagebox.showerror("Error P12", f"{e}\n\n{error_trace}", parent=self.root)
            return

        algorithm = self.algorithm_choice.get()
        output_filename = self.output_filename_entry.get().strip() or "policy.jwt"
        success_count, error_count = 0, 0

        for json_file_path in self.json_files_paths:
            try:
                # json_file_path is the temp file path
                # We want to create output in output_base_dir
                json_name = os.path.splitext(base_name)[0]
                output_folder = os.path.join(output_base_dir, json_name)
                os.makedirs(output_folder, exist_ok=True)

                saved_cert = save_cert_to_cer(cert, self.p12_file_path, output_folder)
                if saved_cert:
                    self.log_message(self.plugin.t("cert_saved_main", saved_cert))
                else:
                    self.log_message(self.plugin.t("no_cert_found"))

                copy_path = duplicate_json_file(json_file_path, output_folder)
                # Formatting only
                with open(copy_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                with open(copy_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=4)

                if update_policy_date_in_file(copy_path):
                    self.log_message(self.plugin.t("date_updated_in", os.path.basename(copy_path)))

                token = sign_json_file(copy_path, pem_key, headers=jwt_headers, algorithm=algorithm)
                output_path = os.path.join(output_folder, output_filename)
                with open(output_path, "w", encoding="utf-8") as out_file:
                    out_file.write(token)
                
                # Use our localized bat creation
                bat = self.create_install_bat_localized(output_folder, output_filename, saved_cert)
                if bat:
                    self.log_message(self.plugin.t("batch_created_file", os.path.basename(bat)))
                
                self.log_message(self.plugin.t("success_path", output_path))
                success_count += 1

                if self.extract_certs_var.get():
                    certs_folder = os.path.join(output_folder, "certificats")
                    saved_certs = extract_certificates_from_json(copy_path, certs_folder)
                    if saved_certs:
                        self.log_message(self.plugin.t("certs_extracted_to", certs_folder))

            except Exception as e:
                self.log_message(self.plugin.t("error_for_file", json_file_path, str(e)))
                error_count += 1
        
        self.log_message(self.plugin.t("signing_summary", success_count, error_count))

        # Cleanup temp file
        try:
            shutil.rmtree(temp_dir)
        except Exception as e:
            print(f"Error cleaning up temp dir: {e}")
