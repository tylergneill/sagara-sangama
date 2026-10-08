"""What each Atlas holds, and which steps would actually do something.

Refreshing an Atlas is rarely a full re-run. A corpus that took five hours to
fetch is usually fine; what goes wrong is downstream -- a truncated file, a
parse that never re-ran after a builder change, a machine that has the caches
but not the built tree. This reports that, so the answer to "do I need to run
this?" is read rather than guessed.

**It only ever reads.** No network, no writes, no imports from any Atlas: this
layer must keep working when an Atlas reorganises its internals, so the checks
are stated here as paths and are allowed to go UNKNOWN rather than wrong.

## What "stale" means, and why it is advisory

A step is stale when its output is older than an input it derives from. That is
mtime, and mtime lies in both directions: touching a file without changing it
reads as stale, and editing a *parser* changes no data file at all yet makes
every downstream output wrong. So a stale mark is a prompt to look, never a
verdict -- and the fix for a false positive is cheap, because every offline
step here runs in seconds.

The expensive steps are judged differently, by COVERAGE rather than age: a
corpus is complete when it holds what the catalogue lists, however old it is.
That is the check that matters for a five-hour walk, and the one that tells you
to copy the cache from another machine instead of re-fetching it.
"""

import argparse
import collections
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ATLAS_ROOT = ROOT.parent / "atlases"

# Colour only when a terminal is listening, so piping this into a file or a
# grep gets plain text.
def _c(code, text):
    return f"\033[{code}m{text}\033[0m" if sys.stdout.isatty() else text


DIM = lambda s: _c("2", s)

# Status words are stored PLAIN and coloured at print time. Colouring them at
# construction put ANSI escapes inside the string, so `len()` counted them and
# every row's padding shifted by the length of its own colour code -- the
# columns fanned out down the page.
STATUS_COLOUR = {"ok": "32", "ok?": "33", "stale": "33",
                 "partial": "33", "missing": "31"}


def newest(path, pattern="*"):
    """Newest mtime under `path`, or None. Directories are walked; a plain
    file answers for itself."""
    if not path.exists():
        return None
    if path.is_file():
        return path.stat().st_mtime
    times = [p.stat().st_mtime for p in path.rglob(pattern) if p.is_file()]
    return max(times) if times else None


def count(path, pattern="*"):
    if not path.exists():
        return 0
    if path.is_file():
        with path.open(encoding="utf-8", errors="replace") as handle:
            return sum(1 for line in handle if line.strip())
    return sum(1 for p in path.rglob(pattern) if p.is_file())


def stamp(mtime):
    if mtime is None:
        return "--"
    import datetime
    return datetime.date.fromtimestamp(mtime).isoformat()


