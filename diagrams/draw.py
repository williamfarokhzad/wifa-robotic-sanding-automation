"""Regenerate the two editable SVG geometry figures from the example values."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from sanding_coverage import analyze


def panel(case, name, zoom=False):
    result = analyze(case)
    length, width = case["length_mm"], case["width_mm"]
    end, side = case["end_inset_mm"], case["side_inset_mm"]
    radius, pitch = case["pad_diameter_mm"] / 2, result["pitch_mm"]
    s, x0, y0 = (8, 58, 104) if zoom else (4, 70, 100)
    max_x, max_y = (60, 31) if zoom else (length, width)
    x, y = lambda u: x0 + s * u, lambda v: y0 + s * v
    lines = [(x(end), y(side + i * pitch), x(length - end))
             for i in range(result["passes"])]
    d = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="640" height="480" viewBox="0 0 640 480">',
        '<rect width="640" height="480" rx="18" fill="#edf7f4"/>',
        '<g font-family="DejaVu Sans,sans-serif" fill="#123834">',
        f'<text x="26" y="45" font-size="29" font-weight="bold">{name}</text>',
        '<text x="26" y="76" font-size="20">Top view · dimensions in millimetres</text>',
        f'<clipPath id="plate"><rect x="{x0}" y="{y0}" width="{max_x*s}" height="{max_y*s}"/></clipPath>',
        f'<rect x="{x0}" y="{y0}" width="{max_x*s}" height="{max_y*s}" fill="#ffdab8"/>',
        '<g clip-path="url(#plate)">',
    ]
    for a, b, c in lines:
        d.append(f'<path d="M {a} {b} H {c}" stroke="#83cdb9" stroke-width="{2*radius*s}" stroke-linecap="round"/>')
    for a, b, c in lines:
        d.append(f'<path d="M {a} {b} H {c}" stroke="#235b52" stroke-width="3" stroke-dasharray="8 5"/>')
    d += ['</g>',
          f'<path d="M {x0} {y(max_y)} V {y0} H {x(max_x)}" fill="none" stroke="#123834" stroke-width="3"/>']
    if zoom:
        a, b, _ = lines[0]
        d += [f'<path d="M {a} {b} L {x0} {y0}" stroke="#692131" stroke-width="4"/>',
              f'<circle cx="{a}" cy="{b}" r="6" fill="#692131"/>',
              f'<circle cx="{x0}" cy="{y0}" r="6" fill="#692131"/>',
              '<text x="238" y="167" font-size="21">Pad center at pass start</text>',
              f'<path d="M 231 170 L {a+8} {b-8}" stroke="#123834" stroke-width="2"/>',
              '<text x="62" y="382" font-size="21">Corner is 21.63 mm from the nearest center.</text>',
              '<text x="62" y="415" font-size="21">The pad radius is 20 mm.</text>',
              '<text x="62" y="447" font-size="20">Orange: uncovered plate</text>']
    else:
        d += [f'<path d="M {x0} {y(max_y)} H {x(max_x)} V {y0}" fill="none" stroke="#123834" stroke-width="3"/>',
              '<text x="74" y="454" font-size="21">Green: swept pad · Dashed: center passes</text>']
    d += ['</g>', '</svg>']
    return '\n'.join(d) + '\n'


for case, title, dest, zoom in [
    ("covered", "Four passes cover the plate", "sanding-raster-coverage", False),
    ("missed-corners", "Overlap can still miss a corner", "sanding-corner-gap", True),
]:
    spec = json.loads((HERE.parent / "examples" / (case + ".json")).read_text())
    (HERE / (dest + ".svg")).write_text(panel(spec, title, zoom), encoding="utf-8")
