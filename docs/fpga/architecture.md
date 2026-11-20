# Prototipo FPGA de media de línea base

## Alcance y contrato numérico

Este núcleo es un prototipo digital independiente de fabricante. Sus parámetros
no son especificaciones de registros ni equipos DRS4.

- Bloque: 50 muestras sin signo de 12 bits (`0..4095`).
- Acumulador: 18 bits sin signo.
- Contador: 6 bits, capaz de representar `0..50`.
- Resultado: 12 bits sin signo.
- Reset: síncrono, activo alto.
- Concurrencia: una transacción activa.

Para 50 muestras válidas:

```text
S = sum(samples)
baseline = (S + 25) // 50
```

La suma de 25 implementa redondeo al entero más cercano con empates hacia
arriba para entradas no negativas. El RTL no usa aritmética flotante. El peor
caso cabe en el acumulador:

```text
50 × 4095 = 204750 < 262144 = 2^18
```

## Interfaz y estados

Puertos: `clk`, `rst`, `start`, `sample_valid`, `sample_ready`, `sample_in`,
`result_valid` y `baseline_out`.

- `IDLE`: espera `start`. Aceptarlo limpia suma y contador, pero no consume una
  muestra en ese ciclo.
- `ACQUIRE`: `sample_ready=1`. Solo `sample_valid && sample_ready` acepta una
  muestra; una pausa no cambia suma ni contador. Otros pulsos `start` se ignoran.
- `DONE`: `result_valid=1` durante un ciclo y `sample_ready=0`; después vuelve a
  `IDLE`.

La muestra 50 se incluye en la suma. Una secuencia incompleta espera muestras o
reset. `rst` tiene prioridad y limpia estado, suma, contador, validez y salida.
`baseline_out` permanece estable desde un resultado hasta otro resultado o
reset. No existen todavía FIFO, backpressure de salida, timeout ni señal de
error.

## Ejemplo temporal abreviado

| Flanco | Estado previo | Entradas relevantes | Efecto |
|---:|---|---|---|
| 1 | IDLE | `start=1` | pasa a ACQUIRE; no consume muestra |
| 2 | ACQUIRE | `sample_valid=1` | acepta muestra 1 |
| 3 | ACQUIRE | `sample_valid=0` | pausa; no cambia la acumulación |
| … | ACQUIRE | muestras válidas | acepta muestras 2–49 |
| 52 | ACQUIRE | muestra válida 50 | suma la última muestra y calcula salida |
| 53 | DONE | — | `result_valid=1`, salida estable |
| 54 | IDLE | — | `result_valid=0`, listo para otro `start` |
