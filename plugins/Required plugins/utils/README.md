# Required Plugin Utilities

This folder contains shared utility modules required for the professional plugins of the **JWT & JSON Visual Editor**.

## 📄 `plugin_utils.py`

This module provides essential functions to ensure plugins work correctly across different execution environments (Development vs. Packaged EXE).

### `get_plugin_resource_path(plugin_folder_path, relative_path)`

This is the most critical function for plugin developers. It resolves the absolute path to a resource (like `languages.json`) whether the application is running as a Python script or as a PyInstaller executable.

**Usage Example:**
```python
from utils.plugin_utils import get_plugin_resource_path

# Resolve path for a language file
# "SDS plugins/policySign" is the relative path from the plugins/ root
lang_path = get_plugin_resource_path("SDS plugins/policySign", "languages.json")

with open(lang_path, "r", encoding="utf-8") as f:
    data = json.load(f)
```

### Why is this required?
When PyInstaller bundles the application, it moves all files to a temporary folder (`_MEIPASS`). Standard path resolution via `__file__` often fails or points to the wrong location in the build. This utility abstracts that complexity.

---

## 🇫🇷 Français

Ce dossier contient les modules utilitaires partagés requis pour les plugins professionnels du **JWT & JSON Visual Editor**.

### Utilité
Le script `plugin_utils.py` permet de résoudre les chemins de fichiers (ressources, images, json) de manière transparente, que l'application soit lancée via Python ou via l'exécutable `.exe` compilé.

**Exemple :**
Utilisez `get_plugin_resource_path` pour charger vos fichiers de langue afin de garantir la compatibilité PyInstaller.
