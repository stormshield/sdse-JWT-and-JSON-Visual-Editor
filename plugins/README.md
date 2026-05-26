# Development of Plugins for JWT & JSON Visual Editor

This folder `plugins/` allows extending the application features without modifying the core code (`.pyw`).

---

## 🇬🇧 English Guide

### How it works

At startup, the application **recursively** scans this folder via the `PluginManager` and automatically loads any Python file whose name starts with `plugin_` (including those in subdirectories). Each module is imported dynamically with `importlib` and must expose a `Plugin` class.

**Loading order:**
1. All `plugin_*.py` files are discovered with `glob` (recursive).
2. Each module is imported and its `Plugin` class is instantiated with the `app` reference.
3. `register()` is called on every plugin.
4. Shortly after startup, a `ui_ready` event is dispatched so plugins can safely interact with the fully built UI.

**Folder Structure:**
Plugins are organized into three categories of subdirectories:

```
plugins/
├── README.md
├── Required plugins/
│   └── utils/
│       ├── plugin_utils.py          # Shared utility: resource path resolution
│       └── README.md
├── Standard plugins/
│   ├── boolean/
│   │   ├── plugin_boolean.py        # Toggle true/false on right-click
│   │   └── README.md
│   ├── certificates/
│   │   ├── plugin_certificates.py   # X.509 certificate viewer/extractor
│   │   ├── languages.json
│   │   └── README.md
│   ├── extractor/
│   │   ├── plugin_extractor.py      # Extract selection to extract.json
│   │   ├── languages.json
│   │   └── README.md
│   └── schemaGenerator/
│       ├── plugin_schemaGenerator.py # Generate JSON Schema from data
│       ├── languages.json
│       └── README.md
└── SDS plugins/
    ├── date/
    │   ├── plugin_SDS_date.py       # Update date fields via context menu
    │   ├── languages.json
    │   └── README.md
    ├── ids/
    │   ├── plugin_SDS_ids.py        # Generate ObjectId/UUID, certificate & LDAP preview
    │   ├── plugin_SDS_id_reveal.py  # AltGr ID reveal (cert CN / LDAP name)
    │   ├── languages.json
    │   ├── languages_reveal.json
    │   └── README.md
    ├── importCerts/
    │   ├── plugin_SDS_import_certs.py  # Import certificates into certificateData
    │   ├── languages.json
    │   └── README.md
    ├── p7bBuilder/
    │   ├── plugin_p7b_builder.py    # Build PKCS#7 (.p7b) bundles
    │   ├── languages.json
    │   └── README.md
    └── policySign/
        ├── plugin_SDS_signer.py     # Sign JSON payloads with P12 → JWT
        ├── languages.json
        ├── CHANGELOG.md
        └── README.md
```

**⚠️ Important:** If your plugin loads local resources (like `languages.json`), see the **Resource Path Resolution** section below for PyInstaller compatibility.

---

### Step 1: Create the file

Create a new Python file whose name starts with `plugin_`, e.g., `plugin_example.py`.
Place it anywhere inside the `plugins/` folder (including subdirectories).

### Step 2: Basic Structure

Each plugin must define a `Plugin` class with two mandatory methods:
1. `__init__(self, app)`: Receives the main `JWTEditorApp` instance.
2. `register(self)`: Called at startup to add menus or buttons.

```python
import tkinter as tk
from tkinter import messagebox

class Plugin:
    def __init__(self, app):
        self.app = app  # 'app' is the main application instance (JWTEditorApp)

    def register(self):
        # This is where you hook into the UI at startup
        pass
```

### Step 3: Optional Hook Methods

Beyond `register()`, plugins can implement additional methods that the `PluginManager` will call automatically:

| Method | When it is called |
| :--- | :--- |
| `register(self)` | Once at startup, after the plugin is loaded. |
| `extend_context_menu(self, menu, event)` | Every time the user right-clicks in the text editor. |
| `on_event(self, event_name, data=None)` | When the application dispatches a lifecycle event (see Events below). |

