# Case study: how Sanskrit Wikisource and Sanskrit Documents relate

How text moves between two collections, and how to tell which way it went.
This started from one text, the Jābāladarśanopaniṣad, and grew to cover every
text the two collections share. It is written to be reused. The methods,
signals and pitfalls apply to any pair of collections, not just SW and SD.

**The figures are measurements of particular snapshots, so re-derive them before citing them.**
- SW: text extracts from the 2026-10-01 dump; revision history from the
  `pages-meta-history` dump of 2026-07-21.
- SD: the Atlas `fulltext_cache` from Aug 2026; the 2020-06-27 mirror; the
  Feb-2025 scrape.

The scripts are in `scripts/` and the result tables in `data/` (see `README.md`).

## Findings

**1. The main direction is SD → SW, and SW copies go stale.**
- **Matches:** 1,873 SW↔SD text pairs where ≥50% of one side is contained in
  the other. Of these, 1,005 are labeled "SD → SW" because the SD version was
  in the 2020 mirror with a date earlier than the SW page's first revision.
- **Staleness test:** 318 SD docs whose text changed after the 2020 mirror.
  Where the change site can be located in SW (about a third of sites), SW holds
  the **pre-change** reading 84% of the time. Excluding the Arthaśāstra, which
  alone has 727 such sites, the figure is 78%.
- **SW pages created before 2020:** across 6–20 years they picked up 38 of
  roughly 1,650 checkable SD changes.
- **SW pages created after 2020:** these carry SD's post-2020 readings (69 to
  27). This is the best corpus-wide evidence that SW copies whatever SD version
  is current.
- **Do SD's changes improve the text?** A random sample of 30 is almost all
  real corrections (`ध्ह्याने`→`ध्याने`, `पुरयंती`→`पूरयंती`, `देवकि`→`देवकी`,
  `प्रह्राद`→`प्रह्लाद`) plus restored lines. A few are reading choices.

**2. Most imports into SW are unattributed.** The SW Atlas audit
(`find_bulk_import_candidates`) flags 107 pages as imported from SD, based on
their links or a `==स्रोतः==` heading. Matching on content instead finds 678 SW
texts that match SD and are dated after it, and **582 of those never mention
sanskritdocuments**. The two methods agree where both can see an import: 101 of
the 107 audit-flagged pages also match on content. Of the 185 SW texts found to
be stale, 25 credit SD.

**3. SW → SD also happens, mainly as one identifiable stream.** Of the 486
pairs where SW is older and the SD doc is missing from the 2020 mirror, 268 are
**PSA Easwaran's** SD stotras (2024–25). He excerpted them from SW Purāṇa pages
(uploaded 2011–12 by Puranastudy, Sbblr0803 and others) and added scan links.
In these pairs SD differs from SW about 84 times per 1,000 tokens, and the
sampled differences are corrections: `arccana`→`arcana`, `kuyyāṃ`→`kuryād`,
`bhakti`→`bhukti`. SD also explicitly credits sa.wikisource on 58 pages, mostly
Purāṇa extracts.

**4. Poor conversion is real but limited.** Only about 9% of SD → SW pairs show
ITRANS-converter damage at ≥5 per 10k Devanāgarī characters.

## The worked example: Jābāladarśanopaniṣad

**Mūla.** The chain is SD-2000 → SW-2012 → EBS, and SD then corrected itself.
- **SD, Aug 2000** (`jabaladarshana.itx`, Hattangadi): read `काऽचनं`, `लोष्ठं`.
- **SW, Mar 2012** (pages 9412–9421, Sandeep V Kulkarni): this is SD-2000 put
  through a broken ITRANS converter, with **no** variant readings.
  - `kSh` became `क्श`
  - `chh` became `च्च्ह`
  - `kA~nchanaM` became `का~चनं`
  - `chottamaM` became `cओत्तमं`
- **SW edits, 2019–22** (Puranastudy): partial cleanup and nasal restyling,
  plus 3 real corrections SD still lacks.
- **SD, Apr 2021:** Hattangadi fixed `kāñcana`, `loṣṭa` and `iḍā`. That is the
  whole 2000→2021 diff.
- **EBS #4282** (contributor RSV Tirupati) is SW's 2012 revision almost exactly:
  12 differing stretches against SW-2012, 67 against SD-2000. It shares every
  converter error, including the literal `~`, `ca ottamaṃ` and `kś`. It lacks
  all of Puranastudy's 2019+ edits and SD's 2021 fixes, so it was copied
  between Mar 2012 and Dec 2019.

**Commentary (Upaniṣadbrahmayogin, Adyar 1968).** SW `दर्शनोपनिषत्` (163623,
Shubha, Jun 2025) and SD `darshanopaniShatsavAkhyA` (Dec 2022) are **separate
typings** of the same printed edition. They disagree in about 119 substantive
places, and each side has its own errors. Neither one corrects the other, so they
need to be collated.
- SD's printed source lacked pp. 160–161. SD says so in a note, which the
  extract garbles (see Pitfalls). SW has those pages.
- The "Birch/Rajagopal input" attribution for the SW text comes from a header
  in a file the owner put together locally. The SW page carries no source
  credit. Diffing it against Birch's own file is still to do.

