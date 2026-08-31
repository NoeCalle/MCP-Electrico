# P8 — Subroadmap del primer piloto real

Este documento descompone la fase P8 del roadmap profesional sin ampliar el alcance declarado de MCP Eléctrico 0.9 Engineering Preview.

## Regla del piloto

El objetivo no es hacer más tipos de cálculo. El objetivo es demostrar que un expediente real puede recorrer una cadena reproducible, trazable y fail-closed sin copiar datos sintéticos de P8A ni inventar valores faltantes.

```text
expediente / SLD / fichas / estudios
        ↓
P8B admisión de entradas
        ↓
P8C reconstrucción y materialización
        ↓
readiness por estudio
        ↓
ejecución controlada P1/P3/P4/P5
        ↓
Workspace V5
        ↓
P7A snapshot + P7B reconstrucción + P7C reporte
        ↓
P8F hardening + entrada MCP controlada
```

`professional_emission=false` durante todo P8 mientras no exista un gate posterior que la habilite legítimamente.

## Estado de subhitos

| Subhito | Estado | Resultado |
| --- | --- | --- |
| P8A | DONE | piloto integral sintético 22.9/0.48 kV |
| P8B | DONE | intake real, topología construible y gates por scope |
| P8C1 | DONE | identidad de `source.bus` real hasta OpenDSS/P2 |
| P8C2 | DONE | contrato Z0 alineado con materialización 1F-T |
| P8C3A | DONE | pandapower deja de depender de `sourcebus` literal |
| P8C3B | DONE | `manifest → OpenDSS + P2 + Z0` reproducible, sin estudios |
| P8C3C | DONE | separación `MODEL_BUILT` vs `STUDY_READY` por scope |
| P8C4A | DONE | conductor real + Ib/In/Iz base + condiciones/factores P3 |
| P8C4B | DONE | dispositivos P5 + curva + dataset TCC numérico real |
| P8C5 | DONE | readiness integral P1/P3/P4/P5 sin ejecutar estudios |
| P8C5A | DONE | `PROJECT_DATA → P2_PROJECT` y etiqueta visual `PROYECTO P2` |
| P8D1 | DONE | ejecución controlada real P1/P3/P4; P5 queda pendiente con binding explícito |
| P8D2 | DONE | binding explícito dispositivo → resultado P4 + capacidad de corte/TCC/clearing P5 |
| P8E1 | DONE | Workspace V5 consume el agregado P8D2 vigente sin recalcular ingeniería |
| P8E2 | DONE | dossier real: Workspace V5 + P7A snapshot + P7B reconstrucción aislada + P7C reporte |
| P8F1 | DONE | entrada MCP única para ejecutar la misma cadena P8E2 desde el servidor |
| P8F2 | DONE | índice SHA-256 portable y verificación del conjunto exacto del dossier antes de READY |
| P8F3 | NEXT | repetición/aislamiento y no sobrescritura silenciosa de entregas |
| P8F4–P8F5 | PENDING | first-use operacional y gate final P8 |

P6 IEEE 1584 permanece `DEFERRED` y no bloquea este recorrido.

El detalle de hardening se mantiene en `docs/P8F_HARDENING_ROADMAP.md`.

## P8C4A — datos P3 reales

Un código de cable del proyecto no necesita existir en la biblioteca interna de fabricantes. P8C4A permite registrar una asignación `PROJECT_DATA` con:

- `element_id`;
- `conductor_code`;
- `base_ampacity_a` explícita;
- `ampacity_reference`;
- `installation_reference`;
- `norm_id` registrado;
- `ib_a` + `ib_reference`;
- `in_a` + `in_reference`;
- factores explícitos con referencia **o** `base_conditions_confirmed=true`.

El binding P3 de proyecto fija `NormAmps` para conservar la ampacidad base, pero no reemplaza R1/X1: las impedancias siguen siendo las declaradas en `topology.lines` por el expediente.

