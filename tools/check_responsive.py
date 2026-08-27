#!/usr/bin/env python3
"""Změří vodorovné přetečení stránky v reálném prohlížeči.

jsdom umí DOM, ale ne layout — přetečení do strany v něm nezjistíš. Tenhle
skript proto pouští headless Chrome na několika šířkách a ptá se přímo
stránky, jestli `documentElement.scrollWidth` přerostl viewport, a který
konkrétní prvek za to může.

Vrací nenulový kód, když se stránka na kterékoli šířce roztáhne do strany.
"""
import argparse, json, re, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGE = ROOT / "dist" / "index.html"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

# šířky, na kterých se to musí chovat: malý telefon → mobil → tablet → desktop
WIDTHS = [320, 360, 390, 414, 768, 1024, 1280, 1536]

# Chrome na macOS neumí okno užší než ~500 px — `--window-size=320` se tiše
# klampne a test by měřil něco jiného, než tvrdí. Stránku proto vkládáme do
# iframu přesné šířky uvnitř širokého okna a měříme uvnitř něj.
HARNESS = """<!doctype html><meta charset="utf-8">
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
  const out = document.createElement('div');
  out.id = 'probe-result';
  out.textContent = JSON.stringify({
    viewport: w,
    scrollWidth: d.documentElement.scrollWidth,
    overflow: d.documentElement.scrollWidth - w,
    guilty: guilty.slice(0, 5),
  });
  document.body.appendChild(out);
}, 600));
</script>
"""


def measure(width: int) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        harness = Path(tmp) / "harness.html"
        harness.write_text(
            HARNESS.replace("PAGE_URL", PAGE.as_uri()).replace("WIDTH", str(width)),
            encoding="utf-8")
        res = subprocess.run(
            [CHROME, "--headless", "--disable-gpu", "--hide-scrollbars",
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
    if not Path(CHROME).exists():
        print("headless Chrome nenalezen, kontrola přeskočena", file=sys.stderr)
        return 0

    failed = False
    for w in args.widths:
        r = measure(w)
        ok = r["overflow"] <= 0
        failed |= not ok
        print(f"  {'✓' if ok else '✗'} {w:>5}px  scrollWidth={r['scrollWidth']:<6} přetečení={r['overflow']:>4}px")
        if not ok:
            for g in r["guilty"]:
                print(f"        viník: {g}")
    print("\nbez vodorovného přetečení" if not failed else "\nstránka se roztahuje do strany")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
