#!/usr/bin/env python3
"""Collect growth series from the sibling Atlas projects.

The companion to `collect_atlas_counts.py`, which reads each Atlas's totals as
they stand today.  This reads the same Atlases' `docs/data/changelog.json` --
the artifact each already publishes to draw its own growth chart -- and emits
`docs/data/growth.json`, the series the About page's chart plots.

Same boundary as the counts collector, for the same reason: an Atlas's
published `docs/data/` and nothing else.  See CONTRACT.md.


One shape out of three shapes in
-------------------------------
The three changelogs do not agree on a shape, and there is no reason they
should -- each was built to drive its own Atlas's chart, and those charts
answer different questions about different collections.  What they do agree on
is the pair of figures this layer needs, so the reading is per-Atlas and the
output is uniform:

    sanskrit-wikisource   a list of monthly entries; the corpus-wide figures
                          live in `all`, not at the top level.  The top-level
                          `new` covers the `root` subtree alone -- 1647 of
                          3805 texts -- so reading it would undercount the
                          collection by more than half, the same trap
                          `collect_atlas_counts.py` documents for `root.stats`.

    sanskrit-documents    a list of yearly entries whose top-level `new` is
                          already corpus-wide; there is no `all` to prefer.

    e-bharatisampat       a dict with `periods`, yearly, each carrying
                          `cumulative_text_count` and
                          `cumulative_iast_bytes_total` -- fields it added on
                          2026-08-26 so this layer would not have to assemble
                          them from format bands whose meaning is local to
                          that Atlas.

Each series is emitted as `{date, texts, bytes}` points, cumulative, monthly.

**Months are the shared publishing granularity**, agreed across the three
Atlases so they can be plotted on one time axis; each stamps a month at its
start.  The chart groups them up to quarters or years at render time, which is
the same split each Atlas's own About page uses -- publish the finest grain,
let the reader coarsen it.


Bytes means `transliterated_bytes`, everywhere
----------------------------------------------
The IAST measure, exactly as in `collect_atlas_counts.py` and for the same
reason: `content_bytes` charges Devanagari ~3 bytes a character, so a
Devanagari collection measured raw looks larger than a roman one holding the
same works, and the three curves would not be comparable.  No other size is
collected.


Where the series stop short of the totals
-----------------------------------------
A growth series ends at or below its Atlas's headline count, and the gap is
worth reporting rather than smoothing:

    sanskrit-documents    lands exactly on its tree's totals.
    sanskrit-wikisource   lands on its tree's text_count exactly, and within
                          0.01% on bytes.
    e-bharatisampat       ends 16 texts short, those works carrying no date at
                          all.  A work with no date has no place on a time
                          axis, and its own `undated_works` says how many.

So `final` records where each series actually ends, and the page compares it
against the counts to say so instead of implying the curve is the whole
collection.

Wikisource's series is not monotonic, and that is history rather than a bug:
pages are deleted, merged and moved on a live wiki, so a corpus rebuilt from
revision history genuinely dips.  Nothing here smooths it.



Run:
    python collect_atlas_growth.py
    python collect_atlas_growth.py --print
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Atlases live beside this project: sagara-sangama/{sagara-sangama,atlases}/
ATLAS_ROOT = Path(__file__).resolve().parent.parent / "atlases"
CHANGELOG = Path("docs") / "data" / "changelog.json"


def _points_from_entries(entries: list, stats_key: str | None) -> list[dict]:
    """Series from a list-shaped changelog (wikisource, sanskrit-documents).

    Each entry describes one period and carries the totals as of its end in a
    `new` block.  `stats_key` picks which `new` to read: wikisource nests the
    corpus-wide one under `all`, sanskrit-documents has only the top-level one.
    """
    points = []
    for entry in entries:
        block = entry.get(stats_key) if stats_key else entry
        if not isinstance(block, dict):
            continue
        new = block.get("new")
        if not isinstance(new, dict):
            continue
        texts = new.get("text_count")
        if texts is None:
            continue
        points.append({
            "date": entry["date"][:10],
            "texts": texts,
            # Absent rather than zero where an Atlas reports no byte figure:
            # zero would draw a line along the axis and read as a measurement.
            "bytes": new.get("transliterated_bytes"),
        })
    return points


def _points_from_periods(periods: list) -> list[dict]:
    """Series from e-bharatisampat's dict-shaped changelog.

    Reads the two fields that Atlas publishes for cross-collection use.  Its
    band counts (`text_only`/`both`/`pdf_only`) are deliberately not summed
    here: what counts as a text there is that Atlas's judgment -- it drops the
    reader endpoint for works whose fetched text holds no Devanagari -- and
    `cumulative_text_count` is where it states the result.
    """
    points = []
    for period in periods:
        texts = period.get("cumulative_text_count")
        if texts is None:
            continue
        points.append({
            "date": period["date"][:10],
            "texts": texts,
            "bytes": period.get("cumulative_iast_bytes_total") or None,
        })
    return points


def read_atlas(spec: dict, root: Path) -> dict:
    """The growth series for one Atlas, or a record carrying `error`."""
    out = {k: spec[k] for k in ("slug", "name")}
    path = root / spec["slug"] / CHANGELOG

    if not path.exists():
        out["error"] = f"no changelog.json at {path}"
        return out

    try:
        data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        out["error"] = f"unreadable: {exc}"
        return out

    if isinstance(data, dict):
        periods = data.get("periods")
        if not isinstance(periods, list):
            out["error"] = "changelog.json has no periods list"
            return out
        points = _points_from_periods(periods)
        out["granularity"] = data.get("granularity") or "year"
        # This Atlas dates its works from an upload stamp, and says how many it
        # could not date. Carried through so the page can explain a series that
        # ends below the Atlas's own total instead of looking short by mistake.
        if data.get("undated_works"):
            out["undated_works"] = data["undated_works"]
    elif isinstance(data, list):
        points = _points_from_entries(data, spec.get("stats_key"))
        out["granularity"] = "month"
    else:
        out["error"] = "changelog.json is neither a list nor an object"
        return out

    if not points:
        out["error"] = "no usable points in changelog.json"
        return out

    points.sort(key=lambda p: p["date"])
    out["points"] = points
    out["final"] = {
        "date": points[-1]["date"],
        "texts": points[-1]["texts"],
        "bytes": points[-1]["bytes"],
    }
    return out


# slug -> how to read it, and how the page should label it. The three read
# differently because the three publish differently; see the module docstring.
ATLASES = (
    {
        "slug": "sanskrit-wikisource-atlas",
        "name": "Sanskrit Wikisource",
        # Corpus-wide, not the `root` subtree the top-level block covers.
        "stats_key": "all",
    },
    {
        "slug": "e-bharatisampat-atlas",
        "name": "E-bhāratīsampat",
    },
    {
        "slug": "sanskrit-documents-atlas",
        "name": "Sanskrit Documents",
        "stats_key": None,
    },
)


def collect(root: Path) -> dict:
    atlases = [read_atlas(spec, root) for spec in ATLASES]
    dated = [a for a in atlases if a.get("points")]
    return {
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "note": "cumulative text counts and IAST bytes from each Atlas's "
                "docs/data/changelog.json; each in its own periodicity",
        "span": {
            "from": min((a["points"][0]["date"] for a in dated), default=None),
            "to": max((a["points"][-1]["date"] for a in dated), default=None),
        },
        "atlases": atlases,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--atlas-root", type=Path, default=ATLAS_ROOT,
                    help=f"where the Atlas repos live (default: {ATLAS_ROOT})")
    ap.add_argument("--out", type=Path,
                    default=Path(__file__).parent / "docs" / "data" / "growth.json",
                    help="where to write growth.json")
    ap.add_argument("--print", action="store_true", dest="show",
                    help="print the series instead of only writing JSON")
    args = ap.parse_args()

    if not args.atlas_root.is_dir():
        sys.exit(f"error: no atlas directory at {args.atlas_root}")

    result = collect(args.atlas_root)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(f"wrote {args.out}")

    failed = [a for a in result["atlases"] if "error" in a]
    if args.show or failed:
        for a in result["atlases"]:
            if "error" in a:
                print(f"  {a['name']:26} {a['error']}")
                continue
            final = a["final"]
            mb = f"{final['bytes'] / 1e6:,.1f} MB" if final["bytes"] else "--"
            print(f"  {a['name']:26} {len(a['points']):>4} points "
                  f"{a['points'][0]['date']} -> {final['date']} "
                  f"({a['granularity']:>5})  "
                  f"ends {final['texts']:>7,} texts, {mb:>12}")

    if failed:
        print(f"warning: {len(failed)} atlas(es) could not be read",
              file=sys.stderr)


if __name__ == "__main__":
    main()