P8C4A materializa datos. No ejecuta `Ib <= In <= Iz` y no convierte materialización en cumplimiento.

## P8C4B — dispositivos P5 y TCC numérico

P8C4B materializa P5A/P5B solo cuando el manifiesto contiene datos suficientes para construir el objeto de protección y la curva numérica sin inferencias.

### Dispositivos

La semántica de capacidad de corte depende del tipo:

- `circuit_breaker`: Icu obligatoria; Ics/Icw opcionales y separadas;
- `fuse`: `breaking_capacity_ka` obligatorio; Icu/Ics/Icw no aplican.

Mientras P8B conserve su campo histórico genérico, un breaker puede declarar también `breaking_capacity_ka` **únicamente como alias legacy explícito igual a Icu**. El materializador P5 no lo usa como rating del interruptor.

Cada dispositivo conserva además:

- In y Ue;
- norma/referencia explícita;
- fabricante/serie/modelo cuando existen;
- ajustes Ir/Isd/Ii solo si están declarados en amperios y con procedencia;
- identidad y procedencia de curva.

Cuando existe una ficha P3 del mismo `Line.*`, In P5 debe coincidir exactamente con In P3.

### TCC

Metadata de curva no equivale a dataset ejecutable. P8C4B exige:

- `curve_id` y `dataset_id`;
- vínculo inequívoco dataset ↔ curve ↔ device;
- `shape=SINGLE|BAND`;
- semántica de tiempo;
- tipo y referencia de fuente;
- al menos un segmento;
- ID explícito por segmento;
- al menos dos puntos por segmento;
- corrientes estrictamente crecientes;
- tiempos positivos;
- `time_min_s <= time_max_s` en bandas;
- dominios de segmentos sin solaparse ni tocarse.

Una curva `MANUFACTURER_DIGITIZED` requiere además método de digitalización explícito.

P8C4B no evalúa la curva, no interpola tiempos de un caso de falla y no ejecuta capacidad de corte, I²t, clearing time ni coordinación. Solo deja los objetos P5A/P5B materializados y verificables.

No se digitalizan ni sintetizan curvas de fabricante automáticamente.

## P8C5/P8C5A — readiness integral cerrado

P8C5 materializa una sola vez hasta la capa más alta solicitada y después inspecciona el modelo activo. No reconstruye el modelo tras P3/P5 y no ejecuta estudios.

P8C5A cerró el único blocker detectado en el primer ensamblaje integral: la ruta histórica P3 rotulaba toda base P2 no normativa como `P2_CATALOG`, aunque la asignación proviniera del expediente.

La semántica queda ahora separada:

```text
PROJECT_DATA → P2_PROJECT → PROYECTO P2
CATALOG_DATA → P2_CATALOG → CATÁLOGO P2
```

Los perfiles P3 nuevos guardan campos genéricos `assignment_*`. Para una asignación `PROJECT_DATA`, los campos `catalog_*` quedan vacíos y no contienen datos de proyecto. Los perfiles históricos de catálogo continúan siendo legibles mediante fallback compatible.

El resultado `ampacity.evaluar()` propaga el origen hasta `base_evidence`, y Workspace V3 consume esa evidencia sin recalcular ni inferir procedencia en JavaScript.

Con P8C5A, el manifiesto integral focalizado queda:

| Scope | Estado pre-P8D |
| --- | --- |
| POWER_FLOW | READY |
| VOLTAGE_DROP | READY |
| AMPACITY | READY |
| IEC60909 3F MAX/MIN | READY |
| IEC60909 1F-T MAX/MIN | READY |
| PROTECTION_TCC | READY |

El gate devuelve:

```text
readiness_status = READY_FOR_CONTROLLED_EXECUTION
all_requested_ready = true
next_gate = P8D_CONTROLLED_EXECUTION
```

