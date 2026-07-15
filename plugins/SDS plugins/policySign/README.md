# SDS Policy Signer Plugin / Plugin de Signature de Politique SDS

## English
### Description
A comprehensive tool for signing Stormshield Data Security (SDS) policy files using P12 certificates or Smart Cards (PKCS#11) to create signed JWTs.

### Features
- **Graphic Interface**: Dedicated window to manage signing parameters.
- **P12 Support**: Load `.p12` or `.pfx` files with password protection.
- **Smart Card / PKCS#11 Support**: Interface with hardware security modules (HSMs) or smart cards using a vendor PKCS#11 middleware DLL. Load and select certificates directly from the card using a PIN.
- **Signing Algorithms**: Selection between RS256 and PS256.
- **Automatic Updates**: Option to automatically update policy dates before signing.
- **Signer Certificate in JWT**: Option to include or omit the signer certificate in the JWT header.
- **Deployment Script**: Generates an `install-policy.bat` file to automate the deployment of the signed policy and certificates to standard SDS directories.
- **Certificate Extraction**: Optional extraction of existing certificates from the JSON policy.
- **Drag & Drop**: Drop a `.p12` or `.pfx` file directly into the signer window when using the P12 method.

### Usage
1. Open the SDS policy JSON file in the editor.
2. Go to `Tools > SDS Policy Signer`.
3. Choose your signing method:
   - **P12 / PFX File**: Select your P12 file, enter its password.
   - **Smart Card (PKCS#11)**: Select the PKCS#11 middleware DLL (e.g. `eTPKCS11.dll` or `opensc-pkcs11.dll`), enter your PIN code, click "Load Certificates", and select the desired certificate from the dropdown list.
4. Configure output options.
5. Click "Sign" to generate the signed JWT and deployment folder.

---

## Français
### Description
Un outil complet pour signer les fichiers de politique Stormshield Data Security (SDS) à l'aide de certificats P12 ou de cartes à puce (PKCS#11) pour créer des JWT signés.

### Fonctionnalités
- **Interface Graphique** : Fenêtre dédiée pour gérer les paramètres de signature.
- **Support P12** : Chargement de fichiers `.p12` ou `.pfx` avec protection par mot de passe.
- **Support Carte à puce / PKCS#11** : Interface avec les cartes à puce et modules HSM en utilisant la DLL du middleware PKCS#11 fourni par le fabricant. Permet de charger et de choisir un certificat de la carte à l'aide du code PIN.
- **Algorithmes de Signature** : Choix entre RS256 et PS256.
- **Mises à jour Automatiques** : Option pour mettre à jour automatiquement les dates de politique avant la signature.
- **Certificat du signataire dans le JWT** : Option pour inclure ou omettre le certificat du signataire dans l'en-tête JWT.
- **Script de Déploiement** : Génère un fichier `install-policy.bat` pour automatiser le déploiement de la politique signée et des certificats vers les répertoires standards de SDS.
- **Extraction de Certificats** : Extraction optionnelle des certificats existants depuis la politique JSON.
- **Glisser-déposer** : Déposez un fichier `.p12` ou `.pfx` directement dans la fenêtre du plugin en mode P12.

### Utilisation
1. Ouvrez le fichier JSON de politique SDS dans l'éditeur.
2. Allez dans `Outils > Signer la politique SDS`.
3. Choisissez votre méthode de signature :
   - **Fichier P12 / PFX** : Sélectionnez votre fichier P12 et saisissez son mot de passe.
   - **Carte à puce (PKCS#11)** : Sélectionnez la DLL PKCS#11 du middleware (ex. `eTPKCS11.dll` ou `opensc-pkcs11.dll`), entrez le code PIN, cliquez sur "Charger les certificats", et sélectionnez le certificat souhaité dans la liste déroulante.
4. Configurez les options de sortie.
5. Cliquez sur "Signer" pour générer le JWT signé et le dossier de déploiement.
