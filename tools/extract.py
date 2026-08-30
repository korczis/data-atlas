#!/usr/bin/env python3
"""Vytáhne záložky a historii z Chrome profilu do .cache/raw.json.

Běží jen lokálně — potřebuje profil na disku. Historii Chrome drží zhruba
90 dní, takže starší návštěvy v datech prostě nejsou.

Pozn.: u účtu přihlášeného ke Google jsou záložky v `AccountBookmarks`,
nikoli v `Bookmarks`. Čtou se oba, pokud existují.
"""
import argparse, json, shutil, sqlite3, tempfile
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PROFILE = Path.home() / "Library/Application Support/Google/Chrome/Default"
# Chrome počítá čas v mikrosekundách od 1601-01-01
CHROME_EPOCH_OFFSET = 11644473600


def bookmarks(path: Path, rows: list) -> None:
    def walk(node, folders):
        if node.get("type") == "url":
            rows.append(dict(url=node.get("url", ""), title=node.get("name", ""),
                             source="bookmark", visits=0, last="",
                             folder="/".join(folders)))
        nested = folders + [node.get("name", "")] if node.get("type") == "folder" else folders
        for child in node.get("children", []):
            walk(child, nested)

    for name in ("AccountBookmarks", "Bookmarks"):
        f = path / name
        if not f.exists():
            continue
        for root in json.loads(f.read_text(encoding="utf-8"))["roots"].values():
            if isinstance(root, dict):
                walk(root, [])
        break  # AccountBookmarks je nadmnožina, druhý soubor by duplikoval


def history(path: Path, rows: list) -> None:
    f = path / "History"
    if not f.exists():
        return
    # Chrome drží soubor zamčený; pracujeme nad kopií
    with tempfile.TemporaryDirectory() as tmp:
        copy = Path(tmp) / "History"
        shutil.copy2(f, copy)
        con = sqlite3.connect(copy)
        q = ("select url, title, visit_count, "
             f"datetime(last_visit_time/1000000-{CHROME_EPOCH_OFFSET},'unixepoch') from urls")
        for url, title, visits, last in con.execute(q):
            rows.append(dict(url=url or "", title=title or "", source="history",
                             visits=visits or 0, last=last or "", folder=""))
        con.close()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--profile", type=Path, default=DEFAULT_PROFILE,
                    help="Chrome profile directory (default: Default)")
    args = ap.parse_args()
    if not args.profile.is_dir():
        raise SystemExit(f"Chrome profile not found: {args.profile}")

    rows: list = []
    bookmarks(args.profile, rows)
    history(args.profile, rows)
    for r in rows:
        host = (urlsplit(r["url"]).hostname or "").lower().lstrip(".")
        r["domain"] = host[4:] if host.startswith("www.") else host

    (ROOT / ".cache").mkdir(exist_ok=True)
    out = ROOT / ".cache" / "raw.json"
    out.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
    domains = {r["domain"] for r in rows if r["domain"]}
    print(f"{len(rows)} records, {len(domains)} domains -> {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
