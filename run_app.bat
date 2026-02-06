@echo off
setlocal EnableDelayedExpansion

:: ============================================================================
:: [EN] UNIVERSAL LAUNCHER
:: This script acts as a wrapper to run Python scripts within a specific
:: virtual environment.
::
:: USAGE:
:: 1. Drag and drop any .py or .pyw file onto this batch file.
:: 2. Or run it from the command line: run_app.bat <script_to_run>
::
:: AUTO-SETUP:
:: - Creates a virtual environment (.venv) if missing.
:: - Installs dependencies from 'requirements.txt' if present.
:: - Checks for an icon (.ico) in the folder to assign to the shortcut.
:: - Prompts to create a Desktop shortcut for the dragged script.
::
:: [FR] LANCEUR UNIVERSEL
:: Ce script sert d'enveloppe pour exécuter des scripts Python dans un
:: environnement virtuel spécifique.
::
:: UTILISATION :
:: 1. Glissez et déposez n'importe quel fichier .py ou .pyw sur ce fichier.
:: 2. Ou lancez-le depuis la ligne de commande : run_app.bat <script_a_lancer>
::
:: AUTO-CONFIG :
:: - Crée un environnement virtuel (.venv) s'il est absent.
:: - Installe les dépendances via 'requirements.txt' si présent.
:: - Cherche une icône (.ico) dans le dossier pour le raccourci.
:: - Propose de créer un raccourci Bureau pour le script déposé.
:: ============================================================================

set "VENV_NAME=.venv"
set "REQ_FILE=requirements.txt"

:: 1. TARGET FILE ANALYSIS
set "TARGET_SCRIPT=%~f1"
set "SCRIPT_NAME=%~nx1"
set "SCRIPT_NAME_NOEXT=%~n1"
set "FILE_EXT=%~x1"
set "LAUNCHER_PATH=%~f0"

title Launcher : !SCRIPT_NAME!

:: 2. INPUT VERIFICATION
if "!TARGET_SCRIPT!"=="" (
    echo [ERROR] No file provided.
    echo [INFO] Drag and drop a script to launch it.
    pause
    exit /b 1
)

:: 3. ENVIRONMENT SETUP
if not exist "%VENV_NAME%" (
    echo [SETUP] Creating venv...
    python -m venv "%VENV_NAME%"
)

if exist "%REQ_FILE%" (
    "%VENV_NAME%\Scripts\python.exe" -m pip install --upgrade pip -q >nul 2>&1
    "%VENV_NAME%\Scripts\python.exe" -m pip install -r "%REQ_FILE%" -q
)

:: --------------------------------------------------------
:: 4. ICON MANAGEMENT
:: --------------------------------------------------------
set "ICON_PATH=%SystemRoot%\System32\shell32.dll,238"
for %%I in ("%~dp0*.ico") do (
    set "ICON_PATH=%%~fI"
    goto :ICON_FOUND
)
:ICON_FOUND

:: --------------------------------------------------------
:: 5. SHORTCUT CREATION PROMPT (Yes by Default)
:: --------------------------------------------------------
set "SHORTCUT_PATH=%USERPROFILE%\Desktop\!SCRIPT_NAME_NOEXT!.lnk"

:: Only ask if the shortcut does NOT exist yet
if not exist "!SHORTCUT_PATH!" (
    echo.
    echo --------------------------------------------------------
    
    :: UX TRICK: Default response is "Y"
    set "USER_CHOICE=Y"
    
    :: Prompt the user (User sees [Y/n])
    set /p "USER_CHOICE=[QUESTION] Create a shortcut on the Desktop? [Y/n] : "
    
    :: If user types 'n' or 'N', we skip
    if /I "!USER_CHOICE!"=="N" (
        echo [INFO] No shortcut created.
    ) else (
        echo [INSTALLATION] Creating shortcut...
        
        (
            echo Set oWS = WScript.CreateObject^("WScript.Shell"^)
            echo sLinkFile = "!SHORTCUT_PATH!"
            echo Set oLink = oWS.CreateShortcut^(sLinkFile^)
            echo oLink.TargetPath = "!LAUNCHER_PATH!"
            echo oLink.Arguments = Chr^(34^) ^& "!TARGET_SCRIPT!" ^& Chr^(34^)
            echo oLink.Description = "Launch !SCRIPT_NAME!"
            echo oLink.IconLocation = "!ICON_PATH!"
            echo oLink.WorkingDirectory = "%~dp0"
            echo oLink.Save
        ) > "%TEMP%\CreateShortcut.vbs"

        cscript //nologo "%TEMP%\CreateShortcut.vbs"
        del "%TEMP%\CreateShortcut.vbs"
        
        echo [SUCCESS] Shortcut created!
        timeout /t 1 >nul
    )
)

:: 6. THE CONTROLLER (GUI vs Console Mode)
if /I "!FILE_EXT!"==".pyw" (
    goto MODE_GUI
) else (
    goto MODE_CONSOLE
)

:: ========================================================
:MODE_GUI
:: ========================================================
start "" "%VENV_NAME%\Scripts\pythonw.exe" "!TARGET_SCRIPT!"
exit

:: ========================================================
:MODE_CONSOLE
:: ========================================================
echo.
echo [CONSOLE MODE] Launching !SCRIPT_NAME!
echo --------------------------------------------------------

"%VENV_NAME%\Scripts\python.exe" "!TARGET_SCRIPT!"
set EXIT_CODE=%errorlevel%

echo.
echo --------------------------------------------------------
if %EXIT_CODE% neq 0 (
    echo [END] Stopped with ERROR (Code: %EXIT_CODE%)
) else (
    echo [END] Execution finished.
)
echo --------------------------------------------------------
pause
exit