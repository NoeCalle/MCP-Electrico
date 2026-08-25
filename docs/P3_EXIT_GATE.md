# P3 — Gate formal de salida de ampacidad

## Estado

**NOT_READY.**

Este gate no decide si un solo circuito puede calcular `Ib <= In <= Iz`; decide si la **Fase P3 del producto** puede considerarse cerrada dentro del alcance P3-v1 y habilitar el paso formal a P4.

La separación es deliberada:

- `phase`: madurez, cobertura normativa y evidencia del producto;
- `model`: preparación técnica y calidad de evidencia del circuito activo.

Un modelo puede devolver `READY_TO_EXECUTE` y seguir usando factores secundarios o manuales. Ese hecho **no cierra P3**.

## Alcance candidato P3-v1

- jurisdicción: Perú;
- referencia: `PERU_CNE_UTILIZACION_2006`;
- perfil: `PERU_CNE_UTIL_2006_030_004`;
- regla: 030-004;
- métodos de instalación enrutados: A1, A2, B1, B2, C, D, E, F y G.

Familias numéricas exigidas antes de considerar `VALIDATED_WITH_LIMITATIONS`:

1. estrategia validada de ampacidad base, mediante Tablas 1/2 o equivalente formalmente validado;
2. Tabla 5A — temperatura;
3. Tabla 5B — resistividad térmica del suelo cuando aplique;
4. Tabla 5C — agrupamiento al aire dentro de su alcance;
5. Tabla 5D — agrupamiento enterrado del método D;
6. Tabla 5E — ramas de disposición cuando apliquen.

El gate no interpola ni amplía el alcance normativo.

## Criterios del gate

### Infraestructura y evidencia primaria implementadas

- `P3C01` — contrato `Ib/In/Iz`;
- `P3C02` — router normativo P3A;
- `P3C03` — infraestructura de datasets numéricos versionados;
- `P3C04` — gate de evidencia primaria y pin de fuente;
- `P3C05` — binding trazable dataset → factor → `Iz`;
- `P3C06` — readiness de evidencia separado de `READY_DATA`;
- `P3C07` — evidencia visible en workspace V3;
- `P3C08` — fuente oficial primaria pinneada por SHA-256;
- `P3C09` — primera revisión numérica `PRIMARY_VERIFIED` de Tabla 5C;
- `P3C10` — estrategia validada de `Iz_base` con primera revisión primaria exacta de Tabla 2.

P3C08 utiliza la copia obtenida desde la URL oficial MINEM registrada y fijada en `ampacity_primary_sources.json`:

```text
source_id = MINEM_CNE_UTIL_2006_OFFICIAL_PDF
pin_status = PINNED
expected_sha256 = 2b3cbd457c519bf9d9aa2cf2754c72b6e531708e45ea2fdf91f839b1acccfd64
```

El pin identifica la copia primaria de referencia, pero no valida numéricamente ninguna tabla.

P3C09 conserva una revisión primaria limitada a las celdas efectivamente verificadas de Tabla 5C. P3C10 añade la primera `Iz_base` primaria:

```text
dataset = PERU_CNE_UTIL_2006_TABLE_2_COL23_C_XLPE_3C_CU_70MM2_PRIMARY_V1
axis = base_ampacity
table = Tabla 2
Método C / Cu / XLPE-EPR / 90 °C / 3 cargados / 70 mm2
ampacity_a = 229 A
verification_status = PRIMARY_VERIFIED
```

El valor 229 A solo es válido para esa consulta exacta. El dataset no representa Tabla 2 completa y no permite interpolación, extrapolación ni vecino más cercano.

La estrategia P3C10 queda demostrada de extremo a extremo:

```text
Tabla 2 primaria
→ exact_rows_v1
→ ampacity_base_binding
→ base_normativa
→ Iz_base
→ Ib <= In <= Iz
→ base_evidence / V3
```

El cálculo conserva en paralelo la ampacidad de catálogo P2; no la reemplaza ni la presenta como normativa.

### P3C11 — cobertura de factores de corrección

P3C11 se ejecuta por subconjuntos primarios, pero **un subconjunto `PRIMARY_VERIFIED` no equivale a una familia completa**. El gate solo considera una familia 5A/5B/5C/5D/5E cubierta cuando un dataset/revisión declara explícitamente:

```text
p3c11_family_coverage = true
```

Los subconjuntos primarios actuales de Tabla 5C y Tabla 5A declaran `false`; por tanto P3C11 permanece bloqueado.

P3C11A incorpora el primer subconjunto primario de Tabla 5A:

