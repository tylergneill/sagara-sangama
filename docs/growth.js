/* The About page's growth chart, drawn from data/growth.json (written by
   `make growth`, collect_atlas_growth.py).

   Three cumulative series on one time axis: how each collection accumulated.
   Like counts.js, the JSON is the only source -- nothing is hardcoded here,
   and a fetch that fails says so rather than drawing an empty box.

   One y-axis, never two. The `texts` and `MB` measures have no principled
   shared scale, so they are a toggle rather than two axes on one plot: a
   dual-axis chart makes the crossing point an artifact of where you put the
   scales, and the reader cannot tell that from signal.

   Months in, quarters or years out. All three Atlases publish monthly and
   stamp a month at its start; the grouping happens here, at render time, the
   same split each Atlas's own About page uses. */

const G_URL = "./data/growth.json";
const SVG_NS = "http://www.w3.org/2000/svg";

/* Slots 1-3 of the documented categorical palette, in fixed order, one per
   Atlas -- identity, so the colour follows the collection and never its rank.
   All three modes validated against this page's surfaces (#ffffff light,
   #0b0d10 dark, #071a2b wave): lightness band, chroma floor, CVD separation
   (worst adjacent pair dE 9.2 deutan light / 9.4 dark / 28.8 protan wave),
   and the normal-vision floor (27.6 / 26.5 / 74.7) all pass. Light-mode aqua
   sits at 2.82:1 against white, just under the 3:1 mark bar, which is why the
   chart ships a legend, direct end labels and a table view rather than leaving
   colour to carry identity alone.

   Wave gets its own set rather than borrowing dark's: the surface is a deep
   blue, not a neutral near-black, and dark's blue series would sit too close
   to its own ground. These are lifted a step in lightness, and all three clear
   7:1 there. */
const SERIES = [
  { slug: "sanskrit-wikisource-atlas", light: "#2a78d6", dark: "#3987e5", wave: "#5aa9f0" },
  { slug: "e-bharatisampat-atlas",     light: "#eb6834", dark: "#d95926", wave: "#f08a4b" },
  { slug: "sanskrit-documents-atlas",  light: "#1baf7a", dark: "#199e70", wave: "#38c793" },
  { slug: "jain-quantum-atlas",        light: "#8e5bd6", dark: "#9b6ee0", wave: "#b48cf0" },
  { slug: "gretil-atlas",              light: "#c9a227", dark: "#d4ad2f", wave: "#e6c24d" },
];

const state = { metric: "texts", granularity: 12, mode: "cumulative",
                // Slugs the reader has switched off, and which collection the
                // x axis starts at ("" = all of them).
                hidden: new Set(), from: "" };

const gnf = new Intl.NumberFormat("en-US");
const gnf1 = new Intl.NumberFormat("en-US", { minimumFractionDigits: 1,
                                              maximumFractionDigits: 1 });

function colorOf(spec) {
  // Anything unrecognised falls back to light, which is the base :root
  // palette -- the surface such a page would actually be painting on.
  const theme = document.documentElement.getAttribute("data-theme");
  return spec[theme] || spec.light;
}

function el(tag, attrs, text) {
  const node = document.createElementNS(SVG_NS, tag);
  for (const [k, v] of Object.entries(attrs || {})) node.setAttribute(k, v);
  if (text != null) node.textContent = text;
  return node;
}

/* "2026-08-01" -> months since 1970, the x coordinate. Read off the string
   rather than parsed with `new Date()`: the dates carry no zone, so parsing
   would land them in local time and shift a January point into December for
   anyone west of UTC. Same reasoning as counts.js's monthYear. */
function monthIndex(iso) {
  const m = /^(\d{4})-(\d{2})/.exec(iso);
  return m ? Number(m[1]) * 12 + (Number(m[2]) - 1) : null;
}

function fmtMonth(index) {
  const year = Math.floor(index / 12);
  const month = index % 12;
  return state.granularity >= 12 ? String(year)
       : `${year}-${String(month + 1).padStart(2, "0")}`;
}

