# Sizes and dates: one figure, one meaning, everywhere

Started 2026-10-08. **This file coordinates the work across all seven repos.**
Each Atlas has a short `notes/scratch/sizes-and-dates.md` of its own that
points back here and lists only its own steps. Delete all of them when the
last box is ticked; what is worth keeping is already in `CONTRACT.md`.

Two things were inconsistent across the cluster, and both are being settled
in one pass:

1. **Sizes.** Some pages divided by 1,024² and some by 1,000,000, both
   labelled "MB", so GRETIL read 270.7 MB on its tree and 283.9 MB on the home
   page. **Decided: decimal everywhere** (1 MB = 1,000,000 bytes). Done.
2. **Dates.** The home card's "as of" was the modification time of each
   `tree.json`, so a rebuild from an old fetch looked like a new fetch.
   **Decided: the card shows when the Atlas took its copy**, which is what
   `__content_version__` in `docs/VERSION` means and what each About page
   prints as "data last sourced". Half done; see below.

## Where each repo is

| Repo | Branch | Sizes | Dates |
| --- | --- | --- | --- |
| `sagara-sangama` | `add-gretil-and-jain` | done | reads `docs/VERSION` as a stopgap |
| `sanskrit-wikisource-atlas` | `fix-sizes-and-dates` | done | `VERSION` correct; `sourced` not published |
| `e-bharatisampat-atlas` | `fix-sizes-and-dates` | done | `VERSION` correct; `sourced` not published |
| `sanskrit-documents-atlas` | `fix-sizes-and-dates` | done, audit to re-run | `VERSION` correct; `sourced` not published |
| `gretil-atlas` | `v0` | done | `VERSION` fixed by hand, rebuild to confirm; `sourced` not published |
| `jain-quantum-atlas` | `v0` | done | **`VERSION` still wrong**; `sourced` not published |
| `rivulet` | `add-jain-quantum` | done (console output only) | nothing to do |

`fix-sizes-and-dates` replaced the earlier `decimal-sizes` branches, which had
no pull requests and were deleted from the remotes.

## What is left

### 1. Jain Quantum's `__content_version__` (needs a machine with its `data/`)

It carries the newest accession (2026-06-09) where it should carry the fetch
date. Steps and the journal's shape are in
`jain-quantum-atlas/notes/scratch/content-version.md`. Until it lands, that
card reads "as of Jun 2026".

### 2. Every Atlas publishes `all_stats.sourced`

The date belongs in `tree.json`, beside the numbers it dates: a separate file
can be committed out of step with the tree, which is the class of mistake the
file-time bug was. So in each Atlas:

- write `sourced` (YYYY-MM-DD) into `all_stats`, **from the same value and in
  the same function that stamps `__content_version__`**, so the two cannot
  disagree;
- rebuild the tree and commit it together with `docs/VERSION`.

`docs/VERSION` stays; each Atlas's own pages read it.

**"Rebuild" means the last step only.** No counts or sizes are recomputed:
each Atlas's tree builder reads intermediate files already on disk. Costs are
from `make steps` here, not timed.

| Atlas | Run (from here) | Cost | Watch for |
| --- | --- | --- | --- |
| E-bhāratīsampat | `make ebs-build` | ~1 s | its tree dates from 2026-09-09: read the diff for drift beyond the new field |
| Sanskrit Documents | `make sd-build` | seconds | |
| Jain Quantum | `make jq-build` | seconds | needs its `data/`; the 15-minute `jq-count-sizes` is not needed if `sizes.jsonl` is there |
| GRETIL | `make gr-build` **then `make gr-changelog`** | seconds each | **the changelog step is what writes each work's `added` date into `tree.json`; a build alone leaves the tree without them.** On a machine with no `data/`, run `make gr-inventory` and `make gr-count-sizes` first (seconds, offline) |
| Sanskrit Wikisource | `make ws-process` | minutes | no separate assemble step: this one goes from the dump to the tree |

The expected diff in each `tree.json` is the new `sourced` field, and in
`docs/VERSION` the pipeline-run date. Anything more is drift worth reading.

### 3. Then, here

- [ ] `make data`, and check that all five cards show the expected month.
- [ ] `collect_atlas_counts.py` already prefers `all_stats.sourced`. Once all
      five publish it, delete `read_sourced`'s `docs/VERSION` fallback (and the
      `VERSION` / `_CONTENT_VERSION_RE` constants), and delete the paragraph
      "The one exception, and it is temporary" from `CONTRACT.md`, leaving the
      `sourced` row in its field table without the parenthesis.
- [ ] `tree_mtime` is still written to `counts.json` and nothing reads it.
      Drop it, or keep it knowingly.

### 4. Sanskrit Documents: the audit's other figures

Re-running its audit on 2026-10-08 confirmed the two decimal size figures
(132.6 MB, 2.8 KB) and also changed eleven unrelated lines of its About page:
the credit-field coverage counts, and "pulled back to an earlier date"
153 → 802 (42% → 95% before mid-2020). The data on that machine was the same
as a USB copy from 2026-09-07, so the published figures looked stale rather
than the data. **Held, not committed**, until the audit is run on the machine
with the freshest cache. If that run gives the old values, the caches differ;
if it gives the new ones, commit them as their own "audit refresh".

## Expected card dates when everything is in

| Atlas | "as of" | From |
| --- | --- | --- |
| Sanskrit Wikisource | Oct 2026 | the dump's date |
| E-bhāratīsampat | Sep 2026 | newest fetch in its journal |
| Sanskrit Documents | Aug 2026 | newest fetch in its journal |
| Jain Quantum | Oct 2026 | newest fetch in its journals (today: Jun 2026, wrong) |
| GRETIL | Nov 2025 | the scrape, a constant |

## Checks that were made, so they need not be repeated

All five tree pages, the home page, the search page and the growth chart were
looked at in a browser on 2026-10-08 after the decimal change: each
collection's size reads the same on its tree page and on its home card
(818.0, 2321.5, 132.6, 1231.9, 283.9 MB). Not looked at: the E-bhāratīsampat
About page, and anything at phone width.
