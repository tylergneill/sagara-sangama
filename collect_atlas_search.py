#!/usr/bin/env python3
"""Build the federated title index from the three sibling Atlases.

Each Atlas publishes `docs/data/tree.json`, the artifact its own site is built
from.  This walks all three, pulls one record per work, and emits
`docs/data/search.json` for docs/search.js to search over.  Same boundary as
`collect_atlas_counts.py`: published `docs/data/` only, never an Atlas's
pipeline scripts, `data/` working files or caches.  See CONTRACT.md.


What counts as one item
-----------------------
A title search searches for works, so the index holds what each Atlas itself
calls a text -- and each says so in `all_stats.text_count`.  The walks below
reproduce that number exactly, which is the check that this file is reading
each collection the way its own Atlas does:

    sanskrit-documents   9756 documents            == all_stats.text_count
    wikisource           3805 pages + Index items  == all_stats.text_count
    e-bharatisampat     11066 works                 > all_stats.text_count 5491

The first two reconcile on the nose.  E-bhāratīsampat is deliberately the
exception, and the `pdf_only` flag below is why.

Getting wikisource's walk right is fiddly in two ways, both load-bearing:

  * **Subpages are chapters, not works.**  3593 top-level pages carry
    `own_stats.text_count >= 1`; all 22931 subpages carry 0.  A subpage's title
    is its parent's plus a chapter label ("जयाख्यसंहिता/पटलः १"), so indexing
    them would trip the file from 8 MB to 19 MB to list rows nobody searches
    for.  The subpage count rides along on the parent as `subpages` instead.
  * **The root node holds 11 pages of its own.**  Walking `root.children` and
    forgetting `root` itself lands on 3804 and looks like a rounding quirk.
    It is one real text.  Walk the root node, not just its children.

Index items (212) are the Atlas's "Proofing" rows -- a scanned book still in
the OCR workflow, with no assembled reading text yet.  They are in its
`text_count`, so they are here, flagged `proofing` so the UI can say what they
are rather than presenting them as finished texts.


E-bhāratīsampat and `pdf_only`
------------------------------
Its `works` array holds 11066 entries but only 5491 carry text; the remaining
5575 are scans with no Unicode text behind them (9421 works have a PDF in all).
Both kinds are real catalogue entries a title search should be able to find, so
both are indexed -- but a work with no text is marked `pdf_only`, and the
frontend leaves those out until the reader asks for them.  That way the default
result counts agree with the totals the home page publishes, and the scans are
one toggle away instead of missing.

`text_count` is not a field on the works, so it is derived the way the Atlas's
own frontend does: `work.text` names the reader endpoint (`readbook3` flat,
`read_chapter` paginated) and is absent when there is no text to read.


Sizes, dates and formats
------------------------
Every record carries what its Atlas's own item row shows, because the search
results reproduce those rows rather than flattening three collections to a
lowest common denominator:

    bytes     transliterated_bytes throughout -- script-neutral, the same
              choice and the same reason as collect_atlas_counts.py
    date      each Atlas's own notion, normalised to ISO where it parses:
              wikisource's last_changed, sanskrit-documents' free-text
              `Latest update`, e-bhāratīsampat's `uploaded`
    formats   which formats exist, as a compact code per record.  The hrefs
              themselves are derived in the browser.


This file is size-sensitive, exactly like the trees it reads
------------------------------------------------------------
The frontend loads the whole index, so nothing derivable is stored -- the same
discipline that keeps sanskrit-documents' own tree at 9.7 MB instead of 41 MB,
applied again one layer up.  Written naively, with a full href per format and
per item, this file is 17.9 MB; with the ids alone it is 6.6 MB, and the
browser rebuilds every URL in `rehydrate()` in docs/search.js.

What that means per Atlas:

    sanskrit-documents  store `doc_id`; page is <site>/<doc_id>.html and each
                        download is that stem with a per-format suffix.  The
                        download labels are a fixed vocabulary of 16, so each
                        record holds indices into a shared table, not strings.
    e-bhāratīsampat     store the base64 bookid; the reader, PDF and metadata
                        endpoints are three query strings around it.
    wikisource          store the page URL as given.  It is a percent-encoded
                        Devanagari title with no shorter derivation -- the
                        Atlas itself stores these, and so does this.

Two shared tables at the top of the file, `dl_labels` and `groups`, hold the
strings that would otherwise repeat tens of thousands of times.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ATLAS_ROOT = Path(__file__).resolve().parent.parent / "atlases"
TREE = Path("docs") / "data" / "tree.json"

# Slug -> the short code stamped on every record. One letter, because it is
# repeated once per item: the full slug would add ~500 KB to the raw file for
# no information. docs/search.js maps these back to name and colour.
CODES = {
    "sanskrit-wikisource-atlas": "w",
    "e-bharatisampat-atlas": "e",
    "sanskrit-documents-atlas": "d",
    "jain-quantum-atlas": "j",
    "gretil-atlas": "g",
}

# The per-format download suffixes live in docs/search.js, beside the other
# URL derivations and copied from the Atlas's own docs/app.js -- this file
# emits the label, and the browser turns a label into an href.
#
# sanskrit-documents' `Latest update` is free text and needs the same
# forgiveness its own build_changelog.py extends it: abbreviated months, a
# stray "Julu", day-first forms. Anything that does not parse keeps its raw
# string -- the row still shows what the site says, it just cannot be sorted.
MONTHS = {m.lower(): i for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July",
     "August", "September", "October", "November", "December"], 1)}
MONTH_ABBR = {m[:3]: i for m, i in MONTHS.items()}
MONTH_ABBR["julu"] = 7  # a real typo in the corpus


def parse_loose_date(raw: str | None) -> str | None:
    """Free-text date -> 'YYYY-MM-DD' / 'YYYY-MM', or None if unreadable."""
    if not raw:
        return None
    s = raw.strip()

    # 11-Feb-2015
    m = re.match(r"^(\d{1,2})[-/\s]+([A-Za-z]+)[-/\s]+(\d{4})$", s)
    if m:
        mon = MONTH_ABBR.get(m.group(2)[:3].lower())
        if mon:
            return f"{int(m.group(3)):04d}-{mon:02d}-{min(int(m.group(1)), 31):02d}"

    # May 12, 2019  /  May 2019
    m = re.match(r"^([A-Za-z]+)\.?\s+(?:(\d{1,2})\s*,?\s*)?(\d{4})$", s)
    if m:
        mon = MONTH_ABBR.get(m.group(1)[:3].lower())
        if mon:
            if m.group(2):
                # "August 43" exists upstream; clamp rather than drop the row.
                return f"{int(m.group(3)):04d}-{mon:02d}-{min(int(m.group(2)), 31):02d}"
            return f"{int(m.group(3)):04d}-{mon:02d}"

    # already ISO, possibly with a time
    m = re.match(r"^(\d{4})-(\d{2})(?:-(\d{2}))?", s)
    if m:
        return m.group(0)[:10]

    m = re.match(r"^(\d{4})$", s)
    if m:
        return s
    return None


def prune(rec: dict) -> dict:
    """Drop empty fields. Repeated once per item, absent beats null."""
    return {k: v for k, v in rec.items() if v not in (None, "", [], {})}


class Tables:
    """Strings that repeat across records, hoisted out and referenced by index.

    Two of them. Download labels are a fixed vocabulary of 16 shared by ~9700
    documents; group names (the folder, category or domain a work sits in) are
    a few hundred shared by every item. Interning both turns tens of thousands
    of repeated strings into small integers, and lets the group carry its own
    browse URL once rather than on every member.
    """

    def __init__(self) -> None:
        self._dl: dict[str, int] = {}
        self._groups: dict[tuple[str, str], int] = {}
        self.dl_labels: list[str] = []
        self.groups: list[dict] = []

    def dl_label(self, label: str) -> int:
        if label not in self._dl:
            self._dl[label] = len(self.dl_labels)
            self.dl_labels.append(label)
        return self._dl[label]

    def group(self, atlas: str, title: str | None, key: str | None = None,
              parent: int | None = None) -> int | None:
        """Intern one group. `key` is whatever that Atlas derives its URL from.

        `parent` makes the table a forest rather than a flat list: a group is
        identified by its title AND where it sits, so wikisource's उपनिषदः
        directly under the root and the उपनिषदः nested inside प्रमुखोपनिषदः
        stay two different groups. Storing the parent once per group -- not
        once per member -- is what keeps a five-level path cheap.
        """
        if not title:
            return None
        ident = (atlas, title, parent)
        if ident not in self._groups:
            self._groups[ident] = len(self.groups)
            self.groups.append(prune({"a": atlas, "t": title, "k": key,
                                      "p": parent}))
        return self._groups[ident]

    def path(self, atlas: str, titles: list[str], keys: list[str | None] | None = None) -> int | None:
        """Intern a whole ancestor chain, returning the id of its LAST group.

        The leaf is what an item stores; walking `p` back up recovers the rest.
        """
        gid = None
        for i, title in enumerate(titles):
            key = keys[i] if keys and i < len(keys) else None
            gid = self.group(atlas, title, key, gid)
        return gid


# --------------------------------------------------------------------------
# sanskrit-documents
# --------------------------------------------------------------------------

def read_sanskrit_documents(tree: dict, tables: "Tables") -> list[dict]:
    """One record per document, enumerated from folders, grouped by topic.

    Two axes, and they do different jobs here. The FOLDERS branch is canonical
    -- one document in exactly one node -- so it is what enumerates the corpus
    without listing anything twice. But a folder is a server directory, mostly
    named for a deity and not uniformly so (veda, upanishhat and the z_misc_*
    buckets are genre divisions), which makes it a poor label for a result.

    The TOPICS branch is the site's own 87 curated `/sanskrit/<slug>/` pages,
    which is what a reader recognises. It is multi-valued -- 2.08 pages per
    document, up to 9 -- so it cannot enumerate, but it can label: every one
    of the 9756 documents appears on at least one topic, so nothing loses its
    group by preferring topics here.

    So: walk folders for the item list, and attach the topics each document
    sits on. Both are flat, one level deep, unlike wikisource's nested tree.
    """
    branches = {c.get("id"): c for c in tree["root"].get("children") or []}
    folders = branches.get("loc")
    if folders is None:
        raise ValueError("sanskrit-documents tree has no 'loc' (folders) branch")

    # doc_id -> the topic groups it is listed under. Built first, so the walk
    # below can attach them as it goes. A topic node's pages are bare `ref`
    # pointers ({id, title, ref}) into the folders branch, which is why this
    # reads `ref` and falls back to meta.doc_id.
    topics: dict[str, list[int]] = {}
    for node in (branches.get("lst") or {}).get("children") or []:
        slug = (node.get("id") or "").split(":", 1)[-1]
        gid = tables.group("d", node.get("title"), f"sanskrit/{slug}")
        if gid is None:
            continue
        for p in node.get("pages") or []:
            ref = p.get("ref") or ""
            doc_id = ref.split(":", 1)[-1] if ref else (p.get("meta") or {}).get("doc_id")
            if doc_id:
                topics.setdefault(doc_id, []).append(gid)

    out: list[dict] = []
    seen: set[str] = set()
    for node in folders.get("children") or []:
        for p in node.get("pages") or []:
            meta = p.get("meta") or {}
            doc_id = meta.get("doc_id")
            if not doc_id or doc_id in seen:
                continue
            seen.add(doc_id)

            stats = p.get("stats") or {}
            out.append(prune({
                "a": "d",
                "t": p.get("title"),
                "n": meta.get("title_deva"),
                # The stem, not a URL: page and every download hang off it.
                "i": doc_id,
                # Local-only plain text; see the note on the e-bharatisampat
                # branch. A bare 1, not a key: the key this Atlas's server
                # resolves IS `i`, and repeating a 40-char path per item cost
                # ~0.4 MB in a file the browser loads whole.
                "lt": 1 if p.get("has_text") else None,
                "b": stats.get("transliterated_bytes"),
                # Already `YYYY-MM`: that Atlas normalizes the site's free-text
                # `Latest update` in its own pipeline now, so there is nothing
                # left here to parse. parse_loose_date still accepts it (the
                # ISO branch), and stays as the reader for `latest_update` in
                # any tree.json built before that change.
                "d": meta.get("updated") or parse_loose_date(meta.get("latest_update")),
                "au": meta.get("author"),
                "lang": meta.get("language"),
                "g": topics.get(doc_id) or None,
                "fmt": [tables.dl_label(label)
                        for label in (meta.get("downloads") or [])],
                # Printed witnesses: a scan of an edition containing this text,
                # not necessarily the one it was encoded from -- the Atlas is
                # careful about that and so is the tooltip in search.js.
                "scan": [s.get("u") for s in (meta.get("scans") or []) if s.get("u")],
            }))
    return out


# --------------------------------------------------------------------------
# wikisource
# --------------------------------------------------------------------------

def read_wikisource(tree: dict, tables: "Tables") -> list[dict]:
    """One record per text-bearing page, plus the Index ('Proofing') items.

    Walks the root node itself as well as its children: root carries 11 pages
    directly, and skipping them lands one short of the published text_count.
    """
    out: list[dict] = []
    # id -> the record already emitted for it, so a page found again under a
    # second category adds that path instead of being skipped. 288 pages sit
    # in more than one place (up to 3), and dropping the later ones lost real
    # classifications -- ऐतरेयोपनिषद् is both उपनिषदः and
    # उपनिषदः / प्रमुखोपनिषदः, and only the first survived.
    seen: dict[str, dict] = {}

    def visit(node: dict, path: list[str]) -> None:
        # The whole ancestor chain, not just its head. This tree is up to five
        # levels deep (दर्शनानि / आस्तिकदर्शनानि / उत्तरमीमांसादर्शनम् /
        # अद्वैतम् / उपनिषद्भाष्यम्) and keeping only the top level threw away
        # everything that made the classification specific.
        gid = tables.path("w", path)
        for p in node.get("pages") or []:
            pid = p.get("id")
            if not pid:
                continue
            if pid in seen:
                if gid is not None:
                    seen[pid].setdefault("g", []).append(gid)
                continue
            # own_stats, not stats: `stats` is a rollup including every nested
            # subpage, so a navigational parent whose own body is empty would
            # look text-bearing because its chapters are.
            if ((p.get("own_stats") or {}).get("text_count") or 0) < 1:
                continue
            stats = p.get("stats") or {}
            rec = prune({
                "a": "w",
                "t": p.get("title"),
                # Local-only plain text; see the note on the e-bharatisampat
                # branch. A bare 1, not a key: the key is the TITLE, already
                # stored as `t`, and that Atlas's server indexes by it.
                "lt": 1 if p.get("has_text") else None,
                # Percent-encoded Devanagari, with no shorter derivation than
                # itself -- the one URL in this index that is stored, not built.
                "u": p.get("url"),
                # The rollup here, deliberately: the reader opening this work
                # gets the whole thing, chapters included.
                "b": stats.get("transliterated_bytes"),
                "d": parse_loose_date(stats.get("last_changed")),
                "g": [gid] if gid is not None else None,
                "sub": len(p.get("subpages") or []) or None,
                "scan": [s.get("url") for s in (p.get("source_indexes") or [])
                         if s.get("url")],
            })
            seen[pid] = rec
            out.append(rec)

        for it in node.get("index_items") or []:
            iid = it.get("id")
            if not iid:
                continue
            if iid in seen:
                if gid is not None:
                    seen[iid].setdefault("g", []).append(gid)
                continue
            stats = it.get("stats") or {}
            rec = prune({
                "a": "w",
                "t": it.get("title"),
                "u": it.get("url"),
                # An untranscluded scan whose leaves the Atlas folded into a
                # file for it. Same flag, same meaning as on a page -- this
                # branch simply never read it before.
                "lt": 1 if it.get("has_text") else None,
                "b": stats.get("transliterated_bytes"),
                "d": parse_loose_date(stats.get("last_changed")),
                "g": [gid] if gid is not None else None,
                # Scanned/OCR source still in the Proofreading workflow: there
                # is no assembled mainspace text to open yet, only the scan.
                "pf": 1,
                # A scan whose pages were never populated has no text ANYWHERE
                # -- not transcluded, not on leaves, nothing to open. That is
                # the same thing e-bhāratīsampat calls PDF-only, so it gets the
                # same flag and the same default-hidden treatment: this search
                # is for finding text, and an unpopulated scan is not text.
                #
                # An Index item WITH text (has_text, its leaves folded into a
                # file) is a real full text and stays visible.
                "po": None if it.get("has_text") else 1,
            })
            seen[iid] = rec
            out.append(rec)

        for ch in node.get("children") or []:
            visit(ch, path + [ch.get("title")])

    # Walk the root ONLY. Its own 11 pages have no category and get an empty
    # path; visit() recurses into the children itself, each one starting a
    # path with its own title. (Walking the children again here, as this did
    # before paths, visited every node twice and gave each page its category
    # twice over.)
    visit(tree["root"], [])
    return out


# --------------------------------------------------------------------------
# e-bharatisampat
# --------------------------------------------------------------------------

def encoded_id(work: dict) -> str:
    """The site's base64 bookid, as the Atlas's app.js reconstructs it."""
    wid = str(work.get("id") or "")
    if work.get("id_encoded"):
        return work["id_encoded"]
    if wid.isdigit():
        import base64
        return base64.b64encode(wid.encode()).decode()
    return wid


def read_e_bharatisampat(tree: dict, tables: "Tables") -> list[dict]:
    """One record per work, PDF-only ones flagged rather than dropped.

    Text and PDF are two distinct documents here, not two renderings of one,
    so each gets its own link and the title points at the metadata page --
    the one page that describes the work rather than a single format of it.
    All three endpoints are query strings around the one base64 bookid, so the
    id is what is stored and search.js builds the rest.
    """
    out: list[dict] = []
    for w in tree.get("works") or []:
        kind = w.get("text")
        sizes = w.get("sizes") or {}
        out.append(prune({
            "a": "e",
            "t": w.get("title"),
            "i": encoded_id(w),
            # Local-only plain text: the key an Atlas's `serve_docs.py
            # --fulltext` resolves at /text/<key>. Carried ONLY when the
            # Atlas published has_text, which it sets from its own cache
            # presence -- so this layer still reads nothing but docs/data/ and
            # CONTRACT.md holds. Absent on the published site, where no local
            # server exists to serve it.
            #
            # The one atlas where this is a real value rather than a flag:
            # its server keys on the SERIAL, while `i` here is the base64
            # bookid. The other two reuse a field they already store.
            "lt": str(w["serial"]) if (w.get("has_text") and w.get("serial")) else None,
            "b": sizes.get("transliterated_bytes"),
            "d": parse_loose_date(w.get("uploaded")),
            "au": w.get("author"),
            "y": str(w["publish_year"]) if w.get("publish_year") else None,
            "pub": w.get("publisher"),
            "ed": w.get("editor"),
            "pg": str(w["pages"]) if w.get("pages") else None,
            # domain / sub_domain as a two-level path, the same shape as
            # wikisource's deeper one -- so `sd` is gone and the frontend has
            # one way to render a group instead of a per-atlas special case.
            "g": [gid] if (gid := tables.path(
                "e", [t for t in (w.get("domain"), w.get("sub_domain")) if t]
            )) is not None else None,
            # `read_chapter` means the site paginates by chapter, i.e. a real
            # table of contents exists; `readbook3` is one flat text. Nothing
            # else in the catalogue carries a signal about internal navigation.
            "toc": 1 if kind == "read_chapter" else None,
            "txt": 1 if kind else None,
            "pdf": 1 if w.get("pdf") else None,
            # No reader endpoint means no Unicode text behind this entry: a
            # scanned book only. Hidden by default in the UI so the default
            # counts agree with the totals the home page publishes.
            "po": 1 if not kind else None,
        }))
    return out


# --------------------------------------------------------------------------
# jain-quantum and gretil -- both publish the flat works+axes shape
# --------------------------------------------------------------------------

def read_jain_quantum(tree: dict, tables: "Tables") -> list[dict]:
    """One record per catalogued item; those without a public text flagged.

    The id is the six-digit sr_no, from which search.js derives the Quantum
    viewer and booktext URLs (the latter also needs the title, carried as `t`).
    Items with no Quantum text -- the post-2022 accessions and the scan-only
    entries -- are indexed but flagged `po`, so the default view agrees with
    the home page's text_count, exactly as E-bhāratīsampat's PDF-only works.
    """
    out: list[dict] = []
    for w in tree.get("works") or []:
        sizes = w.get("sizes") or {}
        out.append(prune({
            "a": "j",
            # `t` is the romanised title (the booktext slug is built from it);
            # `n` the Indic-script one the row displays, as for sanskrit-documents.
            "t": w.get("title_en") or w.get("title"),
            "n": w.get("title") if w.get("title") != w.get("title_en") else None,
            "i": w.get("id"),
            "lt": 1 if w.get("has_text") else None,
            "b": sizes.get("transliterated_bytes"),
            "d": w.get("added"),
            "au": w.get("author"),
            "y": w.get("publish_year"),
            "pg": str(w["pages"]) if w.get("pages") else None,
            "lang": w.get("language"),
            "g": [gid] if (gid := tables.path(
                "j", [t for t in (w.get("domain"), w.get("sub_domain")) if t]
            )) is not None else None,
            "txt": 1 if w.get("text") else None,
            "pdf": 1 if w.get("pdf") else None,
            "po": None if w.get("text") else 1,
        }))
    return out


def read_gretil(tree: dict, tables: "Tables") -> list[dict]:
    """One record per work: a TEI file, or a legacy-only text.

    `i` is the primary file path under the mirror root (the TEI XML, else the
    legacy HTM), which is all search.js needs to build the link. Every work
    has text, so nothing is flagged `po`; `tei` says which layer it is.
    """
    out: list[dict] = []
    for w in tree.get("works") or []:
        sizes = w.get("sizes") or {}
        files = w.get("files") or []
        primary = next((f for f in files if f.endswith(".xml")), None) or \
            next((f for f in files if f.endswith(".htm") and "/transformations/" not in f), None) or \
            (files[0] if files else None)
        out.append(prune({
            "a": "g",
            "t": w.get("title"),
            "i": primary,
            "lt": w.get("id") if w.get("has_text") else None,
            "b": sizes.get("transliterated_bytes"),
            "d": w.get("added"),
            "au": w.get("author"),
            "g": [gid] if (gid := tables.path(
                "g", [t for t in (w.get("domain"), w.get("sub_domain")) if t]
            )) is not None else None,
            "txt": 1,
            "tei": 1 if w.get("tei") else None,
        }))
    return out


READERS = {
    "sanskrit-documents-atlas": read_sanskrit_documents,
    "sanskrit-wikisource-atlas": read_wikisource,
    "e-bharatisampat-atlas": read_e_bharatisampat,
    "jain-quantum-atlas": read_jain_quantum,
    "gretil-atlas": read_gretil,
}


def collect(root: Path) -> dict:
    atlases = []
    items: list[dict] = []
    tables = Tables()

    for slug, reader in READERS.items():
        path = root / slug / TREE
        entry = {"slug": slug, "code": CODES[slug]}
        if not path.exists():
            entry["error"] = f"no tree.json at {path}"
            atlases.append(entry)
            continue
        try:
            tree = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError) as exc:
            entry["error"] = f"unreadable: {exc}"
            atlases.append(entry)
            continue

        recs = reader(tree, tables)
        items.extend(recs)

        stats = tree.get("all_stats") or {}
        entry["indexed"] = len(recs)
        entry["text_count"] = stats.get("text_count")
        entry["pdf_only"] = sum(1 for r in recs if r.get("po"))
        # Every Atlas but e-bhāratīsampat should reconcile exactly; that one is
        # expected to exceed its text_count by its PDF-only works. A mismatch
        # anywhere else means a walk has drifted from what the Atlas publishes.
        expected = entry["text_count"]
        if expected is not None:
            got = entry["indexed"] - entry["pdf_only"]
            entry["reconciles"] = (got == expected)
        entry["tree_mtime"] = datetime.fromtimestamp(
            path.stat().st_mtime, timezone.utc).isoformat(timespec="seconds")
        atlases.append(entry)

    return {
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "note": "titles from each Atlas's docs/data/tree.json; snapshot "
                "figures, not live",
        "atlases": atlases,
        "dl_labels": tables.dl_labels,
        "groups": tables.groups,
        "items": items,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--atlas-root", type=Path, default=ATLAS_ROOT,
                    help=f"where the Atlas repos live (default: {ATLAS_ROOT})")
    ap.add_argument("--out", type=Path,
                    default=Path(__file__).parent / "docs" / "data" / "search.json",
                    help="where to write search.json")
    ap.add_argument("--print", action="store_true", dest="show",
                    help="print the summary table")
    args = ap.parse_args()

    data = collect(args.atlas_root)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(data, ensure_ascii=False,
                                   separators=(",", ":")))

    total = len(data["items"])
    size_mb = args.out.stat().st_size / 1e6
    print(f"wrote {args.out} -- {total} items, {size_mb:.1f} MB")

    problems = []
    for a in data["atlases"]:
        if a.get("error"):
            problems.append(f"{a['slug']}: {a['error']}")
        elif a.get("reconciles") is False:
            problems.append(
                f"{a['slug']}: indexed {a['indexed'] - a['pdf_only']} texts "
                f"but tree.json publishes text_count {a['text_count']}")

    if args.show or problems:
        print()
        print(f"  {'atlas':<28}{'indexed':>9}{'text_count':>12}{'pdf-only':>10}")
        for a in data["atlases"]:
            if a.get("error"):
                print(f"  {a['slug']:<28}{'--':>9}   {a['error']}")
                continue
            mark = "" if a.get("reconciles") else "  <-- MISMATCH"
            print(f"  {a['slug']:<28}{a['indexed']:>9}"
                  f"{a['text_count'] if a['text_count'] is not None else '--':>12}"
                  f"{a['pdf_only']:>10}{mark}")

    if problems:
        print()
        for p in problems:
            print(f"  ! {p}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
