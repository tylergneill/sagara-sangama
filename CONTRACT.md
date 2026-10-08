# The published contract

Sāgarasaṅgama holds no corpus. Every figure it shows is read from the Atlases,
and this is the rule for how:

> **Sāgarasaṅgama reads each Atlas's published `docs/data/`, and nothing
> else** — `tree.json` for the totals and the search index, `changelog.json`
> for the growth series.

Not an Atlas's pipeline scripts, not its `data/` working files, not its caches
or intermediate JSONL. Only the artifacts each Atlas already publishes to build
its own site.

## Why

An Atlas's `docs/data/tree.json` and `docs/data/changelog.json` are deliberate
outputs: the things its own frontend consumes, whose shape it maintains and
whose numbers it stands behind. Everything under `data/` is working state — a
fetch cache, a size measurement, a parse intermediate. Those change shape when
a pipeline is refactored, exist only on the machine that ran the job, and carry
no promise about meaning.

Reading them would make Sāgarasaṅgama break every time an Atlas reorganized its
internals, and — worse — would let it publish a number the Atlas itself had not
chosen to publish. If a figure is not in `tree.json`, the Atlas is not yet
asserting it.

## What this means in practice

**A missing figure is not a gap to route around.** When a number this layer
wants is absent, the fix belongs upstream, in the Atlas that owns it. The Atlas
computes it into `all_stats`; Sāgarasaṅgama picks it up on the next
`make counts` with no change here.

Two worked examples:

- **E-bhāratīsampat's byte sizes.** Its `tree.json` reported `sized: 0` while
  the sizes sat measured in `data/text_sizes.jsonl`. The tempting shortcut was
  to read that file. The right fix was ten lines in the Atlas's `build_tree.py`
  to attach the sizes to each work, after which the figures arrived here for
  free.
- **Sanskrit Wikisource's scan count.** The scans were in `tree.json` all along
  as `source_indexes` links, but no aggregate was. Sāgarasaṅgama could have
  walked the tree and counted them itself. Instead the Atlas's `process.py`
  computes `pdf_count` into `all_stats`, so the definition lives with the
  collection that understands it — including the judgment that one work cited
  from several pages is still one work.
- **E-bhāratīsampat's growth series.** Its `changelog.json` measured size in
  Devanāgarī characters, which cannot be added to a roman-script collection's
  bytes, and counted as text-bearing 66 works its own `tree.json` had already
  decided were empty. Both fixes went upstream — the periods now carry
  `cumulative_iast_bytes_total` and `cumulative_text_count`, and both files
  reach the empty-text verdict through the same loader, so they cannot drift
  apart.

**A local-only affordance still goes through the contract.** The `txt` badge
linking to an Atlas's locally cached plain text is the newest example. The text
itself sits in that Atlas's gitignored `data/` — which this layer must never
read — so the Atlas publishes a `has_text` boolean into its own `tree.json`
instead, derived from its own cache presence. `collect_atlas_search.py` picks
that up as `lt` and `search.js` renders a link.

So even a badge that only ever works on localhost is fed by a published field,
not by reaching into `data/`. The rule did not need an exception for it.

**And the mode is a flag, never an inference.** `make serve` is the published
site byte for byte: it does not probe, and shows no badges even with all three
Atlases running in fulltext mode on the same machine. Only
`make serve-fulltext` (or `make serve-all-fulltext`) turns it on, and the
server says so at `/fulltext-mode` — a route the published site does not have.
An earlier version inferred the mode from whether the Atlas ports happened to
be listening, which meant the page could quietly enter a special mode because
something else was left running.

**Absent stays absent.** Where an Atlas publishes nothing, the page shows an em
dash and says why, rather than estimating, substituting a related figure, or
carrying a hardcoded copy. `collect_atlas_counts.py` leaves those fields `None`
and `docs/counts.js` renders the dash.

**One standing exception, and what it costs to have.** Sanskrit Wikisource's
changelog counts `text_count` two ways and flips between them across 2014–15,
reading ~400 texts high for nine months. `WS_RUNS` in `docs/growth.js` pulls those
runs back at render time. This is a display-layer patch over published data —
precisely what the rest of this document forbids — and it is here only because
the alternative is drawing a spike that never happened, on a chart whose whole
job is the shape of growth.

It is bounded to stay honest: the correction is named, not inferred by
threshold; it moves nothing after the last affected month, so totals still
agree with `counts.json`; it applies only while the offending step is still in
the data, so it goes inert rather than wrong if the changelog is regenerated;
and the About page states it, with the figure asterisked. **The real fix is
still upstream.** When the Atlas resolves the flip, delete `WS_RUNS` and the
note with it. See [notes/changelog-axes.md](notes/changelog-axes.md).