### Step 4: Concrete Examples

#### Example A: Add a button to the "Tools" menu

```python
    def register(self):
        # Adds a "Say Hello" option to the Tools menu
        if hasattr(self.app, 'tools_menu'):
            self.app.tools_menu.add_command(
                label="Say Hello",
                command=self.say_hello
            )

    def say_hello(self):
        messagebox.showinfo("Hi", "Hello from my plugin!")
```

#### Example B: Add an option to the Right-Click (Context) Menu

Define `extend_context_menu` to add options when the user right-clicks in the editor.

```python
    def extend_context_menu(self, menu, event):
        """
        Called every time the user right-clicks.
        'menu' is the context menu object about to be shown.
        'event' contains the click coordinates (event.x, event.y).
        """
        menu.add_separator()
        menu.add_command(label="My Right-Click Action", command=self.my_action)

    def my_action(self):
        print("Right-click action triggered!")
```

**Advanced — detect the word under cursor** (see `plugin_boolean.py`):

```python
    def extend_context_menu(self, menu, event):
        index = self.app.text.index(f"@{event.x},{event.y}")
        try:
            token = self.app.text.get(f"{index} wordstart", f"{index} wordend").strip()
        except Exception:
            token = ""

        if token.lower() in ("true", "false"):
            start_idx = self.app.text.index(f"{index} wordstart")
            end_idx = self.app.text.index(f"{index} wordend")
            new_val = "false" if token.lower() == "true" else "true"
            menu.add_command(
                label=new_val,
                command=lambda s=start_idx, e=end_idx, v=new_val: self.app.replace_word(s, e, v)
            )
```

#### Example C: React to Application Events

Implement `on_event` to react to lifecycle events:

```python
    def on_event(self, event_name, data=None):
        if event_name == "ui_ready":
            # The UI is fully built — safe to add menu items
            self.app.tools_menu.add_command(label="My Tool", command=self.run)

        elif event_name == "jwt_loaded":
            # A JWT file has been loaded and decoded
            print("JWT loaded!")

        elif event_name == "file_closed":
            # The current file has been closed / reset
            pass

        elif event_name == "language_changed":
            # 'data' is the new language code (e.g. 'fr', 'en')
            self.update_menu_labels()
```

#### Example D: Read and Modify JSON Text

Everything happens via `self.app.text` (Tkinter `Text` widget):

```python
    def run_my_tool(self):
        # 1. Get all text
        full_text = self.app.text.get("1.0", "end-1c")

        # 2. Get selected text (if any)
        try:
            selected_text = self.app.text.get("sel.first", "sel.last")
        except:
            selected_text = ""

        # 3. Insert text at cursor position
        self.app.text.insert("insert", " Hello ")

        # 4. Replace a word at a known position
        self.app.replace_word(start_index, end_index, "new_value")
```

---

### Plugin API Reference

#### Application Properties

| Property | Type | Description |
| :--- | :--- | :--- |
| `self.app.root` / `self.app` | `Tk` | The main window (the app *is* the root window). |
| `self.app.text` | `CustomText` | The text editor widget (enhanced Tkinter `Text`). |
| `self.app.tree` | `Treeview` | The tree view panel (left side). |
| `self.app.current_language` | `str` | Current language code (`'fr'`, `'en'`, `'es'`, `'de'`, `'it'`). |
| `self.app.tools_menu` | `Menu` | The "Tools" menu in the menu bar. |
| `self.app.menubar` | `Menu` | The full application menu bar. |
| `self.app.status` | `StringVar` | The status bar text (use `.set("msg")` to update). |
| `self.app.current_jwt_path` | `str\|None` | Path to the currently loaded file, or `None`. |
| `self.app.raw_jwt_content` | `str\|None` | Raw JWT string (before decoding), or `None` if not a JWT. |
| `self.app.is_modified` | `bool` | Whether the document has unsaved changes. |
| `self.app.translations` | `dict` | Core translation dictionary. |
| `self.app.t(key, **kwargs)` | `callable` | Look up a core translation key for the current language. |