function metricOf(point) {
  return state.metric === "bytes" ? point.bytes : point.texts;
}

function fmtMetric(v) {
  if (v == null) return "—";
  return state.metric === "bytes" ? `${gnf1.format(v / 1e6)} MB`
                                  : gnf.format(v);
}

/* Thin the monthly points to one per calendar quarter or year, keeping the
   LAST point in each bucket.

   These are cumulative series, so a bucket's value is the running total as of
   its end -- taking the last point is the whole reduction, and summing would
   be meaningless. Anchored to the calendar (quarters at Jan/Apr/Jul/Oct), so
   a point labelled 2026 is 2026; the newest bucket may be partial, which is
   honest where the period is still in progress.

   The series' own first point is always kept, whatever bucket it falls in.
   Otherwise a collection that starts mid-year is drawn from its year-END
   total -- e-bharatisampat opens at 37 texts in January 2021 and closes that
   year at 1737, and thinning to the bucket alone would erase the opening and
   make the line appear to begin already part-grown. */
function group(points, size) {
  if (size <= 1) return points;
  const out = [];
  let key = null;
  for (const p of points) {
    const idx = monthIndex(p.date);
    if (idx == null) continue;
    const k = `${Math.floor(idx / 12)}:${Math.floor((idx % 12) / size)}`;
    // `out.length > 1` protects the opening point from being superseded by
    // later months of the same bucket; every other bucket keeps its last.
    if (k === key && out.length > 1) out[out.length - 1] = p;
    else if (k === key) out.push(p);
    else { out.push(p); key = k; }
  }
  return out;
}

/* Sanskrit Wikisource counts two ways, and its changelog flips between them.

   `text_count` depends on what the site has materialized, and for nine months
   across 2014-2015 the upstream snapshots report an inflated figure -- the
   series steps up by 393 in 2014-07, holds, falls back in 2015-01, steps up
   again by 457, and falls back for good in 2015-05. The offsets are the same
   quantity counted twice; the surrounding months are the true track, which is
   why the series resumes from the lower level and stays there.

   Each run is pulled back down by the step that opened it, which lands it on
   the level the months on either side agree about. Nothing after the last run
   moves, so the collection's present-day total still matches the counts table
   above -- the correction is local to the affected stretch.

   Named explicitly rather than detected by shape. A threshold that caught
   these would be a standing rule about what counts as an implausible month
   for every collection, and this is one upstream's known bookkeeping quirk,
   not a law about collections. Each run is applied only if its opening step
   is still there, so the patch retires itself if the changelog is ever
   regenerated with the flip resolved. */
const WS_RUNS = [
  { slug: "sanskrit-wikisource-atlas", from: "2014-07", to: "2014-12", step: 393 },
  { slug: "sanskrit-wikisource-atlas", from: "2015-02", to: "2015-04", step: 457 },
];

/* Which series carry a footnote, read off the mending table rather than named
   again here -- the asterisk exists to point at that note, so the two cannot
   drift apart. */
function isMended(slug) {
  return WS_RUNS.some((r) => r.slug === slug);
}

function mend(slug, points) {
  let out = points;
  for (const run of WS_RUNS) {
    if (run.slug !== slug) continue;
    const i = out.findIndex((p) => p.date.startsWith(run.from));
    if (i < 1) continue;
    // The run is only spurious while the step that opened it is present.
    if (out[i].texts - out[i - 1].texts !== run.step) continue;
    out = out.map((p) => {
      const m = p.date.slice(0, 7);
      if (m < run.from || m > run.to) return p;
      return { ...p, texts: p.texts - run.step };
    });
  }
  return out;
}

/* Cumulative running totals -> what arrived in each period, by differencing
   consecutive points. The source publishes only running totals, so the period
   view is derived here rather than read off the JSON.

   The first point is dropped, not kept at its own value: a running total's
   opening figure is everything accumulated up to that date, which for a
   collection that was already part-grown when the series begins is a spike
   belonging to no period the axis shows. Differencing needs a predecessor,
   and the first point has none.

   Clamped at zero. What is left after `mend` is the ordinary case of a
   collection deleting or merging a few pages -- Wikisource's largest is 31
   texts in 2020-05, against monthly gains in the hundreds. At that size a
   negative reads as noise around the axis rather than as information, and
   costs the y-scale a band of empty plot below zero to draw it in. The
   cumulative view still shows every one of these as a dip in the line. */
