# Build helper for Windows
# Creates a venv, installs dependencies and PyInstaller, then builds a single exe

$venv = "$PSScriptRoot\.venv"
python -m venv $venv
& "$venv\Scripts\pip.exe" install --upgrade pip
& "$venv\Scripts\pip.exe" install --upgrade pip
& "$venv\Scripts\pip.exe" install -r requirements.txt pyinstaller Pillow

# If we have an SVG icon, try converting to ICO so the exe can use it.
# We use the Qt-based converter `convert_icon_qt.py` (avoids a Cairo runtime requirement).
if (Test-Path "assets\cursor_icon.svg") {
    & "$venv\Scripts\python.exe" convert_icon_qt.py
}

# Bundle whole assets folder
$add = "assets;assets"

# use an .ico for the exe if present (PyInstaller will be called with --icon when available)

# Build with PyInstaller. Include the assets folder so the SVG is bundled.
if (Test-Path "assets\app.ico") {
    & "$venv\Scripts\pyinstaller.exe" --name "AERO-AutoClicker" --onefile --windowed --add-data "$add" --icon "assets\app.ico" main.py
} else {
    & "$venv\Scripts\pyinstaller.exe" --name "AERO-AutoClicker" --onefile --windowed --add-data "$add" main.py
}

Write-Output "Build complete. See dist\AERO-AutoClicker.exe"