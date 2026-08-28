# P5 — Protección del conductor y coordinación TCC

## Estado

**P5 ACTIVA — P5A, P5B y P5C implementados en esta rama; P5D es el siguiente bloque.**

P4 suministra corrientes de falla dentro de sus alcances declarados. P5A define dispositivos/rating/ajustes; P5B agrega datasets numéricos y evaluación de curvas TCC; P5C añade verificaciones técnicas de capacidad de corte y soportabilidad térmica del conductor. Todavía no se afirma coordinación ni despeje final.

```text
P5A  datos canónicos de protección          DONE / EXPERIMENTAL
P5B  datasets numéricos / semántica TCC     DONE / EXPERIMENTAL
P5C  capacidad de corte + conductor          DONE / EXPERIMENTAL
P5D  tiempos de despeje                      NEXT
P5E  coordinación/selectividad/backup        PENDIENTE
P5F  Workspace V5 / TCC                      PENDIENTE
P5G  benchmarks + gate de uso                PENDIENTE

protection_data          = EXPERIMENTAL
tcc_curve_evaluation     = EXPERIMENTAL
protection_checks        = EXPERIMENTAL
protection_coordination  = NOT_IMPLEMENTED
professional_emission    = false
```

## P5A — contrato de datos

El contrato canónico vive en:

- `mcp_electrico.protection_contract`;
- `mcp_electrico.protection_data`;
- `mcp_electrico.protection_tools`.

Incluye:

- `circuit_breaker`;
- `fuse`.

`relay` permanece fuera del alcance porque requiere CT/VT, funciones ANSI, lógica, ajustes y vínculo explícito con el elemento que despeja la falla.

Cada dispositivo conserva:

- ID `Protection.*`;
- elemento protegido;
- fabricante/serie/modelo cuando se dispone;
- norma declarada;
- procedencia;
- ratings propios de su tipo;
- ajustes explícitos.

### Ratings

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

No se renombran ratings entre familias ni se completan valores ausentes con catálogos implícitos.

### Ajustes

```text
setting_basis = ABSOLUTE_A
Ir [A]
Isd [A]
Ii [A]
derived_from_in = false
```

No se transforma automáticamente un múltiplo de `In` en un ajuste absoluto ni se inventa un pickup ausente.

## Vínculo P3

P3 conserva:

```text
Ib <= In <= Iz
```

P5 no crea un dispositivo desde `In_P3`. Cuando existe una ficha P3 de la línea, compara:

```text
In_P3 ?= In_P5
```

Una discrepancia se conserva como `P5READY201`; ninguno de los dos valores se sobreescribe.

## Vínculo P4

P4 aporta corrientes de falla para los gates posteriores.

Regla permanente:

```text
P4 tk_s != tiempo real de despeje P5
```

`tk_s` de P4 solo sirve al cálculo `Ith` dentro de P4. Nunca se usa como fallback de clearing time.

# P5B — datasets numéricos TCC

## Arquitectura

El registro vive en:

- `mcp_electrico.protection_curves`;
- `mcp_electrico.protection_tcc_tools`.

P5B no modifica la identidad de la curva P5A. Un dataset solo puede vincularse a un dispositivo si:

```text
dataset.curve_id == device.curve.id
```

La discrepancia bloquea el binding; no existe fuzzy match por modelo/fabricante.

## Forma de curva

Se admiten:

```text
SINGLE
BAND
```

`SINGLE` conserva un tiempo por corriente.

`BAND` conserva siempre:

```text
time_min_s
time_max_s
```

La banda **no se promedia ni se convierte en una única curva**.

## Unidades canónicas

```text
current = A
time    = s
```

No existe conversión silenciosa desde múltiplos de In ni desde escalas gráficas.

## Segmentos y discontinuidades

Cada dataset contiene uno o más segmentos explícitos. Dentro de cada segmento:

- hay al menos dos puntos;
- la corriente es estrictamente creciente;
- no se reordenan puntos silenciosamente.

Dos segmentos:

- no pueden solaparse;
- no pueden tocarse;
- conservan un hueco explícito entre dominios.

Esto permite representar discontinuidades, zonas instantáneas u otras separaciones sin unirlas artificialmente.

## Interpolación

Único método P5B:

