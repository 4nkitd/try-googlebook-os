#!/usr/bin/env python3
import io
from pathlib import Path
import subprocess
import tempfile

import resvg_py
from PIL import Image

HERE = Path(__file__).resolve().parent


def main():
    png = resvg_py.svg_to_bytes(
        svg_path=str(HERE / "AppIcon.svg"), width=1024, height=1024
    )
    image = Image.open(io.BytesIO(png)).convert("RGBA")
    image.save(HERE / "icon-1024.png")
    sizes = {
        "icon_16x16.png": 16,
        "icon_16x16@2x.png": 32,
        "icon_32x32.png": 32,
        "icon_32x32@2x.png": 64,
        "icon_128x128.png": 128,
        "icon_128x128@2x.png": 256,
        "icon_256x256.png": 256,
        "icon_256x256@2x.png": 512,
        "icon_512x512.png": 512,
        "icon_512x512@2x.png": 1024,
    }
    with tempfile.TemporaryDirectory(prefix="googlebook-icon-") as temporary:
        iconset = Path(temporary) / "AppIcon.iconset"
        iconset.mkdir()
        for name, size in sizes.items():
            image.resize((size, size), Image.Resampling.LANCZOS).save(iconset / name)
        subprocess.run(
            ["iconutil", "-c", "icns", str(iconset), "-o", str(HERE / "AppIcon.icns")],
            check=True,
        )
    print("Wrote icon-1024.png and AppIcon.icns from AppIcon.svg")


if __name__ == "__main__":
    main()
