# Bitácora verificable del primer núcleo FPGA

**Fecha:** 20 de noviembre de 2026

**Objetivo:** consolidar un estimador sintetizable de la media de línea base para
50 muestras U12, con referencia Python y comparación automática Python–RTL.

## Archivos relevantes

- `src/fixed_point.py` y `tests/test_fixed_point.py`: contrato entero y pruebas.
- `fpga/rtl/baseline_mean.sv`: núcleo RTL.
- `fpga/tb/tb_baseline_mean.sv`: testbench de números, pausas, reset y control.
- `fpga/verify.py`: vectores, simulación, comparación y síntesis.
- `docs/fpga/architecture.md`: contrato temporal y numérico.

## Evidencia

Antes de esta consolidación, el usuario comunicó resultados satisfactorios con
Icarus Verilog 13.0 y Yosys 0.66. En esta ejecución se comprobaron nuevamente:

```bash
python -m fpga.verify
python -m unittest discover -s tests
yosys -p "read_verilog -sv fpga/rtl/baseline_mean.sv; hierarchy -check -top baseline_mean; proc; opt; check; stat"
```

Versiones observadas: Python 3.14.8, Icarus Verilog 13.0 y Yosys 0.66. Las 7
pruebas numéricas pasaron. El control negativo detectó la discrepancia inyectada.
La simulación comparó 79 de 79 bloques emitidos por el RTL con la referencia
Python: cero discrepancias. La suite completa pasó 43 pruebas.

La síntesis genérica terminó correctamente y `check` informó cero problemas. No
se infirieron latches. Las estadísticas genéricas indicaron 30 celdas: 3 `$add`,
1 `$div`, 8 `$mux`, 4 `$sdffe` y lógica auxiliar. Estas cantidades no equivalen
a LUT ni a recursos de un dispositivo concreto.

## Incidencias y límites

No se observaron fallos durante esta consolidación, por lo que no se alteraron
RTL ni expectativas para obtener un resultado positivo. Los temporales se
generaron fuera del repositorio. No se usaron ni prepararon datos experimentales.
El núcleo ha sido implementado, simulado y sintetizado genéricamente, pero no se
ha implementado para una FPGA específica ni validado en una placa física.
