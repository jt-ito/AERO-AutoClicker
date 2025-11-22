"""
Deprecated converter.

This file was the old cairo/cairosvg-dependent converter. The project now
provides `convert_icon_qt.py` which uses PySide6 to render SVGs and Pillow to
write a multi-size ICO without requiring the Cairo runtime.

Keep this file only for reference; running it is not recommended.
"""

print("Deprecated: use convert_icon_qt.py instead. This file is retired.")
