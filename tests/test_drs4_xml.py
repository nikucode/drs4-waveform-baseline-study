import tempfile
import unittest
from pathlib import Path

from analysis.inspect_local_drs4 import inspect_file
from src.drs4_xml import DRS4FormatError, iter_drs4_waveforms


def _xml(second_time: float = 1.0) -> str:
    return f"""<?xml version="1.0"?>
<DRSOSC>
  <Event>
    <Serial>7</Serial><Time>2026/11/20 12:00:00.000</Time>
    <HUnit>ns</HUnit><VUnit>mV</VUnit>
    <Board_3085>
      <Trigger_Cell>393</Trigger_Cell>
      <CHN1><Data>0.0,0.1</Data><Data>{second_time},2.5</Data></CHN1>
      <CHN2><Data>0.0,-0.1</Data><Data>{second_time},1.5</Data></CHN2>
    </Board_3085>
  </Event>
  <Event>
    <Serial>8</Serial><Time>2026/11/20 12:00:00.100</Time>
    <HUnit>ns</HUnit><VUnit>mV</VUnit>
    <Board_3085>
      <Trigger_Cell>394</Trigger_Cell>
      <CHN1><Data>0.0,0.0</Data><Data>{second_time},3.0</Data></CHN1>
      <CHN2><Data>0.0,0.0</Data><Data>{second_time},2.0</Data></CHN2>
    </Board_3085>
  </Event>
</DRSOSC>
"""


class TestDRS4XMLAdapter(unittest.TestCase):
    def _write(self, directory: str, content: str) -> Path:
        path = Path(directory) / "synthetic_drs4.xml"
        path.write_text(content, encoding="utf-8")
        return path

    def test_streams_events_boards_channels_and_samples(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self._write(directory, _xml())
            records = list(iter_drs4_waveforms(path))

        self.assertEqual(len(records), 4)
        self.assertEqual({record.serial for record in records}, {7, 8})
        self.assertEqual({record.channel for record in records}, {"CHN1", "CHN2"})
        self.assertEqual(records[0].times, (0.0, 1.0))
        self.assertEqual(records[0].voltages, (0.1, 2.5))
        self.assertEqual(records[0].horizontal_unit, "ns")
        self.assertEqual(records[0].vertical_unit, "mV")

    def test_rejects_non_increasing_time_axis(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self._write(directory, _xml(second_time=0.0))
            with self.assertRaises(DRS4FormatError):
                list(iter_drs4_waveforms(path))

    def test_rejects_empty_xml(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self._write(directory, "")
            with self.assertRaises(DRS4FormatError):
                list(iter_drs4_waveforms(path))

    def test_local_inventory_does_not_include_sample_arrays(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self._write(directory, _xml())
            inventory = inspect_file(path)

        self.assertEqual(inventory["events"], 2)
        self.assertEqual(inventory["waveform_records"], 4)
        self.assertEqual(inventory["channels"], {"CHN1": 2, "CHN2": 2})
        self.assertEqual(inventory["samples_per_waveform"], {"2": 4})
        self.assertNotIn("voltages", inventory)
        self.assertNotIn("times", inventory)


if __name__ == "__main__":
    unittest.main()
