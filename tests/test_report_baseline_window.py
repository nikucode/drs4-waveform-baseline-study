import tempfile
import unittest
from pathlib import Path

from analysis.report_baseline_window import (
    expected_mean_outlier_bias,
    expected_mean_rmse,
    publish,
)
from analysis.study_baseline_window import WindowStudyConfig, run_study


class TestBaselineWindowReport(unittest.TestCase):
    def test_expected_mean_rmse(self):
        self.assertAlmostEqual(expected_mean_rmse(0.02, 100), 0.002)
        with self.assertRaises(ValueError):
            expected_mean_rmse(0.02, 0)

    def test_expected_outlier_bias(self):
        self.assertAlmostEqual(expected_mean_outlier_bias(0.50, 20), 0.025)
        with self.assertRaises(ValueError):
            expected_mean_outlier_bias(0.50, 0)

    def test_publish_writes_public_artifacts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            results = root / "results"
            artifacts = root / "artifacts"
            config = WindowStudyConfig(
                baseline_windows=(20,), amplitudes=(1.0,),
                noise_sigmas=(0.005, 0.020),
                outlier_scenarios=("none", "positive_spike"), trials=2,
            )
            run_study(results, config)
            publish(results / "summary.csv", results / "manifest.json", artifacts)

            self.assertTrue((artifacts / "report.md").is_file())
            self.assertTrue((artifacts / "baseline_rmse_vs_window.png").is_file())
            self.assertTrue((artifacts / "positive_spike_bias_vs_window.png").is_file())
            self.assertTrue((artifacts / "summary.csv").is_file())
            self.assertTrue((artifacts / "manifest.json").is_file())


if __name__ == "__main__":
    unittest.main()
