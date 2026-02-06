#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
-----------------------------------------------------------------------------
JWT & JSON Visual Editor
Version: 2.0
Author: Jérôme BLONDEL (Professional services)
Last Update: 01/22/2026

Description:
JWT & JSON Visual Editor is a standalone graphical application developed in
Python with Tkinter. It offers a comprehensive environment to visualize, edit,
validate, and manipulate complex JSON structures as well as JWT (JSON Web Token)
payloads.

Key Features:
- Visualization & Editing: Syntax highlighting, auto-indentation, zoom.
- Structural Navigation: Tree View with bidirectional synchronization.
- JWT Support: Automatic detection, payload decoding, public cert extraction.
- Manipulation Tools: Search/Replace, File Merging, Schema Validation, ID/Date tools.
- Security: X.509 certificate visualization and export.
- Ergonomics: Drag & Drop, Bilingual (FR/EN), Undo/Redo.

Dependencies:
- Python 3.8+
- Optional: cryptography, tkinterdnd2
-----------------------------------------------------------------------------
License: GPLv3
-----------------------------------------------------------------------------

Copyright (C) 2026 Jérôme BLONDEL (Professional services)

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import base64
import json
import re
import sys
import os
import glob
import importlib.util
import time
import datetime
import uuid
import secrets
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, font, simpledialog
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

# Regex to identify JSON strings (handling escaped quotes)
RE_JSON_STRING = re.compile(r'"(?:\\.|[^"\\])*"')
# Regex to identify JSON numbers (integers, floats, exponents)
RE_JSON_NUMBER = re.compile(r'\b-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?\b')
# Regex to identify JSON boolean values and null
RE_JSON_BOOL_NULL = re.compile(r'\b(true|false|null)\b', re.IGNORECASE)
# Regex to identify JSON structural characters
RE_JSON_BRACKETS = re.compile(r'[\{\}\[\]\:\,]')

try:
    from tkinterdnd2 import TkinterDnD
    HAS_DND = True
except ImportError:
    HAS_DND = False
    TkinterDnD = None


def b64url_decode(input_str: str) -> bytes:
    """
    Decodes a Base64URL encoded string.
    Adds padding if necessary.
    """
    rem = len(input_str) % 4
    if rem:
        input_str += '=' * (4 - rem)
    return base64.urlsafe_b64decode(input_str)

def extract_payload_from_jwt(jwt_text: str) -> str:
    """
    Extracts the payload part from a JWT string.
    Decodes it from Base64URL to a UTF-8 string.
    """
    parts = jwt_text.strip().split('.')
    if len(parts) < 2:
        raise ValueError("Le fichier ne semble pas contenir un JWT (attendu 2+ segments séparés par '.')")
    payload_b64 = parts[1]
    try:
        payload_bytes = b64url_decode(payload_b64)
    except Exception as e:
        raise ValueError(f"Erreur de décodage Base64URL: {e}")
    try:
        return payload_bytes.decode('utf-8')
    except Exception as e:
        raise ValueError(f"Impossible de décoder le payload en UTF-8: {e}")

class LineNumberCanvas(tk.Canvas):
    """
    Canvas widget to display line numbers corresponding to the text widget.
    """
    def __init__(self, master, text_widget, **kwargs):
        super().__init__(master, **kwargs)
        self.textwidget = text_widget
        self.textwidget.bind("<<Change>>", lambda e: self.redraw())
        self.textwidget.bind("<Configure>", lambda e: self.redraw())
        self.current_line = None
        self.bold_font = font.Font(font=self.textwidget['font'])
        self.bold_font.configure(weight="bold")

    def redraw(self, *args):
        self.delete("all")
        i = self.textwidget.index("@0,0")
        
        while True:
            dline = self.textwidget.dlineinfo(i)
            if dline is None:
                break
            y = dline[1]
            linenum = str(i).split(".")[0]
            
            self.create_text(2, y, anchor="nw", text=linenum, 
                           font=self.textwidget['font'])
            i = self.textwidget.index(f"{i}+1line")

class CustomText(tk.Text):
    """
    Enhanced Text widget with auto-indentation and custom event handling.
    """
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("selectbackground", "#c0c0c0")
        kwargs.setdefault("selectforeground", "black")
        super().__init__(*args, **kwargs)
        self.bind("<<Modified>>", self._on_modified)
        self._reset_modified()

    def _on_modified(self, event=None):
        try:
            self.event_generate("<<Change>>")
        finally:
            self._reset_modified()

    def _reset_modified(self):
        try:
            self.edit_modified(False)
        except Exception:
            pass
    
    def insert_with_auto_indent(self, event=None):
        line_index = self.index("insert linestart")
        line_text = self.get(line_index, f"{line_index} lineend")

        leading_spaces = re.match(r"\s*", line_text).group(0)

        prev_char_index = self.index("insert -1c")
        prev_char = self.get(prev_char_index)
        add_extra_indent = prev_char in "{["

        indent_unit = "  "
        new_indent = leading_spaces + (indent_unit if add_extra_indent else "")

        self.insert("insert", "\n" + new_indent)

        self.event_generate("<<Change>>")
        return "break"

def fusionner_donnees_existantes_avec_modifications(donnees_existantes, donnees_modifications):
    """
    Recursively merges modification data into existing data.
    Handles dictionaries and lists (merging by ID if present).
    """
    if isinstance(donnees_modifications, dict):
        for cle, valeur_modification in donnees_modifications.items():
            if cle in donnees_existantes:
                if isinstance(donnees_existantes[cle], dict) and isinstance(valeur_modification, dict):
                    fusionner_donnees_existantes_avec_modifications(donnees_existantes[cle], valeur_modification)
                elif isinstance(donnees_existantes[cle], list) and isinstance(valeur_modification, list):
                    for nouvel_element in valeur_modification:
                        if isinstance(nouvel_element, dict):
                            id_key = None
                            id_value = None
                            if "id" in nouvel_element:
                                id_key = "id"
                                id_value = nouvel_element["id"]
                            elif "certificateID" in nouvel_element:
                                id_key = "certificateID"
                                id_value = nouvel_element["certificateID"]
                            
                            if id_key and id_value is not None:
                                # Try to match elements by their unique ID for updating
                                element_trouve = False
                                for element_existant in donnees_existantes[cle]:
                                    if isinstance(element_existant, dict) and element_existant.get(id_key) == id_value:
                                        fusionner_donnees_existantes_avec_modifications(element_existant, nouvel_element)
                                        element_trouve = True
                                        break
                                if not element_trouve:
                                    donnees_existantes[cle].append(nouvel_element)
                            else:
                                if nouvel_element not in donnees_existantes[cle]:
                                    donnees_existantes[cle].append(nouvel_element)
                        else:
                            if nouvel_element not in donnees_existantes[cle]:
                                donnees_existantes[cle].append(nouvel_element)
                else:
                    donnees_existantes[cle] = valeur_modification
            else:
                donnees_existantes[cle] = valeur_modification

class PluginManager:
    def __init__(self, app):
        self.app = app
        self.plugins = []

    def load_plugins(self):
        plugin_dir = resource_path("plugins")
        if not os.path.exists(plugin_dir):
            return
            
        plugin_files = glob.glob(os.path.join(plugin_dir, "**", "plugin_*.py"), recursive=True)
        for file_path in plugin_files:
            try:
                # Create a unique and safe module name
                # Avoid spaces and dots that can cause issues with importlib in frozen environments
                rel_path = os.path.relpath(file_path, plugin_dir)
                safe_name = os.path.splitext(rel_path)[0].replace(os.path.sep, "_").replace(" ", "_").replace(".", "_")
                module_name = f"plugin_mod_{safe_name}"
                
                spec = importlib.util.spec_from_file_location(module_name, file_path)
                if spec is None:
                    continue
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                if hasattr(module, "Plugin"):
                    plugin_inst = module.Plugin(self.app)
                    self.plugins.append(plugin_inst)
            except Exception as e:
                # If loading fails in a windowed app, at least we'll have it in stdout/stderr
                # and we could potentially show a messagebox if needed.
                print(f"Error loading plugin {file_path}: {e}")
                import traceback
                traceback.print_exc()

    def register_all(self):
        for p in self.plugins:
            try:
                p.register()
            except Exception as e:
                print(f"Error registering plugin: {e}")
                
    def dispatch_event(self, event_name, data=None):
        for p in self.plugins:
            if hasattr(p, "on_event"):
                try:
                    p.on_event(event_name, data)
                except Exception as e:
                    print(f"Error dispatching event {event_name} to plugin: {e}")

    def extend_context_menu(self, menu, event):
        for p in self.plugins:
            if hasattr(p, "extend_context_menu"):
                try:
                    p.extend_context_menu(menu, event)
                except Exception as e:
                    print(f"Error extending context menu: {e}")

def get_app_dir():
    """
    Returns the directory where the application is located.
    If running as a bundled executable, returns the directory of the executable.
    Otherwise, returns the directory of the script.
    """
    if hasattr(sys, 'frozen'):
        # PyInstaller bundled
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

def resource_path(relative_path):
    """
    Get absolute path to resource, works for dev and for PyInstaller.
    """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))

    return os.path.join(base_path, relative_path)

