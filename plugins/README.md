# Development of Plugins for JWT & JSON Visual Editor

This folder `plugins/` allow to extend the application features without modifying the core code (`.pyw`).

---

## 🇬🇧 English Guide

### How it works

At startup, the application **recursively** scans this folder and automatically loads any file starting with `plugin_` (including those in subdirectories).

**Folder Structure:**
You can organize plugins in subdirectories for better organization:
```
plugins/
├── plugin_utils.py          # Optional: Shared utilities
├── SDS plugins/
│   ├── date/
│   │   ├── plugin_SDS_date.py
│   │   └── languages.json
│   └── ids/
│       ├── plugin_SDS_ids.py
│       └── languages.json
└── Required plugins/
    └── certificates/
        ├── plugin_certificates.py
        └── languages.json
```

**⚠️ Important:** If your plugin loads local resources (like `languages.json`), see the **Internationalization** section below for PyInstaller compatibility.

### Step 1: Create the file
Create a new Python file, e.g., `plugin_example.py`.

### Step 2: Basic Structure
Each plugin must define a `Plugin` class with two mandatory methods:
1.  `__init__(self, app)`: To initialize your plugin.
2.  `register(self)`: To add menus or buttons at startup.

```python
import tkinter as tk
from tkinter import messagebox

class Plugin:
    def __init__(self, app):
        self.app = app  # 'app' is the main application instance

    def register(self):
        # This is where we hook into the UI
        pass
```

### Step 3: Concrete Examples

#### Example A: Add a button to the "Tools" menu

```python
    def register(self):
        # Adds a "Say Hello" option to the Tools menu
        self.add_tool_menu_item("Say Hello", self.say_hello)

    def say_hello(self):
        # This function is called when the menu item is clicked
        messagebox.showinfo("Hi", "Hello from my plugin!")

    def add_tool_menu_item(self, label, command):
        """ Helper function to add to the existing Tools menu """
        # Check if 'tools_menu' exists in the app
        if hasattr(self.app, 'tools_menu'):
            self.app.tools_menu.add_command(label=label, command=command)
```

#### Example B: Add an option to the Right-Click (Context) Menu

To add an option when right-clicking in the editor, define the special method `extend_context_menu`.

```python
    def extend_context_menu(self, menu, event):
        """
        Called every time the user right-clicks.
        'menu' is the context menu object about to be shown.
        """
        # Add a separator for better UI
        menu.add_separator()
        # Add our custom command
        menu.add_command(label="My Right-Click Action", command=self.my_action)

    def my_action(self):
        print("Right-click action triggered!")
```

#### Example C: Read and Modify JSON Text

Everything happens via `self.app.text`. This is the main text editor widget.

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
```

### Useful API (What you can use)

*   `self.app.root`: The main window.
*   `self.app.text`: The text editor (Tkinter Text widget).
*   `self.app.tree`: The tree view on the left (TreeView).
*   `self.app.current_language`: Current language code ('fr' or 'en').

### Internationalization
Plugins can manage their own translations using a `languages.json` file in their directory.

**⚠️ Important for PyInstaller Compatibility:**
When loading resources (like `languages.json`), you must use a special function to ensure the plugin works both in development mode and when packaged as an executable.

```python
import json
import os
import sys

def get_plugin_resource_path(relative_path):
    """Get absolute path to plugin resource, works for dev and for PyInstaller."""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
        # Replace with your plugin's actual path from the plugins/ folder
        plugin_rel = os.path.join("plugins", "Your Plugin Folder", relative_path)
        return os.path.join(base_path, plugin_rel)
    except Exception:
        # In development, use the directory of this file
        current_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(current_dir, relative_path)

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
    import traceback
    traceback.print_exc()
    translations = {}
```

**Example paths to use in `get_plugin_resource_path()`:**
- For `plugins/SDS plugins/date/`: use `"SDS plugins", "date"`
- For `plugins/Required plugins/certificates/`: use `"Required plugins", "certificates"`
- For `plugins/Standard plugins/boolean/`: use `"Standard plugins", "boolean"`

Then use `self.app.current_language` to pick the right string from your translations dictionary.

---

## 🇫🇷 Guide Français

### Comment ça marche ?

Au démarrage de l'application, tout fichier présent dans ce dossier dont le nom commence par `plugin_` sera automatiquement chargé **de manière récursive** (y compris ceux dans les sous-dossiers).

**Structure des dossiers :**
Vous pouvez organiser les plugins dans des sous-dossiers pour une meilleure organisation :
```
plugins/
├── plugin_utils.py          # Optionnel : Utilitaires partagés
├── SDS plugins/
│   ├── date/
│   │   ├── plugin_SDS_date.py
│   │   └── languages.json
│   └── ids/
│       ├── plugin_SDS_ids.py
│       └── languages.json
└── Required plugins/
    └── certificates/
        ├── plugin_certificates.py
        └── languages.json