Esto sigue siendo readiness: no ejecuta Solve, `ampacity.evaluar`, `calc_sc`, evaluación TCC, capacidad de corte, I²t, clearing time ni coordinación.

## P8D1 — primera ejecución controlada real

P8D1 consume el readiness P8C5 y ejecuta una secuencia fija, explícita y trazable:

1. `POWER_FLOW` — OpenDSS;
2. `VOLTAGE_DROP` — OpenDSS;
3. `AMPACITY` — P3 MCP;
4. `IEC60909_3PH_MAX_MIN` — pandapower explícito;
5. `IEC60909_1PH_GROUND_MAX_MIN` — pandapower explícito con Z0.

No existe selección automática de motor, target de falla, cross-check ni emisión profesional. Si hay varias barras de cortocircuito, todas se ejecutan y Workspace conserva el agregado; no se elige una silenciosamente.

La regresión P8D1 verifica además que `Line.R1` de OpenDSS permanece invariante desde readiness hasta 3F MAX/MIN y 1F-T MAX/MIN. El diagnóstico del piloto descartó una mutación térmica de `Line.R1`.

Un manifiesto nuevo que queda bloqueado por readiness invalida los estudios visibles de la ejecución anterior en Workspace. Esto evita que un resultado previo pueda parecer perteneciente al intento bloqueado, sin reconstruir ni modificar el modelo OpenDSS activo.

P5 queda deliberadamente fuera de P8D1. Tener dispositivo y TCC materializados no basta para saber qué corriente de P4 debe alimentar cada chequeo.

## P8D2 — binding P4 → P5 cerrado

P8D2 declara por dispositivo:

- `device_id`;
- `fault_bus`;
- `fault_type` (`3ph` o `1ph-ground`);
- `case` (`max` o `min`);
- `current_quantity=ikss_ka`;
- `operating_voltage_kv` explícita;
- `source_reference` del binding;
- `thermal_check` opcional, únicamente con sección, coeficiente `k` y procedencias explícitas.

El binding falla cerrado si falta un dato, si la barra no fue ejecutada en P4, si tipo/caso no coinciden con el resultado seleccionado, si la magnitud no es `ikss_ka`, si la tensión explícita contradice el `vn_kv` disponible o si existen alternativas sin una selección inequívoca.

P8D2 ejecuta P1/P3/P4 una sola vez mediante la corrida controlada P8D1 y luego **reutiliza esos payloads P4 dentro de P5**. No relanza otro escenario de cortocircuito dentro de P5 (`p4_recalculation_inside_p5=false`).

Con binding válido:

- breaker: `protection_checks.evaluar_capacidad_corte()` usa únicamente Icu; Ics/Icw permanecen visibles y no intervienen en el PASS de capacidad de corte;
- fuse: se usa únicamente `breaking_capacity_ka`;
- TCC: el dataset numérico materializado se evalúa a la corriente `Ik''` ligada;
- clearing time: solo `TOTAL_CLEARING_TIME` dentro de dominio se promueve mediante P5D;
- chequeo térmico: solo se ejecuta cuando el binding trae sección, `k` y fuentes explícitas; usa el `conservative_time_s` promovido por P5D.

Si la TCC está fuera de dominio o su semántica no permite clearing time, la ejecución queda parcial y **no se promociona `protection_tcc` a Workspace**. Un estudio P5 se registra solo cuando todos los dispositivos tienen clearing time numérico realmente listo.

P8D2 conserva:

```text
automatic_dispatch = false
automatic_fault_binding = false
p4_recalculation_inside_p5 = false
crosscheck = false
professional_emission = false
```

## P8E — presentación y dossier real cerrados

P8E1 integra el resultado agregado `protection_tcc` de P8D2 en el mismo Workspace V5 existente. No crea una segunda interfaz y no recalcula ingeniería en JavaScript.

La vista solo presenta el agregado cuando el estudio está vigente y su `model_revision` coincide. Por dispositivo conserva:

