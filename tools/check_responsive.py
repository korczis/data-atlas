#!/usr/bin/env python3
"""Measure in a real browser whether the page is visible and does not overflow.

jsdom knows the DOM but not layout - sideways overflow cannot be detected in it.
This script therefore runs headless Chrome at several widths and asks the page
directly whether `documentElement.scrollWidth` outgrew the viewport, and which
element is responsible.

Besides overflow it checks that the main content **actually occupies space**.
That came from a defect no other gate caught: a missing `</aside>` nested
`#main-content` inside the sidebar, which is off-canvas below `lg`, so the page
was blank - while every row was in the DOM (the jsdom tests passed), nothing
overflowed sideways (this probe passed) and axe reported nothing. Measuring
layout means also measuring that the content has non-zero area.

Below 1024px it additionally opens the sidebar and verifies it can be tapped -
a panel can be visible and still sit entirely under a backdrop that closes it.

Exits non-zero when the page spreads sideways or the content is not visible.
"""
from __future__ import annotations

import argparse, json, re, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGE = ROOT / "dist" / "index.html"
# The country page is its own template with its own table, filters and
# pagination - measuring only the main page would leave the gate blind to half
# the site. Czechia is used: most entries, longest descriptions, widest table.
PLACE = ROOT / "dist" / "cz" / "index.html"
CHROME: str | None = None  # resolved at runtime by find_chrome()

# widths it has to behave at: small phone -> phone -> tablet -> desktop
WIDTHS = [320, 360, 390, 414, 768, 1024, 1280, 1536]

