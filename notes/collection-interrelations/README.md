# collection-interrelations/

Research material on how the Atlas collections share text with one another:
which texts appear in more than one collection, which direction the copying
went, and whether the copies kept up with their sources.

- `case-study-sw-sd.md` — Sanskrit Wikisource × Sanskrit Documents. Findings,
  the signals used to tell direction, methods, and the pitfalls hit. Read this
  first.
- The program that continues this work is in `../scratch/collection-interrelations.md`.

Not maintained and not meant to be re-run routinely. Paths are hard-coded to
the owner's machine. Most scripts take a scratch directory as their first
argument and read the Atlas caches and `third_party_dumps/`, none of which is
committed.

## data/

| File | What it is |
| --- | --- |
| `SW_SD_overlap_pairs.tsv` | 1,873 SW↔SD pairs with ≥50% containment on either side. Columns: direction label, stale-fork flag, dates, SW first uploaders, containment both ways, converter damage per 10k chars, SD credit lines found in SW. |
| `SW_SD_staleness.tsv` | 318 SD docs changed since the 2020 mirror, each with its best SW match. For each: change sites, SW old/new/not-found counts at first and latest revision, and a few stale examples. |

## scripts/

Listed in pipeline order.

| Script | Step |
| --- | --- |
| `textsrc.py`, `iastnorm.py` | Shared helpers: SD HTML and SW wikitext extraction, tokenizing, orthographic normalization. |
| `extract_hist.py`, `revlist.py` | Pull every revision of chosen SW pages from the meta-history dump, and list them. |
| `threeway_jd.py`, `sd00_sw12.py`, `ebs_cmp.py` | Jābāladarśana: SD-2000 / SD-2021 / SW-2012 / SW-now three-way, and EBS against each. |
| `classify.py`, `vote.py` | Commentary pair: orthographic vs substantive, with the mūla as a third witness. |
| `sw_meta.py` | One pass over SW history: first/last revision, users, comments, converter damage counts. |
| `sd_meta.py` | SD metadata (`inf` block), presence in the 2020 mirror, and how much the text changed since then. |
| `match.py` | All-pairs overlap: rolling-hash character 16-grams, sampled 1/16, containment both ways. |
| `join.py`, `stats.py` | Join matches with metadata and assign direction labels. |
| `excerpt_diff.py` | Substantive differences per 1,000 tokens within matched excerpts. |
| `stale_scope.py`, `extract_fl.py`, `stale.py`, `stale_sum.py`, `split.py`, `stale_look.py` | Staleness test. |
| `audit_xcheck.py` | The SW Atlas audit's import detector compared with the content matches. |
| `sd_wscredit.py` | SD pages that credit Wikisource. |
