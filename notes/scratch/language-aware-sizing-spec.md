# Language-aware size measurement and text extraction — spec

Status: **designed 2026-11-10, not started.** A later, cross-Atlas change. The
EBS Atlas did only the minimal furniture pass needed to catch up with the
site's rebuild (below); this is the improvement after it.

## Why

Every Atlas's size figure is a byte count of **whatever text a work holds**,
transliterated to IAST. "Text" is decided by subtraction: strip markup and
known chrome, count the rest. So the figure also counts what is not Sanskrit:

- Hindi, Marathi or English commentary, introductions and translations
  bound into a Sanskrit book (EBS: very common in Hindi-ṭīkā editions);
- English front matter, prefaces and series pages;
- in a few books, nothing Sanskrit at all (EBS has English books in its
  catalogue; ~7% of its works carry no Sanskrit in their language field).

A figure published as "how much Sanskrit text" should count Sanskrit. The
same question arises in every Atlas with mixed-language holdings, and in the
vmlt.in survey, which already has a working prototype.

## Prior work

`~/Library/CloudStorage/Dropbox/Docs/Projects/Computational/vmlt/scripts/vmlt_measure.py`
(2026-10-19), over a 100-book sample of vmlt.in's OCR library:

- **Unit: one page.** Classified by Devanāgarī function words:
  - fewer than 15 Devanāgarī words → empty
  - more Latin or other-script characters than Devanāgarī → nondeva
  - Marathi marker rate > 3% and > Hindi rate / 3 → marathi
  - Hindi marker rate > 8% → hindi; > 3% → mixed
  - otherwise → sanskrit
- Marker sets: Hindi `है हैं के की में और से को का था थी थे यह वह नहीं भी कि ने
  पर तो एक इस उस जो लिए किया होता होती गया जाता कर`; Marathi `आहे आहेत आणि
  नाही होते होता त्या ह्या म्हणून यांनी याचा याची करून असे`.
- On a mixed page, keep only lines with ≥3 Devanāgarī words and no marker.
- Count IAST bytes of the Devanāgarī runs (`deva_only`) of Sanskrit material.
- Book class: Sanskrit share ≥ 0.5 → sanskrit; with mixed ≥ 0.25 →
  sanskrit+other.
- **Known gaps** (from `vmlt/SCRAPE_PLAN.md`): Rajasthani / Old Gujarati /
  Jain Prakrit verse passes as Sanskrit (4–5 of 56 "Sanskrit" sample books);
  Bengali-script Sanskrit needs its own marker set; running heads and front
  matter are still counted.

## Design

### A new statistic beside the existing ones

Add `sanskrit_bytes` (IAST bytes of material classified Sanskrit) next to
each Atlas's existing `raw_bytes` / `content_bytes` / `transliterated_bytes`.
Nothing already published changes meaning. Which figure the UI leads with is
a separate decision, taken after comparing the two across the corpora.

### Shared, pure, offline

One module (Sāgarasaṅgama-level or a small shared package, decided at build
time) holding the classifier and the counter. Each Atlas calls it from its
own offline size stage (`count_sizes` in EBS) over cached text, so the change
costs a local rerun, never a refetch. It must stay a pure function of text,
so it can live on the public side of the rivulet boundary.

### Unit: the paragraph, not the page

Most Atlases have no pages. Classify blocks separated by blank lines, falling
back to lines inside a block when a block is long and mixed (a verse followed
by its Hindi gloss in one paragraph).

### Markers per language, measured not guessed

Start from vmlt's sets; extend with:

- Rajasthani / Old Gujarati / Jain Prakrit (`को रो रा री छे थी ने मांहि …`) —
  the Jain eLibrary Atlas needs this most;
- Bengali-script Hindi/Bengali vs Bengali-script Sanskrit, where an Atlas has
  them.

Thresholds are tuned on a hand-labelled sample per Atlas (≥50 blocks each of
Sanskrit, Hindi, mixed, other), and the per-Atlas confusion table is kept in
that Atlas's `notes/`.

### Script boundaries

- **Romanized Sanskrit is out of scope** for the first version. A romanized
  book (EBS serial 2367, the whole Ṛgveda, 0 Devanāgarī) scores ~0 on
  `sanskrit_bytes`, which is correct for what the field measures and why the
  existing counts stay.
- Latin-script lines in a Devanāgarī book are not Sanskrit unless IAST
  diacritics mark them as transliteration — a later refinement.

### Extraction stays separate

Classification reads extracted text; it never decides what gets extracted.
Footnotes and apparatus are extracted as before (EBS inlines its `title=`
apparatus) and are classified like any other block.

## Interim state (2026-11-10, EBS only)

- The refetch reads only the reader's text container, so site chrome no
  longer enters the text at all.
- `strip_furniture` (EBS `pipeline/text_measure.py`) drops scan watermarks
  ("Digitized by Google", "Jain Education International"), bare page-number
  lines and punctuation-only lines: 0.18% of text bytes over the first 1,180
  refetched books. Running heads, footnotes and apparatus stay.
- No language classification anywhere yet.

## Validation

- Per Atlas: `sanskrit_bytes / transliterated_bytes` by the work's
  language field. Works labelled pure Sanskrit should sit near 1; Hindi-only
  works near 0; the spread in between is the commentary editions.
- Spot-read the 20 books with the largest drop and the 20 labelled Sanskrit
  with the lowest ratio.
- Test cases: EBS 2367 (romanized Ṛgveda → ~0), a Hindi-ṭīkā edition such as
  1248 (laghupārāśarī with Hindi commentary → well below 1), 640 (Sanskrit
  with Hindi front matter → near 1).

## Open questions

- Shared module location: Sāgarasaṅgama, rivulet (no: it is not
  acquisition), or a new small package.
- Does the Atlas UI switch its headline size to `sanskrit_bytes`, show both,
  or keep it as an About-page analysis?
