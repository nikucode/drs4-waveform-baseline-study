# DRS4 Waveform Baseline Study

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

## Estado

La primera etapa implementa media, mediana y media recortada simétrica para
una región previa al pulso. Incluye generadores reproducibles de regiones de
baseline y pulsos triangulares sintéticos con verdad conocida. El extractor
inicial calcula amplitud, ruido RMS, SNR, áreas, tiempo al máximo, tiempo de
subida, FWHM, saturación y detección para los tres métodos de forma pareada.
El primer barrido sintético estudia amplitud, ruido, deriva y valores extremos.
El análisis de registros experimentales todavía está pendiente.

- [Especificación](docs/especificacion.md)
- [Procedencia y publicación](docs/procedencia.md)

## Estructura prevista

```text
src/        implementación propia
tests/      señales sintéticas y pruebas automatizadas
docs/       método, procedencia, resultados y limitaciones
results/    productos regenerables ignorados por Git
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

## Generar el informe y las figuras

Después del barrido:

```bash
python -m pip install -r requirements.txt
python -m analysis.report_synthetic_results
```

Los productos sintéticos seleccionados se publican en
[`artifacts/baseline_sensitivity_01`](artifacts/baseline_sensitivity_01/).
El informe conserva las limitaciones del modelo y no utiliza registros DRS4.

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

## Relación con MiniNeutron

Este estudio es independiente de MiniNeutron. Ambos comparten preguntas
generales de procesamiento de señales, pero los registros DRS4 no validan la
respuesta detectora ni la DAQ simulada de MiniNeutron.
