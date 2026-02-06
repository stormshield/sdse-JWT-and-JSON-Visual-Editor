
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import base64
import json
import re
import os
import sys

import importlib.util
import secrets

def get_plugin_resource_path(relative_path):
    """Get absolute path to plugin resource, works for dev and for PyInstaller."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    dev_path = os.path.join(current_dir, relative_path)
    
    if os.path.exists(dev_path):
        return dev_path
    
    try:
        base_path = sys._MEIPASS
        possible_paths = [
            os.path.join(base_path, "plugins", "Required plugins", "certificates", relative_path),
            os.path.join(base_path, "plugins", "Required_plugins", "certificates", relative_path),
            os.path.join(base_path, relative_path)
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
        return possible_paths[0]
    except Exception:
        return dev_path

# Load translations
try:
    lang_path = get_plugin_resource_path("languages.json")
    if os.path.exists(lang_path):
        with open(lang_path, "r", encoding="utf-8") as f:
            translations = json.load(f)
    else:
        translations = {}
        print(f"Plugin Certificates: languages.json not found at {lang_path}")
except Exception as e:
    print(f"Plugin Certificates: Could not load languages.json: {e}")
    import traceback
    traceback.print_exc()
    translations = {}

try:
    from cryptography import x509
    from cryptography.hazmat.backends import default_backend
    from cryptography.x509.oid import NameOID
    from cryptography.hazmat.primitives.serialization import Encoding
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False
    x509 = None
    default_backend = None
    NameOID = None
    Encoding = None

def b64url_decode(input_str):
    rem = len(input_str) % 4
    if rem:
        input_str += '=' * (4 - rem)
    return base64.urlsafe_b64decode(input_str)

class Plugin:
    def __init__(self, app):
        self.app = app
        self.translations = translations
        self.current_menu_label = None

    def t(self, key, **kwargs):
        lang = getattr(self.app, "current_language", "en")
        try:
             settings_path = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "settings.json")
             if os.path.exists(settings_path):
                 with open(settings_path, "r", encoding="utf-8") as f:
                     settings = json.load(f)
                     lang = settings.get("language", lang)
        except Exception:
            pass
        
        text = self.translations.get(lang, self.translations.get("en", {})).get(key, key)
        if kwargs:
            try:
                return text.format(**kwargs)
            except:
                return text
        return text

    def register(self):
        # Register for events
        pass

    def on_event(self, event_name, data=None):
        if event_name == "ui_ready":
             try:
                 self.app.tools_menu.add_separator()
                 label = self.t("menu_tools_extract_cert")
                 self.current_menu_label = label
                 self.app.tools_menu.add_command(
                     label=label, 
                     command=self.extract_certificate_from_jwt, 
                     state="disabled"
                 )
             except Exception as e:
                print(f"Error registering cert plugin UI: {e}")

        elif event_name == "jwt_loaded":
            # Enable the menu item
            try:
                # Find the item by label (careful with language changes) - or just enabling by index if we knew it to be last
                # Better: search for the label
                label = self.t("menu_tools_extract_cert")
                self.app.tools_menu.entryconfig(label, state="normal")
            except Exception:
                pass

        elif event_name == "language_changed":
            self.update_menu_language()

        elif event_name == "file_closed":
            try:
                label = self.t("menu_tools_extract_cert")
                self.app.tools_menu.entryconfig(label, state="disabled")
            except Exception:
                pass

    def update_menu_language(self):
        if self.current_menu_label is None:
            return

        try:
            tools_menu = self.app.tools_menu
            new_label = self.t("menu_tools_extract_cert")
            if new_label == self.current_menu_label:
                return

            last_index = tools_menu.index('end')
            if last_index is None:
                return

            for i in range(last_index + 1):
                try:
                    item_label = tools_menu.entrycget(i, "label")
                    if item_label == self.current_menu_label:
                        tools_menu.entryconfig(i, label=new_label)
                        self.current_menu_label = new_label
                        break
                except Exception:
                    continue
        except Exception as e:
            print(f"Plugin Certificates: Error updating menu language: {e}")

    def extend_context_menu(self, menu, event):
        if not HAS_CRYPTO:
            return

        text_widget = self.app.text
        index = text_widget.index(f"@{event.x},{event.y}")

        try:
            full = text_widget.get("1.0", "end-1c")
            try:
                cursor_offset = int(text_widget.count("1.0", index, "chars")[0])
            except Exception:
                line, col = map(int, index.split('.'))
                cursor_offset = sum(len(text_widget.get(f"{i}.0", f"{i}.end")) + 1 for i in range(1, line)) + col

            left_double = full.rfind('"', 0, cursor_offset)
            left_single = full.rfind("'", 0, cursor_offset)
            if left_double > left_single:
                left = left_double; quote = '"'
            else:
                left = left_single; quote = "'"

            candidate = None
            if left != -1:
                right = full.find(quote, cursor_offset)
                if right != -1 and right - left > 20:
                    candidate = full[left+1:right]

            if not candidate:
                raw = text_widget.get(f"{index} wordstart", f"{index} wordend").strip()
                if len(raw) > 2 and ((raw[0] == '"' and raw[-1] == '"') or (raw[0] == "'" and raw[-1] == "'")):
                    candidate = raw[1:-1]
                else:
                    candidate = raw

            cert_obj = None
            if candidate and len(candidate) > 50:
                try:
                    decoded = base64.b64decode(candidate, validate=True)
                    try:
                        cert_obj = x509.load_der_x509_certificate(decoded, default_backend())
                    except Exception:
                        cert_obj = None
                except Exception:
                    cert_obj = None

            if cert_obj is not None:
                if menu.index("end") is not None:
                    menu.add_separator()
                
                label = self.t("show_certs")
                if label == "show_certs": label = "Afficher le certificat"
                
                menu.add_command(label=label,
                                 command=lambda c=cert_obj, b=candidate: self._show_certificate_info(c, b))
        except Exception:
            pass

    def extract_certificate_from_jwt(self):
        if not self.app.raw_jwt_content:
            return

        parts = self.app.raw_jwt_content.strip().split('.')
        if len(parts) < 2:
            return
        
        header_b64 = parts[0]
        try:
            header_bytes = b64url_decode(header_b64)
            header_json = json.loads(header_bytes.decode('utf-8'))
        except Exception as e:
            messagebox.showerror(self.t("msg_error_title"), f"Erreur de lecture du header JWT: {e}")
            return
            
        x5c_list = header_json.get('x5c')
        if not x5c_list or not isinstance(x5c_list, list):
            messagebox.showinfo(self.t("msg_info_title"), self.t("msg_no_cert_found"))
            return
            
        cert_b64 = x5c_list[0]
        
        pem_str = "-----BEGIN CERTIFICATE-----\n"
        for i in range(0, len(cert_b64), 64):
            pem_str += cert_b64[i:i+64] + "\n"
        pem_str += "-----END CERTIFICATE-----\n"
        
        if not HAS_CRYPTO:
             messagebox.showerror(self.t("msg_error_title"), "La bibliothèque 'cryptography' est requise pour cette fonctionnalité.")
             return

        try:
             cert = x509.load_pem_x509_certificate(pem_str.encode('utf-8'), default_backend())
             self._show_certificate_info(cert, cert_b64)
        except Exception as e:
             messagebox.showerror(self.t("msg_error_title"), f"Erreur de chargement du certificat: {e}")

    def _show_certificate_info(self, cert_obj, cert_b64=None):
        try:
            win = tk.Toplevel(self.app)
            win.title(self.t("certs_window_title"))
            win.transient(self.app)
            win.grab_set()

            width, height = 720, 400
            self.app.update_idletasks()
            x = self.app.winfo_x() + (self.app.winfo_width() // 2) - (width // 2)
            y = self.app.winfo_y() + (self.app.winfo_height() // 2) - (height // 2)
            win.geometry(f"{width}x{height}+{x}+{y}")
            try:
                win.minsize(600, 260)
            except Exception:
                pass

            frm = ttk.Frame(win, padding=(12,12))
            frm.pack(fill="both", expand=True)
            frm.columnconfigure(1, weight=1)

            try:
                subj = cert_obj.subject.rfc4514_string()
            except Exception:
                subj = ""
            try:
                issuer = cert_obj.issuer.rfc4514_string()
            except Exception:
                issuer = ""

            try:
                cn_attr = cert_obj.subject.get_attributes_for_oid(NameOID.COMMON_NAME)
                subj_cn = cn_attr[0].value if cn_attr else ""
            except Exception:
                subj_cn = ""
            try:
                issuer_cn_attr = cert_obj.issuer.get_attributes_for_oid(NameOID.COMMON_NAME)
                issuer_cn = issuer_cn_attr[0].value if issuer_cn_attr else ""
            except Exception:
                issuer_cn = ""
            try:
                not_before = getattr(cert_obj, 'not_valid_before_utc', None)
                if not_before is None:
                    not_before = cert_obj.not_valid_before
                not_before = not_before.isoformat()
            except Exception:
                not_before = ""
            try:
                not_after = getattr(cert_obj, 'not_valid_after_utc', None)
                if not_after is None:
                    not_after = cert_obj.not_valid_after
                not_after = not_after.isoformat()
            except Exception:
                not_after = ""
            try:
                serial = hex(cert_obj.serial_number)
            except Exception:
                serial = str(cert_obj.serial_number)

            try:
                import hashlib
                der = cert_obj.public_bytes(Encoding.DER)
                sha256 = hashlib.sha256(der).hexdigest()
                fp = ':'.join(sha256[i:i+2] for i in range(0, len(sha256), 2)).upper()
            except Exception:
                fp = ""

            labels = [
                (self.t('cert_cn_subject'), subj_cn),
                (self.t('cert_subject'), subj),
                (self.t('cert_cn_issuer'), issuer_cn),
                (self.t('cert_issuer'), issuer),
                (self.t('cert_valid_from'), not_before),
                (self.t('cert_valid_until'), not_after),
                (self.t('cert_serial'), serial),
                (self.t('cert_sha256'), fp),
            ]

            value_labels = []
            for r, (lbl, val) in enumerate(labels):
                ttk.Label(frm, text=lbl+":", font=(None, 10, 'bold')).grid(row=r, column=0, sticky='nw', pady=2)
                val_widget = ttk.Label(frm, text=val, wraplength=480, justify='left', anchor='w')
                val_widget.grid(row=r, column=1, sticky='we', pady=2, padx=(8,0))
                value_labels.append(val_widget)

                def make_copy(v=val):
                    def _cpy():
                        try:
                            self.app.clipboard_clear()
                            self.app.clipboard_append(v)
                        except Exception:
                            pass
                    return _cpy
                ttk.Button(frm, text=self.t('copy_button'), width=8, command=make_copy(val)).grid(row=r, column=2, padx=(8,0), pady=2)

            btn_frame = ttk.Frame(win)
            btn_frame.pack(fill='x', padx=12, pady=(12,16))
            btn_frame.grid_columnconfigure(0, weight=1)

            def save_cert():
                try:
                    der = cert_obj.public_bytes(Encoding.DER)
                    path = filedialog.asksaveasfilename(defaultextension=".cer",
                                                        filetypes=[("DER certificate", "*.cer;*.der"), ("All files", "*.*")])
                    if path:
                        with open(path, "wb") as f:
                            f.write(der)
                        messagebox.showinfo(self.t('msg_info_title'), self.t('cert_saved', path=path))
                except Exception as e:
                    messagebox.showerror(self.t('msg_error_title'), self.t('cert_save_error', err=e))
            cancel_btn = ttk.Button(btn_frame, text=self.t('button_cancel'), command=win.destroy)
            cancel_btn.grid(row=0, column=1, sticky='e', padx=6)
            cancel_btn.focus_set()
            ttk.Button(btn_frame, text=self.t('save_cer'), command=save_cert).grid(row=0, column=2, sticky='e')

            def adjust_wrap(event=None):
                try:
                    w = max(240, win.winfo_width() - 280)
                    for lbl in value_labels:
                        lbl.config(wraplength=w)
                except Exception:
                    pass

            win.bind('<Configure>', adjust_wrap)
            win.columnconfigure(0, weight=1)
            win.rowconfigure(0, weight=1)
        except Exception as e:
            messagebox.showerror(self.t("msg_error_title"), f"Erreur affichage certificat: {e}")
