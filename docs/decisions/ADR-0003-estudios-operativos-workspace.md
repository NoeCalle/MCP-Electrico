# ADR-0003 — Estudios operativos en el workspace

- **Estado:** Aceptado
- **Fecha:** 2026-08-23
- **Contexto:** PR #6 — flujo de potencia y caída de tensión integrados en el workspace

## Contexto

MCP Eléctrico ya dispone de un workspace HTML persistente y de un inspector técnico read-only. La siguiente necesidad es mostrar estudios operativos dentro del mismo workspace sin convertir el HTML en un segundo motor de cálculo ni mezclar criterios normativos con resultados eléctricos.

OpenDSS sigue siendo el motor que resuelve tensiones, corrientes y pérdidas. ChatGPT sigue siendo la interfaz conversacional. El MCP debe organizar resultados estructurados, registrar su revisión y generar una vista verificable.

## Decisión 1 — OpenDSS conserva la autoridad del cálculo eléctrico

Las tensiones y corrientes no se recalculan en JavaScript. Los estudios llaman a OpenDSS a través de `core.ejecutar_flujo_potencia()` y de las API de `CktElement` para extraer corrientes y potencias del elemento activo.

El navegador únicamente presenta datos ya calculados y serializados en el snapshot.

## Decisión 2 — Los estudios derivados viven en `mcp_electrico/studies.py`

Se crea una capa independiente para:

- flujo detallado por alimentador;
- tensiones resumidas por bus;
- caída de tensión por cada `Line`;
- cargabilidad cuando existe una corriente nominal explícita.

`core.py` permanece como motor eléctrico general y no recibe lógica de presentación ni criterios de aceptación.

## Decisión 3 — Resultado eléctrico y criterio de evaluación son objetos distintos

`analizar_caida_tension(limite_pct=...)` conserva explícitamente:

```text
criterio.limite_pct
criterio.origen = configurable_por_usuario
criterio.normativo_universal = false
```

El valor por defecto de 3 % facilita el uso, pero **no se declara como exigencia normativa universal**. El usuario puede proporcionar otro límite según proyecto, reglamento o especificación aplicable.

## Decisión 4 — Metodología inicial de caída de tensión

Para cada `Line` se utilizan los buses declarados `bus1` y `bus2`.

Para cada fase disponible se calcula:

```text
ΔV% = (Vpu_bus1 - Vpu_bus2) / Vpu_bus1 × 100
```

Se conservan:

- caída por fase;
- caída promedio firmada;
- máxima caída positiva disponible (`caida_evaluada_pct`).

La comparación con el límite se realiza sobre `caida_evaluada_pct`.

Esta definición evita ocultar una fase desfavorable en redes desequilibradas y conserva, al mismo tiempo, la información firmada que permite identificar elevación de tensión.

## Decisión 5 — La cargabilidad no se inventa

OpenDSS entrega corriente del alimentador. Para calcular:

```text
cargabilidad_pct = Imax / Inom × 100
```

se exige que `corriente_nominal_a` exista explícitamente en los metadatos del alimentador.

Mientras MCP Eléctrico no implemente una biblioteca normativa de conductores, esa corriente nominal se identifica como:

```text
fuente_corriente_nominal = metadato_explicito_usuario
```

Por tanto, la pestaña Flujo no afirma que una cargabilidad menor de 100 % constituya por sí sola una validación normativa de ampacidad.

## Decisión 6 — Los estudios usan el mismo sistema de revisiones del workspace

Se registran dos estudios adicionales:

```text
flow
voltage_drop
```

Cada uno queda asociado a `model_revision` y recibe automáticamente `valid=false` cuando cambia el modelo.

No se crea una segunda máquina de estados.

## Decisión 7 — `ejecutar_flujo_potencia()` conserva compatibilidad

La tool existente sigue devolviendo el payload histórico de `powerflow`.

Internamente, además registra el estudio `flow` detallado. Se añade una tool explícita:

```text
analizar_flujo_operacion()
```

para quien necesite el detalle completo por alimentador.

Esto evita romper clientes existentes.

## Decisión 8 — Las vistas de estudios son read-only

Las pestañas `Flujo` y `Caída V` no modifican parámetros OpenDSS. Hacer clic en una fila únicamente sincroniza la selección con el inspector técnico existente.

Cualquier cambio continúa entrando por:

```text
ChatGPT → MCP → OpenDSS → snapshot → HTML
```

## Decisión 9 — Overlay visual basado en IDs del modelo

Las vistas intentan resaltar nodos que ya posean `data-element-id` en el SVG interactivo. El color comunica el estado del estudio:

- caída dentro del criterio: verde;
- caída que excede el criterio: rojo;
- flujo con rating disponible: azul;
- cargabilidad >100 % respecto al rating explícito: rojo.

El resultado numérico de la tabla sigue siendo la fuente principal; el color es solo una ayuda visual.

## Decisión 10 — La UI de estudios se desacopla del HTML base

Se crea `workspace_studies_view.py` para añadir las pestañas y paneles sobre el workspace base ya regenerado.

Motivo: evitar que `workspace.py` se convierta en un archivo monolítico que mezcle estado, inspector y cada nuevo estudio. La extensión consume únicamente el snapshot y es idempotente mediante el marcador:

```text
<!-- MCP-STUDIES-V1 -->
```

Una evolución futura puede convertir esta extensión en un sistema formal de vistas/plugins del workspace.

## Consecuencias positivas

- los cálculos siguen siendo reproducibles y rastreables;
- el HTML no puede producir por sí solo resultados eléctricos nuevos;
- un cambio de modelo invalida automáticamente flujo y caída;
- se conserva compatibilidad con la tool histórica de flujo;
- se evita presentar 3 % como regla universal;
- el usuario puede inspeccionar resultados en la misma interfaz visual del circuito.

## Limitaciones aceptadas

1. La caída inicial se calcula únicamente sobre objetos `Line`.
2. No existe todavía caída acumulada por ruta completa hasta cada carga como estudio independiente.
3. No se evalúan límites normativos de tensión por país/estándar.
4. La corriente nominal sigue siendo un dato explícito, no una ampacidad calculada por método de instalación.
5. El overlay depende de los IDs que el workspace interactivo enlaza al SVG; el renderer nativo aún debe evolucionar para emitir todos los IDs directamente.
6. Transformadores todavía no muestran cargabilidad térmica en esta fase.

## Siguiente decisión prevista

La siguiente fase debería formalizar el modelo de conductores (material, sección, aislamiento, instalación, impedancias, ampacidad y procedencia del dato) antes de convertir la cargabilidad en una verificación de diseño más completa.
