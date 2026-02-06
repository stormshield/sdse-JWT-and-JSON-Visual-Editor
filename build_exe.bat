:: ============================================================================
:: Script Name: build_exe.bat
:: Description: Automates the build process for "JWT & JSON Visual Editor".
::              Automatise le processus de compilation pour "JWT & JSON Visual Editor".
::
:: [ENGLISH]
:: Usage:
:: 1. Ensure Python 3.x is installed and added to your system PATH.
:: 2. Checks for a ".venv" virtual environment. If missing, it creates one and
::    installs dependencies from "requirements.txt".
:: 3. Builds the executable using PyInstaller in "onedir" mode (folder based).
:: 4. Cleans up temporary "build" folders and ".spec" files.
:: 5. The final executable is located at the root of the project.
::
:: [FRANÇAIS]
:: Utilisation :
:: 1. Assurez-vous que Python 3.x est installé et ajouté au PATH système.
:: 2. Vérifie la présence de l'environnement virtuel ".venv". S'il est absent,
::    il le crée et installe les dépendances depuis "requirements.txt".
:: 3. Construit l'exécutable avec PyInstaller en mode "onedir" (dossier).
:: 4. Nettoie les dossiers temporaires "build" et les fichiers ".spec".
:: 5. L'exécutable final se trouve à la racine du projet.
:: ============================================================================

@echo off
setlocal
cd /d "%~dp0"

echo ===================================================
echo Building executable...
echo ===================================================

:: 1. Check and create environment if necessary
if not exist ".venv" (
    echo .venv folder not found. Creating environment...
    
    :: Check if Python is available
    python --version >nul 2>&1
    if %errorlevel% neq 0 (
        echo Python is not installed or not in PATH.
        pause
        exit /b 1
    )

    python -m venv .venv
    if %errorlevel% neq 0 (
        echo Error creating venv.
        pause
        exit /b 1
    )
    
    call .venv\Scripts\activate
    
    echo Updating pip and installing dependencies...
    python -m pip install --upgrade pip
    if exist "requirements.txt" (
        pip install -r requirements.txt
    ) else (
        echo WARNING: requirements.txt missing.
    )
) else (
    :: 2. Activate existing environment
    if exist ".venv\Scripts\activate.bat" (
        call .venv\Scripts\activate
    ) else (
        echo Error: .venv folder exists but activation script not found.
        pause
        exit /b 1
    )
)

:: 3. Launch PyInstaller
echo Launching PyInstaller...
pyinstaller --noconfirm --onedir --windowed --noupx ^
    --add-data "plugins;plugins" ^
    --add-data "languages.json;." ^
    --add-data ".venv\Lib\site-packages\tkinterdnd2\tkdnd;tkdnd" ^
    --add-data ".venv\Lib\site-packages\tkinterdnd2;tkinterdnd2" ^
    --hidden-import "jwt" ^
    --hidden-import "getpass" ^
    --hidden-import "cryptography" ^
    --hidden-import "tkinterdnd2" ^
    --hidden-import "tkinter.scrolledtext" ^
    --collect-all "jwt" ^
    --collect-all "cryptography" ^
    --icon "JWT and JSON Visual Editor.ico" ^
    "JWT and JSON Visual Editor.pyw"

if %errorlevel% neq 0 (
    echo Error creating executable.
    pause
    exit /b 1
)




echo ===================================================
echo Creating ZIP archive...
echo ===================================================

set "ZIP_NAME=JWT and JSON Visual Editor.zip"
set "FOLDER_TO_ZIP=dist\JWT and JSON Visual Editor"

:: Delete existing zip if it exists
if exist "%ZIP_NAME%" del /q "%ZIP_NAME%"

:: Check for 7-Zip
if exist "C:\Program Files\7-Zip\7z.exe" (
    echo Using 7-Zip...
    "C:\Program Files\7-Zip\7z.exe" a -tzip "%ZIP_NAME%" ".\%FOLDER_TO_ZIP%\*"
) else (
    echo 7-Zip not found, using PowerShell...
    powershell -Command "Compress-Archive -Path '%FOLDER_TO_ZIP%\*' -DestinationPath '%ZIP_NAME%' -Force"
)

if %errorlevel% equ 0 (
    echo ZIP created successfully: %ZIP_NAME%
    
    echo.
    echo ===================================================
    echo Cleaning up dist folder...
    echo ===================================================
    if exist "dist" (
        rmdir /s /q "dist"
        echo 'dist' folder deleted.
    )
    if exist "build" (
        rmdir /s /q "build"
        echo 'build' folder deleted.
    )
    if exist "*.spec" (
        del /q "*.spec"
        echo .spec files deleted.
    )
) else (
    echo.
    echo ERROR: Failed to create ZIP archive.
)

echo.
echo ===================================================
echo Done! The package is ready: %ZIP_NAME%
echo ===================================================
pause
