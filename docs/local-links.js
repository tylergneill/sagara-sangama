/* When the page is served locally, point the Atlas links at the Atlases
   running locally too.

   The markup carries the published GitHub Pages URLs -- those are the real
   ones, and the file that ships is the file that is deployed. This rewrites
   them in place only when the host is local or on a private network, so a
   local Sāgarasaṅgama links to the local Atlases you are iterating on rather
   than jumping out to the last thing that was pushed. On the published site
   the condition is false and nothing here runs.

   Ports match the layout in serve_docs.py and the Makefile: 8000 is this
   parent, 8001-8003 the three Atlases, so all four serve side by side. */

const LOCAL_PORTS = {
  "sanskrit-wikisource-atlas": 8001,
  "e-bharatisampat-atlas": 8002,
  "sanskrit-documents-atlas": 8003,
  "jain-quantum-atlas": 8004,
  "gretil-atlas": 8005,
};

const PAGES_PREFIX = "https://tylergneill.github.io/";

/* "Local" means reachable on this machine or this LAN, not just loopback.
   Browsing the parent from a phone at 192.168.1.165:8000 is a normal way to
   work -- the Makefile has a get-server-ip-address target for exactly that --
   and the rewrite below uses location.hostname, so links land back on the same
   host the page came from. Private ranges only: a public hostname is the
   published site, where nothing here should run. */
const PRIVATE_IPV4 = /^(10\.|127\.|192\.168\.|172\.(1[6-9]|2\d|3[01])\.)/;

function isLocal(hostname) {
  return hostname === "localhost"
      || hostname === "[::1]"
      || hostname === "::1"
      || hostname.endsWith(".localhost")
      || hostname.endsWith(".local")   // mDNS, e.g. my-mac.local
      || PRIVATE_IPV4.test(hostname);
}

if (isLocal(location.hostname)) {
  for (const a of document.querySelectorAll("a[href]")) {
    // href is the resolved absolute URL, so a match is unambiguous.
    if (!a.href.startsWith(PAGES_PREFIX)) continue;
    const rest = a.href.slice(PAGES_PREFIX.length);
    const [slug, ...tail] = rest.split("/");
    const port = LOCAL_PORTS[slug];
    if (!port) continue;
    // Keep any deep path and query/hash, so a link into a particular work
    // survives the swap rather than landing on the Atlas's front page.
    a.href = `http://${location.hostname}:${port}/${tail.join("/")}`;
    a.dataset.localized = "true";  // visible in devtools when a link surprises you
  }
}
