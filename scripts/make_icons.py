"""Generate the PWA icon set (run once; output is committed). Usage: uv run --project backend python scripts/make_icons.py"""

from pathlib import Path

from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parents[1] / "frontend" / "public" / "icons"
BG, FG = (11, 18, 32), (34, 197, 94)
# Pulse line in a 100x100 box
PULSE = [(10, 55), (32, 55), (40, 38), (50, 75), (60, 25), (68, 55), (90, 55)]


def draw(size: int, pad: float) -> Image.Image:
    img = Image.new("RGB", (size, size), BG)
    d = ImageDraw.Draw(img)
    inner = size * (1 - 2 * pad)
    pts = [(size * pad + x / 100 * inner, size * pad + y / 100 * inner) for x, y in PULSE]
    d.line(pts, fill=FG, width=max(2, int(size * 0.07)), joint="curve")
    return img


OUT.mkdir(parents=True, exist_ok=True)
draw(192, 0.08).save(OUT / "icon-192.png")
draw(512, 0.08).save(OUT / "icon-512.png")
draw(512, 0.2).save(OUT / "icon-maskable-512.png")  # safe zone for maskable icons
pts = " ".join(f"{x},{y}" for x, y in PULSE)
(OUT / "icon.svg").write_text(
    f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><rect width="100" height="100" rx="18" '
    f'fill="#0b1220"/><polyline points="{pts}" fill="none" stroke="#22c55e" stroke-width="7" '
    f'stroke-linejoin="round" stroke-linecap="round"/></svg>\n'
)
print("icons written to", OUT)
