# Sāgarasaṅgama

**सागरसङ्गमः** — "Meeting of Oceans"

Sāgarasaṅgama is a virtual meeting of oceans for large online Sanskrit e-text
collections. Each component project gets its own **Atlas** interface, and
Sāgarasaṅgama sums over them.

Served at https://sagarasangama.info.

`CLAUDE.md` has the refresh shape, the rate terms, and the growth chart's known
traps. The rest of this file covers what the site is and how to run it.

## Atlases

| Atlas | Collection |
| --- | --- |
| [`sanskrit-wikisource-atlas`](https://github.com/tylergneill/sanskrit-wikisource-atlas) | [Sanskrit Wikisource](https://sa.wikisource.org) |
| [`e-bharatisampat-atlas`](https://github.com/tylergneill/e-bharatisampat-atlas) | [E-bhāratīsampat](https://ebharatisampat.in) |
| [`sanskrit-documents-atlas`](https://github.com/tylergneill/sanskrit-documents-atlas) | [Sanskrit Documents](https://sanskritdocuments.org) |
| [`jain-quantum-atlas`](https://github.com/tylergneill/jain-quantum-atlas) | [Jain Quantum](https://jainqq.org) / [Jain eLibrary](https://jainelibrary.org) |
| [`gretil-atlas`](https://github.com/tylergneill/gretil-atlas) | [GRETIL](https://tylergneill.github.io/gretil-mirror/gretil.html) |

## How the numbers get here

Sāgarasaṅgama reads each Atlas's published `docs/data/` and nothing else —
`tree.json` for the totals and the search index, `changelog.json` for the
growth series — never an Atlas's pipeline scripts, working files, or caches. A
figure an Atlas has computed but not published is not ours to reach in for;
that fix belongs upstream. See [CONTRACT.md](CONTRACT.md).

```sh
make data        # re-read the Atlases: counts.json + growth.json + search.json
make serve       # serve docs/ on :8000
```

## Search

`docs/search.html` searches titles across all three collections at once. Three
collections organised three incompatible ways share no hierarchy to browse, but
they do share titles, so search is the whole interface and the one grouping
offered — **group by atlas** — is the one that is real.

Every row keeps what its own Atlas gives it: per-script downloads for Sanskrit
Documents, separate text and PDF editions for E-bhāratīsampat, chapter counts
and scan links for Wikisource. Typing in IAST finds Devanāgarī and
unmarked-ASCII titles alike. Query, grouping, scheme and collection filters all
live in the URL, so a result list can be linked to.

## Maintaining the Atlases

Each Atlas owns its own pipeline. This repo does not reimplement any of it —
but it does keep the map, because the three refresh differently and the costs
differ by orders of magnitude.

```sh
make steps       # the essential steps for each Atlas, in order, with costs
make status      # diff the published files against their sources
```

Every step has a delegating target here (`ws-`, `ebs-`, `sd-`), so you can run
them one at a time from one place. They are deliberately **not** chained into a
single "refresh everything" recipe — the expensive steps run for hours, and
which one to run next is a judgment call, not a dependency.

## Themes

Three, cycled by the toggle at the top right and remembered in `localStorage`:
**light** → **dark** → **wave** — the last a cerulean palette under a band of
foliate scrollwork that drifts slowly back and forth behind the page.

```sh
make scroll      # write docs/assets/scroll.svg
```

## License

[CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/deed.en).
Applies to this repo's own code and the aggregate metadata it derives; the
texts themselves belong to the three source collections and their contributors.
