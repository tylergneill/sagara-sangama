#!/usr/bin/env python3
"""Generator for the wave mode's scrollwork band (docs/assets/scroll.svg).

Wave mode lays a band of foliate scrollwork behind the page and drifts it
sideways.  The band is one tile repeated on the x axis, so it has to meet
itself exactly at the seam; everything here is built to make that true by
construction rather than by eye.


The motif
---------
Traditional Indian foliate scrollwork -- the running vine of a temple lintel or
a manuscript border: a continuous stem that throws off coiled volutes at
intervals, with leaves and lesser curls packing the ground so no field is left
bare.  Three elements, in decreasing weight:

    the vine       one full sine period across the tile
    the volutes    coils springing from the vine, alternating in handedness
    the ground     tongues and small curls filling what the first two leave

Everything is stroked, nothing filled: at background opacity a filled ornament
reads as a smudge, while line work keeps its drawing at any scale.


Seamlessness
------------
The vine is one full period of a sine, drawn as four quarter-period cubics.
The control-point offset 0.3642 * (quarter width) is the standard best cubic
fit to a sine quarter, which matters here because it leaves the curve
horizontal at both tile edges -- the tile's left end and right end meet at the
same y with the same tangent, so a repeat shows no seam.

Ornament sitting at fx = 0.0 is duplicated at fx = 1.0 for the same reason: the
half of it that overhangs the tile edge is what the neighbouring copy shows on
its own side of the join.


Volute shape
------------
A volute is drawn inward from its mouth as quarter-turn cubics, the radius
scaled by `shrink` each quarter.  The two parameters trade off against each
other and were picked by rendering the grid of them at the size the band
actually uses:

    turns 2.0  shrink 0.66   collapses to a blob, no eye
    turns 2.5  shrink 0.82   a coil with a visible eye        <- what we use
    turns 3.0  shrink 0.88   too open, reads as a spring

Below about shrink 0.78 the coil closes before the eye is legible at
background scale; above about 0.88 it never closes at all.
"""

import argparse
import math
import os

# Tile geometry.  240x120 at a 100px repeat height means roughly two full
# vine periods across a phone and about eight across a desktop -- dense enough
# to read as a border, open enough not to fight the text over it.
W, H = 240.0, 120.0
MID = H / 2
AMP = 20.0            # vine amplitude; 3*AMP still clears the tile's top edge

# Best cubic approximation constants.
SINE_K = 0.3642       # control offset for a sine quarter, as a fraction of it
CIRCLE_K = 0.5523     # control offset for a circle quarter, ditto


def fmt(v):
    """Trim coordinates: the tile ships as a CSS data URI, where every
    character is bytes on the wire."""
    return ("%.1f" % v).rstrip("0").rstrip(".")


def pt(p):
    return "%s,%s" % (fmt(p[0]), fmt(p[1]))


def vine_y(x):
    return MID + AMP * math.sin(2 * math.pi * x / W)


def vine():
    """One full sine period across the tile, as four quarter cubics."""
    q = W / 4
    k = q * SINE_K
    d = "M 0,%s" % fmt(MID)
    for i in range(4):
        x0, x1 = q * i, q * (i + 1)
        y0, y1 = vine_y(x0), vine_y(x1)
        d += " C %s %s %s" % (pt((x0 + k, y0)), pt((x1 - k, y1)), pt((x1, y1)))
    return d


def volute(cx, cy, r, sign, turns=2.5, shrink=0.82, ang0=None):
    """A coil winding inward from its mouth at (cx, cy).

    sign is +1 for a clockwise coil, -1 for counter-clockwise -- alternating
    handedness along the band is what gives running scrollwork its rhythm.
    """
    ang = math.pi if ang0 is None else ang0
    # Work back from the mouth to the centre the first quarter turns about.
    ox = cx - r * math.cos(ang)
    oy = cy - r * math.sin(ang)
    d = "M %s" % pt((cx, cy))
    x, y = cx, cy
    for _ in range(int(turns * 4)):
        nang = ang + sign * math.pi / 2
        nr = r * shrink
        nx = ox + nr * math.cos(nang)
        ny = oy + nr * math.sin(nang)
        # Tangent at each end, turned 90 degrees from the radius.
        t0 = (-math.sin(ang) * sign, math.cos(ang) * sign)
        t1 = (-math.sin(nang) * sign, math.cos(nang) * sign)
        d += " C %s %s %s" % (
            pt((x + t0[0] * r * CIRCLE_K, y + t0[1] * r * CIRCLE_K)),
            pt((nx - t1[0] * nr * CIRCLE_K, ny - t1[1] * nr * CIRCLE_K)),
            pt((nx, ny)))
        x, y, r, ang = nx, ny, nr, nang
    return d


