import unittest

from analysis.report_synthetic_results import count_lowest_baseline_mae


class TestSyntheticReport(unittest.TestCase):
    def test_minimum_count_preserves_ties(self):
        rows = [
            {
                "amplitude_true": 1.0,
                "noise_sigma": 0.0,
                "drift_per_sample": 0.0,
                "outlier_scenario": "none",
                "method": method,
                "baseline_mae": error,
            }
            for method, error in (
                ("mean", 0.1),
                ("median", 0.05),
                ("trimmed_mean", 0.05),
            )
        ]

        counts = count_lowest_baseline_mae(rows)

        self.assertEqual(counts[("median", "trimmed_mean")], 1)


if __name__ == "__main__":
    unittest.main()
