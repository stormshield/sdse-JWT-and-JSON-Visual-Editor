# SDS IDs Plugin / Plugin d'IDs SDS

## English
### Description
This plugin provides tools to generate unique identifiers, preview linked data, and instantly reveal ID references as human-readable names directly within the JSON editor.

### Features
- **Contextual Generation**: Offers ID generation when right-clicking on a value for a key named "id".
- **Multiple Formats**:
  - **Mongo-style**: 24-character hex string (timestamp + random).
  - **UUID**: Standard Version 4 UUID.
- **Certificate Preview**: Right-click on an ID inside `certificateIds`, `certificateID`, `updateOnlyFromCAs`, `removeOnlyFromCAs`, `signatureKeyAuthorityId`, `encryptionKeyAuthorityId` or `ldapAddressBookList` to display the associated certificate details (CN, Issuer, validity, serial number, SHA-256 fingerprint) with options to copy fields or save as `.cer`.
- **LDAP Preview**: Right-click on an ID inside `ldapAddressBookList` to display the associated LDAP configuration (name, address, port, protocol, base DN, timeout, search attributes) with options to copy fields.
- **ID Reveal (AltGr)**: Hold the **AltGr** key to temporarily replace all ID references in the editor with their corresponding human-readable names. Release AltGr to restore the original IDs.

### Usage

**ID Generation:**
1. Click on the value of an "id" field.
2. Right-click and navigate to "Generate ID".
3. Choose the desired format (mongo or uuid) to replace the existing value.

**Certificate / LDAP Preview:**
1. Right-click on an ID value within `certificateIds`, `certificateID`, `updateOnlyFromCAs`, `removeOnlyFromCAs`, `signatureKeyAuthorityId`, `encryptionKeyAuthorityId` or `ldapAddressBookList`.
2. Select "Show associated certificate" or "LDAP Preview" from the context menu.
3. A popup window displays the corresponding details fetched from `certificateData` or `ldapData`.

**ID Reveal:**
1. Open a JSON file containing `certificateData` and/or `ldapData` sections.
2. **Hold AltGr**: all hex IDs referenced throughout the JSON are instantly replaced by:
   - The **CN (Common Name)** extracted from the X.509 certificate (for `certificateData` entries)
   - The **configuration name** (for `ldapData` entries)
3. Revealed names are highlighted (bold, cyan on dark background) for easy identification.
4. The editor is read-only while revealing to prevent accidental edits.
5. **Release AltGr**: the original IDs are restored, along with cursor position and scroll state.

> **Note:** The `cryptography` library is required to extract CN from certificates. Without it, only LDAP names are resolved.

---

## Français
### Description
Ce plugin fournit des outils pour générer des identifiants uniques, prévisualiser les données liées, et révéler instantanément les IDs sous forme de noms lisibles directement dans l'éditeur JSON.

### Fonctionnalités
- **Génération Contextuelle** : Propose la génération d'ID lors d'un clic droit sur une valeur pour une clé nommée "id".
- **Formats Multiples** :
  - **Style Mongo** : Chaîne hexadécimale de 24 caractères (horodatage + aléatoire).
  - **UUID** : UUID standard de version 4.
- **Aperçu Certificat** : Clic droit sur un ID dans `certificateIds`, `certificateID`, `updateOnlyFromCAs`, `removeOnlyFromCAs`, `signatureKeyAuthorityId`, `encryptionKeyAuthorityId` ou `ldapAddressBookList` pour afficher les détails du certificat associé (CN, émetteur, validité, numéro de série, empreinte SHA-256) avec options de copie et de sauvegarde en `.cer`.
- **Aperçu LDAP** : Clic droit sur un ID dans `ldapAddressBookList` pour afficher la configuration LDAP associée (nom, adresse, port, protocole, base DN, timeout, attributs de recherche) avec options de copie. 
- **Révélation d'IDs (AltGr)** : Maintenez la touche **AltGr** enfoncée pour remplacer temporairement tous les IDs dans l'éditeur par leurs noms lisibles correspondants. Relâchez AltGr pour restaurer les IDs originaux.

### Utilisation

**Génération d'ID :**
1. Cliquez sur la valeur d'un champ "id".
2. Faites un clic droit et allez dans "Générer un ID".
3. Choisissez le format souhaité (mongo ou uuid) pour remplacer la valeur existante.

**Aperçu Certificat / LDAP :**
1. Faites un clic droit sur une valeur d'ID dans `certificateIds`, `certificateID`, `updateOnlyFromCAs`, `removeOnlyFromCAs`, `signatureKeyAuthorityId`, `encryptionKeyAuthorityId` ou `ldapAddressBookList`.
2. Sélectionnez "Afficher le certificat associé" ou "Aperçu LDAP" dans le menu contextuel.
3. Une fenêtre popup affiche les détails correspondants récupérés depuis `certificateData` ou `ldapData`.

**Révélation d'IDs :**
1. Ouvrez un fichier JSON contenant des sections `certificateData` et/ou `ldapData`.
2. **Maintenez AltGr** : tous les IDs hexadécimaux référencés dans le JSON sont instantanément remplacés par :
   - Le **CN (Common Name)** extrait du certificat X.509 (pour les entrées `certificateData`)
   - Le **nom de configuration** (pour les entrées `ldapData`)
3. Les noms révélés sont mis en surbrillance (gras, cyan sur fond sombre) pour une identification facile.
4. L'éditeur est en lecture seule pendant la révélation pour éviter toute modification accidentelle.
5. **Relâchez AltGr** : les IDs originaux sont restaurés, ainsi que la position du curseur et le défilement.

> **Note :** La bibliothèque `cryptography` est nécessaire pour extraire le CN des certificats. Sans elle, seuls les noms LDAP sont résolus.

