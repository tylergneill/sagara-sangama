#!/usr/bin/env python3
"""Collect corpus counts from the sibling Atlas projects.

Each Atlas publishes `docs/data/tree.json`, the artifact its own site is built
from, and each of those carries an `all_stats` block.  This walks the three
Atlases, reads that block, and emits `docs/data/counts.json` for the
Sāgarasaṅgama home page to typeset.


Which number to show
--------------------
`all_stats` offers both `count` and `text_count`, and only one of them means
the same thing in all three collections:

    atlas                       count    text_count
    sanskrit-wikisource         26757          3805
    e-bharatisampat             11066          5557
    sanskrit-documents           8547          8547

`count` counts nodes, and a node is a different animal in each Atlas: for
wikisource it includes every category page in the tree, so the 26757 is mostly
structure rather than texts.  `text_count` counts texts, everywhere.  So
`text_count` is what the home page shows, and `count` rides along in the JSON
for anyone who wants it.

The two agree exactly for sanskrit-documents because every document there is a
text; the gap is widest for wikisource, whose tree is largely navigational.


Scope
-----
Read `all_stats`, never `root.stats`.  For wikisource the `root` node is one
subtree among several and its stats cover 22324/1647 against the corpus-wide
26757/3805 - reading it would undercount the collection by more than half.


Fields that not every Atlas reports
-----------------------------------
Three of the collected figures are absent from one Atlas or another.  Each is
left as None rather than substituted or estimated, and the page shows a dash,
so a gap reads as a gap:

    iast_bytes   the transliterated measure, script-neutral where
                 content_bytes is not.  e-bharatisampat's tree.json carries
                 `sized: 0` and no byte fields, pending its full fetcher
                 writing sizes onto the works.  Fills in on the next run
                 once that lands.
    pdfs         all three now report it, each deduplicating by its own
                 notion of one source: wikisource by work, sanskrit-documents
                 by scanned volume (one book cited by forty stotras is one
                 PDF).  Absent only if an Atlas stops publishing it.
    avg_iast     derived, so it is absent exactly where iast_bytes is.

Because these are all read straight from `all_stats`, an Atlas that starts
reporting one needs nothing here but a re-run.

The boundary is each Atlas's published `docs/data/tree.json` and nothing
else.  A figure an Atlas has computed but not published is not ours to reach
in for: the fix belongs upstream, in the Atlas that owns the number.


Freshness
---------
These are snapshot figures, not live ones, and each Atlas is explicit that its
numbers move when its snapshot is re-pulled.  The mtime of each tree.json is
recorded alongside the counts so the page can say how old they are rather than
implying they are current.  Re-run this after any Atlas re-ingests.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# Atlases live beside this project: sagara-sangama/{sagara-sangama,atlases}/
ATLAS_ROOT = Path(__file__).resolve().parent.parent / "atlases"
TREE = Path("docs") / "data" / "tree.json"
# A stopgap, and the one file read outside docs/data/ -- see CONTRACT.md,
# "The one exception". Goes when every Atlas publishes `all_stats.sourced`.
VERSION = Path("docs") / "VERSION"
_CONTENT_VERSION_RE = re.compile(
    r'^__content_version__\s*=\s*["\']?(\d{4}-\d{2}-\d{2})', re.M)


def read_sourced(stats: dict, atlas_dir: Path) -> str | None:
    """When the Atlas took its copy of the collection, as YYYY-MM-DD.

    `all_stats.sourced` where the tree publishes it; until all five do, the
    `__content_version__` line of docs/VERSION, which is the same date each
    Atlas prints on its own About page as "data last sourced". None when
    neither is there -- the card then shows no date rather than a guess.
    """
    if stats.get("sourced"):
        return str(stats["sourced"])[:10]
    try:
        match = _CONTENT_VERSION_RE.search(
            (atlas_dir / VERSION).read_text(encoding="utf-8"))
    except OSError:
        return None
    return match.group(1) if match else None

# slug -> how the home page should label it
ATLASES = (
    {
        "slug": "sanskrit-wikisource-atlas",
        "name": "Sanskrit Wikisource",
        "site": "sa.wikisource.org",
        "site_url": "https://sa.wikisource.org",
        "atlas_url": "https://tylergneill.github.io/sanskrit-wikisource-atlas",
        "repo": "https://github.com/tylergneill/sanskrit-wikisource-atlas",
        "noun": "texts",
    },
    {
        "slug": "e-bharatisampat-atlas",
        "name": "E-bhāratīsampat",
        "site": "ebharatisampat.in",
        "site_url": "https://ebharatisampat.in",
        "atlas_url": "https://tylergneill.github.io/e-bharatisampat-atlas",
        "repo": "https://github.com/tylergneill/e-bharatisampat-atlas",
        "noun": "texts",
    },
    {
        "slug": "sanskrit-documents-atlas",
        "name": "Sanskrit Documents",
        "site": "sanskritdocuments.org",
        "site_url": "https://sanskritdocuments.org",
        "atlas_url": "https://tylergneill.github.io/sanskrit-documents-atlas",
        "repo": "https://github.com/tylergneill/sanskrit-documents-atlas",
        "noun": "texts",
    },
    {
        "slug": "jain-quantum-atlas",
        "name": "Jain Quantum",
        "site": "jainqq.org",
        "site_url": "https://jainqq.org",
        "atlas_url": "https://tylergneill.github.io/jain-quantum-atlas",
        "repo": "https://github.com/tylergneill/jain-quantum-atlas",
        "noun": "texts",
    },
    {
        "slug": "gretil-atlas",
        "name": "GRETIL",
        "site": "gretil.sub.uni-goettingen.de",
        "site_url": "https://tylergneill.github.io/gretil-mirror/gretil.html",
        "atlas_url": "https://tylergneill.github.io/gretil-atlas",
        "repo": "https://github.com/tylergneill/gretil-atlas",
        "noun": "texts",
    },
)


def read_atlas(spec: dict, root: Path) -> dict:
    """Counts for one Atlas, or a record carrying `error` if unreadable."""
    out = {k: spec[k] for k in
           ("slug", "name", "site", "site_url", "atlas_url", "repo", "noun")}
    path = root / spec["slug"] / TREE

    if not path.exists():
        out["error"] = f"no tree.json at {path}"
        return out

    try:
        data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        out["error"] = f"unreadable: {exc}"
        return out

    stats = data.get("all_stats")
    if not isinstance(stats, dict):
        out["error"] = "tree.json has no all_stats block"
        return out
    if "text_count" not in stats:
        out["error"] = "all_stats has no text_count"
        return out

    out["texts"] = stats["text_count"]
    out["nodes"] = stats.get("count")

    # IAST, not content_bytes: content_bytes measures the text as stored, so
    # Devanagari costs ~3 bytes a character and a Devanagari collection looks
    # larger than a roman one holding the same work. The transliterated figure
    # is script-neutral and the only one comparable across collections.
    #
    # Absent until an Atlas publishes it in its own tree.json -- this reads
    # that file and nothing else, never an Atlas's internal pipeline data.
    out["iast_bytes"] = stats.get("transliterated_bytes")
    # How many works the byte figures actually cover, where the Atlas says so.
    # Less than the text count means an incomplete fetch, so the byte totals
    # are a floor. Collected but not currently shown on either page.
    out["sized"] = stats.get("sized")

    # Per text, always -- never per measured file. Where an Atlas has sized
    # only part of its corpus the two differ, and this layer counts items with
    # searchable text, so the text count is the denominator that answers "how
    # much text does a text here run to". Dividing by the measured subset
    # instead would answer a question about the fetcher's progress.
    if out["iast_bytes"] and out["texts"]:
        out["avg_iast_bytes"] = out["iast_bytes"] / out["texts"]
    else:
        out["avg_iast_bytes"] = None

    # Only reported by the Atlases that track scans as a counted field.
    out["pdfs"] = stats.get("pdf_count")

    # the Atlas's own notion of currency, where it keeps one
    out["last_changed"] = stats.get("last_changed")
    # When the copy was taken: what the home card prints as "as of". Not
    # tree_mtime below, which is only when the file was last rewritten -- a
    # rebuild from an old fetch moves that and leaves the content where it was.
    out["sourced"] = read_sourced(stats, root / spec["slug"])
    out["tree_mtime"] = datetime.fromtimestamp(
        path.stat().st_mtime, timezone.utc).isoformat(timespec="seconds")
    return out


def collect(root: Path) -> dict:
    atlases = [read_atlas(spec, root) for spec in ATLASES]
    total = sum(a["texts"] for a in atlases if "texts" in a)
    # Sum only over the Atlases that report bytes, so a partial total is the
    # sum of what is actually known rather than an understated whole.
    sized = [a for a in atlases if a.get("iast_bytes")]
    return {
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "note": "text_count from each Atlas's docs/data/tree.json all_stats; "
                "snapshot figures, not live",
        "total_texts": total,
        "total_iast_bytes": sum(a["iast_bytes"] for a in sized) or None,
        "sized_atlases": len(sized),
        "atlases": atlases,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--atlas-root", type=Path, default=ATLAS_ROOT,
                    help=f"where the Atlas repos live (default: {ATLAS_ROOT})")
    ap.add_argument("--out", type=Path,
                    default=Path(__file__).parent / "docs" / "data" / "counts.json",
                    help="where to write counts.json")
    ap.add_argument("--print", action="store_true", dest="show",
                    help="print the table instead of only writing JSON")
    args = ap.parse_args()

    if not args.atlas_root.is_dir():
        sys.exit(f"error: no atlas directory at {args.atlas_root}")

    result = collect(args.atlas_root)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(f"wrote {args.out}")

    failed = [a for a in result["atlases"] if "error" in a]
    if args.show or failed:
        def num(v, fmt, width):
            return format(v, fmt) if v else "--".rjust(width)

        print(f"  {'atlas':26} {'texts':>8} {'IAST MB':>9} {'avg KB':>8} "
              f"{'PDFs':>8}   snapshot")
        for a in result["atlases"]:
            if "error" in a:
                print(f"  {a['name']:26} {a['error']}")
                continue
            print(f"  {a['name']:26} {a['texts']:>8,} "
                  f"{num(a['iast_bytes'] and a['iast_bytes'] / 1e6, '>9,.1f', 9)} "
                  f"{num(a['avg_iast_bytes'] and a['avg_iast_bytes'] / 1e3, '>8,.1f', 8)} "
                  f"{num(a['pdfs'], '>8,', 8)}   {a['sourced'] or '--'}")
        total_mb = (result["total_iast_bytes"] or 0) / 1e6
        print(f"  {'total':26} {result['total_texts']:>8,} "
              f"{total_mb:>9,.1f}"
              f"   ({result['sized_atlases']} of {len(result['atlases'])} sized)")

    if failed:
        print(f"warning: {len(failed)} atlas(es) could not be read",
              file=sys.stderr)


if __name__ == "__main__":
    main()
