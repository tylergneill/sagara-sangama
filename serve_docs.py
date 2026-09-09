#!/usr/bin/env python3
"""Local dev server for docs/, gzip-compressing responses and setting
Cache-Control so repeated reloads during iteration (and testing over an
ngrok tunnel on a mobile data plan) don't re-transfer the full uncompressed
payload on every load. python -m http.server does neither.

Port 8000, leaving 8001/8002/8003 to the sanskrit-wikisource, e-bharatisampat and
sanskrit-documents Atlases, so this parent and its children can all run at
once.

## Two modes, and `make serve` IS the published site

**`make serve` renders exactly what GitHub Pages renders.** No probing, no
local-only affordances, no divergence -- if it looks different here than it
does deployed, that is a bug. That is what makes this server useful for
checking the real thing.

**`make serve-fulltext` is the separate mode.** Only then does the page probe
the three Atlases for locally served corpus text and offer `txt` links into
it. This server still holds no text of its own -- it links to whichever Atlas
owns the row, and only to one that is itself running with `--fulltext`.

The mode is announced at `/fulltext-mode`, which the page asks once at
startup. Deliberately server-declared rather than inferred from whether the
Atlas ports happen to be listening: the page must not decide it is in a
special mode because something else was left running.
"""
import argparse
import gzip
from functools import partial
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

PORT = 8000

# What the frontend asks to learn which mode this server is in.
MODE_ROUTE = "/fulltext-mode"
CACHE_MAX_AGE = 60  # seconds; short, so edits during iteration aren't stale for long
COMPRESSIBLE_SUFFIXES = {".json", ".js", ".html", ".css", ".svg"}


class CachingGzipHandler(SimpleHTTPRequestHandler):
    fulltext = False

    # Applies to the non-gzipped path, which SimpleHTTPRequestHandler serves
    # itself; the gzipped path sets its own Content-Type via _content_type().
    extensions_map = {
        **SimpleHTTPRequestHandler.extensions_map,
        ".html": "text/html; charset=utf-8",
        ".css": "text/css; charset=utf-8",
        ".js": "text/javascript; charset=utf-8",
        ".json": "application/json; charset=utf-8",
        ".svg": "image/svg+xml; charset=utf-8",
    }

    def end_headers(self):
        self.send_header("Cache-Control", f"max-age={CACHE_MAX_AGE}")
        super().end_headers()

    def do_GET(self):
        # The mode question, answered by the SERVER rather than guessed at by
        # the page. In the published site this route does not exist, the fetch
        # 404s, and the page stays in its normal mode -- which is why `make
        # serve` and GitHub Pages render identically.
        if self.path.split("?")[0] == MODE_ROUTE:
            if not self.fulltext:
                self.send_error(404, "not in fulltext mode")
                return
            body = b'{"fulltext":true}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        path = self.translate_path(self.path)
        accepts_gzip = "gzip" in self.headers.get("Accept-Encoding", "")
        if accepts_gzip and Path(path).suffix in COMPRESSIBLE_SUFFIXES and Path(path).is_file():
            self._serve_gzipped(path)
        else:
            super().do_GET()

    def _content_type(self, path):
        """guess_type() returns bare "text/html" etc, which browsers decode as
        Latin-1 -- turning every em dash and every Devanagari codepoint into
        mojibake. Everything here is UTF-8, so say so."""
        ctype = self.guess_type(path)
        if ctype.startswith("text/") or ctype in (
                "application/json", "application/javascript",
                "image/svg+xml"):
            return f"{ctype}; charset=utf-8"
        return ctype

    def _serve_gzipped(self, path):
        raw = Path(path).read_bytes()
        compressed = gzip.compress(raw)
        self.send_response(200)
        self.send_header("Content-Type", self._content_type(path))
        self.send_header("Content-Encoding", "gzip")
        self.send_header("Content-Length", str(len(compressed)))
        self.end_headers()
        self.wfile.write(compressed)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("port", nargs="?", type=int, default=PORT)
    parser.add_argument(
        "--fulltext", action="store_true",
        help="offer `txt` links into the Atlases' locally served corpus text. "
             "LOCALHOST ONLY. Without this the page renders exactly as the "
             "published site does",
    )
    args = parser.parse_args()
    port = args.port
    CachingGzipHandler.fulltext = args.fulltext
    # Pin the served directory to docs/ rather than inheriting the caller's
    # cwd. `make serve` does `cd docs` first, so this changes nothing there --
    # but run from the repo root the old behaviour served the whole repo.
    handler = partial(CachingGzipHandler,
                      directory=str(Path(__file__).resolve().parent / "docs"))
    # Loopback in fulltext mode, all interfaces otherwise: the normal mode is
    # the published site and is fine to reach from a phone on the LAN; the
    # fulltext one offers links into corpus text and is not.
    host = "127.0.0.1" if args.fulltext else ""
    server = HTTPServer((host, port), handler)
    print(f"Serving docs/ on http://localhost:{port} (gzip + Cache-Control: max-age={CACHE_MAX_AGE})")
    if args.fulltext:
        print("  fulltext: ON -- `txt` links into the Atlases' local text.")
        print("            LOCALHOST ONLY. This is NOT what the published site shows.")
    else:
        print("  fulltext: off -- rendering exactly what the published site renders.")
    server.serve_forever()


if __name__ == "__main__":
    main()
