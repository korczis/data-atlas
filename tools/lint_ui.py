#!/usr/bin/env python3
"""Enforce the Flowbite + Alpine.js conventions over the templates in src/.

The rules come from the official Flowbite documentation (llms.txt) and the
Alpine.js docs; their prose version lives in docs/UI-RULES.md. This script is
the enforcing half - a rule in a document stops nobody on its own.

Every rule is here because breaking it breaks something real. Each one says
what, so it can be judged whether it still makes sense.
"""
import re, subprocess, sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def tracked_files() -> set[str]:
    """Paths git actually carries, for the repo-link rule below.

    Not `Path.exists()`. A file can sit on the author's disk and be absent from
    every clone, and then a link the UI shows to a reader is a 404 while the
    gate stays green - the same shape of hole as the three closed in
    4a26166, only pointed outward at readers instead of inward at us.

    A missing git is not a reason to skip the rule quietly. Nothing in this
    repository builds outside a checkout, so an unreadable index means the
    environment is wrong, and saying so beats measuring nothing.
    """
    try:
        out = subprocess.run(["git", "-C", str(ROOT), "ls-files", "-z"],
                             capture_output=True, text=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError) as exc:
        raise SystemExit(f"lint_ui: cannot read the git index ({exc}) - the "
                         "ui/repo-link rule needs it and will not run blind")
    names = {n for n in out.split("\0") if n}
    if not names:
        raise SystemExit("lint_ui: git reports an empty index - refusing to "
                         "check repository links against nothing")
    return names


TRACKED = tracked_files()

# The templates the rules apply to. The country page is a second template with
# the same risks - Flowbite dropdowns, x-for over a table, dark mode - so it
# goes through the same rules. Guarding only the main page would leave the gate
# blind to half the site.
#
# `scripts` is JS the template does not carry inside itself. The main page holds
# its Alpine component in a <script>; the country page keeps it in
# src/js/place.js and the build appends it at generation time. Without this the
# alpine/data and flowbite rules would fail on code that exists and merely sits
# in the next file.
#
# `closes` is markup the build appends after the template. src/country.html ends
# inside <body>, because tools/build_places.py adds </body></html> after the
# injected <script> tags. The tag-balance check would otherwise report a <body>
# that never closes - a finding about how the build is assembled, not about the
# template.
TEMPLATES = (
    {"path": ROOT / "src" / "template.html", "scripts": (), "closes": ""},
    {"path": ROOT / "src" / "country.html",
     "scripts": (ROOT / "src" / "js" / "place.js",), "closes": "</body>"},
)

problems: list[tuple[str, str]] = []


def tag(name: str) -> str:
    """Opening-tag pattern that tolerates '>' inside an attribute value.

    A naive `<svg[^>]*>` stops at `x-show="i > 0"` and then cannot see the
    attributes after it - the linter reported a missing aria-hidden on a tag
    that has one. A false alarm is worse than no rule: it teaches people to
    ignore the output.
    """
    return rf"""<{name}\b(?:[^>"']|"[^"]*"|'[^']*')*>"""


def fail(rule: str, detail: str) -> None:
    problems.append((rule, detail))


def line_of(text: str, idx: int) -> int:
    return text.count("\n", 0, idx) + 1


VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link",
        "meta", "param", "source", "track", "wbr"}


class Structure(HTMLParser):
    """Check that block tags close, and in the right order.

    Grew out of a defect that took the whole page down and **passed every other
    gate**: a missing `</aside>` nested `#main-content` inside the sidebar.
    Every row was in the DOM, so the jsdom tests passed; the panel is off-canvas
    below `lg`, so the overflow measurement found nothing; and axe reported
    nothing, because the content formally existed. In the browser the page was
    blank.

    A browser silently balances broken tags - which is why a linter has to catch
    this, not a test in the DOM.
    """

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack: list[tuple[str, int]] = []
        self.problems: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag not in VOID:
            self.stack.append((tag, self.getpos()[0]))

    def handle_startendtag(self, tag, attrs):
        pass

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        if not self.stack:
            self.problems.append(f"line {self.getpos()[0]}: </{tag}> with no opening tag")
            return
        if self.stack[-1][0] == tag:
            self.stack.pop()
            return
        # Something other than the top of the stack is being closed - find out
        # whether it is open at all, and report what was left unclosed between.
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                unclosed = ", ".join(f"<{t}> from line {ln}" for t, ln in self.stack[i + 1:])
                self.problems.append(
                    f"line {self.getpos()[0]}: </{tag}> closes across unclosed {unclosed}")
                del self.stack[i:]
                return
        self.problems.append(f"line {self.getpos()[0]}: </{tag}> with no opening tag")


