# Benchmarks P1 — flujo de potencia y caída de tensión

## Objetivo

Validar cuantitativamente la cadena MCP Eléctrico → OpenDSS → postproceso para los módulos `power_flow` y `voltage_drop`, usando una referencia numérica independiente de OpenDSS.

Esta fase no pretende demostrar validez universal. Su criterio de salida es elevar ambos módulos a `VALIDATED_WITH_LIMITATIONS` dentro del alcance explícitamente cubierto.

## Alcance validado

Los casos P1 son sistemas:

- trifásicos;
- balanceados;
- radiales;
- de dos barras;
- con una sola línea serie;
- sin capacitancia shunt;
- con una carga PQ constante en el extremo receptor;
- con fuente prácticamente ideal.

Se incluyen casos BT y MT, con distintos niveles de carga y caída de tensión.

## Solución independiente

La referencia no consume resultados de OpenDSS. Se resuelve por fase usando:

```text
I = conj(S_phase / V_r)
V_r = V_s - Z_line · I
```

con iteración compleja hasta convergencia. A partir de la solución se calculan independientemente:

```text
Vpu_receptor = |V_r| / |V_s|
I = |I|
P_loss = 3 · I² · R
Q_loss = 3 · I² · X
ΔV% = (1 - Vpu_receptor) · 100
```

El código de referencia vive en `mcp_electrico/benchmarks.py` y está separado de `core.py` y `studies.py`.

## Casos incluidos

### `bt_radial_pq`

- 0.48 kV;
- 0.050 km;
- R = 0.200 Ω/km;
- X = 0.080 Ω/km;
- carga = 30 kW + j10 kvar.

### `bt_radial_heavy`

- 0.48 kV;
- 0.100 km;
- R = 0.300 Ω/km;
- X = 0.100 Ω/km;
- carga = 80 kW + j40 kvar.

### `mt_radial_pq`

- 22.9 kV;
- 1.000 km;
- R = 0.3422 Ω/km;
- X = 0.1619 Ω/km;
- carga = 1000 kW + j300 kvar.

Los parámetros R/X del caso MT coinciden deliberadamente con un ejemplo ya soportado por la biblioteca N2XSY, pero el benchmark valida el solver y el postproceso, no la fuente de catálogo.

## Tolerancias declaradas

Las tolerancias están codificadas antes de ejecutar la comparación:

| Magnitud | Tolerancia |
|---|---:|
| tensión receptora | 0.0002 pu absoluta |
| corriente | 0.15 A absoluta o 0.30 % relativa |
| pérdidas activas | 0.005 kW absoluta |
| pérdidas reactivas | 0.005 kvar absoluta |
| caída de tensión | 0.020 puntos porcentuales absolutos |

Las tolerancias consideran también el redondeo de la API pública actual: tensiones pu a 4 decimales, corriente a 3 y pérdidas a 3.

## Hallazgo P1: precisión del postproceso de caída

La primera corrida del benchmark detectó que `voltage_drop` calculaba ΔV a partir del payload de tensiones ya redondeado a 4 decimales. En el caso MT, una referencia de aproximadamente `0.07457 %` terminaba reportada como `0.070 %`, lo que representaba un error relativo superior al 6 % aunque el error absoluto fuese pequeño.

P1 corrigió esa arquitectura: el estudio de caída lee ahora las magnitudes pu vigentes directamente de OpenDSS sin redondeo intermedio y redondea únicamente el resultado de presentación. Después de la corrección, el mismo caso reporta `0.075 %` y el error relativo cae por debajo de 1 %.

Existe una regresión específica que impide reintroducir el redondeo intermedio.

## Reporte automático

Ejecutar:

```bash
python examples/run_benchmarks_p1.py
```

genera `benchmark_p1.json` con, para cada magnitud:

- valor de referencia;
- valor obtenido por MCP/OpenDSS;
- error absoluto;
- error relativo porcentual;
- tolerancia;
- resultado `pass`.

CI ejecuta este generador y falla si cualquier caso queda fuera de tolerancia. El JSON se conserva como artefacto de la ejecución.

## Estado de madurez resultante

Si la suite completa permanece verde:

- `power_flow` → `VALIDATED_WITH_LIMITATIONS`;
- `voltage_drop` → `VALIDATED_WITH_LIMITATIONS`.

No se usa `VALIDATED` porque todavía faltan:

- feeders IEEE/EPRI completos;
- redes desbalanceadas;
- reguladores, capacitores y otros equipos;
- caída acumulada hasta cargas en topologías más complejas;
- cobertura explícita de múltiples fases y secuencias.

## Regla de interpretación

Un benchmark P1 exitoso demuestra que, dentro de este alcance, la implementación MCP/OpenDSS reproduce una solución independiente dentro de tolerancias declaradas. No demuestra por sí solo cumplimiento normativo ni elimina la revisión del ingeniero responsable.
