# The growth chart's two traps

What is easy to get wrong when touching `growth.js`, `collect_atlas_growth.py`,
or an Atlas's `changelog.json`. The design history that produced these is not
here; the code and `CONTRACT.md` carry it.

## 1. `changelog.json` is a different program in each Atlas

Same filename, three shapes. An agent who reads one sibling's
`build_changelog.py` and generalizes will get it wrong — this has already
happened once.

- **sanskrit-wikisource** — real growth, from diffing monthly snapshots
  materialized out of the meta-history dump. A list.
- **sanskrit-documents** — per-item *last-updated* stamps, serving double duty
  as growth. A list.
- **e-bharatisampat** — catalogue upload-epoch bands plus a snapshot coverage
  overlay. A dict.

**Last-updated is not growth**, and where a source records only the most recent
touch, the difference is destructive rather than blurry: a text encoded in 2004
and reproofed in 2023 appears *only* under 2023. SD ships it as growth anyway,
because revision is rare — but **the revision rate is a property of the
interval, not the corpus** (measured: 3.33%/yr over 2020–25, 1.16%/yr over
2025–26), so do not quote a single rate. The documents that do move, move a
median ~5 years, and every revision moves one *out of* an early bucket, so the
error concentrates where counts are smallest. SD's `--attest` mechanism raises
that floor by treating presence in an older dump as a ceiling on arrival. See
`sanskrit-documents-atlas/notes/growth-from-last-updated.md`, which owns this.

**`items_removed` and `items_changed_count` are always zero for SD and EBS.**
One snapshot cannot observe a removal. Do not read those fields as "nothing was
removed".

## 2. `WS_RUNS` suppresses a real upstream bookkeeping flip

Wikisource's `text_count` swaps between two ways of counting across 2014–15.
The series steps **up 393** at 2014-07, holds six months, falls back at 2015-01,
steps **up 457** at 2015-02, holds three months, and falls back for good at
2015-05. Both offsets are the same quantity counted twice: the months on either
side of each run agree with each other.

`WS_RUNS` in `docs/growth.js` pulls each elevated run down by the step that
opened it. Largest monthly rise falls from +457 to +161; largest fall from −369
to −31 (2020-05, a genuine deletion).

**This is a display-layer patch over published data — exactly the reach-in
`CONTRACT.md` otherwise forbids.** It is there because the alternative is
drawing a spike that never happened, on a chart whose whole job is the shape of
growth. Four things keep it honest, and a change that breaks any of them is a
change to the argument for its existence:

- the runs are **named**, not detected by a threshold — this is one upstream's
  quirk, not a law about collections
- nothing after 2015-04 moves, so present-day totals still agree with
  `counts.json` and the About table
- each run applies **only while its opening step is still present**, so the
  patch goes inert rather than wrong if the changelog is regenerated
- the About page states it, with the figure asterisked

**The real fix is upstream.** When the Atlas resolves the flip, delete
`WS_RUNS` and the About note with it.

## Still open

Each Atlas should publish **what kind** of series it is — `measured` /
`approximated` / `inferred` — so the parent can caveat per-series instead of
applying one disclaimer to all three. SW is measured, SD approximated, EBS
inferred from serial order. Not built.

## The two 2026-10 Atlases

Both publish E-bhāratīsampat's dict shape (`periods`, monthly,
`cumulative_text_count`, `cumulative_iast_bytes_total`), so no new reader was
needed. What kind of series each is:

- **Jain Quantum** — *measured* from the library's own accession stamps
  (`web_date` on every API item), but its `text_count` series counts items
  with a Quantum booktext and so flattens after 2022, when Quantum's index
  stopped; `cumulative_count` carries the whole library. Its byte series
  covers only the fetched slice (Sanskrit-only on the first build) and is a
  floor. 2,005 Quantum-only rows carry no date (`undated_works`).
- **GRETIL** — *measured* from the site's own dated update history
  (hist.html, 498 entries 2001–2020) joined to the main page's anchors. 707
  of 1,123 works dated; the rest, the Mahābhārata parvans among them, are
  left out rather than guessed (`undated_works`). The series ends 2020-06,
  the last update that added a text.
