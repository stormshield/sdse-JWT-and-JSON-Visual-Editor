
import uuid
import secrets
import time
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import sys
import json
import base64
import hashlib

import importlib.util

def get_plugin_resource_path(relative_path):
    """Get absolute path to plugin resource, works for dev and for PyInstaller."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    dev_path = os.path.join(current_dir, relative_path)
    
    if os.path.exists(dev_path):
        return dev_path
    
    try:
        base_path = sys._MEIPASS
        possible_paths = [
            os.path.join(base_path, "plugins", "SDS plugins", "ids", relative_path),
            os.path.join(base_path, "plugins", "SDS_plugins", "ids", relative_path),
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
        print(f"Plugin IDs: languages.json not found at {lang_path}")
except Exception as e:
    print(f"Plugin IDs: Could not load languages.json: {e}")
    import traceback
    traceback.print_exc()
    translations = {}

# Try to import cryptography for certificate parsing
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

# Keys that reference certificate IDs in certificateData
CERTIFICATE_ID_KEYS = {"certificateIds", "certificateID", "updateOnlyFromCAs", "removeOnlyFromCAs"}
# Keys that reference LDAP IDs in ldapData
LDAP_ID_KEYS = {"ldapAddressBookList"}

class Plugin:
    def __init__(self, app):
        self.app = app
        self.id_generators = ["mongo", "uuid"]
        self.translations = translations

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
        pass

    def extend_context_menu(self, menu, event):
        # Check for ID field to offer ID generation
        try:
            key_name_at_cursor, _ = self.app.find_json_key_at_cursor()
            if key_name_at_cursor == "id":
                if menu.index("end") is not None:
                    menu.add_separator()
                                
                # Logic to find the value range to replace
                cursor_idx = self.app.text.index(f"@{event.x},{event.y}")
                
                start_replace = None
                end_replace = None
                
                full_text = self.app.text.get("1.0", "end-1c")
                try:
                    c_offset = int(self.app.text.count("1.0", cursor_idx, "chars")[0])
                except Exception:
                    line_num, col_num = map(int, cursor_idx.split('.'))
                    c_offset = sum(len(self.app.text.get(f"{i}.0", f"{i}.end")) + 1 for i in range(1, line_num)) + col_num

                q_left = full_text.rfind('"', 0, c_offset)
                q_right = full_text.find('"', c_offset)
                
                if q_left != -1 and q_right != -1:
                    segment = full_text[q_left:q_right+1]
                    if '\n' not in segment and ':' not in segment:
                        start_replace = self.app.text.index(f"1.0 + {q_left+1} chars")
                        end_replace = self.app.text.index(f"1.0 + {q_right} chars")
                
                if start_replace and end_replace:
                    id_menu = tk.Menu(menu, tearoff=0)
                    # Access id_generators from plugin configuration
                    generators = getattr(self, 'id_generators', ["mongo", "uuid"])
                    for gen_type in generators:
                        id_menu.add_command(
                            label=gen_type, 
                            command=lambda s=start_replace, e=end_replace, t=gen_type: self.app.replace_word(s, e, self.generate_random_id(t))
                        )
                    menu.add_cascade(label=self.t("context_generate_id"), menu=id_menu)

        except Exception:
            pass

        # Check for certificate ID or LDAP ID references to offer preview
        try:
            key_name_at_cursor, json_path = self.app.find_json_key_at_cursor()
            
            if key_name_at_cursor and (key_name_at_cursor in CERTIFICATE_ID_KEYS or key_name_at_cursor in LDAP_ID_KEYS):
                # Extract the ID value under the cursor
                id_value = self._extract_id_at_cursor(event)
                
                if id_value:
                    full_text = self.app.text.get("1.0", "end-1c")
                    try:
                        data = json.loads(full_text)
                    except Exception:
                        data = None
                    
                    if data:
                        if key_name_at_cursor in CERTIFICATE_ID_KEYS:
                            # Look up certificate in certificateData
                            cert_entry = self._find_certificate_data(data, id_value)
                            if cert_entry:
                                if menu.index("end") is not None:
                                    menu.add_separator()
                                menu.add_command(
                                    label=self.t("context_show_certificate"),
                                    command=lambda e=cert_entry, i=id_value: self._show_certificate_preview(e, i)
                                )
                            
                        elif key_name_at_cursor in LDAP_ID_KEYS:
                            # Look up LDAP config in ldapData
                            ldap_entry = self._find_ldap_data(data, id_value)
                            if ldap_entry:
                                if menu.index("end") is not None:
                                    menu.add_separator()
                                menu.add_command(
                                    label=self.t("context_show_ldap"),
                                    command=lambda e=ldap_entry, i=id_value: self._show_ldap_preview(e, i)
                                )
        except Exception:
            pass

    def _extract_id_at_cursor(self, event):
        """Extract the string value (ID) under the cursor position."""
        try:
            cursor_idx = self.app.text.index(f"@{event.x},{event.y}")
            full_text = self.app.text.get("1.0", "end-1c")
            
            try:
                c_offset = int(self.app.text.count("1.0", cursor_idx, "chars")[0])
            except Exception:
                line_num, col_num = map(int, cursor_idx.split('.'))
                c_offset = sum(len(self.app.text.get(f"{i}.0", f"{i}.end")) + 1 for i in range(1, line_num)) + col_num

            # Find the quoted string surrounding the cursor
            q_left = full_text.rfind('"', 0, c_offset)
            q_right = full_text.find('"', c_offset)
            
            if q_left != -1 and q_right != -1:
                candidate = full_text[q_left+1:q_right]
                # Validate: should look like a hex ID (no newlines, no colons, reasonable length)
                if '\n' not in candidate and ':' not in candidate and len(candidate) >= 8 and len(candidate) <= 64:
                    return candidate.strip()
            
            return None
        except Exception:
            return None

    def _find_certificate_data(self, data, cert_id):
        """Find a certificate entry in certificateData by ID."""
        cert_data_list = data.get("certificateData", [])
        if isinstance(cert_data_list, list):
            for entry in cert_data_list:
                if isinstance(entry, dict) and entry.get("id") == cert_id:
                    return entry
        return None

    def _find_ldap_data(self, data, ldap_id):
        """Find an LDAP entry in ldapData by ID."""
        ldap_data_list = data.get("ldapData", [])
        if isinstance(ldap_data_list, list):
            for entry in ldap_data_list:
                if isinstance(entry, dict) and entry.get("id") == ldap_id:
                    return entry
        return None

    def _show_certificate_preview(self, cert_entry, cert_id):
        """Show certificate details in a popup window."""
        cert_b64 = cert_entry.get("data", "")
        
        if not cert_b64:
            messagebox.showwarning(self.t("msg_info_title"), self.t("id_not_found", id=cert_id))
            return

        if not HAS_CRYPTO:
            messagebox.showerror(self.t("msg_error_title"), 
                "The 'cryptography' library is required to display certificate details.")
            return

        try:
            # Decode base64 to DER
            der_bytes = base64.b64decode(cert_b64, validate=True)
            cert_obj = x509.load_der_x509_certificate(der_bytes, default_backend())
        except Exception as e:
            messagebox.showerror(self.t("msg_error_title"), f"Error loading certificate: {e}")
            return

        try:
            win = tk.Toplevel(self.app)
            win.title(self.t("cert_window_title"))
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

            frm = ttk.Frame(win, padding=(12, 12))
            frm.pack(fill="both", expand=True)
            frm.columnconfigure(1, weight=1)

            # Extract certificate fields
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

            close_btn = ttk.Button(btn_frame, text=self.t('button_close'), command=win.destroy)
            close_btn.grid(row=0, column=1, sticky='e', padx=6)
            close_btn.focus_set()
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
            messagebox.showerror(self.t("msg_error_title"), f"Error displaying certificate: {e}")

    def _show_ldap_preview(self, ldap_entry, ldap_id):
        """Show LDAP configuration details in a popup window."""
        config = ldap_entry.get("configuration", {})
        if not config:
            messagebox.showwarning(self.t("msg_info_title"), self.t("id_not_found", id=ldap_id))
            return

        try:
            win = tk.Toplevel(self.app)
            win.title(self.t("ldap_window_title"))
            win.transient(self.app)
            win.grab_set()

            width, height = 560, 460
            self.app.update_idletasks()
            x = self.app.winfo_x() + (self.app.winfo_width() // 2) - (width // 2)
            y = self.app.winfo_y() + (self.app.winfo_height() // 2) - (height // 2)
            win.geometry(f"{width}x{height}+{x}+{y}")
            try:
                win.minsize(450, 280)
            except Exception:
                pass

            frm = ttk.Frame(win, padding=(12, 12))
            frm.pack(fill="both", expand=True)
            frm.columnconfigure(1, weight=1)

            # Extract LDAP configuration fields
            access = config.get("access", {})
            credentials = config.get("credentials", {})
            advanced = config.get("advanced", {})
            search_attrs = config.get("searchAttributeNames", {})

            labels = [
                (self.t('ldap_name'), config.get("name", "")),
                (self.t('ldap_address'), access.get("address", "")),
                (self.t('ldap_port'), str(access.get("port", ""))),
                (self.t('ldap_protocol'), access.get("protocol", "")),
                (self.t('ldap_username'), credentials.get("username", "")),
                (self.t('ldap_base'), advanced.get("base", "")),
                (self.t('ldap_depth'), advanced.get("depth", "")),
                (self.t('ldap_timeout'), str(advanced.get("timeoutSeconds", ""))),
                (self.t('ldap_email_attr'), search_attrs.get("emailAddress", "")),
                (self.t('ldap_cn_attr'), search_attrs.get("commonName", "")),
                (self.t('ldap_cert_attr'), search_attrs.get("certificate", "")),
            ]

            value_labels = []
            for r, (lbl, val) in enumerate(labels):
                ttk.Label(frm, text=lbl+":", font=(None, 10, 'bold')).grid(row=r, column=0, sticky='nw', pady=2)
                val_widget = ttk.Label(frm, text=val, wraplength=350, justify='left', anchor='w')
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

            close_btn = ttk.Button(btn_frame, text=self.t('button_close'), command=win.destroy)
            close_btn.grid(row=0, column=1, sticky='e', padx=6)
            close_btn.focus_set()

            def adjust_wrap(event=None):
                try:
                    w = max(200, win.winfo_width() - 250)
                    for lbl in value_labels:
                        lbl.config(wraplength=w)
                except Exception:
                    pass

            win.bind('<Configure>', adjust_wrap)
            win.columnconfigure(0, weight=1)
            win.rowconfigure(0, weight=1)
        except Exception as e:
            messagebox.showerror(self.t("msg_error_title"), f"Error displaying LDAP preview: {e}")

    def generate_random_id(self, method="mongo"):
        if method == "uuid":
            return str(uuid.uuid4())
        elif method.startswith("hex:"):
            try:
                length = int(method.split(":")[1])
                return secrets.token_hex(length // 2 + length % 2)[:length]
            except Exception:
                return secrets.token_hex(8)
        else:
            timestamp = hex(int(time.time()))[2:]
            if len(timestamp) < 8:
                timestamp = timestamp.zfill(8)
            random_part = secrets.token_hex(8) 
            return (timestamp + random_part)[:24]
