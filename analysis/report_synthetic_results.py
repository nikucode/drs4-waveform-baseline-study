"""Genera figuras e informe publicable del primer barrido sintético."""

from __future__ import annotations

import argparse
import csv
import shutil
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


METHODS = ("mean", "median", "trimmed_mean")
METHOD_LABELS = {
    "mean": "Media",
    "median": "Mediana",
    "trimmed_mean": "Media recortada",
}
COLORS = {
    "mean": "#4c78a8",
    "median": "#f58518",
    "trimmed_mean": "#54a24b",
}
SCENARIOS = ("none", "positive_spike", "mixed_spikes")
SCENARIO_LABELS = {
    "none": "Sin valores extremos",
    "positive_spike": "Pico positivo",
    "mixed_spikes": "Picos mixtos",
}


def read_summary(path: Path) -> list[dict[str, Any]]:
    """Lee la tabla agregada convirtiendo sus magnitudes numéricas."""

    numeric = {
        "amplitude_true",
        "noise_sigma",
        "drift_per_sample",
        "baseline_bias",
        "baseline_error_std",
        "baseline_mae",
        "amplitude_bias",
        "amplitude_mae",
        "signed_area_bias",
        "signed_area_mae",
        "detection_fraction",
        "peak_time_mae",
        "rise_time_recovery_fraction",
        "rise_time_mae",
        "fwhm_recovery_fraction",
        "fwhm_mae",
    }
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8", newline="") as source:
        for raw in csv.DictReader(source):
            row: dict[str, Any] = dict(raw)
            for field in numeric:
                row[field] = float(raw[field]) if raw[field] else None
            row["events"] = int(raw["events"])
            rows.append(row)
    if not rows:
        raise ValueError("la tabla resumen está vacía")
    return rows


def _select(rows: list[dict[str, Any]], **conditions: Any) -> list[dict[str, Any]]:
    return [
        row
        for row in rows
        if all(row[field] == value for field, value in conditions.items())
    ]


def count_lowest_baseline_mae(
    rows: list[dict[str, Any]], *, tolerance: float = 1e-12
) -> Counter[tuple[str, ...]]:
    """Cuenta mínimos y empates por combinación sin mezclar condiciones."""

    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        key = (
            row["amplitude_true"],
            row["noise_sigma"],
            row["drift_per_sample"],
            row["outlier_scenario"],
        )
        groups[key].append(row)

    counts: Counter[tuple[str, ...]] = Counter()
    for group in groups.values():
        best = min(row["baseline_mae"] for row in group)
        tied = tuple(
            method
            for method in METHODS
            if any(
                row["method"] == method
                and abs(row["baseline_mae"] - best) <= tolerance
                for row in group
            )
        )
        counts[tied] += 1
    return counts


def plot_baseline_mae(rows: list[dict[str, Any]], output: Path) -> None:
    """Grafica MAE del baseline frente al ruido para una sección declarada."""

    figure, axes = plt.subplots(1, 3, figsize=(11.5, 4.2), sharey=True)
    for axis, scenario in zip(axes, SCENARIOS):
        selected = _select(
            rows,
            amplitude_true=0.5,
            drift_per_sample=0.0,
            outlier_scenario=scenario,
        )
        for method in METHODS:
            method_rows = sorted(
                (row for row in selected if row["method"] == method),
                key=lambda row: row["noise_sigma"],
            )
            axis.plot(
                [row["noise_sigma"] for row in method_rows],
                [row["baseline_mae"] for row in method_rows],
                marker="o",
                color=COLORS[method],
                label=METHOD_LABELS[method],
            )
        axis.set_title(SCENARIO_LABELS[scenario])
        axis.set_xlabel("Ruido σ [V]")
        axis.grid(alpha=0.25)
    axes[0].set_ylabel("MAE de línea base [V]")
    handles, labels = axes[-1].get_legend_handles_labels()
    figure.legend(handles, labels, loc="lower center", ncol=3, frameon=False)
    figure.suptitle(
        "Sensibilidad del baseline (amplitud 0,5 V; sin deriva)", y=0.98
    )
    figure.tight_layout(rect=(0, 0.12, 1, 0.91))
    figure.savefig(output, dpi=180)
    plt.close(figure)


def plot_amplitude_mae(rows: list[dict[str, Any]], output: Path) -> None:
    """Grafica propagación del baseline hacia la amplitud reconstruida."""

    figure, axes = plt.subplots(1, 3, figsize=(11.5, 4.2), sharey=True)
    for axis, scenario in zip(axes, SCENARIOS):
        selected = _select(
            rows,
            noise_sigma=0.02,
            drift_per_sample=0.0,
            outlier_scenario=scenario,
        )
        for method in METHODS:
            method_rows = sorted(
                (row for row in selected if row["method"] == method),
                key=lambda row: row["amplitude_true"],
            )
            axis.plot(
                [row["amplitude_true"] for row in method_rows],
                [row["amplitude_mae"] for row in method_rows],
                marker="o",
                color=COLORS[method],
                label=METHOD_LABELS[method],
            )
        axis.set_title(SCENARIO_LABELS[scenario])
        axis.set_xlabel("Amplitud verdadera [V]")
        axis.grid(alpha=0.25)
    axes[0].set_ylabel("MAE de amplitud [V]")
    handles, labels = axes[-1].get_legend_handles_labels()
    figure.legend(handles, labels, loc="lower center", ncol=3, frameon=False)
    figure.suptitle(
        "Propagación a amplitud (ruido σ=0,02 V; sin deriva)", y=0.98
    )
    figure.tight_layout(rect=(0, 0.12, 1, 0.91))
    figure.savefig(output, dpi=180)
    plt.close(figure)


