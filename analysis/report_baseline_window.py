"""Publica figuras e informe del estudio sintético de longitud de ventana."""

from __future__ import annotations

import argparse
import csv
import math
import shutil
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
NOISE_LEVELS = (0.005, 0.020)


def expected_mean_rmse(noise_sigma: float, samples: int) -> float:
    """RMSE teórico de la media para ruido gaussiano iid sin sesgo."""

    if samples <= 0:
        raise ValueError("samples debe ser positivo")
    if noise_sigma < 0:
        raise ValueError("noise_sigma no puede ser negativo")
    return noise_sigma / math.sqrt(samples)


def expected_mean_outlier_bias(offset: float, samples: int) -> float:
    """Sesgo de la media producido por un único desplazamiento aditivo."""

    if samples <= 0:
        raise ValueError("samples debe ser positivo")
    return offset / samples


def read_summary(path: Path) -> list[dict[str, Any]]:
    """Lee el resumen y convierte las columnas numéricas usadas."""

    float_fields = {
        "amplitude_true", "noise_sigma", "baseline_bias",
        "baseline_error_std", "baseline_mae", "baseline_rmse",
        "amplitude_bias", "amplitude_mae", "signed_area_bias",
        "signed_area_mae", "detection_fraction", "peak_time_mae",
        "rise_time_mae", "fwhm_mae",
    }
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8", newline="") as source:
        for raw in csv.DictReader(source):
            row: dict[str, Any] = dict(raw)
            for field in float_fields:
                row[field] = float(raw[field]) if raw[field] else None
            row["baseline_window"] = int(raw["baseline_window"])
            row["events"] = int(raw["events"])
            rows.append(row)
    if not rows:
        raise ValueError("la tabla resumen está vacía")
    return rows


def _select(rows: list[dict[str, Any]], **conditions: Any) -> list[dict[str, Any]]:
    return [row for row in rows if all(row[field] == value for field, value in conditions.items())]


def _one(rows: list[dict[str, Any]], **conditions: Any) -> dict[str, Any]:
    selected = _select(rows, **conditions)
    if len(selected) != 1:
        raise ValueError(f"se esperaba una fila para {conditions}, se encontraron {len(selected)}")
    return selected[0]


def plot_clean_rmse(rows: list[dict[str, Any]], output: Path) -> None:
    """Compara RMSE observado y predicción de la media en señales limpias."""

    figure, axes = plt.subplots(1, 2, figsize=(9.8, 4.2))
    for axis, noise_sigma in zip(axes, NOISE_LEVELS):
        selected = _select(rows, amplitude_true=1.0, noise_sigma=noise_sigma, outlier_scenario="none")
        for method in METHODS:
            method_rows = sorted(
                (row for row in selected if row["method"] == method),
                key=lambda row: row["baseline_window"],
            )
            axis.plot(
                [row["baseline_window"] for row in method_rows],
                [row["baseline_rmse"] for row in method_rows],
                marker="o", color=COLORS[method], label=METHOD_LABELS[method],
            )
        windows = sorted({row["baseline_window"] for row in selected})
        axis.plot(
            windows,
            [expected_mean_rmse(noise_sigma, window) for window in windows],
            linestyle="--", color="#333333", label=r"Media: $\sigma/\sqrt{N}$",
        )
        axis.set_title(f"Ruido σ = {noise_sigma:.3f} V")
        axis.set_xlabel("Muestras de línea base N")
        axis.set_ylabel("RMSE de línea base [V]")
        axis.set_xticks(windows)
        axis.grid(alpha=0.25)
    handles, labels = axes[-1].get_legend_handles_labels()
    figure.legend(handles, labels, loc="lower center", ncol=4, frameon=False)
    figure.suptitle("Ventana de línea base bajo ruido gaussiano independiente")
    figure.tight_layout(rect=(0, 0.14, 1, 0.92))
    figure.savefig(output, dpi=180)
    plt.close(figure)


def plot_positive_spike_bias(rows: list[dict[str, Any]], output: Path) -> None:
    """Muestra el sesgo frente a un pico positivo fijo dentro de la ventana."""

    figure, axes = plt.subplots(1, 2, figsize=(9.8, 4.2), sharey=True)
    for axis, noise_sigma in zip(axes, NOISE_LEVELS):
        selected = _select(rows, amplitude_true=1.0, noise_sigma=noise_sigma, outlier_scenario="positive_spike")
        for method in METHODS:
            method_rows = sorted(
                (row for row in selected if row["method"] == method),
                key=lambda row: row["baseline_window"],
            )
            axis.plot(
                [row["baseline_window"] for row in method_rows],
                [row["baseline_bias"] for row in method_rows],
                marker="o", color=COLORS[method], label=METHOD_LABELS[method],
            )
        windows = sorted({row["baseline_window"] for row in selected})
        axis.plot(
            windows,
            [expected_mean_outlier_bias(0.50, window) for window in windows],
            linestyle="--", color="#333333", label=r"Media: $0{,}50/N$",
        )
        axis.axhline(0.0, linewidth=0.8, color="#888888")
        axis.set_title(f"Ruido σ = {noise_sigma:.3f} V")
        axis.set_xlabel("Muestras de línea base N")
        axis.set_xticks(windows)
        axis.grid(alpha=0.25)
    axes[0].set_ylabel("Sesgo de línea base [V]")
    handles, labels = axes[-1].get_legend_handles_labels()
    figure.legend(handles, labels, loc="lower center", ncol=4, frameon=False)
    figure.suptitle("Un desplazamiento de +0,50 V en una muestra")
    figure.tight_layout(rect=(0, 0.14, 1, 0.92))
    figure.savefig(output, dpi=180)
    plt.close(figure)


