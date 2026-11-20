"""Adaptador incremental propio para adquisiciones XML de DRS4.

El módulo preserva identidad de evento, placa y canal. No contiene ni deriva
de macros o extractores recibidos junto con los datos experimentales.
"""

from __future__ import annotations

import math
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator


class DRS4FormatError(ValueError):
    """Indica que un registro no cumple la estructura mínima esperada."""


@dataclass(frozen=True)
class DRS4Waveform:
    source: str
    serial: int
    timestamp: str
    horizontal_unit: str
    vertical_unit: str
    board: int
    trigger_cell: int
    channel: str
    times: tuple[float, ...]
    voltages: tuple[float, ...]


def _tag(element: ET.Element) -> str:
    """Retira un namespace XML opcional del nombre de una etiqueta."""

    return element.tag.rsplit("}", 1)[-1]


def _required_text(parent: ET.Element, name: str, context: str) -> str:
    for child in parent:
        if _tag(child) == name and child.text is not None:
            return child.text.strip()
    raise DRS4FormatError(f"falta {name} en {context}")


def _parse_data(
    channel: ET.Element, context: str
) -> tuple[tuple[float, ...], tuple[float, ...]]:
    times: list[float] = []
    voltages: list[float] = []
    for sample in channel:
        if _tag(sample) != "Data":
            continue
        text = (sample.text or "").strip()
        try:
            time_text, voltage_text = text.split(",", 1)
            time = float(time_text)
            voltage = float(voltage_text)
        except (ValueError, TypeError) as error:
            raise DRS4FormatError(
                f"muestra inválida en {context}: {text!r}"
            ) from error
        if not math.isfinite(time) or not math.isfinite(voltage):
            raise DRS4FormatError(f"muestra no finita en {context}")
        times.append(time)
        voltages.append(voltage)

    if not times:
        raise DRS4FormatError(f"canal sin muestras en {context}")
    if any(right <= left for left, right in zip(times, times[1:])):
        raise DRS4FormatError(f"tiempos no crecientes en {context}")
    return tuple(times), tuple(voltages)


def _parse_event(event: ET.Element, source: str) -> list[DRS4Waveform]:
    serial_text = _required_text(event, "Serial", source)
    try:
        serial = int(serial_text)
    except ValueError as error:
        raise DRS4FormatError(f"serial inválido en {source}: {serial_text!r}") from error

    timestamp = _required_text(event, "Time", f"evento {serial}")
    horizontal_unit = _required_text(event, "HUnit", f"evento {serial}")
    vertical_unit = _required_text(event, "VUnit", f"evento {serial}")
    records: list[DRS4Waveform] = []

    for board_element in event:
        board_tag = _tag(board_element)
        if not board_tag.startswith("Board_"):
            continue
        try:
            board = int(board_tag.removeprefix("Board_"))
            trigger_cell = int(
                _required_text(board_element, "Trigger_Cell", f"evento {serial}")
            )
        except ValueError as error:
            raise DRS4FormatError(
                f"placa o trigger cell inválidos en evento {serial}"
            ) from error

        for channel_element in board_element:
            channel = _tag(channel_element)
            if not channel.startswith("CHN"):
                continue
            context = f"evento {serial}, placa {board}, canal {channel}"
            times, voltages = _parse_data(channel_element, context)
            records.append(
                DRS4Waveform(
                    source=source,
                    serial=serial,
                    timestamp=timestamp,
                    horizontal_unit=horizontal_unit,
                    vertical_unit=vertical_unit,
                    board=board,
                    trigger_cell=trigger_cell,
                    channel=channel,
                    times=times,
                    voltages=voltages,
                )
            )

    if not records:
        raise DRS4FormatError(f"evento {serial} sin canales en {source}")
    return records


def iter_drs4_waveforms(path: str | Path) -> Iterator[DRS4Waveform]:
    """Entrega registros uno a uno y libera cada evento después de leerlo."""

    source_path = Path(path)
    try:
        parser = ET.iterparse(source_path, events=("start", "end"))
        try:
            _, root = next(parser)
        except StopIteration as error:
            raise DRS4FormatError(f"XML vacío en {source_path.name}") from error
        for action, element in parser:
            if action == "end" and _tag(element) == "Event":
                records = _parse_event(element, source_path.name)
                element.clear()
                root.clear()
                yield from records
    except ET.ParseError as error:
        raise DRS4FormatError(f"XML inválido en {source_path.name}: {error}") from error
