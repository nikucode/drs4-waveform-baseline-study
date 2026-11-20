"""Referencia entera para los prototipos digitales del proyecto."""

from __future__ import annotations

from collections.abc import Iterable


SAMPLE_COUNT = 50
U12_MAX = 4095


def baseline_mean_u12(samples: Iterable[int]) -> int:
    """Calcula la media U12 de 50 muestras con empates hacia arriba.

    La entrada se copia para validarla, pero sus objetos no se modifican. Solo
    se aceptan enteros Python exactos: ``bool`` y tipos numéricos implícitamente
    convertibles quedan rechazados.
    """

    try:
        values = tuple(samples)
    except TypeError as error:
        raise TypeError("samples debe ser un iterable de enteros") from error

    if len(values) != SAMPLE_COUNT:
        raise ValueError(f"se requieren exactamente {SAMPLE_COUNT} muestras")
    for index, value in enumerate(values):
        if type(value) is not int:
            raise TypeError(f"la muestra {index} no es un entero Python")
        if not 0 <= value <= U12_MAX:
            raise ValueError(f"la muestra {index} está fuera de U12")

    total = sum(values)
    return (total + SAMPLE_COUNT // 2) // SAMPLE_COUNT
