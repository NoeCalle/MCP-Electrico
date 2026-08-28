# P5 — Protección del conductor y coordinación TCC

## Estado

**P5 ACTIVA — P5A–P5E implementados; P5F Workspace V5 en cierre y P5G es el siguiente gate.**

P4 suministra corrientes de falla dentro de sus alcances declarados. P5 construye encima de ellas datos de protección, datasets TCC, checks de capacidad de corte y conductor, tiempos finales de despeje y coordinación temporal puntual. El alcance sigue siendo deliberadamente conservador: no se afirma selectividad total, backup/cascading ni conformidad integral de normas de producto.

```text
P5A  datos canónicos de protección          DONE / EXPERIMENTAL
P5B  datasets numéricos / semántica TCC     DONE / EXPERIMENTAL
P5C  capacidad de corte + conductor          DONE / EXPERIMENTAL
P5D  tiempos de despeje                      DONE / EXPERIMENTAL
P5E  coordinación temporal puntual           DONE / EXPERIMENTAL
P5F  Workspace V5 / TCC                      DONE / EXPERIMENTAL
P5G  benchmarks + gate de uso                NEXT

protection_data          = EXPERIMENTAL
tcc_curve_evaluation     = EXPERIMENTAL
protection_checks        = EXPERIMENTAL
protection_clearing_time = EXPERIMENTAL
protection_coordination  = EXPERIMENTAL
professional_emission    = false
```

## Reglas permanentes

- P5 cubre por ahora `circuit_breaker` y `fuse`; `relay` queda fuera hasta modelar CT/VT, funciones ANSI, lógica y elemento de corte.
- `In_P3` se compara con `In_P5`; nunca crea automáticamente un dispositivo ni sobreescribe valores.
- `P4 tk_s != tiempo real de despeje P5`.
- no se sintetizan curvas de fabricante, ajustes, ratings, secciones ni coeficientes `k` ausentes;
- el navegador no ejecuta interpolación TCC ni cálculos de protección;
- `professional_emission=false` permanece durante P5.

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

El benchmark analítico independiente utiliza `t = K·I^-2`: 100 A → 10 s y 1000 A → 0.1 s; en la media geométrica de corriente la referencia exacta es 1 s. Se usa `TEST_DATA`, no una curva comercial ficticia.

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

Son referencias objetivo, no un claim de conformidad integral: `full_standard_compliance_claim=false`.

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

P5D evalúa la TCC dentro de su dominio y conserva dataset, curva, segmento, corriente, procedencia e interpolación utilizada.

Para `SINGLE`, el tiempo publicado/evaluado se conserva como un único valor.

Para `BAND`:

```text
time_min_s
time_max_s
```

se mantienen ambos límites. **No se promedian**. Cuando otro check necesita un único valor conservador:

```text
conservative_time_s = time_max_s
```

P4 `tk_s` nunca se consume como fallback de clearing time.

# P5E — coordinación temporal puntual

El motor vive en:

- `mcp_electrico.protection_coordination`;
- `mcp_electrico.protection_coordination_tools`.

Requiere:

- dispositivo downstream explícito;
- dispositivo upstream explícito;
- corriente explícita por cada dispositivo;
- relación upstream/downstream referenciada;
- margen mínimo explícito;
- `CLEARING_TIME_READY` P5D para ambos.

No se infiere topología ni se supone que ambos dispositivos vean la misma corriente.

Para bandas, la comparación conservadora es:

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
total_selectivity  = NOT_EVALUATED
partial_selectivity = NOT_EVALUATED
energy_selectivity = NOT_EVALUATED
backup              = NOT_EVALUATED
cascading           = NOT_EVALUATED
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
- resultados P5B/P5C/P5D/P5E vigentes para la `model_revision` actual;
- estado `EXPERIMENTAL · SIN EMISIÓN PROFESIONAL` visible;
- impresión/PDF compatible con la infraestructura existente.

La transformación log-log de coordenadas del SVG ocurre en **Python** a partir de los puntos ya estructurados. El JavaScript V5 solo gestiona pestañas y selección del elemento protegido:

```text
browser_engineering_calculation = false
```

No interpola TCC, no extrapola, no calcula clearing time, no calcula `I²t`, no calcula margen de coordinación y no decide selectividad.

V5 tampoco inventa una curva de daño del conductor: se incorporará solo si existe un dataset backend explícito y trazable que justifique esa representación.

Los resultados P5 ejecutados mediante tools se registran como estudios versionados en `workspace_state`; si cambia la revisión del modelo dejan de presentarse como vigentes.

# P5G — gate de uso

**NEXT.** P5G cerrará la fase P5 como checkpoint de uso interno, no como emisión profesional. Debe consolidar:

- contratos P5A–P5F;
- benchmarks/regresiones ya existentes;
- gate de completitud de fase;
- limitaciones y validaciones pendientes;
- readiness para el siguiente bloque operacional;
- `professional_emission=false`.

El siguiente bloque de producto después de P5G será **P7 mínimo — expediente/reproducibilidad para Engineering Preview**. P6 IEEE 1584 queda diferida por decisión de producto y no bloquea el primer uso interno.

## Validaciones pendientes

La deuda normativa/externa que no debe confundirse con el cierre funcional está registrada en `docs/VALIDACIONES_PENDIENTES.md`, incluyendo:

- revisión licenciada IEC 60909-0:2026;
- validaciones 2F-T;
- trazabilidad normativa completa de ratings P5C;
- dataset normativo de `k`;
- caso externo protección/conductor.

## Gate actual

```text
validation_status.protection_data          = EXPERIMENTAL
validation_status.tcc_curve_evaluation     = EXPERIMENTAL
validation_status.protection_checks        = EXPERIMENTAL
validation_status.protection_clearing_time = EXPERIMENTAL
validation_status.protection_coordination  = EXPERIMENTAL
professional_emission                      = false
```

Cerrar P5F significa que los resultados P5 ya tienen representación técnica coherente en el workspace. **No** significa que P5 esté listo para emisión profesional ni que exista selectividad integral. El cierre de fase corresponde a P5G.