import os
import sys
from pathlib import Path

from PIL import Image

from PySide6.QtGui import QImage, QPainter
from PySide6.QtSvg import QSvgRenderer


def svg_to_qimage(svg_path: str, size: int) -> QImage:
    renderer = QSvgRenderer(svg_path)
    image = QImage(size, size, QImage.Format_RGBA8888)
    image.fill(0)
    painter = QPainter(image)
    renderer.render(painter)
    painter.end()
    return image


def qimage_to_pil(qimg: QImage) -> Image.Image:
    w = qimg.width()
    h = qimg.height()
    ptr = qimg.bits()
    # qimg.bits() may return a memoryview-like object; use tobytes()/tobytes()
    try:
        arr = ptr.tobytes()
    except Exception:
        arr = bytes(ptr)
    # QImage.Format_RGBA8888 -> raw RGBA
    img = Image.frombuffer("RGBA", (w, h), arr, "raw", "RGBA", 0, 1)
    return img


def make_ico(svg_file: str, out_ico: str):
    sizes = [16, 24, 32, 48, 64, 128, 256]
    # Render the largest size and let Pillow create the smaller sizes
    largest = max(sizes)
    qimg = svg_to_qimage(svg_file, largest)
    pil_img = qimage_to_pil(qimg)

    out_dir = os.path.dirname(out_ico)
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir, exist_ok=True)

    # Pillow can save ICO and resample to required sizes when provided the sizes list
    pil_img.save(out_ico, format="ICO", sizes=[(s, s) for s in sizes])


def main():
    root = Path(__file__).resolve().parent
    svg_path = root / "assets" / "cursor_icon.svg"
    ico_path = root / "assets" / "app.ico"

    if not svg_path.exists():
        print(f"SVG not found at {svg_path}")
        sys.exit(2)

    print(f"Rendering {svg_path} -> {ico_path} ...")
    try:
        make_ico(str(svg_path), str(ico_path))
    except Exception as e:
        print("Conversion failed:", e)
        raise

    print("Wrote:", ico_path)


if __name__ == "__main__":
    main()
