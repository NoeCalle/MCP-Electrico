# P5 — Protección del conductor y coordinación TCC

## Estado

**P5 COMPLETA CON LIMITACIONES — P5A–P5G DONE.**

P4 suministra corrientes de falla dentro de sus alcances declarados. P5 construye encima de ellas datos de protección, datasets TCC, checks de capacidad de corte y conductor, tiempos finales de despeje, coordinación temporal puntual y representación V5.

El cierre P5G es un **gate de fase funcional**, no una promoción artificial de madurez normativa. Los módulos P5 permanecen `EXPERIMENTAL` y `professional_emission=false`.

```text
P5A  datos canónicos de protección          DONE / EXPERIMENTAL
P5B  datasets numéricos / semántica TCC     DONE / EXPERIMENTAL
P5C  capacidad de corte + conductor          DONE / EXPERIMENTAL
P5D  tiempos de despeje                      DONE / EXPERIMENTAL
P5E  coordinación temporal puntual           DONE / EXPERIMENTAL
P5F  Workspace V5 / TCC                      DONE / EXPERIMENTAL
P5G  benchmarks + gate de uso                DONE

P5 phase_status             = READY_WITH_LIMITATIONS
next_phase                  = P7_REPRODUCIBLE_DOSSIER_MINIMUM
deferred_phase              = P6_IEEE1584_ARC_FLASH
operational_path_ready      = true
engineering_preview_ready   = false
professional_emission       = false

protection_data             = EXPERIMENTAL
tcc_curve_evaluation        = EXPERIMENTAL
protection_checks           = EXPERIMENTAL
protection_clearing_time    = EXPERIMENTAL
protection_coordination     = EXPERIMENTAL
```

`engineering_preview_ready=false` se mantiene hasta cerrar P7 mínimo de reproducibilidad/expediente.

## Reglas permanentes

- P5 cubre por ahora `circuit_breaker` y `fuse`; `relay` queda fuera hasta modelar CT/VT, funciones ANSI, lógica y elemento de corte.
- `In_P3` se compara con `In_P5`; nunca crea automáticamente un dispositivo ni sobreescribe valores.
- `P4 tk_s != tiempo real de despeje P5`.
- no se sintetizan curvas de fabricante, ajustes, ratings, secciones ni coeficientes `k` ausentes;
- el navegador no ejecuta interpolación TCC ni cálculos de protección;
- un PASS P5E no significa selectividad integral;
- `professional_emission=false` permanece después del cierre funcional P5.

# P5A — contrato de datos

El contrato canónico vive en:

- `mcp_electrico.protection_contract`;
- `mcp_electrico.protection_data`;
- `mcp_electrico.protection_tools`.

Cada dispositivo conserva ID `Protection.*`, elemento protegido, fabricante/serie/modelo cuando existe, norma declarada, procedencia, ratings propios y ajustes explícitos.

Interruptor:

```text
In
Ue
Icu
Ics
Icw   [si está declarado]
```

Fusible:

```text
In
Ue
breaking_capacity_ka
utilization_category   [si está declarada]
```

Ajustes de interruptor:

```text
setting_basis = ABSOLUTE_A
Ir [A]
Isd [A]
Ii [A]
derived_from_in = false
```

No se renombran ratings entre familias ni se convierten múltiplos de `In` en ajustes absolutos sin una entrada explícita.

## Vínculo P3

P3 conserva:

```text
Ib <= In <= Iz
```

Cuando existe ficha P3, P5 compara `In_P3 ?= In_P5`. Una discrepancia se conserva como `P5READY201`; ninguno de los valores se sobreescribe.

# P5B — datasets numéricos TCC

El registro vive en:

- `mcp_electrico.protection_curves`;
- `mcp_electrico.protection_tcc_tools`.

Un dataset solo puede vincularse si:

```text
dataset.curve_id == device.curve.id
```

Se admiten `SINGLE` y `BAND`. Una banda conserva siempre `time_min_s` y `time_max_s`; nunca se promedia a una curva única.

Unidades canónicas:

```text
current = A
time    = s
```