```

**⚠️ Important :** Si votre plugin charge des ressources locales (comme `languages.json`), consultez la section **Internationalisation** ci-dessous pour la compatibilité PyInstaller.

### Étape 1 : Créer le fichier
Créez un nouveau fichier Python, par exemple `plugin_exemple.py`.

### Étape 2 : La structure de base
Chaque plugin doit contenir une classe `Plugin` avec deux méthodes obligatoires :
1.  `__init__(self, app)` : Pour initialiser votre plugin.
2.  `register(self)` : Pour ajouter vos menus ou boutons au démarrage.

```python
import tkinter as tk
from tkinter import messagebox

class Plugin:
    def __init__(self, app):
        self.app = app  # 'app' est l'application principale (le chef d'orchestre)

    def register(self):
        # C'est ici qu'on ajoute des choses à l'interface
        pass
```

### Étape 3 : Exemples Concrets

#### Exemple A : Ajouter un bouton dans le menu "Outils"

```python
    def register(self):
        # Ajoute une option "Dire Bonjour" dans le menu Outils
        self.add_tool_menu_item("Dire Bonjour", self.say_hello)

    def say_hello(self):
        # Cette fonction est appelée quand on clique sur le menu
        messagebox.showinfo("Coucou", "Bonjour depuis mon plugin !")

    def add_tool_menu_item(self, label, command):
        """ Petite fonction utilitaire pour ajouter au menu Outils existant """
        # On vérifie si le menu 'tools_menu' existe dans l'application
        if hasattr(self.app, 'tools_menu'):
            self.app.tools_menu.add_command(label=label, command=command)
```

#### Exemple B : Ajouter une option au Clic Droit (Menu Contextuel)

Pour ajouter une option quand on fait un clic droit dans l'éditeur, il faut utiliser la méthode spéciale `extend_context_menu`.

```python
    def extend_context_menu(self, menu, event):
        """
        Appelé à chaque fois que l'utilisateur fait un clic droit.
        'menu' est le menu contextuel qui va s'afficher.
        """
        # On ajoute un séparateur pour faire joli
        menu.add_separator()
        # On ajoute notre commande
        menu.add_command(label="Mon Action Clic Droit", command=self.mon_action)

    def mon_action(self):
        print("Action du clic droit déclenchée !")
```

#### Exemple C : Lire et Modifier le texte JSON

Tout se passe via `self.app.text`. C'est l'éditeur de texte principal.

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
```

### API Utile (Ce que vous pouvez utiliser)

*   `self.app.root` : La fenêtre principale.
*   `self.app.text` : L'éditeur de texte (widget Tkinter Text).
*   `self.app.tree` : L'arbre à gauche (TreeView).
*   `self.app.current_language` : La langue actuelle ('fr' ou 'en').

### Internationalisation
Les plugins peuvent gérer leurs propres traductions via un fichier `languages.json` situé dans leur dossier.

**⚠️ Important pour la compatibilité PyInstaller :**
Lors du chargement de ressources (comme `languages.json`), vous devez utiliser une fonction spéciale pour garantir que le plugin fonctionne à la fois en mode développement et lorsqu'il est packagé en exécutable.

```python
import json
import os
import sys

def get_plugin_resource_path(relative_path):
    """Obtient le chemin absolu vers une ressource du plugin, fonctionne en dev et avec PyInstaller."""
    try:
        # PyInstaller crée un dossier temporaire et stocke le chemin dans _MEIPASS
        base_path = sys._MEIPASS
        # Remplacez avec le chemin réel de votre plugin depuis le dossier plugins/
        plugin_rel = os.path.join("plugins", "Dossier de votre Plugin", relative_path)
        return os.path.join(base_path, plugin_rel)
    except Exception:
        # En développement, utilise le dossier de ce fichier
        current_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(current_dir, relative_path)

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
    import traceback
    traceback.print_exc()
    translations = {}
```

**Exemples de chemins à utiliser dans `get_plugin_resource_path()` :**
- Pour `plugins/SDS plugins/date/` : utilisez `"SDS plugins", "date"`
- Pour `plugins/Required plugins/certificates/` : utilisez `"Required plugins", "certificates"`
- Pour `plugins/Standard plugins/boolean/` : utilisez `"Standard plugins", "boolean"`

Utilisez ensuite `self.app.current_language` pour sélectionner la bonne chaîne depuis votre dictionnaire de traductions.
