
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

# Optional drag & drop support (works when the app uses TkinterDnD.Tk)
try:
    from tkinterdnd2 import DND_FILES  # type: ignore
    HAS_DND = True
except Exception:
    DND_FILES = None
    HAS_DND = False

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

HAS_PKCS11 = False
try:
    import pkcs11
    from pkcs11 import Mechanism, MGF
    HAS_PKCS11 = True
    
    # Patch pkcs11 string attributes to handle non-UTF-8 characters (e.g. latin-1) gracefully
    try:
        import pkcs11.attributes
        
        def safe_decode(b: bytes) -> str:
            try:
                return b.decode("utf-8")
            except UnicodeDecodeError:
                try:
                    return b.decode("latin-1")
                except Exception:
                    return b.decode("utf-8", errors="replace")
                    
        patched_handle_str = (
            lambda s: s.encode("utf-8"),
            safe_decode
        )
        
        # Patch the global attribute definition
        pkcs11.attributes.handle_str = patched_handle_str
        
        # Overwrite in ATTRIBUTE_TYPES map
        for attr in [
            pkcs11.Attribute.APPLICATION,
            pkcs11.Attribute.LABEL,
            pkcs11.Attribute.UNIQUE_ID,
            pkcs11.Attribute.URL
        ]:
            if attr in pkcs11.attributes.ATTRIBUTE_TYPES:
                pkcs11.attributes.ATTRIBUTE_TYPES[attr] = patched_handle_str
    except Exception:
        pass
except ImportError:
    pass

def load_plugin_config():
    base_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    settings_path = os.path.join(base_dir, "settings.json")
    old_config_path = os.path.join(base_dir, "sds_signer_config.json")
    
    migrated_config = {}
    if os.path.exists(old_config_path):
        try:
            with open(old_config_path, "r", encoding="utf-8") as f:
                migrated_config = json.load(f)
            os.remove(old_config_path)
        except Exception:
            pass
            
    settings = {}
    if os.path.exists(settings_path):
        try:
            with open(settings_path, "r", encoding="utf-8") as f:
                settings = json.load(f)
        except Exception:
            pass
            
    if migrated_config:
        settings["sds_signer"] = migrated_config
        try:
            with open(settings_path, "w", encoding="utf-8") as f:
                json.dump(settings, f, ensure_ascii=False, indent=4)
        except Exception:
            pass
            
    return settings.get("sds_signer", migrated_config)

