"""Builds a neofetch-style profile: a dotted portrait on the left, your facts on the right, as one picture that scales to the page.
Usage: python3 make_profile.py photo.jpg [--crop x0,y0,x1,y1] [--width 60] [--height 31] [--threshold 130]
Needs Pillow and ascii-image-converter (https://github.com/TheZoraiz/ascii-image-converter) on the PATH.
Reads profile.json, writes profile-dark.svg, profile-light.svg and README.md."""
import hashlib, json, math, subprocess, sys
from html import escape
from pathlib import Path
from PIL import Image, ImageFilter, ImageOps

HERE = Path(__file__).resolve().parent
BRAILLE = {(0, 0): 1, (0, 1): 2, (0, 2): 4, (1, 0): 8, (1, 1): 16, (1, 2): 32, (0, 3): 64, (1, 3): 128}


def portrait(photo, width, height, threshold, crop):
    """Braille dots: four times the detail of letters. Dark features (hair, brows, eyes, mouth) become dots on an empty background."""
    work = HERE / ".portrait-tmp.png"
    im = ImageOps.grayscale(Image.open(photo))
    if crop:
        im = im.crop(crop)
    ImageOps.autocontrast(im, cutoff=1).filter(ImageFilter.UnsharpMask(3, 120, 3)).save(work)
    try:
        cmd = ["ascii-image-converter", str(work), "-b", "-n", "-d", f"{width},{height}", "--threshold", str(threshold)]
        return [line.rstrip() for line in subprocess.run(cmd, capture_output=True, text=True, check=True).stdout.splitlines()]
    finally:
        work.unlink(missing_ok=True)


def add_marks(art, marks, crop, width, height):
    """Small accents (an earring, glasses...) as extra dots. x and y are pixels of the original photo; crop is the box given with --crop."""
    if not marks or not crop:
        return art
    dots_w, dots_h = width * 2, height * 4
    rows = [list(r.ljust(width, "⠀")) for r in art]
    fx = lambda X: (X - crop[0]) * dots_w / (crop[2] - crop[0])
    fy = lambda Y: (Y - crop[1]) * dots_h / (crop[3] - crop[1])

    def dot(x, y):
        x, y = int(round(x)), int(round(y))
        if 0 <= x < dots_w and 0 <= y < dots_h and y // 4 < len(rows):
            cell = rows[y // 4][x // 2]
            base = ord(cell) - 0x2800 if "⠀" <= cell <= "⣿" else 0
            rows[y // 4][x // 2] = chr(0x2800 + (base | BRAILLE[(x % 2, y % 4)]))
    for m in marks:
        cx, cy = fx(m["x"]), fy(m["y"])
        if m["shape"] == "ring":
            for a in range(0, 360, 18):
                dot(cx + 3.0 * math.cos(math.radians(a)), cy + 4.0 * math.sin(math.radians(a)))
        elif m["shape"] == "diamond":
            for t in range(-2, 3):
                dot(cx + t, cy - 2 + abs(t)); dot(cx + t, cy + 2 - abs(t))
            dot(cx, cy)
    return ["".join(r).rstrip("⠀") for r in rows]


def facts(profile):
    key_w = max(len(k[0]) for k in profile["info"] + profile["contact"] if k) + 2
    rows = [profile["handle"], "-"]
    rows += [(k[0] + ":").ljust(key_w) + k[1] if k else "" for k in profile["info"]]
    rows += ["", "Contact"]
    rows += [(k[0] + ":").ljust(key_w) + k[1] for k in profile["contact"]]
    return rows


def to_svg(art, rows, dark):
    """The portrait as round dots and the facts as text in one scalable picture, so GitHub never needs a horizontal scroll."""
    fg, dim, key = ("#c9d1d9", "#8b949e", "#ffa657") if dark else ("#24292f", "#57606a", "#bc4c00")
    step, radius = 3.7, 1.45   # every braille cell is 2 dots wide and 4 high
    cols = max((len(a) for a in art), default=0)
    dots = []
    for r, line in enumerate(art):
        for c, ch in enumerate(line):
            m = ord(ch) - 0x2800
            if 0 < m <= 0xFF:
                for (dx, dy), b in BRAILLE.items():
                    if m & b:
                        dots.append(f'<circle cx="{(c * 2 + dx) * step + 4:.1f}" cy="{(r * 4 + dy) * step + 4:.1f}" r="{radius}"/>')
    art_w, art_h = cols * 2 * step + 8, len(art) * 4 * step + 8
    text_x, line_h, font = art_w + 30, 25, 16
    cw = font * 0.6   # every line gets a fixed length (textLength), so no font can make it wider than the picture
    top = (art_h - len(rows) * line_h) / 2 + font
    longest = max((len(r) for r in rows), default=0)
    w = text_x + longest * cw + 20
    key_w = max((len(r.split(":", 1)[0]) + 1 for r in rows[2:] if ":" in r), default=0)
    texts = []
    put = lambda x, y, s, fill, bold="": f'<text x="{x:.1f}" y="{y:.0f}" fill="{fill}" textLength="{len(s) * cw:.1f}" lengthAdjust="spacingAndGlyphs"{bold} xml:space="preserve">{escape(s)}</text>'
    for k, row in enumerate(rows):
        y = top + k * line_h
        if row == "-":
            texts.append(f'<line x1="{text_x}" y1="{y - 7:.0f}" x2="{text_x + longest * cw:.0f}" y2="{y - 7:.0f}" stroke="{dim}"/>')
        elif row == "Contact":
            texts.append(put(text_x, y, row, dim, ' font-weight="bold"'))
        elif ":" in row and k > 1:
            name, val = row.split(":", 1)
            texts.append(put(text_x, y, name + ":", key, ' font-weight="bold"'))
            texts.append(put(text_x + (len(name) + 1) * cw, y, val, fg))
        elif row:
            texts.append(put(text_x, y, row, fg, ' font-weight="bold"'))
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w:.0f} {art_h:.0f}" width="{w:.0f}" height="{art_h:.0f}" role="img" aria-label="Profile">'
            f'<g fill="{fg}">{"".join(dots)}</g>'
            f'<g font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace" font-size="{font}">{"".join(texts)}</g></svg>\n')


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        sys.exit(__doc__)
    num = lambda flag, default: int(args[args.index(flag) + 1]) if flag in args else default
    crop = tuple(int(v) for v in args[args.index("--crop") + 1].split(",")) if "--crop" in args else None
    profile = json.loads((HERE / "profile.json").read_text())
    width, height = num("--width", 60), num("--height", 31)
    art = add_marks(portrait(args[0], width, height, num("--threshold", 130), crop), profile.get("marks"), crop, width, height)
    rows = facts(profile)
    (HERE / "profile-dark.svg").write_text(to_svg(art, rows, True))
    (HERE / "profile-light.svg").write_text(to_svg(art, rows, False))
    tag = hashlib.md5(((HERE / "profile-dark.svg").read_text() + (HERE / "profile-light.svg").read_text()).encode()).hexdigest()[:8]   # a new address for each version, so GitHub never shows an old cached picture
    (HERE / "README.md").write_text(f'<picture>\n  <source media="(prefers-color-scheme: dark)" srcset="profile-dark.svg?v={tag}">\n  <img alt="Profile" src="profile-light.svg?v={tag}" width="100%">\n</picture>\n')
    print("wrote profile-dark.svg, profile-light.svg and README.md")
