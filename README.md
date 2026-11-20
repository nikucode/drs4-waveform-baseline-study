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

Actualmente se encuentra definida la especificación del estudio. La
implementación y los resultados todavía están pendientes.

- [Especificación](docs/especificacion.md)
- [Procedencia y publicación](docs/procedencia.md)

## Estructura prevista

```text
src/        implementación propia
tests/      señales sintéticas y pruebas automatizadas
docs/       método, procedencia, resultados y limitaciones
results/    productos regenerables ignorados por Git
```

## Relación con MiniNeutron

Este estudio es independiente de MiniNeutron. Ambos comparten preguntas
generales de procesamiento de señales, pero los registros DRS4 no validan la
respuesta detectora ni la DAQ simulada de MiniNeutron.
