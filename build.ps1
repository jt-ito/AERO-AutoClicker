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

# use an .ico for the exe if present
$iconArg = ""
if (Test-Path "assets\app.ico") {
    $iconArg = "--icon assets\\app.ico"
}

# Build with PyInstaller. Include the assets folder so the SVG is bundled.
if ($iconArg -ne "") {
    & "$venv\Scripts\pyinstaller.exe" --onefile --windowed --add-data $add $iconArg main.py
} else {
    & "$venv\Scripts\pyinstaller.exe" --onefile --windowed --add-data $add main.py
}

Write-Output "Build complete. See dist\main.exe (name will match script)."