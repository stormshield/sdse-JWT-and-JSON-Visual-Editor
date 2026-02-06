
import os
import sys
import json
import tkinter as tk
from tkinter import messagebox
import re

def get_plugin_resource_path(relative_path):
    """Get absolute path to plugin resource, works for dev and for PyInstaller."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    dev_path = os.path.join(current_dir, relative_path)
    
    if os.path.exists(dev_path):
        return dev_path
    
    try:
        base_path = sys._MEIPASS
        possible_paths = [
            os.path.join(base_path, "plugins", "SDS plugins", "extractor", relative_path),
            os.path.join(base_path, "plugins", "SDS_plugins", "extractor", relative_path),
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
except Exception:
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
        # Support both TreeView and Text Editor
        if event.widget == self.app.tree:
            item_id = self.app.tree.identify_row(event.y)
            if item_id:
                self.app.tree.selection_set(item_id)
                menu.add_command(label=self.t("context_extract_to_file"), command=lambda: self.extract_from_tree(item_id))
        
        elif event.widget == self.app.text:
            # Need to verify if the app has the method to find path
            if hasattr(self.app, "find_json_path_at_cursor"):
                path = self.app.find_json_path_at_cursor()
                if path:
                    menu.add_command(label=self.t("context_extract_to_file"), command=lambda: self.extract_from_path(path))

    def parse_path(self, path_str):
        """
        Parses a dot-notation path into a list of keys and indices.
        Example: "a.b[1].c" -> ["a", "b", 1, "c"]
        """
        keys = []
        parts = path_str.split('.')
        for part in parts:
            m = re.match(r'^(.*)\[(\d+)\]$', part)
            if m:
                if m.group(1):
                    keys.append(m.group(1))
                keys.append(int(m.group(2)))
            else:
                keys.append(part)
        return keys

    def get_value_at_path(self, data, path_keys):
        curr = data
        for key in path_keys:
            if isinstance(curr, dict) and isinstance(key, str):
                if key in curr:
                    curr = curr[key]
                else:
                    return None
            elif isinstance(curr, list) and isinstance(key, int):
                if 0 <= key < len(curr):
                    curr = curr[key]
                else:
                    return None
            else:
                return None
        return curr

    def reconstruct_structure(self, path_keys, value):
        """
        Reconstructs the nested dictionary/list structure leading to value.
        """
        if not path_keys:
            return value
        
        key = path_keys[0]
        remaining = path_keys[1:]
        
        if isinstance(key, int):
            new_list = [None] * (key + 1)
            new_list[key] = self.reconstruct_structure(remaining, value)
            return new_list
        else:
            return {key: self.reconstruct_structure(remaining, value)}

    def deep_merge(self, base, update):
        """
        Recursively merges update into base.
        """
        if isinstance(base, dict) and isinstance(update, dict):
            for k, v in update.items():
                if k in base:
                    base[k] = self.deep_merge(base[k], v)
                else:
                    base[k] = v
            return base
        elif isinstance(base, list) and isinstance(update, list):
            if len(update) > len(base):
                base.extend([None] * (len(update) - len(base)))
            
            for i, v in enumerate(update):
                if v is not None:
                    if i < len(base) and base[i] is not None:
                         base[i] = self.deep_merge(base[i], v)
                    else:
                         base[i] = v
            return base
        else:
            return update

    def extract_from_tree(self, item_id):
        tags = self.app.tree.item(item_id, "tags")
        if not tags:
            return
        path_str = tags[0]
        self.extract_from_path(path_str)

    def extract_from_path(self, path_str):
        try:
            full_json_text = self.app.text.get("1.0", "end-1c")
            full_data = json.loads(full_json_text)
        except Exception as e:
            messagebox.showerror("Error", f"Invalid JSON / Erreur JSON: {e}")
            return

        path_keys = self.parse_path(path_str)
        value = self.get_value_at_path(full_data, path_keys)
        
        if value is None:
            return

        new_data = self.reconstruct_structure(path_keys, value)

        if self.app.current_jwt_path:
            target_dir = os.path.dirname(self.app.current_jwt_path)
        else:
            target_dir = os.path.join(os.path.expanduser("~"), "Desktop")
            
        target_file = os.path.join(target_dir, "extract.json")

        existing_data = {}
        if os.path.exists(target_file):
            try:
                with open(target_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if content.strip():
                        existing_data = json.loads(content)
            except Exception as e:
                print(f"Error reading existing extract.json: {e}") 

        merged_data = self.deep_merge(existing_data, new_data)

        try:
            with open(target_file, 'w', encoding='utf-8') as f:
                json.dump(merged_data, f, indent=4, ensure_ascii=False)
            
            messagebox.showinfo("Success", self.t("msg_extraction_success") + f"\n{target_file}")
        except Exception as e:
            messagebox.showerror("Error", self.t("msg_extraction_error").format(e))
