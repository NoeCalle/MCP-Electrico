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

### Infraestructura ya implementada

- `P3C01` — contrato `Ib/In/Iz`;
- `P3C02` — router normativo P3A;
- `P3C03` — infraestructura de datasets numéricos versionados;
- `P3C04` — gate de evidencia primaria y pin de fuente;
- `P3C05` — binding trazable dataset → factor → `Iz`;
- `P3C06` — readiness de evidencia separado de `READY_DATA`;
- `P3C07` — evidencia visible en workspace V3.

### Criterios actualmente bloqueantes

- `P3C08` — fuente oficial primaria pinneada por SHA-256;
- `P3C09` — al menos una revisión numérica `PRIMARY_VERIFIED` apta para emisión;
- `P3C10` — estrategia validada de `Iz_base`;
- `P3C11` — cobertura primaria de las familias 5A/5B/5C/5D/5E del alcance P3-v1;
- `P3C12` — benchmarks normativos independientes contra fuente primaria;
- `P3C13` — madurez de ampacidad al menos `VALIDATED_WITH_LIMITATIONS`.

## P3C12 — evidencia de benchmark, no constante

`P3C12` se deriva de `mcp_electrico/data/ampacity_benchmark_evidence.json` mediante `ampacity_benchmark_evidence.evaluar_cobertura()`.

Un benchmark solo cuenta para una familia P3-v1 si es `PASS`, tiene evidencia `PRIMARY`, usa una referencia independiente, está asociado a un dataset `PRIMARY_VERIFIED`, conserva el SHA-256 de una fuente primaria pinneada y tiene revisión humana confirmada.

El benchmark P3B actual permanece:

```text
PASS
SECONDARY
professional_normative_coverage = false
```

Por tanto, **no satisface P3C12**. Que CI esté verde demuestra reproducibilidad de infraestructura, no validación normativa primaria.

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