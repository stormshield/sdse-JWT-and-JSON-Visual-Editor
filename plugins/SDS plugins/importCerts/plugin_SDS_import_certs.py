import tkinter as tk
from tkinter import filedialog, messagebox
import base64
import json
import time
import secrets
import re
import os
import sys

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
            os.path.join(base_path, "plugins", "SDS plugins", "importCerts", relative_path),
            os.path.join(base_path, "plugins", "SDS_plugins", "importCerts", relative_path),
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
        print(f"Plugin SDS Import Certs: languages.json not found at {lang_path}")
except Exception as e:
    print(f"Plugin SDS Import Certs: Could not load languages.json: {e}")
    import traceback
    traceback.print_exc()
    translations = {}

class Plugin:
    def __init__(self, app):
        self.app = app
        print("Plugin Import Certs: Loaded successfully")
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
        try:
            print("Plugin Import Certs: extend_context_menu called")
            
            text_widget = self.app.text
            index = text_widget.index(f"@{event.x},{event.y}")
            line_idx = index.split('.')[0]
            line_text = text_widget.get(f"{line_idx}.0", f"{line_idx}.end")
            
            print(f"Plugin Import Certs: Line text = '{line_text}'")

            # Permissive check: if the line contains "certificateData", show the menu
            if "certificateData" in line_text:
                print("Plugin Import Certs: Found certificateData, adding menu item")
                if menu.index("end") is not None:
                    menu.add_separator()
                
                menu.add_command(label=self.t("context_import_cert"), command=self.import_certificate)
                return

        except Exception as e:
            print(f"Error in extend_context_menu (import certs): {e}")
            import traceback
            traceback.print_exc()

    def import_certificate(self):
        try:
            file_types = [
                ("Certificate files", "*.cer;*.crt;*.pem;*.der"),
                ("All files", "*.*")
            ]
            
            path = filedialog.askopenfilename(
                title=self.t("import_cert_dialog_title"), 
                filetypes=file_types
            )
            if not path:
                return

            with open(path, "rb") as f:
                content_bytes = f.read()

            b64_data = ""
            
            # Check if it looks like PEM
            is_pem = False
            try:
                content_str = content_bytes.decode('utf-8').strip()
                if "-----BEGIN" in content_str:
                    is_pem = True
                    # Remove headers and newlines
                    lines = content_str.splitlines()
                    filtered_lines = [
                        line.strip() for line in lines 
                        if not line.startswith("-----") and line.strip()
                    ]
                    b64_data = "".join(filtered_lines)
            except Exception:
                # Decoding failed or not text, treat as binary DER
                pass

            if not is_pem:
                # Assume DER, encode to base64
                b64_data = base64.b64encode(content_bytes).decode('ascii')

            # Generate ID
            new_id = self.generate_id()

            # Insert into JSON
            self.add_certificate_entry(new_id, b64_data)

            messagebox.showinfo(
                self.t("import_cert_success_title"), 
                self.t("import_cert_success_text")
            )

        except Exception as e:
            messagebox.showerror(
                self.t("import_cert_error_title"), 
                f"{e}"
            )

    def generate_id(self):
        """
        Generates a 24-char hex ID (Mongo-like)
        Timestamp (8 chars) + Random (16 chars)
        """
        timestamp = hex(int(time.time()))[2:]
        if len(timestamp) < 8:
            timestamp = timestamp.zfill(8)
        random_part = secrets.token_hex(8) 
        return (timestamp + random_part)[:24]

    def add_certificate_entry(self, cert_id, cert_data):
        # Save current cursor position and view
        cursor_index = self.app.text.index("insert")
        yview = self.app.text.yview()
        
        txt = self.app.text.get("1.0", "end-1c")
        try:
            data = json.loads(txt)
        except Exception:
            raise ValueError("Invalid JSON in editor")

        if "certificateData" not in data:
            data["certificateData"] = []
        
        if not isinstance(data["certificateData"], list):
             raise ValueError("'certificateData' is not a list")

        new_entry = {
            "id": cert_id,
            "data": cert_data
        }

        data["certificateData"].append(new_entry)

        # Update editor
        pretty = json.dumps(data, indent=2, ensure_ascii=False)
        self.app._replace_text(pretty)
        self.app.update_json_tree()
        
        # Restore cursor position and view
        try:
            self.app.text.mark_set("insert", cursor_index)
            self.app.text.yview_moveto(yview[0])
        except Exception:
            pass  # If position is invalid after reformatting, just ignore
        
        # Highlight the newly added entry
        self.highlight_new_entry(cert_id)
    
    def highlight_new_entry(self, cert_id):
        """Find and highlight the newly added certificate entry"""
        try:
            # Search for the ID in the text
            search_pattern = f'"{cert_id}"'
            start_pos = self.app.text.search(search_pattern, "1.0", stopindex="end")
            
            if start_pos:
                # Get the line number
                line_num = start_pos.split('.')[0]
                
                # Highlight the entire certificate entry (id and data lines)
                # Typically it's 3 lines: { "id": "...", "data": "..." }
                # But can vary based on formatting
                
                # Find the opening brace before this ID
                brace_line = int(line_num)
                search_start = f"{brace_line}.0"
                for i in range(5):  # Look back up to 5 lines
                    check_line = f"{brace_line - i}.0"
                    line_text = self.app.text.get(check_line, f"{brace_line - i}.end")
                    if "{" in line_text and "id" not in line_text:
                        search_start = check_line
                        break
                
                # Find the closing brace after the data
                end_line = int(line_num)
                for i in range(10):  # Look forward up to 10 lines for the closing brace
                    check_line_num = end_line + i
                    line_text = self.app.text.get(f"{check_line_num}.0", f"{check_line_num}.end")
                    if "}" in line_text:
                        search_end = f"{check_line_num}.end"
                        break
                else:
                    search_end = f"{end_line + 5}.end"
                
                # Apply highlight tag
                self.app.text.tag_remove("import_highlight", "1.0", "end")
                self.app.text.tag_add("import_highlight", search_start, search_end)
                self.app.text.tag_configure("import_highlight", background="#90EE90")  # Light green
                
                # Scroll to show the highlighted entry
                self.app.text.see(start_pos)
                
                # Remove highlight after 4 seconds
                self.app.after(4000, lambda: self.app.text.tag_remove("import_highlight", "1.0", "end"))
                
        except Exception as e:
            print(f"Error highlighting new entry: {e}")