- `fault_bus`;
- `fault_type`;
- `case` MAX/MIN;
- `ikss_ka` realmente consumido;
- capacidad de corte y margen ya calculados;
- clearing time promovido por P5D;
- procedencia P4 y referencia del binding;
- Icu/Ics/Icw separados para breaker y poder de corte separado para fuse.

P8E2 genera el dossier reproducible del mismo estado calculado:

- `manifest.json`;
- `execution_p8d2.json`;
- `workspace_v5.html`;
- `project_snapshot_p7a.json` con SHA-256 verificable;
- `reconstruction_p7b.json`;
- `project_report_p7c.html`;
- netlist P7A y directorio reconstruido P7B;
- `dossier_integrity.json`, exigido por P8F2 antes de promover el dossier a READY.

P7B se ejecuta en un proceso hijo para demostrar el round-trip canónico sin destruir o rebindear el circuito, P2/P3/P5 ni los estudios vigentes del proceso principal. P7C consume el snapshot P7A y no recalcula la ingeniería.

El éxito de P8E2/P8F2 es:

```text
DOSSIER_READY_ENGINEERING_PREVIEW
+ DOSSIER_INTEGRITY_VERIFIED
```

Este estado no equivale a autenticidad mediante firma digital ni a emisión profesional.

## P8F — hardening para uso controlado

P8F no incorpora nuevos estudios eléctricos. Endurece la cadena que ya pasó el piloto y la convierte en una ruta operable desde el servidor MCP.

P8F1 cerró la primera brecha detectada: P8B estaba expuesto como tool MCP, mientras P8E2 solo era invocable como módulo Python. La entrada pública es:

```text
generar_dossier_piloto_real(manifest, directorio_salida)
```

Esta tool no implementa motores ni cálculos propios; delega únicamente en P8E2, por lo que conserva P8D1/P8D2 como fronteras obligatorias.

P8F2 endurece la entrega: P8E2 solo devuelve READY cuando `dossier_integrity.json` verifica por SHA-256 el conjunto exacto de artefactos, incluidos los netlists P7A/P7B. La verificación es portable por rutas relativas, rechaza archivos extra, modificaciones, ausencias y symlinks. Es un gate de integridad de contenido, no una firma de autor.

La siguiente frontera es P8F3: repetir la ruta completa sin sobrescribir entregas ni contaminar estado, manteniendo cada dossier independientemente verificable.

## Gate visual del piloto real

La ruta visual sigue siendo **Workspace V5**. No se crea una interfaz paralela para P8.

Se conservan estas reglas:

1. la identidad visual del conductor no puede sobrescribir el binding técnico P2/P3;
2. un conductor `PROJECT_DATA` se distingue de un producto `CATALOG_DATA`;
3. V3 muestra `PROYECTO P2` para base real del expediente y `CATÁLOGO P2` para biblioteca;
4. V4 conserva barra de falla, motor, caso MAX/MIN y madurez;
5. V5 solo muestra curvas TCC cuando exista dataset numérico real materializado;
6. V5 conserva Icu/Ics/Icw de breaker separadas del poder de corte de fuse;
7. ningún panel JavaScript recalcula ingeniería;
8. cada resultado debe pertenecer a la revisión vigente del modelo.

`READY_TO_BUILD_MODEL`, `MODEL_BUILT_NOT_EXECUTED`, `P3_MATERIALIZED`, `P5_TCC_MATERIALIZED_NOT_EXECUTED`, `READY_FOR_CONTROLLED_EXECUTION`, `CONTROLLED_EXECUTION_COMPLETED`, `PROTECTION_EXECUTION_COMPLETED`, `DOSSIER_READY_ENGINEERING_PREVIEW` y `DOSSIER_INTEGRITY_VERIFIED` son estados distintos y no se sustituyen entre sí.

```text
automatic_defaults = false
automatic_dispatch = false
automatic_fault_binding = false
crosscheck = false
professional_emission = false
```