function diff(points) {
  const out = [];
  for (let i = 1; i < points.length; i++) {
    const prev = points[i - 1].y, cur = points[i].y;
    if (prev == null || cur == null) continue;
    out.push({ ...points[i], y: Math.max(0, cur - prev) });
  }
  return out;
}

/* A round number at or above `n`, plus the step between gridlines. The top
   tick is a labelled round figure rather than the raw maximum, so the tallest
   line ends at a number the axis actually prints. */
function niceScale(n) {
  if (!(n > 0)) return { top: 1, step: 1 };
  const pow = Math.pow(10, Math.floor(Math.log10(n)));
  for (const mult of [0.1, 0.2, 0.25, 0.5, 1, 2, 2.5, 5]) {
    const step = mult * pow;
    const top = Math.ceil(n / step) * step;
    if (top / step <= 8) return { top, step };
  }
  return { top: Math.ceil(n / pow) * pow, step: pow };
}

// The right margin is the end labels' gutter, sized to the longest name at
// .g-end-label's weight ("Sanskrit Wikisource", ~133 units) plus its 8-unit
// offset from the line. Set it short and the labels run off the viewBox.
const PAD = { top: 16, right: 148, bottom: 30, left: 56 };
const H = 300;

function draw(data, host) {
  // Monthly, mended, in date order -- the state every later step works from.
  const raw = new Map();
  for (const spec of SERIES) {
    const atlas = (data.atlases || []).find((a) => a.slug === spec.slug);
    if (!atlas || !atlas.points) continue;
    raw.set(spec.slug, { name: atlas.name, points: mend(spec.slug, atlas.points) });
  }

  /* Every line runs to the newest month any collection reports. A series that
     stops early has not vanished -- GRETIL closed in 2020 and still holds what
     it held -- so its last total is carried forward month by month rather than
     the line being left to end mid-plot, which reads as the collection ending
     while a neighbour that merely went flat appears to carry on. Monthly, and
     before grouping, so the period view draws those months as zeros instead of
     one long slope down to the edge. Measured over every series, hidden or
     not, so switching one off never moves another's end. */
  const newest = Math.max(...[...raw.values()]
    .map((e) => monthIndex(e.points[e.points.length - 1].date)));
  for (const entry of raw.values()) {
    const last = entry.points[entry.points.length - 1];
    const padded = [...entry.points];
    for (let m = monthIndex(last.date) + 1; m <= newest; m++) {
      const date = `${Math.floor(m / 12)}-${String(m % 12 + 1).padStart(2, "0")}-01`;
      padded.push({ ...last, date });
    }
    entry.points = padded;
  }

  /* Where the axis starts, in months. Read off the monthly data, and applied
     before grouping: `group` buckets from whatever point it is handed first,
     so clipping afterwards would leave each series bucketed on its own start
     and the handles standing at different dates -- at year granularity, up to
     a year apart. Clipping first puts every series on one grid. */
  const anchor = state.from && raw.has(state.from)
    ? monthIndex(raw.get(state.from).points[0].date) : -Infinity;

  // Every series that has data, hidden or not: the legend lists them all, so a
  // switched-off collection keeps a key to switch back on.
  const all = [];
  for (const spec of SERIES) {
    const entry = raw.get(spec.slug);
    if (!entry) continue;
    const clipped = entry.points.filter((p) => monthIndex(p.date) >= anchor);
    const points = group(clipped, state.granularity)
      .map((p) => ({ x: monthIndex(p.date), y: metricOf(p), date: p.date }))
      .filter((p) => p.x != null && p.y != null);
    const shaped = state.mode === "added" ? diff(points) : points;
    if (shaped.length) all.push({ ...spec, name: entry.name, points: shaped });
  }

  const series = all.filter((s) => !state.hidden.has(s.slug));

  host.innerHTML = "";
  if (!series.length) {
    // Reachable by switching metric (a collection may have no byte series),
    // not by the labels -- those stop at one. Zero drawn means the next label
    // click can only be a "show", which visibleCount() > 1 already allows.
    lastShown = 0;
    host.textContent = all.length ? "No collection selected."
      : state.metric === "bytes" ? "No Atlas publishes a byte series yet."
      : "Growth data unavailable.";
    return all;
  }

  const xs = series.flatMap((s) => s.points.map((p) => p.x));
  const ys = series.flatMap((s) => s.points.map((p) => p.y));
  const xMin = Math.min(...xs), xMax = Math.max(...xs);
  const { top: yTop, step } = niceScale(Math.max(...ys));

  // viewBox units, scaled by CSS to the container -- so the chart is
  // responsive without recomputing on resize.
  const W = 720;
  const plotW = W - PAD.left - PAD.right;
  const plotH = H - PAD.top - PAD.bottom;
  const sx = (x) => PAD.left + (xMax === xMin ? 0 : (x - xMin) / (xMax - xMin) * plotW);
  const sy = (y) => PAD.top + plotH - (y / yTop) * plotH;

  const svg = el("svg", {
    viewBox: `0 0 ${W} ${H}`,
    class: "g-svg",
    role: "img",
    "aria-label": `${state.mode === "added" ? "Added per period" : "Cumulative"} `
      + `${state.metric === "bytes" ? "size in megabytes" : "text count"} `
      + `for three collections, ${fmtMonth(xMin)} to ${fmtMonth(xMax)}`,
  });

  // Gridlines and their labels come off one tick list, so a label can never
  // drift from the line it names.
  for (let v = 0; v <= yTop + 1e-9; v += step) {
    const y = sy(v);
    svg.appendChild(el("line", { x1: PAD.left, y1: y, x2: W - PAD.right, y2: y,
                                 class: "g-grid" }));
    svg.appendChild(el("text", { x: PAD.left - 8, y: y + 4, class: "g-axis-label",
                                 "text-anchor": "end" },
      state.metric === "bytes" ? gnf.format(Math.round(v / 1e6))
                               : gnf.format(Math.round(v))));
  }

  // x labels: about six, evenly spaced over the real range.
  const xTicks = Math.min(6, xMax - xMin + 1);
  for (let i = 0; i < xTicks; i++) {
    const x = xMin + Math.round((i / Math.max(1, xTicks - 1)) * (xMax - xMin));
    svg.appendChild(el("text", { x: sx(x), y: H - 10, class: "g-axis-label",
                                 "text-anchor": "middle" },
      String(Math.floor(x / 12))));
  }

  for (const s of series) {
    const d = s.points.map((p, i) => `${i ? "L" : "M"}${sx(p.x).toFixed(1)},${sy(p.y).toFixed(1)}`).join("");
    svg.appendChild(el("path", { d, fill: "none", stroke: colorOf(s),
                                 "stroke-width": 2, "stroke-linejoin": "round",
                                 "stroke-linecap": "round" }));
  }

  /* A grab handle on each line's first point: click it and the axis starts
     where that collection does, click again for the whole span. The control
     sits on the thing it acts on -- the leftmost point IS where the series
     begins -- so it needs no label of its own, and the toolbar keeps one row.

     The pointer claims the NEAREST handle within GRAB rather than each handle
     owning a fixed disc. Discs stop scaling once they are wide enough to
     touch -- two overlapping ones fight over the pointer and the later-drawn
     wins, which is a worse failure than a small target. Nearest-wins has no
     such ceiling: the radius can be as generous as it likes, and the boundary
     between two handles simply falls halfway between them. Handled on the svg
     in `attachHover`, which is already tracking the pointer. */
  const handles = series.map((s) => ({
    slug: s.slug, name: s.name,
    cx: sx(s.points[0].x), cy: sy(s.points[0].y),
    on: state.from === s.slug,
  }));
  for (const h of handles) {
    const color = colorOf(series.find((s) => s.slug === h.slug));

    /* The halo says "this one is armed" from across the plot. It is what the
       snap radius needed and did not have: a 4px ring growing to 7px is a
       change you have to be looking at the handle to notice, while a wide
       soft disc blooming under the pointer is visible in peripheral vision,
       which is where the reader's attention actually is while moving toward
       it. Drawn before the ring so it sits behind, and it carries the series
       colour so the feedback also says WHICH line is about to be picked. */
    const halo = el("circle", { cx: h.cx, cy: h.cy, r: 5, class: "g-start-halo" });
    halo.style.fill = color;
    h.halo = halo;
    svg.appendChild(halo);

    // Anchored reads as a filled mark, at rest as a hollow one. The fill goes
    // on via style rather than as an attribute: .g-start sets fill in the
    // stylesheet, and a presentation attribute would lose to it.
    const ring = el("circle", { cx: h.cx, cy: h.cy, r: h.on ? 5 : 4,
                                class: "g-start", stroke: color });
    if (h.on) ring.style.fill = color;
    ring.appendChild(el("title", {}, h.on
      ? `Showing from ${h.name} — click for the full span`
      : `Start the axis at ${h.name}`));
    h.ring = ring;
    svg.appendChild(ring);
  }

  /* Direct labels at the line ends -- identity where the reader is already
     looking, and the relief the light-mode contrast WARN asks for. They are
     also the series switch: clicking a name drops its line, and a dropped
     series keeps a dimmed label parked at the right edge so there is always
     something to click to bring it back. That parked stub is why the chart
     can carry the toggle without a legend under it repeating all three names.

     In the period view the three lines all end near zero, so the labels land
     on top of each other. They are placed in one pass instead: sorted by where
     their line actually ends, then pushed down only as far as needed to keep
     LEAD between them, and the whole stack shifted back up if it overruns the
     plot. A label may end up a few pixels off its line, which is the lesser
     evil against three names printed over each other -- and each still carries
     its series colour. */
  // Tracks .g-end-label's font-size: the lead has to clear the glyphs, and a
  // stack set tighter than its own type is what makes three converging series
  // unreadable in the period view.
  const LEAD = 15;
  const labelX = W - PAD.right + 8;
  const ends = series
    .map((s) => ({ s, y: sy(s.points[s.points.length - 1].y),
                   x: sx(s.points[s.points.length - 1].x) }))
    .sort((a, b) => a.y - b.y);

  // Hidden series park below the visible ones, in the order they are declared,
  // so a label does not jump around as collections are switched on and off.
  const lastVisible = ends.length ? ends[ends.length - 1].y : PAD.top;
  const parked = all.filter((s) => state.hidden.has(s.slug))
    .map((s, i) => ({ s, x: labelX, y: lastVisible + LEAD * (i + 1), off: true }));
  const stack = [...ends, ...parked];
  for (let i = 1; i < stack.length; i++) {
    stack[i].y = Math.max(stack[i].y, stack[i - 1].y + LEAD);
  }
  const overrun = stack.length
    ? stack[stack.length - 1].y - (PAD.top + plotH) : 0;
  if (overrun > 0) for (const e of stack) e.y -= overrun;

  lastShown = ends.length;
  for (const e of stack) {
    const label = el("text", { x: e.x + 8, y: e.y + 4,
                               class: e.off ? "g-end-label g-end-off" : "g-end-label",
                               fill: colorOf(e.s), "data-slug": e.s.slug },
      isMended(e.s.slug) ? `${e.s.name}*` : e.s.name);
    label.appendChild(el("title", {}, e.off
      ? `Show ${e.s.name}` : `Hide ${e.s.name}`));
    svg.appendChild(label);
  }

  host.appendChild(svg);
  attachHover(svg, series, { sx, sy, xMin, xMax, plotW, W }, handles);
  return all;
}

