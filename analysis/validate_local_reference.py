"""Valida localmente el extractor propio contra una reducción de referencia."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import statistics
from pathlib import Path
from typing import Any


KEY_OWN = ("source", "serial", "board", "channel")
KEY_REFERENCE = ("file", "serial", "board", "channel")
EQUIVALENT_FIELDS = {
    "baseline": "baseline_mv",
    "amplitude": "peak_mv",
    "peak_time": "peak_time_ns",
    "signed_area": "signed_area_mv_ns",
    "positive_area": "positive_area_mv_ns",
    "rise_time_10_90": "rise_time_10_90_ns",
}
DEFINITION_DEPENDENT_FIELDS = {
    "fwhm": "fwhm_ns",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as source:
        return list(csv.DictReader(source))


def _key(row: dict[str, str], fields: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(row[field] for field in fields)


def _finite(value: str) -> float | None:
    if value == "":
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def _numeric_comparison(
    own: dict[tuple[str, ...], dict[str, str]],
    reference: dict[tuple[str, ...], dict[str, str]],
    own_field: str,
    reference_field: str,
    tolerance: float,
) -> dict[str, Any]:
    differences: list[float] = []
    availability_mismatches = 0
    for key in sorted(own):
        left = _finite(own[key][own_field])
        right = _finite(reference[key][reference_field])
        if (left is None) != (right is None):
            availability_mismatches += 1
        elif left is not None and right is not None:
            differences.append(left - right)
    absolute = [abs(value) for value in differences]
    return {
        "shared_finite": len(differences),
        "availability_mismatches": availability_mismatches,
        "differences_above_tolerance": sum(
            value > tolerance for value in absolute
        ),
        "median_absolute_difference": (
            statistics.median(absolute) if absolute else None
        ),
        "max_absolute_difference": max(absolute) if absolute else None,
    }


def validate_reference(
    own_rows: list[dict[str, str]],
    reference_rows: list[dict[str, str]],
    *,
    baseline_samples: int = 50,
    tolerance: float = 1e-9,
) -> dict[str, Any]:
    """Compara campos equivalentes y separa definiciones incompatibles."""

    own_mean = [row for row in own_rows if row["method"] == "mean"]
    own = {_key(row, KEY_OWN): row for row in own_mean}
    reference = {_key(row, KEY_REFERENCE): row for row in reference_rows}
    if set(own) != set(reference):
        raise ValueError("las claves archivo/serial/placa/canal no coinciden")
    if baseline_samples <= 1:
        raise ValueError("baseline_samples debe ser mayor que uno")

    equivalent = {
        own_field: _numeric_comparison(
            own,
            reference,
            own_field,
            reference_field,
            tolerance,
        )
        for own_field, reference_field in EQUIVALENT_FIELDS.items()
    }

    population_factor = math.sqrt((baseline_samples - 1) / baseline_samples)
    normalized_noise_differences = []
    normalized_snr_differences = []
    for key in own:
        expected_noise = float(reference[key]["baseline_rms_mv"]) * population_factor
        expected_snr = float(reference[key]["snr"]) / population_factor
        normalized_noise_differences.append(
            float(own[key]["noise_rms"]) - expected_noise
        )
        normalized_snr_differences.append(float(own[key]["snr"]) - expected_snr)

    categorical = {
        "saturated_samples_mismatches": sum(
            int(own[key]["saturated_samples"])
            != int(reference[key]["saturation_samples"])
            for key in own
        ),
        "detection_mismatches": sum(
            (own[key]["detected"] == "True")
            != bool(int(reference[key]["detected_5sigma"]))
            for key in own
        ),
    }
    definition_dependent = {
        own_field: _numeric_comparison(
            own,
            reference,
            own_field,
            reference_field,
            tolerance,
        )
        for own_field, reference_field in DEFINITION_DEPENDENT_FIELDS.items()
    }

    return {
        "matched_rows": len(own),
        "tolerance": tolerance,
        "equivalent_fields": equivalent,
        "known_normalization_difference": {
            "description": (
                "own noise uses population RMS; reference uses sample standard "
                "deviation with ddof=1"
            ),
            "population_factor": population_factor,
            "noise_max_absolute_residual": max(
                map(abs, normalized_noise_differences)
            ),
            "snr_max_absolute_residual": max(map(abs, normalized_snr_differences)),
        },
        "categorical_fields": categorical,
        "definition_dependent_fields": {
            "description": (
                "FWHM uses intentionally different interpolation rules; "
                "differences are reported, not failures"
            ),
            **definition_dependent,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--own", type=Path, required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results/local_reference_validation.json"),
    )
    parser.add_argument("--baseline-samples", type=int, default=50)
    args = parser.parse_args()

    report = validate_reference(
        _read(args.own),
        _read(args.reference),
        baseline_samples=args.baseline_samples,
    )
    report["scope"] = "local validation; reference products are not republished"
    report["inputs"] = {
        "own": {"file": args.own.name, "sha256": _sha256(args.own)},
        "reference": {
            "file": args.reference.name,
            "sha256": _sha256(args.reference),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"Matched rows: {report['matched_rows']}")
    print(f"Local validation: {args.output}")


if __name__ == "__main__":
    main()
