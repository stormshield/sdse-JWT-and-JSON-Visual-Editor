
import os
import sys
import json
import re
import tkinter as tk
from tkinter import messagebox, scrolledtext, filedialog
from tkinter import ttk

def get_plugin_resource_path(relative_path):
    """Get absolute path to plugin resource, works for dev and for PyInstaller."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    dev_path = os.path.join(current_dir, relative_path)
    
    if os.path.exists(dev_path):
        return dev_path
    
    try:
        base_path = sys._MEIPASS
        possible_paths = [
            os.path.join(base_path, "plugins", "Standard plugins", "schemaGenerator", relative_path),
            os.path.join(base_path, "plugins", "Standard_plugins", "schemaGenerator", relative_path),
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

# Pattern detection regexes
EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
URL_PATTERN = re.compile(r'^https?://')
ISO_DATE_PATTERN = re.compile(r'^\d{4}-\d{2}-\d{2}$')
ISO_DATETIME_PATTERN = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}')
UUID_PATTERN = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.I)


def detect_string_format(value):
    """Détecte le format d'une chaîne de caractères."""
    if not isinstance(value, str):
        return None
    
    if UUID_PATTERN.match(value):
        return "uuid"
    if EMAIL_PATTERN.match(value):
        return "email"
    if URL_PATTERN.match(value):
        return "uri"
    if ISO_DATETIME_PATTERN.match(value):
        return "date-time"
    if ISO_DATE_PATTERN.match(value):
        return "date"
    
    return None


def infer_type(value):
    """Détecte le type JSON d'une valeur Python."""
    if isinstance(value, dict):
        return "object"
    elif isinstance(value, list):
        return "array"
    elif isinstance(value, bool):
        return "boolean"
    elif isinstance(value, int):
        return "integer"
    elif isinstance(value, float):
        return "number"
    elif value is None:
        return "null"
    else:
        return "string"


def merge_schemas(schemas):
    """Fusionne plusieurs schémas en un seul."""
    if not schemas:
        return {}
    
    if len(schemas) == 1:
        return schemas[0]
    
    # Collecter tous les types
    types = set()
    all_properties = {}
    all_required = {}  # Count occurrences
    all_enums = []
    formats = set()
    items_schemas = []
    
    for schema in schemas:
        schema_type = schema.get("type")
        if isinstance(schema_type, list):
            types.update(schema_type)
        elif schema_type:
            types.add(schema_type)
        
        # Fusionner les propriétés (pour les objets)
        if "properties" in schema:
            for key, prop_schema in schema["properties"].items():
                if key in all_properties:
                    # Fusionner récursivement
                    all_properties[key] = merge_schemas([all_properties[key], prop_schema])
                else:
                    all_properties[key] = prop_schema
        
        # Compter les champs requis
        if "required" in schema:
            for field in schema["required"]:
                all_required[field] = all_required.get(field, 0) + 1
        
        # Fusionner les enums
        if "enum" in schema:
            all_enums.extend(schema["enum"])
        
        # Collecter les formats
        if "format" in schema:
            formats.add(schema["format"])
        
        # Collecter les items (pour les tableaux)
        if "items" in schema:
            items_schemas.append(schema["items"])
    
    # Construire le schéma fusionné
    merged = {}
    
    # Type
    types_list = sorted(list(types))
    if len(types_list) == 1:
        merged["type"] = types_list[0]
    elif len(types_list) > 1:
        merged["type"] = types_list
    
    # Propriétés
    if all_properties:
        merged["properties"] = all_properties
    
    # Required (seulement les champs présents dans TOUS les schémas objets)
    if all_required:
        # Compter le nombre de schémas objets
        object_schema_count = sum(1 for s in schemas if s.get("type") == "object" or "properties" in s)
        
        # Ne garder que les champs présents dans tous les schémas objets
        truly_required = [
            field for field, count in all_required.items()
            if count == object_schema_count
        ]
        if truly_required:
            merged["required"] = sorted(truly_required)
    
    # Items (pour les tableaux)
    if items_schemas:
        merged["items"] = merge_schemas(items_schemas)
    
    # Enum (valeurs uniques)
    if all_enums:
        unique_enums = []
        seen = set()
        for val in all_enums:
            # Pour gérer les valeurs non hashables
            try:
                if val not in seen:
                    unique_enums.append(val)
                    seen.add(val)
            except TypeError:
                # Valeur non hashable (dict, list)
                val_str = json.dumps(val, sort_keys=True)
                if val_str not in seen:
                    unique_enums.append(val)
                    seen.add(val_str)
        merged["enum"] = unique_enums
    
    # Format (si tous concordent)
    if len(formats) == 1:
        merged["format"] = list(formats)[0]
    
    return merged