#### Application Methods

| Method | Description |
| :--- | :--- |
| `self.app.replace_word(start, end, new_value)` | Replace text between two indices, re-applies syntax highlighting. |
| `self.app.apply_syntax_highlighting()` | Re-apply syntax highlighting to the editor. |
| `self.app.clipboard_clear()` | Clear the system clipboard. |
| `self.app.clipboard_append(text)` | Append text to the system clipboard. |
| `self.app.update_idletasks()` | Process pending UI updates. |

#### Plugin Events

Events are dispatched via `PluginManager.dispatch_event()` and received in `on_event(self, event_name, data)`:

| Event Name | `data` | When |
| :--- | :--- | :--- |
| `ui_ready` | `None` | The UI is fully built (≈100ms after startup). Best time to add menu items. |
| `jwt_loaded` | `None` | A JWT file was loaded and its payload decoded. |
| `file_closed` | `None` | The current file has been closed or a new empty document was created. |
| `language_changed` | `str` (lang code) | The user changed the interface language. |

---

### Resource Path Resolution (PyInstaller Compatibility)

When PyInstaller bundles the application, files are moved to a temporary `_MEIPASS` folder. Standard `__file__` paths will not work. Two approaches are available:

#### Option 1: Use the shared `plugin_utils` module (recommended)

```python
from utils.plugin_utils import get_plugin_resource_path
import json

lang_path = get_plugin_resource_path("SDS plugins/policySign", "languages.json")
with open(lang_path, "r", encoding="utf-8") as f:
    translations = json.load(f)
```

**Arguments:**
- `plugin_folder_path`: relative path from `plugins/` to your plugin folder (e.g. `"SDS plugins/date"`)
- `relative_path`: filename inside that folder (e.g. `"languages.json"`)

#### Option 2: Inline path resolution (self-contained)

```python
import json, os, sys

def get_plugin_resource_path(relative_path):
    """Get absolute path to plugin resource, works for dev and for PyInstaller."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    dev_path = os.path.join(current_dir, relative_path)

    if os.path.exists(dev_path):
        return dev_path

    try:
        base_path = sys._MEIPASS
        plugin_rel = os.path.join("plugins", "Your Plugin Folder", relative_path)
        return os.path.join(base_path, plugin_rel)
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
        print(f"Plugin: languages.json not found at {lang_path}")
except Exception as e:
    print(f"Plugin: Could not load languages.json: {e}")
    translations = {}
```

---

### Internationalization

Plugins can manage their own translations using a `languages.json` file placed alongside the plugin script.

**Structure of `languages.json`:**

```json
{
    "fr": {
        "my_label": "Mon libellé",
        "my_message": "Bonjour {name} !"
    },
    "en": {
        "my_label": "My Label",
        "my_message": "Hello {name}!"
    }
}
```

**Translation helper** (define in your Plugin class):

```python
def t(self, key, **kwargs):
    lang = getattr(self.app, "current_language", "en")
    text = self.translations.get(lang, self.translations.get("en", {})).get(key, key)
    if kwargs:
        try:
            return text.format(**kwargs)
        except:
            return text
    return text
```

Use `self.t("my_message", name="World")` in your plugin code.

**Remember to react to language changes** by implementing `on_event("language_changed", data)` if your plugin has dynamic menu labels.

---

### Full Plugin Template

