# Autoclicker (Windows)

Small autoclicker with a modern PySide6 UI that targets a specific application window.

Features:
- Choose a running application window to target
- Configure click interval (ms) or clicks per second
- Single or double-click option
- Start / Stop controls
- Light and Dark themes (dark default)

Requirements (Windows):
- Python 3.8+
- `pip install -r requirements.txt`

Run locally:

```powershell
python main.py
```

Notes:
- This tool uses Windows APIs to post mouse messages to the target window; it is Windows-only.
- Run with normal user privileges. If the target application has elevated permissions, you may need to run this script as Administrator.

Build .exe (Windows):

Open PowerShell in the project folder and run the helper script:

```powershell
.\build.ps1
```

What `build.ps1` does:
- Creates a virtual environment under `.venv`.
- Installs packages from `requirements.txt` plus `pyinstaller` and `Pillow`.
- Converts `assets/cursor_icon.svg` to `assets/app.ico` using `convert_icon_qt.py` (no Cairo runtime required).
- Runs PyInstaller to produce a single-file, windowed executable in the `dist` folder.

Manual build (if you prefer):

```powershell
# install requirements and pyinstaller
python -m pip install -r requirements.txt pyinstaller Pillow

# convert the SVG icon (optional) using the Qt converter included in the repo
.venv\Scripts\python.exe convert_icon_qt.py

# build with pyinstaller (include the assets folder)
pyinstaller --onefile --windowed --add-data "assets;assets" --icon assets\app.ico main.py
```

The produced EXE will be in `dist\` and should contain the app icon. If Explorer still shows a generic Python icon on the desktop, try restarting Explorer or re-creating the shortcut (see project notes).
# Autoclicker (Windows)

Small autoclicker with a modern PySide6 UI that targets a specific application window.

Features:
- Choose a running application window to target
- Configure click interval (ms) or clicks per second
- Single or double-click option
- Start / Stop controls
- Light and Dark themes (dark default)

Requirements (Windows):
- Python 3.8+
- `pip install -r requirements.txt`

Run:
```
python main.py
```

Notes:
- This tool uses Windows APIs to post mouse messages to the target window; it is Windows-only.
- Run with normal user privileges. If the target application has elevated permissions, you may need to run this script as Administrator.

Build .exe (Windows):

Open PowerShell in the project folder and run:

```powershell
.\build.ps1
```

This script creates a virtual environment, installs `requirements.txt` and `pyinstaller`, then builds a single-file Windows executable. The built exe will be in the `dist` folder.

Alternatively, to build manually:

```powershell
python -m pip install -r requirements.txt pyinstaller
pyinstaller --onefile --noconsole --add-data "assets\cursor_icon.svg;assets" main.py
```