def analyze_array_items(items, options):
    """Analyse tous les éléments d'un tableau."""
    if not items:
        return {}
    
    # Si l'option analyze_all_items est désactivée, comportement par défaut
    if not options.get("analyze_all_items", True):
        return generate_schema(items[0], options)
    
    # Générer un schéma pour chaque élément
    schemas = [generate_schema(item, options) for item in items]
    
    # Fusionner les schémas
    return merge_schemas(schemas)


def generate_schema(data, options=None):
    """
    Génère un schéma JSON à partir des données avec options configurables.
    
    Args:
        data: Données JSON à analyser
        options: {
            'all_required': bool (défaut: True),
            'generate_enums': bool (défaut: True),
            'detect_patterns': bool (défaut: True),
            'analyze_all_items': bool (défaut: True)
        }
    """
    if options is None:
        options = {
            'all_required': True,
            'generate_enums': True,
            'detect_patterns': True,
            'analyze_all_items': True
        }
    
    schema = {"type": infer_type(data)}

    if isinstance(data, dict):
        schema["properties"] = {}
        required = []
        for key, value in data.items():
            schema["properties"][key] = generate_schema(value, options)
            if options.get('all_required', True):
                required.append(key)
        if required:
            schema["required"] = sorted(required)

    elif isinstance(data, list):
        if data:
            # Si c'est une liste de valeurs simples
            if all(not isinstance(i, (dict, list)) for i in data):
                item_type = infer_type(data[0])
                schema["items"] = {"type": item_type}
                
                if options.get('generate_enums', True):
                    # Créer enum avec valeurs uniques
                    unique_values = list(set(data))
                    schema["items"]["enum"] = unique_values
            else:
                # Analyser tous les éléments du tableau
                schema["items"] = analyze_array_items(data, options)
        else:
            schema["items"] = {}

    else:
        # Pour les valeurs simples
        if options.get('generate_enums', True):
            schema["enum"] = [data]
        
        # Détection de patterns pour les strings
        if options.get('detect_patterns', True) and isinstance(data, str):
            detected_format = detect_string_format(data)
            if detected_format:
                schema["format"] = detected_format

    return schema


