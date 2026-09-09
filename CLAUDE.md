# CLAUDE.md

Guidance for Claude Code (claude.ai/code) working in this repository.

## What this is

The aggregator over three Atlases. It reads only what each has published under
`docs/data/` — `tree.json` and `changelog.json` — and never an Atlas's pipeline
scripts, working files, or caches. See `CONTRACT.md`; that rule is what makes
reading a sibling repo safe, and a figure an Atlas has computed but not
published gets fixed upstream rather than routed around.

## The refresh shape

Shared even though no stage is: **acquire** (networked, hours) → **parse**
(offline, seconds) → **build `tree.json`** → **changelog** → **audit**. Then
`make data` here.

Wikisource is the cheap one — a monthly XML dump rather than a crawl.
E-bhāratīsampat is the expensive one (~6.5h, and needs `make ebs-clearance`
first). Sanskrit Documents walks ~10k documents in ~5.4h.

`make steps` prints the per-Atlas sequence with costs; `make status` diffs the
published files against their sources.

## Rate is the constraint, not budget

Every networked step is single-threaded, one request per 2s measured start to
start, with a contact-bearing User-Agent, and stops rather than retries on
429/5xx. All are resumable: Ctrl-C stops cleanly and a rerun picks up from the
cache. There is no request ceiling in any of the three.

These are stated as **terms** in rivulet's own CLAUDE.md. Changing one means
changing that text in the same edit.

## Networked checks are dated where they are published

An Atlas's audit stamps each figure with the day the probe actually ran, not
the day the audit ran; a run that could not reach the network reports
*inconclusive* and leaves the last real measurement standing. So a figure can
be older than the page around it, and says so.

## The growth chart's traps

Tracked in [notes/changelog-axes.md](notes/changelog-axes.md), which owns all
three:

- **`changelog.json` is a different program in each Atlas** (two lists, one
  dict), and generalizing from one sibling's `build_changelog.py` has already
  gone wrong once.
- **A render-time correction is applied.** Nine months of Sanskrit Wikisource's
  2014–15 snapshots count `text_count` a second way and read ~400 texts high.
  Those runs are pulled back to the level the surrounding months agree about,
  the chart carries a note saying so, and present-day totals are untouched. The
  real fix is upstream: when the Atlas resolves the flip, delete `WS_RUNS` and
  the note with it.
- **Last-updated is not growth.** A text encoded in 2004 and reproofed in 2023
  appears only under 2023, and the error concentrates where counts are
  smallest — so no single revision rate should be quoted.

No Atlas publishes what *kind* of series it is (measured / approximated /
inferred), so one disclaimer covers all three. Transport is settled; the field
is not built.

## Search index

`make search` rebuilds `docs/data/search.json`. E-bhāratīsampat catalogues
thousands of scanned books with no Unicode text; they are indexed and one
toggle away, but off by default so the default counts agree with the totals the
home page publishes.

Results are colour-coded by collection, using the same three series colours the
About page's growth chart uses.
