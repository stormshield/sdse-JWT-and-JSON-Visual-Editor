# SDS – P7B Builder (certificates)

Ce plugin ajoute un outil GUI pour charger plusieurs certificats (`.cer/.crt/.pem/.der`) et générer un PKCS#7 « degenerate » en sortie (`.p7b`).

## Utilisation

- Menu **Tools** → **SDS - Générer un P7B (certificats)**
- Ajouter des certificats via **Ajouter…**
- Ou glisser-déposer les fichiers dans la zone prévue (si Drag & Drop activé)
- Choisir le fichier de sortie via **Parcourir…** (nom de fichier libre)
- Cliquer sur **Générer**

## Drag & Drop

Le drag & drop repose sur `tkinterdnd2`.
- Si l’application a été lancée sans TkinterDnD (ou si `tkinterdnd2` n’est pas installé), le plugin reste utilisable mais sans DnD.

## Dépendances

- `cryptography` (pour lire les certificats X.509 et sérialiser en PKCS#7)
- `tkinterdnd2` (optionnel, pour le drag & drop)
