# `__data_version__`: what it means, and how precise it is

**Status:** planned. Prerequisite done: `make status` judges the parent's
aggregates by build dates (`atlas_status.py`, `Report.aggregate`), not mtimes.

Two changes to the same stamping code in every Atlas, so they go together:
**meaning** (stamp on change, not on run) and **precision** (the minute, not
the day). A third, Atlas-side only, reuses both: an **audit stamp** for the
About page (§3), which sangama never reads.

## Background

`make status` marks `counts.json`, `growth.json` and `search.json` stale when an
Atlas's `__data_version__` is later than the aggregate's own `generated` stamp.
That is the right question for the parent ("is there anything new to pick
up?"), and today the stamp answers it badly in two ways:

- **It records that the pipeline ran, not that anything changed.** A rebuild of
  sanskrit-documents on 2026-11-17 produced a byte-identical `tree.json` and
  still moved the date, so status flagged the parent stale with nothing to
  pick up.
- **It is a bare date**, so a same-day tie reads as current. Rebuild an Atlas in
  the afternoon after a morning `make data` and status says `ok`.

## 1. Meaning: stamp on change

**`__data_version__` moves only when a published data file the parent reads
actually changed.** For people, label it "data last updated", not "pipeline
last run" or "last pipeline build", which still describe running.

- **The writer decides.** At write time the builder holds both the new output
  and the file it would replace. If they are identical, it skips the write and
  leaves the stamp alone. This is the Atlas comparing its own output. The
  parent still reads only the date and never looks at file contents.
- **Cover every file the parent reads, not just `tree.json`.** `counts` and
  `search` read `tree.json`; `growth` reads `changelog.json`. In
  sanskrit-documents only `make build` stamps `docs/VERSION`, and `make
  changelog` does not, so a changelog-only rebuild never moves the date and
  `growth.json` goes stale silently. (The v0.2.0 change-log dating would have
  been exactly that, had it not shipped alongside a build.) Check each Atlas
  for the same gap.
- **Settle the overlap with `all_stats.last_changed`.** CONTRACT.md already
  carries it as "the Atlas's own notion of currency". Wikisource fills it
  (2026-10-31) and sanskrit-documents leaves it null. A stamp meaning "data
  last updated" says nearly the same thing. Decide whether one replaces the
  other, or write down how they differ.

## 2. Precision: the minute, in UTC

**Each Atlas stamps `__data_version__` to the minute, in UTC:**
`2026-11-16T21:40Z`. UTC because the parent's `generated` is already UTC, so
the two compare as instants. (Today's date-level check has to shift
`generated` to local time because the Atlases stamp `date.today()`.)

Stamp sites, one per Atlas:

| Atlas | where `__data_version__` is written |
|---|---|
| sanskrit-documents | `pipeline/build_tree.py`, `fields["__data_version__"]` |
| e-bharatisampat | `pipeline/build_tree.py`, `fields["__data_version__"]` |
| sanskrit-wikisource | `pipeline/process.py`, `_stamp_data_version` |
| gretil | `pipeline/build_tree.py`, the VERSION write near line 71 |
| jain-elibrary | `pipeline/build_tree.py`, `kv["__data_version__"]` |

**Validators that will reject the new format** and must widen in the same change.
Each currently requires `\d{4}-\d{2}-\d{2}` for both date fields:

- sanskrit-documents and e-bharatisampat: `.github/scripts/check_docs.py`
- sanskrit-wikisource: `pipeline/verify_publish.py`

Widen only `__data_version__`. `__content_version__` (the fetch date) stays a
date. It is user-facing and nothing compares it at sub-day precision.

**Readers round to the day.** Every place a person sees it:

- `docs/about.html` in all five ("data pipeline last run: …", relabelled per §1)
- `docs/app.js` in sanskrit-documents and sanskrit-wikisource (the topbar
  tooltip, `pipelineRunDate`)

Round with `value.slice(0, 10)`. That gives the UTC day, which can differ from
the reader's local day near midnight. That's acceptable for this label.
Converting to local time is also fine if a page already formats dates that way.

## 3. An audit stamp, for the Atlas's own About page

**Each Atlas also stamps `__audit_version__`: when its published audit last
changed.** Sangama never reads it. It exists because the audit can change
without any file the parent reads changing, and then no date on the page moves.

The case that raised it: on 2026-11-18 sanskrit-documents' audit gained two
findings (from its change log) and stopped truncating long lists. That rewrote
the About page's Data Quality section, but touched neither `tree.json` nor
`changelog.json`, so under §1 `__data_version__` correctly stays put, and the
page still showed the previous day's date beside an audit that changed today.

Same rules as `__data_version__`:

- **Stamp on change, not on run.** The audit writer (`audit.py
  --update-about`, `make audit-update-about`) holds both the rendered region
  and what the page currently carries. Identical: skip the write, keep the
  stamp. Different: write and restamp. A rerun on unchanged data is a no-op.
  What counts as the audit's output is the audit region plus its `data-stat`
  figures.
- **The minute, in UTC, in `docs/VERSION`**, beside the other stamps, so dates
  still live in one file. People see the day.
- **Shown beside the audit itself** (sanskrit-documents: under
  "Opportunities for Correction"), labelled e.g. "audit last changed", not
  "audit last run".

Not to be confused with what the findings describe: the data they were
computed from is already dated (the fetch, and per-probe dates such as scan
liveness's "Checked <month>"). This stamp answers "when did this page's audit
last change", which is a property of the code as much as the data.

**Not consumed by sangama, and not part of `make status`.** Atlases adopt it
when they adopt §1, since it reuses the same write-or-skip machinery; the
validators in §2 need to accept it too.

## Sangama's side (mostly free)

`generated` is already an ISO UTC timestamp to the second, so no collector
changes are needed. `Report.aggregate` changes from comparing dates to comparing
instants:

- Parse both sides. Do not compare strings: `"2026-11-16" < "2026-11-16T09:00Z"`
  lexicographically, so a mixed comparison gives the wrong answer.
- **Keep the date fallback while Atlases migrate.** For an Atlas still stamping a
  bare date, compare at day precision as now, where a tie is current.
- Drop the "tie counts as current" paragraph from the docstring once all
  Atlases stamp minutes.

## Not in scope

- `atlas_status.py` checks three Atlases (`ATLASES`). gretil and jain-elibrary
  are stamped here for consistency, but status does not read them, and neither
  does the aggregator.
- The Atlas-internal rows (catalogue → tree, etc.) still use mtimes. That is a
  separate question.

## Done when

All five Atlases stamp on change and to the minute, their validators accept the
format, every page rounds to the day under the new label, each About page shows
its audit stamp (§3), `aggregate` compares instants, and two checks pass:

- a no-op rebuild leaves the parent `ok`;
- a same-day afternoon rebuild that changes output shows `stale`.

Then promote the rules ("stamp on change; machines compare minutes, people see
days") into `CONTRACT.md` and delete this file.