/* Crosshair and tooltip. An SVG chart in a browser is interactive by default
   expectation, and with three lines converging the tooltip is what makes a
   particular month readable at all. */
function attachHover(svg, series, geom, handles) {
  const line = el("line", { class: "g-crosshair", y1: PAD.top,
                            y2: H - PAD.bottom, visibility: "hidden" });
  svg.appendChild(line);
  const dots = series.map((s) => {
    const c = el("circle", { r: 4, fill: colorOf(s), class: "g-dot",
                             visibility: "hidden" });
    svg.appendChild(c);
    return c;
  });

  const tip = document.createElement("div");
  tip.className = "g-tip";
  tip.hidden = true;
  svg.parentElement.appendChild(tip);

  const hide = () => {
    line.setAttribute("visibility", "hidden");
    for (const d of dots) d.setAttribute("visibility", "hidden");
    tip.hidden = true;
  };

  /* Nearest-handle snapping. GRAB is in viewBox units and generous on
     purpose; whichever handle is closest inside it takes the pointer, so the
     radius can grow without two of them ever contesting the same pixel. The
     svg reports which one is armed by pointer position alone -- no hit shapes
     in the DOM, and so nothing for the crosshair or the lines to fight with.

     `nearest` is read by the click listener in the fetch block, which is why
     it hangs off the svg rather than staying local. */
  const GRAB = 36;
  let armed = null;
  const arm = (h) => {
    if (armed === h) return;
    if (armed) {
      armed.ring.classList.remove("g-start-near");
      armed.halo.classList.remove("g-start-halo-on");
    }
    armed = h;
    if (armed) {
      armed.ring.classList.add("g-start-near");
      armed.halo.classList.add("g-start-halo-on");
    }
    svg.nearestHandle = armed;
    svg.style.cursor = armed ? "pointer" : "";
  };

  svg.addEventListener("pointerleave", () => { arm(null); hide(); });
  svg.addEventListener("pointermove", (ev) => {
    const box = svg.getBoundingClientRect();
    // Client px -> viewBox units, so the maths is in the same space as the
    // drawing regardless of how CSS has scaled the svg.
    const vx = (ev.clientX - box.left) / box.width * geom.W;
    const vy = (ev.clientY - box.top) / box.height * H;

    // Arm the closest handle within GRAB. Distance is measured in viewBox
    // units on both axes, so the radius is a true circle on screen only where
    // the svg keeps its aspect ratio -- which it does, being width-scaled.
    let near = null, best = GRAB;
    for (const h of handles || []) {
      const d = Math.hypot(h.cx - vx, h.cy - vy);
      if (d < best) { best = d; near = h; }
    }
    arm(near);

    if (vx < PAD.left || vx > geom.W - PAD.right) return hide();
    const frac = (vx - PAD.left) / geom.plotW;
    const target = geom.xMin + frac * (geom.xMax - geom.xMin);

    // Snap to the nearest x that any series actually has a point at, and read
    // every series at THAT x rather than each at its own nearest. Otherwise
    // the three dots scatter across different months and the crosshair sits
    // at a fourth, so the tooltip's heading names a date none of them are on.
    let at = null;
    for (const s of series) {
      for (const p of s.points) {
        if (at === null || Math.abs(p.x - target) < Math.abs(at - target)) at = p.x;
      }
    }
    if (at === null) return hide();

    // How far from `at` a point may sit and still be read as "at" it. One
    // grouping step, so a series sampled on the same grid always answers and
    // one that has not started yet never does.
    const tol = Math.max(1, state.granularity) / 2;

    const rows = [];
    series.forEach((s, i) => {
      let best = null;
      for (const p of s.points) {
        if (best === null || Math.abs(p.x - at) < Math.abs(best.x - at)) best = p;
      }
      // Only mark a series where it actually has a point here -- Sanskrit
      // Wikisource starts in 2012 and e-bharatisampat in 2021, and a dot
      // pinned to a line's first point across a decade of empty axis would
      // claim data that does not exist.
      if (best && Math.abs(best.x - at) <= tol) {
        dots[i].setAttribute("cx", geom.sx(best.x));
        dots[i].setAttribute("cy", geom.sy(best.y));
        dots[i].setAttribute("visibility", "visible");
        rows.push(`<span class="g-tip-key" style="background:${colorOf(s)}"></span>`
          + `${s.name}: <strong>${fmtMetric(best.y)}</strong>`);
      } else {
        dots[i].setAttribute("visibility", "hidden");
      }
    });

    if (!rows.length) return hide();
    const shown = at;
    line.setAttribute("x1", geom.sx(shown));
    line.setAttribute("x2", geom.sx(shown));
    line.setAttribute("visibility", "visible");
    tip.innerHTML = `<div class="g-tip-when">${fmtMonth(shown)}</div>` + rows.join("<br>");
    tip.hidden = false;
    // Flip the tooltip to the cursor's left near the right edge, so it never
    // hangs off the chart.
    const localX = ev.clientX - box.left;
    tip.style.left = `${localX > box.width * 0.6 ? localX - tip.offsetWidth - 12 : localX + 12}px`;
    tip.style.top = `${ev.clientY - box.top + 12}px`;
  });
}

