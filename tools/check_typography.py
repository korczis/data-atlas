#!/usr/bin/env python3
"""Measure typography in headless Chrome: measure, field font size, headings.

Exists for the same reason as check_responsive.py - none of this is visible in
the markup. `max-w-3xl` looks like a sensible cap but it is 768px: at 14px text
that is 89 characters and at 12px it is 129. Readable is 45 to 75. The cap has
to be measured in characters rather than pixels, which is only possible once
the page is laid out.

Three rules, each from a concrete defect:

1. **No field under 16px on mobile.** iOS Safari zooms the whole page when
   focus enters a smaller field - the reader taps search and the layout jumps.
   14px is fine on desktop, which is why this is measured per width.
2. **No running text over 85 characters per line.** On a long line the eye
   loses the return sweep and re-reads the line it just finished.
3. **No skipped heading levels.** Screen readers use them as a table of
   contents.

Short paragraphs in narrow cards (under 40 characters) are not reported: there
it is the layout's intent, not a typography defect.
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
MAX_MEASURE = 85          # characters per line
MIN_INPUT_PX = 16         # below this iOS zooms
MOBILE_MAX = 640          # the field rule applies up to this width

PROBE = r"""
<script>
window.onerror = m => /ResizeObserver/.test(m) ? true : undefined;
window.addEventListener('load', () => setTimeout(() => {
  // Kolik řádků katalogu je vidět. Bez téhle podlahy projde prázdná stránka:
  // nemá dlouhé řádky, nemá pole ani přeskočené nadpisy, takže je „v pořádku".
  // Stejnou stráž má check_responsive.py; těmhle dvěma chyběla.
  const out = { long: [], small: [], skips: [],
                rows: document.querySelectorAll('[data-row], [data-card]').length };
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
    // Line length only means anything in normal text flow. For a flex or
    // grid container the element's width is the distance between its outer
    // children, not a line - the matrix caption measured 100 characters while
    // actually being two short labels at opposite ends.
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
    # The probe is written next to the original rather than into a temp
    # directory: a country page loads its runtime relatively and would not
    # start from elsewhere - same reason as in check_a11y.py.
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
        raise SystemExit(f"probe returned no result ({page.name}, {width}px)")
    import html as H
    return json.loads(H.unescape(m.group(1)))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--page", choices=tuple(PAGES), default="index")
    args = ap.parse_args()

    page = PAGES[args.page]
    if not page.exists():
        raise SystemExit(f"missing {page.relative_to(ROOT)} - run `just build` first")
    chrome = find_chrome()
    if chrome is None:
        raise SystemExit(
            "headless Chrome not found. This gate measures a real browser, so with no\n"
            "browser there is nothing to measure - and a gate that reports success\n"
            "having looked at nothing is worse than one that is missing, because\n"
            "someone will rely on it. Install Google Chrome, or point CHROME_PATH at it.")

    problems = 0
    for width in WIDTHS:
        r = measure(chrome, page, width)
        bad = []
        for x in r["long"]:
            bad.append(f"line of {x['ch']} characters (max {MAX_MEASURE}) - {x['text']}…")
        # The field font-size rule is about the mobile browser.
        if width <= MOBILE_MAX:
            for x in r["small"]:
                bad.append(f"field #{x['id']} is {x['px']}px - under {MIN_INPUT_PX}px "
                           "iOS Safari zooms the page on focus")
        for x in r["skips"]:
            bad.append(f"skipped heading level {x}")
        if not r.get("rows"):
            bad.append("no catalogue row rendered - the page is empty, so measuring "
                       "it proves nothing")
        mark = "✓" if not bad else "✗"
        print(f"  {mark} {width:>5}px  {len(r['long'])} long lines · "
              f"{len(r['small'])} small fields · {len(r['skips'])} heading skips")
        for b in bad:
            print(f"      {b}")
        problems += len(bad)

    print("\ntypography ok" if not problems else f"\n{problems} typography findings", file=sys.stderr if problems else sys.stdout)
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
