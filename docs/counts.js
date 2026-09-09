/* Fill the Atlas counts from data/counts.json, written by
   `make counts` (collect_atlas_counts.py).

   The JSON is the only source: the cells ship empty and every figure on both
   pages comes from here. There is deliberately no hardcoded copy to fall back
   on -- a second set of numbers in the markup would be a second thing to keep
   correct, and its failure mode is the bad one, showing a stale figure that
   looks authoritative. If the fetch fails the numbers are absent and say so,
   which is honest and obvious. */

const nf = new Intl.NumberFormat("en-US");
const nf1 = new Intl.NumberFormat("en-US", { minimumFractionDigits: 1,
                                             maximumFractionDigits: 1 });

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

/* "2026-08-17T22:55:00+00:00" -> "Aug 2026".

   The Atlases report a full timestamp and that precision is worth keeping in
   the data, but a day-level date overstates how current the figures are: a
   tree rebuilt on the 17th is not meaningfully fresher than one from the 15th.
   The month is the honest granularity.

   Read off the string rather than parsed with `new Date()`, on purpose. The
   timestamps carry a UTC offset, so parsing to a local Date can move the month
   across the boundary -- 2026-08-01T00:30:00+00:00 is July 31st in New York,
   and would print "Jul 2026" for a build everyone involved calls August.
   Returns "" on anything unparseable, so a malformed date shows nothing
   rather than "NaN". */
function monthYear(iso) {
  const m = /^(\d{4})-(\d{2})/.exec(iso || "");
  if (!m) return "";
  const month = MONTHS[Number(m[2]) - 1];
  return month ? `${month} ${m[1]}` : "";
}

/* The About page's at-a-glance table, when present. An absent figure is shown
   as an em dash rather than a zero: the Atlases that do not report bytes or
   PDFs have not measured them, which is a different claim from "none". */
function fillTable(data) {
  for (const atlas of data.atlases || []) {
    const row = document.querySelector(`tr[data-slug="${atlas.slug}"]`);
    if (!row) continue;

    const put = (sel, value, fmt) => {
      const cell = row.querySelector(sel);
      if (!cell) return;
      const known = typeof value === "number" && value > 0;
      cell.textContent = known ? fmt(value) : "—";
      cell.classList.toggle("none", !known);
    };

    put(".t-texts", atlas.texts, (v) => nf.format(v));
    put(".t-mb", atlas.iast_bytes, (v) => nf1.format(v / 1e6));
    put(".t-avg", atlas.avg_iast_bytes, (v) => nf1.format(v / 1e3));
    put(".t-pdf", atlas.pdfs, (v) => nf.format(v));

    /* The PDF footnote is about how Sanskrit Documents links scans -- loosely,
       and mostly off-site -- so the mark goes on that figure rather than on
       the column head, where it would read as a caveat about all three. Added
       after `put`, which writes textContent and would drop a child node. */
    if (atlas.slug === "sanskrit-documents-atlas") {
      const cell = row.querySelector(".t-pdf");
      if (cell && !cell.classList.contains("none")) {
        const mark = document.createElement("span");
        mark.className = "t-mark";
        mark.textContent = "*";
        cell.appendChild(mark);
      }
    }
  }
}

fetch("./data/counts.json")
  .then((r) => (r.ok ? r.json() : Promise.reject(new Error(r.status))))
  .then((data) => {
    for (const atlas of data.atlases || []) {
      // .atlas scopes this to the home page's fanned blocks; the About table's
      // rows carry the same data-slug and are filled by fillTable instead.
      const box = document.querySelector(`.atlas[data-slug="${atlas.slug}"]`);
      if (!box) continue;
      const countEl = box.querySelector(".atlas-count");
      if (countEl) {
        countEl.textContent = "";
        if (typeof atlas.texts === "number") {
          // "3,805 texts (811.7 MB)", with both figures emphasised against the
          // muted units, matching how the total below the logo reads. Built as
          // nodes rather than innerHTML -- no markup assembled from data.
          const n = document.createElement("strong");
          n.textContent = nf.format(atlas.texts);
          countEl.append(n, ` ${atlas.noun || "texts"}`);

          if (atlas.iast_bytes) {
            const mb = document.createElement("strong");
            mb.textContent = nf1.format(atlas.iast_bytes / 1e6);
            countEl.append(" (", mb, " MB)");
          }
        } else {
          // An Atlas that could not be read: say so rather than showing a stale
          // number as if it were current.
          countEl.textContent = "count unavailable";
        }
      }

      // Per-atlas snapshot date, blank where the Atlas reports none -- a date
      // is a claim about currency, and a wrong one is worse than none.
      const dateEl = box.querySelector(".atlas-date");
      if (dateEl) {
        const when = monthYear(atlas.tree_mtime);
        dateEl.textContent = when ? `as of ${when}` : "";
      }
    }

    if (typeof data.total_texts === "number" && data.total_texts > 0) {
      const total = document.getElementById("totalTexts");
      if (total) total.textContent = nf.format(data.total_texts);
    }

    fillTable(data);

    /* The About page's colophon date. `generated` is when `make data` last
       rewrote these aggregates, which is this project's only meaningful data
       date -- it sources no collection of its own. Rounded to the month by the
       same rule as the per-Atlas dates above, and left blank when absent. */
    const built = document.getElementById("dataDate");
    if (built) {
      const when = monthYear(data.generated);
      built.textContent = when ? `aggregate data last built: ${when}` : "";
    }

  })
  .catch((err) => {
    // Nothing to fall back on by design, so say the figures are missing
    // rather than leaving silent blanks that look like a layout bug.
    console.error("counts.json could not be read:", err);
    for (const el of document.querySelectorAll(".atlas-count")) {
      el.textContent = "count unavailable";
    }
    for (const el of document.querySelectorAll("td.num")) {
      el.textContent = "—";
      el.classList.add("none");
    }
  });
