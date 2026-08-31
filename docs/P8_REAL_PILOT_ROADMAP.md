# P8 — Roadmap del primer piloto real

P8 demuestra y endurece la transición de MCP Eléctrico 0.9 desde módulos validados por separado hacia una ruta completa para **uso real controlado bajo Engineering Preview**.

P8 queda cerrado sin ampliar el alcance profesional declarado. `professional_emission=false` permanece obligatorio.

## Cadena demostrada

```text
expediente / SLD / fichas / estudios
        ↓
P8B admisión fail-closed
        ↓
P8C materialización + readiness
        ↓
P8D ejecución controlada P1/P3/P4/P5
        ↓
P8E Workspace V5 + dossier P7A/P7B/P7C
        ↓
P8F entrada MCP + integridad + repetición + first-use + gate final
        ↓
FIRST_CONTROLLED_REAL_PROJECT
```

## Estado final de subhitos

| Subhito | Estado | Resultado |
| --- | --- | --- |
| P8A | DONE | piloto integral sintético 22.9/0.48 kV |
| P8B | DONE | intake real, trazabilidad y gates por scope |
| P8C1 | DONE | identidad de `source.bus` hasta OpenDSS/P2 |
| P8C2 | DONE | contrato Z0 para materialización 1F-T |
| P8C3A | DONE | pandapower independiente de `sourcebus` literal |
| P8C3B | DONE | `manifest → OpenDSS + P2 + Z0` reproducible |
| P8C3C | DONE | separación `MODEL_BUILT` vs `STUDY_READY` |
| P8C4A | DONE | conductor real + Ib/In/Iz + condiciones/factores P3 |
| P8C4B | DONE | dispositivos P5 + dataset TCC numérico |
| P8C5 | DONE | readiness integral P1/P3/P4/P5 sin ejecución |
| P8C5A | DONE | `PROJECT_DATA → P2_PROJECT → PROYECTO P2` |
| P8D1 | DONE | ejecución controlada P1/P3/P4 |
| P8D2 | DONE | binding explícito P4→P5 + capacidad/TCC/clearing |
| P8E1 | DONE | resultado P8D2 vigente integrado en Workspace V5 |
| P8E2 | DONE | dossier real Workspace + P7A/P7B/P7C |
| P8F1 | DONE | entrypoint MCP único `generar_dossier_piloto_real` |
| P8F2 | DONE | integridad SHA-256 del conjunto exacto del dossier |
| P8F3 | DONE | repetición collision-safe y no sobrescritura |
| P8F4 | DONE | first-use end-to-end por MCP stdio contra `server.py` |
| P8F5 | DONE | gate final + checklist de datos para expediente real |

```text
P8 = CLOSED
phase_status = READY_FOR_CONTROLLED_REAL_PROJECT_USE
allowed_use = CONTROLLED_REAL_PROJECT_ENGINEERING_PREVIEW
next_activity = FIRST_CONTROLLED_REAL_PROJECT
```

P6 IEEE 1584 permanece `DEFERRED` y no bloquea P8.

## P8B — admisión real

La admisión inspecciona el manifiesto sin construir el modelo ni ejecutar ingeniería.

La tool pública es:

```text
evaluar_admision_piloto_real(manifest)
```

Estados relevantes:

```text
READY_TO_BUILD_MODEL
BLOCKED_MISSING_INPUTS
```

P8B conserva:

```text
electrical_calculation = false
model_mutation = false
automatic_defaults = false
automatic_dispatch = false
crosscheck = false
professional_emission = false
```

## P8C — materialización y readiness

P8C convierte datos explícitos del proyecto en un modelo trazable sin confundir materialización con cumplimiento.

### Datos P2 y origen

```text
PROJECT_DATA → P2_PROJECT → PROYECTO P2
CATALOG_DATA → P2_CATALOG → CATÁLOGO P2
```

Los datos de proyecto no se presentan como catálogo ni norma.