```python
import tkinter as tk
from tkinter import messagebox
import json
import os
import sys

def get_plugin_resource_path(relative_path):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    dev_path = os.path.join(current_dir, relative_path)
    if os.path.exists(dev_path):
        return dev_path
    try:
        base_path = sys._MEIPASS
        plugin_rel = os.path.join("plugins", "Standard plugins", "myPlugin", relative_path)
        return os.path.join(base_path, plugin_rel)
    except Exception:
        return dev_path

# Load translations
try:
    lang_path = get_plugin_resource_path("languages.json")
    with open(lang_path, "r", encoding="utf-8") as f:
        translations = json.load(f)
except Exception:
    translations = {}

class Plugin:
    def __init__(self, app):
        self.app = app
        self.translations = translations

    def t(self, key, **kwargs):
        lang = getattr(self.app, "current_language", "en")
        text = self.translations.get(lang, self.translations.get("en", {})).get(key, key)
        if kwargs:
            try:
                return text.format(**kwargs)
            except:
                return text
        return text

    def register(self):
        pass  # Use on_event("ui_ready") for menu items if needed

    def on_event(self, event_name, data=None):
        if event_name == "ui_ready":
            if hasattr(self.app, 'tools_menu'):
                self.app.tools_menu.add_separator()
                self.app.tools_menu.add_command(
                    label=self.t("menu_label"),
                    command=self.run
                )
        elif event_name == "language_changed":
            pass  # Update menu labels here

    def extend_context_menu(self, menu, event):
        menu.add_separator()
        menu.add_command(label=self.t("ctx_label"), command=self.run)

    def run(self):
        text = self.app.text.get("1.0", "end-1c")
        messagebox.showinfo("Plugin", f"Text length: {len(text)}")
```

---
---

## 🇫🇷 Guide Français

### Comment ça marche ?

Au démarrage de l'application, le `PluginManager` scanne **récursivement** ce dossier et charge automatiquement tout fichier Python dont le nom commence par `plugin_` (y compris dans les sous-dossiers). Chaque module est importé dynamiquement avec `importlib` et doit exposer une classe `Plugin`.

**Ordre de chargement :**
1. Tous les fichiers `plugin_*.py` sont découverts via `glob` (récursif).
2. Chaque module est importé et sa classe `Plugin` est instanciée avec la référence `app`.
3. `register()` est appelé sur chaque plugin.
4. Peu après le démarrage, un événement `ui_ready` est envoyé pour que les plugins puissent interagir avec l'interface complètement construite.

**Structure des dossiers :**
Les plugins sont organisés en trois catégories de sous-dossiers :

```
plugins/
├── README.md
├── Required plugins/
│   └── utils/
│       ├── plugin_utils.py          # Utilitaire partagé : résolution de chemins
│       └── README.md
├── Standard plugins/
│   ├── boolean/
│   │   ├── plugin_boolean.py        # Basculer true/false au clic droit
│   │   └── README.md
│   ├── certificates/
│   │   ├── plugin_certificates.py   # Visualiseur/extracteur de certificats X.509
│   │   ├── languages.json
│   │   └── README.md
│   ├── extractor/
│   │   ├── plugin_extractor.py      # Extraire la sélection vers extract.json
│   │   ├── languages.json
│   │   └── README.md
│   └── schemaGenerator/
│       ├── plugin_schemaGenerator.py # Générer un JSON Schema à partir des données
│       ├── languages.json
│       └── README.md
└── SDS plugins/
    ├── date/
    │   ├── plugin_SDS_date.py       # Mise à jour des champs date via menu contextuel
    │   ├── languages.json
    │   └── README.md
    ├── ids/
    │   ├── plugin_SDS_ids.py        # Génération ObjectId/UUID, aperçu certificat & LDAP
    │   ├── plugin_SDS_id_reveal.py  # Révélation d'IDs via AltGr (CN certificat / nom LDAP)
    │   ├── languages.json
    │   ├── languages_reveal.json
    │   └── README.md
    ├── importCerts/
    │   ├── plugin_SDS_import_certs.py  # Import de certificats dans certificateData
    │   ├── languages.json
    │   └── README.md
    ├── p7bBuilder/
    │   ├── plugin_p7b_builder.py    # Construction de bundles PKCS#7 (.p7b)
    │   ├── languages.json
    │   └── README.md
    └── policySign/
        ├── plugin_SDS_signer.py     # Signature de payloads JSON avec P12 → JWT
        ├── languages.json
        ├── CHANGELOG.md
        └── README.md
```

**⚠️ Important :** Si votre plugin charge des ressources locales (comme `languages.json`), consultez la section **Résolution de chemins** ci-dessous pour la compatibilité PyInstaller.

