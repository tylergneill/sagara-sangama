# Minute-precision build stamps

**Status:** planned. Prerequisite done: `make status` judges the parent's
aggregates by build dates (`atlas_status.py`, `Report.aggregate`), not mtimes.

## The problem this closes

`make status` marks `counts.json`, `growth.json` and `search.json` stale when an
Atlas's `__data_version__` is later than the aggregate's `generated` stamp. Every
Atlas stamps `__data_version__` as a bare date, so the comparison runs at day
precision and **a same-day tie reads as current**. Rebuild an Atlas in the
afternoon after a morning `make data`, and status says `ok`.

Today that is covered by hygiene (rebuild the parent last on any day you rebuild
an Atlas). The fix is precision, not hygiene: machines get the minute, and people
get the day.

## The change

**Each Atlas stamps `__data_version__` to the minute, in UTC:**
`2026-11-16T21:40Z`. UTC because the parent's `generated` is already UTC, so
the two compare as instants with no timezone guessing. (Today's date-level
check has to shift `generated` to local time because the Atlases stamp
`date.today()`.)

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

- `docs/about.html` in all five ("data pipeline last run: …")
- `docs/app.js` in sanskrit-documents and sanskrit-wikisource (the topbar
  tooltip, `pipelineRunDate`)

Round with `value.slice(0, 10)`. That gives the UTC day, which can differ from
the reader's local day near midnight. That's acceptable for a "last run" label.
Converting to local time is also fine if a page already formats dates that way.

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

All five Atlases stamp minutes and their validators accept them, every page
rounds to the day, `aggregate` compares instants, and a same-day afternoon
rebuild shows `stale`. Then promote the one-line rule ("machines compare
minutes, people see days") into `CONTRACT.md` and delete this file.
