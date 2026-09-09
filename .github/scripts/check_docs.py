#!/usr/bin/env python3
"""Smoke-test the committed contents of docs/ before a Pages deploy.

docs/ has no build step -- whatever is committed there is what gets served --
so this is the only stage that would notice a truncated or half-written
artifact. It is deliberately shallow: it checks that the files the frontend
fetches exist, parse, and are not empty. It does NOT check that the figures in
them are right.

That shallowness matters more here than in the atlases. This repo's data/ is
*collected from the sibling atlas repos* (collect_atlas_counts.py and friends),
so a stale file here means the hub disagrees with an atlas it links to -- and
nothing in this checkout can detect that, because the atlases are not present.
Catching it needs the collectors rerun against real checkouts, not a runner.

Reads only committed files. No network, no sibling repos, so it runs anywhere
a bare python3 does.
"""

import json
import re
import sys
from pathlib import Path

DOCS = Path(__file__).resolve().parents[2] / "docs"

# The frontend fetches exactly these: counts.js -> counts.json,
# growth.js -> growth.json, search.js -> search.json. A missing one is a
# broken page rather than a degraded one.
#
# Every one is an aggregate over the sibling atlases, so each carries an
# `atlases` key -- an empty one means the collector ran but found nothing,
# which is the failure that would otherwise publish as a blank hub.
REQUIRED_JSON = ("counts.json", "growth.json", "search.json")


def check_json_files(problems):
    for name in REQUIRED_JSON:
        path = DOCS / "data" / name
        if not path.exists():
            problems.append(f"docs/data/{name} is missing")
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            problems.append(f"docs/data/{name} is not valid JSON: {exc}")
            continue
        if not payload:
            problems.append(f"docs/data/{name} is empty")
            continue

        atlases = payload.get("atlases")
        if not atlases:
            problems.append(
                f"docs/data/{name} lists no atlases -- the collector produced an "
                f"empty aggregate")
            continue

        print(f"  ok   {name}: {len(atlases)} atlases "
              f"({path.stat().st_size:,} bytes)")


def check_version(problems):
    """Only __code_version__ here.

    Unlike the atlases, this repo ships no corpus of its own, so it has no
    content or data date to stamp -- the dates belong to the atlases this hub
    aggregates. Requiring them would fail every run.
    """
    path = DOCS / "VERSION"
    if not path.exists():
        problems.append("docs/VERSION is missing")
        return
    found = dict(re.findall(r'^(__\w+__)\s*=\s*"([^"]*)"',
                            path.read_text(encoding="utf-8"), re.MULTILINE))
    if not found.get("__code_version__"):
        problems.append("docs/VERSION is missing __code_version__")
        return
    print(f"  ok   VERSION: {' '.join(f'{k}={v}' for k, v in found.items())}")


def check_pages_present(problems):
    """The hand-written pages, which no data check would cover."""
    for name in ("index.html", "about.html", "search.html"):
        path = DOCS / name
        if not path.exists():
            problems.append(f"docs/{name} is missing")
        elif path.stat().st_size == 0:
            problems.append(f"docs/{name} is empty")
    if not problems:
        print("  ok   index.html, about.html, search.html present")


def main():
    problems = []
    check_json_files(problems)
    check_version(problems)
    check_pages_present(problems)

    if problems:
        print("\ndocs/ failed its pre-publish smoke test:", file=sys.stderr)
        for problem in problems:
            print(f"  FAIL {problem}", file=sys.stderr)
        return 1
    print("\ndocs/ looks publishable")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