class JWTEditorApp(TkinterDnD.Tk if HAS_DND else tk.Tk):

    """
    Main Application Class.
    Inherits from TkinterDnD.Tk (if available) or tk.Tk.
    """
    def load_core_translations(self):
        json_path = resource_path("languages.json")
        if os.path.exists(json_path):
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    core_translations = json.load(f)
                    for lang, content in core_translations.items():
                        if lang not in self.translations:
                            self.translations[lang] = content
                        else:
                            self.translations[lang].update(content)
            except Exception as e:
                print(f"Error loading languages.json: {e}")

    def __init__(self, default_lang=None):
        super().__init__()
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.is_modified = False
        
        self.translations = {}
        self.load_core_translations()
        
        self.plugin_manager = PluginManager(self)
        self.plugin_manager.load_plugins()
        self.plugin_manager.register_all()

        
        if default_lang is None:
            default_lang = 'en'

        self.current_language = default_lang

        self.t = lambda key, **kwargs: self.translations.get(self.current_language, {}).get(key, key).format(**kwargs)

        self.title(self.t("title_main"))

        icon_data = """iVBORw0KGgoAAAANSUhEUgAAACAAAAAeCAYAAABNChwpAAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAAAJcEhZcwAADsIAAA7CARUoSoAAAAAZdEVYdFNvZnR3YXJlAFBhaW50Lk5FVCA1LjEuMTGKCBbOAAAAuGVYSWZJSSoACAAAAAUAGgEFAAEAAABKAAAAGwEFAAEAAABSAAAAKAEDAAEAAAADAAAAMQECABEAAABaAAAAaYcEAAEAAABsAAAAAAAAAJ2TAADoAwAAnZMAAOgDAABQYWludC5ORVQgNS4xLjExAAADAACQBwAEAAAAMDIzMAGgAwABAAAAAQAAAAWgBAABAAAAlgAAAAAAAAACAAEAAgAEAAAAUjk4AAIABwAEAAAAMDEwMAAAAADS+8vrCE8zXAAABrpJREFUWEetl1tsXFcVhr91bjNnxh7f7TipY8dpnIvbJKZyAFOa0EbQCAI8hDyUIlAq9QHEAyBUVYJKVaM+cCuqoghxkRAFVKlUqG1AVCRVIG2aiiYlCU0TJ83Fju3Y8WXGMx7PnMvePMx4PB7bIVT5R2fO7HPWXvvfa69/7T3ypT2PWuPJ1DNa631BGDajNXPQgJRat0a57XK/EcGyrGuCHHzr8Ks/ApC+h77wDMgPnIiDbdlzpqXOFB3MOZqnt3CQuXYATKBJIBDAVB4aXXACUKHGNzz8wMcQ+fZbh187IH07dw/bttOaSCRuOdvbiYYPtIuwL+Lwz9kAf0PA7l7Fb/9mcGFtFHeFRfZQhtR4kjAMTh0/cug+IwiCVtu2S7Obv/T8XWvQhfvSn0IfT2uaBTaaJu3KoL1Fsak9pLVWo1ot7DYb0zWwDAuldfXm3gei0rv9YZ1I1OBGowtC6QcBfhBWzPF/QwF3G8KQ0oQmrGmA/lGQmCCuoMcVfpDH973+TCq5Wbbt2KUdx8E0zZKTMFR0rm6lqaEeVZaUcyjPiUpoIATMYiNQYJkghSBimMKVgSEGh0f7c5npzdK7/WFdk6jBdd1iMGFsIsVPnv4+9/d9Eq01Smm0VpVjfQQIlmXy+z++yDee+ml/d110s1F8DkBVPE51VRWh0liWhYgwOHid6fQ0tm3fgavg0zRNVKjQIhQIFKGUwrasIidBa83ps2eJubFyszsDEQQWEgjDkLyXxzAKISmEX5Xadwy69FVGQAoDhmFhrZVWGIbBpo0bSKWmS2Z3BKX56DICGizLJJGoLui+aNW1bh119Q3848wYV29kuDiUJueFJDMeOS/E8xU5LySbD1BKkcvlSi6XRUlYFTkQjUYJgqD8EQCmIXx8QwPxqMXZa2kuDWc4fz3NmSsp3v5ggldOjHDk9E3ynsfE5GRl98UoW9HS6ooIqdQ0ydQ0UkyQOYhA1DFpqo3S2eJS7dps7ayjqcbBMoV7VlfTtbIK38szMXEbBMpgzEVDa000GqGupqa4BAsxOZMinZth69o6GmphNsiwZkUVn+pupLujhvV3VeO6MdZ3ravsuhhl7itkqLGdwo5YTiFUIYcuvM1oepKTgx8wlU0zMDXKUPIm50evcvHmIGeGL+F5Pvm8V9ZzOeiSEhapYHo6jchC2ZmGyfqGNmKOy4mhC4xlpkjmMqTzWfrHr9M/Psh4dhrPy5PLzQJwaSjNC28MsP+lizz3yoe88e9R0lm/OFZR5kCh6hQLj+f5WNb8nlCOnrb1GGLw1S07scTACwOils2q2iYipk2oFenJFIFSvPzmMHteH6EnYbK9JcqlKY/vvjvFF5vHeG7PWmyrlHnzEVBaU1uToL6+DqUqckBprEwW0/OpdVxi6SyJoTEikynckZs4lo1rR2huaebssLDnL0P84aFmjn5zEz/72np+/dhGLjzeRdwSvvWnK5y+nKK7KQJizBOQ4lqHQbio8qlMhtzRY+TePE7uxL8IkknCbBZcl7CsSCUzHk8cGeHA/Y08sqONRNxBRLBMg662BD/e08m4p3jhRj018RiSvVFGQIRUKs34EjISx8bp2YK1thMcGzHNwgFlZqawxxZVc210htPpgF09jZUuAFjVFGPfpmoG4s2o+Ers9/sLBMprwVzbMIR8Ps/JU+8h0ShW213YHe1Ee+/D7lxDpGcL1qqVRLZuLiVVZjYAx6A6tvBsWY7WWgfERNtVGHMyrFS9BrTSRCIRboyOMjk5VWGxNGqrbPAUk+nlpXh1PA86QPIpwso6sADFsBSIOJVvl0R7S5zPNTq89M7o4kQuSvM35zPcOzOMZEcItvQsT0AQfN/nnu5NxOPxytdLosq1eWrnSn74XornD11mZGIWzw/J5gLe7Z/ke3++ylioiKZHkDCLttzlCSitsG2bjo72yle3RF93I0f3rubAuWlWHjjHI788x+cPvk/v7y7z6miaOgNm1/ThdX1Ff+zkcV+27dilE4kEMTdW2gNuTCT5+f4n6fvEtkr/t43xVJ4zl5NcvTmLYxt0tyWYGunn8ZevYKzqxlGBJ0rtNSzLHPD9oHDKFSkpwSo7JX8UNNZEeLCnhX2f7eDRz6ym5+5aHvz0Nn715VbGBv6DEnGUYRyUvp27nwSedWwHwzDQQHpmlq/v3c293RsJw///v8HSKJwxT546xYuvHSZ84Duv+9Ur/i7PPr1fDh175wm0fixRXbXGMAxTpEAimc4WDwzF+iDzkpUK+c7VksW5X4CIkM3lPT8IPlxVX/X8scN//QXAfwHB+PLqaziYwAAAAABJRU5ErkJggg=="""
        try:
            icon_img = tk.PhotoImage(data=icon_data)
            self.iconphoto(True, icon_img)
        except Exception as e:
            print(f"Error loading icon: {e}")

        self.current_font = font.nametofont("TkFixedFont")
        self.current_font.configure(size=11)

        # Menu Bar
        self.menubar = tk.Menu(self, tearoff=0)
        self.config(menu=self.menubar)

        # File Menu
        self.file_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label=self.t("menu_file"), menu=self.file_menu)
        self.file_menu.add_command(label=self.t("toolbar_new"), command=self.new_file)
        self.file_menu.add_command(label=self.t("toolbar_open"), command=self.open_jwt_file)
        self.file_menu.add_command(label=self.t("toolbar_save"), command=self.save_current_file, state="disabled")
        self.file_menu.add_command(label=self.t("toolbar_save_as"), command=self.save_as_json)

        # Tools Menu
        self.tools_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label=self.t("menu_tools"), menu=self.tools_menu)
        self.tools_menu.add_command(label=self.t("toolbar_validate"), command=self.validate_json)
        self.tools_menu.add_command(label=self.t("toolbar_apply_mod"), command=self.apply_external_modifications)
        self.tools_menu.add_command(label=self.t("toolbar_load_schema"), command=self.load_schema_file)
        self.tools_menu.add_command(label=self.t("toolbar_unload_schema"), command=self.unload_schema)
        self.tools_menu.add_separator()
        
        self.tree_var = tk.BooleanVar(value=False)
        self.tools_menu.add_checkbutton(label=self.t("toolbar_toggle_tree"), variable=self.tree_var, command=self.toggle_tree_panel)
        
        self.wrap_var = tk.BooleanVar(value=False)
        self.tools_menu.add_checkbutton(label=self.t("wrap_label"), variable=self.wrap_var, command=self.on_toggle_wrap)

        # Language Menu
        self.lang_var = tk.StringVar(value=self.current_language)
        self.lang_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label=self.t("menu_language"), menu=self.lang_menu)
        
        # Sort languages to have a stable order, e.g., French first then alphabetical or just alphabetical
        # For simplicity, let's sort by key, or try to keep French/English first if preferred.
        # Let's verify keys availability.
        available_langs = sorted(self.translations.keys())
        
        for lang_code in available_langs:
            # Construct label key, e.g. "lang_french", "lang_english", "lang_spanish"...
            # We assume the key mapping is predictable or just use the localized name from the current dict
            # Actually, we need the label key to look up the translated name. 
            # In our dictionary we have keys like "lang_french" inside "fr" dict.
            # But the menu item label should be "Français", "English", "Español" etc. displayed in current language?
            # Usually language menus display the language name in the target language (e.g. "Français", "Deutsch") 
            # OR they display the language name in the CURRENT language. 
            # The existing code did: label=self.t("lang_french") -> which means "Français" (if in FR) or "French" (if in EN).
            # So I should continue this pattern.
            
            # Use a mapping or heuristic if keys are standard. 
            # In plugin_languages.py we have keys: lang_french, lang_english, lang_spanish, lang_german, lang_italian.
            # We can map 'fr' -> 'lang_french', 'en' -> 'lang_english', 'es' -> 'lang_spanish', etc.
            lang_key_map = {
                'fr': 'lang_french',
                'en': 'lang_english',
                'es': 'lang_spanish',
                'de': 'lang_german',
                'it': 'lang_italian'
            }
            label_key = lang_key_map.get(lang_code, f"lang_{lang_code}")
            
            self.lang_menu.add_radiobutton(
                label=self.t(label_key), 
                variable=self.lang_var, 
                value=lang_code, 
                command=lambda l=lang_code: self.set_language(l)
            )

        # Zoom Menu
        self.zoom_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label=self.t("menu_zoom"), menu=self.zoom_menu)
        self.zoom_menu.add_command(label=self.t("zoom_plus"), command=self.zoom_in)
        self.zoom_menu.add_command(label=self.t("zoom_minus"), command=self.zoom_out)

        # Help Menu
        self.help_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label=self.t("menu_help"), menu=self.help_menu)
        self.help_menu.add_command(label=self.t("menu_about"), command=self.show_about_dialog)

        self.main_paned = ttk.PanedWindow(self, orient="horizontal")
        self.main_paned.pack(fill="both", expand=True, padx=6, pady=(0,6))

        self.tree_frame = ttk.LabelFrame(self.main_paned, text=self.t("tree_panel_title"), padding=5)
        
        tree_scroll = ttk.Scrollbar(self.tree_frame, orient="vertical")
        tree_scroll.pack(side="right", fill="y")
        
        self.tree = ttk.Treeview(self.tree_frame, yscrollcommand=tree_scroll.set, selectmode="browse")
        self.tree.pack(side="left", fill="both", expand=True)
        tree_scroll.config(command=self.tree.yview)
        
        self.tree.column("#0", width=240, minwidth=150)
        self.tree.heading("#0", text=self.t("tree_column_key"))
        
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)
        self.tree.bind("<Button-3>", self.show_tree_context_menu)
        
        self.editor_frame = ttk.Frame(self.main_paned)
        
        self.main_paned.add(self.editor_frame, weight=1)
        self.tree_visible = False

        container = ttk.Frame(self.editor_frame)
        container.pack(fill="both", expand=True)

        right_frame = ttk.Frame(container)
        right_frame.pack(side="right", fill="both", expand=True)

        self.vscroll = ttk.Scrollbar(right_frame, orient="vertical")
        self.vscroll.grid(row=0, column=1, sticky="ns")
        self.hscroll = ttk.Scrollbar(right_frame, orient="horizontal")
        self.hscroll.grid(row=1, column=0, sticky="ew")

        self.text = CustomText(right_frame, wrap="none", undo=True, font=self.current_font,
                               xscrollcommand=self.hscroll.set, yscrollcommand=self.vscroll.set)
        self.text.grid(row=0, column=0, sticky="nsew")
        self.text.bind("<Double-Button-1>", self.select_word)
        self.text.bind("<Button-1>", self.clear_highlight_on_click, add="+")
        self.text.bind("<Control-z>", lambda e: self.text.edit_undo())
        self.text.bind("<Control-y>", lambda e: self.text.edit_redo())

        right_frame.rowconfigure(0, weight=1)
        right_frame.columnconfigure(0, weight=1)

        self.hscroll.config(command=self.text.xview)
        self.vscroll.config(command=self.on_vscroll)
        self.text['yscrollcommand'] = self.on_textscroll

        self.linenumbers = LineNumberCanvas(container, self.text, width=50)
        self.linenumbers.pack(side="left", fill="y")

        self.text.bind("<KeyRelease>", lambda e: self.on_text_changed())
        self.text.bind("<ButtonRelease-1>", lambda e: self.on_cursor_moved())
        self.text.bind("<Return>", self.text.insert_with_auto_indent)
        self.text.bind("<BackSpace>", lambda e: self.on_text_changed())

        self.text.bind("<MouseWheel>", self._on_mousewheel)
        self.text.bind("<Shift-MouseWheel>", self._on_horiz_mousewheel)
        self.text.bind("<Control-MouseWheel>", self._on_ctrl_mousewheel)
        self.text.bind("<Button-4>", self._on_mousewheel)
        self.text.bind("<Button-5>", self._on_mousewheel)
        try:
            if sys.platform.startswith("linux"):
                self.text.bind("<Button-6>", self._on_horiz_mousewheel)
                self.text.bind("<Button-7>", self._on_horiz_mousewheel)
        except Exception:
            pass

        self.bind_all("<Control-f>", self.show_find_dialog)
        self.bind_all("<Control-h>", self.show_replace_dialog)
        
        self.bind_all("<Control-s>", lambda e: self.save_current_file())

        self.text.bind("<Button-3>", self.show_context_menu)

        if HAS_DND:
            self.text.drop_target_register('DND_Files')
            self.text.dnd_bind('<<Drop>>', self.on_drop)

        self.setup_tags()

        self.status = tk.StringVar(value=self.t("status_ready"))
        statusbar = ttk.Label(self, textvariable=self.status, relief="sunken", anchor="w")
        statusbar.pack(side="bottom", fill="x")

        self.current_jwt_path = None
        self.raw_jwt_content = None
        self.loaded_schema_data = None
        self._replace_text("")
        self.is_modified = False
        
        self.key_positions = {}

        self._large_file_mode = False
        self._large_file_highlight_chars_threshold = 300_000
        self._large_file_pretty_print_chars_threshold = 800_000
        self._tree_build_batch_size = 300
        self._tree_build_job = None
        self._tree_search_pos = None
        self._last_syntax_start = None
        self._last_syntax_end = None
        self._json_error_state = False
        self._last_edit_time = 0.0
        self._scroll_redraw_after_id = None
        self._last_textscroll_args = None

        self.load_settings()
        self.set_window_size_and_center(1200, 800)

        self.after(100, lambda: self.plugin_manager.dispatch_event("ui_ready"))

    def build_json_tree(self, parent="", data=None, path=""):
        """
        Recursively builds the TreeView from JSON data.
        """
        if data is None:
            return
            
        if isinstance(data, dict):
            for key, value in data.items():
                current_path = f"{path}.{key}" if path else key
                
                key_pattern = [
                    json.dumps(key, ensure_ascii=False),
                    json.dumps(key, ensure_ascii=True),
                ]
                self.find_key_position(key, current_path, key_pattern)
                
                if isinstance(value, (dict, list)):
                    node = self.tree.insert(parent, "end", text=key, tags=(current_path,))
                    self.build_json_tree(node, value, current_path)
                else:
                    self.tree.insert(parent, "end", text=key, tags=(current_path,))
                    
        elif isinstance(data, list):
            for idx, item in enumerate(data):
                current_path = f"{path}[{idx}]"
                
                if isinstance(item, (dict, list)):
                    node = self.tree.insert(parent, "end", text=f"[{idx}]", tags=(current_path,))
                    self.build_json_tree(node, item, current_path)
                else:
                    self.tree.insert(parent, "end", text=f"[{idx}]", tags=(current_path,))

    def find_key_position(self, key, path, pattern):
        """
        Locates the position of a specific key in the text widget to map TreeView items to text positions.
        """
        start_pos = self._tree_search_pos or "1.0"
        patterns = pattern if isinstance(pattern, (list, tuple)) else [pattern]
        pos = None

        for p in patterns:
            pos = self.text.search(p, start_pos, stopindex="end", regexp=False)
            if not pos:
                pos = self.text.search(p, "1.0", stopindex="end", regexp=False)
            if pos:
                break

        if pos:
            self.key_positions[path] = pos
            try:
                self._tree_search_pos = f"{pos}+1c"
            except Exception:
                self._tree_search_pos = None

    def find_json_path_at_cursor(self):
        """
        Determines the JSON path based on the current cursor position in the text editor.
        """
        if not self.key_positions:
            return None
        
        cursor_pos = self.text.index("insert")

        try:
            cursor_offset = int(self.text.count("1.0", cursor_pos, "chars")[0])
        except Exception:
            line, col = map(int, cursor_pos.split('.'))
            cursor_offset = sum(len(self.text.get(f"{i}.0", f"{i}.end")) + 1 for i in range(1, line)) + col
        
        best_path = None
        best_distance = float('inf')
        
        for path, pos in self.key_positions.items():
            try:
                pos_offset = int(self.text.count("1.0", pos, "chars")[0])
            except Exception:
                p_line, p_col = map(int, pos.split('.'))
                pos_offset = sum(len(self.text.get(f"{i}.0", f"{i}.end")) + 1 for i in range(1, p_line)) + p_col
            
            if pos_offset <= cursor_offset:
                distance = cursor_offset - pos_offset
                if distance < best_distance:
                    best_distance = distance
                    best_path = path
        
        return best_path

    def sync_tree_with_cursor(self):
        if not self.tree_var.get():
            return
        
        path = self.find_json_path_at_cursor()
        if not path:
            return
        
        def find_item_by_path(item=""):
            children = self.tree.get_children(item)
            for child in children:
                tags = self.tree.item(child, "tags")
                if tags and tags[0] == path:
                    return child
                result = find_item_by_path(child)
                if result:
                    return result
            return None
        
        tree_item = find_item_by_path()
        if tree_item:
            parent = self.tree.parent(tree_item)
            while parent:
                self.tree.item(parent, open=True)
                parent = self.tree.parent(parent)
            
            self.tree.selection_set(tree_item)
            self.tree.see(tree_item)

    def update_json_tree(self):
        """
        Parses the current text content as JSON and updates the TreeView.
        Handles large files incrementally if necessary.
        """
        if not self.tree_var.get():
            return

        try:
            if self._tree_build_job is not None:
                self.after_cancel(self._tree_build_job)
        except Exception:
            pass
        self._tree_build_job = None

        for item in self.tree.get_children():
            self.tree.delete(item)
        
        self.key_positions.clear()
        self._tree_search_pos = "1.0"
        
        txt = self.text.get("1.0", "end-1c")
        if not txt.strip():
            return
            
        try:
            data = json.loads(txt)
            if self._large_file_mode:
                self._start_incremental_tree_build(data)
            else:
                self.build_json_tree("", data, "")
        except json.JSONDecodeError:
            pass

    def _start_incremental_tree_build(self, data):
        """
        Builds the tree incrementally using a stack to keep the UI responsive.
        """
        stack = [("", data, "")]

        def step():
            nonlocal stack
            processed = 0
            try:
                while stack and processed < self._tree_build_batch_size:
                    parent, node, path = stack.pop()
                    if isinstance(node, dict):
                        items = list(node.items())
                        for key, value in reversed(items):
                            current_path = f"{path}.{key}" if path else key
                            key_pattern = f'"{key}"'
                            self.find_key_position(key, current_path, key_pattern)

                            if isinstance(value, (dict, list)):
                                tree_id = self.tree.insert(parent, "end", text=key, tags=(current_path,))
                                stack.append((tree_id, value, current_path))
                            else:
                                self.tree.insert(parent, "end", text=key, tags=(current_path,))
                            processed += 1
                            if processed >= self._tree_build_batch_size:
                                break
                    elif isinstance(node, list):
                        for idx in range(len(node) - 1, -1, -1):
                            item = node[idx]
                            current_path = f"{path}[{idx}]"
                            if isinstance(item, (dict, list)):
                                tree_id = self.tree.insert(parent, "end", text=f"[{idx}]", tags=(current_path,))
                                stack.append((tree_id, item, current_path))
                            else:
                                self.tree.insert(parent, "end", text=f"[{idx}]", tags=(current_path,))
                            processed += 1
                            if processed >= self._tree_build_batch_size:
                                break
            except Exception:
                stack = []

            if stack:
                self._tree_build_job = self.after(1, step)
            else:
                self._tree_build_job = None

        self._tree_build_job = self.after(1, step)

    def on_tree_select(self, event):
        """
        Handles selection events in the TreeView.
        Highlights the corresponding JSON key in the text editor.
        """
        selection = self.tree.selection()
        if not selection:
            return
            
        item = selection[0]
        tags = self.tree.item(item, "tags")
        
        if tags:
            path = tags[0]
            if path in self.key_positions:
                pos = self.key_positions[path]
                
                self.text.tag_remove("tree_highlight", "1.0", "end")
                end_pos = f"{pos}+{len(self.tree.item(item, 'text'))+2}c"
                self.text.tag_add("tree_highlight", pos, end_pos)
                self.text.tag_configure("tree_highlight", background="#FFD700")
                
                self.text.mark_set("insert", pos)
                self.text.see(pos)
                
                self.linenumbers.redraw()
                
                self.after(2000, lambda: self.text.tag_remove("tree_highlight", "1.0", "end"))

    def select_word(self, event):
        """
        Highlights all occurrences of the word under the cursor on double-click.
        """
        text = event.widget
        index = text.index(f"@{event.x},{event.y}")
        if getattr(self, "_large_file_mode", False):
            start_idx, end_idx = self._get_highlight_range()
            content = text.get(start_idx, end_idx)
            try:
                offset = int(text.count(start_idx, index, "chars")[0])
            except Exception:
                line, col = map(int, index.split('.'))
                offset = sum(len(text.get(f"{i}.0", f"{i}.end")) + 1 for i in range(1, line)) + col
                start_idx = "1.0"
        else:
            content = text.get("1.0", "end-1c")
            start_idx = "1.0"
            line, col = map(int, index.split('.'))
            offset = sum(len(text.get(f"{i}.0", f"{i}.end")) + 1 for i in range(1, line)) + col

        pattern = re.compile(
            r'"(\\.|[^"\\])*"'
            r'|\b(true|false|null)\b'
            r'|\b-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?\b',
            re.IGNORECASE
        )

        word_to_highlight = None
        sel_start_idx = sel_end_idx = None

        for m in pattern.finditer(content):
            if m.start() <= offset < m.end():
                start = m.start()
                end = m.end()
                if content[start] == '"' and content[end-1] == '"':
                    start += 1
                    end -= 1
                word_to_highlight = content[start:end]
                sel_start_idx = f"{start_idx}+{start}c"
                sel_end_idx = f"{start_idx}+{end}c"
                break

        if not word_to_highlight:
            return "break"

        text.tag_remove("all_occurrences", "1.0", "end")
        text.tag_remove("selected_word", "1.0", "end")
        text.tag_remove(tk.SEL, "1.0", "end")

        if getattr(self, "_large_file_mode", False):
            search_start, search_end = self._get_highlight_range()
        else:
            search_start, search_end = "1.0", "end"

        start_pos = search_start
        while True:
            start_pos = text.search(word_to_highlight, start_pos, stopindex=search_end, nocase=True)
            if not start_pos:
                break
            end_pos = f"{start_pos}+{len(word_to_highlight)}c"
            if start_pos != sel_start_idx:
                text.tag_add("all_occurrences", start_pos, end_pos)
            start_pos = end_pos

        text.tag_configure("all_occurrences", background="yellow")

        text.tag_add(tk.SEL, sel_start_idx, sel_end_idx)
        text.mark_set(tk.INSERT, sel_end_idx)
        text.see(sel_start_idx)

        text.tag_add("selected_word", sel_start_idx, sel_end_idx)
        text.tag_configure("selected_word", background="orange")

        return "break"

    def clear_highlight_on_click(self, event):
        text = event.widget
        index = text.index(f"@{event.x},{event.y}")
        tags = text.tag_names(index)
        if "selected_word" not in tags and "all_occurrences" not in tags:
            text.tag_remove("all_occurrences", "1.0", "end")
            text.tag_remove("selected_word", "1.0", "end")
            text.tag_remove(tk.SEL, "1.0", "end")

    def set_window_size_and_center(self, width=1200, height=800):
        self.update_idletasks()
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)

        self.geometry(f"{width}x{height}+{x}+{y}")

    def set_language(self, lang: str):
        if lang not in self.translations:
            return
        self.current_language = lang
        if hasattr(self, 'lang_var') and self.lang_var.get() != lang:
            self.lang_var.set(lang)
        try:
            self.update_window_title()
        except Exception:
            pass
        try:
            # Update Menu Labels
            self.menubar.entryconfig(0, label=self.t("menu_file"))
            self.menubar.entryconfig(1, label=self.t("menu_tools"))
            self.menubar.entryconfig(2, label=self.t("menu_language"))
            self.menubar.entryconfig(3, label=self.t("menu_zoom"))

            # File Menu
            self.file_menu.entryconfig(0, label=self.t("toolbar_new"))
            self.file_menu.entryconfig(1, label=self.t("toolbar_open"))
            self.file_menu.entryconfig(2, label=self.t("toolbar_save"))
            self.file_menu.entryconfig(3, label=self.t("toolbar_save_as"))

            # Tools Menu
            self.tools_menu.entryconfig(0, label=self.t("toolbar_validate"))
            self.tools_menu.entryconfig(1, label=self.t("toolbar_apply_mod"))
            self.tools_menu.entryconfig(2, label=self.t("toolbar_load_schema"))
            self.tools_menu.entryconfig(3, label=self.t("toolbar_unload_schema"))
            self.tools_menu.entryconfig(5, label=self.t("toolbar_toggle_tree"))
            self.tools_menu.entryconfig(6, label=self.t("wrap_label"))
            
            # Language Menu
            available_langs = sorted(self.translations.keys())
            lang_key_map = {
                'fr': 'lang_french',
                'en': 'lang_english',
                'es': 'lang_spanish',
                'de': 'lang_german',
                'it': 'lang_italian'
            }
            for i, code in enumerate(available_langs):
                 label_key = lang_key_map.get(code, f"lang_{code}")
                 try:
                     self.lang_menu.entryconfig(i, label=self.t(label_key))
                 except Exception:
                     pass

            # Zoom Menu
            self.zoom_menu.entryconfig(0, label=self.t("zoom_plus"))
            self.zoom_menu.entryconfig(1, label=self.t("zoom_minus"))

            # Help Menu
            self.menubar.entryconfig(4, label=self.t("menu_help"))
            self.help_menu.entryconfig(0, label=self.t("menu_about"))
        except Exception:
            pass
        
        try:
            for child in self.winfo_children():
                if isinstance(child, ttk.PanedWindow):
                    for pane_child in child.winfo_children():
                        if isinstance(pane_child, ttk.LabelFrame):
                            pane_child.config(text=self.t("tree_panel_title"))
                            break
            self.tree.heading("#0", text=self.t("tree_column_key"))
        except Exception:
            pass

        try:
            self.status.set(self.t("status_ready"))
        except Exception:
            pass

        try:
            if hasattr(self, 'find_win') and getattr(self, 'find_win') and self.find_win.winfo_exists():
                self.find_win.title(self.t("find_title"))
                for child in self.find_win.winfo_children():
                    if isinstance(child, tk.Label):
                        child.config(text=self.t("find_label"))
                    if isinstance(child, ttk.Frame):
                        btns = [w for w in child.winfo_children() if isinstance(w, ttk.Button)]
                        if len(btns) >= 2:
                            btns[0].config(text=self.t("prev_button"))
                            btns[1].config(text=self.t("next_button"))
        except Exception:
            pass

        try:
            if hasattr(self, 'rep_win') and getattr(self, 'rep_win') and self.rep_win.winfo_exists():
                self.rep_win.title(self.t("replace_title"))
                for child in self.rep_win.winfo_children():
                    if isinstance(child, tk.Label):
                        txt = child.cget('text')
                        child.config(text=self.t("replace_find_label") if 'Rechercher' in txt or 'Find' in txt else self.t("replace_replace_label"))
                    if isinstance(child, ttk.Frame):
                        btns = [w for w in child.winfo_children() if isinstance(w, ttk.Button)]
                        if len(btns) >= 3:
                            btns[0].config(text=self.t("replace_next"))
                            btns[1].config(text=self.t("replace_replace"))
                            btns[2].config(text=self.t("replace_all"))
        except Exception:
            pass
        self.save_settings()
        self.plugin_manager.dispatch_event("language_changed", lang)

    def toggle_language(self):
        new = 'en' if self.current_language == 'fr' else 'fr'
        self.set_language(new)

    def toggle_tree_panel(self):
        if not self.tree_var.get():
            self.main_paned.remove(self.tree_frame)
            self.tree_visible = False
        else:
            self.main_paned.insert(0, self.tree_frame)
            self.main_paned.sashpos(0, 320)
            self.tree_visible = True
            self.update_json_tree()


    def zoom_in(self, event=None):
        size = self.current_font.cget("size")
        self.current_font.configure(size=size + 1)
        self.bold_font.configure(size=size + 1)
        self.linenumbers.redraw()
        self.apply_syntax_highlight()
        self.save_settings()

    def zoom_out(self, event=None):
        size = self.current_font.cget("size")
        if size > 6:
            self.current_font.configure(size=size - 1)
            self.bold_font.configure(size=size - 1)
            self.linenumbers.redraw()
            self.apply_syntax_highlight()
            self.save_settings()

    def _on_ctrl_mousewheel(self, event):
        delta = getattr(event, "delta", None)
        if delta is None:
            if getattr(event, "num", None) == 4:
                self.zoom_in(); return "break"
            elif getattr(event, "num", None) == 5:
                self.zoom_out(); return "break"
            return
        if delta > 0:
            self.zoom_in()
        else:
            self.zoom_out()
        return "break"

    def on_vscroll(self, *args):
        self.text.yview(*args)
        self._schedule_linenumbers_redraw(30)
        self._schedule_syntax_highlight(120)

    def on_textscroll(self, *args):
        try:
            self.vscroll.set(*args)
        except Exception:
            pass
        if args != self._last_textscroll_args:
            self._last_textscroll_args = args
            self._schedule_linenumbers_redraw(30)
            if (time.monotonic() - getattr(self, "_last_edit_time", 0.0)) > 0.25:
                self._schedule_syntax_highlight(150)

    def _on_mousewheel(self, event):
        state = getattr(event, "state", 0) or 0
        shift_mask = 0x0001
        control_mask = 0x0004
        if state & control_mask:
            return self._on_ctrl_mousewheel(event)
        if state & shift_mask:
            return self._on_horiz_mousewheel(event)

        if hasattr(event, "delta"):
            units = int(-1 * (event.delta / 120)) * 3
            if units == 0:
                units = -1 if event.delta > 0 else 3
            self.text.yview_scroll(units, "units")
        else:
            if getattr(event, "num", None) == 4:
                self.text.yview_scroll(-3, "units")
            elif getattr(event, "num", None) == 5:
                self.text.yview_scroll(3, "units")
        self._schedule_linenumbers_redraw(30)
        self._schedule_syntax_highlight(120)
        return "break"

    def _on_horiz_mousewheel(self, event):
        if hasattr(event, "delta"):
            units = int(-1 * (event.delta / 120))
            self.text.xview_scroll(units, "units")
        else:
            if getattr(event, "num", None) in (6,):
                self.text.xview_scroll(-1, "units")
            elif getattr(event, "num", None) in (7,):
                self.text.xview_scroll(1, "units")
        self.linenumbers.redraw()
        return "break"

    def on_text_changed(self):
        self.is_modified = True
        self._last_edit_time = time.monotonic()
        if hasattr(self, "_redraw_after_id"):
            self.after_cancel(self._redraw_after_id)
        self._redraw_after_id = self.after(50, self.linenumbers.redraw)

        delay = 800 if self._large_file_mode else 400
        self._schedule_syntax_highlight(delay)

    def _schedule_linenumbers_redraw(self, delay_ms: int = 30):
        if self._scroll_redraw_after_id is not None:
            try:
                self.after_cancel(self._scroll_redraw_after_id)
            except Exception:
                pass
        self._scroll_redraw_after_id = self.after(delay_ms, self.linenumbers.redraw)

    def _schedule_syntax_highlight(self, delay_ms: int = 150):
        if hasattr(self, "_highlight_after_id"):
            try:
                self.after_cancel(self._highlight_after_id)
            except Exception:
                pass
        self._highlight_after_id = self.after(delay_ms, self.apply_syntax_highlight)

    def on_cursor_moved(self, sync_tree=False):
        if hasattr(self, "_cursor_after_id"):
            self.after_cancel(self._cursor_after_id)
        self._cursor_after_id = self.after(100, self.linenumbers.redraw)
        
        if sync_tree:
            self.after(50, self.sync_tree_with_cursor)

    def on_toggle_wrap(self):
        if self.wrap_var.get():
            self.text.config(wrap="word")
            self.hscroll.grid_remove()
            self.status.set(self.t("status_wrap_on"))
        else:
            self.text.config(wrap="none")
            self.hscroll.grid()
            self.status.set(self.t("status_wrap_off"))
        self.linenumbers.redraw()

    def _replace_text(self, content: str):
        try:
            self.text.config(undo=False)
        except Exception:
            pass
        self.text.delete("1.0", "end")
        self.text.insert("1.0", content)
        try:
            self.text.edit_reset()
        except Exception:
            pass
        try:
            self.text.config(undo=True)
        except Exception:
            pass

        threshold = getattr(self, "_large_file_highlight_chars_threshold", 300_000)
        self._large_file_mode = len(content) >= threshold
        self._last_syntax_start = None
        self._last_syntax_end = None
        self.on_text_changed()

    def _get_highlight_range(self):
        try:
            start_idx = self.text.index("@0,0")
            end_idx = self.text.index(f"@0,{self.text.winfo_height()}")
            start_idx = self.text.index(f"{start_idx} linestart")
            end_idx = self.text.index(f"{end_idx} lineend")
            return start_idx, end_idx
        except Exception:
            return "1.0", "end"

    def setup_tags(self):
        """
        Configures Tkinter text tags for syntax highlighting (colors, fonts).
        """
        self.bold_font = font.Font(self.text, self.current_font)
        self.bold_font.configure(weight="bold")

        self.text.tag_configure("key", foreground="#ad00ff", selectforeground=None)
        self.text.tag_configure("string", foreground="#800000", selectforeground=None)
        self.text.tag_configure("number", foreground="#ff8000", selectforeground=None)
        self.text.tag_configure("bool", foreground="#18af8a", selectforeground=None)
        self.text.tag_configure("keyword", foreground="#800000", selectforeground=None)
        self.text.tag_configure("bracket", foreground="#000000", selectforeground=None)
        self.text.tag_configure("error", background="#fa0f00", selectforeground=None)

        self.text.tag_configure("highlight", background="yellow")
        self.text.tag_configure("current", background="orange")

    def apply_syntax_highlight(self):
        """
        Applies syntax highlighting to the text (or visible range).
        Uses Regex to identify keys, strings, numbers, booleans, etc.
        """
        start_idx, end_idx = self._get_highlight_range()

        remove_start = self._last_syntax_start or start_idx
        remove_end = self._last_syntax_end or end_idx

        content = self.text.get(start_idx, end_idx)
        for tag in ("key", "string", "number", "bool", "keyword", "bracket"):
            self.text.tag_remove(tag, remove_start, remove_end)
        if not content:
            if not getattr(self, "_json_error_state", False):
                self.text.config(bg="white")
            return

        protected = []

        for m in RE_JSON_STRING.finditer(content):
            j = m.end()
            # Check if the string is followed by a colon (making it a JSON key)
            while j < len(content) and content[j].isspace():
                j += 1
            tag = "key" if j < len(content) and content[j] == ":" else "string"
            start = f"{start_idx}+{m.start()}c"
            end = f"{start_idx}+{m.end()}c"
            self.text.tag_add(tag, start, end)
            # Mark string regions as protected to prevent other regexes (like keywords) from matching inside
            protected.append((m.start(), m.end()))

        if protected:
            protected.sort(key=lambda t: t[0])
            merged = [protected[0]]
            for s, e in protected[1:]:
                last_s, last_e = merged[-1]
                if s <= last_e:
                    merged[-1] = (last_s, max(last_e, e))
                else:
                    merged.append((s, e))
            protected = merged

        def is_protected(pos: int) -> bool:
            if not protected:
                return False
            i = getattr(is_protected, "_i", 0)
            while i < len(protected) and protected[i][1] <= pos:
                i += 1
            setattr(is_protected, "_i", i)
            if i < len(protected):
                s, e = protected[i]
                return s <= pos < e
            return False

        setattr(is_protected, "_i", 0)
        for m in RE_JSON_NUMBER.finditer(content):
            if is_protected(m.start()):
                continue
            start = f"{start_idx}+{m.start()}c"
            end = f"{start_idx}+{m.end()}c"
            self.text.tag_add("number", start, end)

        setattr(is_protected, "_i", 0)
        for m in RE_JSON_BOOL_NULL.finditer(content):
            if is_protected(m.start()):
                continue
            start = f"{start_idx}+{m.start()}c"
            end = f"{start_idx}+{m.end()}c"
            self.text.tag_add("bool", start, end)

        for m in RE_JSON_BRACKETS.finditer(content):
            start = f"{start_idx}+{m.start()}c"
            end = f"{start_idx}+{m.end()}c"
            self.text.tag_add("bracket", start, end)

        if not getattr(self, "_json_error_state", False):
            self.text.config(bg="white")
        self._last_syntax_start = start_idx
        self._last_syntax_end = end_idx

    def show_context_menu(self, event):
        """
        Displays a context menu on right-click.
        Includes options for boolean toggling, certificate info, schema values, and clipboard operations.
        """
        self.text.mark_set("insert", f"@{event.x},{event.y}")
        self.text.focus_set()

        menu = tk.Menu(self, tearoff=0)

        index = self.text.index(f"@{event.x},{event.y}")

        try:
            token = self.text.get(f"{index} wordstart", f"{index} wordend").strip().lower()
        except Exception:
            token = ""

        self.plugin_manager.extend_context_menu(menu, event)

        if self.loaded_schema_data and token not in ("true", "false"):
            key_name, json_path = self.find_json_key_at_cursor()
            
            if json_path:
                enum_values = self.get_schema_enum_for_path(json_path)
                
                if enum_values and len(enum_values) > 0:
                    schema_menu = tk.Menu(menu, tearoff=0)
                    
                    key_pattern = rf'"{re.escape(key_name)}"\s*:\s*'
                    count_var = tk.IntVar(value=0)
                    match_start = None
                    try:
                        match_start = self.text.search(key_pattern, index, stopindex="1.0", backwards=True, regexp=True, count=count_var)
                    except Exception:
                        match_start = None

                    if match_start and int(count_var.get()) > 0:
                        value_start_idx = self.text.index(f"{match_start}+{int(count_var.get())}c")
                        snippet = self.text.get(value_start_idx, f"{value_start_idx}+400c")
                        value_pattern = r'^\s*("(?:[^"\\]|\\.)*"|true|false|null|-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)'
                        value_match = re.match(value_pattern, snippet, re.IGNORECASE)
                        
                        if value_match:
                            start_off, end_off = value_match.span(1)
                            start_idx = self.text.index(f"{value_start_idx}+{start_off}c")
                            end_idx = self.text.index(f"{value_start_idx}+{end_off}c")
                            
                            for enum_val in enum_values:
                                if isinstance(enum_val, str):
                                    formatted_val = f'"{enum_val}"'
                                elif isinstance(enum_val, bool):
                                    formatted_val = "true" if enum_val else "false"
                                elif enum_val is None:
                                    formatted_val = "null"
                                else:
                                    formatted_val = str(enum_val)
                                
                                display_text = str(enum_val)
                                schema_menu.add_command(
                                    label=display_text,
                                    command=lambda s=start_idx, e=end_idx, v=formatted_val: self.replace_word(s, e, v)
                                )
                            
                            menu.add_cascade(label=self.t("context_schema_values"), menu=schema_menu)

        if menu.index("end") is not None:
            menu.add_separator()

        menu.add_command(label=self.t("context_copy"), command=lambda: self.text.event_generate("<<Copy>>"))
        menu.add_command(label=self.t("context_cut"), command=lambda: self.text.event_generate("<<Cut>>"))
        menu.add_command(label=self.t("context_paste"), command=lambda: self.text.event_generate("<<Paste>>"))

        if menu.index("end") is not None:
            try:
                menu.tk_popup(event.x_root, event.y_root)
            finally:
                menu.grab_release()

    def show_tree_context_menu(self, event):
        """
        Displays a context menu on right-click for the TreeView.
        """
        item = self.tree.identify_row(event.y)
        if not item:
            return
            
        # Select the item locally for visual feedback
        self.tree.selection_set(item)
        
        menu = tk.Menu(self, tearoff=0)
        self.plugin_manager.extend_context_menu(menu, event)
        
        if menu.index("end") is not None:
            try:
                menu.tk_popup(event.x_root, event.y_root)
            finally:
                menu.grab_release()

    def replace_word(self, start, end, new_value):
        try:
            yview = self.text.yview()
        except Exception:
            yview = None
        self.text.delete(start, end)
        self.text.insert(start, new_value)
        self.apply_syntax_highlight()
        self.is_modified = True
        if yview is not None:
            try:
                self.text.yview_moveto(yview[0])
            except Exception:
                pass

    def new_file(self):
        """
        Create a new empty document. Prompts to save if current document is modified.
        """
        if self.is_modified:
            resp = self.custom_ask_yes_no_cancel(
                self.t("confirm_unsaved_title"),
                self.t("confirm_unsaved_text")
            )
            if resp is None:
                return
            elif resp:
                if self.current_jwt_path and self.current_jwt_path.lower().endswith('.json'):
                    self.save_current_file()
                else:
                    self.save_as_json()

        self.current_jwt_path = None
        self.raw_jwt_content = None
        self._replace_text("")
        self.is_modified = False
        self.update_window_title()
        try:
            # Disable Save until a file is opened or saved
            self.file_menu.entryconfig(2, state="disabled")
        except Exception:
            pass
        self.plugin_manager.dispatch_event("file_closed")
        self.status.set(self.t("status_ready"))

    def open_jwt_file(self):
        """
        Opens a file dialog to load a JWT or JSON file.
        Decodes JWT payloads or loads JSON content.
        """
        path = filedialog.askopenfilename(
            title=self.t("filedialog_open_title"),
            filetypes=[("SDS policy files", "*.jwt *.json")]
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                text = f.read().strip()

            if path.lower().endswith(".jwt"):
                payload_str = extract_payload_from_jwt(text)
                content = payload_str
                self.raw_jwt_content = text
                self.status.set(self.t("msg_loaded_payload_from", path=path))
                self.plugin_manager.dispatch_event("jwt_loaded")
            elif path.lower().endswith(".json"):
                try:
                    parsed = json.loads(text)
                    content = text
                    self.raw_jwt_content = None
                    self.status.set(self.t("msg_loaded_json_from", path=path))
                    self.plugin_manager.dispatch_event("file_closed")
                except Exception as e:
                    messagebox.showerror(self.t("msg_error_title"), self.t("msg_error_loading_json", err=e))
                    self.status.set(self.t("status_error_loading_json"))
                    return
            else:
                self.raw_jwt_content = None
                self.plugin_manager.dispatch_event("file_closed")
                messagebox.showwarning(self.t("msg_unknown_format_title"), self.t("msg_unknown_format_text"))
                return

            self.current_jwt_path = path
            self.update_window_title()
            try:
                # Update File menu: Enable/Disable 'Save'
                state = "normal" if path.lower().endswith('.json') else "disabled"
                self.file_menu.entryconfig(2, state=state)
            except Exception as e:
                print(f"Error updating menu state: {e}")

            if path.lower().endswith('.json') and len(content) >= self._large_file_pretty_print_chars_threshold:
                self._replace_text(content)
            else:
                try:
                    parsed = json.loads(content)
                    pretty = json.dumps(parsed, indent=2, ensure_ascii=False)
                    self._replace_text(pretty)
                except Exception:
                    self._replace_text(content)
            self.is_modified = False

            self.update_json_tree()

        except Exception as e:
            messagebox.showerror(self.t("msg_error_title"), self.t("msg_cannot_open_mods", err=e))
            self.status.set(self.t("status_error_opening"))

    def validate_json(self):
        """
        Validates the JSON content in the editor.
        Re-indents and pretty-prints if valid; highlights errors if invalid.
        """
        txt = self.text.get("1.0", "end-1c")

        if hasattr(self, "_highlight_after_id"):
            try:
                self.after_cancel(self._highlight_after_id)
            except Exception:
                pass
            self._highlight_after_id = None

        cursor_index = self.text.index("insert")
        yview = self.text.yview()

        try:
            parsed = json.loads(txt)
            pretty = json.dumps(parsed, indent=2, ensure_ascii=False)

            self._json_error_state = False

            self._replace_text(pretty)

            self.text.mark_set("insert", cursor_index)
            self.text.yview_moveto(yview[0])

            self.status.set(self.t("msg_json_valid_reindented"))
            
            self.text.config(bg="white")
            self.text.tag_remove("error", "1.0", "end")
            
            self.update_json_tree()

        except json.JSONDecodeError as e:
            self._json_error_state = True
            self.text.config(bg="#FFEEEE")
            line = e.lineno
            col = e.colno
            start = f"{line}.{col-1}"
            end = f"{line}.{col}"
            try:
                self.text.tag_remove("error", "1.0", "end")
                self.text.tag_add("error", start, end)
                self.text.mark_set("insert", start)
                self.text.see(start)
            except Exception:
                pass
            messagebox.showerror(self.t("msg_json_invalid_title"), self.t("msg_json_current_invalid", err=e))
            self.status.set(self.t("msg_json_invalid_title"))
        except Exception as e:
            self._json_error_state = True
            self.text.config(bg="#FFEEEE")
            messagebox.showerror(self.t("msg_json_invalid_title"), self.t("msg_json_current_invalid", err=e))
            self.status.set(self.t("msg_json_invalid_title"))

    def save_current_file(self):
        """
        Saves the current content to the file.
        Only allows saving if it's a JSON file (not raw JWT).
        """
        if not self.current_jwt_path or not self.current_jwt_path.lower().endswith('.json'):
            return self.save_as_json()

        txt = self.text.get("1.0", "end-1c")
        if not txt.strip():
            messagebox.showwarning(self.t("msg_empty_title"), self.t("msg_empty_nothing_to_save"))
            return
        try:
            parsed = json.loads(txt)
        except Exception as e:
            resp = self.custom_ask_yes_no(self.t("msg_json_invalid_title"), self.t("msg_json_invalid_save_question", err=e))
            if not resp:
                return
            to_write = txt
        else:
            to_write = json.dumps(parsed, indent=2, ensure_ascii=False) + "\n"
        path = self.current_jwt_path
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(to_write)
            messagebox.showinfo(self.t("msg_info_title"), self.t("msg_saved", path=path))
            self.status.set(self.t("msg_saved_status", path=path))
            self.is_modified = False
        except Exception as e:
            messagebox.showerror(self.t("msg_error_title"), self.t("msg_cannot_save", err=e))
            self.status.set(self.t("status_error_save"))

    def save_as_json(self):
        txt = self.text.get("1.0", "end-1c")
        if not txt.strip():
            messagebox.showwarning(self.t("msg_empty_title"), self.t("msg_empty_nothing_to_save"))
            return
        try:
            parsed = json.loads(txt)
        except Exception as e:
            resp = self.custom_ask_yes_no(self.t("msg_json_invalid_title"), self.t("msg_json_invalid_save_question", err=e))
            if not resp:
                return
            to_write = txt
        else:
            to_write = json.dumps(parsed, indent=2, ensure_ascii=False) + "\n"
        path = filedialog.asksaveasfilename(defaultextension=".json",
                                            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
                                            title=self.t("filedialog_save_title"))
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(to_write)
            messagebox.showinfo(self.t("msg_info_title"), self.t("msg_saved", path=path))
            self.status.set(self.t("msg_saved_status", path=path))
            self.is_modified = False
            self.current_jwt_path = path
            self.update_window_title()
            try:
                self.file_menu.entryconfig(2, state="normal")
            except Exception:
                pass
        except Exception as e:
            messagebox.showerror(self.t("msg_error_title"), self.t("msg_cannot_save", err=e))
            self.status.set(self.t("status_error_save"))

    def show_find_dialog(self, event=None):
        """
        Opens the Find dialog window.
        """
        if hasattr(self, 'find_win') and self.find_win.winfo_exists():
            self.find_win.lift()
            try:
                self.find_entry.focus_set()
            except Exception:
                pass
            return

        self.find_win = tk.Toplevel(self)
        self.find_win.title(self.t("find_title"))
        self.find_win.transient(self)
        self.find_win.resizable(False, False)

        self.find_win.update_idletasks()
        width = 320
        height = 105
        x = self.winfo_x() + (self.winfo_width() // 2) - (width // 2)
        y = self.winfo_y() + (self.winfo_height() // 2) - (height // 2)
        self.find_win.geometry(f"{width}x{height}+{x}+{y}")

        main_frame = ttk.Frame(self.find_win, padding="10 10 10 10")
        main_frame.pack(fill="both", expand=True)

        tk.Label(main_frame, text=self.t("find_label")).grid(row=0, column=0, padx=(0, 5), pady=5, sticky="e")
        self.search_var = tk.StringVar()
        self.find_entry = ttk.Entry(main_frame, textvariable=self.search_var, width=25)
        self.find_entry.grid(row=0, column=1, padx=0, pady=5, sticky="ew")
        self.find_entry.focus_set()

        main_frame.columnconfigure(1, weight=1)

        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=1, column=0, columnspan=2, pady=(15, 0))
        
        ttk.Button(btn_frame, text=self.t("prev_button"), command=self.find_prev).pack(side="left", padx=5)
        ttk.Button(btn_frame, text=self.t("next_button"), command=self.find_next).pack(side="left", padx=5)

        self.update_matches()
        self.current_match_index = -1

        def on_search_var_change(*args):
            self.update_matches()
            self.current_match_index = -1
        self.search_var.trace_add("write", on_search_var_change)

    def update_matches(self):
        term = self.search_var.get()
        self.matches = []
        self.text.tag_remove("highlight", "1.0", "end")
        self.text.tag_remove("current", "1.0", "end")
        if not term:
            return
        start_pos = "1.0"
        while True:
            start_pos = self.text.search(term, start_pos, stopindex="end", nocase=True)
            if not start_pos:
                break
            end_pos = f"{start_pos}+{len(term)}c"
            self.matches.append((start_pos, end_pos))
            start_pos = end_pos
        for start, end in self.matches:
            self.text.tag_add("highlight", start, end)
        self.text.tag_configure("highlight", background="yellow")

    def find_next(self):
        if not getattr(self, 'matches', None):
            return
        self.current_match_index = (self.current_match_index + 1) % len(self.matches)
        self.select_current_match()

    def find_prev(self):
        if not getattr(self, 'matches', None):
            return
        self.current_match_index = (self.current_match_index - 1) % len(self.matches)
        self.select_current_match()

    def select_current_match(self):
        start, end = self.matches[self.current_match_index]
        self.text.tag_remove("current", "1.0", "end")
        self.text.tag_add("current", start, end)
        self.text.tag_configure("current", background="orange")
        self.text.mark_set("insert", start)
        self.text.see(start)

    def show_replace_dialog(self, event=None):
        """
        Opens the Replace dialog window.
        """
        if hasattr(self, 'rep_win') and self.rep_win.winfo_exists():
            self.rep_win.lift()
            try:
                self.rep_find_entry.focus_set()
            except Exception:
                pass
            return

        self.rep_win = tk.Toplevel(self)
        self.rep_win.title(self.t("replace_title"))
        self.rep_win.transient(self)
        self.rep_win.resizable(False, False)

        self.rep_win.update_idletasks()
        width = 360
        height = 135
        x = self.winfo_x() + (self.winfo_width() // 2) - (width // 2)
        y = self.winfo_y() + (self.winfo_height() // 2) - (height // 2)
        self.rep_win.geometry(f"{width}x{height}+{x}+{y}")

        main_frame = ttk.Frame(self.rep_win, padding="10 10 10 10")
        main_frame.pack(fill="both", expand=True)

        tk.Label(main_frame, text=self.t("replace_find_label")).grid(row=0, column=0, padx=(0, 5), pady=5, sticky="e")
        tk.Label(main_frame, text=self.t("replace_replace_label")).grid(row=1, column=0, padx=(0, 5), pady=5, sticky="e")

        self.rep_find_var = tk.StringVar()
        self.rep_replace_var = tk.StringVar()
        self.rep_find_entry = ttk.Entry(main_frame, textvariable=self.rep_find_var, width=25)
        replace_entry = ttk.Entry(main_frame, textvariable=self.rep_replace_var, width=25)
        self.rep_find_entry.grid(row=0, column=1, padx=0, pady=5, sticky="ew")
        replace_entry.grid(row=1, column=1, padx=0, pady=5, sticky="ew")
        self.rep_find_entry.focus_set()

        main_frame.columnconfigure(1, weight=1)

        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=2, column=0, columnspan=2, pady=(15, 0))

        ttk.Button(btn_frame, text=self.t("replace_next"), command=self.rep_find_next).pack(side="left", padx=5)
        ttk.Button(btn_frame, text=self.t("replace_replace"), command=self.rep_replace_current).pack(side="left", padx=5)
        ttk.Button(btn_frame, text=self.t("replace_all"), command=self.rep_replace_all).pack(side="left", padx=5)

        self.rep_matches = []
        self.rep_current_index = -1

        def on_replace_search_var_change(*args):
            self.rep_update_matches()
            self.rep_current_index = -1
        self.rep_find_var.trace_add("write", on_replace_search_var_change)

    def rep_update_matches(self):
        term = self.rep_find_var.get()
        self.rep_matches = []
        self.text.tag_remove("highlight", "1.0", "end")
        self.text.tag_remove("current", "1.0", "end")
        if not term:
            return
        start_pos = "1.0"
        while True:
            start_pos = self.text.search(term, start_pos, stopindex="end", nocase=True)
            if not start_pos:
                break
            end_pos = f"{start_pos}+{len(term)}c"
            self.rep_matches.append((start_pos, end_pos))
            start_pos = end_pos
        for start, end in self.rep_matches:
            self.text.tag_add("highlight", start, end)
        self.text.tag_configure("highlight", background="yellow")

    def rep_find_next(self):
        if not self.rep_matches:
            return
        self.rep_current_index = (self.rep_current_index + 1) % len(self.rep_matches)
        self.rep_select_current()

    def rep_select_current(self):
        if self.rep_current_index == -1 or not self.rep_matches:
            return
        start, end = self.rep_matches[self.rep_current_index]
        self.text.tag_remove("current", "1.0", "end")
        self.text.tag_add("current", start, end)
        self.text.tag_configure("current", background="orange")
        self.text.mark_set("insert", start)
        self.text.see(start)

    def rep_replace_current(self):
        if not self.rep_matches or self.rep_current_index == -1:
            return
        start, end = self.rep_matches[self.rep_current_index]
        replacement = self.rep_replace_var.get()
        self.text.delete(start, end)
        self.text.insert(start, replacement)
        self.rep_update_matches()
        self.on_text_changed()

    def rep_replace_all(self):
        self.rep_update_matches()
        if not self.rep_matches:
            return
        replacement = self.rep_replace_var.get()
        for start, end in reversed(self.rep_matches):
            self.text.delete(start, end)
            self.text.insert(start, replacement)
        self.rep_update_matches()
        self.on_text_changed()

    def apply_external_modifications(self):
        """
        Loads a secondary JSON/JWT file and merges its content into the current JSON.
        """
        path = filedialog.askopenfilename(
            title=self.t("filedialog_mod_title"),
            filetypes=[("JSON & JWT files", "*.json *.jwt"), ("JSON files", "*.json"), ("JWT files", "*.jwt"), ("All files", "*.*")]
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                file_content = f.read()
            
            file_content_stripped = file_content.strip()
            if '.' in file_content_stripped and file_content_stripped.count('.') >= 2 and not file_content_stripped.startswith('{'):
                try:
                    payload_str = extract_payload_from_jwt(file_content_stripped)
                    modifications = json.loads(payload_str)
                except Exception as e:
                    messagebox.showerror(self.t("msg_error_title"), self.t("msg_cannot_open_mods", err=e))
                    return
            else:
                try:
                    modifications = json.loads(file_content)
                except Exception as e:
                    messagebox.showerror(self.t("msg_error_title"), self.t("msg_cannot_open_mods", err=e))
                    return
        except Exception as e:
            messagebox.showerror(self.t("msg_error_title"), self.t("msg_cannot_open_mods", err=e))
            return

        cursor_index = self.text.index("insert")
        yview = self.text.yview()

        txt = self.text.get("1.0", "end-1c")
        try:
            current_json = json.loads(txt)
        except Exception as e:
            messagebox.showerror(self.t("msg_json_invalid_title"), self.t("msg_json_current_invalid", err=e))
            return

        fusionner_donnees_existantes_avec_modifications(current_json, modifications)

        pretty = json.dumps(current_json, indent=2, ensure_ascii=False)
        self._replace_text(pretty)

        self.text.mark_set("insert", cursor_index)
        self.text.yview_moveto(yview[0])

        self.status.set(self.t("msg_merge_applied", path=path))
        
        self.update_json_tree()

    def update_window_title(self):
        title = self.t("title_main")
        if self.current_jwt_path:
            title += f" - {os.path.basename(self.current_jwt_path)}"
        self.title(title)

    def load_settings(self):
        # settings.json should be in the application directory, not MEIPASS (which is temp)
        settings_path = os.path.join(get_app_dir(), "settings.json")
        if not os.path.exists(settings_path):
            # Create default settings file if it doesn't exist
            try:
                default_settings = {
                    "language": self.current_language,
                    "zoom_level": 11
                }
                with open(settings_path, "w", encoding="utf-8") as f:
                    json.dump(default_settings, f, indent=4)
            except Exception as e:
                print(f"Error creating default settings: {e}")
            return

        try:
            with open(settings_path, "r", encoding="utf-8") as f:
                settings = json.load(f)
            
            last_schema_path = settings.get("last_schema_path")
            if last_schema_path and os.path.exists(last_schema_path):
                self.load_schema_from_path(last_schema_path, silent=True)
            
            val_lang = settings.get("language")
            if val_lang in self.translations and val_lang != self.current_language:
                self.set_language(val_lang)
            
            zoom_level = settings.get("zoom_level")
            if isinstance(zoom_level, int) and zoom_level > 0:
                self.current_font.configure(size=zoom_level)
                self.bold_font.configure(size=zoom_level)
                if hasattr(self, 'linenumbers'):
                    self.linenumbers.redraw()
        except Exception as e:
            print(f"Error loading settings: {e}")

    def save_settings(self, schema_path=None):
        settings_path = os.path.join(get_app_dir(), "settings.json")
        try:
            settings = {}
            if os.path.exists(settings_path):
                try:
                    with open(settings_path, "r", encoding="utf-8") as f:
                        settings = json.load(f)
                except Exception:
                    settings = {}
            
            if schema_path is not None:
                settings["last_schema_path"] = schema_path
            
            settings["language"] = self.current_language
            settings["zoom_level"] = self.current_font.cget("size")
            
            with open(settings_path, "w", encoding="utf-8") as f:
                json.dump(settings, f, indent=4)
        except Exception as e:
            print(f"Error saving settings: {e}")

    def load_schema_from_path(self, path, silent=False):
        try:
            with open(path, "r", encoding="utf-8") as f:
                schema_data = json.load(f)
            self.loaded_schema_data = schema_data
            self.status.set(self.t("msg_schema_loaded", path=path))
            if not silent:
                messagebox.showinfo(self.t("msg_info_title"), self.t("msg_schema_loaded", path=path))
        except Exception as e:
            if not silent:
                messagebox.showerror(self.t("msg_error_title"), self.t("msg_schema_invalid", err=e))
            self.status.set(self.t("msg_error_title"))

    def load_schema_file(self):
        """
        Loads a JSON Schema file to provide context-aware suggestions (enums) in the editor.
        """
        path = filedialog.askopenfilename(
            title=self.t("filedialog_schema_title"),
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if not path:
            return
        
        self.load_schema_from_path(path)
        self.save_settings(path)

    def unload_schema(self):
        """
        Unloads the currently loaded JSON Schema.
        """
        self.loaded_schema_data = None
        # Remove schema path from settings
        self.save_settings(schema_path=None) 
        # But wait, save_settings(None) might not clear it if the logic is "if path is not None: set it".
        # Let's check save_settings implementation.
        # It says: if schema_path is not None: settings["last_schema_path"] = schema_path
        # So passing None won't clear it. I need to explicitly clear it contextually or change save_settings.
        # Actually save_settings reads the file first.
        # simpler way: 
        
        settings_path = os.path.join(get_app_dir(), "settings.json")
        try:
             settings = {}
             if os.path.exists(settings_path):
                 with open(settings_path, "r", encoding="utf-8") as f:
                     settings = json.load(f)
             
             if "last_schema_path" in settings:
                 del settings["last_schema_path"]
             
             settings["language"] = self.current_language
             settings["zoom_level"] = self.current_font.cget("size")
             
             with open(settings_path, "w", encoding="utf-8") as f:
                 json.dump(settings, f, indent=4)
        except Exception as e:
             print(f"Error saving settings: {e}")

        self.status.set(self.t("msg_schema_unloaded"))
        messagebox.showinfo(self.t("msg_info_title"), self.t("msg_schema_unloaded"))

    def get_schema_enum_for_path(self, json_path):
        if not self.loaded_schema_data:
            return None
        
        path_parts = json_path.split('.')
        
        current = self.loaded_schema_data
        
        if "properties" not in current:
            return None
        
        current = current["properties"]
        
        for part in path_parts:
            part_clean = re.sub(r'\[\d+\]', '', part)
            
            if part_clean not in current:
                return None
            
            current = current[part_clean]
            
            if isinstance(current, dict):
                if "properties" in current:
                    current = current["properties"]
                elif "items" in current:
                    current = current["items"]
                    if isinstance(current, dict) and "properties" in current:
                        current = current["properties"]
        
        if isinstance(current, dict) and "enum" in current:
            return current["enum"]
        
        return None

    def find_json_key_at_cursor(self):
        content = self.text.get("1.0", "end-1c")
        cursor_index = self.text.index("insert")
        
        line, col = map(int, cursor_index.split('.'))
        cursor_offset = sum(len(self.text.get(f"{i}.0", f"{i}.end")) + 1 for i in range(1, line)) + col
        
        lines = content[:cursor_offset].split('\n')
        
        key_pattern = r'"([^"]+)"\s*:'
        
        keys_before = []
        for match in re.finditer(key_pattern, content[:cursor_offset]):
            key_name = match.group(1)
            key_pos = match.start()
            line_start = content[:key_pos].rfind('\n') + 1
            indent_level = len(content[line_start:key_pos]) - len(content[line_start:key_pos].lstrip())
            keys_before.append({
                'name': key_name,
                'pos': key_pos,
                'indent': indent_level
            })
        
        if not keys_before:
            return None, None
        
        path_components = []
        current_indent = keys_before[-1]['indent']
        path_components.append(keys_before[-1]['name'])
        
        for i in range(len(keys_before) - 2, -1, -1):
            if keys_before[i]['indent'] < current_indent:
                path_components.insert(0, keys_before[i]['name'])
                current_indent = keys_before[i]['indent']
        
        json_path = '.'.join(path_components)
        key_name = path_components[-1] if path_components else None
        
        return key_name, json_path

    def custom_ask_yes_no_cancel(self, title, message):
        """
        Custom dialog to ask Yes/No/Cancel with translated buttons.
        Returns: True (Yes), False (No), None (Cancel)
        """
        dialog = tk.Toplevel(self)
        dialog.title(title)
        dialog.transient(self)
        dialog.resizable(False, False)
        
        # Icon and Message
        # Using a standard Frame for layout
        content_frame = ttk.Frame(dialog, padding=(15, 15, 15, 5))
        content_frame.pack(fill="both", expand=True)
        
        # Try to use a standard icon if available, otherwise just text
        # 'question' is a standard bitmap name in Tkinter
        try:
            icon_lbl = ttk.Label(content_frame, image="::tk::icons::question")
            icon_lbl.pack(side="left", padx=(0, 15), anchor="n")
        except Exception:
            pass # No icon, proceed with just text

        msg_label = ttk.Label(content_frame, text=message, wrap=350, justify='left')
        msg_label.pack(side="left", fill="both", expand=True)
        
        btn_frame = ttk.Frame(dialog, padding=(10, 5, 10, 10))
        btn_frame.pack(side="bottom", fill="x")
        
        self._custom_dialog_result = None
        
        def on_yes():
            self._custom_dialog_result = True
            dialog.destroy()
            
        def on_no():
            self._custom_dialog_result = False
            dialog.destroy()
            
        def on_cancel():
            self._custom_dialog_result = None
            dialog.destroy()
            
        # Right aligned buttons: Yes, No, Cancel (Standard Windows order)
        # Or typically Cancel is right-most on Windows. 
        # Yes | No | Cancel
        
        ttk.Button(btn_frame, text=self.t("button_cancel"), command=on_cancel).pack(side="right", padx=5)
        ttk.Button(btn_frame, text=self.t("button_no"), command=on_no).pack(side="right", padx=5)
        yes_btn = ttk.Button(btn_frame, text=self.t("button_yes"), command=on_yes)
        yes_btn.pack(side="right", padx=5)
        yes_btn.focus_set()
        
        dialog.protocol("WM_DELETE_WINDOW", on_cancel)
        
        # Center the dialog based on its actual content size
        dialog.update_idletasks()
        width = dialog.winfo_reqwidth()
        height = dialog.winfo_reqheight()
        x = self.winfo_x() + (self.winfo_width() // 2) - (width // 2)
        y = self.winfo_y() + (self.winfo_height() // 2) - (height // 2)
        dialog.geometry(f"{width}x{height}+{x}+{y}")
        
        dialog.grab_set()
        self.wait_window(dialog)
        
        return self._custom_dialog_result

    def custom_ask_yes_no(self, title, message):
        """
        Custom Yes/No dialog using translated button labels.
        Returns True for Yes, False for No.
        """
        dialog = tk.Toplevel(self)
        dialog.title(title)
        dialog.transient(self)
        dialog.resizable(False, False)

        frm = ttk.Frame(dialog, padding=12)
        frm.pack(fill="both", expand=True)

        lbl = ttk.Label(frm, text=message)
        lbl.pack(fill="x", pady=(0, 12))

        btn_frame = ttk.Frame(frm)
        btn_frame.pack(fill="x")

        result = {'value': False}

        def on_yes():
            result['value'] = True
            dialog.destroy()

        def on_no():
            result['value'] = False
            dialog.destroy()

        # Right aligned buttons: Yes | No
        ttk.Button(btn_frame, text=self.t("button_no"), command=on_no).pack(side="right", padx=5)
        yes_btn = ttk.Button(btn_frame, text=self.t("button_yes"), command=on_yes)
        yes_btn.pack(side="right", padx=5)
        yes_btn.focus_set()

        dialog.protocol("WM_DELETE_WINDOW", on_no)
        dialog.grab_set()
        self.wait_window(dialog)

        return result['value']

    def on_close(self):
        if self.is_modified:
            resp = self.custom_ask_yes_no_cancel(
                self.t("confirm_unsaved_title"),
                self.t("confirm_unsaved_text")
            )
            if resp is None:
                return
            elif resp:
                if self.current_jwt_path and self.current_jwt_path.lower().endswith('.json'):
                    self.save_current_file()
                else:
                    self.save_as_json()
        self.destroy()

    def on_drop(self, event):
        if not HAS_DND:
            return
        files = self.tk.splitlist(event.data)
        if files:
            file_path = files[0]
            self.load_file_from_path(file_path)

    def load_file_from_path(self, path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                text = f.read().strip()

            if path.lower().endswith(".jwt"):
                payload_str = extract_payload_from_jwt(text)
                content = payload_str
                self.raw_jwt_content = text
                self.status.set(self.t("msg_loaded_payload_from", path=path))
                self.plugin_manager.dispatch_event("jwt_loaded")
            elif path.lower().endswith(".json"):
                try:
                    parsed = json.loads(text)
                    content = text
                    self.raw_jwt_content = None
                    self.status.set(self.t("msg_loaded_json_from", path=path))
                    self.plugin_manager.dispatch_event("file_closed")
                except Exception as e:
                    messagebox.showerror(self.t("msg_error_title"), self.t("msg_error_loading_json", err=e))
                    self.status.set(self.t("status_error_loading_json"))
                    return
            else:
                self.raw_jwt_content = None
                self.plugin_manager.dispatch_event("file_closed")
                messagebox.showwarning(self.t("msg_unknown_format_title"), self.t("msg_unknown_format_text"))
                return

            self.current_jwt_path = path
            self.update_window_title()
            try:
                # Update File menu: Enable/Disable 'Save'
                state = "normal" if path.lower().endswith('.json') else "disabled"
                self.file_menu.entryconfig(2, state=state)
                

            except Exception as e:
                print(f"Error updating menu state: {e}")

            if path.lower().endswith('.json') and len(content) >= self._large_file_pretty_print_chars_threshold:
                self._replace_text(content)
            else:
                try:
                    parsed = json.loads(content)
                    pretty = json.dumps(parsed, indent=2, ensure_ascii=False)
                    self._replace_text(pretty)
                except Exception:
                    self._replace_text(content)
            self.is_modified = False
            
            self.update_json_tree()

        except Exception as e:
            messagebox.showerror(self.t("msg_error_title"), self.t("msg_cannot_open_mods", err=e))
            self.status.set(self.t("status_error_opening"))

    def show_about_dialog(self):
        """
        Displays the About dialog.
        """
        messagebox.showinfo(self.t("menu_about"), self.t("about_dialog_text"))

def main():
    root = JWTEditorApp()
    root.mainloop()

if __name__ == "__main__":
    main()