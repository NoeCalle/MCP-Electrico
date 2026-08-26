# P3 — Gate formal de salida de ampacidad

## Estado

**READY_WITH_LIMITATIONS — P3-v1 CERRADA.**

`evaluar_cierre_p3()` separa la madurez/cobertura del producto del estado de un modelo concreto. Con los trece criterios `P3C01`–`P3C13` en `DONE`, el gate devuelve:

```text
phase_status = READY_WITH_LIMITATIONS
ready_for_next_phase = true
next_phase = P4_IEC_60909
professional_emission = false
```

`professional_emission=false` es deliberado: cerrar P3 no sustituye el QA del modelo, la calidad de sus datos ni la revisión del ingeniero responsable.

## Alcance P3-v1

- jurisdicción: Perú;
- referencia: `PERU_CNE_UTILIZACION_2006`;
- perfil: `PERU_CNE_UTIL_2006_030_004`;
- regla: 030-004;
- métodos enrutados: A1, A2, B1, B2, C, D, E, F y G;
- contrato: `Ib <= In <= Iz`, con `Iz = Iz_base * product(k_i)`.

## Evidencia de cierre

- P3C01–P3C07: contrato, router, datasets, evidencia, bindings, readiness y V3;
- P3C08: fuente oficial MINEM/CNE pinneada por SHA-256;
- P3C09: datasets numéricos `PRIMARY_VERIFIED`;
- P3C10: estrategia `Iz_base` primaria exacta de Tablas 1/2 demostrada;
  caso de referencia: `PERU_CNE_UTIL_2006_TABLE_2_COL23_C_XLPE_3C_CU_70MM2_PRIMARY_V1`, método C, 70 mm², `ampacity_a = 229 A`;
- P3C11: cobertura primaria declarada de 5A/5B/5C/5D/5E;
- P3C12: referencias primarias independientes, 29/29 casos PASS, seis familias;
  el gate deriva esta cobertura mediante `ampacity_benchmark_evidence.evaluar_cobertura()` y vuelve a comprobar la suite independiente viva;
- P3C13: módulo `ampacity` elevado a `VALIDATED_WITH_LIMITATIONS`.

El benchmark histórico P3B con evidencia `SECONDARY` se conserva como regresión de infraestructura, pero no califica para P3C12 ni habilita cobertura normativa profesional. El objeto `benchmark_evidence` del gate distingue explícitamente esta evidencia secundaria de los benchmarks `PRIMARY` independientes.

Fuente primaria pinneada:

```text
source_id = MINEM_CNE_UTIL_2006_OFFICIAL_PDF
expected_sha256 = 2b3cbd457c519bf9d9aa2cf2754c72b6e531708e45ea2fdf91f839b1acccfd64
```

## Qué significa VALIDATED_WITH_LIMITATIONS

P3-v1 es utilizable dentro de su alcance declarado, pero no equivale a una transcripción universal del CNE:

1. Tablas 1/2 no están cargadas exhaustivamente; `Iz_base` profesional requiere coincidencia exacta con una fila `PRIMARY_VERIFIED`.
2. No existe interpolación, extrapolación ni vecino más cercano.
3. Cobertura primaria de una tabla no implica binding automático de toda combinación física.
4. Tabla 5A mantiene fail-closed para columnas 20–25 por la inconsistencia editorial identificada.
5. Datasets secundarios históricos requieren opt-in y nunca habilitan emisión profesional.
6. IEC 60364-5-52:2009+AMD1:2024 continúa `REFERENCE_ONLY`.

## Estado de modelo

Un modelo concreto puede ser `MODEL_NOT_CONFIGURED`, `MODEL_NOT_READY` o `MODEL_TECHNICALLY_READY`. Su evidencia normativa se evalúa aparte. Por ello una fase P3 cerrada puede coexistir con un modelo que use evidencia secundaria y no sea apto para emisión.

## Paso a P4

P4 IEC 60909 queda formalmente habilitada como siguiente fase del roadmap. Esto no convierte el actual `OpenDSS FaultStudy` en IEC 60909: el módulo `short_circuit` permanece `UNDER_VALIDATION` hasta que P4 implemente y valide el método formal.
