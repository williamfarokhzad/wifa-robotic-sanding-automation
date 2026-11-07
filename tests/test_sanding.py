import json
import math
from pathlib import Path
import subprocess
import sys
import unittest

from sanding_coverage import analyze

ROOT = Path(__file__).resolve().parents[1]


def read_case(name):
    return json.loads((ROOT / "examples" / (name + ".json")).read_text(encoding="utf-8"))


class CoverageTests(unittest.TestCase):
    def test_known_safe_geometry(self):
        result = analyze(read_case("covered"))
        self.assertEqual(result["passes"], 4)
        self.assertEqual(result["pitch_mm"], 20)
        self.assertAlmostEqual(result["clearance_mm"], 20 - math.sqrt(164))
        self.assertEqual(result["covered_samples"], 600)
        self.assertTrue(result["full_coverage_ideal"])

    def test_corner_requires_radial_distance(self):
        result = analyze(read_case("missed-corners"))
        self.assertGreater(result["interior_overlap_percent"], 50)
        self.assertAlmostEqual(result["worst_distance_mm"], math.sqrt(18**2 + 12**2))
        self.assertEqual(result["witness_mm"], [0, 0])
        self.assertLess(result["covered_samples"], result["total_samples"])
        self.assertFalse(result["full_coverage_ideal"])

    def test_closed_pad_touches_exact_boundary(self):
        case = read_case("covered") | {"length_mm": 20, "width_mm": 8,
                                     "end_inset_mm": 3, "side_inset_mm": 0,
                                     "pad_diameter_mm": 10, "max_pitch_mm": 8}
        result = analyze(case)
        self.assertEqual(result["witness_mm"], [0, 4])
        self.assertEqual(result["clearance_mm"], 0)
        self.assertTrue(result["full_coverage_ideal"])
        self.assertFalse(analyze(case | {"pad_diameter_mm": 9.99})["full_coverage_ideal"])

    def test_gap_witness_and_sample_count(self):
        result = analyze(read_case("missed-stripes"))
        self.assertEqual(result["witness_mm"], [0, 20])
        self.assertEqual(result["clearance_mm"], -6)
        self.assertEqual(result["covered_samples"], 480)

    def test_sampling_can_miss_a_real_gap(self):
        result = analyze(read_case("sampling-blind-spot"))
        self.assertEqual(result["sample_coverage_percent"], 100)
        self.assertFalse(result["full_coverage_ideal"])

    def test_samples_against_exhaustive_segment_projection(self):
        case = read_case("missed-corners")
        lines = [(18, y, 102) for y in (12, 92 / 3, 148 / 3, 68)]
        hits = 0
        for ix in range(120):
            for iy in range(80):
                x, y = ix + 0.5, iy + 0.5
                distances = []
                for start, center, stop in lines:
                    t = max(0, min(1, (x - start) / (stop - start)))
                    distances.append((x - (start + t * (stop - start)))**2 + (y - center)**2)
                hits += min(distances) <= 400
        self.assertEqual(analyze(case)["covered_samples"], hits)

    def test_bad_inputs_fail_before_sampling(self):
        case = read_case("covered")
        for update in [{"pad_diameter_mm": True}, {"pad_diameter_mm": float("nan")},
                       {"sample_step_mm": 0.001}, {"max_pitch_mm": 0.001},
                       {"end_inset_mm": 60}, {"side_inset_mm": -1}, {"meters": 1}]:
            with self.subTest(update=update), self.assertRaises(ValueError):
                analyze(case | update)

    def test_cli_stdout_is_machine_readable(self):
        result = subprocess.run([sys.executable, str(ROOT / "sanding_coverage.py"),
                                 str(ROOT / "examples/missed-stripes.json")],
                                text=True, capture_output=True, check=True)
        self.assertFalse(result.stderr)
        self.assertEqual(json.loads(result.stdout)["sample_coverage_percent"], 80)

    def test_cli_reports_missing_input(self):
        result = subprocess.run([sys.executable, str(ROOT / "sanding_coverage.py"),
                                 str(ROOT / "examples/absent.json")],
                                text=True, capture_output=True)
        self.assertEqual(result.returncode, 2)
        self.assertTrue(result.stderr.startswith("error:"))
        self.assertEqual(result.stdout, "")


if __name__ == "__main__":
    unittest.main()