---

### Étape 1 : Créer le fichier

Créez un nouveau fichier Python dont le nom commence par `plugin_`, par exemple `plugin_exemple.py`.
Placez-le n'importe où dans le dossier `plugins/` (y compris dans des sous-dossiers).

### Étape 2 : La structure de base

Chaque plugin doit contenir une classe `Plugin` avec deux méthodes obligatoires :
1. `__init__(self, app)` : Reçoit l'instance principale `JWTEditorApp`.
2. `register(self)` : Appelée au démarrage pour ajouter des menus ou boutons.

```python
import tkinter as tk
from tkinter import messagebox

class Plugin:
    def __init__(self, app):
        self.app = app  # 'app' est l'application principale (JWTEditorApp)

    def register(self):
        # C'est ici qu'on ajoute des éléments à l'interface au démarrage
        pass
```

### Étape 3 : Méthodes optionnelles (Hooks)

En plus de `register()`, les plugins peuvent implémenter des méthodes additionnelles que le `PluginManager` appellera automatiquement :

| Méthode | Quand elle est appelée |
| :--- | :--- |
| `register(self)` | Une fois au démarrage, après le chargement du plugin. |
| `extend_context_menu(self, menu, event)` | À chaque clic droit dans l'éditeur de texte. |
| `on_event(self, event_name, data=None)` | Lors de la diffusion d'un événement de cycle de vie (voir Événements ci-dessous). |

### Étape 4 : Exemples Concrets

#### Exemple A : Ajouter un bouton dans le menu « Outils »

```python
    def register(self):
        # Ajoute une option "Dire Bonjour" dans le menu Outils
        if hasattr(self.app, 'tools_menu'):
            self.app.tools_menu.add_command(
                label="Dire Bonjour",
                command=self.say_hello
            )

    def say_hello(self):
        messagebox.showinfo("Coucou", "Bonjour depuis mon plugin !")
```

#### Exemple B : Ajouter une option au Clic Droit (Menu Contextuel)

Définissez `extend_context_menu` pour ajouter des options au clic droit dans l'éditeur.

```python
    def extend_context_menu(self, menu, event):
        """
        Appelé à chaque fois que l'utilisateur fait un clic droit.
        'menu' est le menu contextuel qui va s'afficher.
        'event' contient les coordonnées du clic (event.x, event.y).
        """
        menu.add_separator()
        menu.add_command(label="Mon Action Clic Droit", command=self.mon_action)

    def mon_action(self):
        print("Action du clic droit déclenchée !")
```

**Avancé — détecter le mot sous le curseur** (voir `plugin_boolean.py`) :

```python
    def extend_context_menu(self, menu, event):
        index = self.app.text.index(f"@{event.x},{event.y}")
        try:
            token = self.app.text.get(f"{index} wordstart", f"{index} wordend").strip()
        except Exception:
            token = ""

        if token.lower() in ("true", "false"):
            start_idx = self.app.text.index(f"{index} wordstart")
            end_idx = self.app.text.index(f"{index} wordend")
            new_val = "false" if token.lower() == "true" else "true"
            menu.add_command(
                label=new_val,
                command=lambda s=start_idx, e=end_idx, v=new_val: self.app.replace_word(s, e, v)
            )
```

#### Exemple C : Réagir aux événements de l'application

Implémentez `on_event` pour réagir aux événements du cycle de vie :

```python
    def on_event(self, event_name, data=None):
        if event_name == "ui_ready":
            # L'interface est complètement construite — sûr d'ajouter des menus
            self.app.tools_menu.add_command(label="Mon Outil", command=self.run)

        elif event_name == "jwt_loaded":
            # Un fichier JWT a été chargé et décodé
            print("JWT chargé !")

        elif event_name == "file_closed":
            # Le fichier actuel a été fermé / réinitialisé
            pass

        elif event_name == "language_changed":
            # 'data' est le nouveau code de langue (ex : 'fr', 'en')
            self.update_menu_labels()
```

