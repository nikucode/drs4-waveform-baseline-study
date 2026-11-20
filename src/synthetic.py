"""Generación determinista de regiones sintéticas con baseline conocido."""

from __future__ import annotations

import random


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

