/* Federated title search over all three Atlases, from data/search.json
   (written by `make search`, collect_atlas_search.py).

   The page looks like an Atlas and behaves like one -- same topbar, same
   transliteration control, same result rows -- but it has no sidebar and no
   tree, because it is not browsing a hierarchy. Three collections organised
   three incompatible ways have no shared hierarchy to browse; what they do
   share is titles. So search is the whole interface, and grouping is offered
   in two layers: by collection, and within a collection by that Atlas's own
   categories. Layers, not alternatives -- a category belongs to exactly one
   Atlas, and wikisource's उपनिषदः and e-bhāratīsampat's are different
   namespaces that merely share a word, so a category heading spanning
   collections would assert a shared taxonomy that does not exist. Turning
   categories on turns collections on with it.

   Category grouping is many-to-many on purpose. A wikisource page can sit in
   three places and a sanskrit-documents document on nine topic pages, so a
   work appears under each of its categories and the section counts sum to
   more than the match count -- collapsing to a first-listed category would
   invent a canonical one the data does not have. The depth control (1 / 2 /
   all) exists because wikisource nests five levels deep: at full depth that
   is hundreds of small headings, at depth 1 a readable handful.


   Rows keep what their Atlas gives them
   -------------------------------------
   A result is not flattened to a common shape. Each Atlas's own item row
   carries things the others have no equivalent for -- sanskrit-documents'
   scan of a printed witness, e-bhāratīsampat's separate text and PDF editions
   with a page count and a printing year, wikisource's chapter count and its
   Proofing badge -- and all of it survives into the result row, because the
   reason to search across three collections is to reach the items in them.

   What a row does NOT carry is anything its own Atlas chose not to show.
   sanskrit-documents has a per-script download for every document (ITX and
   half a dozen PDFs) and renders none of them; six near-identical badges is
   most of a row's width spent on one document's transliterations. This page
   follows suit -- see rehydrate.

   That is why renderRow branches per atlas rather than rendering a common
   subset: the common subset is title, size and date, which is not enough to
   act on a hit.


   URLs are derived here, not stored
   ---------------------------------
   The index ships ids, not links, exactly as each Atlas's own tree.json does
   (writing every href out costs 10 MB across 24627 items). rehydrate() puts
   them back on load, with each Atlas's rule copied from that Atlas's app.js:

     sanskrit-documents  <site>/<doc_id>.html. DOWNLOAD_SUFFIXES still spells
                         out the per-format rule, though no badge uses it
                         today -- see rehydrate
     e-bhāratīsampat     three query strings around one base64 bookid
     wikisource          stored whole -- a percent-encoded Devanagari title
                         has no shorter form

   If a link ever looks wrong, it is one of these three rules that drifted
   from its Atlas, and the Atlas is right.


   Scoring
   -------
   Substring matching, ranked so the obvious hit is first: exact title, then
   prefix, then word-boundary, then anywhere. Within a rank, shorter titles
   first -- a query is likelier to mean the work called exactly that than a
   longer title containing it. Ties break on title so the order is stable
   between renders rather than depending on index order. */

const DATA_URL = "./data/search.json";

/* Slots 1-3 of the categorical palette, one per Atlas, the same assignment and
   the same hex values as the About page's growth chart (docs/growth.js) --
   identity, so a collection keeps its colour everywhere on the site.

   These are kept here for the parts of the UI that need the colour as a value
   (nothing does yet) and, more importantly, as the readable record of which
   collection owns which hue. The rows and chips take their colour from the
   matching `.s-row--{code}` rules in styles.css, which set one `--atlas`
   custom property per theme and let CSS mix the background wash off it -- a
   stroke colour used as a fill would be far too loud behind text, and mixing
   it in CSS keeps the wash from drifting away from the stroke it came from. */
const ATLASES = {
  w: {
    slug: "sanskrit-wikisource-atlas",
    name: "Sanskrit Wikisource",
    site: "sa.wikisource.org",
    url: "https://tylergneill.github.io/sanskrit-wikisource-atlas",
    light: "#2a78d6", dark: "#3987e5", wave: "#5aa9f0",
  },
  e: {
    slug: "e-bharatisampat-atlas",
    name: "E-bhāratīsampat",
    site: "ebharatisampat.in",
    url: "https://tylergneill.github.io/e-bharatisampat-atlas",
    light: "#eb6834", dark: "#d95926", wave: "#f08a4b",
  },
  d: {
    slug: "sanskrit-documents-atlas",
    name: "Sanskrit Documents",
    site: "sanskritdocuments.org",
    url: "https://tylergneill.github.io/sanskrit-documents-atlas",
    light: "#1baf7a", dark: "#199e70", wave: "#38c793",
  },
};

/* Fixed display order wherever all three are listed -- the chips, and the
   group headings. Alphabetical by name would reorder them if one were
   renamed; this is the constellation's own order, clockwise from the top. */
const ATLAS_ORDER = ["w", "d", "e"];

const SD_SITE = "https://sanskritdocuments.org";
const EB_SITE = "https://www.ebharatisampat.in";

/* Copied from the Atlas's docs/app.js. The site appends these to a document's
   stem; keep them in step with that file, which is the source of truth. */
const DOWNLOAD_SUFFIXES = {
  "ITX": ".itx",
  "Devanagari PDF": ".pdf",
  "Tamil PDF": "-ta.pdf",
  "Telugu PDF": "-te.pdf",
  "Kananda PDF": "-kn.pdf",
  "Kannada PDF": "-kn.pdf",
  "Gujarati PDF": "-gu.pdf",
  "Bengali PDF": "-bn.pdf",
  "Oriya PDF": "-or.pdf",
  "Malayalam PDF": "-ml.pdf",
  "Punjabi PDF": "-pa.pdf",
  "Assamese PDF": "-as.pdf",
  "Sanskrit PDF": "-sa.pdf",
};

