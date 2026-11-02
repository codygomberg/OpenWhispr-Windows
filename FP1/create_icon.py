"""Run once to regenerate icon.ico for the Windows shortcut."""
import math
import os

import numpy as np
from PIL import Image, ImageDraw


def make_icon(size: int) -> Image.Image:
    # Draw at 4x resolution, then scale down with LANCZOS for clean anti-aliasing
    s = size * 4
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    cx, cy = s / 2, s / 2

    # Rounded square background
    d.rounded_rectangle([0, 0, s - 1, s - 1], radius=s // 5, fill=(28, 28, 30, 255))

    # Three rotated ellipses — matching the Mac orbital geometry
    rx = s * 0.37
    ry = s * 0.155
    stroke = max(3, s // 18)
    white = (255, 255, 255, 255)

    t = np.linspace(0, 2 * math.pi, 400)

    for angle_deg in [0, 60, 120]:
        a = math.radians(angle_deg)
        cos_a, sin_a = math.cos(a), math.sin(a)
        x = rx * np.cos(t)
        y = ry * np.sin(t)
        xr = x * cos_a - y * sin_a + cx
        yr = x * sin_a + y * cos_a + cy
        pts = list(zip(xr.tolist(), yr.tolist()))
        d.line(pts + [pts[0]], fill=white, width=stroke)

    return img.resize((size, size), Image.LANCZOS)


out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.ico")

# PIL requires saving from the largest image and passing all sizes explicitly
img_256 = make_icon(256)
img_256.save(
    out,
    format="ICO",
    sizes=[(16, 16), (32, 32), (48, 48), (256, 256)],
)
print(f"Saved: {out}")

# Verify
from PIL import Image as _I
check = _I.open(out)
print(f"Embedded sizes: {check.info.get('sizes')}")
