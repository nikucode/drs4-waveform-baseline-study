# Estudio sintético de longitud de la ventana de baseline

Fecha de registro previo: 20 de noviembre de 2026.

## Pregunta

¿Cómo cambia el error de la línea base y su propagación hacia amplitud, área y
tiempos reconstruidos al utilizar 20, 50 o 100 muestras previas al pulso?

## Motivación

El estudio principal fijó 50 muestras por compatibilidad con una reducción
anterior. Ese valor no demuestra por sí mismo que la ventana sea adecuada. Una
ventana corta contiene menos información; una larga puede reducir variación
estadística, pero en una adquisición real también puede incorporar deriva,
señal u otras estructuras.

## Hipótesis previas

- Con baseline constante y ruido gaussiano independiente, la dispersión de la
  media debería disminuir al aumentar la cantidad de muestras.
- La mediana podría presentar mayor dispersión que la media en el caso
  gaussiano limpio, a cambio de mayor robustez frente a valores extremos.
- Con una cantidad fija de valores extremos, su influencia sobre la media
  debería diluirse al aumentar la ventana.
- La mediana y la media recortada podrían rechazar esos casos en las
  condiciones elegidas, pero no se asumirá que lo harán para cualquier tasa o
  distribución de contaminación.
- Una ventana mayor no se declarará universalmente preferible: este primer
  barrido no incluye baseline correlacionado, pulsos previos ni contaminación
  de la ventana por la señal principal.

## Diseño pareado

Cada forma de onda se generará una sola vez y será procesada por las nueve
combinaciones de ventana (20, 50 y 100 muestras) y estimador (media, mediana y
media recortada al 10 %).

El pulso comenzará después de las primeras 100 muestras. La ventana de señal
se mantendrá fija entre 110 y 160 unidades de tiempo para que el área integrada
no cambie al modificar la longitud usada para el baseline.

## Grilla inicial

- baseline verdadero: 0,5 V;
- amplitud: 0,1 y 1,0 V;
- ruido gaussiano sigma: 0,005 y 0,020 V;
- contaminación: ninguna, un valor extremo positivo o dos valores extremos
  mixtos;
- realizaciones: 100 por condición;
- semilla inicial fija y registrada.

La contaminación se mantendrá en índices presentes en las tres ventanas. Su
magnitud y ubicación quedarán registradas en el manifiesto.

## Métricas

Por combinación se calcularán sesgo, desviación, MAE y RMSE de baseline; sesgo
y MAE de amplitud y área con signo; fracción de detección; y MAE de tiempo al
máximo, subida 10--90 % y FWHM cuando sean recuperables.

## Límites de interpretación

Los resultados solo describirán el generador y la grilla declarados. No se
usarán para escoger automáticamente una ventana en DRS4 ni para afirmar que el
ruido experimental sea gaussiano e independiente. Una extensión experimental
deberá estudiar estabilidad temporal, correlación y contaminación real por
canal y adquisición.