#### Exemple D : Lire et Modifier le texte JSON

Tout se passe via `self.app.text` (widget Tkinter `Text`) :

```python
    def run_my_tool(self):
        # 1. Récupérer tout le texte
        full_text = self.app.text.get("1.0", "end-1c")

        # 2. Récupérer le texte sélectionné (s'il y en a)
        try:
            selected_text = self.app.text.get("sel.first", "sel.last")
        except:
            selected_text = ""

        # 3. Insérer du texte à la position du curseur
        self.app.text.insert("insert", " Hello ")

        # 4. Remplacer un mot à une position connue
        self.app.replace_word(start_index, end_index, "nouvelle_valeur")
```

---

### Référence API des Plugins

#### Propriétés de l'Application

| Propriété | Type | Description |
| :--- | :--- | :--- |
| `self.app.root` / `self.app` | `Tk` | La fenêtre principale (l'app *est* la fenêtre root). |
| `self.app.text` | `CustomText` | Le widget éditeur de texte (Tkinter `Text` amélioré). |
| `self.app.tree` | `Treeview` | Le panneau arborescent (côté gauche). |
| `self.app.current_language` | `str` | Code de la langue actuelle (`'fr'`, `'en'`, `'es'`, `'de'`, `'it'`). |
| `self.app.tools_menu` | `Menu` | Le menu « Outils » dans la barre de menus. |
| `self.app.menubar` | `Menu` | La barre de menus complète. |
| `self.app.status` | `StringVar` | Texte de la barre de statut (utilisez `.set("msg")` pour modifier). |
| `self.app.current_jwt_path` | `str\|None` | Chemin du fichier actuellement chargé, ou `None`. |
| `self.app.raw_jwt_content` | `str\|None` | Chaîne JWT brute (avant décodage), ou `None` si ce n'est pas un JWT. |
| `self.app.is_modified` | `bool` | Indique si le document a des modifications non sauvegardées. |
| `self.app.translations` | `dict` | Dictionnaire de traductions de l'application principale. |
| `self.app.t(key, **kwargs)` | `callable` | Rechercher une traduction principale pour la langue actuelle. |

#### Méthodes de l'Application

| Méthode | Description |
| :--- | :--- |
| `self.app.replace_word(start, end, new_value)` | Remplacer le texte entre deux indices, réapplique la coloration syntaxique. |
| `self.app.apply_syntax_highlighting()` | Réappliquer la coloration syntaxique de l'éditeur. |
| `self.app.clipboard_clear()` | Vider le presse-papiers système. |
| `self.app.clipboard_append(text)` | Ajouter du texte au presse-papiers système. |
| `self.app.update_idletasks()` | Traiter les mises à jour d'interface en attente. |

#### Événements Plugins

Les événements sont émis via `PluginManager.dispatch_event()` et reçus dans `on_event(self, event_name, data)` :

| Nom de l'événement | `data` | Quand |
| :--- | :--- | :--- |
| `ui_ready` | `None` | L'interface est entièrement construite (≈100ms après le démarrage). Meilleur moment pour ajouter des éléments de menu. |
| `jwt_loaded` | `None` | Un fichier JWT a été chargé et son payload décodé. |
| `file_closed` | `None` | Le fichier actuel a été fermé ou un nouveau document vide a été créé. |
| `language_changed` | `str` (code langue) | L'utilisateur a changé la langue de l'interface. |

---

### Résolution de chemins (Compatibilité PyInstaller)

Lorsque PyInstaller crée l'exécutable, les fichiers sont déplacés dans un dossier temporaire `_MEIPASS`. Les chemins standards via `__file__` ne fonctionneront pas. Deux approches sont disponibles :

#### Option 1 : Utiliser le module partagé `plugin_utils` (recommandé)

```python
from utils.plugin_utils import get_plugin_resource_path
import json

lang_path = get_plugin_resource_path("SDS plugins/policySign", "languages.json")
with open(lang_path, "r", encoding="utf-8") as f:
    translations = json.load(f)
```

**Arguments :**
- `plugin_folder_path` : chemin relatif depuis `plugins/` vers le dossier du plugin (ex : `"SDS plugins/date"`)
- `relative_path` : nom du fichier dans ce dossier (ex : `"languages.json"`)

#### Option 2 : Résolution inline (autonome)

```python
import json, os, sys

def get_plugin_resource_path(relative_path):
    """Obtient le chemin absolu vers une ressource du plugin, fonctionne en dev et avec PyInstaller."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    dev_path = os.path.join(current_dir, relative_path)

    if os.path.exists(dev_path):
        return dev_path

    try:
        base_path = sys._MEIPASS
        plugin_rel = os.path.join("plugins", "Dossier de votre Plugin", relative_path)
        return os.path.join(base_path, plugin_rel)
    except Exception:
        return dev_path

# Chargement des traductions
try:
    lang_path = get_plugin_resource_path("languages.json")
    if os.path.exists(lang_path):
        with open(lang_path, "r", encoding="utf-8") as f:
            translations = json.load(f)
    else:
        translations = {}
        print(f"Plugin: languages.json introuvable à {lang_path}")
except Exception as e:
    print(f"Plugin: Impossible de charger languages.json: {e}")
    translations = {}
```

---

### Internationalisation

Les plugins peuvent gérer leurs propres traductions via un fichier `languages.json` situé dans leur dossier.

**Structure de `languages.json` :**

```json
{
    "fr": {
        "mon_label": "Mon libellé",
        "mon_message": "Bonjour {name} !"
    },
    "en": {
        "mon_label": "My Label",
        "mon_message": "Hello {name}!"
    }
}
```

**Fonction de traduction** (à définir dans votre classe Plugin) :

```python
def t(self, key, **kwargs):
    lang = getattr(self.app, "current_language", "en")
    text = self.translations.get(lang, self.translations.get("en", {})).get(key, key)
    if kwargs:
        try:
            return text.format(**kwargs)
        except:
            return text
    return text
```

Utilisez `self.t("mon_message", name="Monde")` dans votre code.

**Pensez à réagir aux changements de langue** en implémentant `on_event("language_changed", data)` si votre plugin a des libellés de menu dynamiques.

---

### Template complet de Plugin

```python
import tkinter as tk
from tkinter import messagebox
import json
import os
import sys

def get_plugin_resource_path(relative_path):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    dev_path = os.path.join(current_dir, relative_path)
    if os.path.exists(dev_path):
        return dev_path
    try:
        base_path = sys._MEIPASS
        plugin_rel = os.path.join("plugins", "Standard plugins", "monPlugin", relative_path)
        return os.path.join(base_path, plugin_rel)
    except Exception:
        return dev_path

# Chargement des traductions
try:
    lang_path = get_plugin_resource_path("languages.json")
    with open(lang_path, "r", encoding="utf-8") as f:
        translations = json.load(f)
except Exception:
    translations = {}

class Plugin:
    def __init__(self, app):
        self.app = app
        self.translations = translations

    def t(self, key, **kwargs):
        lang = getattr(self.app, "current_language", "en")
        text = self.translations.get(lang, self.translations.get("en", {})).get(key, key)
        if kwargs:
            try:
                return text.format(**kwargs)
            except:
                return text
        return text

    def register(self):
        pass  # Utilisez on_event("ui_ready") pour les menus si nécessaire

    def on_event(self, event_name, data=None):
        if event_name == "ui_ready":
            if hasattr(self.app, 'tools_menu'):
                self.app.tools_menu.add_separator()
                self.app.tools_menu.add_command(
                    label=self.t("menu_label"),
                    command=self.run
                )
        elif event_name == "language_changed":
            pass  # Mettre à jour les libellés de menu ici

    def extend_context_menu(self, menu, event):
        menu.add_separator()
        menu.add_command(label=self.t("ctx_label"), command=self.run)

    def run(self):
        text = self.app.text.get("1.0", "end-1c")
        messagebox.showinfo("Plugin", f"Longueur du texte : {len(text)}")
```
