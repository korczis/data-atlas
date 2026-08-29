#!/usr/bin/env python3
"""Změří v reálném prohlížeči, jestli je stránka vidět a neteče do strany.

jsdom umí DOM, ale ne layout — přetečení do strany v něm nezjistíš. Tenhle
skript proto pouští headless Chrome na několika šířkách a ptá se přímo
stránky, jestli `documentElement.scrollWidth` přerostl viewport, a který
konkrétní prvek za to může.

Vedle přetečení kontroluje i to, že hlavní obsah **skutečně něco zabírá**.
Vzniklo z chyby, kterou neodhalila žádná jiná brána: chybějící `</aside>`
zanořilo `#main-content` do postranního panelu, ten je pod `lg` mimo plátno,
takže stránka byla prázdná — a přitom v DOM byly všechny řádky (jsdom testy
prošly), nic neteklo do strany (tahle sonda prošla) a axe nehlásil nic.
Měřit rozvržení znamená měřit i to, že obsah má nenulovou plochu.

Pod 1024px navíc otevře postranní panel a ověří, že se do něj dá ťuknout —
panel může být vidět a přitom být celý pod backdropem, který ho zavře.

Vrací nenulový kód, když se stránka roztáhne do strany nebo není vidět obsah.
"""
from __future__ import annotations

import argparse, json, re, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGE = ROOT / "dist" / "index.html"
CHROME: str | None = None  # zjistí se v runtime přes find_chrome()

# šířky, na kterých se to musí chovat: malý telefon → mobil → tablet → desktop
WIDTHS = [320, 360, 390, 414, 768, 1024, 1280, 1536]

