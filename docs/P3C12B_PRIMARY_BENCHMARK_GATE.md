# P3C12B — promoción formal de benchmarks primarios independientes

P3C12B conecta el registro formal de evidencia del gate P3 con la suite independiente introducida en P3C12A.

## Regla de seguridad

Un registro con `result=PASS` y `evidence_level=PRIMARY` ya no califica por ser estático. Para el modo producto debe además declarar:

- `benchmark_suite_id=P3C12_PRIMARY_INDEPENDENT_REFERENCE_V1`;
- `benchmark_family` idéntica a la familia que pretende cubrir;
- referencia independiente;
- dataset `PRIMARY_VERIFIED`;
- SHA-256 de la fuente primaria pinneada;
- revisión explícita;
- `professional_normative_coverage=true`.

Durante la evaluación real, `ampacity_benchmark_evidence` ejecuta la suite independiente P3C12A y comprueba que:

- la suite global continúe PASS;
- la familia concreta continúe PASS;
- el SHA-256 de la suite coincida con el declarado por el benchmark.

Por tanto, editar solamente el JSON de evidencia no puede cerrar P3C12 si el benchmark real deja de pasar.

## Evidencia CI base

La promoción se apoya en la ejecución P3C12A ya integrada:

- workflow run: `33009898372`;
- artifact: `9622086390` (`mcp-electrico-benchmarks-p3c12`);
- digest: `sha256:3fe5839700395937648184be461b7ba9159ba0d551f004ba19db91a40c852400`;
- resultado: 29/29 casos PASS sobre las seis familias P3-v1.

El artifact es evidencia histórica reproducible; el gate no confía únicamente en él y vuelve a ejecutar la suite viva.

## Seis familias registradas

`ampacity_benchmark_evidence.json` contiene un registro PRIMARY por cada familia requerida:

1. base de ampacidad Tabla 1/2;
2. Tabla 5A;
3. Tabla 5B;
4. Tabla 5C;
5. Tabla 5D;
6. Tabla 5E.

El benchmark secundario histórico P3B se conserva y sigue sin calificar como evidencia primaria.

## Efecto en el gate

Después de P3C12B:

```text
P3C01-P3C12 = DONE
P3C13       = PENDING
P3          = NOT_READY
P4          = BLOQUEADA
```

P3C12 no cambia la madurez del módulo ni habilita emisión profesional global. El único bloqueante formal restante es P3C13.
