/* Fill the About page's code version from docs/VERSION.

   VERSION is `__key__ = "value"` lines rather than a bare version string,
   matching the three Atlases, so the same file is readable by a Python
   pipeline and by this parser. The Atlases track three keys -- code, data and
   content -- because each one sources a collection of its own. This project
   sources nothing: it aggregates what the Atlases publish, so only
   __code_version__ is meaningful here.

   The data date deliberately does NOT live in this file. data/counts.json
   already stamps itself with the moment `make data` wrote it, and that is the
   authoritative record; copying it here would be a second thing to keep
   correct, with the bad failure mode of a stale hand-edited date presented as
   fact. counts.js owns the figures from that file; the date below is read
   straight off the same JSON.

   Both fields are optional in the honest sense: on a fetch failure the spans
   stay empty rather than showing a guess. */

function readKey(text, key) {
  return (text.match(new RegExp(`__${key}__\\s*=\\s*"([^"]*)"`)) || [])[1];
}

fetch("./VERSION")
  .then((r) => (r.ok ? r.text() : Promise.reject(new Error(r.status))))
  .then((text) => {
    const code = readKey(text, "code_version");
    const el = document.getElementById("appVersion");
    if (el && code) el.textContent = `v${code}`;
  })
  .catch((err) => {
    // A missing version is cosmetic -- the rest of the page is unaffected --
    // so this is logged rather than surfaced.
    console.error("VERSION could not be read:", err);
  });
