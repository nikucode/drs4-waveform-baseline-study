import json
import tempfile
import unittest
from pathlib import Path

from analysis.study_baseline_sensitivity import (
    StudyConfig,
    aggregate_rows,
    generate_event_rows,
    run_study,
)


class TestBaselineSensitivityStudy(unittest.TestCase):
    def setUp(self):
        self.config = StudyConfig(
            amplitudes=(0.5,),
            noise_sigmas=(0.0,),
            drift_per_samples=(0.0,),
            outlier_scenarios=("none",),
            trials=2,
        )

    def test_every_event_has_all_three_paired_methods(self):
        rows = generate_event_rows(self.config)

        self.assertEqual(len(rows), 6)
        for event_id in (0, 1):
            methods = {
                row["method"] for row in rows if row["event_id"] == event_id
            }
            self.assertEqual(methods, {"mean", "median", "trimmed_mean"})

    def test_clean_noiseless_signal_has_zero_baseline_error(self):
        rows = generate_event_rows(self.config)

        self.assertTrue(all(row["baseline_error"] == 0.0 for row in rows))
        self.assertTrue(all(row["amplitude_error"] == 0.0 for row in rows))
        self.assertTrue(all(row["signed_area_error"] == 0.0 for row in rows))

    def test_summary_keeps_conditions_and_methods_separate(self):
        rows = generate_event_rows(self.config)
        summary = aggregate_rows(rows)

        self.assertEqual(len(summary), 3)
        self.assertTrue(all(row["events"] == 2 for row in summary))

    def test_run_writes_manifest_and_both_tables(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            counts = run_study(output, self.config)
            manifest = json.loads((output / "manifest.json").read_text())

            self.assertEqual(counts, (6, 3))
            self.assertTrue((output / "event_results.csv").is_file())
            self.assertTrue((output / "summary.csv").is_file())
            self.assertEqual(manifest["outputs"]["event_rows"], 6)
            self.assertIn("src/features.py", manifest["files"])


if __name__ == "__main__":
    unittest.main()
