#!/usr/bin/env python3
"""Run axe-core against the built page in a real browser.

Not jsdom: it computes neither layout nor colour, so `color-contrast` ends up
"incomplete" there and a page with nothing visible on it still passes. Headless
Chrome is the only way to get a real answer.

Both themes and both a mobile and a desktop width: contrast differs between
light and dark, and a different layout exposes different elements.
"""
from __future__ import annotations

import argparse, json, re, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGE = ROOT / "dist" / "index.html"
# The country page has its own markup - a table with filters and pagination -
# and therefore its own contrast and control-naming risks.
PLACE = ROOT / "dist" / "cz" / "index.html"
AXE = ROOT / "node_modules" / "axe-core" / "axe.min.js"
CHROME: str | None = None  # resolved at runtime by find_chrome()

# (label, width, data-theme value)
SCENARIOS = [
    ("mobile / light", 390, "light"),
    ("mobile / dark", 390, "dark"),
    ("desktop / light", 1280, "light"),
    ("desktop / dark", 1280, "dark"),
]


def find_chrome() -> str | None:
    """Locate Chrome across platforms.

    A hard-coded path means the check silently does not run in CI while
    someone believes it guards something. Order: CHROME_PATH, then the usual
    locations.
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

def run_axe(width: int, theme: str) -> dict:
    html = PAGE.read_text(encoding="utf-8")
    # The theme is stamped on :root the same way the artifact viewer does it.
    html = html.replace('<html lang="cs">', f'<html lang="cs" data-theme="{theme}">')
    probe = f"""
<script>{AXE.read_text(encoding="utf-8")}</script>
<script>
window.addEventListener('load', () => setTimeout(() => {{
  axe.run(document, {{ resultTypes: ['violations'] }}).then(r => {{
    const out = document.createElement('div');
    out.id = 'axe-result';
    // Vedle nálezů se posílá i počet vykreslených řádků. Bez téhle podlahy
    // projde prázdná stránka: nemá co porušit, takže nemá nálezy a je
    // „v pořádku". Stejnou stráž má check_responsive.py.
    out.textContent = JSON.stringify({{ rows:
      document.querySelectorAll('[data-row], [data-card]').length,
      violations: r.violations.map(v => ({{
      id: v.id, impact: v.impact, help: v.help, nodes: v.nodes.length,
      target: v.nodes.slice(0, 2).map(n => n.target.join(' ')),
      summary: (v.nodes[0] && v.nodes[0].failureSummary || '').split('\\\\n').slice(0, 2).join(' '),
    }})) }});
    document.body.appendChild(out);
  }});
}}, 700));
</script>
"""
    # The probe is written **next to the original**, not into a temp directory.
    # A country page loads its runtime relatively (`../assets/atlas.js`); from a
    # temp directory it would not load, Alpine would not start, and axe would
    # report empty buttons - a false finding that looks like a page defect. The
    # main page is self-contained, so the difference never showed there.
    page = PAGE.with_name(f".a11y-{width}-{theme}.html")
    try:
        page.write_text(html.replace("</body>", probe + "</body>"), encoding="utf-8")
        res = subprocess.run(
            [CHROME, "--headless", "--disable-gpu", "--hide-scrollbars",
             "--virtual-time-budget=15000", f"--window-size={max(width, 520)},1200",
             "--dump-dom", page.as_uri()],
            capture_output=True, text=True, timeout=120)
    finally:
        page.unlink(missing_ok=True)
    m = re.search(r'<div id="axe-result">(.*?)</div>', res.stdout, re.S)
    if not m:
        raise SystemExit(f"axe returned no result ({width}px, {theme})")
    raw = m.group(1).replace("&quot;", '"').replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    return json.loads(raw)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--page", choices=("index", "place"), default="index",
                    help="which page to audit (default: index)")
    ap.add_argument("--impact", default="serious",
                    choices=["minor", "moderate", "serious", "critical"],
                    help="minimum impact that fails the run (default: serious)")
    args = ap.parse_args()
    global PAGE
    if args.page == "place":
        PAGE = PLACE

    if not PAGE.exists():
        raise SystemExit(f"missing {PAGE.relative_to(ROOT)} - run `just build` first")
    global CHROME
    CHROME = find_chrome()
    if CHROME is None:
        raise SystemExit(
            "headless Chrome not found. This gate measures a real browser, so with no\n"
            "browser there is nothing to measure - and a gate that reports success\n"
            "having looked at nothing is worse than one that is missing, because\n"
            "someone will rely on it. Install Google Chrome, or point CHROME_PATH at it.")

    order = ["minor", "moderate", "serious", "critical"]
    threshold = order.index(args.impact)
    failing = 0

    for label, width, theme in SCENARIOS:
        result = run_axe(width, theme)
        violations = result["violations"]
        if not result.get("rows"):
            print(f"  ✗ {label:<20} the page rendered no catalogue row - it is "
                  "empty, so auditing it proves nothing")
            failing += 1
            continue
        blocking = [v for v in violations
                    if order.index(v.get("impact") or "minor") >= threshold]
        failing += len(blocking)
        mark = "✓" if not blocking else "✗"
        print(f"  {mark} {label:<20} {len(violations)} findings"
              + (f", {len(blocking)} of them blocking" if blocking else ""))
        for v in violations:
            print(f"      [{v.get('impact')}] {v['id']} — {v['help']} ({v['nodes']}×)")
            for t in v["target"]:
                print(f"         {t}")

    print(f"\n{'no blocking findings' if not failing else f'{failing} blocking findings'}")
    return 1 if failing else 0


if __name__ == "__main__":
    raise SystemExit(main())
