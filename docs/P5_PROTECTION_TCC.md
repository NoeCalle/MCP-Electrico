# P5 — Protección del conductor y coordinación TCC

## Estado

**P5 ACTIVA — P5A FOUNDATION DONE; P5B es el siguiente bloque.**

P4-v1 quedó `READY_WITH_LIMITATIONS` y habilitó el inicio de P5. P5A ya define una base canónica y fail-closed de dispositivos; todavía no existe un solver TCC ni coordinación profesional.

```text
P5A  datos canónicos de protección          DONE / EXPERIMENTAL
P5B  datasets numéricos / semántica TCC     NEXT
P5C  capacidad de corte + conductor          PENDIENTE
P5D  tiempos de despeje                      PENDIENTE
P5E  coordinación/selectividad/backup        PENDIENTE
P5F  Workspace V5 / TCC                      PENDIENTE
P5G  benchmarks + gate de madurez            PENDIENTE

protection_data = EXPERIMENTAL
protection_coordination = NOT_IMPLEMENTED
professional_emission = false
```

## P5A — contrato de datos

El contrato canónico vive en:

- `mcp_electrico.protection_contract`;
- `mcp_electrico.protection_data`;
- `mcp_electrico.protection_tools`.

### Alcance P5A

Incluido:

- `circuit_breaker`;
- `fuse`.

Fuera de P5A:

- `relay`.

El relé no se aproxima como interruptor porque requiere un modelo propio de CT/VT, funciones ANSI, lógica/ajustes y vínculo con el elemento que realmente despeja la falla.

### Identidad y vínculo físico

Cada dispositivo P5A declara:

- ID estable `Protection.*`;
- tipo;
- elemento protegido canónico (`Line.*`, `Transformer.*`, `Bus.*`, etc. cuando existe en el modelo);
- fabricante/serie/modelo cuando se dispone;
- norma de referencia explícita;
- procedencia de la ficha.

No se crean dispositivos a partir de símbolos visuales ni de un valor `In` aislado.

## Ratings

### Interruptor

P5A distingue:

- `In`;
- `Ue`;
- `Icu`;
- `Ics`;
- `Icw` cuando está declarado.

Un `Icu` ausente permanece ausente y bloquea la futura evaluación de capacidad de corte. P5A no rellena ratings de catálogo por familia/modelo si no existe un dataset trazable.

### Fusible

P5A usa:

- `In`;
- `Ue`;
- `breaking_capacity_ka`;
- categoría de utilización cuando fue declarada.

No se renombran `Icu/Ics/Icw` como si fueran ratings de fusible.

## Ajustes

El foundation usa magnitudes absolutas explícitas:

```text
Ir [A]
Isd [A]
Ii [A]
```

Política:

```text
setting_basis = ABSOLUTE_A
derived_from_in = false
```

P5A no convierte automáticamente `Ir=0.8×In`, `Isd=5×Ir`, etc. Si más adelante se admiten ajustes relativos, deberán conservar simultáneamente valor original, base, conversión y procedencia.

## Vínculo P3

P3 ya conserva `In` dentro del criterio:

```text
Ib <= In <= Iz
```

P5A **no crea un dispositivo desde ese In**. Si el dispositivo protege una `Line.*` con ficha P3 existente, compara:

```text
In_P3 ?= In_P5A
```

- coincidencia → `MATCH`;
- discrepancia → `P5READY201`, fail-closed para protección del conductor;
- ausencia de P3 → se conserva como `P3_NOT_CONFIGURED`, sin inventar vínculo.

Ninguno de los dos valores se sobreescribe automáticamente.

## Vínculo P4

P4 aporta corrientes de falla dentro de su alcance validado. P5 consumirá esas corrientes en gates posteriores, pero P5A aún no ejecuta capacidad de corte ni coordinación.

Regla no negociable:

```text
P4 tk_s != tiempo real de despeje P5
```

`tk_s` fue un dato explícito usado por P4 para `Ith`. No se convierte automáticamente en clearing time. El tiempo real deberá provenir de curva/función/dispositivo y lógica de protección trazables.

## Curvas y TCC

P5A solo permite vincular metadata:

- `curve_id`;
- tipo (`MANUFACTURER_TCC`, `STANDARD_CURVE`, `TEST_CURVE`);
- revisión;
- fuente.

Y fuerza:

```text
numeric_dataset_loaded = false
synthetic = false
tcc_execution_ready = false
```

P5A **no digitaliza, interpola ni sintetiza** una curva de fabricante.

### P5B — siguiente bloque

P5B deberá definir antes de dibujar TCC:

1. esquema numérico de curva/banda;
2. unidades canónicas;
3. dominio de corriente válido;
4. límites mínimo/máximo de tiempo cuando el fabricante publica bandas;
5. semántica de puntos discontinuos/instantáneos;
6. procedencia por dataset/revisión;
7. interpolación permitida y método, solo si está técnicamente justificado;
8. fail-closed fuera del dominio;
9. benchmark independiente de evaluación temporal.

Solo después podrá existir una función que devuelva tiempo de despeje.

## Camino posterior

### P5C — capacidad de corte y protección del conductor

Previsto:

- confrontar corriente de falla P4 con rating de corte aplicable;
- conservar MAX/MIN y tipo de falla;
- verificar relación con conductor P3;
- implementar `I²t <= k²S²` con datos y norma trazables;
- no confundir `Icu`, `Ics`, `Icw` ni poder de corte de fusible.

### P5D — tiempo de despeje

Previsto:

- evaluar curva/dispositivo en corriente de falla;
- distinguir pickup, tolerancia/banda y zona instantánea;
- retornar fuente exacta del tiempo;
- nunca usar `tk_s` P4 como fallback.

### P5E — coordinación

Previsto:

- par upstream/downstream explícito;
- margen temporal configurable/versionado;
- selectividad total/parcial cuando exista evidencia;
- backup/cascading solo con tablas de fabricante trazables;
- ningún claim comercial derivado por heurística.

### P5F — V5

Se conserva el mismo workspace/unifilar/inspector. V5 añadirá una vista TCC vinculada a objetos `Protection.*` reales.

El navegador:

- no calcula curvas;
- no interpola tiempos;
- no decide selectividad;
- no inventa ajustes;
- solo representa datasets/resultados preparados por Python/MCP.

No se crea una segunda aplicación visual.

## Gate actual

P5A no cambia la madurez de `protection_coordination`.

```text
validation_status.protection_data = EXPERIMENTAL
validation_status.protection_coordination = NOT_IMPLEMENTED
professional_emission = false
```

Cerrar P5A significa que existe una base de datos/contrato segura para continuar a P5B; no significa que el MCP ya coordine protecciones.