```text
dataset = PERU_CNE_UTIL_2006_TABLE_5A_XLPE_AIR_A1_COL15_PRIMARY_V1
Tabla 2 / método A1 / columna 15 / XLPE-EPR / aire
35 °C -> 0.96
40 °C -> 0.91
```

La Tabla 5A oficial (PDF 563 / Tablas - Pág. 16 de 82) declara el primer bloque aplicable a columnas 2–16. Tabla 3 (PDF 555) confirma A1 + XLPE/EPR + 3 conductores → Tabla 2 Col. 15 y remite el factor de temperatura a Tabla 5A.

Se detectó además una inconsistencia normativa abierta: Tabla 3 remite B1/B2/C/D a Tabla 5A aunque sus columnas XLPE/EPR llegan hasta 25, y la Nota 3 de Tabla 2 también remite a Tabla 5A. El Manual de Sustentación confirma la intención de aplicar 5A-a/5A-b por temperatura, pero no elimina expresamente la restricción literal de columnas de la tabla.

Política del MCP: **fail-closed**. El dataset P3C11A no generaliza a columna 23 ni a cualquier otra combinación fuera de sus filas exactas. El binding automático hacia `Iz` queda pendiente hasta validar de forma determinista base/routing/temperatura.

Detalle: `docs/P3C11A_TABLE5A_PRIMARY.md`.

### Criterios actualmente bloqueantes

- `P3C11` — cobertura primaria completa declarada de las familias 5A/5B/5C/5D/5E del alcance P3-v1;
- `P3C12` — benchmarks normativos independientes contra fuente primaria;
- `P3C13` — madurez de ampacidad al menos `VALIDATED_WITH_LIMITATIONS`.

P3C10 `DONE` valida la **estrategia** de base normativa, no la cobertura completa de todas las filas de Tablas 1/2. La ampliación de dichas tablas seguirá utilizando el mismo contrato de lookup exacto y evidencia primaria.

## P3C12 — evidencia de benchmark, no constante

`P3C12` se deriva de `mcp_electrico/data/ampacity_benchmark_evidence.json` mediante `ampacity_benchmark_evidence.evaluar_cobertura()`.

Un benchmark solo cuenta para una familia P3-v1 si es `PASS`, tiene evidencia `PRIMARY`, usa una referencia independiente, está asociado a un dataset `PRIMARY_VERIFIED`, conserva el SHA-256 de una fuente primaria pinneada y satisface la política de revisión definida para benchmarks.

El benchmark P3B histórico de infraestructura permanece:

```text
PASS
SECONDARY
professional_normative_coverage = false
```

Por tanto, **no satisface P3C12**. Que CI esté verde demuestra reproducibilidad de infraestructura, no validación normativa independiente.

Detalle: `docs/P3_BENCHMARK_EVIDENCE.md`.

## Estado de fase vs. estado de modelo

`evaluar_cierre_p3()` devuelve ambos planos y además `benchmark_evidence`.

### Fase

```text
phase_status = NOT_READY
ready_for_next_phase = false
next_phase = null
professional_emission = false
```

Mientras exista un criterio pendiente, P3 no habilita formalmente P4.

### Modelo

El modelo activo puede ser:

- `MODEL_NOT_CONFIGURED`;
- `MODEL_NOT_READY`;
- `MODEL_TECHNICALLY_READY`.

Además se reporta por separado `normative_evidence` y `professional_normative_evidence_ready`.

Ejemplo válido durante desarrollo:

```text
technical_readiness = READY_TO_EXECUTE
normative_evidence = SECONDARY_EVIDENCE_ONLY
phase_status = NOT_READY
```

Esto significa que el cálculo puede ejecutarse para revisión/desarrollo, pero la fase y la evidencia profesional siguen abiertas.

## Regla para avanzar a P4

P4 solo aparece como `next_phase = P4_IEC_60909` cuando todos los criterios P3-v1 estén en `DONE`.

El gate por sí mismo:

- no promueve datasets;
- no eleva la madurez;
- no cambia `professional_emission`;
- no sustituye QA;
- no declara normativa válida por haber pasado CI.

La tool MCP es:

`evaluar_cierre_p3()`

Su función es hacer visible, de forma determinista, **qué falta exactamente** para cerrar P3 y evitar que el roadmap avance por impresión subjetiva.

Después de P3C11A, el siguiente subbloque natural es implementar el binding genérico seguro de factores `exact_rows_v1` hacia `Iz`, preservando la política fail-closed de compatibilidad; luego continuar con cobertura primaria 5B/5D/5E y ampliación controlada de 5A/5C.
