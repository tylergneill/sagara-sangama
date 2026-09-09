# notes/

**The shape here is the same in all five repos** — this Atlas cluster's
convention, not a local one.

    notes/*.md        non-trivial notes on structure
    notes/<topic>/    folders of research material
    notes/scratch/    tasks in flight

## The lifecycle

**A new task is written into `scratch/`.** That is where a plan, a scoped
design, a measurement in progress, or a running investigation lives while it is
live.

**When the task finishes, one of two things happens to its file:**

- an insight worth keeping is **promoted** — rewritten into a top-level note
  about the structure it explains, or into a code comment beside the thing it
  explains, and
- the scratch file is **deleted**.

Nothing is kept because it was expensive to write. A finished task whose
conclusion is already in the code leaves no file behind.

## What top-level notes are for

Structure, not history. A top-level note answers "why is it built this way" or
"what will bite me here" — the two traps in `changelog-axes.md` are the shape
to aim at. It is **not** a record of how a decision was reached, what was tried
first, or what the state of play was on some date. That is churn, and it is
what `scratch/` absorbs and then loses.

Keep them short. A long top-level note usually means a task's history was never
cut out of it.

## Research folders

A subfolder holds the material behind a note — sample data, one-off analysis
scripts, measurements kept as evidence. It carries its own README saying what
each file is and which note it supports. This material is not maintained and is
not meant to be re-run routinely; it exists so a figure can be re-derived
rather than re-guessed.

## `githistory/`

Gitignored: a `git bundle` of this repo's history plus a plain-text digest,
kept locally as a backup.