# Chrome na macOS neumí okno užší než ~500 px — `--window-size=320` se tiše
# klampne a test by měřil něco jiného, než tvrdí. Stránku proto vkládáme do
# iframu přesné šířky uvnitř širokého okna a měříme uvnitř něj.
HARNESS = r"""<!doctype html><meta charset="utf-8">
<style>html,body{margin:0}iframe{border:0;display:block}</style>
<iframe id="f" src="PAGE_URL" width="WIDTH" height="900"></iframe>
<script>
document.getElementById('f').addEventListener('load', () => setTimeout(() => {
  const d = document.getElementById('f').contentDocument;
  const w = d.documentElement.clientWidth;
  const guilty = [];
  for (const el of d.querySelectorAll('body *')) {
    const cs = d.defaultView.getComputedStyle(el);
    // Off-canvas prvky (fixed + posun mimo plátno) jsou záměr, ne chyba.
    if (cs.position === 'fixed') continue;
    const r = el.getBoundingClientRect();
    if (r.width === 0 && r.height === 0) continue;
    if (r.right <= w + 1) continue;
    let p = el.parentElement, contained = false;
    while (p) {
      const ox = d.defaultView.getComputedStyle(p).overflowX;
      if (ox === 'auto' || ox === 'scroll' || ox === 'hidden') { contained = true; break; }
      p = p.parentElement;
    }
    if (!contained) {
      guilty.push(el.tagName.toLowerCase() +
        (typeof el.className === 'string' && el.className
          ? '.' + el.className.trim().split(/\\s+/).slice(0, 3).join('.') : '') +
        ' @' + Math.round(r.right) + 'px');
    }
  }
  // Obsah musí mít nenulovou plochu a nesmí být zanořený v panelu —
  // jinak je stránka „vykreslená" a přitom prázdná.
  const main = d.getElementById('main-content');
  const side = d.getElementById('sidebar');
  const mainBox = main ? main.getBoundingClientRect() : { width: 0, height: 0 };
  const rows = [...d.querySelectorAll('table tbody tr[data-row], ul[role="list"] > li')]
    .filter(el => el.getBoundingClientRect().height > 0).length;
  // Vnitřní scroll je legitimní únik pro širokou tabulku, ale znamená, že
  // část sloupců není vidět. U katalogu to bylo 1004px tabulky v 768px okně,
  // takže dva sloupce zmizely za okrajem — proto se to měří.
  const box = d.querySelector('.scroll-x');
  const innerOverflow = box ? box.scrollWidth - box.clientWidth : 0;
  const EDGE = 8;   // tolerance pro „ukotvené k okraji"

  // Překryv se nepozná, dokud se nescrolluje: `position: sticky` do té doby
  // nic nedělá. Lepivá hlavička tabulky proto překryla první řádek a všechny
  // brány prošly. Kontroluje se po odscrollování a jen u prvků, které
  // *neplavou* u horního ani dolního okraje — pod horní lištou a nad souhrnnou
  // lištou obsah projíždět má, uprostřed viewportu ne.
  // Měří se **při scrollu 0**, a to je celý trik. Lepivý prvek do prvního
  // scrollu drží svou přirozenou pozici, takže tam nemá co překrývat.
  // Když překrývá, znamená to, že se jeho lepivý kontext počítá od něčeho
  // jiného, než člověk čeká — přesně to udělala `sticky top-16` na hlavičce
  // tabulky uvnitř `overflow-x-auto`: obal se stal scroll kontejnerem
  // a hlavička skončila 4rem pod jeho horní hranou, přes záhlaví sekce
  // a první řádek.
  //
  // Po odscrollování se naopak překrývat *má* — lepivé nadpisy sekcí v kartách
  // fungují právě tak. Proto se scrolluje jen kvůli tomu, aby se vyloučily
  // prvky ukotvené k okraji (horní lišta, souhrnná lišta, spodní navigace),
  // pod kterými obsah projíždět má.
  const occluders = [...d.querySelectorAll('body *')].filter(el => {
    const cs = d.defaultView.getComputedStyle(el);
    if (cs.position !== 'fixed' && cs.position !== 'sticky') return false;
    if (cs.bottom !== 'auto') return false;
    return !(cs.top !== 'auto' && parseFloat(cs.top) <= EDGE);
  });
  const overlaps = [];
  const vh = d.documentElement.clientHeight;
  {
    const y = 0;
    for (const el of occluders) {
      const a = el.getBoundingClientRect();
      if (a.width === 0 || a.height === 0) continue;
      for (const row of d.querySelectorAll('tr[data-row], ul[role="list"] > li')) {
        const b = row.getBoundingClientRect();
        if (b.height === 0) continue;
        if (b.bottom < 0 || b.top > vh) continue;
        const dx = Math.min(a.right, b.right) - Math.max(a.left, b.left);
        const dy = Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top);
        if (dx > 1 && dy > 1) {
          overlaps.push((el.tagName + (el.className && typeof el.className === 'string'
            ? '.' + el.className.trim().split(/\s+/).slice(0, 2).join('.') : ''))
            + ` překrývá řádek o ${Math.round(dy)}px při scrollu ${y}`);
          break;
        }
      }
    }
  }
  // Šuplík se testuje až nakonec: otevření přidá <body class="overflow-hidden">
  // a backdrop, což by zkreslilo měření nad tímhle řádkem.
  //
  // Nestačí se ptát, jestli je panel po kliknutí vidět — byl vidět i tehdy,
  // když nešel používat. Flowbite si k šuplíku vyrábí vlastní backdrop
  // s natvrdo zadrátovaným `z-30` a připojuje ho na konec <body>. Když měl
  // panel taky `z-30`, prohrál pořadím v DOM: menu se otevřelo pod ztmavením
  // a každé ťuknutí do něj spadlo na backdrop, který šuplík zavřel.
  // Proto se ptáme na to jediné, na čem záleží: co je doopravdy na pixelu
  // uprostřed otevřeného panelu.
  const drawer = { testovan: false };
  const toggle = d.querySelector('[data-drawer-toggle="sidebar"]');
  if (side && toggle && w < 1024) {
    drawer.testovan = true;
    drawer.spoustecVidet = toggle.getBoundingClientRect().width > 0;
    toggle.click();
    const sr = side.getBoundingClientRect();
    drawer.left = Math.round(sr.left);
    drawer.viditelnost = d.defaultView.getComputedStyle(side).visibility;
    const hit = d.elementFromPoint(Math.round(sr.left + sr.width / 2),
                                   Math.round(Math.min(300, vh / 2)));
    drawer.naPixelu = hit ? (hit.id || hit.tagName.toLowerCase() +
      (typeof hit.className === 'string' && hit.className
        ? '.' + hit.className.trim().split(/\s+/).slice(0, 2).join('.') : '')) : null;
    drawer.klikatelny = !!(hit && side.contains(hit));

    // Backdrop si Flowbite vyrábí za běhu, takže Tailwind jeho třídy nevidí
    // a ořízne je. Bez `inset-0` má nulový rozměr: šuplík se otevře bez
    // ztmavení a ťuknutí vedle něj ho nezavře. V DOM přitom je, takže
    // pouhá kontrola přítomnosti by prošla — měří se plocha a chování.
    const bd = d.querySelector('[drawer-backdrop]');
    drawer.backdrop = !!bd;
    if (bd) {
      const br = bd.getBoundingClientRect();
      drawer.backdropPlocha = Math.round(br.width) + 'x' + Math.round(br.height);
      drawer.backdropKryje = br.width >= w - 1 && br.height >= vh - 1;
      const mimo = d.elementFromPoint(w - 4, Math.round(Math.min(300, vh / 2)));
      drawer.backdropNahore = mimo === bd;
      bd.click();
      drawer.zavreSe = Math.round(side.getBoundingClientRect().left) < 0;
    }
  }

  const out = document.createElement('div');
  out.id = 'probe-result';
  out.textContent = JSON.stringify({
    drawer,
    viewport: w,
    scrollWidth: d.documentElement.scrollWidth,
    overflow: d.documentElement.scrollWidth - w,
    mainWidth: Math.round(mainBox.width),
    mainHeight: Math.round(mainBox.height),
    mainInSidebar: !!(side && main && side.contains(main)),
    visibleRows: rows,
    innerOverflow: Math.max(0, innerOverflow),
    overlaps: overlaps.slice(0, 3),
    guilty: guilty.slice(0, 5),
  });
  document.body.appendChild(out);
}, 600));
</script>
"""