class Report:
    """One Atlas's rows, accumulated then printed together."""

    def __init__(self, name, root):
        self.name, self.root = name, root
        self.rows = []
        self.present = root.exists()

    def artifact(self, label, rel, inputs=(), step=None, pattern="*",
                 covers=None, extra_inputs=()):
        """One derived file: does it exist, and is it older than its inputs?

        `covers` is an optional "what this file actually spans" note -- for a
        changelog, the last month it plots. Worth showing even when the row is
        fresh, because that is the number a reader compares against the chart.

        `inputs` are relative to this report's own root, which is the ordinary
        case: a step reads the caches of the Atlas it belongs to. `extra_inputs`
        are `(name, absolute path)` pairs, for the one derivation that crosses
        a repo boundary -- the parent's files, which read the Atlases' published
        trees and changelogs. They are named explicitly because the basenames
        collide: three `tree.json` in three repos, and "older than tree.json"
        would not say whose.
        """
        path = self.root / rel
        mine = newest(path)
        if mine is None:
            self.rows.append(("missing", label, "--", step or "", ""))
            return
        stale_against = []
        for src in inputs:
            theirs = newest(self.root / src)
            if theirs is not None and theirs > mine:
                stale_against.append(Path(src).name)
        for name, abs_path in extra_inputs:
            theirs = newest(abs_path)
            if theirs is not None and theirs > mine:
                stale_against.append(name)
        if stale_against:
            # Just the reason. `covers` says what the file spans, which matters
            # when the row is otherwise fine -- beside "older than its input"
            # it is the same news twice, and the step to run is identical
            # either way.
            self.rows.append(("stale", label, stamp(mine), step or "",
                              "older than " + ", ".join(stale_against)))
        else:
            self.rows.append(("ok", label, stamp(mine), "", ""))

    def corpus(self, label, rel, listed_rel=None, pattern="*", step=None,
               listed=None, unit="files", floor_note=None, key=None):
        """An acquired cache, judged by COVERAGE rather than age -- see the
        module docstring.

        The target count comes from `listed` (a number, when the Atlas
        publishes one) or `listed_rel` (a file whose lines are the target).
        Prefer `listed` wherever the Atlas states the figure itself: a
        denominator derived here can disagree with the one it publishes, and
        the published one is the honest target. Works known to be unfetchable
        belong OUT of it, named in `floor_note` -- not counted as missing and
        then excused, which is how this row grew a green status trailing a
        clause explaining why it was green.
        """
        path = self.root / rel
        have = (len({k for k in (key(p.name) for p in path.rglob(pattern)
                                 if p.is_file()) if k is not None})
                if key and path.is_dir() else count(path, pattern))
        if not have:
            self.rows.append(("missing", label, "--", step or "",
                              "nothing fetched"))
            return
        want = listed if listed is not None else (
            count(self.root / listed_rel) if listed_rel else None)
        when = stamp(newest(path, pattern))
        if want and have < want * 0.95:
            self.rows.append(("partial", label, when, step or "",
                              f"{have:,} of {want:,} {unit}"))
        elif want and have < want:
            # Short of a target that is supposed to be reachable. `ok?` rather
            # than `ok`: small enough not to be a failed run, but unexplained,
            # and an unexplained gap might be unfinished work. Anything KNOWN
            # to be unfetchable should have been left out of `want`, so it
            # never reaches here.
            note = f"{have:,} of {want:,} {unit}"
            if floor_note:
                note += f" ({floor_note})"
            self.rows.append(("ok?", label, when, "",
                              f"{note}, {want - have:,} short"))
        elif want:
            note = f"{have:,} of {want:,} {unit}"
            if floor_note:
                note += f" ({floor_note})"
            self.rows.append(("ok", label, when, "", note))
        else:
            # No target to measure against, so the count answers no question --
            # "1 file" said nothing "ok" had not already said.
            self.rows.append(("ok", label, when, "", ""))

    def print(self):
        head = f"  {self.name}"
        print(f"\n{_c('1', head)}")
        if not self.present:
            print(f"    {DIM('not on this machine — ' + str(self.root))}")
            return
        if not self.rows:
            print(f"    {DIM('nothing to check')}")
            return
        for status, label, when, step, note in self.rows:
            # Build the line from plain text so every column lines up, then
            # colour only the status word in place.
            shown = _c(STATUS_COLOUR.get(status, "0"), status)
            line = f"    {status:<9}{label:<17}{when:<13}"
            line = line.replace(status, shown, 1)
            tail = note
            if step:
                tail = f"{tail}   → make {step}" if tail else f"→ make {step}"
            print(line + DIM(tail) if tail else line.rstrip())


def dump_month(root):
    """The month of the newest downloaded dump, as `YYYY-MM`, or None.

    Read from the filename (`sawikisource-2026-09-01-p1p165617.xml`) rather
    than the mtime, which is when it was downloaded, not what it covers.
    """
    d = root / "data/dump/1_current_format_live"
    if not d.is_dir():
        return None
    names = sorted(p.name for p in d.glob("sawikisource-*.xml"))
    if not names:
        return None
    parts = names[-1].split("-")
    return f"{parts[1]}-{parts[2]}" if len(parts) > 3 else None


def newest_snapshot(root):
    """The newest materialized monthly snapshot, as `YYYY-MM`, or None."""
    d = root / "data/dump/_backfill_snapshots"
    if not d.is_dir():
        return None
    months = sorted(p.name[5:12] for p in d.glob("tree-*.json.gz"))
    return months[-1] if months else None


def serial_of(name):
    """`6385 - manusmRtiH.txt` -> 6385. The leading integer is the work's
    serial, which is what a distinct-works denominator counts."""
    head = name.split(" - ")[0].removesuffix(".txt")
    return int(head) if head.isdigit() else None


def manual_verdicts(path):
    """`{serial: verdict}` from an Atlas's hand-checked verdicts file.

    Curatorial judgment the audit cannot measure -- whether a work genuinely
    has no text, or has it in a form no fetcher route reaches. Read, never
    restated, so a count here cannot drift from what the Atlas publishes.

    Empty when absent: every work then counts as fetchable, and the row reports
    a shortfall rather than quietly shrinking its own target. A missing
    curation file must never read as a clean bill of health.
    """
    if not path.exists():
        return {}
    try:
        with path.open(encoding="utf-8") as handle:
            data = json.load(handle)
    except (json.JSONDecodeError, OSError):
        return {}
    return {k: v.get("verdict") for k, v in (data.get("verdicts") or {}).items()
            if isinstance(v, dict)}


