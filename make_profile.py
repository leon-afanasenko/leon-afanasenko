"""Builds a neofetch-style profile README: an ASCII portrait on the left, your facts on the right.
Usage: python3 make_profile.py photo.jpg [--crop x0,y0,x1,y1] [--width 46] [--height 24] [--threshold 130]
Needs Pillow and ascii-image-converter (https://github.com/TheZoraiz/ascii-image-converter) on the PATH. Reads profile.json, writes README.md."""
import json, subprocess, sys
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


def facts(profile):
    key_w = max(len(k[0]) for k in profile["info"] + profile["contact"] if k) + 2
    rows = [profile["handle"], "-" * 46]
    rows += [(k[0] + ":").ljust(key_w) + k[1] if k else "" for k in profile["info"]]
    rows += ["", "Contact " + "-" * 38]
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
    out = "```\n" + merge(portrait(args[0], num("--width", 46), num("--height", 24), num("--threshold", 130), crop), facts(profile)) + "\n```\n"
    (HERE / "README.md").write_text(out)
    print(out)