### Ampacidad P3

Un conductor real puede provenir del expediente aunque no exista en la biblioteca interna. El manifiesto declara ampacidad base, Ib, In, instalación, factores/condiciones y procedencias.

P8C no sustituye R1/X1 del expediente por la ampacidad ni por datos visuales.

### Protección P5 y TCC

Se mantienen semánticas distintas:

- breaker: Icu obligatoria para capacidad de corte; Ics/Icw separadas;
- fuse: `breaking_capacity_ka`;
- metadata TCC no equivale a dataset ejecutable;
- el dataset numérico debe incluir shape, semántica temporal, segmentos, puntos y procedencia.

No se sintetizan ni digitalizan curvas automáticamente.

### Readiness integral

Los scopes del piloto pueden llegar a:

```text
POWER_FLOW = READY
VOLTAGE_DROP = READY
AMPACITY = READY
IEC60909_3PH_MAX_MIN = READY
IEC60909_1PH_GROUND_MAX_MIN = READY
PROTECTION_TCC = READY
```

sin ejecutar todavía los estudios.

## P8D — ejecución controlada real

### P8D1

Secuencia fija:

1. POWER_FLOW — OpenDSS;
2. VOLTAGE_DROP — OpenDSS;
3. AMPACITY — MCP P3;
4. IEC60909 3F MAX/MIN — pandapower explícito;
5. IEC60909 1F-T MAX/MIN — pandapower explícito con Z0.

Si existen varias barras solicitadas no se elige una silenciosamente. Las regresiones verifican además que `Line.R1` permanece invariante durante la cadena.

### P8D2 — binding P4→P5

Por dispositivo se declara explícitamente:

- `device_id`;
- `fault_bus`;
- `fault_type`;
- `case` MAX/MIN;
- `current_quantity=ikss_ka`;
- `operating_voltage_kv`;
- `source_reference`;
- datos térmicos opcionales con procedencia.

P8D2 reutiliza los payloads P4 ejecutados por P8D1:

```text
p4_recalculation_inside_p5 = false
automatic_fault_binding = false
```

Con binding válido:

- breaker usa Icu para el PASS de capacidad de corte;
- fuse usa su poder de corte;
- TCC se evalúa a la `Ik''` ligada;
- clearing se promueve solo con `TOTAL_CLEARING_TIME` dentro de dominio;
- chequeo térmico solo se ejecuta con sección, `k` y referencias explícitas.

Un resultado TCC incompleto/no promocionable no aparece como estudio P5 vigente en Workspace.

## P8E — Workspace y dossier reproducible

### P8E1 — Workspace V5

P8 usa el mismo Workspace V5; no existe una interfaz paralela.

La vista integrada P8D2 es read-only y solo consume `protection_tcc` vigente de la revisión actual. Muestra, entre otros:

- barra/tipo de falla;
- caso MAX/MIN;
- `ikss_ka` consumido;
- capacidad de corte y margen;
- clearing time;
- procedencia P4;
- referencia del binding;
- Icu/Ics/Icw separadas para breaker.

El navegador no recalcula ingeniería.

### P8E2 — dossier

La ruta integral genera:

```text
manifest.json
execution_p8d2.json
workspace_v5.html
project_snapshot_p7a.json
reconstruction_p7b.json
project_report_p7c.html
p7a_netlist/
p7b_reconstructed/
dossier_integrity.json
```

P7B se verifica en proceso hijo para no rebindear/destruir el estado principal. P7C consume el snapshot P7A y no recalcula ingeniería.

El estado de entrega es:

```text
DOSSIER_READY_ENGINEERING_PREVIEW
```

únicamente cuando P8F2 verifica integridad.

## P8F — hardening de producto

Detalle completo: `docs/P8F_HARDENING_ROADMAP.md`.

### P8F1 — entrada MCP

Único entrypoint integral:

```text
generar_dossier_piloto_real(manifest, directorio_salida)
```

