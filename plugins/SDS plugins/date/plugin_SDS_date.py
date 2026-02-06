
import datetime
import tkinter as tk
import re
import os
import sys
import json

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
            os.path.join(base_path, "plugins", "SDS plugins", "date", relative_path),
            os.path.join(base_path, "plugins", "SDS_plugins", "date", relative_path),
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
        print(f"Plugin SDS Date: languages.json not found at {lang_path}")
except Exception as e:
    print(f"Plugin SDS Date: Could not load languages.json: {e}")
    import traceback
    traceback.print_exc()
    translations = {}

class Plugin:
    def __init__(self, app):
        self.app = app
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
            key_name_at_cursor, _ = self.app.find_json_key_at_cursor()
            if key_name_at_cursor and key_name_at_cursor.lower() == "date":
                if menu.index("end") is not None:
                    menu.add_separator()
                
                cursor_idx = self.app.text.index(f"@{event.x},{event.y}")
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
                    if '\n' not in segment and ',' not in segment and '{' not in segment and '}' not in segment:
                        is_key = False
                        try:
                            after_segment = full_text[q_right+1:q_right+10] 
                            if re.match(r'\s*:', after_segment):
                                is_key = True
                        except Exception:
                            pass
                        
                        if not is_key:
                            start_replace = self.app.text.index(f"1.0 + {q_left+1} chars")
                            end_replace = self.app.text.index(f"1.0 + {q_right} chars")
                            
                            now_val = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')
                            
                            menu.add_command(
                                label=self.t("context_update_date"),
                                command=lambda s=start_replace, e=end_replace, v=now_val: self.app.replace_word(s, e, v)
                            )
        except Exception:
            pass
