#!/usr/bin/env python3
"""Přegeneruje ikony a OG kartu do static/.

Běží jen lokálně — potřebuje headless Chrome (kvůli věrnému SVG a webfontům)
a ImageMagick. Výstupy jsou committnuté, takže CI je jen kopíruje a tenhle
skript nemusí umět spustit.

Počty na OG kartě se berou z data/catalog.csv, aby obrázek nelhal poté,
co katalog povyroste.
"""
import csv, shutil, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC, STATIC, TMP = ROOT / "src" / "assets", ROOT / "static", ROOT / ".cache" / "assets"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


def need(cmd: str) -> None:
    if shutil.which(cmd) is None:
        raise SystemExit(f"chybí {cmd}")


def shot(html: Path, w: int, h: int, out: Path) -> None:
    subprocess.run([CHROME, "--headless", "--disable-gpu", "--hide-scrollbars",
                    "--force-device-scale-factor=1", "--default-background-color=00000000",
                    f"--window-size={w},{h}", f"--screenshot={out}", html.as_uri()],
                   check=True, capture_output=True)


def icon(size: int, out: Path) -> None:
    page = TMP / f"icon-{size}.html"
    page.write_text(
        '<!doctype html><meta charset="utf-8">'
        "<style>html,body{margin:0;background:transparent}"
        f"img{{display:block;width:{size}px;height:{size}px}}</style>"
        f'<img src="{(SRC / "icon.svg").as_uri()}">', encoding="utf-8")
    shot(page, size, size, TMP / "raw.png")
    subprocess.run(["magick", TMP / "raw.png", "-trim", "+repage",
                    "-resize", f"{size}x{size}", "-background", "none",
                    "-gravity", "center", "-extent", f"{size}x{size}", out], check=True)


def stats() -> dict[str, int]:
    with (ROOT / "data" / "catalog.csv").open(encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    return {"ITEMS": len(rows),
            "TOPICS": len({r["Téma"] for r in rows}),
            "COUNTRIES": len({r["Kód"] for r in rows})}


def main() -> None:
    need("magick")
    if not Path(CHROME).exists():
        raise SystemExit(f"chybí headless Chrome na {CHROME}")
    TMP.mkdir(parents=True, exist_ok=True)
    STATIC.mkdir(exist_ok=True)

    shutil.copy(SRC / "icon.svg", STATIC / "favicon.svg")
    icon(512, STATIC / "icon-512.png")
    icon(192, STATIC / "icon-192.png")
    icon(180, STATIC / "apple-touch-icon.png")

    # maskable potřebuje safe zone — motiv na ~78 % plochy
    subprocess.run(["magick", STATIC / "icon-512.png", "-resize", "400x400",
                    "-background", "#14357f", "-gravity", "center",
                    "-extent", "512x512", STATIC / "icon-maskable-512.png"], check=True)

    for px in (16, 32, 48):
        subprocess.run(["magick", STATIC / "icon-512.png", "-resize", f"{px}x{px}",
                        TMP / f"i{px}.png"], check=True)
    subprocess.run(["magick", TMP / "i16.png", TMP / "i32.png", TMP / "i48.png",
                    STATIC / "favicon.ico"], check=True)

    numbers = stats()
    og = (SRC / "og.html").read_text(encoding="utf-8")
    # Zástupné značky, ne náhrada literálů: dřív se v šabloně přepisovalo
    # "<b>142</b>", takže úprava textu karty tiše rozbila dosazování počtů.
    for key, value in numbers.items():
        token = "{{" + key + "}}"
        if token not in og:
            raise SystemExit(f"src/assets/og.html neobsahuje značku {token}")
        og = og.replace(token, str(value))
    page = TMP / "og.html"
    page.write_text(og, encoding="utf-8")
    shot(page, 1200, 630, STATIC / "og-image.png")
    # PNG je bezztrátový; velikost se sráží filtrem a kompresní úrovní,
    # ne "kvalitou". Paleta by na gradientu vytvořila pruhy.
    subprocess.run(["magick", STATIC / "og-image.png", "-strip",
                    "-define", "png:compression-filter=5",
                    "-define", "png:compression-level=9",
                    "-define", "png:compression-strategy=1",
                    STATIC / "og-image.png"], check=True)

    print("static/: ikony + OG karta ("
          + ", ".join(f"{v} {k.lower()}" for k, v in numbers.items()) + ")")
    for f in sorted(STATIC.iterdir()):
        print(f"  {f.name:26s} {f.stat().st_size / 1024:7.1f} KB")


if __name__ == "__main__":
    main()