class MinWidth(HTMLParser):
    """Catch a fixed minimum width with nothing to absorb it.

    Two things can absorb it: horizontal scroll (the content scrolls away) or
    wrapping (`flex-wrap` - the element drops to the next line). Anything else
    pushes the document wider, which at 320px means the whole page scrolls
    sideways.

    It asks about **ancestors**, not about a window in the text. The original
    version looked back 600 characters and was wrong in both directions: with
    long Tailwind class strings it never reached the parent and reported a false
    finding, while an `overflow-x-auto` on a mere *sibling* satisfied it.
    """

    ESCAPES = ("overflow-x-auto", "overflow-auto", "flex-wrap")

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack: list[str] = []
        self.problems: list[str] = []

    def _look(self, tag, attrs) -> str:
        cls = dict(attrs).get("class") or ""
        m = re.search(r"min-w-\[[^\]]+\]", cls)
        if m and not any(e in a for a in self.stack for e in self.ESCAPES):
            self.problems.append(
                f"line {self.getpos()[0]}: '{m.group(0)}' with no ancestor "
                "having overflow-x-auto or flex-wrap")
        return cls

    def handle_starttag(self, tag, attrs):
        cls = self._look(tag, attrs)
        if tag not in VOID:
            self.stack.append(cls)

    def handle_startendtag(self, tag, attrs):
        self._look(tag, attrs)

    def handle_endtag(self, tag):
        if tag not in VOID and self.stack:
            self.stack.pop()