La tool delega en P8E2. No implementa un segundo flujo eléctrico.

### P8F2 — integridad

`dossier_integrity.json` inventaría tamaño y SHA-256 de cada archivo con rutas relativas. Detecta modificación, ausencia, archivos extra, rutas inseguras y symlinks.

```text
DOSSIER_INTEGRITY_VERIFIED
```

significa integridad respecto del índice, no autenticidad/firma profesional.

### P8F3 — repetición

```text
output_collision_policy = SUFFIX_INCREMENT
silent_overwrite = false
```

Una segunda entrega usa `_2`, luego `_3`, etc. Cada dossier se verifica de forma independiente. Un intento bloqueado no crea una nueva entrega.

### P8F4 — first-use público

`examples/p8_first_use_mcp.py` levanta `server.py` por MCP stdio y ejecuta únicamente tools públicas:

```text
evaluar_admision_piloto_real
→ generar_dossier_piloto_real
→ verificar_integridad_dossier_real
```

La plantilla `examples/p8_first_use_manifest.json` es demostrativa y no debe presentarse como evidencia real.

Guía: `docs/P8F4_FIRST_USE_MCP.md`.

### P8F5 — gate final

Tool:

```text
evaluar_cierre_p8f5_uso_real_controlado()
```

El gate se basa en contratos ejecutables P7/P8 y falla cerrado si se reabre una política crítica.

Con la release actual devuelve:

```text
READY_FOR_CONTROLLED_REAL_PROJECT_USE
```

La tool:

```text
obtener_checklist_p8f5_datos_proyecto_real()
```

devuelve los 10 bloques de datos/procedencias requeridos antes de una corrida real.

Checklist legible: `docs/P8_CONTROLLED_REAL_USE_CHECKLIST.md`.

## Matriz de motores vigente

```text
OpenDSS = motor por defecto
pandapower = IEC 60909 explícito/experimental
MCP = ampacidad/protección y gobernanza
```

Se mantiene:

```text
automatic_dispatch = false
crosscheck = false
iec60909_full_conformance_claim = false
```

P4 ha sido revisado contra IEC 60909-0:2026 con limitaciones declaradas; esto no constituye un claim de conformidad integral de la edición.

## Gate visual

La ruta visual única sigue siendo **Workspace V5**.

Reglas:

1. visualización no sobrescribe bindings técnicos;
2. `PROJECT_DATA` se distingue de `CATALOG_DATA`;
3. V3 conserva evidencia P3;
4. V4 conserva motor, barra y caso IEC 60909;
5. V5 presenta TCC solo con dataset numérico materializado;
6. breaker Icu/Ics/Icw permanecen separados del fuse;
7. JavaScript no recalcula ingeniería;
8. solo se presenta la revisión vigente;
9. P8D2 integrado usa el mismo Workspace, no una UI paralela.

## Fronteras profesionales

P8 cerrado **no** significa:

- certificación del software;
- conformidad normativa integral;
- garantía de que cualquier entrada sea correcta;
- validación automática del criterio del ingeniero;
- firma digital/autenticidad del dossier;
- autorización para emitir entregables profesionales sin revisión humana.

Permanece:

```text
automatic_defaults = false
automatic_dispatch = false
automatic_fault_binding = false
crosscheck = false
professional_report = false
professional_emission = false
P6_IEEE1584 = DEFERRED
```

## Siguiente actividad

P8 ya no tiene un subhito de desarrollo pendiente para iniciar el piloto de campo.

La siguiente actividad es:

```text
FIRST_CONTROLLED_REAL_PROJECT
```

El primer expediente debe comenzar con una red acotada, trazable y bien documentada. Antes de ejecutar, usar `docs/P8_CONTROLLED_REAL_USE_CHECKLIST.md` y el preflight P8B.

Las fricciones encontradas durante ese uso real deberán entrar como nuevos issues/hardening posteriores, sin reabrir automáticamente P8 ni debilitar sus gates.
