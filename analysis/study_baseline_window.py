"""Barrido sintético pareado de longitud de ventana de línea base."""

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

from src.features import compare_baseline_methods
from src.synthetic import triangular_pulse_waveform


@dataclass(frozen=True)
class WindowStudyConfig:
    baseline: float = 0.5
    baseline_windows: tuple[int, ...] = (20, 50, 100)
    amplitudes: tuple[float, ...] = (0.10, 1.00)
    noise_sigmas: tuple[float, ...] = (0.005, 0.020)
    outlier_scenarios: tuple[str, ...] = (
        "none",
        "positive_spike",
        "mixed_spikes",
    )
    trials: int = 100
    seed_start: int = 20261121
    total_samples: int = 180
    pulse_start: int = 120
    peak_index: int = 130
    pulse_end: int = 150
    signal_time_min: float = 110.0
    signal_time_max: float = 160.0


OUTLIERS: dict[str, dict[int, float]] = {
    "none": {},
    "positive_spike": {0: 0.50},
    "mixed_spikes": {0: 0.50, 1: -0.35},
}


def generate_rows(config: WindowStudyConfig) -> list[dict[str, Any]]:
    """Reutiliza cada forma de onda en todas las ventanas y métodos."""

    if config.trials <= 0:
        raise ValueError("trials debe ser positivo")
    if not config.baseline_windows or min(config.baseline_windows) <= 0:
        raise ValueError("las ventanas de baseline deben ser positivas")
    largest_window = max(config.baseline_windows)
    if largest_window > config.pulse_start:
        raise ValueError("la ventana de baseline no puede incluir el pulso")
    unknown = set(config.outlier_scenarios) - set(OUTLIERS)
    if unknown:
        raise ValueError(f"escenarios desconocidos: {unknown}")

    area_truth = {
        amplitude: 0.5
        * (config.pulse_end - config.pulse_start)
        * amplitude
        for amplitude in config.amplitudes
    }
    rise_truth = 0.8 * (config.peak_index - config.pulse_start)
    fwhm_truth = 0.5 * (config.pulse_end - config.pulse_start)
    rows: list[dict[str, Any]] = []
    event_id = 0

    for amplitude in config.amplitudes:
        for noise_sigma in config.noise_sigmas:
            for scenario in config.outlier_scenarios:
                for trial in range(config.trials):
                    seed = config.seed_start + event_id
                    times, voltages = triangular_pulse_waveform(
                        baseline=config.baseline,
                        amplitude=amplitude,
                        total_samples=config.total_samples,
                        baseline_samples=largest_window,
                        pulse_start=config.pulse_start,
                        peak_index=config.peak_index,
                        pulse_end=config.pulse_end,
                        noise_sigma=noise_sigma,
                        baseline_outliers=OUTLIERS[scenario],
                        seed=seed,
                    )
                    for window in config.baseline_windows:
                        paired = compare_baseline_methods(
                            times,
                            voltages,
                            baseline_samples=window,
                            signal_time_min=config.signal_time_min,
                            signal_time_max=config.signal_time_max,
                        )
                        for method, features in paired.items():
                            baseline_error = features.baseline - config.baseline
                            amplitude_error = features.amplitude - amplitude
                            area_error = features.signed_area - area_truth[amplitude]
                            rows.append(
                                {
                                    "event_id": event_id,
                                    "trial": trial,
                                    "seed": seed,
                                    "amplitude_true": amplitude,
                                    "noise_sigma": noise_sigma,
                                    "outlier_scenario": scenario,
                                    "baseline_window": window,
                                    "method": method,
                                    "baseline_error": baseline_error,
                                    "baseline_absolute_error": abs(baseline_error),
                                    "baseline_squared_error": baseline_error**2,
                                    "amplitude_error": amplitude_error,
                                    "amplitude_absolute_error": abs(amplitude_error),
                                    "signed_area_error": area_error,
                                    "signed_area_absolute_error": abs(area_error),
                                    "detected": features.detected,
                                    "peak_time_absolute_error": abs(
                                        features.peak_time - config.peak_index
                                    ),
                                    "rise_time_absolute_error": (
                                        None
                                        if features.rise_time_10_90 is None
                                        else abs(features.rise_time_10_90 - rise_truth)
                                    ),
                                    "fwhm_absolute_error": (
                                        None
                                        if features.fwhm is None
                                        else abs(features.fwhm - fwhm_truth)
                                    ),
                                }
                            )
                    event_id += 1
    return rows


def _mean_present(rows: list[dict[str, Any]], field: str) -> float | None:
    values = [row[field] for row in rows if row[field] is not None]
    return statistics.fmean(values) if values else None


def aggregate_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    fields = (
        "amplitude_true",
        "noise_sigma",
        "outlier_scenario",
        "baseline_window",
        "method",
    )
    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
    for row in rows:
        groups.setdefault(tuple(row[field] for field in fields), []).append(row)

    summary: list[dict[str, Any]] = []
    for key in sorted(groups, key=lambda item: tuple(map(str, item))):
        group = groups[key]
        errors = [row["baseline_error"] for row in group]
        summary.append(
            {
                **dict(zip(fields, key)),
                "events": len(group),
                "baseline_bias": statistics.fmean(errors),
                "baseline_error_std": statistics.pstdev(errors),
                "baseline_mae": _mean_present(group, "baseline_absolute_error"),
                "baseline_rmse": math.sqrt(
                    statistics.fmean(
                        row["baseline_squared_error"] for row in group
                    )
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
                "rise_time_mae": _mean_present(
                    group, "rise_time_absolute_error"
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


def run_study(output_dir: Path, config: WindowStudyConfig) -> tuple[int, int]:
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = generate_rows(config)
    summary = aggregate_rows(rows)
    _write_csv(output_dir / "event_results.csv", rows)
    _write_csv(output_dir / "summary.csv", summary)

    repository = Path(__file__).resolve().parents[1]
    sources = [
        Path(__file__).resolve(),
        repository / "src" / "baseline.py",
        repository / "src" / "features.py",
        repository / "src" / "synthetic.py",
        repository / "docs" / "estudio_longitud_ventana.md",
    ]
    manifest = {
        "study": "synthetic_baseline_window_length",
        "config": asdict(config),
        "outlier_offsets": OUTLIERS,
        "design": (
            "paired: each waveform is reused across all windows and methods; "
            "signal integration window remains fixed"
        ),
        "files": {
            str(path.relative_to(repository)): _sha256(path) for path in sources
        },
        "outputs": {"event_rows": len(rows), "summary_rows": len(summary)},
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
        default=Path("results/baseline_window_01"),
    )
    parser.add_argument("--trials", type=int, default=100)
    args = parser.parse_args()
    counts = run_study(
        args.output_dir,
        WindowStudyConfig(trials=args.trials),
    )
    print(f"Event-method-window rows: {counts[0]}")
    print(f"Summary rows: {counts[1]}")
    print(f"Results: {args.output_dir}")


if __name__ == "__main__":
    main()
