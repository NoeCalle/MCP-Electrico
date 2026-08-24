# Workspace — Flujo de potencia y caída de tensión

Esta guía describe la primera capa de estudios operativos integrada en el workspace HTML de MCP Eléctrico.

## Principio de operación

La arquitectura se mantiene:

```text
ChatGPT
   ↓
MCP Eléctrico
   ↓
OpenDSS
   ↓
resultados estructurados + revisiones
   ↓
workspace.html
```

El navegador **no calcula** flujo de potencia ni caída de tensión. Únicamente presenta el snapshot generado por el MCP.

## Herramientas MCP

### `ejecutar_flujo_potencia()`

Conserva el retorno histórico:

- convergencia;
- tensiones por bus;
- pérdidas kW/kvar.

Adicionalmente registra en el workspace el estudio `flow`, que incorpora por cada alimentador:

- corriente máxima del terminal 1;
- corrientes por conductor del terminal 1;
- flujo kW del terminal 1;
- flujo kvar del terminal 1;
- cargabilidad si existe una corriente nominal explícita disponible para el alimentador.

### `analizar_flujo_operacion()`

Devuelve directamente el estudio detallado completo y actualiza el workspace.

Ejemplo conversacional:

```text
Ejecuta el flujo de potencia y muéstrame los alimentadores más cargados.
```

### `analizar_caida_tension(limite_pct=3.0)`

Resuelve el circuito y calcula caída bus1 → bus2 por cada `Line`.

Ejemplo:

```text
Analiza la caída de tensión con límite de 2.5 %.
```

El resultado incluye:

- Vpu promedio en origen;
- Vpu promedio en destino;
- caída por fase;
- caída promedio firmada;
- caída evaluada;
- estado `OK` / `EXCEDE` respecto al criterio suministrado.

## Sobre el límite porcentual

El valor por defecto `3.0` es únicamente una comodidad de interfaz.

El resultado serializado deja explícito:

```json
{
  "criterio": {
    "limite_pct": 3.0,
    "origen": "configurable_por_usuario",
    "normativo_universal": false
  }
}
```

MCP Eléctrico no debe presentar ese valor como requisito universal. El criterio correcto depende del proyecto, reglamento, norma y alcance del estudio.

## Pestaña Flujo

El workspace muestra una tabla con:

| Campo | Significado |
|---|---|
| Alimentador | rótulo de ingeniería |
| Trayecto | bus1 → bus2 |
| Corriente máx. | mayor magnitud del terminal 1 |
| kW T1 | suma de P de los conductores del terminal 1 |
| kvar T1 | suma de Q de los conductores del terminal 1 |
| Cargabilidad | Imax / Inom, únicamente si Inom existe |

La pestaña también resume pérdidas, corriente máxima y cargabilidad máxima disponible.

## Pestaña Caída V

Muestra:

- límite configurado;
- número de alimentadores que exceden el criterio;
- mínima tensión pu del sistema;
- tabla completa por alimentador.

La fila se marca visualmente como:

- `OK`: dentro del criterio;
- `EXCEDE`: superior al criterio suministrado.

## Vigencia de resultados

Los estudios están ligados a `model_revision`.

Si después del cálculo se agrega una carga, cambia una impedancia o se abre/cierra persistentemente un elemento, el workspace marca automáticamente los estudios anteriores como no vigentes.

Un cambio exclusivamente visual no invalida los estudios.

## Cargabilidad, catálogo y ampacidad

La biblioteca de conductores BT/MT ya existe y permite aplicar un producto comercial trazable a un `Line.*` mediante `aplicar_conductor(...)`.

Cuando la ficha cargada contiene una ampacidad publicada para la instalación elegida, el MCP puede actualizar `Line.NormAmps` y conservar la procedencia del dato. En cables MT donde además existe un par R/X verificable, también puede actualizar la impedancia del modelo; en BT, si falta X verificable, la impedancia previa se conserva deliberadamente.

También sigue siendo posible declarar manualmente `corriente_nominal_a` como metadato del alimentador. En cualquiera de los dos casos, la cargabilidad mostrada por el estudio representa una comparación contra el rating disponible:

```text
cargabilidad = Imax / Inom × 100
```

Esto **no equivale todavía a una verificación normativa de ampacidad**. P3 deberá calcular `Iz` considerando método de instalación, temperatura, agrupamiento, suelo/resistividad y factores de corrección según la norma aplicable.

La biblioteca y sus reglas de trazabilidad se documentan en `docs/CONDUCTORES.md`.

## Selección desde tablas

Las filas de `Flujo` y `Caída V` conservan el ID del elemento, por ejemplo:

```text
Line.f_motor
```

Al hacer clic, el workspace sincroniza ese ID con el inspector técnico. Así el usuario puede regresar a ChatGPT y pedir, por ejemplo:

```text
En Line.f_motor, aumenta la sección del conductor y vuelve a analizar la caída.
```

## Limitaciones de esta versión

- solo se evalúa caída individual sobre objetos `Line`;
- aún no existe reporte de caída acumulada hasta cada carga;
- transformadores no tienen todavía una vista de cargabilidad;
- no se derivan ampacidades normativas a partir de condiciones de instalación;
- no se aplican límites regulatorios automáticos;
- el inspector todavía debe ampliar la ficha estructurada del conductor y su procedencia;
- una pestaña ya abierta sigue requiriendo recarga para leer el archivo regenerado.

## Evolución visual siguiente

La biblioteca de conductores ya dejó de ser solo texto de presentación. El siguiente paso visual, definido en `docs/ROADMAP_VISUAL.md`, es integrar en P2 la ficha estructurada de conductor, transformador y fuente equivalente directamente en el inspector, manteniendo la misma identidad estable de los elementos y sin mover cálculos eléctricos al navegador.