/* How many series are currently drawn. Read off the last render rather than
   recomputed: whether a collection has a line at all depends on the metric (a
   byte series may be missing) and on the granularity, which draw() has already
   worked out. */
let lastShown = 0;
function visibleCount() {
  return lastShown;
}

function render(data) {
  const host = document.getElementById("growthChart");
  if (!host) return;
  draw(data, host);
  for (const btn of document.querySelectorAll("#growthControls button")) {
    // String on both sides: granularity is a number in state, a string in the
    // DOM, and === across the two would never match.
    const on = String(state[btn.dataset.axis]) === btn.dataset.value;
    btn.classList.toggle("g-on", on);
    btn.setAttribute("aria-pressed", String(on));
  }
}

fetch(G_URL)
  .then((r) => (r.ok ? r.json() : Promise.reject(new Error(r.status))))
  .then((data) => {
    render(data);

    const controls = document.getElementById("growthControls");
    if (controls) {
      controls.addEventListener("click", (ev) => {
        const btn = ev.target.closest("button[data-axis]");
        if (!btn) return;
        const { axis, value } = btn.dataset;
        state[axis] = axis === "granularity" ? Number(value) : value;
        render(data);
      });
    }

    /* Delegated from the chart host: the svg is rebuilt on every render, so
       the listener cannot live on it. The click acts on whichever handle the
       pointer has armed -- the same nearest-wins test that drew the hover
       state -- rather than on what was physically under the cursor, so the
       generous radius applies to clicking too. */
    const chart = document.getElementById("growthChart");
    if (chart) {
      chart.addEventListener("click", (ev) => {
        // A label switches its own series; anywhere else, the armed handle
        // anchors the axis. Labels are tested first -- one can sit over a
        // handle's grab radius, and the thing under the pointer wins there.
        const label = ev.target.closest("[data-slug]");
        if (label) {
          const slug = label.dataset.slug;
          if (state.hidden.has(slug)) state.hidden.delete(slug);
          // The last visible series does not switch off: an empty chart's only
          // way back is the labels it would have hidden.
          else if (visibleCount() > 1) state.hidden.add(slug);
          else return;
          // A hidden collection cannot also be the one the axis starts at.
          if (state.from === slug) state.from = "";
          render(data);
          return;
        }
        const svg = ev.target.closest("svg") || chart.querySelector("svg");
        const near = svg && svg.nearestHandle;
        if (!near) return;
        state.from = state.from === near.slug ? "" : near.slug;
        render(data);
      });
    }

    // The series colours are theme-dependent, so a theme flip has to redraw.
    // theme.js sets data-theme on the root element; observing it keeps the two
    // files from needing to know about each other.
    new MutationObserver(() => render(data)).observe(
      document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
  })
  .catch((err) => {
    // Nothing to fall back on, by the same reasoning as counts.js: a chart
    // drawn from stale hardcoded numbers is worse than a stated absence.
    console.error("growth.json could not be read:", err);
    const host = document.getElementById("growthChart");
    if (host) host.textContent = "Growth data unavailable.";
  });
