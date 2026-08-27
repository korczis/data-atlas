#!/usr/bin/env python3
"""Spustí axe-core nad postavenou stránkou v reálném prohlížeči.

Proč ne v jsdom: jsdom nepočítá layout ani barvy, takže pravidlo
`color-contrast` v něm skončí jako "incomplete" a projde i stránka, na které
není nic vidět. Headless Chrome je jediný způsob, jak dostat skutečný výsledek.

Testuje se v obou motivech a na mobilní i desktopové šířce — kontrast se mezi
světlým a tmavým režimem liší a jiné rozvržení odhalí jiné prvky.
"""
from __future__ import annotations

import argparse, json, re, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGE = ROOT / "dist" / "index.html"
AXE = ROOT / "node_modules" / "axe-core" / "axe.min.js"
CHROME: str | None = None  # zjistí se v runtime přes find_chrome()

# (popisek, šířka, hodnota data-theme)
SCENARIOS = [
    ("mobil / světlý", 390, "light"),
    ("mobil / tmavý", 390, "dark"),
    ("desktop / světlý", 1280, "light"),
    ("desktop / tmavý", 1280, "dark"),
]


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

def run_axe(width: int, theme: str) -> dict:
    html = PAGE.read_text(encoding="utf-8")
    # Motiv se razí na :root stejně, jako to dělá prohlížeč artefaktů.
    html = html.replace('<html lang="cs">', f'<html lang="cs" data-theme="{theme}">')
    probe = f"""
<script>{AXE.read_text(encoding="utf-8")}</script>
<script>
window.addEventListener('load', () => setTimeout(() => {{
  axe.run(document, {{ resultTypes: ['violations'] }}).then(r => {{
    const out = document.createElement('div');
    out.id = 'axe-result';
    out.textContent = JSON.stringify(r.violations.map(v => ({{
      id: v.id, impact: v.impact, help: v.help, nodes: v.nodes.length,
      target: v.nodes.slice(0, 2).map(n => n.target.join(' ')),
      summary: (v.nodes[0] && v.nodes[0].failureSummary || '').split('\\\\n').slice(0, 2).join(' '),
    }})));
    document.body.appendChild(out);
  }});
}}, 700));
</script>
"""
    with tempfile.TemporaryDirectory() as tmp:
        page = Path(tmp) / "a11y.html"
        page.write_text(html.replace("</body>", probe + "</body>"), encoding="utf-8")
        res = subprocess.run(
            [CHROME, "--headless", "--disable-gpu", "--hide-scrollbars",
             "--virtual-time-budget=15000", f"--window-size={max(width, 520)},1200",
             "--dump-dom", page.as_uri()],
            capture_output=True, text=True, timeout=120)
    m = re.search(r'<div id="axe-result">(.*?)</div>', res.stdout, re.S)
    if not m:
        raise SystemExit(f"axe nevrátil výsledek ({width}px, {theme})")
    raw = m.group(1).replace("&quot;", '"').replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    return json.loads(raw)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--impact", default="serious",
                    choices=["minor", "moderate", "serious", "critical"],
                    help="od jaké závažnosti selhat (výchozí: serious)")
    args = ap.parse_args()

    if not PAGE.exists():
        raise SystemExit("chybí dist/index.html — spusť nejdřív `just build`")
    global CHROME
    CHROME = find_chrome()
    if CHROME is None:
        print("headless Chrome nenalezen, audit přeskočen "
              "(nastav CHROME_PATH)", file=sys.stderr)
        return 0

    order = ["minor", "moderate", "serious", "critical"]
    threshold = order.index(args.impact)
    failing = 0

    for label, width, theme in SCENARIOS:
        violations = run_axe(width, theme)
        blocking = [v for v in violations
                    if order.index(v.get("impact") or "minor") >= threshold]
        failing += len(blocking)
        mark = "✓" if not blocking else "✗"
        print(f"  {mark} {label:<20} {len(violations)} nálezů"
              + (f", z toho {len(blocking)} blokujících" if blocking else ""))
        for v in violations:
            print(f"      [{v.get('impact')}] {v['id']} — {v['help']} ({v['nodes']}×)")
            for t in v["target"]:
                print(f"         {t}")

    print(f"\n{'bez blokujících nálezů' if not failing else f'{failing} blokujících nálezů'}")
    return 1 if failing else 0


if __name__ == "__main__":
    raise SystemExit(main())
