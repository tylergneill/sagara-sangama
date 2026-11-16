# Search UX across Sāgarasaṅgama and the five Atlases — spec

Status: **designed 2026-11-10, not started.** A cross-repo change, to be built
on top of `add-gretil-and-jain-2` (which carries the fuzzy toggle below).
Touches this repo and all five Atlases' `docs/app.js`.

## Why

Search grew one feature at a time and now behaves differently per surface:

- **The Atlases search only the script on screen.** In Devanagari mode an
  ASCII query cannot match any title; it hits only authors that happen to fold
  and, in the EBS Atlas, the hidden `title_eg`. Results look random (serials
  120 and 10458 for "karmapradipa", never 9021).
- **The Atlases' "exact" chip does three unrelated jobs**: a user-toggled
  mode, the landing state of Sāgarasaṅgama's deep links (`?q=…&exact=1`, built
  in `docs/search.js`), and, in the Wikisource and Sanskrit Documents Atlases,
  the magnifier on a work row ("Also filed under … click the search icon").
  A hidden mode that silently changes results is easy to forget is on.
  Sāgarasaṅgama has no such chip and gets by on ranking.
- **Fuzzy spelling exists only in Sāgarasaṅgama**, on `add-gretil-and-jain-2`
  (`fuzzyFold`, measured on the Jain library's Hindi-style romanisation).
- **Alternate titles are handled three ways**: EBS `title_eg` (romanized,
  sometimes English; ad-hoc ASCII with typos) is searched but never shown;
  Jain `title_en` is the displayed Latin label in Sāgarasaṅgama's branch and
  unused by the Jain Atlas.
- **Filters hide matches silently.** Sāgarasaṅgama hides PDF-only items by
  default, so a search for an English EBS title (all PDF-only) finds nothing
  with no hint that it matched.

## Principles

1. **The display script never changes what search finds.** It is a reading
   preference.
2. **Every promise a mode makes is checkable by looking at the result.**
3. **Loosening is opt-in and visible**; loose hits never outrank as-typed hits.
4. **Nothing that affects the result list is hidden**: why a row matched, and
   how many matches a filter removed.
5. **One implementation of the matching rules**, specified here, so the six
   surfaces cannot drift apart.

## Design

### Search keys

Each searchable field gets keys in two forms: its displayed form, and its
IAST transliteration folded by `fold` (diacritics stripped, lowercase,
punctuation and hyphens to spaces, plus Sāgarasaṅgama's existing sh/ch/aa/ri
folds). The query gets the same: as typed, folded, and transliterated from
Devanagari when it is Devanagari. A match on any form is a match.

**No new normalization in this change** (e.g. dropping a final visarga). Only
the folds already in use.

### Fields

| field | searched by default | can be an exact hit | shown |
|---|---|---|---|
| title | yes | yes | yes |
| author | yes | yes | yes |
| alternate title (EBS `title_eg`; Jain `title_en` where not the displayed label) | yes | **no** | only as the "matched: …" hint |

### Ranking (contains search, the only mode)

1. whole-key match on title, then author
2. prefix match on title, then author
3. substring match on title, then author
4. any match on an alternate title
5. fuzzy hits (when the toggle is on)

Ties: shorter title first, then code-point order (as Sāgarasaṅgama does now).
Whole-key matches at the top replace what the exact chip was for.

### The "matched: …" hint

A row that matched **only** through an alternate title shows it on a muted
line under the title: `matched: Abhijnana-shakuntalam`. Typos in the source
become visible exactly when they explain a result.

### Fuzzy spelling toggle

`add-gretil-and-jain-2`'s `fuzzyFold` and `FUZZY_MIN`, unchanged, in
Sāgarasaṅgama and every Atlas. Visible as a labelled checkbox ("fuzzy
spelling"), off by default. Applies to title, author and alternate titles.

### No exact chip; exact lookups are a page state

Remove the user-facing exact toggle from all five Atlases. The two internal
callers become a **lookup state** shown as a banner above the results, not as a
search mode:

- Sāgarasaṅgama deep link `?q=<title>&exact=1` (keep the URL parameter so old
  links work): "Showing the title *X* — show all matches".
- Atlas magnifier: "Every filing of *X* (2) — clear".

Exact comparison in a lookup is on the visible title's keys only.

### Filtered-out matches are counted

When a filter hides matches, say how many and offer to show them:
"3 more PDF-only matches — show". Applies to Sāgarasaṅgama's PDF-only default
and any Atlas filter that hides works (e.g. Wikisource's
"include asambaddhavargīkṛtam").

## Interim state (2026-11-10, shipped before this)

- EBS `title_eg` flows into both searches as plain contains-matching
  (`parse_metadata` → `tree.json` → `collect_atlas_search.py` field `te`).
- The EBS Atlas leaves `title_eg` out of its exact mode, so exact compares only
  what is visible.
- No hint, no ranking tier for it yet, no change to the chip.

## Test cases

| query | display | expect |
|---|---|---|
| karmapradipa | Devanagari, any Atlas or Sāgarasaṅgama | 120, 10458 (via `title_eg`, with hint) and 9021 (via title) |
| abhijnana shakuntalam | any | the Śākuntala works, hint shown if only `title_eg` matched |
| practical grammar of the pali | Sāgarasaṅgama, default filters | "1 more PDF-only match — show" → 12340 |
| कादम्बरी / kādambarī / kadambari | any | identical result sets |
| Wikisource magnifier on kāṇva-śatapatha brāhmaṇam | — | banner "Every filing of … (2)", both rows |
| Sāgarasaṅgama row → Atlas | — | banner, the linked title first |
| vadidevsuri, fuzzy off / on | — | nothing / Vādidevasūri, ranked after as-typed hits |

## Open questions

- Does the Atlas need fuzzy at all, or only Sāgarasaṅgama? (Default: both, for
  principle 5.)
- Should alternate-title hits be cut off below some query length, as fuzzy is
  by `FUZZY_MIN`?
