import unittest

from src.features import compare_baseline_methods, extract_features
from src.synthetic import triangular_pulse_waveform


class TestWaveformFeatures(unittest.TestCase):
    def test_known_triangle_recovers_amplitude_area_and_times(self):
        times, voltages = triangular_pulse_waveform(
            baseline=0.5,
            amplitude=1.0,
            pulse_start=60,
            peak_index=70,
            pulse_end=90,
            sample_period=0.5,
        )

        features = extract_features(times, voltages, method="mean")

        self.assertEqual(features.baseline, 0.5)
        self.assertEqual(features.amplitude, 1.0)
        self.assertAlmostEqual(features.signed_area, 7.5)
        self.assertAlmostEqual(features.positive_area, 7.5)
        self.assertEqual(features.peak_time, 35.0)
        self.assertAlmostEqual(features.rise_time_10_90, 4.0)
        self.assertAlmostEqual(features.fwhm, 7.5)
        self.assertTrue(features.detected)

    def test_all_methods_receive_the_same_waveform(self):
        times, voltages = triangular_pulse_waveform(
            baseline=0.2,
            amplitude=0.8,
            noise_sigma=0.002,
            seed=12,
        )

        results = compare_baseline_methods(times, voltages)

        self.assertEqual(set(results), {"mean", "median", "trimmed_mean"})
        self.assertEqual(
            {result.peak_time for result in results.values()},
            {results["mean"].peak_time},
        )

    def test_baseline_outliers_propagate_to_amplitude_and_area(self):
        times, voltages = triangular_pulse_waveform(
            baseline=0.5,
            amplitude=1.0,
            baseline_outliers={0: 10.0, 1: -8.0},
        )

        results = compare_baseline_methods(times, voltages)

        self.assertAlmostEqual(results["median"].amplitude, 1.0)
        self.assertAlmostEqual(results["trimmed_mean"].amplitude, 1.0)
        self.assertNotAlmostEqual(results["mean"].amplitude, 1.0)
        self.assertNotAlmostEqual(
            results["mean"].signed_area,
            results["median"].signed_area,
        )

    def test_saturation_count_uses_explicit_adc_limits(self):
        times, voltages = triangular_pulse_waveform(
            baseline=0.0,
            amplitude=1.0,
        )

        features = extract_features(
            times,
            voltages,
            method="mean",
            adc_min=-1.0,
            adc_max=1.0,
        )

        self.assertEqual(features.saturated_samples, 1)

    def test_invalid_time_axis_is_rejected(self):
        with self.assertRaises(ValueError):
            extract_features(
                [0.0, 1.0, 1.0],
                [0.0, 0.0, 1.0],
                method="mean",
                baseline_samples=2,
            )


if __name__ == "__main__":
    unittest.main()
