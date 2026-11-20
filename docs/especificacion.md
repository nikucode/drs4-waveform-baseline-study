# Especificación del estudio de línea base

Fecha de inicio: 20 de noviembre de 2026.

## 1. Objetivo

Evaluar de manera reproducible cuánto depende la extracción de características
de una forma de onda del estimador utilizado para calcular su línea base.

El estudio debe separar:

1. exactitud conocida sobre señales sintéticas;
2. sensibilidad entre métodos sobre registros experimentales compartidos;
3. interpretación física, que requiere información del montaje y no se
   deducirá únicamente desde los archivos.

## 2. Pregunta de investigación

¿Cómo cambian la amplitud, el área, la relación señal-ruido y los parámetros
temporales reconstruidos al utilizar media, mediana o media recortada para
estimar la línea base de formas de onda digitalizadas?

## 3. Hipótesis previas

- La media y la mediana deberían producir resultados semejantes cuando la
  región previa al pulso es estable y no contiene valores extremos.
- La media podría ser más sensible a valores atípicos o contaminación de la
  región de línea base.
- La mediana y la media recortada podrían ser más robustas frente a esos
  valores, pero no se asumirá que siempre son más exactas.
- Las diferencias deberían afectar proporcionalmente más a pulsos pequeños y
  a integrales calculadas sobre ventanas extensas.
- El método preferible podría cambiar según canal, adquisición o nivel de
  ruido; no se definirá anticipadamente un ganador.

Estas hipótesis se registran antes de observar los resultados del nuevo
barrido.

## 4. Métodos de línea base

Todos utilizarán la misma región inicial de 50 muestras, preservada por
compatibilidad con la reducción anterior.

### Media

\[
B_{\mathrm{media}}=\frac{1}{N}\sum_{i=1}^{N}V_i.
\]

### Mediana

Valor central de las muestras ordenadas. Para un número par se utiliza la media
de los dos valores centrales.

### Media recortada al 10 %

Se ordenan las 50 muestras, se eliminan las cinco inferiores y las cinco
superiores y se calcula la media de las 40 restantes.

El porcentaje y la regla de redondeo deben quedar registrados en cada corrida.

## 5. Diseño pareado

Cada forma de onda se leerá una sola vez. Sus tres resultados compartirán:

- archivo y adquisición;
- serial de evento;
- placa y canal;
- eje temporal;
- muestras de amplitud;
- ventana de señal;
- reglas de saturación y calidad.

Solo cambiará el estimador de línea base. Esto permite calcular diferencias
evento por evento sin mezclarlas con realizaciones diferentes.

## 6. Características por comparar

Para cada método se conservarán al menos:

- línea base estimada;
- ruido RMS respecto de esa línea base;
- amplitud máxima corregida;
- relación señal-ruido;
- área con signo;
- área positiva;
- tiempo al máximo;
- tiempo de subida 10–90 %;
- FWHM discreto;
- cantidad de muestras saturadas;
- resultado del criterio de detección vigente.

La carga equivalente no se tratará como ganancia del PMT. Si se conserva la
conversión por 50 ohm, se identificará explícitamente como una magnitud
derivada bajo ese supuesto.

## 7. Métricas del estudio

### Validación sintética

Como la línea base verdadera será conocida:

- error y error absoluto del baseline;
- sesgo y dispersión por método;
- error de amplitud y área;
- sensibilidad a uno o más valores extremos;
- sensibilidad a deriva gradual;
- proporción de cruces y parámetros temporales recuperables.

### Sensibilidad experimental

Sin baseline verdadero no se hablará de exactitud. Se calcularán:

- diferencias pareadas entre métodos;
- mediana y percentiles de esas diferencias;
- porcentaje de eventos cuya clasificación de detección cambia;
- eventos con discrepancias grandes para inspección local;
- resultados separados por archivo, placa y canal.

No se mezclarán canales ni adquisiciones para producir un único promedio sin
mostrar primero sus resultados separados.

## 8. Datos y fases

1. Señales sintéticas públicas con condiciones conocidas.
2. Muestras locales de 10 eventos cósmicos y 10 LED para comprobar el flujo.
3. Cuatro XML completos, solo después de validar las fases anteriores y medir
   uso de memoria y tiempo.

Los XML y muestras experimentales no se copiarán al repositorio público.

## 9. Productos previstos

- módulo de estimadores de baseline;
- extractor o adaptador propio y documentado;
- pruebas unitarias y de regresión sintética;
- manifiesto de configuración y hashes del código;
- tabla agregada por adquisición, canal y método;
- informe con método, resultados, limitaciones y procedencia;
- figuras regenerables que no expongan datos no autorizados.

## 10. Criterios de término

El estudio se considerará terminado cuando:

- los tres métodos estén implementados y probados;
- las señales sintéticas recuperen resultados esperados dentro de tolerancias
  explícitas;
- la comparación pareada funcione sobre las dos muestras locales;
- Alex haya ejecutado las pruebas y pueda explicar cada estimador;
- se documenten las discrepancias sin convertir sensibilidad en exactitud;
- se separe claramente lo publicable de lo que permanece local;
- cualquier resultado experimental público tenga permiso y atribución.

## 11. No objetivos

- atribuir a Alex la adquisición DRS4;
- estimar eficiencia absoluta de detector;
- calcular ganancia absoluta del PMT sin calibración;
- interpretar diferencias temporales como tiempo de vuelo;
- validar MiniNeutron con estos registros;
- declarar un estimador universalmente superior.
