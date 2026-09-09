#!/usr/bin/env python3
"""Production generator for the teardrop logo.

Supersedes teardrop_logo.py, centre_variants.py and ring_studies.py: this is
the one to keep.  Four parameters - N, k, style, size - and it emits ready SVGs
(optionally PNGs) with the ring geometry optically compensated for the size
requested.


Geometry
--------
One teardrop is a circle (the bulb) plus an apex, joined by the two tangent
lines from apex to circle.  With apex T = (0,0), bulb centre C = (0,L) and bulb
radius R, a radius meets its tangent at a right angle, so triangle T-P-C is
right-angled at P and the tangent points are

    cos(alpha) = R / L
    P = C + R * (+-sin(alpha), -cos(alpha))

The outline runs T -> P_right -> major arc round the bulb -> P_left -> T.  N of
these are rotated about the origin so their apexes converge at the centre; a
180 degree phase puts one petal at 12 o'clock.


k - lobe fatness
----------------
k = R / L is the only proportion that matters.  It sets how much of the disc is
positive space:

    petal angle = 2 * asin(k)
    gap between neighbours = 360/N - 2 * asin(k)
    ceiling: petals collide at k = sin(180/N)

The ceiling is 0.707 at N=4 but only 0.588 at N=5, so the *same* k is a far more
aggressive setting at five petals than at four.  What travels between counts is
the fraction of the ceiling used, not k itself - both of the settings we landed
on sit near 71%:

    N=4, k=0.50  ->  30.0 deg gap, 71% of ceiling
    N=5, k=0.42  ->  22.3 deg gap, 71% of ceiling

Outer extent is held at EXT regardless of k (L + R = EXT), so changing fatness
never changes the footprint.


Styles
------
ring        gold ring struck across the petals
gapped-ring
            ring with an isolation void masked out of the petals either
            side of the stroke, so the ring sits in its own clearance rather
            than lying on the teal.  Strongest at every size we tested.
bindu       a gold centre disc and no ring at all: the petals converge on the
            dot itself.
ring+bindu  ring plus a gold centre disc.  Needs k >= ~0.5 to breathe:
            at lower k the ring and the bindu crowd each other.
gapped-ring+bindu
            the isolation void of `gapped-ring` with the bindu sitting
            in the cleared centre.  The two fix different failures and the
            combination is the one that survives furthest down: the void keeps
            the ring off the teal, while the bindu reoccupies the centre the
            void empties.  Without it, at low N and small sizes the void severs
            the petal tips and leaves them floating (see MAX_VOID_FRAC).


Optical compensation
--------------------
A logo scaled linearly fails small.  At 512px the ring stroke is ~24 device
pixels; the same geometry at 24px leaves it near 1.1, and the isolation gap at
0.3 - both below the threshold where a renderer can show them honestly.  So
stroke, gap and bindu are each given a floor in *device* pixels and converted
back into user units for the size being emitted:

    raw_per_device_px = 2 * EXT * PAD / size_px
    stroke = max(base_fraction * EXT, MIN_STROKE_PX * raw_per_device_px)

This means small sizes are deliberately NOT scaled-down copies of large ones -
they are their own optical size, with proportionally heavier ring furniture.
That is intended.  The void is additionally capped at MAX_VOID_FRAC of the
extent, because an unbounded gap eventually severs each petal into an inner nub
and an outer blob; --report tells you when the cap or a floor has bitten.


Usage
-----
    python3 generate_logo.py --n 5 --k 0.42 --style gapped-ring
    python3 generate_logo.py --n 4 --k 0.50 --style ring+bindu --sizes 512 128 32
    python3 generate_logo.py --n 4 --k 0.50 --style gapped-ring --png --report
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

# ------------------------------------------------------------------ constants
EXT = 130.0                 # outer extent of the logo, in user units
PAD = 1.08                  # viewBox breathing room around EXT

TEAL = "#0F766E"
GOLD = "#C89B3C"

# ring furniture, as fractions of EXT - the large-size proportions
RING_R_FRAC = 0.380
RING_W_FRAC = 0.100
ISO_GAP_FRAC = 0.027
BINDU_R_FRAC = 0.105

# optical floors, in device pixels at the size being emitted
MIN_STROKE_PX = 1.75
MIN_GAP_PX = 1.00
MIN_BINDU_R_PX = 2.00
MAX_VOID_FRAC = 0.32        # cap on (stroke + 2*gap) as a fraction of EXT

PHASE = 180.0               # one petal at 12 o'clock
STYLES = ("ring", "gapped-ring", "bindu",
          "ring+bindu", "gapped-ring+bindu")
DEFAULT_SIZES = (512, 128, 48, 24)


# ------------------------------------------------------------------- geometry
def geom(k: float) -> tuple[float, float]:
    """Bulb radius and apex distance for fatness k, with L + R held at EXT."""
    if not 0.0 < k < 1.0:
        raise ValueError("k must lie in (0, 1)")
    apex_distance = EXT / (1.0 + k)
    return EXT - apex_distance, apex_distance


def ceiling_k(n: int) -> float:
    """Fatness at which neighbouring petals would just touch."""
    return math.sin(math.pi / n)


def gap_degrees(k: float, n: int) -> float:
    """Angular clearance between neighbouring petals; <= 0 means collision."""
    return 360.0 / n - 2.0 * math.degrees(math.asin(k))


def teardrop_path(radius: float, apex_distance: float) -> str:
    """Path data for one teardrop: apex at (0,0), bulb centre at (0, L)."""
    cos_a = radius / apex_distance
    sin_a = math.sqrt(1.0 - cos_a * cos_a)
    px = radius * sin_a
    py = apex_distance - radius * cos_a
    # major arc (large-arc-flag 1), clockwise in SVG's y-down frame (sweep 1)
    return (f"M 0,0 L {px:.4f},{py:.4f} "
            f"A {radius:.4f},{radius:.4f} 0 1,1 {-px:.4f},{py:.4f} Z")


def petals(n: int, k: float) -> str:
    radius, apex_distance = geom(k)
    drop = teardrop_path(radius, apex_distance)
    body = "".join(
        f'<path d="{drop}" transform="rotate({PHASE + i * 360 / n:.4f})" />'
        for i in range(n)
    )
    return f'<g fill="{TEAL}">{body}</g>'


# ------------------------------------------------------- optical compensation
def optical(size_px: int) -> dict:
    """Ring furniture in user units, floored for the given output size.

    Returns the resolved dimensions plus flags recording which floors or caps
    were applied, so --report can explain any departure from pure scaling.
    """
    raw_per_px = 2.0 * EXT * PAD / size_px

    base_stroke = RING_W_FRAC * EXT
    base_gap = ISO_GAP_FRAC * EXT
    base_bindu = BINDU_R_FRAC * EXT

    stroke = max(base_stroke, MIN_STROKE_PX * raw_per_px)
    gap = max(base_gap, MIN_GAP_PX * raw_per_px)
    bindu = max(base_bindu, MIN_BINDU_R_PX * raw_per_px)

    # keep the void from eating the petals in half
    void_cap = MAX_VOID_FRAC * EXT
    capped = stroke + 2.0 * gap > void_cap
    if capped:
        gap = max(0.0, (void_cap - stroke) / 2.0)

    return {
        "raw_per_px": raw_per_px,
        "ring_r": RING_R_FRAC * EXT,
        "stroke": stroke,
        "gap": gap,
        "bindu": bindu,
        "stroke_px": stroke / raw_per_px,
        "gap_px": gap / raw_per_px,
        "bindu_px": bindu / raw_per_px,
        "stroke_floored": stroke > base_stroke + 1e-9,
        "gap_floored": gap > base_gap + 1e-9,
        "bindu_floored": bindu > base_bindu + 1e-9,
        "void_capped": capped,
    }


# --------------------------------------------------------------------- render
def render(n: int, k: float, style: str, size_px: int, uid: str = "r") -> str:
    """A complete standalone SVG for one logo at one optical size."""
    if style not in STYLES:
        raise ValueError(f"unknown style {style!r}; choose from {STYLES}")
    if k >= ceiling_k(n):
        raise ValueError(
            f"k={k} is at or past the N={n} ceiling of {ceiling_k(n):.3f}; "
            "the petals would collide")

    o = optical(size_px)
    half = EXT * PAD
    ring = (f'<circle r="{o["ring_r"]:.4f}" fill="none" stroke="{GOLD}" '
            f'stroke-width="{o["stroke"]:.4f}" />')

    bindu = f'<circle r="{o["bindu"]:.4f}" fill="{GOLD}" />'

    if style.startswith("gapped-ring"):
        # petals masked by a void concentric with the ring, so the stroke sits
        # in its own clearance instead of on the teal
        void = o["stroke"] + 2.0 * o["gap"]
        cut = (
            f'<mask id="cut-{uid}" maskUnits="userSpaceOnUse" '
            f'x="{-EXT}" y="{-EXT}" width="{2 * EXT}" height="{2 * EXT}">'
            f'<rect x="{-EXT}" y="{-EXT}" width="{2 * EXT}" height="{2 * EXT}" '
            f'fill="white" />'
            f'<circle r="{o["ring_r"]:.4f}" fill="none" stroke="black" '
            f'stroke-width="{void:.4f}" /></mask>'
        )
        body = f'{cut}<g mask="url(#cut-{uid})">{petals(n, k)}</g>{ring}'
    elif style == "bindu":
        # no ring at all: the petals converge on the dot itself. The bindu is
        # the only gold, so it carries the centre unaided.
        body = petals(n, k)
    else:
        body = petals(n, k) + ring

    if style.endswith("bindu"):
        # drawn last: the bindu is unmasked, so it holds the centre the void
        # would otherwise leave empty
        body += bindu

    return (f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'viewBox="{-half:.3f} {-half:.3f} {2 * half:.3f} {2 * half:.3f}" '
            f'width="{size_px}" height="{size_px}" role="img" '
            f'aria-label="{n}-fold teardrop logo">\n'
            f'  <title>{n} teardrops, points in, {style}, k={k:.2f}, '
            f'{size_px}px</title>\n  {body}\n</svg>\n')


# ------------------------------------------------------------------ reporting
def report(n: int, k: float, sizes) -> None:
    ceil = ceiling_k(n)
    print(f"N={n}  k={k:.3f}  ({k / ceil:.0%} of the {ceil:.3f} ceiling)")
    print(f"  petal angle {2 * math.degrees(math.asin(k)):.1f} deg, "
          f"gap {gap_degrees(k, n):.1f} deg")
    print(f"  {'size':>6}  {'stroke':>7}  {'gap':>6}  {'bindu r':>8}   notes")
    for px in sizes:
        o = optical(px)
        notes = ", ".join(
            label for flag, label in (
                (o["stroke_floored"], "stroke floored"),
                (o["gap_floored"], "gap floored"),
                (o["bindu_floored"], "bindu floored"),
                (o["void_capped"], "void capped"),
            ) if flag) or "pure scaling"
        print(f"  {px:>5}px  {o['stroke_px']:>6.2f}p  {o['gap_px']:>5.2f}p  "
              f"{o['bindu_px']:>7.2f}p   {notes}")


# ----------------------------------------------------------------------- main
def main() -> None:
    ap = argparse.ArgumentParser(
        description="Generate the teardrop logo.",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--n", type=int, default=5, help="number of teardrops")
    ap.add_argument("--k", type=float, default=0.42, help="lobe fatness R/L")
    ap.add_argument("--style", choices=STYLES, default="gapped-ring")
    ap.add_argument("--sizes", type=int, nargs="+", default=list(DEFAULT_SIZES),
                    help="output sizes in px, e.g. 512 128 48 24")
    ap.add_argument("--outdir", default=str(Path(__file__).parent / "logo-out"),
                    help="where to write the SVGs (default: logo-out/ beside "
                         "this script)")
    ap.add_argument("--png", action="store_true",
                    help="also rasterise each size (needs cairosvg)")
    ap.add_argument("--report", action="store_true",
                    help="print the resolved optical dimensions")
    args = ap.parse_args()

    if args.k >= ceiling_k(args.n):
        sys.exit(f"error: k={args.k} meets the N={args.n} ceiling "
                 f"{ceiling_k(args.n):.3f}; petals would collide")
    if (args.style.endswith("bindu") and args.style != "bindu"
            and args.k < 0.48):
        print(f"note: {args.style} crowds below k~0.48 (you gave {args.k:.2f}); "
              "the ring and the bindu will compete", file=sys.stderr)

    out = Path(args.outdir)
    out.mkdir(parents=True, exist_ok=True)
    slug = f"teardrop-n{args.n}-k{args.k:.2f}-{args.style.replace('+', '-')}"

    for px in args.sizes:
        svg_path = out / f"{slug}-{px}.svg"
        svg_path.write_text(render(args.n, args.k, args.style, px,
                                   uid=f"{slug}-{px}"))
        print(f"wrote {svg_path}")
        if args.png:
            try:
                import cairosvg
            except ImportError:
                print("  (png skipped: pip install cairosvg)", file=sys.stderr)
                continue
            png_path = out / f"{slug}-{px}.png"
            cairosvg.svg2png(url=str(svg_path), write_to=str(png_path),
                             output_width=px, output_height=px)
            print(f"wrote {png_path}")

    if args.report:
        report(args.n, args.k, args.sizes)


if __name__ == "__main__":
    main()
