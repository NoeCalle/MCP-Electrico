# P7 — MCP Eléctrico 0.9 Engineering Preview

## Estado

P7D define el gate final del expediente mínimo reproducible. Cuando todos sus criterios están `DONE`, MCP Eléctrico puede declararse:

```text
MCP_ELECTRICO_0_9_ENGINEERING_PREVIEW
engineering_preview_ready = true
internal_use_ready = true
allowed_use = CONTROLLED_INTERNAL_ENGINEERING_PREVIEW
professional_emission = false
```

La Engineering Preview habilita **uso interno controlado** dentro de los alcances y limitaciones ya declarados. No significa certificación, conformidad normativa integral, firma profesional ni autorización automática para emitir entregables contractuales.

## Cadena P7

```text
P7A — snapshot reproducible + SHA-256
P7B — reconstrucción verificable del netlist DSS
P7C — reporte técnico reproducible HTML / impresión PDF
P7D — gate Engineering Preview 0.9
```

### P7A

Congela netlist, workspace, datos P2/P3/P5, estudios, versiones, motores, madurez y limitaciones. La integridad se verifica mediante SHA-256 canónico.

### P7B

Reconstruye el netlist únicamente después de `HASH_MATCH`, recompila `Master.dss` y exige round-trip canónico. No promueve silenciosamente datos estructurados ni resultados históricos: requieren rebind/recalculation.

### P7C

Genera un reporte técnico determinista exclusivamente desde un snapshot P7A verificado. El navegador no recalcula ingeniería. La opción PDF usa `BROWSER_PRINT`.

```text
professional_report = false
professional_emission = false
```

### P7D

El gate `MCP_ELECTRICO_P7D_ENGINEERING_PREVIEW_GATE_V1` exige:

1. P5 `READY_WITH_LIMITATIONS` y ruta operacional cerrada;
2. P7A disponible con madurez explícita;
3. P7B disponible y fail-closed;
4. P7C disponible, con origen `HASH_MATCH` y sin cálculo eléctrico en navegador;
5. Workspace V5 persistente;
6. política determinista de motores: `automatic_dispatch=false`, `crosscheck=false`, OpenDSS por defecto;
7. coordinación P5 reconocida como implementada sin claim profesional;
8. IEEE 1584 explícitamente `DEFERRED` y `NOT_IMPLEMENTED`;
9. `professional_report=NOT_IMPLEMENTED` y `professional_emission=false`.

Si un criterio falla:

```text
phase_status = NOT_READY
engineering_preview_ready = false
internal_use_ready = false
product_release = null
```

## Coordinación P5 en la matriz de motores

La metadata histórica de `protection_coordination` precedía al cierre P5 y aún figuraba como no implementada. P7D introduce una alineación explícita:

```text
preferred = mcp+pandapower
implemented = true
professional_emission_candidate = false
```

Esto **no** amplía el alcance de P5. Continúan vigentes sus límites:

- coordinación temporal puntual;
- relación downstream/upstream explícita;
- sin inferencia automática de topología;
- sin claim de selectividad total/parcial o energética;
- backup y cascading no evaluados sin evidencia específica.

## Arc Flash

IEEE 1584 no forma parte de la 0.9:

```text
P6_IEEE1584_ARC_FLASH = DEFERRED
arc_flash_ieee1584.status = NOT_IMPLEMENTED
```

El método Lee permanece separado y experimental; no sustituye IEEE 1584.

## Eje visual

La 0.9 conserva el mismo workspace persistente V5. No se crea otra aplicación visual. JavaScript solo representa/navega información preparada por Python/MCP.

## Siguiente actividad

Con P7D verde:

```text
next_activity = REAL_SUBSTATION_PILOT
```

El piloto debe utilizar una subestación real o un caso suficientemente representativo, preferentemente utility-fed y dentro del alcance pasivo actualmente soportado. Su objetivo es descubrir fricción de uso, entradas faltantes, ergonomía, trazabilidad y necesidades de reporte antes de endurecer una futura versión 1.0.