def find_chrome() -> str | None:
    """Najde Chrome napříč systémy.

    Cesta natvrdo znamená, že kontrola v CI tiše neběží a člověk si myslí,
    že něco hlídá. Pořadí: proměnná CHROME_PATH, pak obvyklá místa.
    """
    import os, shutil
    if (env := os.environ.get("CHROME_PATH")) and Path(env).exists():
        return env
    candidates = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
    ]
    for c in candidates:
        if Path(c).exists():
            return c
    for name in ("google-chrome", "google-chrome-stable", "chromium",
                 "chromium-browser", "chrome"):
        if (found := shutil.which(name)):
            return found
    return None

def measure(width: int) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        harness = Path(tmp) / "harness.html"
        harness.write_text(
            HARNESS.replace("PAGE_URL", PAGE.as_uri()).replace("WIDTH", str(width)),
            encoding="utf-8")
        res = subprocess.run(
            # Bez vypnutých přechodů se měří mezistav: šuplík se v okamžiku
            # kliknutí teprve rozjíždí a `left` je pořád -256px.
            [CHROME, "--headless", "--disable-gpu", "--hide-scrollbars",
             "--force-prefers-reduced-motion",
             "--allow-file-access-from-files", "--virtual-time-budget=6000",
             f"--window-size={max(width, 900) + 40},1000",
             "--dump-dom", harness.as_uri()],
            capture_output=True, text=True, timeout=90)
    m = re.search(r'<div id="probe-result">(.*?)</div>', res.stdout, re.S)
    if not m:
        raise SystemExit(f"sonda nevrátila výsledek pro {width}px")
    return json.loads(m.group(1).replace("&quot;", '"').replace("&amp;", "&"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--widths", type=int, nargs="*", default=WIDTHS)
    args = ap.parse_args()

    if not PAGE.exists():
        raise SystemExit("chybí dist/index.html — spusť nejdřív `just build`")
    global CHROME
    CHROME = find_chrome()
    if CHROME is None:
        print("headless Chrome nenalezen, kontrola přeskočena "
              "(nastav CHROME_PATH)", file=sys.stderr)
        return 0

    failed = False
    for w in args.widths:
        r = measure(w)
        problems = []
        if r["overflow"] > 0:
            problems.append(f"teče do strany o {r['overflow']}px")
        # Prázdná stránka se pozná jinak než přetečením: obsah je v DOM,
        # ale nic nezabírá — typicky když se zanoří do off-canvas panelu.
        if r["mainInSidebar"]:
            problems.append("#main-content je zanořený v #sidebar")
        if r["mainWidth"] <= 0 or r["mainHeight"] <= 0:
            problems.append(f"hlavní obsah nic nezabírá ({r['mainWidth']}×{r['mainHeight']}px)")
        if r["visibleRows"] == 0:
            problems.append("není vidět ani jedna položka katalogu")
        # Karty (< md) tabulku nevykreslují, tam se vnitřní scroll neměří.
        if w >= 768 and r["innerOverflow"] > 0:
            problems.append(f"tabulka je o {r['innerOverflow']}px širší než okno "
                            "— sloupce zmizí za okrajem")
        for o in r.get("overlaps", []):
            problems.append(o)
        dr = r.get("drawer") or {}
        if dr.get("testovan"):
            if not dr.get("spoustecVidet"):
                problems.append("hamburger není vidět, panel se nedá otevřít")
            elif dr.get("left", -1) != 0 or dr.get("viditelnost") != "visible":
                problems.append(f"panel se po kliknutí neotevřel "
                                f"(left={dr.get('left')}px, {dr.get('viditelnost')})")
            elif not dr.get("klikatelny"):
                problems.append("otevřený panel překrývá " + str(dr.get("naPixelu"))
                                + " — ťuknutí do menu na něj nedosáhne")
            elif not dr.get("backdrop"):
                problems.append("šuplík nemá backdrop")
            elif not dr.get("backdropKryje"):
                problems.append(f"backdrop má rozměr {dr.get('backdropPlocha')} místo "
                                "celé plochy — Tailwind ořízl třídy, které Flowbite "
                                "přidává za běhu (safelist v tailwind.config.js)")
            elif not dr.get("backdropNahore"):
                problems.append("backdrop neleží nad obsahem vedle šuplíku")
            elif not dr.get("zavreSe"):
                problems.append("ťuknutí vedle šuplíku ho nezavře")
        failed |= bool(problems)
        print(f"  {'✓' if not problems else '✗'} {w:>5}px  scrollWidth={r['scrollWidth']:<6} "
              f"přetečení={r['overflow']:>4}px  obsah={r['mainWidth']}×{r['mainHeight']}px  "
              f"položek={r['visibleRows']}  tabulka+{r['innerOverflow']}px"
              + ("  šuplík ok" if not problems and (r.get("drawer") or {}).get("zavreSe") else ""))
        for problem in problems:
            print(f"        {problem}")
        if r["overflow"] > 0:
            for g in r["guilty"]:
                print(f"        viník: {g}")
    print("\nrozvržení v pořádku" if not failed else "\nrozvržení je rozbité")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