def check(html: str, extra_script: str = "") -> None:
    # Body without <script> - markup rules have no business reading the JS.
    #
    # Blanked, not deleted. Deleting the blocks pulled every later line up, so
    # the line numbers in the findings were wrong by however much JS sat above
    # them - a repo-link finding on line 696 was reported as 686, and the drift
    # grew further down the file. A rule that points at the wrong line is the
    # false alarm this file warns about elsewhere: it teaches people to stop
    # reading the output. Newlines in, characters out.
    markup = re.sub(r"<script\b.*?</script>",
                    lambda m: "\n" * m.group(0).count("\n"), html, flags=re.S)
    script = "\n".join(re.findall(r"<script\b.*?>(.*?)</script>", html, flags=re.S))
    # The country page's component lives outside the template, but for the JS
    # rules it is the same code, because the build injects it into that page.
    script += "\n" + extra_script

    # ── Structure: balanced tags ──────────────────────────────────────────────
    structure = Structure()
    structure.feed(re.sub(r"<!--.*?-->", "", markup, flags=re.S))
    for problem in structure.problems:
        fail("html/structure", problem)
    for name, line in structure.stack:
        fail("html/structure", f"line {line}: <{name}> never closes")

    # ── Flowbite: how it binds to Alpine ──────────────────────────────────────
    # Flowbite can do two things: `data-*` attributes walked by a **single DOM
    # scan** at start-up, and plain classes (Dropdown, Drawer) with destroy().
    # Only the second fits Alpine - Alpine renders after start-up and throws
    # nodes away on every re-filter, so anything bound by the scan is dead
    # afterwards: visible, looking right, doing nothing, with no console error.
    #
    # The project therefore binds Flowbite with the `x-flowbite` directive
    # (src/js/flowbite-entry.js), which builds the instance when Alpine creates
    # the node and destroys it when Alpine discards it. `data-*` attributes are
    # consequently forbidden outright - nothing scans them, so they would
    # silently do nothing.
    FLOWBITE_ATTRS = r"data-(drawer|dropdown|modal|tooltip|popover|accordion|tabs|collapse|dial|carousel)-[a-z-]+"
    for m in re.finditer(FLOWBITE_ATTRS, markup):
        fail("flowbite/binding",
             f"line {line_of(markup, m.start())}: '{m.group(0)}' - Flowbite binds through "
             "the x-flowbite directive; nothing scans this attribute and it stays dead")

    # Comments are stripped: a mention in a note ("no initFlowbite()") is not a
    # call, and a rule that scolds an explanation of itself teaches people to
    # ignore the output.
    code = re.sub(r"/\*.*?\*/", "", script, flags=re.S)
    code = re.sub(r"^\s*//.*$", "", code, flags=re.M)
    if re.search(r"\binitFlowbite\b", code):
        fail("flowbite/binding",
             "initFlowbite() is called - the project binds Flowbite through x-flowbite, "
             "and a one-shot DOM scan would bind a second time over what the "
             "directive already built")

    # The directive must name a supported component and an existing target.
    # Both are statically knowable while the target is a literal - and writing
    # it as an expression just to hide it from the linter would be evading the
    # gate, not solving anything.
    SUPPORTED = {"dropdown", "drawer"}
    ids = set(re.findall(r'\bid="([^"]+)"', markup))
    for m in re.finditer(r'x-flowbite:([a-z-]*)="([^"]*)"', markup):
        comp, expr = m.group(1), m.group(2).strip()
        line = line_of(markup, m.start())
        if comp not in SUPPORTED:
            fail("flowbite/binding",
                 f"line {line}: x-flowbite:{comp or '(missing)'} - supported are "
                 + ", ".join(sorted(SUPPORTED)))
        literal = re.fullmatch(r"'([^']+)'", expr) or re.fullmatch(r'&#39;([^&]+)&#39;', expr)
        if literal and literal.group(1) not in ids:
            fail("flowbite/binding",
                 f"line {line}: x-flowbite:{comp} points at #{literal.group(1)}, "
                 "which is not in the template")

    # ── Links into the repository must resolve ────────────────────────────────
    # The template links to documentation by absolute GitHub address. When a file
    # is renamed or split, the link in the UI keeps pointing at the old name and
    # nobody notices - the Markdown checker cannot see into HTML. That just
    # happened: "Schéma, číselníky a pravidla klasifikace" pointed at a plan the
    # schema had meanwhile moved out of.
    #
    # The target has to be *tracked*, not merely present. `blob/main/<path>` is
    # resolved by GitHub against the pushed branch, so an untracked file makes
    # the link a 404 for every reader while it opens fine for whoever wrote it.
    for m in re.finditer(r"blob/[^/]+/([A-Za-z0-9._/-]+\.(?:md|csv|json))", markup):
        target = m.group(1)
        if target not in TRACKED:
            why = ("is untracked - commit it, or the link 404s for everyone but you"
                   if (ROOT / target).exists() else "is not in the repository")
            fail("ui/repo-link",
                 f"line {line_of(markup, m.start())}: link points at {target}, which {why}")

    # ── The radius scale is closed ────────────────────────────────────────────
    # Tailwind offers six steps, the project uses four: `rounded-sm` for the tiny
    # legend squares, `rounded` for badges, `rounded-lg` for controls and cards,
    # `rounded-full` for pills. The intermediate steps add no meaning, only
    # difference - the same count badge was `rounded-md` in the header and
    # `rounded` everywhere else, which is exactly the quiet inconsistency nobody
    # reports and everybody sees.
    RADII_OK = {"rounded-sm", "rounded", "rounded-lg", "rounded-full"}
    for m in re.finditer(r"\brounded(?:-(?:sm|md|lg|xl|2xl|3xl|full|none))?\b", markup):
        if m.group(0) not in RADII_OK:
            fail("ui/radius",
                 f"line {line_of(markup, m.start())}: '{m.group(0)}' is not in the scale - "
                 + ", ".join(sorted(RADII_OK)))

    # ── Flowbite: RTL and logical properties ──────────────────────────────────
    # Flowbite 2.x runs on logical properties because of RTL mode.
    directional = {
        r"\bml-\d": "ms-", r"\bmr-\d": "me-", r"\bpl-\d": "ps-", r"\bpr-\d": "pe-",
        r"\bleft-\d": "start-", r"\bright-\d": "end-",
        r"\btext-left\b": "text-start", r"\btext-right\b": "text-end",
    }
    for pattern, replacement in directional.items():
        for m in re.finditer(pattern, markup):
            fail("flowbite/rtl",
                 f"line {line_of(markup, m.start())}: '{m.group(0)}' - use the logical "
                 f"variant '{replacement}' (Flowbite RTL)")

    # ── Flowbite: dark mode ───────────────────────────────────────────────────
    # A colour without a dark: counterpart means black text on a black ground.
    for m in re.finditer(r'class="([^"]*)"', markup):
        cls = m.group(1)
        if "dark:" in cls:
            continue
        for token in ("bg-white", "bg-gray-50", "bg-gray-100", "text-gray-900", "text-gray-500"):
            if re.search(rf"\b{token}\b", cls):
                fail("flowbite/dark",
                     f"line {line_of(markup, m.start())}: '{token}' without a dark: counterpart")
                break

    # ── Alpine: keys in x-for ─────────────────────────────────────────────────
    # A duplicate or missing :key takes down the whole list, not one row.
    for m in re.finditer(tag("template"), markup):
        if "x-for" not in m.group(0):
            continue
        if ":key" not in m.group(0):
            fail("alpine/key",
                 f"line {line_of(markup, m.start())}: x-for without :key")

    # ── Alpine: x-cloak ───────────────────────────────────────────────────────
    # Without it the unrendered template flashes before Alpine starts.
    # The root is searched among **all** opening tags, not just <div>: the
    # country page has x-data on <body>. This also used to slice `markup` with an
    # index taken from an already-sliced section, so the search bounced between
    # two positions and looped forever on a template with no <div x-data> - the
    # linter hung instead of reporting anything.
    any_tag = rf"""<([a-zA-Z][a-zA-Z0-9-]*)\b(?:[^>"']|"[^"]*"|'[^']*')*>"""
    root = next((m for m in re.finditer(any_tag, markup) if "x-data=" in m.group(0)), None)
    if "x-data=" in markup and root is None:
        fail("alpine/cloak", "x-data is in the template but not on an opening tag")
    if root and "x-cloak" not in root.group(0):
        fail("alpine/cloak", f"the root x-data (<{root.group(1)}>) has no x-cloak")
    # The rule may also live in the shared input.css - it moved there when the
    # country pages started needing it. What is guarded is that it exists, not
    # where it sits.
    shared = (ROOT / "src" / "input.css")
    css_sources = html + (shared.read_text(encoding="utf-8") if shared.exists() else "")
    if "[x-cloak]" not in css_sources:
        fail("alpine/cloak",
             "no CSS rule for [x-cloak] in the template or in src/input.css")

    # ── Alpine: registrace komponenty ─────────────────────────────────────────
    # Alpine.data() keeps the logic out of the global namespace.
    if "x-data=" in markup and "Alpine.data(" not in script:
        fail("alpine/data",
             "the component is not registered through Alpine.data() inside alpine:init")

    # ── Alpine: debounce on search ────────────────────────────────────────────
    # Filtering on every keystroke re-renders the whole list.
    if re.search(r'type="search"', markup):
        m = re.search(r'type="search"[^>]*', markup)
        if m and "debounce" not in m.group(0):
            fail("alpine/debounce", "the search input has no x-model.debounce")

    # ── Accessibility ─────────────────────────────────────────────────────────
    for m in re.finditer(tag("button") + r"(.*?)</button>", markup, re.S):
        open_tag, inner = m.group(0), m.group(1)
        # inner is the content BETWEEN the tags, so no '>' is searched there -
        # only the text left after nested elements are removed.
        text = re.sub(r"<[^>]*>", "", inner).strip()
        named = bool(text) or "aria-label" in open_tag or "x-text" in open_tag \
            or "x-text" in inner or "sr-only" in inner
        if not named:
            fail("a11y/button-name",
                 f"line {line_of(markup, m.start())}: button with no accessible name")

    for m in re.finditer(tag("svg"), markup):
        if "aria-hidden" not in m.group(0) and "role=" not in m.group(0):
            fail("a11y/svg",
                 f"line {line_of(markup, m.start())}: decorative <svg> without aria-hidden=\"true\"")

    for m in re.finditer(tag("input"), markup):
        ident_m = re.search(r'\bid="([^"]+)"', m.group(0))
        if not ident_m:
            continue
        ident = ident_m.group(1)
        if f'for="{ident}"' not in markup and "aria-label" not in m.group(0):
            fail("a11y/label", f"input #{ident} has neither <label for> nor aria-label")

    # A toggle must report its state, or a screen reader never learns it.
    for m in re.finditer(tag("button"), markup):
        open_tag = m.group(0)
        if ":class=" in open_tag and re.search(r"@click=\"[a-zA-Z]+ ?=", open_tag):
            if "aria-pressed" not in open_tag and "aria-current" not in open_tag:
                fail("a11y/toggle-state",
                     f"line {line_of(markup, m.start())}: toggle without aria-pressed/aria-current")

    # ── Mobile-first ──────────────────────────────────────────────────────────
    widths = MinWidth()
    widths.feed(markup)
    for problem in widths.problems:
        fail("responsive/min-width", problem)

    # Breakpoints stack upwards; max-* goes the other way.
    for m in re.finditer(r"\bmax-(sm|md|lg|xl):", markup):
        fail("responsive/mobile-first",
             f"line {line_of(markup, m.start())}: '{m.group(0)}' - write mobile-first (min-width)")


def report(path: Path) -> None:
    by_rule: dict[str, list[str]] = {}
    for rule, detail in problems:
        by_rule.setdefault(rule, []).append(detail)
    print(f"\n{path.relative_to(ROOT)}")
    for rule, details in sorted(by_rule.items()):
        print(f"  {rule} ({len(details)})")
        for d in details[:12]:
            print(f"    {d}")
        if len(details) > 12:
            print(f"    … and {len(details) - 12} more")


def main() -> int:
    global problems
    found = 0
    for tpl in TEMPLATES:
        path: Path = tpl["path"]
        if not path.exists():
            raise SystemExit(f"missing {path}")
        problems = []
        extra = "\n".join(js.read_text(encoding="utf-8") for js in tpl["scripts"])
        check(path.read_text(encoding="utf-8") + tpl["closes"], extra)
        if problems:
            report(path)
            found += len(problems)
        else:
            print(f"lint_ui: {path.relative_to(ROOT)} — no findings")

    if found:
        print(f"\nlint_ui: {found} findings", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
