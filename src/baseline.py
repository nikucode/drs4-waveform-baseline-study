"""Estimadores de línea base para formas de onda digitalizadas.

Los estimadores operan sobre una región previa al pulso. La selección de esa
región es responsabilidad de quien llama a estas funciones; en el estudio
principal se usarán las primeras 50 muestras de cada forma de onda.
"""

from __future__ import annotations

import math
import statistics
from collections.abc import Iterable


def _validated_samples(samples: Iterable[float]) -> list[float]:
    """Convierte las muestras a ``float`` y exige valores finitos."""

    values = [float(value) for value in samples]
    if not values:
        raise ValueError("se requiere al menos una muestra de línea base")
    if not all(math.isfinite(value) for value in values):
        raise ValueError("las muestras de línea base deben ser finitas")
    return values


def mean_baseline(samples: Iterable[float]) -> float:
    """Estima la línea base mediante la media aritmética."""

    return statistics.fmean(_validated_samples(samples))


def median_baseline(samples: Iterable[float]) -> float:
    """Estima la línea base mediante la mediana."""

    return float(statistics.median(_validated_samples(samples)))


def trimmed_mean_baseline(
    samples: Iterable[float], *, trim_fraction: float = 0.10
) -> float:
    """Calcula una media recortada simétrica.

    Se eliminan ``floor(N * trim_fraction)`` valores de cada extremo después
    de ordenar las muestras. Para las 50 muestras y la fracción 0,10 del
    estudio, esto elimina cinco valores inferiores y cinco superiores.
    """

    values = sorted(_validated_samples(samples))
    if not math.isfinite(trim_fraction) or not 0.0 <= trim_fraction < 0.5:
        raise ValueError("trim_fraction debe estar en el intervalo [0, 0.5)")

    count = math.floor(len(values) * trim_fraction)
    kept = values[count : len(values) - count] if count else values
    return statistics.fmean(kept)


def estimate_baselines(
    samples: Iterable[float], *, trim_fraction: float = 0.10
) -> dict[str, float]:
    """Aplica los tres métodos a una misma región de forma pareada."""

    values = _validated_samples(samples)
    return {
        "mean": mean_baseline(values),
        "median": median_baseline(values),
        "trimmed_mean": trimmed_mean_baseline(
            values, trim_fraction=trim_fraction
        ),
    }