def save_plugin_config(config):
    settings_path = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "settings.json")
    settings = {}
    if os.path.exists(settings_path):
        try:
            with open(settings_path, "r", encoding="utf-8") as f:
                settings = json.load(f)
        except Exception:
            pass
            
    settings["sds_signer"] = config
    
    try:
        with open(settings_path, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Error saving settings: {e}")

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


def _normalize_path(path: str) -> str:
    p = (path or "").strip().strip('"')
    p = p.replace("/", os.sep)
    return os.path.normpath(p)


def _split_dnd_files(data: str):
    """Parse TkinterDnD's event.data for DND_FILES into a list of paths."""
    if not data:
        return []

    data = data.strip()

    # Common format on Windows: {C:\Path With Spaces\a.p12} {C:\b.pfx}
    if "{" in data and "}" in data:
        out = []
        current = []
        in_brace = False
        for ch in data:
            if ch == "{":
                in_brace = True
                current = []
                continue
            if ch == "}":
                in_brace = False
                token = "".join(current).strip()
                if token:
                    out.append(token)
                current = []
                continue
            if in_brace:
                current.append(ch)
        return [_normalize_path(p) for p in out if p]

    parts = [p for p in data.split() if p]
    return [_normalize_path(p) for p in parts]


def _try_enable_dnd(widget, handler) -> bool:
    """Enable TkinterDnD drop on a widget if supported (runtime check)."""
    if not HAS_DND or DND_FILES is None:
        return False
    try:
        drop_target_register = getattr(widget, "drop_target_register", None)
        dnd_bind = getattr(widget, "dnd_bind", None)
        if callable(drop_target_register) and callable(dnd_bind):
            drop_target_register(DND_FILES)
            dnd_bind("<<Drop>>", handler)
            return True
    except Exception:
        pass
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
        self.include_signer_cert_var = tk.BooleanVar(value=False)

        # PKCS11 state variables
        self.config = load_plugin_config()
        self.pkcs11_dll_path = self.config.get("pkcs11_dll_path", "")
        self.signing_method = tk.StringVar(value=self.config.get("signing_method", "p12"))
        self.pkcs11_dll_text = tk.StringVar(value=self.pkcs11_dll_path)
        self.pkcs11_pin = tk.StringVar()
        self.loaded_certificates = [] # list of dicts: {"slot": slot, "label": label, "subject": subject, "id": cert_id, "cert": cert_obj}

        self.create_ui()

        # Bring to front and force focus
        self.root.lift()
        self.root.focus_force()
        
        # Initialize default view and focus
        self.update_signer_method_ui()
        if self.signing_method.get() == "p12":
            self.p12_password_entry.focus_set()
        else:
            self.pin_entry.focus_set()

    def create_ui(self):
        main_frame = tk.Frame(self.root, padx=10, pady=10)
        main_frame.pack(fill="both", expand=True)

        # === 1. Signer Group ===
        signer_frame = ttk.LabelFrame(main_frame, text=self.plugin.t("group_signer"), padding=(10, 5))
        signer_frame.pack(fill="x", pady=(0, 10))

        # Radio Buttons at the top of the group
        method_container = tk.Frame(signer_frame)
        method_container.grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 5))
        
        tk.Label(method_container, text=self.plugin.t("method_label")).pack(side="left", padx=(0, 10))
        
        self.r_p12 = tk.Radiobutton(method_container, text=self.plugin.t("method_p12"), variable=self.signing_method, value="p12", command=self.update_signer_method_ui)
        self.r_p12.pack(side="left", padx=(0, 10))
        
        self.r_pkcs11 = tk.Radiobutton(method_container, text=self.plugin.t("method_pkcs11"), variable=self.signing_method, value="pkcs11", command=self.update_signer_method_ui)
        self.r_pkcs11.pack(side="left")

        # Container for changing frames
        self.method_details_frame = tk.Frame(signer_frame)
        self.method_details_frame.grid(row=1, column=0, columnspan=3, sticky="ew")
        self.method_details_frame.columnconfigure(0, weight=1)

        # Subframe A: P12
        self.p12_subframe = tk.Frame(self.method_details_frame)
        self.p12_subframe.columnconfigure(1, weight=1)

        # P12 File Selection
        tk.Label(self.p12_subframe, text=self.plugin.t("signer_label")).grid(row=0, column=0, sticky="w", padx=(0, 5))
        self.p12_entry = tk.Entry(self.p12_subframe, textvariable=self.p12_label_text, state="readonly", width=50)
        self.p12_entry.grid(row=0, column=1, sticky="ew", padx=(0, 5))
        ttk.Button(self.p12_subframe, text="...", width=4, command=self.select_p12_file).grid(row=0, column=2, sticky="w")
        _try_enable_dnd(self.p12_entry, self.on_drop_p12)
        
        # Password
        tk.Label(self.p12_subframe, text=self.plugin.t("password_label")).grid(row=1, column=0, sticky="w", padx=(0, 5), pady=(5, 0))
        pwd_container = tk.Frame(self.p12_subframe)
        pwd_container.grid(row=1, column=1, sticky="w", pady=(5, 0))
        self.p12_password_entry = tk.Entry(pwd_container, show="*", width=30)
        self.p12_password_entry.pack(side="left", fill="x", expand=True)
        self.show_pwd_btn = tk.Button(pwd_container, text="👁", width=3, command=self.toggle_password_visibility)
        self.show_pwd_btn.pack(side="left", padx=(5, 0))

        # Subframe B: PKCS11 (Smart Card)
        self.pkcs11_subframe = tk.Frame(self.method_details_frame)
        self.pkcs11_subframe.columnconfigure(1, weight=1)

        # DLL Path Selection
        tk.Label(self.pkcs11_subframe, text=self.plugin.t("dll_label")).grid(row=0, column=0, sticky="w", padx=(0, 5))
        
        dll_container = tk.Frame(self.pkcs11_subframe)
        dll_container.grid(row=0, column=1, columnspan=2, sticky="ew")
        dll_container.columnconfigure(0, weight=1)
        
        self.dll_entry = tk.Entry(dll_container, textvariable=self.pkcs11_dll_text, width=40)
        self.dll_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        ttk.Button(dll_container, text="...", width=4, command=self.select_dll_file).pack(side="left", padx=(0, 5))
        ttk.Button(dll_container, text=self.plugin.t("btn_sds_middleware"), command=self.set_sds_middleware_path).pack(side="left")
        
        # PIN code
        tk.Label(self.pkcs11_subframe, text=self.plugin.t("pin_label")).grid(row=1, column=0, sticky="w", padx=(0, 5), pady=(5, 0))
        pin_container = tk.Frame(self.pkcs11_subframe)
        pin_container.grid(row=1, column=1, sticky="w", pady=(5, 0))
        self.pin_entry = tk.Entry(pin_container, show="*", width=30, textvariable=self.pkcs11_pin)
        self.pin_entry.pack(side="left", fill="x", expand=True)
        self.show_pin_btn = tk.Button(pin_container, text="👁", width=3, command=self.toggle_pin_visibility)
        self.show_pin_btn.pack(side="left", padx=(5, 0))
        
        # Load Card Button
        self.load_cards_btn = ttk.Button(self.pkcs11_subframe, text=self.plugin.t("load_certs_btn"), command=self.load_smartcard_certificates)
        self.load_cards_btn.grid(row=1, column=2, sticky="w", padx=(5, 0), pady=(5, 0))
        
        # Certificate Selector
        tk.Label(self.pkcs11_subframe, text=self.plugin.t("select_cert_label")).grid(row=2, column=0, sticky="w", padx=(0, 5), pady=(5, 0))
        
        cert_container = tk.Frame(self.pkcs11_subframe)
        cert_container.grid(row=2, column=1, columnspan=2, sticky="ew", pady=(5, 0))
        
        self.cert_combobox = ttk.Combobox(cert_container, state="readonly", width=45)
        self.cert_combobox.pack(side="left", fill="x", expand=True)
        self.cert_combobox.bind("<<ComboboxSelected>>", self.on_cert_selected)
        
        self.show_cert_btn = tk.Button(cert_container, text="👁", width=3, command=self.show_certificate_details)
        self.show_cert_btn.pack(side="left", padx=(5, 0))

        # Certificate serial display label
        self.cert_serial_label = tk.Label(self.pkcs11_subframe, text="", justify="left", anchor="w", fg="#005A9E", font=("Consolas", 9))
        self.cert_serial_label.grid(row=3, column=1, columnspan=2, sticky="w", pady=(2, 0))

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
        tk.Checkbutton(output_frame, text=self.plugin.t("include_signer_cert"), variable=self.include_signer_cert_var).grid(row=2, column=0, columnspan=2, sticky="w", pady=(5, 0))

        tk.Checkbutton(output_frame, text=self.plugin.t("extract_certs"), variable=self.extract_certs_var).grid(row=3, column=0, columnspan=2, sticky="w", pady=(5, 0))

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

    def select_dll_file(self):
        path = filedialog.askopenfilename(
            parent=self.root,
            title=self.plugin.t("select_dll_title"),
            filetypes=[("DLL Files", "*.dll"), ("All Files", "*.*")],
            initialdir=os.environ.get("SystemRoot", "C:\\Windows")
        )
        if path:
            self.pkcs11_dll_text.set(path)
            self.config["pkcs11_dll_path"] = path
            save_plugin_config(self.config)

    def set_sds_middleware_path(self):
        path = os.path.normpath("C:/Windows/System32/pkcs11CNG.dll")
        self.pkcs11_dll_text.set(path)
        self.config["pkcs11_dll_path"] = path
        save_plugin_config(self.config)
        self.log_message(f"Middleware Stormshield sélectionné : {path}")

    def toggle_pin_visibility(self):
        current_show = self.pin_entry.cget('show')
        if current_show == '*':
            self.pin_entry.config(show='')
        else:
            self.pin_entry.config(show='*')

    def update_signer_method_ui(self):
        method = self.signing_method.get()
        self.config["signing_method"] = method
        save_plugin_config(self.config)
        if method == "p12":
            self.pkcs11_subframe.grid_forget()
            self.p12_subframe.grid(row=0, column=0, sticky="ew")
        else:
            self.p12_subframe.grid_forget()
            self.pkcs11_subframe.grid(row=0, column=0, sticky="ew")

    def load_smartcard_certificates(self):
        if not HAS_PKCS11:
            messagebox.showerror("Error", self.plugin.t("pkcs11_missing"), parent=self.root)
            return

        dll_path = self.pkcs11_dll_text.get().strip()
        if not dll_path:
            messagebox.showerror("Error", self.plugin.t("error_no_dll"), parent=self.root)
            return
        if not os.path.exists(dll_path):
            messagebox.showerror("Error", f"DLL not found: {dll_path}", parent=self.root)
            return

        pin = self.pkcs11_pin.get().strip()
        if not pin:
            messagebox.showerror("Error", self.plugin.t("error_no_pin"), parent=self.root)
            return

        self.log_message(self.plugin.t("loading_certs"))
        self.root.config(cursor="watch")
        self.root.update()

        try:
            lib = pkcs11.lib(dll_path)
            tokens = []
            for slot in lib.get_slots(token_present=True):
                try:
                    tokens.append(slot.get_token())
                except Exception:
                    pass
            self.loaded_certificates = []
            
            for token in tokens:
                token_label = token.label or "Unknown Token"
                try:
                    with token.open(user_pin=pin) as session:
                        certs = session.get_objects({pkcs11.Attribute.CLASS: pkcs11.ObjectClass.CERTIFICATE})
                        for cert in certs:
                            try:
                                label = cert[pkcs11.Attribute.LABEL] or "No Label"
                                cert_id = cert[pkcs11.Attribute.ID]
                                cert_der = cert[pkcs11.Attribute.VALUE]
                                
                                if cert_der:
                                    # Parse subject CN using cryptography
                                    x509_cert = x509.load_der_x509_certificate(cert_der, default_backend())
                                    subject = x509_cert.subject
                                    cns = subject.get_attributes_for_oid(x509.NameOID.COMMON_NAME)
                                    subject_cn = cns[0].value if cns else "Unknown Subject"
                                    
                                    # Extract Serial Number (hex formatted with colons)
                                    serial_val = f"{x509_cert.serial_number:X}"
                                    if len(serial_val) % 2 != 0:
                                        serial_val = "0" + serial_val
                                    serial_str = ":".join(serial_val[i:i+2] for i in range(0, len(serial_val), 2))
                                    
                                    # Extract Key Usage (KU) keys
                                    ku_keys = []
                                    try:
                                        ku_ext = x509_cert.extensions.get_extension_for_class(x509.KeyUsage).value
                                        if ku_ext.digital_signature: ku_keys.append("ku_digital_signature")
                                        if ku_ext.content_commitment: ku_keys.append("ku_non_repudiation")
                                        if ku_ext.key_encipherment: ku_keys.append("ku_key_encipherment")
                                        if ku_ext.data_encipherment: ku_keys.append("ku_data_encipherment")
                                        if ku_ext.key_agreement: ku_keys.append("ku_key_agreement")
                                        if ku_ext.key_cert_sign: ku_keys.append("ku_key_cert_sign")
                                        if ku_ext.crl_sign: ku_keys.append("ku_crl_sign")
                                        if ku_ext.encipher_only: ku_keys.append("ku_encipher_only")
                                        if ku_ext.decipher_only: ku_keys.append("ku_decipher_only")
                                    except Exception:
                                        pass
                                    
                                    # Extract Extended Key Usage (EKU) keys
                                    eku_keys = []
                                    try:
                                        eku_ext = x509_cert.extensions.get_extension_for_class(x509.ExtendedKeyUsage).value
                                        oid_map = {
                                            "1.3.6.1.5.5.7.3.1": "eku_server_auth",
                                            "1.3.6.1.5.5.7.3.2": "eku_client_auth",
                                            "1.3.6.1.5.5.7.3.3": "eku_code_signing",
                                            "1.3.6.1.5.5.7.3.4": "eku_email_protection",
                                            "1.3.6.1.5.5.7.3.8": "eku_time_stamping",
                                            "1.3.6.1.5.5.7.3.9": "eku_ocsp_signing",
                                            "1.3.6.1.4.1.311.20.2.2": "eku_smartcard_logon"
                                        }
                                        for oid in eku_ext:
                                            dotted = oid.dotted_string
                                            eku_keys.append(oid_map.get(dotted, dotted))
                                    except Exception:
                                        pass
                                    
                                    # Extract Validity Dates
                                    try:
                                        nvb = getattr(x509_cert, "not_valid_before_utc", None) or x509_cert.not_valid_before
                                        nva = getattr(x509_cert, "not_valid_after_utc", None) or x509_cert.not_valid_after
                                        nvb_str = nvb.strftime("%Y-%m-%d %H:%M:%S")
                                        nva_str = nva.strftime("%Y-%m-%d %H:%M:%S")
                                    except Exception:
                                        nvb_str = "Unknown"
                                        nva_str = "Unknown"
                                    # Extract Issuer
                                    try:
                                        issuer = x509_cert.issuer
                                        issuer_cns = issuer.get_attributes_for_oid(x509.NameOID.COMMON_NAME)
                                        issuer_cn = issuer_cns[0].value if issuer_cns else "Unknown Issuer"
                                        issuer_dn = issuer.rfc4514_string()
                                    except Exception:
                                        issuer_cn = "Unknown Issuer"
                                        issuer_dn = "Unknown"
                                else:
                                    subject_cn = "Unknown Subject"
                                    serial_str = "Unknown"
                                    ku_keys = []
                                    eku_keys = []
                                    nvb_str = "Unknown"
                                    nva_str = "Unknown"
                                    issuer_cn = "Unknown Issuer"
                                    issuer_dn = "Unknown"
                                
                                # Store certificate info
                                self.loaded_certificates.append({
                                    "token_label": token_label,
                                    "cert_label": label,
                                    "subject_cn": subject_cn,
                                    "id": cert_id,
                                    "value": cert_der,
                                    "display_name": f"[{token_label}] {subject_cn} ({label})",
                                    "serial": serial_str,
                                    "ku_keys": ku_keys,
                                    "eku_keys": eku_keys,
                                    "valid_from": nvb_str,
                                    "valid_to": nva_str,
                                    "issuer_cn": issuer_cn,
                                    "issuer_dn": issuer_dn
                                })
                            except Exception as ce:
                                self.log_message(f"Error reading certificate object on token '{token_label}': {ce}")
                except Exception as te:
                     self.log_message(f"Could not open session or log in to token '{token_label}': {te}")
             
            display_names = [c["display_name"] for c in self.loaded_certificates]
            self.cert_combobox["values"] = display_names
            if display_names:
                self.cert_combobox.current(0)
                self.on_cert_selected()
                self.log_message(self.plugin.t("certs_loaded", len(display_names)))
            else:
                self.cert_combobox.set("")
                self.cert_serial_label.config(text="")
                self.log_message(self.plugin.t("no_certs_on_card"))
                messagebox.showwarning("Warning", self.plugin.t("no_certs_on_card"), parent=self.root)
                
        except Exception as e:
            self.log_message(f"Error loading PKCS#11 module: {e}")
            messagebox.showerror("Error PKCS#11", f"Error: {e}", parent=self.root)
        finally:
            self.root.config(cursor="")

    def show_certificate_details(self):
        selected_idx = self.cert_combobox.current()
        if selected_idx < 0 or selected_idx >= len(self.loaded_certificates):
            messagebox.showwarning("Warning", self.plugin.t("error_no_cert"), parent=self.root)
            return
            
        cert_info = self.loaded_certificates[selected_idx]
        
        # Translate KU keys
        ku_keys = cert_info.get("ku_keys", [])
        translated_ku = [self.plugin.t(k) for k in ku_keys]
        ku_str = ", ".join(translated_ku) if translated_ku else self.plugin.t("none_val")
        
        # Translate EKU keys
        eku_keys = cert_info.get("eku_keys", [])
        translated_eku = [self.plugin.t(k) if k.startswith("eku_") else k for k in eku_keys]
        eku_str = ", ".join(translated_eku) if translated_eku else self.plugin.t("none_val")

        details = (
            f"{self.plugin.t('serial_label')} {cert_info.get('serial', 'Unknown')}\n\n"
            f"Subject (CN):\n  {cert_info.get('subject_cn', 'Unknown')}\n\n"
            f"Label:\n  {cert_info.get('cert_label', 'Unknown')}\n\n"
            f"{self.plugin.t('issuer_label')} {cert_info.get('issuer_cn', 'Unknown')}\n"
            f"  DN: {cert_info.get('issuer_dn', 'Unknown')}\n\n"
            f"{self.plugin.t('validity_label')} {cert_info.get('valid_from', 'Unknown')} -> {cert_info.get('valid_to', 'Unknown')}\n\n"
            f"{self.plugin.t('ku_label')} {ku_str}\n\n"
            f"{self.plugin.t('eku_label')} {eku_str}"
        )
        
        detail_win = tk.Toplevel(self.root)
        detail_win.title(self.plugin.t("cert_details_title"))
        detail_win.geometry("500x425")
        detail_win.transient(self.root)
        detail_win.grab_set()
        detail_win.resizable(True, True)
        
        frame = tk.Frame(detail_win, padx=10, pady=10)
        frame.pack(fill="both", expand=True)
        
        scrollbar = ttk.Scrollbar(frame)
        scrollbar.pack(side="right", fill="y")
        
        txt = tk.Text(frame, wrap="word", font=("Consolas", 10), yscrollcommand=scrollbar.set, bg="#F3F3F3", fg="#333333")
        txt.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=txt.yview)
        
        txt.insert("1.0", details)
        txt.config(state="disabled")
        
        btn_frame = tk.Frame(detail_win, pady=5)
        btn_frame.pack(fill="x")
        ttk.Button(btn_frame, text="OK", command=detail_win.destroy).pack()
        
        detail_win.update_idletasks()
        parent_x = self.root.winfo_x()
        parent_y = self.root.winfo_y()
        parent_w = self.root.winfo_width()
        parent_h = self.root.winfo_height()
        
        win_w = detail_win.winfo_width()
        win_h = detail_win.winfo_height()
        
        x = parent_x + (parent_w - win_w) // 2
        y = parent_y + (parent_h - win_h) // 2
        detail_win.geometry(f"+{x}+{y}")

    def on_cert_selected(self, event=None):
        selected_idx = self.cert_combobox.current()
        if selected_idx >= 0 and selected_idx < len(self.loaded_certificates):
            cert_info = self.loaded_certificates[selected_idx]
            serial = cert_info.get("serial", "Unknown")
            self.cert_serial_label.config(text=f"{self.plugin.t('serial_label')} {serial}")
        else:
            self.cert_serial_label.config(text="")

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

    def on_drop_p12(self, event):
        try:
            paths = _split_dnd_files(getattr(event, "data", ""))
            if not paths:
                return

            picked = None
            for p in paths:
                ext = os.path.splitext(p)[1].lower()
                if ext in (".p12", ".pfx") and os.path.exists(p):
                    picked = p
                    break

            if not picked:
                return

            self.p12_file_path = picked
            self.p12_label_text.set(picked)
            self.log_message(self.plugin.t("cert_saved_main", picked))
        except Exception:
            # Fail silently: DnD is optional.
            return

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

        method = self.signing_method.get()
        
        if method == "p12":
            if not self.p12_file_path:
                messagebox.showerror("Error", self.plugin.t("error_no_p12"), parent=self.root)
                return
        else: # pkcs11
            if not HAS_PKCS11:
                messagebox.showerror("Error", self.plugin.t("pkcs11_missing"), parent=self.root)
                return
            dll_path = self.pkcs11_dll_text.get().strip()
            if not dll_path:
                messagebox.showerror("Error", self.plugin.t("error_no_dll"), parent=self.root)
                return
            if not os.path.exists(dll_path):
                messagebox.showerror("Error", f"DLL not found: {dll_path}", parent=self.root)
                return
            pin = self.pkcs11_pin.get().strip()
            if not pin:
                messagebox.showerror("Error", self.plugin.t("error_no_pin"), parent=self.root)
                return
            selected_idx = self.cert_combobox.current()
            if selected_idx < 0 or not self.loaded_certificates:
                messagebox.showerror("Error", self.plugin.t("error_no_cert"), parent=self.root)
                return
            selected_cert_info = self.loaded_certificates[selected_idx]
        
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
            if method == "p12":
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
                jwt_headers = {}
                if self.include_signer_cert_var.get():
                    x5c_list = cert_to_x5c_list(cert, additional_certs)
                    jwt_headers = {"x5c": x5c_list} if x5c_list else {}
            else: # pkcs11
                cert = x509.load_der_x509_certificate(selected_cert_info["value"], default_backend())
                additional_certs = []
                jwt_headers = {}
                if self.include_signer_cert_var.get():
                    x5c_list = cert_to_x5c_list(cert, additional_certs)
                    jwt_headers = {"x5c": x5c_list} if x5c_list else {}
        except Exception as e:
            error_trace = traceback.format_exc()
            messagebox.showerror("Error Setup Key", f"{e}\n\n{error_trace}", parent=self.root)
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

                saved_cert = save_cert_to_cer(cert, None, output_folder)
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

                if method == "p12":
                    token = sign_json_file(copy_path, pem_key, headers=jwt_headers, algorithm=algorithm)
                else: # pkcs11
                    self.log_message(self.plugin.t("signing_pkcs11"))
                    lib = pkcs11.lib(dll_path)
                    tokens = []
                    for slot in lib.get_slots(token_present=True):
                        try:
                            tokens.append(slot.get_token())
                        except Exception:
                            pass
                    target_token = None
                    for tok in tokens:
                        if tok.label == selected_cert_info["token_label"]:
                            target_token = tok
                            break
                    if not target_token:
                        raise RuntimeError(f"Token '{selected_cert_info['token_label']}' not found.")

                    with target_token.open(user_pin=pin) as session:
                        # Find private key matching ID
                        priv_keys = list(session.get_objects({
                            pkcs11.Attribute.CLASS: pkcs11.ObjectClass.PRIVATE_KEY,
                            pkcs11.Attribute.ID: selected_cert_info["id"]
                        }))
                        if not priv_keys:
                            # Try finding by label
                            priv_keys = list(session.get_objects({
                                pkcs11.Attribute.CLASS: pkcs11.ObjectClass.PRIVATE_KEY,
                                pkcs11.Attribute.LABEL: selected_cert_info["cert_label"]
                            }))
                        if not priv_keys:
                            raise RuntimeError(f"Private key for certificate '{selected_cert_info['cert_label']}' not found on token.")
                        
                        priv_key_obj = priv_keys[0]
                        
                        # Read payload
                        with open(copy_path, "r", encoding="utf-8") as f:
                            payload_data = json.load(f)
                        
                        headers = {
                            "alg": algorithm,
                            "typ": "JWT"
                        }
                        if jwt_headers:
                            headers.update(jwt_headers)
                            
                        header_json = json.dumps(headers, separators=(',', ':'))
                        payload_json = json.dumps(payload_data, separators=(',', ':'))
                        
                        header_b64 = base64.urlsafe_b64encode(header_json.encode('utf-8')).decode('utf-8').rstrip('=')
                        payload_b64 = base64.urlsafe_b64encode(payload_json.encode('utf-8')).decode('utf-8').rstrip('=')
                        
                        signing_input = f"{header_b64}.{payload_b64}".encode('utf-8')
                        
                        if algorithm == "RS256":
                            import hashlib
                            digest = hashlib.sha256(signing_input).digest()
                            # ASN.1 DER prefix for SHA-256 DigestInfo
                            digest_info = b'\x30\x31\x30\x0d\x06\x09\x60\x86\x48\x01\x65\x03\x04\x02\x01\x05\x00\x04\x20' + digest
                            mechanism = pkcs11.Mechanism.RSA_PKCS
                            signature = priv_key_obj.sign(digest_info, mechanism=mechanism)
                        elif algorithm == "PS256":
                            mechanism = pkcs11.Mechanism.RSA_PKCS_PSS
                            mechanism_param = (pkcs11.Mechanism.SHA256, pkcs11.MGF.SHA256, 32)
                            signature = priv_key_obj.sign(signing_input, mechanism=mechanism, mechanism_param=mechanism_param)
                        else:
                            raise ValueError(f"Unsupported algorithm: {algorithm}")
                            
                        signature_b64 = base64.urlsafe_b64encode(signature).decode('utf-8').rstrip('=')
                        token = f"{header_b64}.{payload_b64}.{signature_b64}"

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
                error_msg = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
                self.log_message(self.plugin.t("error_for_file", json_file_path, error_msg))
                error_count += 1
        
        self.log_message(self.plugin.t("signing_summary", success_count, error_count))

        # Cleanup temp file
        try:
            shutil.rmtree(temp_dir)
        except Exception as e:
            print(f"Error cleaning up temp dir: {e}")
