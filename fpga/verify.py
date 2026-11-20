"""Verificación reproducible Python–RTL del estimador de línea base."""

from __future__ import annotations

import math
import random
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from src.fixed_point import baseline_mean_u12
from src.synthetic import baseline_region


ROOT = Path(__file__).resolve().parents[1]
RTL = ROOT / "fpga" / "rtl" / "baseline_mean.sv"
TESTBENCH = ROOT / "fpga" / "tb" / "tb_baseline_mean.sv"


def voltage_to_u12(value: float, *, full_scale: float = 1.0) -> int:
    """Cuantiza explícitamente voltios en [0, full_scale] a códigos U12."""

    if not math.isfinite(value) or not math.isfinite(full_scale) or full_scale <= 0:
        raise ValueError("valor y escala deben ser finitos; la escala debe ser positiva")
    normalized = min(max(value / full_scale, 0.0), 1.0)
    return int(normalized * 4095 + 0.5)


def build_vectors() -> list[list[int]]:
    """Combina casos manuales, pseudoaleatorios y regiones sintéticas."""

    vectors = [
        [0] * 50,
        [4095] * 50,
        [1729] * 50,
        [1] * 24 + [0] * 26,
        [1] * 25 + [0] * 25,
        [1] * 26 + [0] * 24,
        list(range(50)),
    ]
    rng = random.Random(20261120)
    vectors.extend([[rng.randrange(4096) for _ in range(50)] for _ in range(64)])
    for index in range(8):
        volts = baseline_region(
            baseline=(0.2, 0.5, 0.8, 0.95)[index % 4],
            noise_sigma=0.01 + 0.005 * (index % 2),
            seed=7000 + index,
        )
        vectors.append([voltage_to_u12(value) for value in volts])
    return vectors


def compare_results(expected: list[int], actual: list[int]) -> list[tuple[int, int | None, int | None]]:
    """Devuelve discrepancias, incluyendo resultados ausentes o adicionales."""

    differences = []
    for index in range(max(len(expected), len(actual))):
        reference = expected[index] if index < len(expected) else None
        observed = actual[index] if index < len(actual) else None
        if reference != observed:
            differences.append((index, reference, observed))
    return differences


def run_numeric_tests() -> bool:
    result = subprocess.run(
        [sys.executable, "-m", "unittest", "tests.test_fixed_point", "-q"],
        cwd=ROOT,
        check=False,
    )
    return result.returncode == 0


def run_cross_verification(vectors: list[list[int]]) -> tuple[str, int, int]:
    iverilog = shutil.which("iverilog")
    vvp = shutil.which("vvp")
    if not iverilog or not vvp:
        print("BLOCKED: RTL simulation unavailable")
        return "BLOCKED", 0, 0

    expected = [baseline_mean_u12(vector) for vector in vectors]
    with tempfile.TemporaryDirectory(prefix="drs4_fpga_verify_") as directory:
        temporary = Path(directory)
        vector_file = temporary / "vectors.txt"
        output_file = temporary / "rtl_results.txt"
        executable = temporary / "tb.out"
        vector_file.write_text(
            "".join(
                " ".join(map(str, [reference, *vector])) + "\n"
                for reference, vector in zip(expected, vectors)
            ),
            encoding="utf-8",
        )
        compile_result = subprocess.run(
            [iverilog, "-g2012", "-s", "tb_baseline_mean", "-o", str(executable), str(RTL), str(TESTBENCH)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        if compile_result.returncode:
            print(compile_result.stderr, file=sys.stderr)
            return "FAIL", 0, len(vectors)
        simulation = subprocess.run(
            [vvp, str(executable), f"+VECTORS={vector_file}", f"+OUTPUT={output_file}"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        if simulation.returncode:
            print(simulation.stdout, file=sys.stderr)
            print(simulation.stderr, file=sys.stderr)
            return "FAIL", 0, len(vectors)
        actual = [int(line) for line in output_file.read_text().splitlines()]
        differences = compare_results(expected, actual)
        if differences:
            print(f"FAIL: {len(differences)} discrepancias; primeras: {differences[:5]}")
            return "FAIL", len(vectors), len(differences)
    print(f"PASS: {len(vectors)} bloques Python–RTL; 0 discrepancias")
    return "PASS", len(vectors), 0


def run_synthesis() -> str:
    yosys = shutil.which("yosys")
    if not yosys:
        print("NOT RUN: Yosys unavailable")
        return "NOT RUN"
    script = f"read_verilog -sv {RTL}; hierarchy -check -top baseline_mean; proc; opt; check; stat"
    result = subprocess.run(
        [yosys, "-q", "-p", script], cwd=ROOT, text=True,
        capture_output=True, check=False,
    )
    if result.returncode:
        print(result.stdout)
        print(result.stderr, file=sys.stderr)
        print("FAIL: synthesis")
        return "FAIL"
    print(result.stdout)
    print("PASS: generic Yosys synthesis")
    return "PASS"


def main() -> int:
    if not run_numeric_tests():
        print("FAIL: Python numeric tests")
        return 1
    print("PASS: Python numeric tests")

    # Control negativo aislado del comparador, sin modificar el RTL.
    if compare_results([7], [8]) != [(0, 7, 8)]:
        print("FAIL: negative comparison control")
        return 1
    print("PASS: negative comparison control detected an injected mismatch")

    vectors = build_vectors()
    simulation, checked, discrepancies = run_cross_verification(vectors)
    synthesis = run_synthesis()
    print(
        f"SUMMARY: vectors={len(vectors)} checked={checked} "
        f"discrepancies={discrepancies} simulation={simulation} synthesis={synthesis}"
    )
    return 0 if simulation == "PASS" and synthesis != "FAIL" else 2 if simulation == "BLOCKED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
