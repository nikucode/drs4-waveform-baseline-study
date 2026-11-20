# DRS4 Waveform Baseline Study

[![Tests](https://github.com/nikucode/drs4-waveform-baseline-study/actions/workflows/tests.yml/badge.svg)](https://github.com/nikucode/drs4-waveform-baseline-study/actions/workflows/tests.yml)

Estudio educativo y reproducible sobre la sensibilidad de características de
formas de onda frente al método de estimación de línea base.

## Pregunta

¿Cuánto cambian la amplitud, el área y los parámetros temporales reconstruidos
cuando la línea base se estima mediante media, mediana o media recortada?

La comparación se diseñará de forma pareada: cada método analizará exactamente
la misma forma de onda. La validación pública utilizará señales sintéticas con
línea base conocida.

## Procedencia y alcance

El interés por este problema nació al estudiar registros DRS4 de
hodoscopio/PMT y LED compartidos por Javi en el contexto de trabajo SAPHIR.
Alex no realizó esas adquisiciones. Los XML, macros, informes y muestras
recibidas conservan su autoría y no forman parte de este repositorio.

Este repositorio contendrá solamente:

- código nuevo para comparar estimadores;
- pruebas con señales sintéticas propias;
- metodología y decisiones documentadas;
- resultados sintéticos reproducibles;
- eventualmente, resultados experimentales agregados cuya publicación haya
  sido autorizada.

No contendrá datos experimentales ni código de terceros sin permiso y
atribución confirmados.

## Estado y resultados verificables

- Implementación propia de media, mediana y media recortada simétrica.
- Extracción pareada de amplitud, ruido RMS, SNR, áreas, tiempo al máximo,
  subida 10–90 %, FWHM, saturación y detección.
- Barrido público de 1.080 formas de onda sintéticas: 3.240 resultados
  evento–método y 162 resúmenes por condición.
- Informe, tabla agregada, manifiesto y dos figuras regenerables.
- Adaptador XML DRS4 incremental propio, validado con fixtures sintéticos.
- Pipeline local de sensibilidad aplicado a muestras recibidas de hodoscopio/
  PMT y LED; los datos y derivados experimentales no se publican.
- Validador local fila por fila contra la reducción colaborativa anterior,
  manteniendo separadas equivalencias y diferencias metodológicas.
- 29 pruebas automatizadas; GitHub Actions las ejecuta en Python 3.11 y 3.12.

- [Especificación](docs/especificacion.md)
- [Procedencia y publicación](docs/procedencia.md)
- [Estudio de longitud de ventana](docs/estudio_longitud_ventana.md)

## Estructura

```text
src/        estimadores, extractor de características y adaptador XML propio
analysis/   barridos, inventarios, informes y validación local
tests/      fixtures sintéticos y pruebas automatizadas
docs/       especificación, procedencia y límites de publicación
artifacts/  informe y resultados exclusivamente sintéticos publicables
results/    productos regenerables y análisis locales ignorados por Git
```

## Ejecutar las pruebas

Desde la raíz del repositorio:

```bash
python -m unittest discover -v
```

La media recortada usa por defecto una fracción de 0,10 y elimina
`floor(N * 0,10)` muestras de cada extremo. Con la región prevista de 50
muestras, se eliminan cinco valores inferiores y cinco superiores.

## Ejecutar el primer barrido sintético

```bash
python -m analysis.study_baseline_sensitivity \
  --output-dir results/baseline_sensitivity_01 \
  --trials 20
```

La corrida compara los métodos sobre las mismas formas de onda y conserva una
fila por evento y método en `event_results.csv`. `summary.csv` mantiene
separadas las condiciones de amplitud, ruido, deriva y valores extremos. El
manifiesto registra la configuración, los desplazamientos utilizados como
valores extremos y hashes SHA-256 del código que generó los resultados.

## Estudiar la longitud de la ventana

La segunda extensión sintética compara 20, 50 y 100 muestras de baseline sobre
las mismas formas de onda y mantiene fija la ventana de señal:

```bash
python -m analysis.study_baseline_window \
  --output-dir results/baseline_window_01 \
  --trials 100
```

La pregunta, hipótesis y límites se registraron antes del barrido en
[`docs/estudio_longitud_ventana.md`](docs/estudio_longitud_ventana.md).

Para publicar únicamente el resumen y las figuras sintéticas:

```bash
python -m analysis.report_baseline_window
```

El resultado se conserva en
[`artifacts/baseline_window_01`](artifacts/baseline_window_01/) y compara los
valores simulados con las dependencias analíticas de la media `σ/sqrt(N)` y
`0,50/N`.

## Generar el informe y las figuras

Después del barrido:

```bash
python -m pip install -r requirements.txt
python -m analysis.report_synthetic_results
```

Los productos sintéticos seleccionados se publican en
[`artifacts/baseline_sensitivity_01`](artifacts/baseline_sensitivity_01/).
El informe conserva las limitaciones del modelo y no utiliza registros DRS4.

## Prototipo FPGA de línea base

El prototipo independiente de fabricante calcula la media entera de bloques de
50 muestras U12. Su contrato, RTL, referencia Python y verificación cruzada se
encuentran en la [arquitectura](docs/fpga/architecture.md), la
[guía de aprendizaje](docs/fpga/guia_aprendizaje.md), la
[bitácora verificable](docs/fpga/bitacora.md), [`fpga/`](fpga/) y
[`src/fixed_point.py`](src/fixed_point.py). Para ejecutar la verificación:

```bash
python -m fpga.verify
```

La ejecución documentada comprobó 79/79 bloques Python–RTL sin discrepancias y
una síntesis genérica con Yosys sin problemas estructurales. Esto no constituye
implementación ni validación en una FPGA física. La integración usa solamente
vectores manuales, pseudoaleatorios y señales sintéticas cuantizadas
explícitamente; la procedencia de los registros experimentales permanece
separada y no se incorporan al flujo FPGA.

## Adaptador local DRS4

`src/drs4_xml.py` implementa un lector incremental propio que conserva evento,
placa, canal, unidades, celda de trigger y pares tiempo–voltaje. Se prueba con
un XML completamente sintético; los registros recibidos no se incluyen en el
repositorio.

Para generar únicamente un inventario estructural local:

```bash
python -m analysis.inspect_local_drs4 \
  /ruta/privada/muestra_cosmicos_10_eventos.xml \
  /ruta/privada/muestra_led_10_eventos.xml
```

La salida queda bajo `results/`, directorio ignorado por Git.

## Comparación local pareada

El adaptador puede conectarse con el extractor propio para medir cuánto cambian
las características de cada registro al modificar solamente el estimador de
baseline:

```bash
python -m analysis.study_local_drs4_baseline \
  /ruta/privada/muestra_cosmicos_10_eventos.xml \
  /ruta/privada/muestra_led_10_eventos.xml
```

La configuración predeterminada reproduce valores de compatibilidad de una
reducción colaborativa anterior (50 muestras, ventana 50–160 ns, SNR 5,
amplitud 3 mV y techo 949,9 mV). Estos parámetros son modificables y no se
presentan como una calibración independiente. Las tablas experimentales se
mantienen bajo `results/` hasta contar con autorización para publicar derivados.

## Validación local contra la reducción anterior

Los resultados del método de media pueden contrastarse fila por fila con una
tabla colaborativa de referencia sin copiarla al repositorio:

```bash
python -m analysis.validate_local_reference \
  --own results/local_drs4_baseline_01/event_method_results.csv \
  --reference /ruta/privada/metricas_por_evento.csv
```

El validador separa campos matemáticamente equivalentes, la diferencia conocida
entre RMS poblacional y desviación muestral, y parámetros cuyas definiciones
son deliberadamente distintas (actualmente FWHM interpolado frente a anchura
discreta). El informe resultante permanece bajo `results/`.

## Relación con MiniNeutron

Este estudio es independiente de MiniNeutron. Ambos comparten preguntas
generales de procesamiento de señales, pero los registros DRS4 no validan la
respuesta detectora ni la DAQ simulada de MiniNeutron.
