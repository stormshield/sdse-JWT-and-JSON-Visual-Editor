# Certificates Plugin / Plugin de Certificats

## English
### Description
This plugin allows users to extract and view digital certificates directly from JWT headers or base64 encoded strings within the editor.

### Features
- **Extract from JWT**: Available in the "Tools" menu when a JWT is loaded. It extracts the `x5c` certificate chain from the header.
- **Contextual Viewer**: Right-click on any base64 string that looks like a certificate to view its details.
- **Certificate Details**: Displays Common Name (Subject/Issuer), Serial Number, Validity dates, and SHA-256 Fingerprint.
- **Export**: Ability to copy certificate fields to the clipboard or save the certificate as a `.cer` file.

### Usage
1. Open a JWT file or paste a base64 encoded certificate.
2. Go to `Tools > Extract Certificate` or right-click on the certificate string.
3. View or export the details as needed.

---

## Français
### Description
Ce plugin permet aux utilisateurs d'extraire et de visualiser des certificats numériques directement à partir des en-têtes JWT ou de chaînes encodées en base64 dans l'éditeur.

### Fonctionnalités
- **Extraction depuis JWT** : Disponible dans le menu "Outils" lorsqu'un JWT est chargé. Il extrait la chaîne de certificats `x5c` de l'en-tête.
- **Visionneuse Contextuelle** : Faites un clic droit sur n'importe quelle chaîne base64 ressemblant à un certificat pour voir ses détails.
- **Détails du Certificat** : Affiche le Common Name (Sujet/Émetteur), le numéro de série, les dates de validité et l'empreinte SHA-256.
- **Exportation** : Possibilité de copier les champs du certificat dans le presse-papiers ou d'enregistrer le certificat sous forme de fichier `.cer`.

### Utilisation
1. Ouvrez un fichier JWT ou collez un certificat encodé en base64.
2. Allez dans `Outils > Extraire le certificat` ou faites un clic droit sur la chaîne du certificat.
3. Visualisez ou exportez les détails selon vos besoins.