def write_report(rows: list[dict[str, Any]], output: Path) -> None:
    """Documenta resultados sin extrapolarlos a adquisiciones DRS4 reales."""

    windows = sorted({row["baseline_window"] for row in rows})
    lines = [
        "# Longitud de la ventana de línea base: estudio sintético", "",
        "## Pregunta", "",
        "¿Cómo cambia la estimación de la línea base al usar 20, 50 o 100",
        "muestras, tanto con ruido gaussiano independiente como con valores",
        "extremos controlados? El diseño es pareado: cada forma de onda se",
        "procesó con todas las ventanas y métodos, manteniendo fija la región",
        "de señal.", "", "## Alcance", "",
        "Este informe usa exclusivamente señales sintéticas. No contiene",
        "registros DRS4, no determina una ventana óptima para un instrumento",
        "real y no representa una eficiencia física de detección.", "",
        "## Control analítico: ruido limpio", "",
        "Para muestras independientes con ruido gaussiano de desviación",
        "estándar σ, la media de N muestras tiene un RMSE esperado",
        "σ/√N. La simulación se aproxima a esa referencia; las diferencias",
        "residuales son compatibles con la estimación mediante 100 eventos",
        "por condición.", "",
        "| σ [V] | N | RMSE media observado [V] | σ/√N [V] |",
        "|---:|---:|---:|---:|",
    ]
    for noise_sigma in NOISE_LEVELS:
        for window in windows:
            row = _one(rows, amplitude_true=1.0, noise_sigma=noise_sigma, outlier_scenario="none", baseline_window=window, method="mean")
            lines.append(
                f"| {noise_sigma:.3f} | {window} | {row['baseline_rmse']:.6f} | "
                f"{expected_mean_rmse(noise_sigma, window):.6f} |"
            )
    lines.extend([
        "", "![RMSE frente a longitud de ventana](baseline_rmse_vs_window.png)", "",
        "## Contaminación positiva controlada", "",
        "Se añadió +0,50 V a una sola muestra de la región de línea base.",
        "Para la media, el sesgo esperado es 0,50/N: una ventana mayor",
        "diluye ese valor extremo, pero no lo rechaza. La mediana y la media",
        "recortada presentaron mucho menos sesgo en este escenario particular.", "",
        "| N | Sesgo media observado [V] | 0,50/N [V] | MAE mediana [V] | MAE recortada [V] |",
        "|---:|---:|---:|---:|---:|",
    ])
    for window in windows:
        shared = {"amplitude_true": 1.0, "noise_sigma": 0.005, "outlier_scenario": "positive_spike", "baseline_window": window}
        mean = _one(rows, **shared, method="mean")
        median = _one(rows, **shared, method="median")
        trimmed = _one(rows, **shared, method="trimmed_mean")
        lines.append(
            f"| {window} | {mean['baseline_bias']:.6f} | "
            f"{expected_mean_outlier_bias(0.50, window):.6f} | "
            f"{median['baseline_mae']:.6f} | {trimmed['baseline_mae']:.6f} |"
        )
    lines.extend([
        "", "![Sesgo ante pico positivo](positive_spike_bias_vs_window.png)", "",
        "## Interpretación limitada", "",
        "- En el modelo limpio, aumentar N reduce la variación de los tres",
        "  estimadores; para la media aparece la dependencia esperada 1/√N.",
        "- Ante un único pico positivo fijo, aumentar N reduce el sesgo de",
        "  la media como 1/N. Los estimadores robustos responden mejor a esta",
        "  contaminación concreta, pero eso no establece un ganador universal.",
        "- En el pulso pequeño del barrido, los escenarios con valores extremos",
        "  cambiaron también la estimación de ruido y la decisión de detección.",
        "  Ese efecto requiere un diagnóstico separado antes de interpretarlo.", "",
        "## Limitaciones y siguiente paso", "",
        "- El ruido es gaussiano e independiente; no incluye correlación,",
        "  oscilaciones, deriva temporal ni estructura de canales DRS4.",
        "- Los valores extremos tienen posiciones y magnitudes fijadas por el",
        "  diseño, no por una caracterización experimental.",
        "- Las ventanas no contienen señal en este estudio; falta estudiar",
        "  contaminación por llegada temprana del pulso.",
        "- Antes de aplicar el método a registros reales se debe conservar la",
        "  procedencia de los datos y definir criterios sin usar una línea base",
        "  verdadera, que en una adquisición no está disponible.", "",
    ])
    output.write_text("\n".join(lines), encoding="utf-8")


def publish(summary: Path, manifest: Path, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = read_summary(summary)
    plot_clean_rmse(rows, output_dir / "baseline_rmse_vs_window.png")
    plot_positive_spike_bias(rows, output_dir / "positive_spike_bias_vs_window.png")
    write_report(rows, output_dir / "report.md")
    # La tabla de estudio usa el dialecto CSV por defecto (CRLF). La copia
    # publicable se normaliza a LF para producir diffs limpios sin alterar datos.
    (output_dir / "summary.csv").write_text(
        summary.read_text(encoding="utf-8"),
        encoding="utf-8",
        newline="\n",
    )
    shutil.copy2(manifest, output_dir / "manifest.json")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-dir", type=Path, default=Path("results/baseline_window_01"))
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/baseline_window_01"))
    args = parser.parse_args()
    publish(args.results_dir / "summary.csv", args.results_dir / "manifest.json", args.output_dir)
    print(f"Published report: {args.output_dir}")


if __name__ == "__main__":
    main()
