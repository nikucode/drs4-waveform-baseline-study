"""Genera un inventario local de archivos DRS4 sin publicar sus muestras."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

from src.drs4_xml import iter_drs4_waveforms


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def inspect_file(path: Path) -> dict[str, Any]:
    """Resume estructura y rangos sin conservar formas de onda en la salida."""

    records = 0
    serials: set[int] = set()
    boards: set[int] = set()
    channels: Counter[str] = Counter()
    sample_counts: Counter[int] = Counter()
    units: set[tuple[str, str]] = set()
    time_min = float("inf")
    time_max = float("-inf")
    voltage_min = float("inf")
    voltage_max = float("-inf")

    for waveform in iter_drs4_waveforms(path):
        records += 1
        serials.add(waveform.serial)
        boards.add(waveform.board)
        channels[waveform.channel] += 1
        sample_counts[len(waveform.times)] += 1
        units.add((waveform.horizontal_unit, waveform.vertical_unit))
        time_min = min(time_min, waveform.times[0])
        time_max = max(time_max, waveform.times[-1])
        voltage_min = min(voltage_min, min(waveform.voltages))
        voltage_max = max(voltage_max, max(waveform.voltages))

    if not records:
        raise ValueError(f"no se encontraron formas de onda en {path}")
    return {
        "file": path.name,
        "size_bytes": path.stat().st_size,
        "sha256": _sha256(path),
        "events": len(serials),
        "serial_first": min(serials),
        "serial_last": max(serials),
        "waveform_records": records,
        "boards": sorted(boards),
        "channels": dict(sorted(channels.items())),
        "samples_per_waveform": {
            str(count): occurrences
            for count, occurrences in sorted(sample_counts.items())
        },
        "units": [list(pair) for pair in sorted(units)],
        "time_range": [time_min, time_max],
        "voltage_range": [voltage_min, voltage_max],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", type=Path, nargs="+")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results/local_drs4_inventory.json"),
    )
    args = parser.parse_args()
    inventory = {
        "scope": "local structural inventory; no waveforms are published",
        "files": [inspect_file(path) for path in args.inputs],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(inventory, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"Files inspected: {len(inventory['files'])}")
    print(f"Local inventory: {args.output}")


if __name__ == "__main__":
    main()
