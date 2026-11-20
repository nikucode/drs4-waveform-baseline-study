"""Barrido sintético de sensibilidad al estimador de línea base."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import statistics
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from src.features import compare_baseline_methods
from src.synthetic import triangular_pulse_waveform


@dataclass(frozen=True)
class StudyConfig:
    """Condiciones declaradas del primer barrido sintético."""

    baseline: float = 0.5
    amplitudes: tuple[float, ...] = (0.10, 0.50, 1.00)
    noise_sigmas: tuple[float, ...] = (0.0, 0.005, 0.020)
    drift_per_samples: tuple[float, ...] = (0.0, 0.0005)
    outlier_scenarios: tuple[str, ...] = (
        "none",
        "positive_spike",
        "mixed_spikes",
    )
    trials: int = 20
    seed_start: int = 20261120
    sample_period: float = 1.0
    pulse_start: int = 60
    peak_index: int = 70
    pulse_end: int = 90


OUTLIERS: dict[str, dict[int, float]] = {
    "none": {},
    "positive_spike": {0: 0.50},
    "mixed_spikes": {0: 0.50, 1: -0.35},
}


def _absolute_error(value: float | None, truth: float) -> float | None:
    return None if value is None else abs(value - truth)


def generate_event_rows(config: StudyConfig) -> list[dict[str, Any]]:
    """Genera una fila por evento y método usando formas de onda pareadas."""

    if config.trials <= 0:
        raise ValueError("trials debe ser positivo")
    unknown = set(config.outlier_scenarios) - set(OUTLIERS)
    if unknown:
        raise ValueError(f"escenarios de valores extremos desconocidos: {unknown}")

    rows: list[dict[str, Any]] = []
    event_id = 0
    rise_truth = (
        0.8
        * (config.peak_index - config.pulse_start)
        * config.sample_period
    )
    fwhm_truth = (
        0.5
        * (config.pulse_end - config.pulse_start)
        * config.sample_period
    )
    peak_time_truth = config.peak_index * config.sample_period

    for amplitude in config.amplitudes:
        area_truth = (
            0.5
            * (config.pulse_end - config.pulse_start)
            * config.sample_period
            * amplitude
        )
        for noise_sigma in config.noise_sigmas:
            for drift in config.drift_per_samples:
                for scenario in config.outlier_scenarios:
                    for trial in range(config.trials):
                        seed = config.seed_start + event_id
                        times, voltages = triangular_pulse_waveform(
                            baseline=config.baseline,
                            amplitude=amplitude,
                            noise_sigma=noise_sigma,
                            drift_per_sample=drift,
                            baseline_outliers=OUTLIERS[scenario],
                            sample_period=config.sample_period,
                            pulse_start=config.pulse_start,
                            peak_index=config.peak_index,
                            pulse_end=config.pulse_end,
                            seed=seed,
                        )
                        paired = compare_baseline_methods(times, voltages)
                        for method, features in paired.items():
                            rows.append(
                                {
                                    "event_id": event_id,
                                    "trial": trial,
                                    "seed": seed,
                                    "amplitude_true": amplitude,
                                    "noise_sigma": noise_sigma,
                                    "drift_per_sample": drift,
                                    "outlier_scenario": scenario,
                                    "method": method,
                                    "baseline_true": config.baseline,
                                    "baseline_estimate": features.baseline,
                                    "baseline_error": (
                                        features.baseline - config.baseline
                                    ),
                                    "baseline_absolute_error": abs(
                                        features.baseline - config.baseline
                                    ),
                                    "amplitude_estimate": features.amplitude,
                                    "amplitude_error": (
                                        features.amplitude - amplitude
                                    ),
                                    "amplitude_absolute_error": abs(
                                        features.amplitude - amplitude
                                    ),
                                    "area_true": area_truth,
                                    "signed_area_estimate": features.signed_area,
                                    "signed_area_error": (
                                        features.signed_area - area_truth
                                    ),
                                    "signed_area_absolute_error": abs(
                                        features.signed_area - area_truth
                                    ),
                                    "noise_rms": features.noise_rms,
                                    "snr": features.snr,
                                    "detected": features.detected,
                                    "peak_time": features.peak_time,
                                    "peak_time_absolute_error": abs(
                                        features.peak_time - peak_time_truth
                                    ),
                                    "rise_time_10_90": (
                                        features.rise_time_10_90
                                    ),
                                    "rise_time_absolute_error": _absolute_error(
                                        features.rise_time_10_90, rise_truth
                                    ),
                                    "fwhm": features.fwhm,
                                    "fwhm_absolute_error": _absolute_error(
                                        features.fwhm, fwhm_truth
                                    ),
                                }
                            )
                        event_id += 1
    return rows


def _mean_present(rows: list[dict[str, Any]], field: str) -> float | None:
    values = [row[field] for row in rows if row[field] is not None]
    return statistics.fmean(values) if values else None


def aggregate_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Resume errores sin mezclar amplitud, ruido, deriva ni contaminación."""

    fields = (
        "amplitude_true",
        "noise_sigma",
        "drift_per_sample",
        "outlier_scenario",
        "method",
    )
    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
    for row in rows:
        groups.setdefault(tuple(row[field] for field in fields), []).append(row)

    summary: list[dict[str, Any]] = []
    for key in sorted(groups, key=lambda item: tuple(map(str, item))):
        group = groups[key]
        baseline_errors = [row["baseline_error"] for row in group]
        summary.append(
            {
                **dict(zip(fields, key)),
                "events": len(group),
                "baseline_bias": statistics.fmean(baseline_errors),
                "baseline_error_std": (
                    statistics.pstdev(baseline_errors)
                    if len(baseline_errors) > 1
                    else 0.0
                ),
                "baseline_mae": _mean_present(
                    group, "baseline_absolute_error"
                ),
                "amplitude_bias": _mean_present(group, "amplitude_error"),
                "amplitude_mae": _mean_present(
                    group, "amplitude_absolute_error"
                ),
                "signed_area_bias": _mean_present(group, "signed_area_error"),
                "signed_area_mae": _mean_present(
                    group, "signed_area_absolute_error"
                ),
                "detection_fraction": statistics.fmean(
                    float(row["detected"]) for row in group
                ),
                "peak_time_mae": _mean_present(
                    group, "peak_time_absolute_error"
                ),
                "rise_time_recovery_fraction": statistics.fmean(
                    float(row["rise_time_10_90"] is not None) for row in group
                ),
                "rise_time_mae": _mean_present(
                    group, "rise_time_absolute_error"
                ),
                "fwhm_recovery_fraction": statistics.fmean(
                    float(row["fwhm"] is not None) for row in group
                ),
                "fwhm_mae": _mean_present(group, "fwhm_absolute_error"),
            }
        )
    return summary


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError("no hay filas para escribir")
    with path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_study(output_dir: Path, config: StudyConfig) -> tuple[int, int]:
    """Ejecuta el barrido y escribe productos regenerables y trazables."""

    output_dir.mkdir(parents=True, exist_ok=True)
    rows = generate_event_rows(config)
    summary = aggregate_rows(rows)
    _write_csv(output_dir / "event_results.csv", rows)
    _write_csv(output_dir / "summary.csv", summary)

    repository = Path(__file__).resolve().parents[1]
    sources = [
        Path(__file__).resolve(),
        repository / "src" / "baseline.py",
        repository / "src" / "features.py",
        repository / "src" / "synthetic.py",
    ]
    manifest = {
        "study": "synthetic_baseline_sensitivity",
        "config": asdict(config),
        "outlier_offsets": OUTLIERS,
        "design": "paired: each event is processed by all three methods",
        "files": {str(path.relative_to(repository)): _sha256(path) for path in sources},
        "outputs": {
            "event_rows": len(rows),
            "summary_rows": len(summary),
        },
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return len(rows), len(summary)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("results/baseline_sensitivity_01"),
    )
    parser.add_argument("--trials", type=int, default=20)
    args = parser.parse_args()

    event_rows, summary_rows = run_study(
        args.output_dir,
        StudyConfig(trials=args.trials),
    )
    print(f"Event-method rows: {event_rows}")
    print(f"Summary rows: {summary_rows}")
    print(f"Results: {args.output_dir}")


if __name__ == "__main__":
    main()