/* One constant pageno across every readbook3 link in the corpus -- a
   session/view token, not a page number. From the Atlas's app.js. */
const EB_READBOOK_PAGENO = "MjI0MjQyNjk5NTk=";

/* How many rows to put in the DOM at once. The index holds 24627 items and an
   empty query matches all of them; rendering that many rows locks the page up
   for seconds. Everything below the cut stays one button away. */
const PAGE_SIZE = 200;

const state = {
  items: [],
  groups: [],
  dlLabels: [],
  meta: null,
  q: "",
  scheme: "iast",
  groupByAtlas: false,
  // Group under each Atlas's own categories. Mutually exclusive with
  // groupByAtlas -- two different partitions of the same list cannot both be
  // the outer one, and the checkbox handlers turn the other off.
  groupByCategory: false,
  // How much of a category path is the heading. 1 or 2 levels, or 0 for the
  // whole chain. Not cosmetic: wikisource nests five deep, so `all` yields
  // hundreds of small headings where 1 yields a handful of broad ones.
  catDepth: 1,
  showPdfOnly: false,
  // Atlas codes switched off by their chip. Empty = show all three.
  hidden: new Set(),
  limit: PAGE_SIZE,
  // Per-scheme lowercased title cache, built lazily -- the same shape and the
  // same reason as each Atlas's indexedTitleById.
  translit: new Map(),
};

const nf = new Intl.NumberFormat("en-US");

function el(tag, attrs = {}, ...kids) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v == null || v === false) continue;
    if (k === "class") node.className = v;
    else if (k.startsWith("on") && typeof v === "function") {
      node.addEventListener(k.slice(2), v);
    } else node.setAttribute(k, v === true ? "" : v);
  }
  for (const kid of kids) {
    if (kid == null || kid === false) continue;
    node.append(kid.nodeType ? kid : document.createTextNode(String(kid)));
  }
  return node;
}

/* ------------------------------------------------------------------ *
 * Rehydration: put back what the index leaves out
 * ------------------------------------------------------------------ */

function rehydrate(data) {
  const groups = data.groups || [];
  for (const it of data.items) {
    if (it.a === "d") {
      it.u = `${SD_SITE}/${it.i}.html`;
      // No per-format download badges, matching the Atlas: its own row offers
      // the title, the size and the scan, and nothing else. Six near-identical
      // "... PDF" badges per row is most of the row's width spent on links to
      // one document's transliterations, and it crowds out `scan`, which is
      // the badge that says something the title does not. The formats are one
      // click away on the document's own page. `it.fmt` is still in the index
      // (see DOWNLOAD_SUFFIXES above, kept in step with the Atlas) so this is
      // a rendering decision, reversible without a reindex.
      it.fmtLinks = [];
    } else if (it.a === "e") {
      it.u = `${EB_SITE}/readSearch.php?id=${it.i}`;
      it.fmtLinks = [];
      if (it.txt) {
        it.fmtLinks.push({
          label: "text",
          href: it.toc
            ? `${EB_SITE}/read_chapter.php?bookid=${it.i}`
            : `${EB_SITE}/readbook3.php?bookid=${it.i}&pageno=${EB_READBOOK_PAGENO}`,
        });
      }
      if (it.pdf) {
        it.fmtLinks.push({ label: "PDF", href: `${EB_SITE}/ebook/index.php?bookid=${it.i}` });
      }
    } else {
      it.fmtLinks = [];   // wikisource stores its url whole
    }

    // `g` is a list of group ids, each the LEAF of an ancestor chain: the
    // index stores one id per placement and the parent links live on the
    // groups themselves, so a five-level wikisource path costs one integer
    // on the item. Expanded here into arrays of {t, url} from root down.
    it.groupPaths = (it.g || []).map((gid) => groupChain(groups, gid));
  }
  return data;
}

/* One group id -> its ancestors, root first. Walks `p` up the group table.

   Guarded against a cycle: the table is written by collect_atlas_search.py and
   is a forest by construction, but this runs on data loaded over the network
   and an infinite loop here would hang the page rather than misdraw a row. */
function groupChain(groups, gid) {
  const chain = [];
  const guard = new Set();
  let cur = gid;
  while (cur != null && groups[cur] && !guard.has(cur)) {
    guard.add(cur);
    const g = groups[cur];
    chain.push({
      t: g.t,
      // Only sanskrit-documents' groups are pages of their own -- a topic is
      // a real /sanskrit/<slug>/ page on the site. The other two Atlases'
      // categories are tree nodes with no upstream URL, and get no link
      // rather than a guessed one.
      url: g.k ? `${SD_SITE}/${g.k}/` : null,
    });
    cur = g.p;
  }
  return chain.reverse();
}

/* ------------------------------------------------------------------ *
 * Transliteration
 * ------------------------------------------------------------------ */

function hasSanscript() {
  return typeof window.Sanscript !== "undefined";
}

/* The title as it should read in the reader's chosen scheme.

   Only sanskrit-documents ships a separate Devanagari title (`n`); its Latin
   `t` is an English descriptive label ("1000 names of ... in Marathi"), not a
   transliteration, so converting `t` would produce nonsense. The other two
   store Devanagari titles directly in `t`. So: convert the Devanagari field
   where there is one, convert `t` where `t` is itself Devanagari, and leave a
   Latin label alone in every scheme -- exactly the rule each Atlas applies. */
const DEVANAGARI = /[ऀ-ॿ]/;