def text_bearing(path):
    """How many works in a published metadata.json actually have text.

    Returns None when the file is absent or shaped unexpectedly, so the row
    falls back to a plain file count rather than inventing a denominator.
    """
    if not path.exists():
        return None
    try:
        with path.open(encoding="utf-8") as handle:
            works = json.load(handle)
    except (json.JSONDecodeError, OSError):
        return None
    if not isinstance(works, list):
        return None
    return sum(1 for w in works if isinstance(w, dict) and w.get("text"))


def last_period(path):
    """The newest period a changelog plots, as `YYYY-MM`, or None.

    Shared by all three Atlases: they publish different shapes but every one
    keys its periods by an ISO date, so the last one is the last month on the
    chart. Returns None rather than raising on a file we cannot read -- an
    UNKNOWN row is honest, a crash is not.
    """
    if not path.exists():
        return None
    try:
        with path.open(encoding="utf-8") as handle:
            data = json.load(handle)
    except (json.JSONDecodeError, OSError):
        return None
    periods = data.get("periods") if isinstance(data, dict) else data
    if not isinstance(periods, list) or not periods:
        return None
    keys = []
    for entry in periods:
        if not isinstance(entry, dict):
            continue
        for field in ("period", "date", "month", "start"):
            if entry.get(field):
                keys.append(str(entry[field])[:7])
                break
    return max(keys) if keys else None


def wikisource(root):
    r = Report("Sanskrit Wikisource", root)
    if not r.present:
        return r
    # The dump is the only acquisition, and unlike the other two it is a file
    # we are handed rather than a walk we perform.
    #
    # Narrowed to the exact directory `process.py` globs. `data/dump/` also
    # holds backfill snapshots and caches, and pointing at the parent counted
    # those as the dump -- reporting five files present when the actual dump
    # was one, and dating it from whatever the backfill last wrote.
    dump = "data/dump/1_current_format_live"
    r.corpus("dump", dump, pattern="sawikisource-*.xml", step="ws-dump")
    r.artifact("tree.json", "docs/data/tree.json",
               inputs=[dump], step="ws-process")

    # The changelog is NOT a product of `process`, and mtime cannot see the gap
    # that matters. It is built by `regen-changelog` from the monthly snapshots
    # `backfill` materializes -- so it goes stale when a dump arrives for a
    # month no snapshot covers, which is a comparison of MONTHS, not
    # timestamps.
    #
    # Checked this way because the empty-input version of this row reported
    # `ok` against a changelog three weeks older than the dump beside it: with
    # nothing declared to compare against, nothing could ever read as stale.
    have, want = newest_snapshot(root), dump_month(root)
    if want and have and have < want:
        r.rows.append(("stale", "snapshots", have, "ws-backfill",
                       f"newest is {have}, dump covers {want}"))
    elif have:
        r.rows.append(("ok", "snapshots", have, "", ""))
    else:
        r.rows.append(("missing", "snapshots", "--", "ws-backfill", ""))

    # Judged by the last month it PLOTS, for the same reason: the file is
    # rewritten wholesale, so its mtime says when it was built and not what it
    # covers. A changelog rebuilt today from August snapshots is still a
    # changelog that stops in August.
    covered = last_period(root / "docs/data/changelog.json")
    if not covered:
        r.rows.append(("missing", "changelog.json", "--", "ws-changelog", ""))
    elif have and covered < have:
        r.rows.append(("stale", "changelog.json", covered, "ws-changelog",
                       f"snapshots reach {have}"))
    else:
        r.rows.append(("ok", "changelog.json", covered, "", ""))
    return r