Cada dataset contiene segmentos explícitos. Los puntos de un segmento tienen corriente estrictamente creciente; dos segmentos no se solapan ni se tocan. Los huecos conservan discontinuidades reales del dataset.

Única interpolación P5B:

```text
LOG_LOG_LINEAR
```

solo entre dos puntos vecinos del **mismo segmento**.

```text
extrapolation = false
cross_segment_interpolation = false
```

Fuera del dominio o dentro de un hueco:

```text
OUT_OF_DOMAIN
values = None
```

Toda curva declara una semántica de tiempo:

```text
TRIP_TIME
TOTAL_CLEARING_TIME
MELTING_TIME
OPERATING_TIME
```

Procedencia admitida:

```text
MANUFACTURER_DATASET
MANUFACTURER_DIGITIZED
TEST_DATA
```

`MANUFACTURER_DIGITIZED` exige `digitization_method`. P5B nunca digitaliza automáticamente una imagen.

# P5C — capacidad de corte y conductor

El cálculo vive en:

- `mcp_electrico.protection_checks`;
- `mcp_electrico.protection_check_tools`.

Referencias objetivo versionadas:

```text
IEC 60947-2:2024     interruptores
IEC 60269-1:2024     fusibles
IEC 60364-4-43:2023  protección contra sobrecorriente
```

Son referencias objetivo, no un claim de conformidad integral:

```text
full_standard_compliance_claim = false
```

## Capacidad de corte

Interruptor:

```text
fault_current <= Icu
```

`Ics` e `Icw` se reportan cuando existen pero **no sustituyen a `Icu`** para producir el PASS.

Fusible:

```text
fault_current <= breaking_capacity_ka
```

Si `tension_operacion_kv > Ue`, el check devuelve `NOT_APPLICABLE_VOLTAGE`; no extrapola el rating a otra tensión.

## Soportabilidad térmica

P5C evalúa:

```text
I²t <= k²S²
```

con `I`, `t`, `k` y `S` explícitos y trazables.

```text
k_derived_automatically       = false
section_derived_automatically = false
p4_tk_s_consumed              = false
```

Si existe conductor P2 asignado, `S_input` debe coincidir exactamente con su sección. Una discrepancia produce `SECTION_MISMATCH`; no se sustituye silenciosamente. Si no existe asignación P2, se exige `fuente_seccion`.

Resultados auxiliares:

```text
actual_i2t_a2s
limit_k2s2_a2s
utilization_ratio
max_permissible_clearing_time_s_at_input_current
max_permissible_current_ka_at_input_time
```

# P5D — tiempo final de despeje

El contrato vive en:

- `mcp_electrico.protection_clearing_time`;
- `mcp_electrico.protection_clearing_tools`.

Regla de promoción:

```text
TOTAL_CLEARING_TIME -> CLEARING_TIME_READY
TRIP_TIME           -> no promoción automática
MELTING_TIME        -> no promoción automática
OPERATING_TIME      -> no promoción automática
```

Para `BAND`:

```text
time_min_s
time_max_s
```

se mantienen ambos límites y **no se promedian**. Cuando otro check necesita un único valor conservador:

```text
conservative_time_s = time_max_s
```

P4 `tk_s` nunca se consume como fallback de clearing time.

# P5E — coordinación temporal puntual

El motor vive en:

- `mcp_electrico.protection_coordination`;
- `mcp_electrico.protection_coordination_tools`.

Requiere downstream/upstream explícitos, corriente por dispositivo, relación referenciada, margen mínimo explícito y `CLEARING_TIME_READY` P5D para ambos.

No se infiere topología ni se supone que ambos dispositivos vean la misma corriente.

Para bandas:

```text
conservative_margin_s = upstream_time_min_s - downstream_time_max_s
PASS <=> conservative_margin_s >= required_margin_s
```

Un `PASS` significa únicamente:

```text
TEMPORAL_POINT_COORDINATION
```

No declara:

```text
total_selectivity   = NOT_EVALUATED
partial_selectivity = NOT_EVALUATED
energy_selectivity  = NOT_EVALUATED
backup               = NOT_EVALUATED
cascading            = NOT_EVALUATED
```

No existe barrido automático del dominio de corriente en P5E.

# P5F — Workspace V5 / TCC