function displayTitle(it) {
  const source = it.n || (DEVANAGARI.test(it.t || "") ? it.t : null);
  if (!source) return it.t || "";
  if (state.scheme === "devanagari") return source;
  if (!hasSanscript()) return source;
  try {
    return window.Sanscript.t(source, "devanagari", state.scheme);
  } catch {
    return source;
  }
}

/* Diacritics stripped and the common ASCII digraphs folded away.

   This is what lets one query reach three collections that romanise
   differently. A document's Latin title on sanskritdocuments.org is unmarked
   ASCII ("Gayatri Ramayana"); the same work's Devanagari transliterates to
   marked IAST ("gayatri ramayanam"); e-bharatisampat and wikisource store
   Devanagari and nothing else. Without a fold, a reader typing the IAST they
   see on screen -- "ramayana" with its dots and macrons -- matches the first
   two and silently misses every ASCII-titled document in the third.

   NFD splits a letter from its marks so the combining range can be dropped in
   one pass; the digraph rules then cover the ITRANS/HK-ish spellings the site
   actually uses ("sh", "ii", "aa") so "vishnu" and "visnu" and "viṣṇu" all
   land on the same key. Deliberately lossy: this is a matching aid, never a
   display string -- displayTitle is what the reader sees. */
function fold(s) {
  return s
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/ri\b/g, "r")     // vowel r written as "ri"
    .replace(/sh/g, "s")
    .replace(/ch/g, "c")
    .replace(/([aiu])\1/g, "$1")  // aa/ii/uu -> a/i/u
    .replace(/[^a-z0-9\u0900-\u097f]+/g, " ")
    .trim();
}

/* Lowercased searchable form, cached per scheme. Three forms go in, so a hit
   is found whichever way the reader spells it: the title in the scheme now on
   screen, the Atlas's own Latin label, and both of those folded to bare ASCII.
   The author too -- searching a name is a normal way to look for a text. */
function searchKey(it, idx) {
  const cache = state.translit;
  const key = state.scheme + "\u001f" + idx;
  let v = cache.get(key);
  if (v === undefined) {
    const shown = displayTitle(it);
    const lower = shown.toLowerCase();
    const folded = fold(shown);
    const parts = [lower, folded];
    if (it.t) { parts.push(it.t.toLowerCase()); parts.push(fold(it.t)); }
    if (it.n) parts.push(it.n);
    if (it.au) { parts.push(it.au.toLowerCase()); parts.push(fold(it.au)); }
    // \u001f between fields so a match cannot straddle two of them and be
    // scored as though it were one word. The title's own two forms ride along
    // so scoring never has to re-fold: this runs 24627 times per keystroke.
    v = { hay: parts.join("\u001f"), title: lower, folded };
    cache.set(key, v);
  }
  return v;
}

/* The query in every shape the keys are indexed in: as typed, folded to bare
   ASCII, and -- since the index always carries the Devanagari -- transliterated
   there too. A hit on any of them is a hit; scoring uses the best one.

   Transliterating from IAST covers the ordinary case of a reader typing what
   they see. It is attempted whatever the scheme, because the box is where
   people type IAST regardless of which scheme the titles are being shown in. */
function queryForms(raw) {
  const q = raw.trim().toLowerCase();
  if (!q) return [];
  const forms = [q];
  const folded = fold(q);
  if (folded && folded !== q) forms.push(folded);
  if (hasSanscript()) {
    try {
      const deva = window.Sanscript.t(q, "iast", "devanagari");
      if (deva && deva !== q) forms.push(deva);
    } catch { /* leave the literal forms to do the work */ }
  }
  return forms;
}

/* ------------------------------------------------------------------ *
 * Searching
 * ------------------------------------------------------------------ */

