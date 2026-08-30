# CLAUDE.md — how to work in this repository

Read [`AGENTS.md`](AGENTS.md) first. It holds the invariants: source of truth,
generated files, verification, traps, privacy. This file does not repeat them —
it covers how to behave while changing things here.

If a CLAUDE.md from a parent workspace directory is also loaded — on the
maintainer's machine that is `~/dev/CLAUDE.md`, describing an Elixir umbrella
monorepo — **none of it applies here.** This repository has no Elixir, no
submodules, no `mix`. `just` is the entry point; Python 3 and Node are the only
runtimes.

## Inspect before you edit

Never infer this repository's architecture from a filename. Two things in
particular look ordinary and are not:

- `data/catalog.csv` reads like the catalogue and is a build artefact.
- `src/country.html` reads like a variant of `src/template.html` and is a second
  first-class template with its own generator, its own tests, and the same lint
  rules applied to it.

Before documenting a command, read the justfile. Before documenting a generated
file, read its generator. Before documenting a test, read the test. Prose that
exists is not evidence; it is the thing most likely to be stale.

## Work in small verified steps

One narrow change, one verification, then re-plan. Prefer the narrowest check
that can fail — `just validate` after a data edit, `just lint` after a template
edit — and keep `just check` for the end. A twenty-file change that passes
`just check` is still worse than five changes that each passed something.

Never batch unrelated edits because they happen to touch Markdown.

## Use the repository's own commands

`just` is the interface. Do not hand-write a substitute for a recipe, and do not
invent one: `just --list` is the complete set of public recipes — the private
`_`-prefixed ones exist but are not for you to call — and `tools/check_docs.py`
fails the build if documentation, or `just help` itself, names a recipe that
does not exist.

If a documented command does not work, that is a bug in the repository, not an
obstacle to route around. Fix the layer that is wrong.

## Source fixes versus generated output

When a generated file looks wrong, the defect is upstream — in
`data/sources/*.json` or in the generator. Fix it there and regenerate. Editing
the artefact produces a change that disappears and a CI failure that looks
unrelated to what you did.

When a generated file legitimately changes because you changed its input, commit
it alongside the input. CI compares the two.

## Data changes

Verify the URL first, then write the description. `access` and `data` describe
what a source really yields, not what its homepage claims; a browsable register
is `search`, not `api`. Leave `unknown` rather than guessing a licence. The
vocabularies and the workflow are in
[`docs/DATA-MODEL.md`](docs/DATA-MODEL.md).

Adding a country needs no code: `data/sources/<CODE>.json` plus an entry in
`data/countries.json`, and the country page, sitemap entry and coverage row all
follow from `just check`.

## Network

Of the checks, only `just links` needs the network, and it is not in
`just check`. `just flags` and `just install` need it too, and `just e2e` shells
to `npx`. If you cannot reach the network, say so and run
`just links --changed` later — do not mark link verification as done, and do not
substitute a guess about whether a URL resolves.

## Reporting

State what you verified and with which command. If a check was skipped, say it
was skipped. If a change is unverifiable in this environment — anything visual
beyond what `just responsive`, `just typography` and `just a11y` measure — say
that, and point at `just shots`.

Do not claim a rule is enforced unless you have seen the code that enforces it.

## Do not

- Refactor for architectural taste. The objective is correctness, clarity and
  enforceability; boring systems that fail loudly beat elegant ones.
- Weaken `just check`, or move a check out of it to make something pass.
- Let a check report success when it did not run. This repository has produced
  that bug five times: three measuring gates returned success when no Chrome was
  installed; `just links` reported success on an empty selection; the drawer
  probe in `check_responsive.py` searched for a `data-drawer-toggle` attribute
  the linter forbids, so eight assertions silently never ran; the typography and
  a11y gates passed a page that rendered nothing; and six narrow checks measured
  whatever the previous build had left in `dist/`. All are fixed. A gate that
  goes green without looking is worse than a missing gate, because someone relies
  on it. If a prerequisite is missing or the population you measured is empty,
  fail and say what to do.
- Replace the project's Flowbite/Alpine binding with upstream defaults.
- Type a count into prose.
- Commit `dist/`, `.cache/`, or anything derived from a browser profile beyond
  `data/provenance.csv` and `data/longlist.csv`.
