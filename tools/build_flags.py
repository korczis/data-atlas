#!/usr/bin/env python3
"""Postaví sprite s vlajkami zemí do src/assets/.

Běží **jen lokálně** — potřebuje síť a ImageMagick. Výstup je committnutý,
takže CI a `build_page.py` s ním jen pracují; build stránky nesmí na síti
záviset.

Proč sprite a ne SVG: zdrojové SVG jsou nepoužitelně nerovnoměrné. Rakouská
vlajka má 216 B, španělská 235 kB — znak ve znaku. Inline by to stránku
nafouklo o stovky kilobajtů kvůli detailu, který je při dvaceti pixelech
neviditelný. Jeden PNG pruh s 40×28 dlaždicemi má jednotky kilobajtů,
dekóduje se jednou a v CSS stačí posun pozadí.

Rozsahy `EU` a `GLOBAL` vlajku **nedostávají** schválně. Nejsou to země, tak
si nechávají textový odznak — vizuální rozdíl tím odpovídá tomu, jak je
katalog dělí. Emblém EU navíc podléhá pravidlům užití, která se sem netahají.

Zdroj obrázků: https://github.com/korczis/flags — vlajky z Wikimedia Commons,
public domain (viz NOTICE.md).
"""
from __future__ import annotations

import base64, json, shutil, subprocess, sys, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "src" / "assets"
TMP = ROOT / ".cache" / "flags"
RAW = "https://raw.githubusercontent.com/korczis/flags/master/png/256/{}.png"

# Dlaždice: 40×28 zařízených pixelů, tedy 20×14 CSS při dvojnásobném DPR.
# Vlajky mají různý poměr stran, takže se do dlaždice **vejdou** a zbytek je
# průhledný — deformovat je na jednotný poměr vypadá levně a u některých
# (Švýcarsko je čtvercové) je to nápadné.
TILE_W, TILE_H = 40, 28


def main() -> int:
    if shutil.which("magick") is None:
        raise SystemExit("ImageMagick (magick) not found — `just flags` needs it")
    codes = [c["code"] for c in
             json.loads((ROOT / "data" / "countries.json").read_text(encoding="utf-8"))["countries"]]
    TMP.mkdir(parents=True, exist_ok=True)

    tiles = []
    for code in codes:
        src = TMP / f"{code}.png"
        if not src.exists():
            try:
                urllib.request.urlretrieve(RAW.format(code), src)
            except Exception as exc:                       # noqa: BLE001
                raise SystemExit(f"{code}: download failed — {exc}")
        tile = TMP / f"t-{code}.png"
        subprocess.run(["magick", src, "-resize", f"{TILE_W}x{TILE_H}",
                        "-background", "none", "-gravity", "center",
                        "-extent", f"{TILE_W}x{TILE_H}", tile], check=True)
        tiles.append(tile)

    sprite = OUT / "flags.png"
    subprocess.run(["magick", *tiles, "+append", "-strip",
                    "-define", "png:compression-level=9", sprite], check=True)

    # Posun je index × šířka dlaždice v CSS pixelech. Ukládá se, aby ho
    # `build_page.py` nemusel odvozovat z pořadí v číselníku — to se může
    # změnit a sprite by se tiše rozešel s daty.
    offsets = {code: -(i * TILE_W // 2) for i, code in enumerate(codes)}
    meta = {"tile": [TILE_W // 2, TILE_H // 2], "width": len(codes) * TILE_W // 2,
            "offsets": offsets}
    (OUT / "flags.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1) + "\n",
                                    encoding="utf-8")

    size = sprite.stat().st_size
    b64 = len(base64.b64encode(sprite.read_bytes()))
    print(f"  src/assets/flags.png   {len(codes)} flags · {size / 1024:.1f} KB "
          f"· jako data URI {b64 / 1024:.1f} KB")
    print(f"  src/assets/flags.json  tile {TILE_W // 2}×{TILE_H // 2} CSS px")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
