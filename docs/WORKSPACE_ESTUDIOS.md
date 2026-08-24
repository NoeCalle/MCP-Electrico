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
- cargabilidad si existe `corriente_nominal_a` explícita.

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

## Cargabilidad y ampacidad

Actualmente `corriente_nominal_a` proviene de un metadato explícito configurado en el alimentador.

Ejemplo:

```python
server.configurar_alimentador_unifilar(
    "Line.f_motor",
    etiqueta="F-01",
    conductor="3x70 mm2 Cu XLPE",
    corriente_nominal_a=160,
)
```

El cálculo:

```text
cargabilidad = Imax / 160 A × 100
```

es válido respecto a ese rating declarado, pero **no significa que MCP Eléctrico haya verificado normativamente la ampacidad del cable**.

La biblioteca de conductores será una fase posterior.

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
- no se derivan ampacidades a partir de condiciones de instalación;
- no se aplican límites regulatorios automáticos;
- una pestaña ya abierta sigue requiriendo recarga para leer el archivo regenerado.

## Próxima fase recomendada

Crear un modelo formal de conductores y cables con:

- material;
- sección;
- aislamiento;
- tensión nominal;
- número de conductores;
- método de instalación;
- longitud;
- R/X;
- ampacidad;
- procedencia del dato.

Eso permitirá que el workspace deje de mostrar el conductor solo como texto y pueda relacionar diseño físico, modelo OpenDSS y verificación de cargabilidad.
