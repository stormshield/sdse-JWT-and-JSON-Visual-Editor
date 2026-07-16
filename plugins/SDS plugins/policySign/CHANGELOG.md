# Changelog

## 2026-07-16 (v2.0.6.1)
- Added smart card (PKCS#11) signature support.
- Added input fields for middleware DLL path and card PIN code.
- Added dropdown to list and select active certificates from the card.
- Added a detail eye button ("👁") next to the certificate selector which displays all parsed certificate metadata (Serial Number, Subject CN, Label, Issuer CN & DN, Validity Dates, Key Usage, and Extended Key Usage) in a clean, scrollable pop-up window, with KU and EKU values fully translated into the active UI language. A permanent label displays the selected certificate's Serial Number directly on the main UI.
- Added a shortcut button to quickly set the DLL path to the Stormshield middleware (`C:\Windows\System32\pkcs11CNG.dll`).
- Integrated settings storage directly into the main application's `settings.json` file.
- Optimized signing compatibility by pre-hashing the DigestInfo in Python and using standard `Mechanism.RSA_PKCS` to support smart cards without on-chip hashing.

## 2026-02-07
- Added checkbox to include or omit signer certificate (x5c) in JWT header; default is off.
- Added drag and drop support for .p12/.pfx selection.
- Updated translations and documentation.
