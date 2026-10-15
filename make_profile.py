"""Builds a neofetch-style profile README: an ASCII portrait on the left, your facts on the right.
Usage: python3 make_profile.py photo.jpg [--crop x0,y0,x1,y1] [--width 46] [--height 30] [--threshold 130]
Needs Pillow and ascii-image-converter (https://github.com/TheZoraiz/ascii-image-converter) on the PATH. Reads profile.json, writes README.md."""
import json, math, subprocess, sys
from pathlib import Path
from PIL import Image, ImageFilter, ImageOps

HERE = Path(__file__).resolve().parent


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
    """Small accents (an earring, glasses...) drawn as extra braille dots. x and y are pixels of the original photo; crop is the box given with --crop."""
    if not marks or not crop:
        return art
    cols, dots_w, dots_h = width, width * 2, height * 4
    rows = [list(r.ljust(cols, "\u2800")) for r in art]
    bit = {(0, 0): 1, (0, 1): 2, (0, 2): 4, (1, 0): 8, (1, 1): 16, (1, 2): 32, (0, 3): 64, (1, 3): 128}
    fx = lambda X: (X - crop[0]) * dots_w / (crop[2] - crop[0]); fy = lambda Y: (Y - crop[1]) * dots_h / (crop[3] - crop[1])

    def dot(x, y):
        x, y = int(round(x)), int(round(y))
        if 0 <= x < dots_w and 0 <= y < dots_h and y // 4 < len(rows):
            cell = rows[y // 4][x // 2]; base = ord(cell) - 0x2800 if "\u2800" <= cell <= "\u28ff" else 0
            rows[y // 4][x // 2] = chr(0x2800 + (base | bit[(x % 2, y % 4)]))
    for m in marks:
        cx, cy = fx(m["x"]), fy(m["y"])
        if m["shape"] == "ring":
            for a in range(0, 360, 18):
                dot(cx + 3.0 * math.cos(math.radians(a)), cy + 4.0 * math.sin(math.radians(a)))
        elif m["shape"] == "diamond":
            for t in range(-2, 3):
                dot(cx + t, cy - 2 + abs(t)); dot(cx + t, cy + 2 - abs(t))
            dot(cx, cy)
    return ["".join(r).rstrip("\u2800") for r in rows]


def facts(profile):
    key_w = max(len(k[0]) for k in profile["info"] + profile["contact"] if k) + 2
    rows = [profile["handle"], "-" * 34]
    rows += [(k[0] + ":").ljust(key_w) + k[1] if k else "" for k in profile["info"]]
    rows += ["", "Contact " + "-" * 26]
    rows += [(k[0] + ":").ljust(key_w) + k[1] for k in profile["contact"]]
    return rows


def merge(art, rows):
    width = max((len(a) for a in art), default=0); n = max(len(art), len(rows)); top = (n - len(rows)) // 2
    art = art + [""] * (n - len(art)); rows = [""] * top + rows + [""] * (n - len(rows) - top)
    return "\n".join((a.ljust(width) + "   " + r).rstrip() for a, r in zip(art, rows))


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        sys.exit(__doc__)
    num = lambda flag, default: int(args[args.index(flag) + 1]) if flag in args else default
    crop = tuple(int(v) for v in args[args.index("--crop") + 1].split(",")) if "--crop" in args else None
    profile = json.loads((HERE / "profile.json").read_text())
    out = "```\n" + merge(add_marks(portrait(args[0], num("--width", 46), num("--height", 30), num("--threshold", 130), crop), profile.get("marks"), crop, num("--width", 46), num("--height", 30)), facts(profile)) + "\n```\n"
    (HERE / "README.md").write_text(out)
    print(out)