def leaf(tipx, tipy, bx, by, bulge):
    """A foliate tongue: two arcs bowed apart, meeting at a point each end."""
    mx, my = (tipx + bx) / 2, (tipy + by) / 2
    dx, dy = bx - tipx, by - tipy
    n = math.hypot(dx, dy) or 1.0
    px, py = -dy / n, dx / n          # unit normal to the tongue's axis
    return "M %s Q %s %s Q %s %s" % (
        pt((tipx, tipy)),
        pt((mx + px * bulge, my + py * bulge)), pt((bx, by)),
        pt((mx - px * bulge, my - py * bulge)), pt((tipx, tipy)))


def build_paths():
    paths = [vine()]

    # Principal volutes at the vine's crests, winding opposite ways, each with
    # a tongue springing back over its own coil.
    for fx, sign in [(0.25, 1), (0.75, -1)]:
        x, y = W * fx, vine_y(W * fx)
        paths.append(volute(x, y, 26.0, sign))
        paths.append(leaf(x - sign * 30, y - sign * 30, x - sign * 8, y - sign * 6, 6.5))

    # Counter-coils where the vine crosses its midline.  0.0 and 1.0 are the
    # same coil seen from either side of the seam.
    for fx, sign in [(0.0, -1), (0.5, 1), (1.0, -1)]:
        x, y = W * fx, vine_y(W * fx)
        paths.append(volute(x, y, 15.0, sign, turns=2.0))

    # Ground: a tongue and a small curl in each field the vine leaves open,
    # above the troughs and below the crests.
    for fx, sign in [(0.13, -1), (0.38, 1), (0.63, 1), (0.88, -1)]:
        x, y = W * fx, vine_y(W * fx)
        paths.append(leaf(x, y + sign * 42, x, y + sign * 20, 5.0))
        paths.append(volute(x + 13, y + sign * 30, 8.5, sign, turns=1.75))

    return paths


def build_svg(stroke="currentColor", width=2.3):
    """The tile.

    Defaults to currentColor so the same file can be used in an <img> or
    inlined; the CSS background copy is written with a literal colour, since a
    background image has no colour to inherit.
    """
    body = "".join('<path d="%s"/>' % p for p in build_paths())
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %s %s" '
            'width="%s" height="%s" role="img" '
            'aria-label="Foliate scrollwork band">'
            '<g fill="none" stroke="%s" stroke-width="%s" stroke-linecap="round" '
            'stroke-linejoin="round">%s</g></svg>'
            % (fmt(W), fmt(H), fmt(W), fmt(H), stroke, fmt(width), body))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--outdir", default="docs/assets",
                    help="where to write scroll.svg (default: docs/assets)")
    ap.add_argument("--stroke", default="currentColor",
                    help="stroke colour (default: currentColor)")
    ap.add_argument("--stroke-width", type=float, default=2.3)
    ap.add_argument("--print-uri", action="store_true",
                    help="print the URL-encoded data URI for styles.css")
    args = ap.parse_args()

    svg = build_svg(args.stroke, args.stroke_width)
    os.makedirs(args.outdir, exist_ok=True)
    path = os.path.join(args.outdir, "scroll.svg")
    with open(path, "w") as fh:
        fh.write(svg + "\n")
    print("wrote %s (%d bytes)" % (path, len(svg)))

    if args.print_uri:
        # Only the characters that actually break inside a CSS url("...").
        enc = (svg.replace("%", "%25").replace('"', "%22")
                  .replace("#", "%23").replace("<", "%3C").replace(">", "%3E"))
        print('url("data:image/svg+xml,%s")' % enc)


if __name__ == "__main__":
    main()