```text
LOG_LOG_LINEAR
```

La interpolación ocurre únicamente entre dos puntos vecinos del **mismo segmento**:

```text
log(I) ↔ log(t)
```

Reglas no negociables:

```text
extrapolation = false
cross_segment_interpolation = false
```

Si la corriente queda:

- por debajo del dominio;
- por encima del dominio;
- dentro de un hueco entre segmentos;

el resultado es:

```text
OUT_OF_DOMAIN
values = None
```

## Semántica del tiempo

Todo dataset declara exactamente una de:

```text
TRIP_TIME
TOTAL_CLEARING_TIME
MELTING_TIME
OPERATING_TIME
```

P5B **evalúa el tiempo publicado**, pero no decide todavía que ese valor sea el tiempo final de despeje del circuito.

En particular:

```text
curve_time != necessarily final_clearing_time
```

P5D establecerá qué semánticas pueden consumirse directamente para despeje y cuáles requieren lógica/elementos adicionales.

## Procedencia

Tipos admitidos:

```text
MANUFACTURER_DATASET
MANUFACTURER_DIGITIZED
TEST_DATA
```

Para `MANUFACTURER_DIGITIZED` se exige `digitization_method` explícito. P5B no toma una imagen y genera puntos automáticamente.

El dataset conserva referencia, URL/revisión cuando existen y método de digitalización cuando aplica.

## Benchmark P5B

La interpolación se verifica con un benchmark analítico independiente basado en:

```text
t = K · I^-2
```

Puntos de prueba:

```text
I = 100 A   -> t = 10 s
I = 1000 A  -> t = 0.1 s
```

En el punto geométrico intermedio:

```text
I = sqrt(100·1000) A
```

la referencia exacta es:

```text
t = 1 s
```

El benchmark usa `TEST_DATA`; no se presenta como curva de fabricante.

También se prueba:

- exactitud en puntos publicados;
- banda min/max;
- rechazo de extrapolación;
- huecos entre segmentos;
- rechazo de puntos desordenados;
- rechazo de segmentos solapados/tangentes;
- método explícito de digitalización;
- binding exacto dataset ↔ curve ID;
- separación entre P5B y coordinación.

## Readiness y compatibilidad P5A

Para no romper el contrato histórico P5A se conserva `tcc_status` y se añade `tcc_data_status`.

Antes de dataset:

```text
tcc_status      = MODULE_NOT_READY_P5A
tcc_data_status = TCC_DATA_NOT_BOUND
```

Con dataset P5B válido:

```text
tcc_status      = TCC_DATA_READY_P5B
tcc_data_status = TCC_DATA_READY
```

Incluso con TCC numérica lista:

```text
clearing_time_source = None
p4_tk_s_consumed     = false
```

## Tools P5B

P5B mantiene un registro público separado para no cambiar la API P5A:

- `registrar_dataset_curva_tcc_p5b`;
- `listar_datasets_curva_tcc_p5b`;
- `vincular_dataset_curva_tcc_p5b`;
- `evaluar_curva_tcc_p5b`;
- `evaluar_dataset_tcc_p5b`.

No existe todavía una tool de coordinación/selectividad en P5B.

# P5C — capacidad de corte y protección térmica del conductor

## Alcance

El cálculo vive en:

- `mcp_electrico.protection_checks`;
- `mcp_electrico.protection_check_tools`.

P5C implementa **checks técnicos reproducibles**, no una certificación integral de la norma de producto.

Referencias objetivo versionadas:

```text
IEC 60947-2:2024  Ed.6  circuit-breakers
IEC 60269-1:2024  Ed.5  low-voltage fuses
IEC 60364-4-43:2023 Ed.4 protection against overcurrent
```

Estas referencias fijan el objetivo técnico/documental. `full_standard_compliance_claim=false` permanece hasta disponer de una trazabilidad normativa suficiente.

## Capacidad de corte

Entrada explícita:

```text
dispositivo
corriente_falla_ka
tension_operacion_kv
fuente_corriente
tipo_falla      [opcional]
escenario       [opcional]
```

La corriente puede proceder de P4, pero el vínculo se declara mediante su referencia; P5C no ejecuta automáticamente otro motor ni cambia de escenario.

### Interruptor

