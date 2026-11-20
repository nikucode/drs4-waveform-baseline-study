"""Extracción inicial de características de pulsos positivos."""

from __future__ import annotations

import math
from dataclasses import dataclass

from .baseline import estimate_baselines


@dataclass(frozen=True)
class WaveformFeatures:
    """Características reconstruidas con un estimador de línea base."""

    baseline: float
    noise_rms: float
    amplitude: float
    snr: float
    signed_area: float
    positive_area: float
    peak_time: float
    rise_time_10_90: float | None
    fwhm: float | None
    saturated_samples: int
    detected: bool


def _crossing_time(
    times: list[float],
    values: list[float],
    level: float,
    *,
    rising: bool,
) -> float | None:
    """Interpola un cruce, priorizando el flanco próximo al máximo."""

    indices = (
        range(len(values) - 1, 0, -1) if rising else range(1, len(values))
    )
    for index in indices:
        left, right = values[index - 1], values[index]
        crossed = left <= level <= right if rising else left >= level >= right
        if not crossed or left == right:
            continue
        fraction = (level - left) / (right - left)
        return times[index - 1] + fraction * (times[index] - times[index - 1])
    return None


def _trapezoid(times: list[float], values: list[float]) -> float:
    return sum(
        (right_value + left_value) * (right_time - left_time) / 2
        for left_time, right_time, left_value, right_value in zip(
            times, times[1:], values, values[1:]
        )
    )


def extract_features(
    times: list[float],
    voltages: list[float],
    *,
    method: str,
    baseline_samples: int = 50,
    trim_fraction: float = 0.10,
    detection_snr: float = 5.0,
    detection_amplitude: float = 0.0,
    signal_time_min: float | None = None,
    signal_time_max: float | None = None,
    adc_min: float | None = None,
    adc_max: float | None = None,
) -> WaveformFeatures:
    """Extrae características usando uno de los tres baselines definidos.

    Esta primera versión asume pulsos positivos. Los tiempos de cruce usan
    interpolación lineal y el área se integra mediante trapecios sobre la
    región posterior al baseline.
    """

    if len(times) != len(voltages) or len(times) < 2:
        raise ValueError("times y voltages deben tener igual longitud >= 2")
    if not 0 < baseline_samples < len(voltages):
        raise ValueError("baseline_samples debe dejar una región de señal")
    if not all(math.isfinite(value) for value in times + voltages):
        raise ValueError("tiempos y voltajes deben ser finitos")
    if any(right <= left for left, right in zip(times, times[1:])):
        raise ValueError("el eje temporal debe ser estrictamente creciente")
    if detection_snr < 0:
        raise ValueError("detection_snr no puede ser negativo")
    if detection_amplitude < 0:
        raise ValueError("detection_amplitude no puede ser negativa")
    if (
        signal_time_min is not None
        and signal_time_max is not None
        and signal_time_min >= signal_time_max
    ):
        raise ValueError("signal_time_min debe ser menor que signal_time_max")
    if adc_min is not None and adc_max is not None and adc_min >= adc_max:
        raise ValueError("adc_min debe ser menor que adc_max")

    estimates = estimate_baselines(
        voltages[:baseline_samples], trim_fraction=trim_fraction
    )
    if method not in estimates:
        raise ValueError(f"método de línea base desconocido: {method}")
    baseline = estimates[method]
    baseline_region = voltages[:baseline_samples]
    noise_rms = math.sqrt(
        sum((value - baseline) ** 2 for value in baseline_region)
        / len(baseline_region)
    )

    signal = [
        (time, voltage - baseline)
        for time, voltage in zip(
            times[baseline_samples:], voltages[baseline_samples:]
        )
        if (signal_time_min is None or time >= signal_time_min)
        and (signal_time_max is None or time <= signal_time_max)
    ]
    if len(signal) < 2:
        raise ValueError("la ventana de señal debe contener al menos 2 muestras")
    signal_times = [time for time, _ in signal]
    corrected = [value for _, value in signal]
    peak_index = max(range(len(corrected)), key=corrected.__getitem__)
    amplitude = corrected[peak_index]
    peak_time = signal_times[peak_index]
    snr = amplitude / noise_rms if noise_rms > 0 else math.inf

    pre_peak_times = signal_times[: peak_index + 1]
    pre_peak_values = corrected[: peak_index + 1]
    post_peak_times = signal_times[peak_index:]
    post_peak_values = corrected[peak_index:]

    time_10 = _crossing_time(
        pre_peak_times, pre_peak_values, 0.10 * amplitude, rising=True
    )
    time_90 = _crossing_time(
        pre_peak_times, pre_peak_values, 0.90 * amplitude, rising=True
    )
    rise_time = (
        time_90 - time_10
        if time_10 is not None and time_90 is not None
        else None
    )
    half_rise = _crossing_time(
        pre_peak_times, pre_peak_values, 0.50 * amplitude, rising=True
    )
    half_fall = _crossing_time(
        post_peak_times, post_peak_values, 0.50 * amplitude, rising=False
    )
    fwhm = (
        half_fall - half_rise
        if half_rise is not None and half_fall is not None
        else None
    )

    saturated = sum(
        (adc_min is not None and value <= adc_min)
        or (adc_max is not None and value >= adc_max)
        for value in voltages
    )
    detected = (
        amplitude >= detection_amplitude
        and amplitude > 0
        and (noise_rms == 0 or snr >= detection_snr)
    )

    return WaveformFeatures(
        baseline=baseline,
        noise_rms=noise_rms,
        amplitude=amplitude,
        snr=snr,
        signed_area=_trapezoid(signal_times, corrected),
        positive_area=_trapezoid(
            signal_times, [max(0.0, value) for value in corrected]
        ),
        peak_time=peak_time,
        rise_time_10_90=rise_time,
        fwhm=fwhm,
        saturated_samples=saturated,
        detected=detected,
    )


def compare_baseline_methods(
    times: list[float],
    voltages: list[float],
    **kwargs: object,
) -> dict[str, WaveformFeatures]:
    """Extrae resultados pareados para media, mediana y media recortada."""

    return {
        method: extract_features(times, voltages, method=method, **kwargs)
        for method in ("mean", "median", "trimmed_mean")
    }