## Telling direction: the signals, strongest first

1. **Edit history.** SW keeps every revision. Compare a page's first revision
   with the candidate source **as it stood then**: the SD 2020 mirror or the
   Feb-2025 scrape. The other collections have no history; there are only our
   own successive snapshots.
2. **Errors only one side could have made.** The best are mechanical artefacts
   that no human typist produces:
   - converter damage: `क्श` for `क्ष`, `च्च्ह` for `छ`, a literal `~`, Latin
     letters inside Devanāgarī words
   - SD credit lines inside SW text (`Encoded by`, `% File name`, `.itx`)
   - shared idiosyncratic typos

   If B has A's artefacts and also everything A had, B descends from A, or from
   a copy of A.
3. **Missing later layers.** A copy lacks the edits its source received after
   it was taken (EBS lacks SW's 2019 edits). This dates the copy.
4. **Readings that appear after a source changed.** A copy made after a source
   was revised carries the revision (SW pages created after 2020).
5. **Dates alone are the weakest signal.**
   - SD's "Latest update" is not a creation date.
   - The 2020 mirror holds only 4,555 of 9,756 SD docs, so a doc missing from
     it may still be old.
   - An earlier date does not rule out a **common ancestor**. The Arthaśāstra
     on SW (2005) predates SD's 2010 version.

**Copy vs independent typing.** Copies differ almost only in
mechanical/orthographic ways (Jābāladarśana mūla: 7 substantive differences in
about 2,000 tokens). Independent typings of one edition scatter substantive
disagreements throughout (the Darśana commentary: about 119 in about 2,500
tokens). Calibrate any threshold against known cases like these two.

## Methods that worked

- **Normalization before comparing.** Fold these:
  - ZWJ/ZWNJ and avagraha
  - SW's converter damage
  - final `m`/`ṃ`
  - a nasal written as anusvāra vs as the matching class nasal, **but only
    before a consonant of its own class** (`ṅ` before k/g, `ñ` before c/j, `ṇ`
    before ṭ/ḍ, `n` before t/d, `m` before p/b). An earlier version folded every
    nasal before any stop, which wrongly made `bhagavānbhūta` equal
    `bhagavāṃbhūta`.
  - spaces (sandhi splitting differs between the collections)

  Report what is left as substantive.
- **Overlap matching** (`match.py`): character 16-grams over normalized IAST
  with all spaces removed, hashed with a numpy rolling hash and sampled 1/16. Drop
  shingles found in more than 8 SD docs, then measure containment in **both**
  directions. All 9.7k SD docs against 4.1k SW texts runs in minutes.
- **Grouping SW pages.** Merge SW subpages into a text by their top-level title.
  SW also has anthologies, such as `ईशादिविंशोत्तरशतोपनिषदः` (the 120
  upaniṣads), which contain many single texts. They show up as high containment
  on the SD side and near-zero on the SW side, so keep both numbers.
- **Staleness test** (`stale.py`):
  1. Diff SD-2020 against SD-now (SD has full-page snapshots from both dates).
  2. For each change site, build a lookup string from about 10 normalized
     characters of context on each side around the old reading, and another
     around the new one.
  3. Search SW's first and latest revisions for each, and count old / new /
     both / not found.

  It runs in parallel on one machine. It is CPU-bound, so spawning agents gains
  nothing.
- **Sanity checks.** Reproduce the case done by hand before trusting the
  aggregate: the staleness test must find `kāñcana` and `loṣṭa` stale and `iḍā`
  fixed in Jābāladarśana.

## Pitfalls hit

- **Extraction artefacts that look like text errors.**
  - SD writes शृ as श + ZWJ + ृ, which the IAST extract renders as `śaṛ` (83
    lines).
  - Both Atlases run English notes through Devanāgarī→IAST, which turns them
    into nonsense. SD's "Missing pages 160-161 from the commentary book" became
    `ṃisasnaga pagsa…`, and SW's Muktabodha headers (M00111, M00334) went the
    same way.
  - Check the source HTML or wikitext before blaming a collection for an error.
- **Attribution has to be checked on the source page itself.** A credit header
  found in a locally assembled file was taken to be on the SW page. It was not
  there in any revision.
- **Pairs are not texts.** One SD doc can match a SW single text, a SW
  anthology and a commentary edition at once. Deduplicate (here, the best SW
  match per SD doc) before quoting counts.
- **Mūla matched against commentary** produces wrong direction labels. A
  commentary edition contains the whole mūla.
- **A few outliers dominate.** Report figures with and without the largest
  text (the Arthaśāstra: 32% of stale sites; the top 12 docs: 57%).
- **Most change sites can't be located** (about two-thirds here). The SW
  context differs, or the passage is on an unmatched page. The stale share
  applies only to sites SW reproduces closely.

## Where this sits relative to the contract

This research reads Atlas `data/` caches and the dumps under
`third_party_dumps/`, which `CONTRACT.md` forbids for anything Sāgarasaṅgama
**publishes**. It is research material, not a published figure. If a finding
becomes a published number (an "unattributed import" count, a duplicate flag),
it belongs upstream: in the owning Atlas's audit and `tree.json`, or in SETI's
edition/quality annotations (ISCLS 9 paper, §3.2). It should not be computed
here.