El check usa exclusivamente:

```text
fault_current <= Icu
```

`Ics` e `Icw` se conservan y reportan si existen, pero **no sustituyen a `Icu`** para producir el PASS de este check.

Esto significa que incluso si:

```text
Ics > fault_current
```

pero:

```text
Icu < fault_current
```

el resultado P5C es `FAIL`.

### Fusible

El check usa exclusivamente:

```text
fault_current <= breaking_capacity_ka
```

No se renombran ratings de interruptor como ratings de fusible.

### Tensión

Si:

```text
tension_operacion_kv > Ue
```

P5C devuelve `NOT_APPLICABLE_VOLTAGE`; no asume que el rating de corte registrado sea válido a una tensión superior.

## Soportabilidad térmica adiabática

P5C evalúa:

```text
I²t <= k²S²
```

con:

```text
I = corriente de falla explícita [A]
t = tiempo de despeje explícito [s]
k = coeficiente explícito y trazable [A·sqrt(s)/mm²]
S = sección explícita [mm²]
```

Políticas:

```text
k_derived_automatically       = false
section_derived_automatically = false
p4_tk_s_consumed              = false
```

El valor `k` no se deriva automáticamente del material/aislamiento. P5C exige una referencia explícita.

El tiempo tampoco se toma de `tk_s` P4. Mientras P5D no exista, debe aportarse con una fuente explícita. Cuando P5D cierre, su resultado trazable podrá ser una fuente válida.

## Binding con conductor P2

Si `Line.*` tiene conductor de biblioteca asignado, P5C compara:

```text
S_input ?= S_conductor_asignado
```

- coincidencia → `MATCH`;
- discrepancia → `SECTION_MISMATCH`;
- P5C no sustituye la sección introducida por la sección del catálogo.

Si no existe conductor P2 asignado, se exige `fuente_seccion` explícita.

Esto impide que `I²t <= k²S²` pase utilizando accidentalmente una sección distinta de la que pertenece al alimentador modelado.

## Resultados térmicos auxiliares

Además del PASS/FAIL, P5C devuelve:

```text
actual_i2t_a2s
limit_k2s2_a2s
utilization_ratio
max_permissible_clearing_time_s_at_input_current
max_permissible_current_ka_at_input_time
```

Son resultados matemáticos del check declarado; no amplían por sí solos el alcance normativo.

## Tools P5C

- `obtener_referencias_proteccion_p5c`;
- `evaluar_capacidad_corte_p5c`;
- `evaluar_soportabilidad_termica_conductor_p5c`.

No existe en P5C una tool de coordinación/selectividad.

# Camino posterior

## P5D — tiempo de despeje

Siguiente bloque:

- evaluar la curva a una corriente explícita;
- decidir de forma fail-closed qué `time_semantics` puede considerarse clearing time;
- conservar bandas como rango;
- no extrapolar;
- no utilizar `tk_s` P4;
- preservar dataset, segmento, corriente y procedencia del tiempo.

## P5E — coordinación

Primera cobertura prevista:

- par downstream/upstream explícito;
- corriente de evaluación explícita;
- margen temporal explícito;
- comparación conservadora de bandas;
- fail-closed si alguna curva está fuera de dominio.

No se inferirá selectividad energética/cascading a partir de heurísticas cuando se requieran tablas del fabricante.

## P5F — Workspace V5

Se conserva el mismo workspace/unifilar/inspector.

V5 mostrará datos y resultados preparados en Python/MCP. El navegador:

- no interpola curvas;
- no calcula tiempos;
- no calcula márgenes de coordinación;
- no decide selectividad;
- no inventa ajustes.

No se crea una segunda aplicación visual.

## Gate actual

```text
validation_status.protection_data         = EXPERIMENTAL
validation_status.tcc_curve_evaluation    = EXPERIMENTAL
validation_status.protection_checks       = EXPERIMENTAL
validation_status.protection_coordination = NOT_IMPLEMENTED
professional_emission                     = false
```

Cerrar P5C significa que la plataforma puede evaluar, con entradas explícitas y trazables, capacidad de corte declarada y soportabilidad térmica adiabática. No significa todavía que exista tiempo final de despeje, coordinación/selectividad o conformidad integral de las normas objetivo.