def _format_methods(methods: tuple[str, ...]) -> str:
    return " + ".join(METHOD_LABELS[method] for method in methods)


def write_report(rows: list[dict[str, Any]], output: Path) -> None:
    """Escribe observaciones limitadas al modelo y condiciones ejecutadas."""

    counts = count_lowest_baseline_mae(rows)
    clean = _select(
        rows,
        amplitude_true=0.5,
        noise_sigma=0.0,
        drift_per_sample=0.0,
        outlier_scenario="none",
    )
    positive = _select(
        rows,
        amplitude_true=0.5,
        noise_sigma=0.0,
        drift_per_sample=0.0,
        outlier_scenario="positive_spike",
    )
    drift = _select(
        rows,
        amplitude_true=0.5,
        noise_sigma=0.0,
        drift_per_sample=0.0005,
        outlier_scenario="none",
    )

    lines = [
        "# Primer estudio sintético de sensibilidad al baseline",
        "",
        "## Alcance",
        "",
        "Este informe resume señales sintéticas positivas con línea base y",
        "pulso triangular conocidos. No contiene registros DRS4 ni demuestra",
        "exactitud sobre datos experimentales. Cada forma de onda fue procesada",
        "por los tres métodos; por tanto, las comparaciones son pareadas.",
        "",
        "## Controles de consistencia",
        "",
        "| Condición | Método | MAE baseline [V] | MAE amplitud [V] |",
        "|---|---:|---:|---:|",
    ]
    for label, selected in (("Limpia", clean), ("Pico +0,50 V", positive)):
        for row in selected:
            lines.append(
                f"| {label} | {METHOD_LABELS[row['method']]} | "
                f"{row['baseline_mae']:.6f} | {row['amplitude_mae']:.6f} |"
            )

    lines.extend(
        [
            "",
            "En el caso limpio y sin ruido, los tres métodos recuperaron los",
            "valores esperados dentro de la precisión numérica. Un valor extremo",
            "de +0,50 V dentro de 50 muestras desplazó la media en +0,010 V; en",
            "esta construcción particular, la mediana y la media recortada no",
            "cambiaron.",
            "",
            "## Deriva",
            "",
            "La deriva se definió respecto del centro de la región de baseline y",
            "continuó durante el pulso. Por eso un baseline medio aparentemente",
            "correcto no garantiza amplitud ni área correctas si la línea base no",
            "es estacionaria.",
            "",
            "| Método | MAE baseline [V] | MAE amplitud [V] | MAE área |",
            "|---|---:|---:|---:|",
        ]
    )
    for row in drift:
        lines.append(
            f"| {METHOD_LABELS[row['method']]} | {row['baseline_mae']:.6f} | "
            f"{row['amplitude_mae']:.6f} | {row['signed_area_mae']:.6f} |"
        )

    lines.extend(
        [
            "",
            "## Mínimos y empates en la grilla",
            "",
            "La siguiente cuenta solo identifica el menor MAE de baseline dentro",
            "de cada una de las 54 combinaciones simuladas. No es una clasificación",
            "universal ni pondera condiciones según su frecuencia experimental.",
            "",
            "| Método(s) con menor MAE | Condiciones |",
            "|---|---:|",
        ]
    )
    for methods, count in sorted(counts.items(), key=lambda item: (-item[1], item[0])):
        lines.append(f"| {_format_methods(methods)} | {count} |")

    lines.extend(
        [
            "",
            "## Figuras",
            "",
            "![MAE de línea base](baseline_mae_vs_noise.png)",
            "",
            "![MAE de amplitud](amplitude_mae_vs_amplitude.png)",
            "",
            "## Limitaciones",
            "",
            "- Los pulsos son triangulares, positivos y generados por un modelo",
            "  deliberadamente simple.",
            "- Los valores extremos y la deriva son escenarios elegidos, no una",
            "  caracterización de un instrumento DRS4 específico.",
            "- El menor error depende de la distribución simulada y del tamaño de",
            "  la ventana de línea base.",
            "- La fase experimental deberá conservar procedencia, canales y",
            "  adquisiciones separados, y no dispondrá de un baseline verdadero.",
            "",
        ]
    )
    output.write_text("\n".join(lines), encoding="utf-8")


def publish(summary: Path, manifest: Path, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = read_summary(summary)
    plot_baseline_mae(rows, output_dir / "baseline_mae_vs_noise.png")
    plot_amplitude_mae(rows, output_dir / "amplitude_mae_vs_amplitude.png")
    write_report(rows, output_dir / "report.md")
    shutil.copy2(summary, output_dir / "summary.csv")
    shutil.copy2(manifest, output_dir / "manifest.json")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=Path("results/baseline_sensitivity_01"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("artifacts/baseline_sensitivity_01"),
    )
    args = parser.parse_args()
    publish(
        args.results_dir / "summary.csv",
        args.results_dir / "manifest.json",
        args.output_dir,
    )
    print(f"Published report: {args.output_dir}")


if __name__ == "__main__":
    main()
