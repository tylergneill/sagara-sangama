# Mapping how the collections relate

**Status: open. Scoped 2026-10-27.** Meant to be run by a cloud agent over
several weeks of nightly sessions. Delete this file once its findings have been
promoted: into Atlas audits and `tree.json`, into SETI annotations, and into a
top-level note on what the mapping found.

## Goal

A clear, evidence-backed map of how the five Atlas collections (SW, SD, EBS,
GRETIL, JEL) share text, at the level of individual texts. For every text that
appears in more than one collection, record:

- **Identity.** Same work? Same edition? Same transcription (a copy) or an
  independent typing?
- **Direction.** Who copied from whom, or from what common ancestor, and the
  evidence for it.
- **Freshness.** Did the copy keep up with corrections made at its source?
- **Quality.** Which witness has better readings, and where.

This is the "identifying and subtracting duplicates" step toward D1 in the
ISCLS 9 paper (§3). It produces the edition and quality annotations that §3.2
says SETI should record, so that users can choose their own deduplication
threshold. Record what is found; do not discard anything.

## End product this feeds

Planned: an overlap feature on sagarasangama.info that advises readers which
version of a text to prefer, based on its **pedigree**. It has two views:

- **Collection level:** Sankey-style flows (texts and MB copied SD→SW, SW→EBS,
  …). Undirected relations (independent typings, shared ancestry) are shown
  separately, because they have no direction to draw.
- **Single text:** a dated lineage, e.g. SD-2000 → SW-2012 → EBS; SD-2021
  corrected 3 readings; SW added 3 corrections of its own.

Advice gives reasons and evidence, not a single winner. Pedigree is not the
same as quality: a source can be worse than a copy that corrected it, and
independent typings must be collated. The labels below should be enough, each
linked to its evidence and given a confidence level:

- *source, current*
- *stale copy*
- *copy with its own fixes*
- *independent witness — collate*
- *excerpt of*
- *contained in an anthology*

**The contract needs to change.** Overlap spans collections, so no single
Atlas can publish it. Before this ships, `CONTRACT.md` needs a third kind of
published input: a relations artifact (e.g. `relations.json`) from whichever
producer owns it (SETI, rivulet, or a new repo).

**Output format for every night's work**, so results flow into the feature
without rework:

- a cluster of member texts `(atlas, text_id)`
- edges, each with:
  - `kind` (copy / excerpt / anthology / independent-typing / common-ancestor)
  - `direction`, or none
  - `evidence[]` (signal, detail, snapshot date)
  - `confidence`
- per-edge freshness: source changes since the copy was taken, and how many the
  copy still lacks / has / that couldn't be checked
- per-member advice label and its reasons

Start from `../collection-interrelations/case-study-sw-sd.md`. Its signals,
normalization rules and pitfalls are the starting kit.

## Blocker: getting the data to a cloud session

All text lives in gitignored `data/` directories and under `third_party_dumps/`
on the owner's machine, roughly 25 GB. A cloud session has none of it. Decide
one of these before the first night:

- **Fetch inside the session** what is public and fetchable in bulk: the SW
  monthly dump and meta-history (Wikimedia), and GRETIL (closed archive).
  SD (about 5.4h) and EBS (about 6.5h, plus a clearance step) are crawls under
  the 2-second-per-request rule. Running them every night is not acceptable.
- **Ship a prepared corpus** to the cloud: normalized IAST per text plus
  metadata, built locally once with rivulet's extractors and refreshed when an
  Atlas refreshes. This is probably the right choice, but it is a private copy of
  other people's text, so keep it private.
- **Shingles only.** Ship hashed shingles plus metadata. That is enough for
  matching but not for reading diffs, which most direction work needs.

Also decide where the reusable code lives: rivulet (it already holds the text
machinery), this repo's notes (research only, per `CONTRACT.md`), or a new
private repo.

## Work queue

Roughly one item per night. Each night appends its results to a running log
in a sibling scratch file, and that log is condensed when the work finishes.

- [ ] **Regression set first.** Encode the known cases from the case study as
      checks every method must reproduce before it is trusted:
      - Jābāladarśana mūla: SD → SW → EBS copy chain; SD-2021 fixes stale in SW.
      - Darśana commentary: independent typings of one edition.
      - Easwaran excerpts: SW → SD with corrections.
      - Arthaśāstra: possible common ancestor.
- [ ] **Shared text units.** Use each Atlas's own definition of a text (its
      `tree.json` works), so that every result keys to an ID an Atlas or SETI
      can publish. The SW grouping by top-level title in the case study was an
      improvised stand-in.
- [ ] **Matching across all ten collection pairs**, from one shared shingle
      index. Keep both containment directions. Tag anthologies and
      mūla-vs-commentary matches as their own kinds of match, not as duplicates.
- [ ] **Library of fingerprints per collection**, to judge direction:
      - SD: `.itx` headers, credit lines, ITRANS conversion damage, the
        ZWJ-शृ convention
      - SW: `==स्रोतः==` headings and the audit's domain list
      - GRETIL: "Input by" headers, TEI vs legacy layers
      - EBS: GRETIL files converted to Devanāgarī (the paper notes this happens)
      - others as they turn up

      Each fingerprint needs a precision estimate checked against the
      regression set.
- [ ] **Staleness wherever versions exist.** Generalize `stale.py`. The
      versioned sources are SW history, SD 2020/2025/now, GRETIL legacy vs TEI,
      and successive snapshots of our own Atlases going forward.
- [ ] **Copy vs independent typing.** Calibrate a classifier on substantive
      differences per 1,000 tokens after normalization, plus shared rare errors,
      page-break and verse-number patterns, and front matter. Check it against
      known cases before trusting it.
- [ ] **Better-reading signals** for each disagreement: support from a third
      witness, metre, a dictionary or lemmatizer, and scan links where an Atlas
      has them (SD lists 873 distinct sources). Flag; do not auto-decide.
- [ ] **Aggregators.** Measure Intellexus, Dharmamitra, Sañcaya and Travelogue
      against the same index (the paper's Tables 1–2), so their copies can be
      placed in the same graph.
- [ ] **Push findings upstream.** For example, a content-based "unattributed
      import" check for the SW Atlas audit (in the case study, the link-based
      audit catches about 1 in 6 SD imports), and SETI rows for edition and
      quality.

## Rules for the agent

- **Never cite a figure without its snapshot date.** Counts in texts and
  counts in pairs are different numbers; say which.
- **Verify attribution and provenance on the source page itself** (the case
  study got this wrong once). Before blaming a collection, rule out problems
  introduced by the extraction step.
- **Report every result with its denominator**, including how many items could
  not be checked. Report figures with and without dominant outliers.
- **Rate terms apply to any network fetch:** one request per 2 seconds,
  single-threaded, back off and stop on errors. No nightly re-crawls.
- **Nothing in this program publishes text.** Outputs are notes, TSVs and
  upstream proposals.