V5 extiende incrementalmente el **mismo workspace persistente**:

```text
workspace base -> V3 ampacidad -> V4 cortocircuito -> V5 protección/TCC
```

No crea una segunda aplicación visual.

Implementado:

- pestaña `Protecciones / TCC`;
- tarjetas de `Protection.*` vinculadas al elemento protegido;
- ratings In/Ue/Icu/Ics/Icw o poder de corte;
- ajustes Ir/Isd/Ii;
- identidad de curva, dataset, semántica y procedencia;
- gráfico SVG TCC por dispositivo;
- `SINGLE` y `BAND`;
- segmentos separados para preservar discontinuidades;
- min/max de bandas como trazos independientes;
- resultados P5 vigentes para la `model_revision` actual;
- estado `EXPERIMENTAL · SIN EMISIÓN PROFESIONAL` visible;
- impresión/PDF compatible con la infraestructura existente.

La transformación log-log de coordenadas del SVG ocurre en **Python**. El JavaScript V5 solo gestiona pestañas y selección del elemento protegido:

```text
browser_engineering_calculation = false
```

V5 no inventa una curva de daño del conductor: se incorporará solo si existe un dataset backend explícito y trazable que justifique esa representación.

# P5G — benchmarks y gate de cierre

P5G implementa:

- `mcp_electrico.p5_benchmarks`;
- `examples/run_benchmarks_p5g.py`;
- `mcp_electrico.p5_completion`;
- tool pública `evaluar_cierre_p5()`;
- benchmark obligatorio en CI.

## Suite reproducible

```text
MCP_ELECTRICO_P5G_BENCHMARK_SUITE_V1

P5G_B01_TCC_BAND_LOGLOG
P5G_B02_TCC_NO_EXTRAPOLATION
P5G_B03_CLEARING_TIME_BAND
P5G_B04_TEMPORAL_COORDINATION
P5G_B05_BREAKING_CAPACITY
P5G_B06_CONDUCTOR_THERMAL
```

La suite usa un circuito sintético y exclusivamente `TEST_DATA`. No representa una curva comercial ni evidencia de conformidad normativa.

Comprueba de extremo a extremo:

- interpolación log-log analítica de una banda;
- ausencia de extrapolación;
- clearing time min/max y campo conservador;
- margen temporal conservador;
- uso de Icu para capacidad de corte;
- sustitución directa independiente en `I²t` y `k²S²`.

El reporte exige:

```text
failed                     = 0
pass                       = true
manufacturer_claim         = false
normative_compliance_claim = false
professional_emission      = false
```

## Gate formal P5

`evaluar_cierre_p5()` verifica diez criterios P5G y devuelve:

```text
phase                       = P5
phase_version               = P5-v1
phase_status                = READY_WITH_LIMITATIONS
ready_for_next_phase        = true
next_phase                  = P7_REPRODUCIBLE_DOSSIER_MINIMUM
deferred_phase              = P6_IEEE1584_ARC_FLASH
operational_path_ready      = true
engineering_preview_ready   = false
engineering_preview_blocker = P7_REPRODUCIBLE_DOSSIER_MINIMUM
professional_emission       = false
```

El gate acepta que un módulo implementado siga `EXPERIMENTAL`; no permite `NOT_IMPLEMENTED` para los módulos P5 requeridos y **no modifica** `validation_status` para fingir una madurez superior.

## Validaciones pendientes

La deuda normativa/externa que no debe confundirse con el cierre funcional está registrada en `docs/VALIDACIONES_PENDIENTES.md`, incluyendo:

- revisión licenciada IEC 60909-0:2026;
- validaciones 2F-T;
- trazabilidad normativa completa de ratings P5C;
- dataset normativo de `k`;
- caso externo protección/conductor.

## Handoff de producto

P5 queda listo con limitaciones para la ruta operacional. El siguiente bloque es **P7 mínimo — expediente/reproducibilidad**.

P6 IEEE 1584 permanece diferida y no bloquea el primer uso interno.

La Engineering Preview 0.9 solo podrá declararse lista cuando P7 cierre su gate mínimo de reconstrucción, fuentes/versiones, warnings/limitaciones y exportación reproducible.