"""Geometry only: finite horizontal line segments swept by a circular pad."""
import argparse
import json
import math
from pathlib import Path

FIELDS = {
    "length_mm", "width_mm", "pad_diameter_mm", "max_pitch_mm",
    "end_inset_mm", "side_inset_mm", "sample_step_mm",
}


def check(spec):
    if not isinstance(spec, dict) or spec.keys() != FIELDS:
        raise ValueError("provide exactly the seven fields in the example JSON")
    for key, value in spec.items():
        if (type(value) not in (float, int) or not 0 <= value <= 100_000
                or (value < 0.001 and (value or key not in {"end_inset_mm", "side_inset_mm"}))):
            raise ValueError(f"{key} must be between 0.001 and 100000 mm, or zero for an inset")
    if 2 * spec["end_inset_mm"] >= spec["length_mm"]:
        raise ValueError("end insets must leave a positive line length")
    if 2 * spec["side_inset_mm"] >= spec["width_mm"]:
        raise ValueError("side insets must leave positive space between first and last rows")


def bounded_count(span, step, limit, field):
    ratio = span / step
    if not math.isfinite(ratio) or ratio > limit:
        raise ValueError(f"{field} would create too many lines or samples")
    return max(1, math.ceil(ratio))


def analyze(spec):
    check(spec)
    length, width = spec["length_mm"], spec["width_mm"]
    end, side = spec["end_inset_mm"], spec["side_inset_mm"]
    radius = spec["pad_diameter_mm"] / 2
    if radius == 0:
        raise ValueError("pad diameter is too small to represent its radius")
    span = width - 2 * side
    gaps = bounded_count(span, spec["max_pitch_mm"], 10_000, "max_pitch_mm")
    pitch = span / gaps
    if pitch == 0:
        raise ValueError("pitch is too small to represent")
    worst_y = max(side, pitch / 2)
    worst = math.hypot(end, worst_y)

    nx = bounded_count(length, spec["sample_step_mm"], 1_000_000, "sample_step_mm")
    ny = bounded_count(width, spec["sample_step_mm"], 1_000_000, "sample_step_mm")
    if nx * ny > 1_000_000:
        raise ValueError("sample_step_mm would create over one million samples")
    # Midpoints of equal cells. A row is never considered infinite along x.
    xs = [length * (i + 0.5) / nx for i in range(nx)]
    dxs = [max(0.0, end - x, x - (length - end)) for x in xs]
    hits = 0
    for i in range(ny):
        y = width * (i + 0.5) / ny
        row = min(gaps, max(0, round((y - side) / pitch)))
        dy = abs(y - (side + row * pitch))
        hits += sum(math.hypot(dx, dy) <= radius for dx in dxs)

    return {
        "passes": gaps + 1,
        "pitch_mm": pitch,
        "interior_overlap_percent": 100 * (1 - pitch / (2 * radius)),
        "worst_distance_mm": worst,
        "clearance_mm": radius - worst,
        "full_coverage_ideal": worst <= radius,
        "witness_mm": [0.0, 0 if side >= pitch / 2 else side + pitch / 2],
        "covered_samples": hits,
        "total_samples": nx * ny,
        "sample_coverage_percent": 100 * hits / (nx * ny),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case", type=Path)
    args = parser.parse_args()
    try:
        result = analyze(json.loads(args.case.read_text(encoding="utf-8")))
        print(json.dumps(result, indent=2, allow_nan=False))
    except (OSError, ValueError, OverflowError) as exc:
        parser.exit(2, f"error: {exc}\n")


if __name__ == "__main__":
    main()