def ebharatisampat(root):
    r = Report("E-bhāratīsampat", root)
    if not r.present:
        return r
    r.artifact("catalogue", "data/catalogue.jsonl", step="ebs-fetch-metadata")

    # The denominator is works that HAVE text, not catalogue rows.
    #
    # E-bhāratīsampat catalogues PDF-only scans alongside searchable texts, and
    # `catalogue.jsonl` carries a row per listing appearance -- 13,620 rows over
    # 11,066 distinct items, of which only 5,557 have text at all. Measured
    # against the rows, a complete corpus reported `partial 5,540 of 13,620`
    # and pointed at a ~6.5h refetch that had nothing to fetch: the other 9,421
    # items are scans this fetcher is not for.
    #
    # Read from the Atlas's own published metadata.json, so this figure is the
    # one its About page states rather than a second derivation that could
    # disagree with it.
    # Counted by SERIAL, not by file. The cache holds ~5,540 files over one
    # fewer distinct serial -- a title appears twice -- and counting files
    # against a denominator of distinct works overstates coverage by one, which
    # read as "17 short" beside a genuine shortfall of 18.
    #
    # The denominator is text this pipeline can actually GET, so every work
    # hand-checked as unreachable is subtracted -- the same rule as SD's 25
    # site-404s: a target that can never be reached makes a finished corpus
    # read as unfinished forever.
    #
    # ALL of them, not just the ones with no text at all. An earlier pass kept
    # the two whose text exists only as a machine-generated PDF, on the theory
    # that a future route might reach them. But the question this row asks is
    # "is there work to do", and by that test they are identical to the rest:
    # no route here fetches any of the fifteen. Splitting them produced a green
    # row trailing a clause explaining why it was green, which is a note, not a
    # status. WHY each is unreachable is recorded in the verdicts file and
    # published on the Atlas's own About page, which is where that belongs.
    texts = text_bearing(root / "docs/data/metadata.json")
    verdicts = manual_verdicts(root / "notes" / "manual_verdicts.json")
    # `+ 1` is serial 2736, login-gated. It carries no verdict because it is
    # not an empty text -- it holds 177 KB fetched before it hit the wall -- so
    # the verdicts file, which only ever narrows the empty-text finding, is the
    # wrong place for it.
    unfetchable = len(verdicts) + 1
    r.corpus("fulltext cache", "data/fulltext_cache",
             listed=(texts - unfetchable) if texts else None,
             step="ebs-fetch-text", unit="texts", key=serial_of,
             floor_note=(f"{unfetchable} more listed but not served"
                         if unfetchable else None))
    r.artifact("text sizes", "data/text_sizes.jsonl",
               inputs=["data/fulltext_cache"], step="ebs-count-sizes")
    r.artifact("tree.json", "docs/data/tree.json",
               inputs=["data/text_sizes.jsonl"], step="ebs-build")
    r.artifact("changelog.json", "docs/data/changelog.json",
               inputs=["data/text_sizes.jsonl"], step="ebs-changelog",
               covers=last_period(root / "docs/data/changelog.json"))
    return r


def sanskritdocuments(root):
    r = Report("Sanskrit Documents", root)
    if not r.present:
        return r
    # Tier 1 is cheap to redo and cheaper to rebuild: the catalogue is a pure
    # function of the cached listings, so a truncated one is a local repair.
    r.corpus("listings cache", "data/metadata_cache/listings", pattern="*.html",
             step="sd-fetch-metadata")
    r.artifact("catalogue", "data/catalogue.jsonl",
               inputs=["data/metadata_cache/listings"], step="sd-build-catalogue")
    # The denominator is what the site SERVES, not what it lists.
    #
    # The catalogue lists 9,781 and 25 of those 404 -- the audit's first
    # finding, "listed but not served", published by name on the About page.
    # Fetching can never reach 9,781, so measuring against it calls a complete
    # corpus incomplete and asks for a refetch that cannot succeed. The
    # inventory is the honest target: it is built from pages that came back.
    served = count(root / "data/site_inventory.jsonl") or None
    listed = count(root / "data/catalogue.jsonl")
    unservable = (listed - served) if (served and listed > served) else 0
    r.corpus("fulltext cache", "data/fulltext_cache", listed=served,
             pattern="*.html", step="sd-fetch-text", unit="texts",
             floor_note=(f"{unservable} more listed but not served"
                         if unservable else None))
    r.artifact("inventory", "data/site_inventory.jsonl",
               inputs=["data/fulltext_cache"], step="sd-parse-site")
    r.artifact("listings", "data/site_listings.jsonl",
               inputs=["data/metadata_cache/listings"], step="sd-parse-listings")
    r.artifact("sizes", "data/site_sizes.jsonl",
               inputs=["data/fulltext_cache"], step="sd-count-sizes")
    r.artifact("tree.json", "docs/data/tree.json",
               inputs=["data/site_inventory.jsonl", "data/site_sizes.jsonl",
                       "data/site_listings.jsonl"], step="sd-build")
    r.artifact("changelog.json", "docs/data/changelog.json",
               inputs=["data/site_inventory.jsonl"], step="sd-changelog",
               covers=last_period(root / "docs/data/changelog.json"))
    return r


