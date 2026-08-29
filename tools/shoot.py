#!/usr/bin/env python3
"""Render screenshots of the page at several widths into .cache/shots/.

Exists because measurement alone is not enough. A missing `</aside>` nested the
content inside the sidebar and every gate passed: the rows were in the DOM,
nothing overflowed sideways, axe found nothing - and the page was blank. A
sticky table header once covered the first row and no number caught it.

check_responsive.py catches both of those today, but a new defect of that kind
is found fastest by someone looking at the page. This script makes that cheap:
the images go to .cache/, which is gitignored.

Chrome on macOS cannot open a window narrower than ~500px, so the page is
embedded in an iframe of the exact width and the result is cropped - the same
trick as in check_responsive.py.
"""
from __future__ import annotations

import argparse, shutil, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGE = ROOT / "dist" / "index.html"
OUT = ROOT / ".cache" / "shots"
SHOTS = [(390, 1400), (768, 1200), (1280, 1000), (1536, 1000)]

HARNESS = """<!doctype html><meta charset="utf-8">
<style>html,body{margin:0;background:#888}iframe{border:0;display:block}</style>
<iframe src="PAGE_URL" width="WIDTH" height="HEIGHT"></iframe>"""


def main() -> int:
    sys.path.insert(0, str(ROOT / "tools"))
    from check_responsive import find_chrome

    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--widths", type=int, nargs="*",
                    help="only these widths (default: 390 768 1280 1536)")
    args = ap.parse_args()

    if not PAGE.exists():
        raise SystemExit("missing dist/index.html - run `just build` first")
    chrome = find_chrome()
    if chrome is None:
        print("headless Chrome nenalezen (nastav CHROME_PATH)", file=sys.stderr)
        return 1
    crop = shutil.which("magick")
    OUT.mkdir(parents=True, exist_ok=True)

    shots = [s for s in SHOTS if not args.widths or s[0] in args.widths]
    for width, height in shots:
        with tempfile.TemporaryDirectory() as tmp:
            harness = Path(tmp) / "h.html"
            harness.write_text(
                HARNESS.replace("PAGE_URL", PAGE.resolve().as_uri())
                       .replace("WIDTH", str(width)).replace("HEIGHT", str(height)),
                encoding="utf-8")
            png = OUT / f"{width}.png"
            subprocess.run([chrome, "--headless", "--disable-gpu", "--no-sandbox",
                            "--allow-file-access-from-files", "--hide-scrollbars",
                            f"--window-size={max(width, 900) + 20},{height}",
                            "--virtual-time-budget=20000", f"--screenshot={png}",
                            harness.as_uri()], capture_output=True, timeout=180)
            if not png.exists():
                print(f"  ✗ {width}px se nevykreslil", file=sys.stderr)
                return 1
            if crop:
                subprocess.run([crop, str(png), "-crop", f"{width}x{height}+0+0",
                                "+repage", str(png)], check=True)
            print(f"  {width:>5}px  {png.relative_to(ROOT)}  {png.stat().st_size // 1024} kB")
    if not crop:
        print("  (without ImageMagick nothing is cropped - images hold the whole window)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