# Chrome on macOS cannot open a window narrower than ~500px - `--window-size=320`
# is silently clamped and the test would measure something other than it claims.
# So the page is embedded in an iframe of the exact width inside a wide window
# and measured in there.
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
    // Off-canvas elements (fixed + translated away) are intent, not a defect.
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
  // The content must have non-zero area and must not be nested in the sidebar -
  // otherwise the page is "rendered" and blank at the same time.
  const main = d.getElementById('main-content');
  const side = d.getElementById('sidebar');
  const mainBox = main ? main.getBoundingClientRect() : { width: 0, height: 0 };
  const rows = [...d.querySelectorAll('table tbody tr[data-row], ul[role="list"] > li')]
    .filter(el => el.getBoundingClientRect().height > 0).length;
  // Inner scroll is a legitimate escape for a wide table, but it means some
  // columns are out of sight. For the catalogue that was a 1004px table in a
  // 768px window, so two columns vanished past the edge - hence the measurement.
  const box = d.querySelector('.scroll-x');
  const innerOverflow = box ? box.scrollWidth - box.clientWidth : 0;
  const EDGE = 8;   // tolerance for "anchored to the edge"

  // An overlap cannot be seen until the page is scrolled: `position: sticky`
  // does nothing before that. That is how a sticky table header covered the
  // first row while every gate passed. It is checked after scrolling and only
  // for elements that do *not* float at the top or bottom edge - content is
  // meant to pass under the top bar and over the summary bar, not mid-viewport.
  // Measured **at scroll 0**, and that is the whole trick. Until the first
  // scroll a sticky element holds its natural position, so there is nothing for
  // it to cover. If it covers something, its sticky context is being computed
  // from something other than one expects - which is exactly what `sticky top-16`
  // on the table header inside `overflow-x-auto` did: the wrapper became the
  // scroll container and the header ended up 4rem below its top edge, over the
  // section heading and the first row.
  //
  // After scrolling it *should* overlap - the sticky section headings in the
  // card view work exactly that way. Scrolling happens only to rule out
  // edge-anchored elements (top bar, summary bar, bottom nav) that content is
  // meant to pass under.
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
            + ` covers a row by ${Math.round(dy)}px at scroll ${y}`);
          break;
        }
      }
    }
  }
  // The drawer is tested last: opening it adds <body class="overflow-hidden">
  // and a backdrop, which would distort every measurement above this line.
  //
  // Asking whether the panel is visible after the click is not enough - it was
  // visible even when it could not be used. Flowbite builds its own backdrop
  // with a hard-wired `z-30` and appends it to the end of <body>. When the
  // panel also had `z-30` it lost on DOM order: the menu opened beneath the
  // dimming and every tap on it landed on the backdrop, which closed the drawer.
  // So we ask the only thing that matters: what is really at the pixel in the
  // middle of the open panel.
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
    drawer.atPixel = hit ? (hit.id || hit.tagName.toLowerCase() +
      (typeof hit.className === 'string' && hit.className
        ? '.' + hit.className.trim().split(/\s+/).slice(0, 2).join('.') : '')) : null;
    drawer.klikatelny = !!(hit && side.contains(hit));

    // Flowbite builds the backdrop at runtime, so Tailwind never sees its
    // classes and purges them. Without `inset-0` it has zero size: the drawer
    // opens without dimming and tapping beside it does not close it. It is in
    // the DOM all the same, so a presence check would pass - area and behaviour
    // are what get measured.
    const bd = d.querySelector('[drawer-backdrop]');
    drawer.backdrop = !!bd;
    if (bd) {
      const br = bd.getBoundingClientRect();
      drawer.backdropArea = Math.round(br.width) + 'x' + Math.round(br.height);
      drawer.backdropKryje = br.width >= w - 1 && br.height >= vh - 1;
      const mimo = d.elementFromPoint(w - 4, Math.round(Math.min(300, vh / 2)));
      drawer.backdropNahore = mimo === bd;
      bd.click();
      drawer.closes = Math.round(side.getBoundingClientRect().left) < 0;
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
    """Locate Chrome across platforms.

    A hard-coded path means the check silently does not run in CI while someone
    believes it guards something. Order: CHROME_PATH, then the usual locations.
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
            # Without transitions disabled we would measure an intermediate
            # state: at the moment of the click the drawer is still moving and
            # `left` is still -256px.
            [CHROME, "--headless", "--disable-gpu", "--hide-scrollbars",
             "--force-prefers-reduced-motion",
             "--allow-file-access-from-files", "--virtual-time-budget=6000",
             f"--window-size={max(width, 900) + 40},1000",
             "--dump-dom", harness.as_uri()],
            capture_output=True, text=True, timeout=90)
    m = re.search(r'<div id="probe-result">(.*?)</div>', res.stdout, re.S)
    if not m:
        raise SystemExit(f"probe returned no result for {width}px")
    return json.loads(m.group(1).replace("&quot;", '"').replace("&amp;", "&"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--widths", type=int, nargs="*", default=WIDTHS)
    ap.add_argument("--page", choices=("index", "place"), default="index",
                    help="which page to measure (default: index)")
    args = ap.parse_args()
    global PAGE
    if args.page == "place":
        PAGE = PLACE

    if not PAGE.exists():
        raise SystemExit("missing dist/index.html - run `just build` first")
    global CHROME
    CHROME = find_chrome()
    if CHROME is None:
        raise SystemExit(
            "headless Chrome not found. This gate measures a real browser, so with no\n"
            "browser there is nothing to measure - and a gate that reports success\n"
            "having looked at nothing is worse than one that is missing, because\n"
            "someone will rely on it. Install Google Chrome, or point CHROME_PATH at it.")

    failed = False
    for w in args.widths:
        r = measure(w)
        problems = []
        if r["overflow"] > 0:
            problems.append(f"overflows sideways by {r['overflow']}px")
        # A blank page shows up differently from overflow: the content is in
        # the DOM but occupies nothing - typically when it ends up nested inside
        # the off-canvas panel.
        if r["mainInSidebar"]:
            problems.append("#main-content is nested inside #sidebar")
        if r["mainWidth"] <= 0 or r["mainHeight"] <= 0:
            problems.append(f"main content occupies nothing ({r['mainWidth']}×{r['mainHeight']}px)")
        if r["visibleRows"] == 0:
            problems.append("not a single catalogue row is visible")
        # Cards (< md) render no table, so inner scroll is not measured there.
        if w >= 768 and r["innerOverflow"] > 0:
            problems.append(f"table is {r['innerOverflow']}px wider than the window "
                            "- columns disappear past the edge")
        for o in r.get("overlaps", []):
            problems.append(o)
        dr = r.get("drawer") or {}
        if dr.get("testovan"):
            if not dr.get("spoustecVidet"):
                problems.append("the hamburger is not visible, the panel cannot be opened")
            elif dr.get("left", -1) != 0 or dr.get("viditelnost") != "visible":
                problems.append(f"the panel did not open after the click "
                                f"(left={dr.get('left')}px, {dr.get('viditelnost')})")
            elif not dr.get("klikatelny"):
                problems.append("the open panel is covered by " + str(dr.get("atPixel"))
                                + " - a tap on the menu cannot reach it")
            elif not dr.get("backdrop"):
                problems.append("the drawer has no backdrop")
            elif not dr.get("backdropKryje"):
                problems.append(f"the backdrop measures {dr.get('backdropArea')} instead of "
                                "the full area - Tailwind purged the classes Flowbite "
                                "adds at runtime (safelist in tailwind.config.js)")
            elif not dr.get("backdropNahore"):
                problems.append("the backdrop does not sit above the content beside the drawer")
            elif not dr.get("closes"):
                problems.append("tapping beside the drawer does not close it")
        failed |= bool(problems)
        print(f"  {'✓' if not problems else '✗'} {w:>5}px  scrollWidth={r['scrollWidth']:<6} "
              f"overflow={r['overflow']:>4}px  content={r['mainWidth']}×{r['mainHeight']}px  "
              f"rows={r['visibleRows']}  table+{r['innerOverflow']}px"
              + ("  drawer ok" if not problems and (r.get("drawer") or {}).get("closes") else ""))
        for problem in problems:
            print(f"        {problem}")
        if r["overflow"] > 0:
            for g in r["guilty"]:
                print(f"        culprit: {g}")
    print("\nlayout ok" if not failed else "\nlayout is broken")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
