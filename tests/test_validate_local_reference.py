import math
import unittest

from analysis.validate_local_reference import validate_reference


class TestLocalReferenceValidation(unittest.TestCase):
    def test_equivalent_and_normalized_fields_are_separated(self):
        reference_noise = 2.0
        factor = math.sqrt(49 / 50)
        reference = {
            "file": "sample.xml",
            "serial": "1",
            "board": "3085",
            "channel": "CHN1",
            "baseline_mv": "0.5",
            "baseline_rms_mv": str(reference_noise),
            "peak_mv": "10.0",
            "peak_time_ns": "75.0",
            "snr": "5.0",
            "signed_area_mv_ns": "100.0",
            "positive_area_mv_ns": "110.0",
            "rise_time_10_90_ns": "5.0",
            "fwhm_ns": "12.0",
            "saturation_samples": "0",
            "detected_5sigma": "1",
        }
        own = {
            "source": "sample.xml",
            "serial": "1",
            "board": "3085",
            "channel": "CHN1",
            "method": "mean",
            "baseline": "0.5",
            "noise_rms": str(reference_noise * factor),
            "amplitude": "10.0",
            "snr": str(5.0 / factor),
            "signed_area": "100.0",
            "positive_area": "110.0",
            "peak_time": "75.0",
            "rise_time_10_90": "5.0",
            "fwhm": "12.5",
            "saturated_samples": "0",
            "detected": "True",
        }

        report = validate_reference([own], [reference])

        self.assertEqual(report["matched_rows"], 1)
        self.assertEqual(
            report["equivalent_fields"]["baseline"][
                "differences_above_tolerance"
            ],
            0,
        )
        self.assertAlmostEqual(
            report["known_normalization_difference"][
                "noise_max_absolute_residual"
            ],
            0.0,
        )
        self.assertEqual(
            report["definition_dependent_fields"]["fwhm"][
                "differences_above_tolerance"
            ],
            1,
        )

    def test_rejects_nonmatching_event_keys(self):
        own = [
            {
                "method": "mean",
                "source": "a",
                "serial": "1",
                "board": "1",
                "channel": "C",
            }
        ]
        reference = [
            {
                "file": "b",
                "serial": "1",
                "board": "1",
                "channel": "C",
            }
        ]

        with self.assertRaises(ValueError):
            validate_reference(own, reference)


if __name__ == "__main__":
    unittest.main()
