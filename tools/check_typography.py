#!/usr/bin/env python3
"""Změří sazbu v headless Chrome: délku řádku, velikost písma v polích, nadpisy.

Existuje ze stejného důvodu jako check_responsive.py — tyhle vady se nedají
poznat z markupu. `max-w-3xl` vypadá jako rozumný strop, ale je to 768 px:
při textu 14 px to vyjde na 89 znaků a při 12 px na 129. Čitelné je 45–75.
Strop se proto musí měřit ve znacích, ne v pixelech, a to jde až po vysázení.

Tři pravidla, každé z konkrétní vady:

1. **Pole nesmí mít pod 16 px na mobilu.** iOS Safari při fokusu do menšího
   pole zoomuje celou stránku — uživatel ťukne do hledání a rozvržení se mu
   rozjede. Na desktopu je 14 px v pořádku, proto se měří po šířkách.
2. **Souvislý text nesmí přes 85 znaků na řádek.** Oko na dlouhém řádku
   ztrácí návaznost a skáče o řádek zpět.
3. **Úrovně nadpisů se nesmí přeskakovat.** Odečítač je používá jako obsah.

Krátké odstavce v úzkých kartách (pod 40 znaků) se nehlásí: tam je to
záměr rozvržení, ne vada sazby.
"""
from __future__ import annotations

import argparse, json, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from check_responsive import find_chrome  # noqa: E402

PAGES = {"index": ROOT / "dist" / "index.html",
         "place": ROOT / "dist" / "cz" / "index.html"}
WIDTHS = (390, 1280)
MAX_MEASURE = 85          # znaků na řádek
MIN_INPUT_PX = 16         # pod tím iOS zoomuje
MOBILE_MAX = 640          # do téhle šířky platí pravidlo o polích

PROBE = r"""
<script>
window.onerror = m => /ResizeObserver/.test(m) ? true : undefined;
window.addEventListener('load', () => setTimeout(() => {
  const out = { long: [], small: [], skips: [] };
  const chWidth = (el) => {
    const s = getComputedStyle(el);
    const probe = document.createElement('span');
    probe.style.cssText = 'position:absolute;visibility:hidden;white-space:pre;font:' + s.font;
    probe.textContent = '0'.repeat(50);
    document.body.appendChild(probe);
    const w = probe.getBoundingClientRect().width / 50;
    probe.remove();
    return w;
  };
  for (const el of document.querySelectorAll('p, li, dd, figcaption')) {
    const text = (el.textContent || '').trim();
    if (text.length < 90) continue;
    const box = el.getBoundingClientRect();
    if (box.width <= 0 || box.height <= 0) continue;
    // Délka řádku dává smysl jen v normálním toku textu. U flex/grid
    // kontejneru je šířka prvku vzdálenost mezi dvěma krajními dětmi,
    // ne délka řádku — u titulku matice to vycházelo na 100 znaků,
    // přestože jsou to dva krátké popisky na opačných koncích.
    const disp = getComputedStyle(el).display;
    if (disp === 'flex' || disp === 'grid' || disp === 'inline-flex') continue;
    const ch = Math.round(box.width / chWidth(el));
    if (ch > __MAX__) out.long.push({ ch, text: text.slice(0, 60),
                                      cls: (el.className || '').slice(0, 60) });
  }
  for (const el of document.querySelectorAll('input, select, textarea')) {
    const box = el.getBoundingClientRect();
    if (box.width <= 0 || box.height <= 0) continue;
    if (el.type === 'hidden' || el.type === 'checkbox' || el.type === 'radio') continue;
    const px = parseFloat(getComputedStyle(el).fontSize);
    if (px < __MINPX__) out.small.push({ id: el.id || el.name || el.type, px: Math.round(px) });
  }
  const hs = [...document.querySelectorAll('h1,h2,h3,h4,h5,h6')]
    .filter(h => h.getBoundingClientRect().height > 0);
  for (let i = 1; i < hs.length; i++) {
    const a = +hs[i - 1].tagName[1], b = +hs[i].tagName[1];
    if (b > a + 1) out.skips.push(hs[i - 1].tagName + ' -> ' + hs[i].tagName);
  }
  const div = document.createElement('div');
  div.id = 'typo';
  div.textContent = JSON.stringify(out);
  document.body.appendChild(div);
}, 1800));
</script>
"""


def measure(chrome: str, page: Path, width: int) -> dict:
    probe = PROBE.replace("__MAX__", str(MAX_MEASURE)).replace("__MINPX__", str(MIN_INPUT_PX))
    # Sonda se zapisuje vedle originálu, ne do temp adresáře: stránka země
    # načítá runtime relativně a odjinud by nenaběhla — stejný důvod jako
    # v check_a11y.py.
    tmp = page.with_name(f".typo-{width}.html")
    tmp.write_text(page.read_text(encoding="utf-8").replace("</body>", probe + "</body>"),
                   encoding="utf-8")
    try:
        res = subprocess.run(
            [chrome, "--headless", "--disable-gpu", "--hide-scrollbars",
             "--virtual-time-budget=20000", f"--window-size={max(width, 520)},1200",
             "--dump-dom", tmp.as_uri()],
            capture_output=True, text=True, timeout=120)
    finally:
        tmp.unlink(missing_ok=True)
    m = re.search(r'<div id="typo">(.*?)</div>', res.stdout, re.S)
    if not m:
        raise SystemExit(f"sonda nevrátila výsledek ({page.name}, {width}px)")
    import html as H
    return json.loads(H.unescape(m.group(1)))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--page", choices=tuple(PAGES), default="index")
    args = ap.parse_args()

    page = PAGES[args.page]
    if not page.exists():
        raise SystemExit(f"chybí {page.relative_to(ROOT)} — spusť nejdřív `just build`")
    chrome = find_chrome()
    if chrome is None:
        print("Chrome nenalezen — sazba se nezměřila")
        return 0

    problems = 0
    for width in WIDTHS:
        r = measure(chrome, page, width)
        bad = []
        for x in r["long"]:
            bad.append(f"řádek {x['ch']} znaků (max {MAX_MEASURE}) — {x['text']}…")
        # Pravidlo o velikosti písma v polích je o mobilním prohlížeči.
        if width <= MOBILE_MAX:
            for x in r["small"]:
                bad.append(f"pole #{x['id']} má {x['px']}px — pod {MIN_INPUT_PX}px "
                           "iOS Safari při fokusu zoomuje stránku")
        for x in r["skips"]:
            bad.append(f"přeskočená úroveň nadpisu {x}")
        mark = "✓" if not bad else "✗"
        print(f"  {mark} {width:>5}px  {len(r['long'])} dlouhých řádků · "
              f"{len(r['small'])} malých polí · {len(r['skips'])} skoků v nadpisech")
        for b in bad:
            print(f"      {b}")
        problems += len(bad)

    print("\nsazba v pořádku" if not problems else f"\n{problems} nálezů v sazbě", file=sys.stderr if problems else sys.stdout)
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