## The shared publishing format

**Monthly**, across all five Atlases, each period stamped at its start. A
growth chart puts the collections on one time axis, and a yearly series
there is a straight line between Decembers laid over its neighbours' real
shape. Each Atlas's own About page groups those months up to quarters or years
at render time, so publishing the finest grain costs nothing and the reader
still chooses.

## The fields read

From `all_stats` in each `tree.json`:

| Field | Used for | Notes |
| --- | --- | --- |
| `text_count` | the headline count | the only count comparable across all five; `count` includes non-text nodes and means something different in each Atlas |
| `transliterated_bytes` | MB (IAST) | script-neutral; `content_bytes` inflates Devanāgarī at ~3 bytes a character |
| `sized` | — | how many works the byte figures cover; below `text_count` means the totals are a floor. Collected, not currently shown |
| `pdf_count` | PDFs | works with a scan, deduplicated |
| `last_changed` | currency | the Atlas's own notion, where it keeps one |

Averages divide by `text_count`, never by `sized`: this layer counts items with
searchable text, so "how long is a text here" is the question, not "how far has
the fetcher got".

## The search index

`collect_atlas_search.py` reads the same `tree.json` files a fourth time and
writes `docs/data/search.json`, the index behind `docs/search.html`. It reads
per-work records rather than `all_stats`, but the boundary is identical:
published `docs/data/` only.

**It reconciles, and fails loudly when it cannot.** Each Atlas's walk is
checked against that Atlas's own `all_stats.text_count`, and `make search`
exits non-zero on a mismatch. This is the same principle as the Atlases'
`data-stat` contract — a figure this layer publishes must be derived the way
the Atlas that owns it derives it — enforced at build time rather than trusted:

| Atlas | Indexed | Against | Rule |
| --- | --- | --- | --- |
| sanskrit-documents | 9756 | `text_count` 9756 | the folders branch enumerates the corpus; the topics branch is multi-valued and would double-count |
| wikisource | 3805 | `text_count` 3805 | pages with `own_stats.text_count >= 1`, plus Index items — **and the root node's own 11 pages**, which are easy to miss and land the walk one short |
| e-bhāratīsampat | 11066 | `text_count` 5491 | the one expected excess: 5575 works are PDF-only scans, indexed and flagged `po` |
| jain-quantum | 2465 | `text_count` 1961 | the Sanskrit tier only (books whose catalogued language is exactly Sanskrit); the 504 without a public Quantum text are indexed and flagged `po`, like the scans above |
| gretil | 1123 | `text_count` 1123 | one work per TEI file plus one per legacy-only text; every work has text, so nothing is flagged |

Two judgments worth keeping:

- **Wikisource subpages are chapters, not works.** All 22931 carry
  `text_count: 0`, and a subpage's title is its parent's plus a chapter label.
  Indexing them takes the file from 8 MB to 19 MB to list rows nobody searches
  for; the count rides along on the parent instead.
- **PDF-only works are indexed but hidden by default.** They are real
  catalogue entries a title search should find, so leaving them out entirely
  would be wrong — but counting them by default would put the search page's
  totals at odds with the home page's. The toggle is the honest resolution,
  and the status line names which of the two is on screen.

**Size discipline applies here too.** The index ships ids, not URLs, exactly
as each Atlas's `tree.json` does; `rehydrate()` in `docs/search.js` rebuilds
every link from the same rule that Atlas's own `app.js` uses. Written naively
the file is 17.9 MB; it is 7.9 MB (1.2 MB gzipped) this way. If a result's
link is ever wrong, one of those three derivations has drifted from its Atlas
— and the Atlas is right.

## Refreshing

From each `changelog.json`, per period, cumulative:

| Field | Used for | Notes |
| --- | --- | --- |
| `text_count` | the texts series | under `all` for wikisource, whose top-level block covers the `root` subtree alone; `cumulative_text_count` for e-bhāratīsampat, which states it outright |
| `transliterated_bytes` | the MB series | `cumulative_iast_bytes_total` for e-bhāratīsampat. IAST throughout, for the same reason as above |
| `undated_works` | the note under the chart | where an Atlas dates its works from an upload stamp and cannot date all of them, its series ends below its own total |

```sh
make counts      # re-read the Atlases, rewrite docs/data/counts.json
make growth      # ... and docs/data/growth.json, the chart's series
make search      # ... and docs/data/search.json, the search index
make data        # all three (counts, growth, search), over all five Atlases
```

The Atlases are read from `../atlases/<slug>/docs/data/tree.json` by default;
override with `make counts ARGS="--atlas-root /path"`. Nothing is written to
them. If an Atlas has itself been rebuilt, its new figures appear here on the
next run.
