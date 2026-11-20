import tempfile
import unittest
from pathlib import Path

from analysis.study_local_drs4_baseline import (
    LocalStudyConfig,
    analyze_inputs,
    run_local_study,
)


def _synthetic_xml() -> str:
    data = []
    for index in range(120):
        if 60 <= index <= 70:
            pulse = (index - 60) / 10
        elif 70 < index <= 90:
            pulse = (90 - index) / 20
        else:
            pulse = 0.0
        data.append(f"<Data>{index:.1f},{0.5 + pulse:.6f}</Data>")
    return f"""<?xml version="1.0"?>
<DRSOSC><Event><Serial>1</Serial><Time>2026/11/20 12:00:00.000</Time>
<HUnit>ns</HUnit><VUnit>mV</VUnit><Board_3085>
<Trigger_Cell>10</Trigger_Cell><CHN1>{''.join(data)}</CHN1>
</Board_3085></Event></DRSOSC>"""


class TestLocalDRS4BaselineStudy(unittest.TestCase):
    def _input(self, directory: str) -> Path:
        path = Path(directory) / "synthetic.xml"
        path.write_text(_synthetic_xml(), encoding="utf-8")
        return path

    def test_clean_waveform_produces_three_methods_and_pairs(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self._input(directory)
            events, pairs, summary = analyze_inputs(
                [path],
                LocalStudyConfig(
                    signal_time_min=50.0,
                    signal_time_max=110.0,
                    detection_amplitude=0.0,
                ),
            )

        self.assertEqual(len(events), 3)
        self.assertEqual(len(pairs), 3)
        self.assertEqual(len(summary), 3)
        self.assertTrue(all(row["baseline_delta"] == 0.0 for row in pairs))
        self.assertTrue(all(row["amplitude_delta"] == 0.0 for row in pairs))
        self.assertTrue(all(row["snr_delta"] == 0.0 for row in pairs))

    def test_local_outputs_include_manifest_and_three_tables(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self._input(directory)
            output = Path(directory) / "results"
            counts = run_local_study(
                [path],
                output,
                LocalStudyConfig(
                    signal_time_min=50.0,
                    signal_time_max=110.0,
                    detection_amplitude=0.0,
                ),
            )

            self.assertEqual(counts, (3, 3, 3))
            for name in (
                "event_method_results.csv",
                "pairwise_differences.csv",
                "pairwise_summary.csv",
                "manifest.json",
            ):
                self.assertTrue((output / name).is_file())


if __name__ == "__main__":
    unittest.main()