class JSONSchemaGeneratorWindow:
    def __init__(self, parent, app, plugin):
        self.app = app
        self.plugin = plugin
        self.root = tk.Toplevel(parent)
        self.root.title(self.plugin.t("window_title"))
        self.root.geometry("950x700")

        # Liste des exemples: [(name, data), ...]
        self.examples = []
        
        # Cadre principal
        main_frame = tk.Frame(self.root)
        main_frame.pack(padx=10, pady=10, fill="both", expand=True)
        
        # Section exemples
        examples_frame = ttk.LabelFrame(main_frame, text=self.plugin.t("examples_label"), padding=5)
        examples_frame.pack(fill="x", pady=(0, 10))
        
        # Layout horizontal pour la listbox et les boutons
        examples_inner = tk.Frame(examples_frame)
        examples_inner.pack(fill="x")
        
        # Listbox pour les exemples
        list_frame = tk.Frame(examples_inner)
        list_frame.pack(side="left", fill="both", expand=True)
        
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")
        
        self.examples_listbox = tk.Listbox(list_frame, height=4, yscrollcommand=scrollbar.set)
        self.examples_listbox.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.examples_listbox.yview)
        
        # Boutons
        btn_examples_frame = tk.Frame(examples_inner)
        btn_examples_frame.pack(side="left", padx=(10, 0))
        
        tk.Button(btn_examples_frame, text=self.plugin.t("btn_add_example"), 
                 command=self.add_example).pack(fill="x", pady=2)
        tk.Button(btn_examples_frame, text=self.plugin.t("btn_remove_example"), 
                 command=self.remove_example).pack(fill="x", pady=2)
        
        # Afficher le fichier actuel comme premier exemple
        self.examples_listbox.insert(tk.END, self.plugin.t("current_file_label"))
        
        # Boutons d'action principaux
        btn_frame = tk.Frame(main_frame)
        btn_frame.pack(pady=5)
        
        tk.Button(btn_frame, text=self.plugin.t("btn_generate_from_current"), 
                 command=self.generate_schema_from_examples).pack(side="left", padx=5)
        tk.Button(btn_frame, text=self.plugin.t("btn_save_schema"), 
                 command=self.save_schema).pack(side="left", padx=5)
        tk.Button(btn_frame, text=self.plugin.t("btn_copy_to_clipboard"), 
                 command=self.copy_to_clipboard).pack(side="left", padx=5)
        tk.Button(btn_frame, text=self.plugin.t("btn_clear"), 
                 command=self.clear_schema).pack(side="left", padx=5)

        # Zone d'affichage du résultat
        self.text = scrolledtext.ScrolledText(main_frame, wrap=tk.WORD, font=("Consolas", 10))
        self.text.pack(fill="both", expand=True, padx=5, pady=5)

        self.schema = None
        
        # Focus on window
        self.root.focus_force()

        # Support Drag & Drop
        try:
            self.examples_listbox.drop_target_register('DND_Files')
            self.examples_listbox.dnd_bind('<<Drop>>', self.on_drop)
        except Exception:
            pass

    def add_example(self):
        """Ajoute un ou plusieurs fichiers JSON comme exemple."""
        paths = filedialog.askopenfilenames(
            parent=self.root,
            title=self.plugin.t("choose_json_file"),
            filetypes=[(self.plugin.t("file_type_json"), "*.json"), 
                      (self.plugin.t("file_type_all"), "*.*")]
        )
        if not paths:
            return
        
        for path in paths:
            self.load_example_file(path)

    def load_example_file(self, path):
        """Charge un fichier exemple individuel."""
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            name = os.path.basename(path)
            self.examples.append((name, data))
            self.examples_listbox.insert(tk.END, name)

        except Exception as e:
            messagebox.showerror(
                self.plugin.t("error_title"),
                self.plugin.t("error_load_example").format(e)
            )

    def on_drop(self, event):
        """Gère le glisser-déposer de fichiers."""
        try:
            if hasattr(event, 'data'):
                files = self.root.tk.splitlist(event.data)
                for path in files:
                    # On accepte tout, le load tentera le json.load
                    self.load_example_file(path)
        except Exception:
            pass

    def remove_example(self):
        """Supprime l'exemple sélectionné."""
        selection = self.examples_listbox.curselection()
        if not selection:
            return
        
        index = selection[0]
        
        # Ne pas permettre de supprimer le fichier actuel (index 0)
        if index == 0:
            messagebox.showwarning(
                self.plugin.t("warning_title"),
                self.plugin.t("warning_cannot_remove_current")
            )
            return
        
        # Supprimer de la liste (index - 1 car le fichier actuel n'est pas dans self.examples)
        self.examples.pop(index - 1)
        self.examples_listbox.delete(index)

    def clear_schema(self):
        """Efface le schéma affiché."""
        self.text.delete("1.0", tk.END)
        self.schema = None

    def generate_schema_from_examples(self):
        """Génère le schéma à partir du fichier actuel et des exemples additionnels."""
        try:
            # Récupérer le contenu JSON actuel de l'éditeur
            json_text = self.app.text.get("1.0", "end-1c")
            if not json_text.strip():
                messagebox.showwarning(
                    self.plugin.t("warning_title"), 
                    self.plugin.t("warning_no_json")
                )
                return

            current_data = json.loads(json_text)
            
            # Options de génération
            options = {
                'all_required': True,
                'generate_enums': True,
                'detect_patterns': True,
                'analyze_all_items': True
            }
            
            # Si pas d'exemples additionnels, générer normalement
            if not self.examples:
                self.schema = generate_schema(current_data, options)
            else:
                # Générer un schéma pour chaque exemple
                all_data = [current_data] + [data for _, data in self.examples]
                schemas = [generate_schema(data, options) for data in all_data]
                
                # Fusionner tous les schémas
                self.schema = merge_schemas(schemas)
                
                # Schema generated from multi-examples successfully (no pop-up)


            # Afficher le schéma
            self.text.delete("1.0", tk.END)
            self.text.insert(tk.END, json.dumps(self.schema, indent=4, ensure_ascii=False))

            if not self.examples:
                # Schema generated successfully (no pop-up)
                pass


        except json.JSONDecodeError as e:
            messagebox.showerror(
                self.plugin.t("error_title"), 
                self.plugin.t("error_invalid_json").format(e)
            )
        except Exception as e:
            messagebox.showerror(
                self.plugin.t("error_title"), 
                self.plugin.t("error_generation").format(e)
            )

    def copy_to_clipboard(self):
        """Copie le schéma dans le presse-papiers."""
        if not self.schema:
            messagebox.showwarning(
                self.plugin.t("warning_title"), 
                self.plugin.t("warning_no_schema")
            )
            return

        try:
            schema_text = self.text.get("1.0", "end-1c")
            self.root.clipboard_clear()
            self.root.clipboard_append(schema_text)
            # Copied successfully (no pop-up)

        except Exception as e:
            messagebox.showerror(
                self.plugin.t("error_title"), 
                self.plugin.t("error_copy").format(e)
            )

    def save_schema(self):
        """Sauvegarde le schéma dans un fichier."""
        if not self.schema:
            messagebox.showwarning(
                self.plugin.t("warning_title"), 
                self.plugin.t("warning_no_schema")
            )
            return

        # Déterminer le chemin de sauvegarde par défaut
        if self.app.current_jwt_path:
            # Utiliser le même répertoire que le fichier courant
            target_dir = os.path.dirname(self.app.current_jwt_path)
            base_name = os.path.splitext(os.path.basename(self.app.current_jwt_path))[0]
            default_name = f"{base_name}_schema.json"
        else:
            target_dir = os.path.join(os.path.expanduser("~"), "Desktop")
            default_name = "schema.json"

        path = filedialog.asksaveasfilename(
            title=self.plugin.t("save_dialog_title"),
            initialdir=target_dir,
            initialfile=default_name,
            defaultextension=".json",
            filetypes=[(self.plugin.t("file_type_json"), "*.json"), 
                      (self.plugin.t("file_type_all"), "*.*")]
        )
        if not path:
            return

        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.schema, f, indent=4, ensure_ascii=False)
            # Saved successfully (no pop-up)

        except Exception as e:
            messagebox.showerror(
                self.plugin.t("error_title"), 
                self.plugin.t("error_save").format(e)
            )