function scoreOf(hay, title, q) {
  const at = hay.indexOf(q);
  if (at < 0) return -1;
  if (title === q) return 0;            // the title is exactly the query
  if (title.startsWith(q)) return 1;    // the title starts with it
  if (at === 0) return 2;               // some other field starts with it
  // A match at a word boundary beats one buried inside a word: searching
  // "rama" should rank "... Rama ..." above "paramartha". \u001f is the field
  // separator searchKey joins on, so it counts as a boundary too.
  return /[\s\u001f\-\u2013\u2014/(",.:]/.test(hay[at - 1]) ? 3 : 4;
}

/* The best score any spelling of the query achieves against this item. Taking
   the minimum rather than the first hit matters: "ramayana" folds to a form
   that matches mid-word in some long compound while matching a title exactly
   somewhere else, and the exact hit is the one that should decide the rank. */
function bestScore(hay, title, folded, forms) {
  let best = -1;
  for (const q of forms) {
    const s = scoreOf(hay, title, q);
    if (s >= 0 && (best < 0 || s < best)) best = s;
    // Folded titles are compared against folded queries as well, so an ASCII
    // title and a diacritic query meet in the middle.
    const sf = scoreOf(hay, folded, q);
    if (sf >= 0 && (best < 0 || sf < best)) best = sf;
    if (best === 0) break;
  }
  return best;
}

function search() {
  const forms = queryForms(state.q);
  const out = [];

  for (let i = 0; i < state.items.length; i++) {
    const it = state.items[i];
    if (state.hidden.has(it.a)) continue;
    if (it.po && !state.showPdfOnly) continue;

    // searchKey both ways: it is the one place a title is transliterated and
    // folded, and it caches. Calling displayTitle from a sort comparator
    // instead costs a Sanscript conversion per comparison -- ~270000 of them
    // to order an unfiltered 19000-row list, which is seconds, not milliseconds.
    const k = searchKey(it, i);
    if (!forms.length) {
      out.push({ it, score: 5, title: k.title });
      continue;
    }
    const score = bestScore(k.hay, k.title, k.folded, forms);
    if (score >= 0) out.push({ it, score, title: k.title });
  }

  if (forms.length) {
    out.sort((a, b) =>
      a.score - b.score ||
      a.title.length - b.title.length ||
      (a.title < b.title ? -1 : a.title > b.title ? 1 : 0));
  } else {
    // No query: the index order is arbitrary, so sort by title for a stable,
    // legible browse rather than showing whatever the collector emitted first.
    // Code-point order, not localeCompare: the titles are Devanagari and IAST
    // rather than one locale's alphabet, and localeCompare is ~50x slower per
    // comparison for no ordering the reader of this list would recognise.
    out.sort((a, b) => (a.title < b.title ? -1 : a.title > b.title ? 1 : 0));
  }
  return out;
}

/* ------------------------------------------------------------------ *
 * Rendering
 * ------------------------------------------------------------------ */

function formatBytes(b) {
  if (b == null) return null;
  if (b < 1024) return `${b} B`;
  if (b < 1024 * 1024) return `${(b / 1024).toFixed(1)} KB`;
  return `${(b / (1024 * 1024)).toFixed(1)} MB`;
}

/* "2022-02-01" -> "Feb 2022". Read off the string rather than parsed with
   `new Date()`: these carry no zone, so parsing would shift a January date
   into December for anyone west of UTC. Same reasoning as counts.js. */
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

function formatDate(iso) {
  if (!iso) return null;
  const m = /^(\d{4})(?:-(\d{2}))?/.exec(iso);
  if (!m) return null;
  if (!m[2]) return m[1];
  const mon = MONTHS[Number(m[2]) - 1];
  return mon ? `${mon} ${m[1]}` : m[1];
}

function badge(label, href, title, cls = "") {
  const attrs = { class: `s-badge ${cls}`.trim(), title };
  if (!href) return el("span", attrs, label);
  return el("a", { ...attrs, class: `s-badge s-badgeLink ${cls}`.trim(),
                   href, target: "_blank", rel: "noopener" }, label);
}

/* The meta line under a title: what this item is, in its own Atlas's terms.
   Assembled per atlas because the facts differ -- there is no shared set of
   three that would say anything useful about all of them. */
function metaBits(it) {
  const bits = [];
  if (it.a === "e") {
    // Author and publisher through displayDeva: e-bhāratīsampat records both
    // in Devanagari, and they follow the reader's scheme like everything else
    // on the row. A Latin name is returned unchanged.
    if (it.au) bits.push(displayDeva(it.au));
    // Two of the 11066 years are Devanagari -- one a numeral (१८९७), one a
    // name in the wrong field upstream -- so this goes through the same
    // helper rather than being the last raw string on the row.
    if (it.y) bits.push(displayDeva(it.y));
    if (it.pg) bits.push(`${it.pg} pp`);
    if (it.pub) bits.push(displayDeva(it.pub));
  } else if (it.a === "d") {
    // sanskrit-documents writes its authors in Latin, but a handful carry
    // Devanagari; same treatment, same no-op where there is none.
    if (it.au) bits.push(displayDeva(it.au));
    // Only worth saying when it is not the collection's default.
    if (it.lang && it.lang !== "Sanskrit") bits.push(it.lang);
  } else if (it.a === "w") {
    if (it.sub) bits.push(`${it.sub} ${it.sub === 1 ? "chapter" : "chapters"}`);
  }
  const size = formatBytes(it.b);
  if (size) bits.push(size);
  const date = formatDate(it.d);
  if (date) bits.push(date);

  // Properties of the item, NOT links. They used to sit in the badge row
  // beside `text`/`PDF`/`scan`, where an unclickable pill reads as a broken
  // link -- they name what a thing IS, while a badge names somewhere to go.
  // Last in the meta line, so the identifying facts (author, year, size) stay
  // at the front where they are scanned for.
  if (it.toc) bits.push("TOC");
  if (it.pf) bits.push("proofing");
  // Wikisource's scans are .pdf, .djvu and .tif alike, so "PDF only" would be
  // wrong there; e-bhāratīsampat's really are all PDFs.
  if (it.po) bits.push(it.a === "w" ? "image only" : "PDF only");
  return bits;
}

/* The atlas tag opens this item IN its own Atlas, already searched for.

   A bare link to the Atlas home page named the collection without doing
   anything with the row it sat on -- the reader had to retype the title on
   the other side. The Atlases read `?q=` at startup (applyQueryFromURL in
   each one's app.js), so the tag can carry the title across instead.

   `exact=1` because we know the whole title, not a fragment: the Atlases'
   substring search on a short title would otherwise bury it among partial
   matches. Sent as displayTitle(it) -- the string the row is showing, in the
   reader's current scheme -- because that is what the Atlas indexes and
   matches against. Following the link in Devanagari therefore searches
   Devanagari, which is what the reader is looking at.
*/
function atlasSearchUrl(atlas, it) {
  const base = atlasBase(atlas);
  const q = displayTitle(it);
  if (!q) return base;
  return `${base}/?q=${encodeURIComponent(q)}&exact=1`;
}

/* local-links.js rewrites published Atlas URLs to local ports, but it sweeps
   the DOM once at load and these rows are built on every keystroke, so a
   result row would keep jumping out to GitHub Pages while you iterate. The
   rule is duplicated rather than re-run: this is the one place a row's Atlas
   URL is constructed, and rewriting after the fact would mean re-sweeping the
   list on every render. Ports and host test match that file -- keep them in
   step. */
const ATLAS_LOCAL_PORTS = {
  "sanskrit-wikisource-atlas": 8001,
  "e-bharatisampat-atlas": 8002,
  "sanskrit-documents-atlas": 8003,
};

/* Which Atlases are actually serving their corpus right now. Probed once at
   startup, never assumed: an Atlas only answers /text/ when started with
   `--fulltext`, and on GitHub Pages nothing answers at all. Kept a Set rather
   than a boolean because the three run independently -- one may be in
   fulltext mode while the others are not. */
const FULLTEXT_ATLASES = new Set();

async function detectFulltextAtlases() {
  // THE SERVER DECIDES, not this page. `make serve` does not answer this
  // route, so the fetch 404s and we return having probed nothing -- which is
  // what makes `make serve` render byte-identically to the published site,
  // even with all three Atlases running in fulltext mode on this machine.
  //
  // Inferring the mode from whether the Atlas ports happen to be listening
  // was the earlier design and it was wrong: the page would quietly enter a
  // special mode because something else was left running.
  try {
    const mode = await fetch("/fulltext-mode");
    if (!mode.ok) return;
    if (!(await mode.json()).fulltext) return;
  } catch {
    return;   // published site, offline, or file://
  }

  await Promise.all(Object.keys(ATLAS_LOCAL_PORTS).map(async (slug) => {
    const port = ATLAS_LOCAL_PORTS[slug];
    try {
      const res = await fetch(`http://${location.hostname}:${port}/text/`,
                              { method: "HEAD" });
      if (res.headers.get("X-Fulltext-Mode") === "on") FULLTEXT_ATLASES.add(slug);
    } catch {
      /* that Atlas is not running, or is not offering text -- either way, no
         badge. A dead probe must never block the page. */
    }
  }));
}

function atlasBase(atlas) {
  const port = ATLAS_LOCAL_PORTS[atlas.slug];
  if (!port || !isLocalHost(location.hostname)) return atlas.url;
  return `http://${location.hostname}:${port}`;
}

/* Copied from local-links.js. "Local" means this machine or this LAN, not just
   loopback: browsing from a phone at 192.168.1.165:8000 is a normal way to
   work here, and those sessions must reach the local Atlases too. */
const PRIVATE_IPV4 = /^(10\.|127\.|192\.168\.|172\.(1[6-9]|2\d|3[01])\.)/;

function isLocalHost(hostname) {
  return hostname === "localhost"
      || hostname === "[::1]"
      || hostname === "::1"
      || hostname.endsWith(".localhost")
      || hostname.endsWith(".local")
      || PRIVATE_IPV4.test(hostname);
}

/* Any incidental Devanagari string -- a group name, an author, a publisher --
   rendered in the reader's chosen scheme.

   The transliteration control governs everything on the page that IS
   Devanagari, not just the titles: e-bhāratīsampat records its authors and
   publishers in Devanagari (वेदव्यासाचार्यः), and printing those raw left the
   one part of a row that ignored the control sitting beside the parts that
   obey it. Strings with no Devanagari in them -- sanskrit-documents' ASCII
   topic slugs, a Latin author name -- pass through untouched, so this is safe
   to apply to any field that MIGHT be Devanagari without knowing whether it
   is.

   Distinct from displayTitle, which picks between an item's Latin and
   Devanagari titles; this one transliterates a single string it is given. */
function displayDeva(text) {
  if (!text || !DEVANAGARI.test(text)) return text || "";
  if (state.scheme === "devanagari" || !hasSanscript()) return text;
  try {
    return window.Sanscript.t(text, "devanagari", state.scheme);
  } catch {
    return text;
  }
}

function renderRow(it) {
  const atlas = ATLASES[it.a];

  const title = el("a", {
    class: "s-title", href: it.u, target: "_blank", rel: "noopener",
    // e-bhāratīsampat's title goes to the metadata page: it names the work,
    // and the work is not any one of its formats. Reaching a format is the
    // badges' job, as in that Atlas's own rows.
    title: it.a === "e" ? "Open the work's page on ebharatisampat.in"
                        : `Open on ${atlas.site}`,
  }, displayTitle(it));

  const head = el("div", { class: "s-rowHead" }, title);

  // No second copy of the title in Devanagari. displayTitle already renders
  // `it.n` in whatever scheme the reader picked, so the extra span repeated
  // the same name -- and, printed raw, was the one string on the row that
  // ignored the transliteration control it sat next to.

  const bits = metaBits(it);
  if (bits.length) head.append(el("span", { class: "s-meta" }, bits.join(" · ")));

  const badges = el("span", { class: "s-badges" });

  for (const f of it.fmtLinks) {
    badges.append(badge(f.label, f.href, `Open ${f.label} on ${atlas.site}`));
  }

  for (const href of (it.scan || [])) {
    badges.append(badge("scan", href,
      "A scan of an edition containing this text — not necessarily the one it was encoded from",
      "s-badgeScan"));
  }

  // ALWAYS LAST. The published links come first -- they are what the row
  // is about -- and this local-only affordance sits at the end of the
  // row, after `scan`, so the badge order does not shift depending on
  // which mode the server is in.
  //
  // The locally cached plain text, served by an Atlas's own
  // `serve_docs.py --fulltext`. Three conditions, all required: that Atlas
  // published `has_text` for this item (`it.lt`), we are browsing locally at
  // all, and that Atlas's server answered our probe saying it is offering the
  // corpus. On the published site the last two are false and this never
  // renders -- the text is not ours to republish.
  //
  // The key differs per atlas because their servers do: e-bharatisampat
  // resolves a serial (carried in `lt`), sanskrit-documents a doc stem
  // (already `i`), wikisource a title (already `t`).
  const localTxtKey = it.lt === 1
    ? (it.a === "d" ? it.i : it.t)
    : it.lt;
  if (localTxtKey && FULLTEXT_ATLASES.has(atlas.slug)) {
    const path = String(localTxtKey).split("/").map(encodeURIComponent).join("/");
    badges.append(badge("txt", `${atlasBase(atlas)}/text/${path}`,
      "Open the locally cached plain text (this machine only)", "s-badgeLocal"));
  }

  const foot = el("div", { class: "s-rowFoot" });
  // On EVERY row, grouped or not. It reads like a label naming the collection
  // -- which the group heading above would already be saying -- but it is a
  // per-item link into that Atlas, searched for this title (atlasSearchUrl).
  // Hiding it under grouping was right while it was only a label, and became
  // a loss of navigation the moment it stopped being one.
  foot.append(el("a", { class: "s-atlasTag", href: atlasSearchUrl(atlas, it),
                        target: "_blank", rel: "noopener",
                        title: `View this text in the ${atlas.name} Atlas` },
                 atlas.name));
  // Every placement, each as its full path from the root down. A wikisource
  // page classified twice shows both chains; a sanskrit-documents document on
  // nine topic pages shows nine. Only the deepest name of each chain is the
  // group proper -- its ancestors are rendered dimmer, as the context that
  // makes it specific (उपनिषदः means one thing under वेदाः and another under
  // प्रमुखोपनिषदः).
  for (const chain of (it.groupPaths || [])) {
    if (!chain.length) continue;
    const crumb = el("span", { class: "s-group" });
    chain.forEach((node, i) => {
      const last = i === chain.length - 1;
      if (i) crumb.append(el("span", { class: "s-groupSep" }, "/"));
      const label = displayDeva(node.t);
      crumb.append(node.url
        ? el("a", { class: last ? "s-groupLeaf" : "s-groupAnc",
                    href: node.url, target: "_blank", rel: "noopener",
                    title: `Browse this topic on ${atlas.site}` }, label)
        : el("span", { class: last ? "s-groupLeaf" : "s-groupAnc" }, label));
    });
    foot.append(crumb);
  }
  if (badges.childNodes.length) foot.append(badges);

  return el("article", { class: `s-row s-row--${it.a}` }, head, foot);
}

function renderResults(hits) {
  const host = document.getElementById("results");
  host.textContent = "";

  if (!hits.length) {
    host.append(el("p", { class: "s-empty" },
      state.q ? `Nothing matches “${state.q}”.` : "No items to show."));
    return;
  }

  const shown = hits.slice(0, state.limit);

  // Category grouping IMPLIES atlas grouping, so this tests the pair rather
  // than groupByAtlas alone: a category belongs to exactly one collection --
  // wikisource's उपनिषदः and e-bhāratīsampat's are different namespaces that
  // happen to share a name -- so a category heading spanning collections
  // would merge two unrelated classifications under one title.
  if (!state.groupByAtlas && !state.groupByCategory) {
    const list = el("div", { class: "s-list" });
    for (const h of shown) list.append(renderRow(h.it));
    host.append(list);
    return;
  }

  // Grouped: the same ranked order, partitioned by collection. Every visible
  // collection gets a heading, including one with no hits, so the reader can
  // see that it was searched and came back empty rather than wondering.
  const byAtlas = new Map(ATLAS_ORDER.map((c) => [c, []]));
  for (const h of shown) byAtlas.get(h.it.a)?.push(h.it);

  for (const code of ATLAS_ORDER) {
    if (state.hidden.has(code)) continue;
    const rows = byAtlas.get(code) || [];
    const atlas = ATLASES[code];
    const total = hits.filter((h) => h.it.a === code).length;

    const section = el("section", { class: `s-group-section s-row--${code}` });
    section.append(el("h2", { class: "s-groupHead" },
      el("a", { class: "s-groupName", href: atlas.url, target: "_blank",
                rel: "noopener", title: `Browse ${atlas.name} in its own Atlas` },
         atlas.name),
      el("span", { class: "s-groupCount" },
        total === rows.length
          ? `${nf.format(total)} ${total === 1 ? "result" : "results"}`
          : `${nf.format(rows.length)} of ${nf.format(total)} shown`)));

    if (!rows.length) {
      section.append(el("p", { class: "s-empty s-emptyGroup" }, "No matches here."));
    } else if (state.groupByCategory) {
      // This collection's own categories, nested under its heading.
      for (const sub of categorySections(rows)) section.append(sub);
    } else {
      const list = el("div", { class: "s-list" });
      for (const it of rows) list.append(renderRow(it));
      section.append(list);
    }
    host.append(section);
  }
}

/* One collection's results, split by its own categories.

   Returns sections to nest inside that collection's heading -- never a
   top-level partition, because a category belongs to exactly one Atlas.
   Two collections can use the same word for unrelated classifications, and
   merging them under one heading would assert a shared taxonomy that does
   not exist.

   MANY-TO-MANY within a collection, on purpose: a wikisource page in three
   categories, or a sanskrit-documents document on nine topic pages, appears
   under each. Collapsing to a first-listed category would invent a canonical
   one the data does not have. The section counts therefore sum to more than
   the collection's result count, which renderStatus says out loud.

   Headings are the path truncated to state.catDepth, so two sibling leaves
   under one parent merge into that parent at depth 1 and separate at `all`.
   Items with no category at all collect under one trailing "Uncategorized"
   section rather than vanishing. */
const UNCATEGORIZED = "\u0000uncat";

function categorySections(items) {
  const depth = state.catDepth;
  const keyOf = (chain) => {
    const cut = depth > 0 ? chain.slice(0, depth) : chain;
    return cut.map((n) => n.t).join(" / ");
  };

  // key -> {chain, items[]}. Insertion order is the ranked order of each
  // section's best hit, so the strongest matches stay near the top.
  const sections = new Map();
  const add = (key, chain, it) => {
    let sec = sections.get(key);
    if (!sec) sections.set(key, (sec = { chain, items: [] }));
    sec.items.push(it);
  };

  for (const it of items) {
    const paths = it.groupPaths || [];
    if (!paths.length) {
      add(UNCATEGORIZED, null, it);
      continue;
    }
    // De-duplicated per item: at depth 1, two of an item's paths that share
    // a root would otherwise list it twice under the one heading.
    const keys = new Set();
    for (const chain of paths) {
      const key = keyOf(chain);
      if (keys.has(key)) continue;
      keys.add(key);
      add(key, depth > 0 ? chain.slice(0, depth) : chain, it);
    }
  }

  const out = [];
  for (const [key, sec] of sections) {
    if (key === UNCATEGORIZED) continue;
    out.push(categorySection(sec.chain, sec.items));
  }
  // Trailing, whatever order it was met in: "no category" is not a category,
  // and sorting it in among real ones would imply it is.
  const uncat = sections.get(UNCATEGORIZED);
  if (uncat) out.push(categorySection(null, uncat.items));
  return out;
}

function categorySection(chain, items) {
  const section = el("section", { class: "s-catSection" });
  const heading = el("h3", { class: "s-catHead" });

  if (chain && chain.length) {
    const name = el("span", { class: "s-catName" });
    chain.forEach((node, i) => {
      if (i) name.append(el("span", { class: "s-groupSep" }, "/"));
      name.append(el("span", { class: i === chain.length - 1 ? "" : "s-groupAnc" },
                     displayDeva(node.t)));
    });
    heading.append(name);
  } else {
    heading.append(el("span", { class: "s-catName s-groupAnc" }, "Uncategorized"));
  }

  heading.append(el("span", { class: "s-groupCount" },
    `${nf.format(items.length)} ${items.length === 1 ? "result" : "results"}`));
  section.append(heading);

  const list = el("div", { class: "s-list" });
  for (const it of items) list.append(renderRow(it));
  section.append(list);
  return section;
}

function renderStatus(hits) {
  const status = document.getElementById("status");
  const total = hits.length;
  const shown = Math.min(state.limit, total);

  const parts = [];
  parts.push(state.q
    ? `${nf.format(total)} ${total === 1 ? "match" : "matches"}`
    : `${nf.format(total)} titles`);
  if (total > shown) parts.push(`showing the first ${nf.format(shown)}`);

  // The PDF-only works are the one place the visible count can disagree with
  // the totals the home page publishes, so the page says which it is showing.
  if (state.showPdfOnly) {
    parts.push("including scans with no text");
  }
  // Categories are multi-valued in two of the three collections, so a work
  // appears under each of its categories and the section counts add up to
  // more than the match count. Said out loud, because a reader who adds up
  // the headings and gets a bigger number deserves to know why.
  if (state.groupByCategory) {
    parts.push(state.catDepth > 0
      ? `grouped by category, ${state.catDepth} level${state.catDepth === 1 ? "" : "s"} deep`
      : "grouped by full category path");
    parts.push("within each collection; a work in several categories is listed under each");
  }
  status.textContent = parts.join(" · ");

  const more = document.getElementById("moreBtn");
  more.hidden = total <= shown;
  more.textContent = `Show ${nf.format(Math.min(PAGE_SIZE, total - shown))} more`;
}

function renderChips() {
  const host = document.getElementById("atlasChips");
  host.textContent = "";
  for (const code of ATLAS_ORDER) {
    const atlas = ATLASES[code];
    const on = !state.hidden.has(code);
    host.append(el("button", {
      class: `s-chip s-row--${code}${on ? " is-on" : ""}`,
      type: "button",
      "aria-pressed": on ? "true" : "false",
      title: on ? `Hide ${atlas.name} results` : `Show ${atlas.name} results`,
      onclick: () => {
        if (on) state.hidden.add(code); else state.hidden.delete(code);
        // Turning a collection off can leave fewer results than the current
        // window; reset so the reader is not left staring at a stale cut.
        state.limit = PAGE_SIZE;
        render();
        // Which collections are showing is part of what a result list IS, so
        // it belongs in the URL like the query does -- otherwise a link to a
        // filtered view silently reopens unfiltered.
        syncUrl();
      },
    }, el("span", { class: "s-chipDot" }), atlas.name));
  }
}

function render() {
  const hits = search();
  renderChips();
  renderResults(hits);
  renderStatus(hits);
}

/* ------------------------------------------------------------------ *
 * Wiring
 * ------------------------------------------------------------------ */

/* The query lives in the URL, so a result list can be linked to and the back
   button returns to the previous one. Written with replaceState while typing
   -- one history entry per keystroke would make Back useless. */
function syncUrl() {
  const p = new URLSearchParams();
  if (state.q) p.set("q", state.q);
  if (state.scheme !== "iast") p.set("scheme", state.scheme);
  if (state.groupByAtlas) p.set("group", "atlas");
  if (state.groupByCategory) {
    p.set("group", "category");
    if (state.catDepth !== 1) p.set("depth", String(state.catDepth));
  }
  if (state.showPdfOnly) p.set("pdfonly", "1");
  for (const code of state.hidden) p.append("hide", code);
  const qs = p.toString();
  history.replaceState(null, "", qs ? `?${qs}` : location.pathname);
}

function readUrl() {
  const p = new URLSearchParams(location.search);
  state.q = p.get("q") || "";
  const scheme = p.get("scheme");
  if (scheme) state.scheme = scheme;
  const grouping = p.get("group");
  state.groupByCategory = grouping === "category";
  // "category" implies "atlas": the categories are rendered inside the
  // collection sections, so the outer partition has to be on.
  state.groupByAtlas = grouping === "atlas" || state.groupByCategory;
  // Guarded on the raw string, not the number: Number(null) is 0, which is a
  // valid depth ("all"), so testing the number alone made every URL without
  // a depth parameter mean "full path".
  const rawDepth = p.get("depth");
  if (rawDepth !== null && ["0", "1", "2"].includes(rawDepth)) {
    state.catDepth = Number(rawDepth);
  }
  state.showPdfOnly = p.get("pdfonly") === "1";
  for (const code of p.getAll("hide")) {
    if (ATLASES[code]) state.hidden.add(code);
  }
}

function renderProvenance() {
  const host = document.getElementById("provenance");
  if (!host || !state.meta) return;
  const counts = state.meta.atlases
    .filter((a) => !a.error)
    .map((a) => `${ATLASES[a.code].name} ${nf.format(a.indexed)}`)
    .join(" · ");
  host.textContent =
    `Titles read from each Atlas's published data — ${counts}. `
    + `Snapshot figures, not live; rebuilt with ‘make search’.`;
}

async function init() {
  readUrl();

  // Probe the three Atlases before the first render, so rows come up with
  // their `txt` badges already correct rather than flickering one in.
  await detectFulltextAtlases();

  const input = document.getElementById("q");
  const clear = document.getElementById("qClear");
  const scheme = document.getElementById("scheme");
  const group = document.getElementById("groupByAtlas");
  const byCat = document.getElementById("groupByCategory");
  const depthWrap = document.getElementById("catDepthWrap");
  const pdfOnly = document.getElementById("showPdfOnly");
  const more = document.getElementById("moreBtn");

  input.value = state.q;
  scheme.value = state.scheme;
  group.checked = state.groupByAtlas;
  byCat.checked = state.groupByCategory;
  pdfOnly.checked = state.showPdfOnly;
  syncDepthUI();
  clear.hidden = !state.q;

  let timer = null;
  input.addEventListener("input", () => {
    state.q = input.value;
    clear.hidden = !state.q;
    state.limit = PAGE_SIZE;
    // Debounced: 24627 items is fast to scan but not free, and re-running on
    // every keystroke of a long query is wasted work the user never sees.
    clearTimeout(timer);
    timer = setTimeout(() => { render(); syncUrl(); }, 90);
  });

  input.addEventListener("keydown", (ev) => {
    if (ev.key === "Escape" && state.q) {
      ev.preventDefault();
      input.value = "";
      input.dispatchEvent(new Event("input"));
    }
  });

  clear.addEventListener("click", () => {
    input.value = "";
    input.dispatchEvent(new Event("input"));
    input.focus();
  });

  scheme.addEventListener("change", () => {
    state.scheme = scheme.value;
    state.limit = PAGE_SIZE;
    render();
    syncUrl();
  });

  // The two groupings are layers, not alternatives: categories nest inside
  // collections, because a category belongs to one Atlas. So turning
  // categories on turns collections on with it, and turning collections off
  // takes categories off too -- there is nothing left to nest them in.
  group.addEventListener("change", () => {
    state.groupByAtlas = group.checked;
    if (!state.groupByAtlas) state.groupByCategory = false;
    byCat.checked = state.groupByCategory;
    syncDepthUI();
    render();
    syncUrl();
  });

  byCat.addEventListener("change", () => {
    state.groupByCategory = byCat.checked;
    if (state.groupByCategory) state.groupByAtlas = true;
    group.checked = state.groupByAtlas;
    syncDepthUI();
    render();
    syncUrl();
  });

  depthWrap.addEventListener("click", (ev) => {
    const btn = ev.target.closest(".s-depthBtn");
    if (!btn) return;
    state.catDepth = Number(btn.dataset.depth);
    syncDepthUI();
    // Only meaningful while category grouping is on, but changing it there
    // should switch the view on rather than silently doing nothing.
    if (!state.groupByCategory) {
      state.groupByCategory = true;
      state.groupByAtlas = true;
      byCat.checked = true;
      group.checked = true;
    }
    render();
    syncUrl();
  });

  function syncDepthUI() {
    depthWrap.hidden = !state.groupByCategory;
    for (const btn of depthWrap.querySelectorAll(".s-depthBtn")) {
      const on = Number(btn.dataset.depth) === state.catDepth;
      btn.classList.toggle("is-on", on);
      btn.setAttribute("aria-pressed", on ? "true" : "false");
    }
  }

  pdfOnly.addEventListener("change", () => {
    state.showPdfOnly = pdfOnly.checked;
    state.limit = PAGE_SIZE;
    render();
    syncUrl();
  });

  more.addEventListener("click", () => {
    state.limit += PAGE_SIZE;
    render();
  });

  try {
    const r = await fetch(DATA_URL);
    if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
    const data = rehydrate(await r.json());
    state.items = data.items;
    state.groups = data.groups || [];
    state.dlLabels = data.dl_labels || [];
    state.meta = data;
  } catch (err) {
    // Say what failed rather than leaving an empty box, the same way counts.js
    // and growth.js do when their JSON does not arrive.
    document.getElementById("status").textContent =
      `Could not load the search index (${err.message}). `
      + `It is built by ‘make search’ into docs/data/search.json.`;
    document.getElementById("results").textContent = "";
    return;
  }

  renderProvenance();
  render();
  // Focus last: an autofocus before the index lands invites typing into a box
  // that cannot answer yet.
  if (!state.q) input.focus();
}

document.addEventListener("DOMContentLoaded", init);
