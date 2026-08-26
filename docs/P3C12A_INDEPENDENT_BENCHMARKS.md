# P3C12A — benchmarks normativos primarios independientes

P3C12A añade la infraestructura de validación independiente necesaria antes de permitir que el gate `P3C12` pase a `DONE`.

## Principio

Un dataset no puede validarse usando como referencia el mismo valor que contiene. Por eso los valores esperados de este bloque viven en `ampacity_p3c12_independent_reference.json`, separado de los datasets de producción, y se declaran como transcripción de páginas de la fuente primaria pinneada.

El runner `ampacity_independent_benchmarks` toma cada referencia esperada y consulta el resolver real del producto. La suite solo pasa cuando:

- la fuente primaria coincide con el SHA-256 pinneado;
- el lookup devuelve `RESOLVED_EXACT`;
- el dataset consultado permanece `PRIMARY_VERIFIED`;
- la consulta está habilitada para evidencia profesional exacta;
- el valor calculado coincide con la referencia independiente dentro de la tolerancia declarada.

## Cobertura P3-v1

La suite contiene 29 casos sobre las seis familias exigidas por P3C12:

1. `Iz_base` de Tabla 1/2 o equivalente validado;
2. Tabla 5A — temperatura;
3. Tabla 5B — resistividad térmica del suelo;
4. Tabla 5C — agrupamiento en aire;
5. Tabla 5D — agrupamiento enterrado método D;
6. Tabla 5E — disposiciones en aire.

Se seleccionan casos distribuidos en distintas filas, ramas y disposiciones; no se limita la validación a una única celda representativa.

## Prueba contra validación circular

Los tests mutan deliberadamente una referencia primaria: el caso de 229 A se cambia temporalmente a 230 A. La suite debe producir `FAIL` y conservar como valor real 229 A. Esto demuestra que el resultado no se autojustifica leyendo el valor esperado desde el dataset de producción.

## CI

`examples/run_benchmarks_p3c12.py` genera `benchmark_p3c12.json`. GitHub Actions exige:

```text
failed = 0
pass = true
reference_evidence = PRIMARY_INDEPENDENT
independent_reference = true
```

El JSON se publica como artifact `mcp-electrico-benchmarks-p3c12`.

## Gate

P3C12A **no cambia todavía** `ampacity_benchmark_evidence.json`. Por diseño, después de este PR:

```text
P3C11 = DONE
P3C12 = PENDING
P3C13 = PENDING
P4    = BLOQUEADA
```

La promoción formal de las seis familias al registro de evidencia pertenece a P3C12B y solo debe realizarse después de que esta suite independiente esté verde en CI.
