"""Generación determinista de regiones sintéticas con baseline conocido."""

from __future__ import annotations

import random


def triangular_pulse_waveform(
    *,
    baseline: float,
    amplitude: float,
    total_samples: int = 120,
    baseline_samples: int = 50,
    pulse_start: int = 60,
    peak_index: int = 70,
    pulse_end: int = 90,
    sample_period: float = 1.0,
    noise_sigma: float = 0.0,
    drift_per_sample: float = 0.0,
    baseline_outliers: dict[int, float] | None = None,
    seed: int = 0,
) -> tuple[list[float], list[float]]:
    """Genera una forma de onda positiva con pulso triangular conocido.

    El triángulo es útil como referencia porque su máximo, área y cruces
    temporales pueden calcularse de manera independiente. Los valores extremos
    opcionales se restringen a la región usada para estimar la línea base.
    """

    if amplitude <= 0:
        raise ValueError("amplitude debe ser positiva")
    if sample_period <= 0:
        raise ValueError("sample_period debe ser positivo")
    if noise_sigma < 0:
        raise ValueError("noise_sigma no puede ser negativo")
    if not 0 < baseline_samples <= pulse_start < peak_index < pulse_end:
        raise ValueError("el orden de las regiones y del pulso no es válido")
    if pulse_end >= total_samples:
        raise ValueError("pulse_end debe estar dentro de la forma de onda")

    rng = random.Random(seed)
    baseline_center = (baseline_samples - 1) / 2
    times = [index * sample_period for index in range(total_samples)]
    voltages: list[float] = []
    for index in range(total_samples):
        if pulse_start <= index <= peak_index:
            pulse = amplitude * (index - pulse_start) / (peak_index - pulse_start)
        elif peak_index < index <= pulse_end:
            pulse = amplitude * (pulse_end - index) / (pulse_end - peak_index)
        else:
            pulse = 0.0
        drift = drift_per_sample * (index - baseline_center)
        voltages.append(
            baseline + drift + pulse + rng.gauss(0.0, noise_sigma)
        )

    for index, offset in (baseline_outliers or {}).items():
        if not 0 <= index < baseline_samples:
            raise IndexError(
                f"valor extremo fuera de la región de línea base: {index}"
            )
        voltages[index] += offset

    return times, voltages


def baseline_region(
    *,
    baseline: float,
    samples: int = 50,
    noise_sigma: float = 0.0,
    drift_per_sample: float = 0.0,
    outliers: dict[int, float] | None = None,
    seed: int = 0,
) -> list[float]:
    """Genera una región previa al pulso con perturbaciones controladas.

    ``outliers`` asigna a cada índice indicado un desplazamiento adicional,
    no un valor absoluto. El uso de una semilla local hace reproducible la
    realización sin modificar el generador aleatorio global.
    """

    if samples <= 0:
        raise ValueError("samples debe ser positivo")
    if noise_sigma < 0:
        raise ValueError("noise_sigma no puede ser negativo")

    rng = random.Random(seed)
    center = (samples - 1) / 2
    values = [
        baseline
        + drift_per_sample * (index - center)
        + rng.gauss(0.0, noise_sigma)
        for index in range(samples)
    ]

    for index, offset in (outliers or {}).items():
        if not 0 <= index < samples:
            raise IndexError(f"índice de valor extremo fuera de rango: {index}")
        values[index] += offset

    return values

