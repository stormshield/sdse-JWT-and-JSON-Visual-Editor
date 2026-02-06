# SDS Import Certs Plugin / Plugin d'Importation de Certificats SDS

## English
### Description
Simplifies the process of adding digital certificates to the `certificateData` section of an SDS policy JSON file.

### Features
- **File Import**: Supports `.cer`, `.crt`, `.pem`, and `.der` files.
- **Auto-Encoding**: Automatically converts binary certificates to base64 and strips PEM headers.
- **ID Generation**: Generates a unique 24-char ID for each imported certificate.
- **JSON Integration**: Appends the new certificate to the `certificateData` list and highlights the change in the editor.

### Usage
1. Right-click on a line containing "certificateData" in the JSON editor.
2. Select "Import certificate".
3. Choose the certificate file from your computer.

---

## Français
### Description
Simplifie le processus d'ajout de certificats numériques à la section `certificateData` d'un fichier JSON de politique SDS.

### Fonctionnalités
- **Importation de Fichiers** : Supporte les fichiers `.cer`, `.crt`, `.pem` et `.der`.
- **Auto-encodage** : Convertit automatiquement les certificats binaires en base64 et supprime les en-têtes PEM.
- **Génération d'ID** : Génère un ID unique de 24 caractères pour chaque certificat importé.
- **Intégration JSON** : Ajoute le nouveau certificat à la liste `certificateData` et met en évidence le changement dans l'éditeur.

### Utilisation
1. Faites un clic droit sur une ligne contenant "certificateData" dans l'éditeur JSON.
2. Sélectionnez "Importer un certificat".
3. Choisissez le fichier de certificat sur votre ordinateur.