def jainquantum(root):
    r = Report("Jain Quantum", root)
    if not r.present:
        return r
    r.corpus("API metadata cache", "data/metadata_cache/jainelibrary", pattern="*.json",
             step="(recon pull; fetcher not yet in rivulet)")
    r.corpus("Quantum catalog cache", "data/metadata_cache/jainqq", pattern="*.json",
             step="jq-fetch-catalog")
    r.artifact("catalogue", "data/catalogue.jsonl",
               inputs=["data/metadata_cache/jainqq"], step="jq-parse-catalog")
    # The denominator is the slice chosen for fetching, not every sized row:
    # `make jq-fetch-text` defaults to sanskrit-only, and a complete slice must
    # not read as a 7%-complete corpus.
    r.corpus("fulltext cache", "data/fulltext_cache", pattern="*.json",
             step="jq-fetch-text", unit="items")
    r.artifact("sizes", "data/sizes.jsonl",
               inputs=["data/fulltext_cache"], step="jq-count-sizes")
    r.artifact("tree.json", "docs/data/tree.json",
               inputs=["data/sizes.jsonl", "data/catalogue.jsonl"], step="jq-build")
    r.artifact("changelog.json", "docs/data/changelog.json",
               inputs=["docs/data/tree.json"], step="jq-changelog",
               covers=last_period(root / "docs/data/changelog.json"))
    return r


def gretil(root):
    r = Report("GRETIL", root)
    if not r.present:
        return r
    # Nothing to acquire: the sources are read-only checkouts under GRETIL_ROOT.
    r.artifact("inventory", "data/inventory.jsonl", step="gr-inventory")
    r.artifact("sizes", "data/sizes.jsonl",
               inputs=["data/inventory.jsonl"], step="gr-count-sizes")
    r.artifact("tree.json", "docs/data/tree.json",
               inputs=["data/sizes.jsonl"], step="gr-build")
    r.artifact("changelog.json", "docs/data/changelog.json",
               inputs=["docs/data/tree.json"], step="gr-changelog",
               covers=last_period(root / "docs/data/changelog.json"))
    return r


ATLASES = [
    ("sanskrit-wikisource-atlas", wikisource),
    ("e-bharatisampat-atlas", ebharatisampat),
    ("sanskrit-documents-atlas", sanskritdocuments),
    ("jain-quantum-atlas", jainquantum),
    ("gretil-atlas", gretil),
]


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--atlas-root", type=Path, default=ATLAS_ROOT)
    args = parser.parse_args()

    reports = [fn(args.atlas_root / name) for name, fn in ATLASES]
    for r in reports:
        r.print()

    # The parent's own outputs are last, because they are downstream of every
    # Atlas and there is no point reporting them as fresh when a tree they read
    # has not been built.
    parent = Report("Sāgarasaṅgama (here)", ROOT)
    # Named inputs, because these three are the only rows whose sources live in
    # ANOTHER repo. Declared with no inputs at all they could never read as
    # stale -- the same empty-comparison bug the Wikisource changelog row was
    # built to avoid -- so all three sat green while the Atlas trees they
    # aggregate were rebuilt days later.
    #
    # counts and search read every Atlas's tree.json; growth reads every
    # changelog.json. The slugs come from ATLASES above, so an Atlas added
    # there is picked up here without a second list to keep in step.
    slugs = [name for name, _ in ATLASES]
    trees = [(f"{slug.removesuffix('-atlas')} tree.json",
              args.atlas_root / slug / "docs/data/tree.json")
             for slug in slugs]
    changelogs = [(f"{slug.removesuffix('-atlas')} changelog.json",
                   args.atlas_root / slug / "docs/data/changelog.json")
                  for slug in slugs]
    for label, rel, sources in (
            ("counts.json", "docs/data/counts.json", trees),
            ("growth.json", "docs/data/growth.json", changelogs),
            ("search.json", "docs/data/search.json", trees)):
        parent.artifact(label, rel, step="data", extra_inputs=sources)
    parent.print()

    # `reports + [parent]`, not `reports`: the parent's rows could not be
    # flagged before, so the one Atlas that is always downstream of the others
    # printed a stale row with no advisory under it.
    flagged = [row for r in reports + [parent] for row in r.rows
               if row[0] not in ("ok", "ok?")]
    print()
    if flagged:
        print(DIM("  Marks are advisory: mtime cannot see a parser change, and a"))
        print(DIM("  touched file reads as stale. Offline steps cost seconds --"))
        print(DIM("  re-run rather than agonise. A partial corpus is the one to"))
        print(DIM("  think about: copying it from another machine beats a refetch."))
        print()


if __name__ == "__main__":
    main()
