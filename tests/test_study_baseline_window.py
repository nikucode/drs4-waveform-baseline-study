import json
import tempfile
import unittest
from pathlib import Path

from analysis.study_baseline_window import (
    WindowStudyConfig,
    aggregate_rows,
    generate_rows,
    run_study,
)


class TestBaselineWindowStudy(unittest.TestCase):
    def setUp(self):
        self.config = WindowStudyConfig(
            baseline_windows=(20, 50),
            amplitudes=(0.5,),
            noise_sigmas=(0.0,),
            outlier_scenarios=("none",),
            trials=2,
        )

    def test_same_events_are_reused_across_windows_and_methods(self):
        rows = generate_rows(self.config)

        self.assertEqual(len(rows), 12)
        for event_id in (0, 1):
            event = [row for row in rows if row["event_id"] == event_id]
            combinations = {
                (row["baseline_window"], row["method"]) for row in event
            }
            self.assertEqual(len(combinations), 6)
            self.assertEqual({row["seed"] for row in event}, {20261121 + event_id})

    def test_clean_noiseless_baseline_is_exact_for_every_window(self):
        rows = generate_rows(self.config)

        self.assertTrue(all(row["baseline_error"] == 0.0 for row in rows))
        self.assertTrue(all(row["amplitude_error"] == 0.0 for row in rows))
        self.assertTrue(all(row["signed_area_error"] == 0.0 for row in rows))

    def test_summary_keeps_window_and_method_separate(self):
        summary = aggregate_rows(generate_rows(self.config))

        self.assertEqual(len(summary), 6)
        self.assertTrue(all(row["events"] == 2 for row in summary))

    def test_run_writes_tables_and_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            counts = run_study(output, self.config)
            manifest = json.loads((output / "manifest.json").read_text())

            self.assertEqual(counts, (12, 6))
            self.assertTrue((output / "event_results.csv").is_file())
            self.assertTrue((output / "summary.csv").is_file())
            self.assertIn(
                "docs/estudio_longitud_ventana.md",
                manifest["files"],
            )


if __name__ == "__main__":
    unittest.main()
