# P3 — Registro de evidencia de benchmarks normativos

## Objetivo

Evitar que `P3C12` dependa de una constante manual o de la simple existencia de un benchmark verde.

El registro `mcp_electrico/data/ampacity_benchmark_evidence.json` conserva evidencia por familia normativa y distingue:

- que un benchmark haya ejecutado con `PASS`;
- que su referencia sea realmente independiente;
- que el dataset asociado sea `PRIMARY_VERIFIED`;
- que la fuente primaria esté pinneada por SHA-256;
- que exista revisión humana documentada;
- que el caso pueda contar como cobertura normativa primaria.

## Regla de calificación

Un registro solo puede satisfacer una familia de `P3C12` si cumple simultáneamente:

```text
result = PASS
evidence_level = PRIMARY
independent_reference = true
dataset_verification_status = PRIMARY_VERIFIED
source_sha256 = <hash primario pinneado>
review_record.reviewer != vacío
review_record.manual_comparison_confirmed = true
professional_normative_coverage = true
```

Un `PASS` secundario no se convierte en benchmark primario por haber pasado CI.

## Registro actual

El benchmark P3B existente está registrado como:

`P3B_TABLE_5C_SECONDARY_INFRA_V1`

Su situación es deliberadamente:

```text
result = PASS
evidence_level = SECONDARY
independent_reference = false
dataset_verification_status = PENDING_PRIMARY_VERIFICATION
professional_normative_coverage = false
```

Por tanto, prueba la infraestructura de lookup y regresión, pero **no satisface ni siquiera la familia Table_5C_grouping_air para P3C12**.

## Cobertura requerida P3-v1

El gate exige benchmark primario independiente para cada familia:

1. `base_ampacity_strategy_Table_1_2_or_validated_equivalent`;
2. `Table_5A_temperature`;
3. `Table_5B_soil_thermal_resistivity_when_applicable`;
4. `Table_5C_grouping_air`;
5. `Table_5D_grouping_buried_method_D`;
6. `Table_5E_arrangement_branches_when_applicable`.

`ampacity_benchmark_evidence.evaluar_cobertura()` devuelve cobertura individual, registros disponibles, razones de no calificación y familias faltantes.

## Relación con el gate P3

`p3_completion.evaluar_cierre_p3()` incorpora ahora:

`benchmark_evidence`

El criterio `P3C12` queda en `DONE` únicamente cuando:

`benchmark_evidence.ready = true`

No existe un booleano manual que permita saltarse la evidencia.

## Seguridad

La cobertura de benchmark por sí sola:

- no promueve datasets;
- no cambia `PRIMARY_VERIFIED`;
- no eleva la madurez de ampacidad;
- no habilita `professional_emission`;
- no sustituye P3C08–P3C11 ni P3C13.

Los fixtures sintéticos de tests pueden demostrar que la lógica reconoce una cobertura primaria completa, pero el gate del producto consume exclusivamente el registro versionado real del repositorio.