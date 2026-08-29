#!/usr/bin/env python3
"""Přegeneruje ikony a OG kartu do static/.

Běží jen lokálně — potřebuje headless Chrome (kvůli věrnému SVG a webfontům)
a ImageMagick. Výstupy jsou committnuté, takže CI je jen kopíruje a tenhle
skript nemusí umět spustit.

Počty na OG kartě se berou z data/catalog.csv, aby obrázek nelhal poté,
co katalog povyroste.
"""
import csv, json, math, shutil, subprocess, sys
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


# Odstíny rodin témat — musí sedět s GROUP_HUE v src/template.html, jinak
# by náhled používal jiný barevný klíč než stránka, na kterou vede.
GROUP_HUE = [162, 217, 268, 22, 190, 322]


def coverage() -> tuple[str, int]:
    """Matice pokrytí jako HTML a počet témat kompletních ve všech 27 státech.

    Kreslí se ze stejných dat a stejným klíčem jako matice na stránce: odstín
    nese rodinu tématu, sytost počet zdrojů. Kdyby se náhled kreslil z čísel
    napsaných ručně, zastaral by při prvním přírůstku katalogu.
    """
    data = ROOT / "data"
    groups = json.loads((data / "topics.json").read_text(encoding="utf-8"))["groups"]
    places = json.loads((data / "countries.json").read_text(encoding="utf-8"))
    with (data / "catalog.csv").open(encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))

    counts: dict[tuple[str, str], int] = {}
    for r in rows:
        key = (r["Kód"], r["Téma ID"])
        counts[key] = counts.get(key, 0) + 1
    used_topics = {r["Téma ID"] for r in rows}
    used_places = {r["Kód"] for r in rows}

    cols = [(gi, t["id"]) for gi, g in enumerate(groups)
            for t in g["topics"] if t["id"] in used_topics]
    eu = [c["code"] for c in places["countries"]
          if c.get("eu") and c["code"] in used_places]
    scopes = [c["code"] for c in places["scopes"] if c["code"] in used_places]
    order = eu + scopes
    top = max(counts.values(), default=1)

    parts, last_group = ['<div class="m">'], cols[0][0]
    for gi, topic in cols:
        if gi != last_group:
            parts.append('<span class="sep"></span>')
            last_group = gi
        parts.append('<div class="col">')
        parts.append(f'<span class="band" style="background:hsl({GROUP_HUE[gi]} 62% 48%)"></span>')
        for code in order:
            n = counts.get((code, topic), 0)
            if n == 0:
                parts.append('<i style="background:rgba(255,255,255,.06)"></i>')
            else:
                s = min(1.0, math.log(1 + n) / math.log(1 + top))
                parts.append(f'<i style="background:hsl({GROUP_HUE[gi]} '
                             f'{40 + s * 30:.0f}% {26 + s * 34:.0f}%)"></i>')
        parts.append("</div>")
    parts.append("</div>")

    full = sum(1 for _, topic in cols if all(counts.get((c, topic)) for c in eu))
    return "".join(parts), full


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

    # Social preview pro GitHub: 1280×640. Jiný formát než OG karta (1200×630)
    # a jiný obsah — GitHub ho zobrazuje větší a vedle názvu repozitáře, takže
    # unese matici, která na OG kartě jen šumí.
    matrix, full = coverage()
    social = (SRC / "social.html").read_text(encoding="utf-8")
    for key, value in {**numbers, "MATRIX": matrix, "FULL": full}.items():
        token = "{{" + key + "}}"
        if token not in social:
            raise SystemExit(f"src/assets/social.html neobsahuje značku {token}")
        social = social.replace(token, str(value))
    page = TMP / "social.html"
    page.write_text(social, encoding="utf-8")
    shot(page, 1280, 640, STATIC / "social-preview.png")
    subprocess.run(["magick", STATIC / "social-preview.png", "-strip",
                    "-define", "png:compression-filter=5",
                    "-define", "png:compression-level=9",
                    "-define", "png:compression-strategy=1",
                    STATIC / "social-preview.png"], check=True)

    print("static/: ikony + OG karta ("
          + ", ".join(f"{v} {k.lower()}" for k, v in numbers.items()) + ")")
    for f in sorted(STATIC.iterdir()):
        print(f"  {f.name:26s} {f.stat().st_size / 1024:7.1f} KB")


if __name__ == "__main__":
    main()
