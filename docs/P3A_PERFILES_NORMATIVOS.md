# P3A — Perfiles normativos de aplicabilidad para ampacidad

## Estado

**IMPLEMENTADO COMO ROUTER NORMATIVO — UNDER_VALIDATION.**

P3A no implementa todavía tablas numéricas completas de ampacidad. Su función es anterior y deliberadamente más estricta: determinar **qué regla, tabla base y eje de corrección resultan aplicables** antes de aceptar factores manuales en la ficha `Ib/In/Iz`.

El objetivo es evitar tres errores frecuentes:

1. usar una ampacidad de catálogo como `Iz` final sin revisar condiciones;
2. aplicar un factor correcto a una condición o edición normativa equivocada;
3. mezclar silenciosamente CNE 2006 e IEC 60364-5-52:2024.

## Perfiles registrados

### `PERU_CNE_UTIL_2006_030_004`

Perfil de routing para el **Código Nacional de Electricidad — Utilización**, aprobado por R.M. N.° 0037-2006-MEM, Regla 030-004.

Fuente legal registrada:

- https://www.gob.pe/institucion/minem/normas-legales/108855-0037-2006-mem

El router modela actualmente:

- métodos A1, A2, B1, B2, C y D → **Tabla 2**;
- métodos E, F y G → **Tabla 1**;
- corrección por temperatura → Regla 030-004(8) / **Tabla 5A**;
- corrección por resistividad térmica del suelo, dentro del alcance modelado para método D en ductos enterrados → Regla 030-004(9) / **Tabla 5B**;
- agrupamiento → Regla 030-004(1)(c), (10) / **Tabla 5C** y ramas que requieren distinguir disposición física al aire;
- transición subterránea → visible dentro del alcance de 030-004(13): gobierna la menor ampacidad aplicable;
- 030-004(14): **no se automatiza**. Si se solicita la excepción de tramo corto, P3A exige revisión manual.

Condiciones base registradas para el routing CNE:

- aire: 30 °C;
- ducto enterrado/tierra: 20 °C;
- resistividad térmica base del suelo: 2,5 K·m/W.

Estas condiciones permiten saber si un eje de corrección es necesario, pero **no devuelven por sí mismas el valor del factor**.

### `IEC_60364_5_52_2009_A1_2024`

Referencia internacional registrada:

- IEC 60364-5-52:2009+AMD1:2024;
- edición consolidada 3.1;
- fecha de publicación 2024-11-22;
- fuente oficial: https://webstore.iec.ch/en/publication/103734

Estado P3A: `REFERENCE_ONLY`.

La edición IEC está registrada para trazabilidad, pero sus tablas/datasets no están cargados. MCP Eléctrico **no reutiliza** valores CNE 2006 bajo el identificador IEC 2024.

## Estados del router

P3A puede devolver:

- `BASE_CONDITIONS_IDENTIFIED`: las variables declaradas coinciden con las condiciones base modeladas y no se identifican ejes de corrección;
- `REQUIREMENTS_IDENTIFIED`: se identificó uno o más ejes de corrección, pero el valor numérico de la tabla sigue `TABLE_DATA_NOT_LOADED`;
- `MISSING_INPUTS`: faltan datos para decidir la aplicabilidad;
- `MANUAL_REVIEW_REQUIRED`: la regla requiere una clasificación o revisión que P3A no automatiza;
- `TABLE_DATA_NOT_LOADED`: perfil registrado sin dataset/routing numérico suficiente, caso actual de IEC 2024.

## Vinculación con la ficha `Ib/In/Iz`

La tool `definir_aplicabilidad_normativa_ampacidad()` permite asociar un routing a un `Line.*`.

Cuando existe routing vinculado:

1. la referencia normativa de la ficha P3 debe coincidir con `norm_reference_id` del perfil;
2. si el router identifica ejes obligatorios, no puede usarse `confirmar_condiciones_base=True`;
3. cada factor manual debe declarar `axis` para demostrar qué eje cubre;
4. si el routing cambia después, `evaluar_ampacidad()` y el readiness vuelven a comprobar la consistencia;
5. una revisión manual pendiente bloquea `READY_DATA`.

Ejemplo conceptual:

```text
Método C
T ambiente = 35 °C
1 circuito

→ Tabla base: Tabla 2
→ Eje requerido: ambient_temperature
→ Referencia: 030-004(8) / Tabla 5A
→ Valor numérico: TABLE_DATA_NOT_LOADED
```

La ficha puede aceptar posteriormente un factor manual trazable:

```json
{
  "id": "k_temp",
  "axis": "ambient_temperature",
  "value": 0.96,
  "reference": "fuente autorizada del proyecto",
  "table_or_clause": "030-004(8) / Tabla 5A"
}
```

P3A valida el **vínculo lógico**, no certifica todavía que `0.96` sea el valor normativo correcto. Esa verificación requiere el futuro dataset numérico versionado y sus benchmarks.

## Regla 030-004(13)-(14)

P3A restringe expresamente 030-004(13) a su alcance declarado: la aparición de más de una ampacidad aplicable como consecuencia de la transición de una porción subterránea a otra visible.

No se generaliza la regla a cualquier cambio de instalación.

La excepción de 030-004(14) permanece manual. El software no decide automáticamente si un tramo corto puede adoptar la ampacidad de otra porción.

## Casos patrón

Los casos de regresión están separados del algoritmo en:

`mcp_electrico/data/ampacity_p3a_reference_cases.json`

Cubren al menos:

- método C en condiciones base;
- método C con corrección de temperatura;
- método D con temperatura, resistividad y agrupamiento;
- método F agrupado con revisión de disposición;
- transición dentro del alcance 030-004(13);
- IEC 2024 como `REFERENCE_ONLY`.

Estos casos validan el **routing**. No son todavía benchmarks de valores numéricos de tablas.

## Lo que P3A no hace

- no copia tablas IEC completas;
- no presenta factores CNE como si fueran IEC 2024;
- no calcula automáticamente factores 5A/5B/5C/5E;
- no decide la excepción 030-004(14);
- no convierte el módulo `ampacity` en `VALIDATED_WITH_LIMITATIONS`;
- no habilita emisión profesional automática.

## Siguiente bloque de P3

Para elevar la madurez se necesita un bloque P3B con datasets numéricos de alcance y procedencia legal explícitos, selección por aislamiento/método/sección, pruebas manuales independientes y gate formal de salida P3.
