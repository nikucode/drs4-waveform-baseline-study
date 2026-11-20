"""Compara localmente estimadores sobre XML DRS4 sin publicar resultados."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import statistics
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from src.drs4_xml import iter_drs4_waveforms
from src.features import WaveformFeatures, compare_baseline_methods


METHOD_PAIRS = (
    ("mean", "median"),
    ("mean", "trimmed_mean"),
    ("median", "trimmed_mean"),
)


@dataclass(frozen=True)
class LocalStudyConfig:
    """Configuración explícita y modificable de la comparación local."""

    baseline_samples: int = 50
    trim_fraction: float = 0.10
    signal_time_min: float = 50.0
    signal_time_max: float = 160.0
    detection_snr: float = 5.0
    detection_amplitude: float = 3.0
    adc_max: float = 949.9


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _feature_row(
    source: str,
    serial: int,
    board: int,
    channel: str,
    method: str,
    features: WaveformFeatures,
) -> dict[str, Any]:
    return {
        "source": source,
        "serial": serial,
        "board": board,
        "channel": channel,
        "method": method,
        **asdict(features),
    }


def _difference(left: float | None, right: float | None) -> float | None:
    """Calcula right-left conservando parámetros no recuperables como nulos."""

    if left is None or right is None:
        return None
    if not math.isfinite(left) or not math.isfinite(right):
        return 0.0 if left == right else None
    return right - left


def analyze_inputs(
    inputs: list[Path], config: LocalStudyConfig
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Procesa cada waveform una vez y compara los métodos por pares."""

    event_rows: list[dict[str, Any]] = []
    pair_rows: list[dict[str, Any]] = []
    for path in inputs:
        for waveform in iter_drs4_waveforms(path):
            paired = compare_baseline_methods(
                list(waveform.times),
                list(waveform.voltages),
                baseline_samples=config.baseline_samples,
                trim_fraction=config.trim_fraction,
                signal_time_min=config.signal_time_min,
                signal_time_max=config.signal_time_max,
                detection_snr=config.detection_snr,
                detection_amplitude=config.detection_amplitude,
                adc_max=config.adc_max,
            )
            for method, features in paired.items():
                event_rows.append(
                    _feature_row(
                        waveform.source,
                        waveform.serial,
                        waveform.board,
                        waveform.channel,
                        method,
                        features,
                    )
                )
            for method_a, method_b in METHOD_PAIRS:
                first, second = paired[method_a], paired[method_b]
                pair_rows.append(
                    {
                        "source": waveform.source,
                        "serial": waveform.serial,
                        "board": waveform.board,
                        "channel": waveform.channel,
                        "method_a": method_a,
                        "method_b": method_b,
                        "delta_definition": "method_b_minus_method_a",
                        "baseline_delta": second.baseline - first.baseline,
                        "amplitude_delta": second.amplitude - first.amplitude,
                        "noise_rms_delta": second.noise_rms - first.noise_rms,
                        "snr_delta": _difference(first.snr, second.snr),
                        "signed_area_delta": (
                            second.signed_area - first.signed_area
                        ),
                        "positive_area_delta": (
                            second.positive_area - first.positive_area
                        ),
                        "peak_time_delta": second.peak_time - first.peak_time,
                        "rise_time_delta": _difference(
                            first.rise_time_10_90, second.rise_time_10_90
                        ),
                        "fwhm_delta": _difference(first.fwhm, second.fwhm),
                        "detection_changed": first.detected != second.detected,
                    }
                )
    return event_rows, pair_rows, aggregate_pairwise(pair_rows)


def _percentile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] + fraction * (ordered[upper] - ordered[lower])


def aggregate_pairwise(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Resume diferencias pareadas por archivo, placa, canal y par de métodos."""

    keys = ("source", "board", "channel", "method_a", "method_b")
    fields = (
        "baseline_delta",
        "amplitude_delta",
        "noise_rms_delta",
        "snr_delta",
        "signed_area_delta",
        "positive_area_delta",
        "peak_time_delta",
        "rise_time_delta",
        "fwhm_delta",
    )
    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
    for row in rows:
        groups.setdefault(tuple(row[key] for key in keys), []).append(row)

    summary: list[dict[str, Any]] = []
    for key in sorted(groups, key=lambda item: tuple(map(str, item))):
        group = groups[key]
        item: dict[str, Any] = {
            **dict(zip(keys, key)),
            "waveforms": len(group),
            "detection_changes": sum(row["detection_changed"] for row in group),
        }
        for field in fields:
            values = [row[field] for row in group if row[field] is not None]
            item[f"{field}_available"] = len(values)
            item[f"{field}_median"] = statistics.median(values) if values else None
            item[f"{field}_p05"] = _percentile(values, 0.05) if values else None
            item[f"{field}_p95"] = _percentile(values, 0.95) if values else None
        summary.append(item)
    return summary


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"no hay filas para escribir en {path.name}")
    with path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def run_local_study(
    inputs: list[Path], output_dir: Path, config: LocalStudyConfig
) -> tuple[int, int, int]:
    """Escribe tablas y manifiesto solo en el directorio local ignorado."""

    output_dir.mkdir(parents=True, exist_ok=True)
    event_rows, pair_rows, summary = analyze_inputs(inputs, config)
    _write_csv(output_dir / "event_method_results.csv", event_rows)
    _write_csv(output_dir / "pairwise_differences.csv", pair_rows)
    _write_csv(output_dir / "pairwise_summary.csv", summary)

    repository = Path(__file__).resolve().parents[1]
    code_paths = [
        Path(__file__).resolve(),
        repository / "src" / "baseline.py",
        repository / "src" / "features.py",
        repository / "src" / "drs4_xml.py",
    ]
    manifest = {
        "scope": "local sensitivity analysis; not approved for publication",
        "interpretation": (
            "paired differences measure sensitivity, not experimental accuracy"
        ),
        "configuration_origin": (
            "compatibility values from prior collaborative reduction; "
            "not independently calibrated"
        ),
        "config": asdict(config),
        "inputs": [
            {
                "file": path.name,
                "size_bytes": path.stat().st_size,
                "sha256": _sha256(path),
            }
            for path in inputs
        ],
        "code_sha256": {
            str(path.relative_to(repository)): _sha256(path) for path in code_paths
        },
        "outputs": {
            "event_method_rows": len(event_rows),
            "pairwise_rows": len(pair_rows),
            "summary_rows": len(summary),
        },
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return len(event_rows), len(pair_rows), len(summary)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", type=Path, nargs="+")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("results/local_drs4_baseline_01"),
    )
    parser.add_argument("--baseline-samples", type=int, default=50)
    parser.add_argument("--signal-start-ns", type=float, default=50.0)
    parser.add_argument("--signal-end-ns", type=float, default=160.0)
    parser.add_argument("--detection-snr", type=float, default=5.0)
    parser.add_argument("--detection-amplitude-mv", type=float, default=3.0)
    parser.add_argument("--adc-max-mv", type=float, default=949.9)
    args = parser.parse_args()

    config = LocalStudyConfig(
        baseline_samples=args.baseline_samples,
        signal_time_min=args.signal_start_ns,
        signal_time_max=args.signal_end_ns,
        detection_snr=args.detection_snr,
        detection_amplitude=args.detection_amplitude_mv,
        adc_max=args.adc_max_mv,
    )
    counts = run_local_study(args.inputs, args.output_dir, config)
    print(f"Event-method rows: {counts[0]}")
    print(f"Pairwise rows: {counts[1]}")
    print(f"Summary rows: {counts[2]}")
    print(f"Local results: {args.output_dir}")


if __name__ == "__main__":
    main()
