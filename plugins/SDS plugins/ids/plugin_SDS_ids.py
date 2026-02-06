
import uuid
import secrets
import time
import tkinter as tk
import os
import sys
import json

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
