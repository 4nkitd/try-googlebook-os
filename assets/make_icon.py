#!/usr/bin/env python3
"""Draw the Try Googlebook OS app icon and its .icns.

    uv run --with pillow assets/make_icon.py

Writes assets/icon-1024.png and assets/AppIcon.icns (through iconutil).
The art: a graphite squircle, the slat wallpaper motif, one glowing bar.
"""

import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

HERE = Path(__file__).resolve().parent
S = 1024


def rounded_mask(size, radius, margin):
    m = Image.new("L", (size, size), 0)
    ImageDraw.Draw(m).rounded_rectangle(
        [margin, margin, size - margin, size - margin], radius=radius, fill=255
    )
    return m


def vertical_gradient(size, top, bottom):
    g = Image.new("RGBA", (size, size))
    d = ImageDraw.Draw(g)
    for y in range(size):
        t = y / (size - 1)
        d.line(
            [(0, y), (size, y)],
            fill=tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3))
            + (255,),
        )
    return g


def main():
    bg = vertical_gradient(S, (38, 42, 50), (10, 11, 14))

    slats = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    bar_w, gap, n = 118, 42, 5
    total = n * bar_w + (n - 1) * gap
    x0 = (S - total) // 2 + 46
    for i in range(n):
        x = x0 + i * (bar_w + gap)
        bar = Image.new("RGBA", (bar_w, S), (0, 0, 0, 0))
        bd = ImageDraw.Draw(bar)
        for xb in range(bar_w):
            t = xb / (bar_w - 1)
            lum = int(96 * (1 - t) + 18 * t)
            bd.line([(xb, 0), (xb, S)], fill=(lum, lum + 5, lum + 12, 235))
        slats.alpha_composite(bar, (x, 0))
    smask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(smask).rounded_rectangle(
        [x0 - 46, 170, x0 + total + 46, S - 170], radius=96, fill=255
    )
    slats.putalpha(
        Image.composite(slats.getchannel("A"), Image.new("L", (S, S), 0), smask)
    )
    bg.alpha_composite(slats)

    halo = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(halo).rounded_rectangle(
        [232, 188, 372, S - 188], radius=70, fill=(96, 156, 255, 150)
    )
    halo = halo.filter(ImageFilter.GaussianBlur(78))
    bg.alpha_composite(halo)

    glow = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(glow).rounded_rectangle(
        [268, 232, 336, S - 232], radius=34, fill=(255, 255, 255, 235)
    )
    glow = glow.filter(ImageFilter.GaussianBlur(46))
    bg.alpha_composite(glow)

    core = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(core).rounded_rectangle(
        [288, 262, 316, S - 262], radius=14, fill=(255, 255, 255, 255)
    )
    bg.alpha_composite(core)

    out = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    out.paste(bg, (0, 0), rounded_mask(S, 208, 96))
    out.save(HERE / "icon-1024.png")

    iconset = HERE / "AppIcon.iconset"
    iconset.mkdir(exist_ok=True)
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
    for name, px in sizes.items():
        out.resize((px, px), Image.LANCZOS).save(iconset / name)
    try:
        subprocess.run(
            ["iconutil", "-c", "icns", str(iconset), "-o", str(HERE / "AppIcon.icns")],
            check=True,
        )
    finally:
        shutil.rmtree(iconset, ignore_errors=True)
    print("wrote", HERE / "icon-1024.png", "and", HERE / "AppIcon.icns")


if __name__ == "__main__":
    main()
