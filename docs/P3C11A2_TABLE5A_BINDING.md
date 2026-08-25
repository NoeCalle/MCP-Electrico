# P3C11A2 — Binding seguro de Tabla 5A hacia `Iz`

## Objetivo

P3C11A creó el primer subconjunto primario de Tabla 5A, pero deliberadamente no lo conectó al cálculo. P3C11A2 incorpora el contrato que permite que un factor `exact_rows_v1` llegue a:

```text
Iz = Iz_base × product(k_i)
```

solo cuando la fila numérica y el contexto del modelo son exactamente compatibles.

## Principio fail-closed

Resolver un número no significa que ese número sea aplicable al alimentador.

Para `axis = ambient_temperature`, el binding exige simultáneamente:

1. misma referencia normativa entre factor, base y routing;
2. mismo perfil P3A;
3. mismo método de instalación;
4. mismo ambiente;
5. misma temperatura ambiente declarada;
6. mismo aislamiento;
7. misma tabla base;
8. misma columna base.

Si falta `Iz_base` normativa, Tabla 5A no se aplica sobre la ampacidad de catálogo P2. Si alguna condición cambia, el cálculo se bloquea.

## Estado real del catálogo tras P3C11A

Factor disponible:

```text
PERU_CNE_UTIL_2006_TABLE_5A_XLPE_AIR_A1_COL15_PRIMARY_V1
A1 / Tabla 2 col.15 / XLPE-EPR / aire
35 °C -> 0.96
40 °C -> 0.91
```

Base normativa primaria disponible:

```text
PERU_CNE_UTIL_2006_TABLE_2_COL23_C_XLPE_3C_CU_70MM2_PRIMARY_V1
C / Tabla 2 col.23 / XLPE-EPR / Cu / 70 mm2
Iz_base = 229 A
```

Estas dos revisiones **no son compatibles**. El MCP debe rechazarlas y lo hace de forma explícita. P3C11A2 no crea ni infiere una base A1/col.15.

## Revalidación hasta el cálculo

El factor se revalida contra el catálogo:

- al ejecutar `definir_condiciones_ampacidad()`;
- nuevamente al ejecutar `evaluar_ampacidad()`.

La segunda validación evita estado obsoleto. Ejemplo:

```text
configuración inicial: A1 / aire / 35 °C / kT=0.96
cambio posterior:       A1 / aire / 40 °C
resultado:               DATOS_INSUFICIENTES
causa:                   factor 35 °C ya no coincide con routing actual
```

No se reutiliza silenciosamente `0.96`.

## Tool MCP genérica

```text
resolver_factor_normativo_ampacidad(dataset_id, consulta, permitir_dataset_secundario=false)
```

La tool usa `exact_rows_v1`. Si existe coincidencia exacta devuelve `factor_p3` portable con query, metadata de fila, procedencia y estado de evidencia.

El resultado todavía debe pasar el binding contextual al configurar `Ib/In/Iz`.

## Visual V3

V3 incorpora una columna **Factores aplicados** preparada completamente por Python. Puede mostrar, por ejemplo:

```text
ambient_temperature: k=0.96 · Tabla 5A · 35 °C · <dataset_id>
```

Además, el detalle de `Iz_base` muestra la columna normativa cuando está disponible.

El navegador:

- no selecciona factores;
- no resuelve tablas;
- no multiplica `k`;
- no decide compatibilidad;
- no evalúa `Ib <= In <= Iz`.

Solo presenta el resultado ya validado por MCP/Python.

## Alcance de este PR

P3C11A2 implementa únicamente la política contextual para Tabla 5A / `ambient_temperature`.

Los futuros factores genéricos 5B/5D/5E no se aceptan automáticamente por reutilizar `exact_rows_v1`; cada familia deberá declarar su propia política de compatibilidad.

## Estado de fase

Este bloque no aumenta cobertura normativa y no cierra P3C11.

```text
P3C01-P3C10 = DONE
P3C11 = PENDING
P3C12 = PENDING
P3C13 = PENDING
P3 = NOT_READY / UNDER_VALIDATION
P4 = bloqueada
professional_emission = false
```
