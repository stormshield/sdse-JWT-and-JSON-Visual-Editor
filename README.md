# JWT & JSON Visual Editor

**Version:** 2.0.7  
**Author:** Jérôme BLONDEL  
**Last Update:** 16/07/2026  
**Source:** [github.com/stormshield/sdse-JWT-and-JSON-Visual-Editor](https://github.com/stormshield/sdse-JWT-and-JSON-Visual-Editor)

## Screenshots

![Screenshot](screenshots/Screenshot.png)

## Description

**JWT & JSON Visual Editor** is a standalone graphical application developed in Python with Tkinter. It offers a comprehensive environment to visualize, edit, validate, and manipulate complex JSON structures as well as JWT (JSON Web Token) payloads.

The tool is designed to be lightweight, performant (even with large files), and easy to use, with a modern and responsive interface.

## Key Features

*   **Visualization & Editing:**
    *   Text editor with syntax highlighting for JSON.
    *   Automatic indentation and formatting ("Beautify").
    *   Zoom in/out on text.
    *   Toggleable Word wrap.
    *   **Dynamic Title:** The window title automatically adapts to show the type of file being edited (JSON or JWT).

*   **Structural Navigation:**
    *   **Tree View:** Explore the hierarchy of your JSON objects and quickly navigate to corresponding keys in the editor.
    *   Bidirectional synchronization between the tree and the editor.

*   **JWT (JSON Web Tokens) Support:**
    *   Automatic detection of JWT strings.
    *   Extraction and decoding of the payload (central part) without requiring a secret key (Base64URL decoding).

*   **Manipulation Tools:**
    *   **Search and Replace:** Optimized, modern dialogs with full features (Ctrl+F, Ctrl+H).
    *   **File Merging (Patching):** Intelligent recursive algorithm to merge a modification file into the current JSON (handling IDs in lists).
    *   **Schema Validation:** Validate your JSON against a schema (supports enumerations and types).
    *   **Context Menu Tools:** Generate IDs (ObjectId, UUID) and update date fields directly from the editor.
    *   **Certificate/LDAP Preview:** Right-click on a referenced ID to instantly preview the associated certificate details or LDAP configuration.
    *   **ID Reveal (AltGr):** Hold the AltGr key to temporarily replace all IDs with human-readable names (certificate CN or LDAP config name).

*   **Security & Certificates:**
    *   Visualization of X.509 certificate details (Subject CN, Issuer CN) present in JSON values (requires `cryptography` library).
    *   Export of certificates to `.cer` format.
    *   **JWT Certificate Extraction:** Extract public certificates from JWT headers.

*   **Ergonomics:**
    *   **Drag & Drop:** Drag and drop your files directly into the window (requires `tkinterdnd2`).
    *   **Internationalization:** Multi-language interface (FR, EN, ES, DE, IT) managed via a core `languages.json` file. Support for dynamic switching and automatic detection.
    *   **Undo/Redo:** Full Undo/Redo support (Ctrl+Z / Ctrl+Y).

*   **Extensibility (Plugins):**
    *   **Modular Architecture:** Expand functionality via Python plugins organized in categories: `Required`, `Standard`, and `SDS` (Specialized).
    *   **Decentralized Translations:** Each plugin manages its own translations via a local `languages.json` file for easier internationalization.
    *   **Specialized Tools:** Includes plugins like the **SDS Policy Signer** for signing JSON payloads with P12 certificates or Smart Cards (PKCS#11), and the **ID Reveal** for instant AltGr-based ID resolution.

### Included Plugins

Plugins shipped in the `plugins/` folder:

*   **Standard plugins**: Boolean toggle, Certificates viewer/extractor, Extractor (to `extract.json`), JSON Schema Generator
*   **SDS plugins**: Date updater, IDs generator & preview (certificate/LDAP), ID Reveal (AltGr), Import certificates into `certificateData`, P7B Builder (PKCS#7), Policy Signer (P12/Smart Card → signed JWT)

## Installation

### Prerequisites

*   Python 3.8 or higher recommended.

### Dependencies

For the full feature set (including all plugins), install the project dependencies:

```bash
pip install -r requirements.txt
```

You can also install only what you need via `pip`:

```bash
pip install cryptography tkinterdnd2 pyjwt python-pkcs11
```

*   **cryptography**: (Optional) For X.509 certificate management and visualization.
*   **tkinterdnd2**: (Optional) Adds file drag-and-drop support. The application works without it, but this feature will be disabled.
*   **pyjwt**: (Optional) Required by the **SDS Policy Signer** plugin (JWT signing).
*   **python-pkcs11**: (Optional) Required by the **SDS Policy Signer** plugin for Smart Card (PKCS#11) signature support.
*   **pyinstaller**: (Optional) Only required to build the standalone `.exe` (used by `build_exe.bat`).
*   **tkinter**: Normally included by default with Python on Windows.

## Usage

To launch the application, simply execute the script:

```bash
python "JWT & JSON Visual Editor.pyw"
```

### Languages

The language is automatically detected if the filename contains `(FR)` or `(EN)`.
You can also force the language at startup:
```bash
python script.pyw --lang en
```

### Keyboard Shortcuts

| Shortcut | Action |
| :--- | :--- |
| **Ctrl + S** | Save |
| **Ctrl + F** | Search |
| **Ctrl + H** | Replace |
| **Ctrl + Z** | Undo |
| **Ctrl + Y** | Redo |
| **Ctrl + Wheel** | Text Zoom |
| **Shift + Wheel** | Horizontal Scroll |
| **AltGr (hold)** | Reveal IDs as names (SDS IDs plugin) |

## Automation Scripts

The project includes two `.bat` scripts to simplify common tasks:

*   **`run_app.bat`**:
    *   **Universal Launcher**: Drag and drop any `.py` or `.pyw` file onto this script to run it.
    *   Automatically sets up the virtual environment if it's missing.
    *   Can create a Desktop shortcut for your application.
    *   Differentiates between GUI (`.pyw`) and Console (`.py`) scripts.

*   **`build_exe.bat`**:
    *   Compiles the application into a standalone binary using **PyInstaller**.
    *   Handles the entire build process including plugin integration and language resource packaging.
    *   The output is placed at the root of the project.
    *   Generates an **`install.bat`** script in the output folder for easy deployment.

---

## Changelog

### v2.0.7 — 16/07/2026

*   **SDS Policy Signer — Microsoft Certificate Store (CAPI/CNG) support:** Added capability to sign policies using a certificate from the Windows Certificate Store. It supports TPM-backed, smart card, and non-exportable keys natively, showing native Windows security prompts if required.
*   **Version bump:** Updated version number to 2.0.7.

### v2.0.6.1 — 16/07/2026

*   **SDS Policy Signer — Smart Card (PKCS#11) support:** Added capability to sign policies using a smart card. Users can specify a PKCS#11 middleware DLL, input their PIN, load, list and select certificates from the card.
*   **SDS Policy Signer — Certificate Metadata Display:** Added an eye button ("👁") next to the certificate selector to view all details (Serial Number, Issuer CN & DN, Validity Dates, Key Usage, Extended Key Usage) in a clean, scrollable popup, with all KU/EKU values fully translated. A permanent label displays the certificate's Serial Number directly under the dropdown.
*   **SDS Policy Signer — Stormshield Middleware shortcut:** Added a button to quickly target the Stormshield PKCS#11 DLL (`C:\Windows\System32\pkcs11CNG.dll`).
*   **SDS Policy Signer — Unified Settings:** Plugin parameters are stored directly in the main `settings.json` file.
*   **SDS Policy Signer — Signing compatibility:** Pre-hash data and use the standard `Mechanism.RSA_PKCS` to ensure compatibility with smart cards that do not support on-chip hashing.
*   **Version bump:** Updated version number to 2.0.6.1.
### v2.0.5 — 05/06/2026

*   **About dialog — Version bump:** Updated version number to 2.0.5 in the About dialog.
*   **About dialog — Source link:** The About dialog now displays a clickable hyperlink pointing to the project source repository on GitHub.

### v2.0.4 — 27/05/2026

*   **ID Reveal — Visual improvements:** Removed bold formatting from revealed IDs for better readability. Retained cyan color with dark background highlighting.
*   **ID Reveal — Syntax highlighting fix:** Fixed a bug where syntax highlighting was lost during ID reveal (incorrect method name `apply_syntax_highlighting` → `apply_syntax_highlight`, and text widget was disabled before highlighting was applied).
*   **ID Reveal — Scroll fix during reveal:** AltGr+Scroll no longer triggers zoom. During ID reveal, mouse wheel scrolling now correctly scrolls the document instead of changing zoom level.

### v2.0.3 — 26/05/2026

*   **New Plugin — ID Reveal (AltGr):** Hold the AltGr key to temporarily replace all hex IDs in the editor with human-readable names (certificate CN from `certificateData`, configuration name from `ldapData`). Revealed names are highlighted in bold cyan. The editor is read-only during reveal and the original content is fully restored on release.
*   **Certificate Preview by ID:** Right-click on an ID inside `certificateIds`, `certificateID`, `updateOnlyFromCAs`, `removeOnlyFromCAs`, `signatureKeyAuthorityId`, or `encryptionKeyAuthorityId` to display the associated certificate details (CN, Issuer, validity, serial number, SHA-256 fingerprint) with copy and `.cer` export options.
*   **LDAP Preview by ID:** Right-click on an ID inside `ldapAddressBookList` to display the associated LDAP configuration (name, address, port, protocol, username, base DN, depth, timeout, search attributes) with copy options.
*   **Multilingual support for new features:** All new plugins include translations in 5 languages (FR, EN, ES, DE, IT).

---
*Developed to simplify JSON configuration management and JWT debugging.*

***

# JWT & JSON Visual Editor

**Version :** 2.0.7  
**Auteur :** Jérôme BLONDEL  
**Dernière mise à jour :** 16/07/2026  
**Source :** [github.com/stormshield/sdse-JWT-and-JSON-Visual-Editor](https://github.com/stormshield/sdse-JWT-and-JSON-Visual-Editor)

## Description

**JWT & JSON Visual Editor** est une application graphique autonome (standalone) développée en Python avec Tkinter. Elle offre un environnement complet pour visualiser, éditer, valider et manipuler des structures JSON complexes ainsi que des payloads de jetons JWT (JSON Web Tokens).

L'outil est conçu pour être léger, performant (même avec de gros fichiers) et facile à utiliser, avec une interface moderne et réactive.

## Fonctionnalités Clés

*   **Visualisation & Édition :**
    *   Éditeur de texte avec coloration syntaxique pour JSON.
    *   Indentation automatique et formatage ("Beautify").
    *   Zoom in/out sur le texte.
    *   Retour à la ligne automatique (Word wrap) commutable.
    *   **Titre Dynamique :** Le titre de la fenêtre s'adapte automatiquement pour afficher le type de fichier édité (JSON ou JWT).

*   **Navigation Structurelle :**
    *   **Vue en Arbre (Tree View) :** Explorez la hiérarchie de vos objets JSON et naviguez rapidement vers les clés correspondantes dans l'éditeur.
    *   Synchronisation bidirectionnelle entre l'arbre et l'éditeur.

*   **Support JWT (JSON Web Tokens) :**
    *   Détection automatique des chaînes JWT.
    *   Extraction et décodage du payload (partie centrale) sans nécessiter la clé secrète (décodage Base64URL).

*   **Outils de Manipulation :**
    *   **Recherche et Remplacement :** Dialogues optimisés et modernes avec fonctionnalités complètes (Ctrl+F, Ctrl+H).
    *   **Fusion de Fichiers (Patching) :** Algorithme récursif intelligent pour fusionner un fichier de modifications dans le JSON actuel (gestion des IDs dans les listes).
    *   **Validation de Schéma :** Validez votre JSON contre un schéma (support des énumérations et types).
    *   **Outils Contextuels :** Génération d'identifiants (ObjectId, UUID) et mise à jour des champs date directement depuis l'éditeur.
    *   **Aperçu Certificat/LDAP :** Clic droit sur un ID référencé pour prévisualiser instantanément les détails du certificat associé ou la configuration LDAP.
    *   **Révélation d'IDs (AltGr) :** Maintenez la touche AltGr pour remplacer temporairement tous les IDs par des noms lisibles (CN du certificat ou nom de configuration LDAP).

*   **Sécurité & Certificats :**
    *   Visualisation des détails des certificats X.509 (CN Sujet, CN Émetteur) présents dans les valeurs JSON (requiert la librairie `cryptography`).
    *   Exportation des certificats au format `.cer`.
    *   **Extraction Certificat JWT :** Extraction des certificats publics présents dans les headers JWT.

*   **Ergonomie :**
    *   **Drag & Drop :** Glissez-déposez vos fichiers directement dans la fenêtre (nécessite `tkinterdnd2`).
    *   **Internationalisation :** Interface multilingue (FR, EN, ES, DE, IT) gérée via un fichier `languages.json` principal. Support du basculement à la volée et détection automatique.
    *   **Annuler/Rétablir :** Support complet du Undo/Redo (Ctrl+Z / Ctrl+Y).

*   **Extensibilité (Plugins) :**
    *   **Architecture Modulaire :** Possibilité d'étendre les fonctionnalités via des plugins Python organisés par catégories : `Required`, `Standard`, et `SDS` (Spécialisés).
    *   **Traductions Décentralisées :** Chaque plugin gère ses propres traductions via un fichier `languages.json` local, facilitant l'internationalisation.
    *   **Outils Spécialisés :** Inclut des outils comme le **SDS Policy Signer** pour signer des payloads JSON avec des certificats P12, et le **ID Reveal** pour la résolution instantanée d'IDs via AltGr.

### Plugins Inclus

Plugins fournis dans le dossier `plugins/` :

*   **Plugins Standard** : Bascule booléen, Certificats (visualisation/extraction), Extractor (vers `extract.json`), Générateur de schéma JSON
*   **Plugins SDS** : Mise à jour de date, Génération d'IDs & aperçu (certificat/LDAP), Révélation d'IDs (AltGr), Import de certificats dans `certificateData`, Générateur P7B (PKCS#7), Signature de politique (P12 → JWT signé)

## Installation

### Prérequis

*   Python 3.8 ou supérieur recommandé.

### Dépendances

Pour bénéficier de toutes les fonctionnalités (y compris tous les plugins), installez les dépendances du projet :

```bash
pip install -r requirements.txt
```

Vous pouvez aussi n’installer que ce dont vous avez besoin via `pip` :

```bash
pip install cryptography tkinterdnd2 pyjwt
```

*   **cryptography** : (Optionnel) Pour la gestion et visualisation des certificats X.509.
*   **tkinterdnd2** : (Optionnel) Ajoute le support du glisser-déposer de fichiers. L'application fonctionne sans, mais cette fonctionnalité sera désactivée.
*   **pyjwt** : (Optionnel) Requis par le plugin **SDS Policy Signer** (signature JWT).
*   **pyinstaller** : (Optionnel) Uniquement requis pour compiler l’exécutable `.exe` (utilisé par `build_exe.bat`).
*   **tkinter** : Normalement inclus par défaut avec Python sur Windows.

## Utilisation

Pour lancer l'application, exécutez simplement le script :

```bash
python "JWT & JSON Visual Editor.pyw"
```

### Langues

La langue est détectée automatiquement si le nom du fichier contient `(FR)` ou `(EN)`.
Vous pouvez aussi forcer la langue au démarrage :
```bash
python script.pyw --lang en
```

### Raccourcis Clavier

| Raccourci | Action |
| :--- | :--- |
| **Ctrl + S** | Sauvegarder |
| **Ctrl + F** | Rechercher |
| **Ctrl + H** | Remplacer |
| **Ctrl + Z** | Annuler |
| **Ctrl + Y** | Rétablir |
| **Ctrl + Molette** | Zoom Text |
| **Shift + Molette** | Scroll Horizontal |
| **AltGr (maintenu)** | Révéler les IDs sous forme de noms (plugin SDS IDs) |

## Scripts d'Automatisation

Le projet inclut plusieurs scripts `.bat` pour simplifier les tâches courantes :

*   **`run_app.bat`** :
    *   **Lanceur Universel** : Glissez et déposez n'importe quel fichier `.py` ou `.pyw` sur ce script pour le lancer.
    *   Configure automatiquement l'environnement virtuel s'il est manquant.
    *   Peut créer un raccourci sur le Bureau pour votre application.
    *   Différencie les scripts GUI (`.pyw`) et Console (`.py`).

*   **`build_exe.bat`** :
    *   Compile l'application en un exécutable autonome avec **PyInstaller**.
    *   Gère tout le processus de compilation incluant l'intégration des plugins et des ressources linguistiques.
    *   L'exécutable généré est placé à la racine du projet.
    *   Génère un script **`install.bat`** dans le dossier de sortie pour faciliter le déploiement.

---

## Changelog

### v2.0.7 — 16/07/2026

*   **Signataire de politique SDS — Support du magasin de certificats Microsoft (CAPI/CNG) :** Ajout de la possibilité de signer des politiques avec un certificat du magasin Windows. Supporte nativement les clés protégées par TPM, cartes à puce et clés non exportables, avec affichage des invites de sécurité Windows si nécessaire.
*   **Mise à jour de version :** Numéro de version mis à jour en 2.0.7.

### v2.0.6.1 — 16/07/2026

*   **Signataire de politique SDS — Support de carte à puce (PKCS#11) :** Ajout de la possibilité de signer des politiques avec une carte à puce. Les utilisateurs peuvent spécifier une DLL de middleware PKCS#11, saisir le code PIN, charger, lister et sélectionner des certificats de la carte.
*   **Signataire de politique SDS — Affichage des métadonnées du certificat :** Ajout d'un bouton œil ("👁") à côté du sélecteur de certificat pour visualiser tous les détails (Numéro de série, Émetteur CN & DN, Dates de validité, Key Usage, Extended Key Usage) dans une popup propre et défilante, avec traduction automatique des valeurs KU/EKU. Un label permanent affiche le numéro de série du certificat sous le sélecteur.
*   **Signataire de politique SDS — Raccourci Middleware Stormshield :** Ajout d'un bouton pour cibler rapidement la DLL PKCS#11 Stormshield (`C:\Windows\System32\pkcs11CNG.dll`).
*   **Signataire de politique SDS — Paramètres unifiés :** Les paramètres du plugin sont sauvegardés directement dans le fichier `settings.json` principal.
*   **Signataire de politique SDS — Compatibilité de signature :** Hachage des données côté client et utilisation du mécanisme standard `Mechanism.RSA_PKCS` pour assurer une compatibilité optimale avec les cartes qui ne supportent pas le hachage interne.
*   **Mise à jour de version :** Numéro de version mis à jour en 2.0.6.1.

### v2.0.5 — 05/06/2026

*   **Boîte « À propos » — Mise à jour de la version :** Numéro de version mis à jour en 2.0.5 dans la boîte « À propos ».
*   **Boîte « À propos » — Lien source :** La boîte « À propos » affiche désormais un lien cliquable pointant vers le dépôt source du projet sur GitHub.

### v2.0.4 — 27/05/2026

*   **Révélation d'IDs — Améliorations visuelles :** Suppression du formatage gras des IDs révélés pour une meilleure lisibilité. Couleur cyan conservée avec fond noir de surbrillance.
*   **Révélation d'IDs — Correction coloration syntaxique :** Correction d'un bug où la coloration syntaxique était perdue pendant la révélation (nom de méthode incorrect `apply_syntax_highlighting` → `apply_syntax_highlight`, et widget texte désactivé avant l'application de la coloration).
*   **Révélation d'IDs — Correction du scroll pendant la révélation :** AltGr+Scroll ne déclenche plus le zoom. Pendant la révélation, le scroll de la souris fait défiler correctement le document au lieu de changer le niveau de zoom.

### v2.0.3 — 26/05/2026

*   **Nouveau plugin — Révélation d'IDs (AltGr) :** Maintenez la touche AltGr pour remplacer temporairement tous les IDs hexadécimaux dans l'éditeur par des noms lisibles (CN du certificat depuis `certificateData`, nom de configuration depuis `ldapData`). Les noms révélés sont mis en surbrillance en gras cyan. L'éditeur est en lecture seule pendant la révélation et le contenu original est entièrement restauré au relâchement.
*   **Aperçu Certificat par ID :** Clic droit sur un ID dans `certificateIds`, `certificateID`, `updateOnlyFromCAs`, `removeOnlyFromCAs`, `signatureKeyAuthorityId` ou `encryptionKeyAuthorityId` pour afficher les détails du certificat associé (CN, émetteur, validité, numéro de série, empreinte SHA-256) avec options de copie et export `.cer`.
*   **Aperçu LDAP par ID :** Clic droit sur un ID dans `ldapAddressBookList` pour afficher la configuration LDAP associée (nom, adresse, port, protocole, utilisateur, base DN, profondeur, timeout, attributs de recherche) avec options de copie.
*   **Support multilingue des nouvelles fonctionnalités :** Tous les nouveaux plugins incluent des traductions en 5 langues (FR, EN, ES, DE, IT).

---
*Développé pour simplifier la gestion des configurations JSON et le débogage JWT.*

---
GPL License.