# Coordinación temporal en un intervalo declarado

La herramienta `evaluar_coordinacion_intervalo_p5e` amplía la comprobación
puntual P5E: busca el menor margen temporal en todo un intervalo de corriente
declarado. Consume los dispositivos y datasets TCC ya registrados en P5A/P5B.
No resuelve cortocircuitos ni selecciona ajustes automáticamente.

## Uso

Registrar los dos dispositivos, sus curvas y sus puntos numéricos con procedencia.
Las curvas deben representar `TOTAL_CLEARING_TIME`. Después invocar:

```json
{
  "estudio": "coordinacion_intervalo",
  "parametros": {
    "dispositivo_downstream": "QF_alimentador",
    "dispositivo_upstream": "QF_general",
    "corriente_minima_downstream_a": 1000,
    "corriente_maxima_downstream_a": 12000,
    "factor_corriente_upstream": 1,
    "margen_minimo_s": 0.2,
    "fuente_relacion": "Unifilar del proyecto, revisión y par de dispositivos",
    "fuente_corrientes": "Estudio y escenario que justifican el intervalo y el factor"
  }
}
```

Este objeto es un ejemplo de invocación, no una selección de corrientes o márgenes
para una instalación. Deben sustituirse por valores justificados. El factor es
obligatorio incluso si vale 1: `I_upstream = factor * I_downstream`. Es una
relación constante declarada, que debe ser válida para el escenario estudiado.
No se deduce de transformadores, TC, nombres, topología o contribuciones de motores.
Si esa relación cambia con la falla, se requieren estudios separados adecuados;
esta ruta no traduce corrientes de una red ramificada.

## Resultado

| Estado | Significado |
| --- | --- |
| `PASS` | El margen mínimo calculado cumple el criterio en todo el rango cubierto por las curvas declaradas |
| `FAIL` | El cálculo es válido, pero existe una corriente donde el margen es insuficiente |
| `COORDINATION_RANGE_NOT_READY` | Faltan curvas, semántica, cobertura continua o resolución numérica; no se publica un mínimo válido |

`worst_case` identifica ambas corrientes, el tiempo máximo downstream, el mínimo
upstream y su diferencia. `intervals` contiene los tramos y candidatos evaluados.
Se guardan copias completas del dispositivo y dataset con un SHA-256 reproducible
por cada entrada. El resultado se registra en el workspace como
`protection_coordination_range`, separado del resultado puntual y ligado a la
revisión por el registro existente. Un bloqueo queda `resultados_validos=false`;
un incumplimiento calculado conserva `resultados_validos=true`.

El manifiesto P8 admite ahora `protection.coordination_ranges` como solicitud
explícita: enlaza límites P4 MIN/MAX de la misma ejecución, incorpora el criterio
a `design_checks.json` y guarda una traza íntegra con tabla en visor e informe.
Ver [formato y límites de integración](P8_COORDINACION_EXPEDIENTE.md).
La llamada P5E independiente sigue disponible; no cambia su alcance físico.

## Método y cobertura

Se conserva la interpolación P5B lineal en coordenadas log(I)-log(t). Cada rango
debe caber por completo en un segmento explícito de cada curva. Los huecos,
discontinuidades y zonas fuera de dominio bloquean el rango completo: no se
recorta la solicitud ni se unen segmentos separados.

Se divide el intervalo en todos los puntos de ambas curvas, convirtiendo los
puntos upstream con el factor declarado. En cada tramo, con `x=log(I/I_izquierda)`,
el margen es `m(x)=A*exp(p*x)-B*exp(q*x)`. Su mínimo se encuentra entre los
extremos y, cuando existe dentro del tramo, el punto estacionario:

```text
x* = [log(|q|) + log(B) - log(|p|) - log(A)] / (p-q)
```

Ese candidato solo existe para pendientes no nulas de igual signo y distintas.
Se conservan también los máximos estacionarios como candidatos; no perjudican
la elección del mínimo. Las pendientes iguales, constantes o de distinto signo
solo necesitan extremos. El mínimo global incluye todos los tramos.

Es una evaluación analítica de las curvas interpoladas en precisión flotante,
no un barrido de unos pocos puntos ni una garantía sobre la curva física entre
datos publicados. Un intervalo no resoluble o un valor no representable bloquea
el resultado. No se suma una tolerancia favorable para convertir FAIL en PASS;
los casos al límite requieren revisión de precisión y criterios.

## Límite de ingeniería

El cálculo usa `upstream_time_min_s - downstream_time_max_s`. No acredita que el
dispositivo upstream no comience a actuar: los tiempos totales de despeje no
representan automáticamente su característica de no actuación. No acredita
selectividad total/parcial, energética o instantánea; tampoco backup/cascading,
capacidad de corte o Icw. Las tolerancias ausentes no se inventan.

La [guía primaria ABB sobre selectividad](https://new.abb.com/low-voltage/el/our-solutions/selectivity/focus-on/standard-requirements)
distingue la comparación de características y los datos de ensayo del fabricante
para actuación instantánea. Se usa para delimitar el alcance; no aporta puntos
numéricos a este banco ni sustituye una revisión normativa licenciada.

## Verificación reproducible

```text
python -m pytest tests/test_p5e_coordination_range.py tests/test_p5e_temporal_coordination.py tests/test_study_dispatch.py tests/test_engine_selection.py -q
python scripts/verify_protection_coordination_range_mcp.py --output outputs/coordination-range
```

El banco usa datos sintéticos identificados como `TEST_DATA`. Incluye un fallo
intermedio aunque ambos extremos cumplan; un mínimo interior analítico a 200 A;
bandas conservadoras; escalas de corriente distintas; huecos; otras semánticas;
entrada no finita; igualdad; precisión insuficiente; snapshots y registro de
resultados bloqueados. Doce curvas por tramos se contrastan con interpolación
NumPy, optimización acotada SciPy y 4.001 muestras por caso, independientes del
algoritmo de extremos operativo.

El script stdio registra todas las llamadas, entradas y salidas JSON, con hashes
de archivos y fuentes en `Summary.json`. La lane `engineering-acceptance` lo
ejecuta en Windows y Linux. Esta evidencia no cierra Brno ni valida una pareja
de equipos comerciales o una instalación real.
