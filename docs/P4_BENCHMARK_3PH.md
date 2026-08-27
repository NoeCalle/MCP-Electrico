# P4C09A — benchmark independiente 3F max/min

## Propósito

Contrastar el primer motor numérico P4B contra una implementación analítica independiente antes de ampliar el alcance a `ip`, `Ith` o nuevas fallas.

Este benchmark **no usa pandapower ni OpenDSS para calcular los valores de referencia**. Pandapower aparece únicamente como sistema bajo prueba mediante `mcp_electrico.iec60909.ejecutar_3ph()`.

## Caso

Red radial de secuencia positiva:

```text
Red equivalente 22.9 kV ── línea 0.25 km ── barra de falla 3F
```

Datos:

```text
Un = 22.9 kV

MAX:
Scc3 = 500 MVA
X/R = 10
cmax = 1.10

MIN:
Scc3 = 250 MVA
X/R = 5
cmin = 1.00

Línea:
R1 = 0.18 ohm/km
X1 = 0.09 ohm/km
L  = 0.25 km
endtemp min = 20 °C explícitos
```

El valor de 20 °C se usa únicamente en este caso matemático para que el factor de resistencia de línea del escenario mínimo sea 1 y el benchmark no introduzca una segunda hipótesis térmica. No es una temperatura recomendada para estudios reales.

## Referencia analítica

Para cada escenario:

```text
|ZQ| = c · Un² / Scc
R/X = 1 / (X/R)
XQ = |ZQ| / sqrt(1 + (R/X)²)
RQ = (R/X) · XQ

Rline = R1 · L
Xline = X1 · L

Rk = RQ + Rline
Xk = XQ + Xline
|Zk| = sqrt(Rk² + Xk²)

Ik'' = c · Un / (sqrt(3) · |Zk|)
Sk'' = sqrt(3) · Un · Ik''
```

Para 22.9 kV se fija en el benchmark `cmax=1.10` y `cmin=1.00`, coherente con el alcance >1 kV usado por el método documentado de pandapower/IEC 60909. La fuente equivalente usa el Scc y X/R de entrada, mientras la capa MCP convierte explícitamente X/R a R/X para el `ext_grid` pandapower.

## Magnitudes comparadas

- `Ik''` en kA;
- `Sk''` en MVA;
- `Rk` en ohm;
- `Xk` en ohm.

Tolerancias declaradas antes de la comparación:

```text
Ik'' : ±0.002 kA
Sk'' : ±0.10 MVA
Rk   : ±0.001 ohm
Xk   : ±0.001 ohm
```

## Trazabilidad

Código independiente:

`mcp_electrico/iec60909_benchmarks.py`

Runner reproducible:

```bash
python examples/benchmark_p4_3ph.py --output benchmark_p4_3ph.json
```

El CI comprueba que:

```text
pass = true
depends_on_pandapower = false
depends_on_opendss = false
p4c09_complete = false
professional_emission = false
```

## Alcance del hito

Si MAX y MIN pasan, se considera implementado **P4C09A — benchmark independiente 3F**.

No se cambia todavía `P4C09` a DONE porque el gate global debe cubrir los otros alcances numéricos que P4-v1 finalmente admita. Tampoco cambia `short_circuit=UNDER_VALIDATION` ni habilita emisión profesional.

## Referencias técnicas públicas usadas para formular el benchmark

- IEC Webstore: metadata de `IEC 60909-0:2026`, edición 3.0.
- pandapower 3.5.4 — Short-Circuit: método de fuente de tensión equivalente DIN/IEC EN 60909.
- pandapower — Initial Short-Circuit Current: `VQ = c·Un/sqrt(3)` y `Ik'' = VQ/Zkk` para 3F.
- pandapower — Voltage Source Elements / External Grid: impedancia de red equivalente a partir de `s_sc_*_mva` y `rx_*`.
- pandapower — Branch Elements: impedancia serie de línea y requisito `endtemp_degree` para el mínimo.

La conformidad específica del backend con la nueva edición IEC 60909-0:2026 permanece separada en `P4C10` y sigue `PENDING`.