class Plugin:
    def __init__(self, app):
        self.app = app
        self.translations = translations

    def t(self, key, **kwargs):
        """Récupère une traduction dans la langue actuelle."""
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
        """Enregistre le plugin - appelé au chargement initial."""
        pass

    def on_event(self, event_name, data=None):
        """Gère les événements de l'application."""
        if event_name == "ui_ready":
            self.register_menu()
        elif event_name == "language_changed":
            self.update_menu_text()

    def register_menu(self):
        """Ajoute le plugin dans le menu Outils une fois l'interface prête."""
        try:
            # Ajouter une entrée dans le menu Outils
            self.app.tools_menu.add_separator()
            self.app.tools_menu.add_command(
                label=self.t("menu_label"), 
                command=self.open_schema_generator
            )
            self.menu_index = self.app.tools_menu.index("end")
            print("Plugin Schema Generator: Added to menu")
        except Exception as e:
            print(f"Error registering schema generator plugin: {e}")

    def update_menu_text(self):
        """Met à jour le texte du menu lors du changement de langue."""
        if hasattr(self, 'menu_index'):
            try:
                self.app.tools_menu.entryconfig(self.menu_index, label=self.t("menu_label"))
            except Exception as e:
                print(f"Error updating schema generator menu: {e}")

    def open_schema_generator(self):
        """Ouvre la fenêtre du générateur de schéma JSON."""
        try:
            JSONSchemaGeneratorWindow(self.app, self.app, self)
        except Exception as e:
            messagebox.showerror(
                "Error", 
                f"Failed to open JSON Schema Generator: {e}"
            )
