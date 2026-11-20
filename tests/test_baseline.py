import math
import unittest

from src.baseline import (
    estimate_baselines,
    mean_baseline,
    median_baseline,
    trimmed_mean_baseline,
)
from src.synthetic import baseline_region


class TestBaselineEstimators(unittest.TestCase):
    def test_constant_region_recovers_known_baseline(self):
        samples = baseline_region(baseline=0.5)

        estimates = estimate_baselines(samples)

        self.assertEqual(
            estimates,
            {"mean": 0.5, "median": 0.5, "trimmed_mean": 0.5},
        )

    def test_median_uses_two_central_values_for_even_sample_count(self):
        self.assertEqual(median_baseline([1.0, 2.0, 10.0, 20.0]), 6.0)

    def test_ten_percent_trim_removes_five_values_per_side(self):
        central = [2.0] * 40
        samples = [-100.0] * 5 + central + [100.0] * 5

        self.assertEqual(trimmed_mean_baseline(samples), 2.0)

    def test_outliers_expose_expected_difference_between_methods(self):
        samples = baseline_region(
            baseline=0.5,
            outliers={0: 10.0, 1: -8.0},
        )

        estimates = estimate_baselines(samples)

        self.assertAlmostEqual(estimates["median"], 0.5)
        self.assertAlmostEqual(estimates["trimmed_mean"], 0.5)
        self.assertNotAlmostEqual(estimates["mean"], 0.5)

    def test_symmetric_drift_is_centered_on_known_baseline(self):
        samples = baseline_region(baseline=0.25, drift_per_sample=0.002)

        estimates = estimate_baselines(samples)

        for estimate in estimates.values():
            self.assertAlmostEqual(estimate, 0.25)

    def test_seed_makes_noise_reproducible(self):
        first = baseline_region(baseline=0.0, noise_sigma=0.01, seed=17)
        second = baseline_region(baseline=0.0, noise_sigma=0.01, seed=17)

        self.assertEqual(first, second)

    def test_invalid_samples_are_rejected(self):
        for samples in ([], [1.0, math.nan], [1.0, math.inf]):
            with self.subTest(samples=samples):
                with self.assertRaises(ValueError):
                    mean_baseline(samples)

    def test_invalid_trim_fraction_is_rejected(self):
        for fraction in (-0.1, 0.5, math.nan):
            with self.subTest(fraction=fraction):
                with self.assertRaises(ValueError):
                    trimmed_mean_baseline([1.0, 2.0], trim_fraction=fraction)


if __name__ == "__main__":
    unittest.main()

