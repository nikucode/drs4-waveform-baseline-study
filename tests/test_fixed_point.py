import unittest

from src.fixed_point import baseline_mean_u12


class TestBaselineMeanU12(unittest.TestCase):
    def test_zero_maximum_and_constant_inputs(self):
        self.assertEqual(baseline_mean_u12([0] * 50), 0)
        self.assertEqual(baseline_mean_u12([4095] * 50), 4095)
        self.assertEqual(baseline_mean_u12([1729] * 50), 1729)

    def test_integer_and_fractional_means(self):
        self.assertEqual(baseline_mean_u12([2] * 25 + [4] * 25), 3)
        self.assertEqual(baseline_mean_u12([1] * 24 + [0] * 26), 0)
        self.assertEqual(baseline_mean_u12([1] * 26 + [0] * 24), 1)

    def test_halfway_rounds_up(self):
        # Sumas 24, 25 y 26: medias 0,48; 0,50; 0,52.
        self.assertEqual(baseline_mean_u12([1] * 24 + [0] * 26), 0)
        self.assertEqual(baseline_mean_u12([1] * 25 + [0] * 25), 1)
        self.assertEqual(baseline_mean_u12([1] * 26 + [0] * 24), 1)

    def test_accumulator_limit_case(self):
        self.assertEqual(sum([4095] * 50), 204750)
        self.assertLess(204750, 2**18)

    def test_wrong_lengths_are_rejected(self):
        for values in ([], [0] * 49, [0] * 51):
            with self.subTest(length=len(values)):
                with self.assertRaises(ValueError):
                    baseline_mean_u12(values)

    def test_invalid_types_and_ranges_are_rejected(self):
        invalid = (True, 1.0, "1", None, -1, 4096)
        for value in invalid:
            values = [0] * 50
            values[17] = value
            with self.subTest(value=value):
                with self.assertRaises((TypeError, ValueError)):
                    baseline_mean_u12(values)
        with self.assertRaises(TypeError):
            baseline_mean_u12(None)

    def test_deterministic_and_does_not_mutate_input(self):
        values = list(range(50))
        before = values.copy()
        first = baseline_mean_u12(values)
        second = baseline_mean_u12(values)
        self.assertEqual(first, 25)  # suma 1225; (1225 + 25) // 50
        self.assertEqual(first, second)
        self.assertEqual(values, before)


if __name__ == "__main__":
    unittest.main()
