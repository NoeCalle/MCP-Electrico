# Workspace persistente

El workspace es el visor técnico del circuito activo de MCP Eléctrico.

## Principio de uso

La conversación permanece en ChatGPT. El HTML no contiene un segundo chat ni
usa una API de modelos. Cada tool MCP actualiza OpenDSS y, cuando corresponde,
regenera `workspace.html`.

## Tools nuevas

### `configurar_workspace`

Configura la ruta estable del HTML, su título y si debe regenerarse
automáticamente.

Ejemplo conceptual:

```text
configurar_workspace(
    ruta_salida="workspace.html",
    titulo="Hospital — Sistema eléctrico",
    auto_regenerar=true
)
```

### `obtener_estado_workspace`

Devuelve:

- ruta configurada;
- estado `EMPTY`, `MODIFIED`, `SOLVED` o `ERROR`;
- revisión actual del modelo;
- revisión que fue resuelta;
- revisión visual;
- si los resultados actuales son vigentes;
- estudios registrados y su bandera `valid`;
- errores eléctricos y de visualización por separado.

### `regenerar_workspace`

Fuerza la regeneración manual del HTML y SVG compañero.

## Estados

### `EMPTY`

No existe un circuito activo utilizable.

### `MODIFIED`

La topología o parámetros eléctricos cambiaron después de la última solución.
El HTML muestra una advertencia y los estudios previos quedan con `valid=false`.

### `SOLVED`

La revisión actual del modelo coincide con la revisión resuelta y el flujo
convergió.

### `ERROR`

El último cálculo eléctrico relevante no convergió o se registró un error
eléctrico. Un error de HTML/SVG se reporta aparte como `workspace_error` y no
cambia por sí solo el estado eléctrico.

## Regeneración automática

Actualmente se actualiza el archivo después de:

- crear circuito;
- agregar línea;
- agregar transformador;
- agregar carga;
- agregar generador;
- cambiar simbología o etiquetas;
- configurar barras/alimentadores;
- ejecutar flujo de potencia;
- abrir/cerrar elementos;
- ejecutar cortocircuito;
- simular contingencias.

El archivo se reescribe automáticamente, pero una pestaña del navegador que ya
está abierta sobre un archivo local no detecta por sí sola el cambio. Use el
botón **Recargar archivo** o el refresco del navegador. La actualización en
vivo mediante servidor local queda para una fase posterior.

## Contenido actual del HTML

- título del proyecto/circuito;
- estado de cálculo;
- revisiones del modelo y visuales;
- resumen de buses, alimentadores y cargas;
- pérdidas totales si existe un flujo vigente;
- unifilar SVG embebido;
- pestaña de datos;
- botón **Imprimir / PDF**;
- botón **Descargar SVG**;
- botón **Recargar archivo**;
- snapshot JSON embebido como `application/json`.

## PDF

El botón **Imprimir / PDF** utiliza la impresión estándar del navegador. El CSS
de impresión oculta controles y deja el unifilar en una disposición adecuada
para `Guardar como PDF`.

No se añade todavía una librería PDF porque la prioridad de esta fase es fijar
el contrato de datos y la validez de resultados.

## Snapshot

El contrato inicial usa `schema_version = 1` y contiene tres bloques:

```text
schema_version
status
model
```

`status` contiene revisiones y estudios. `model` contiene buses, líneas,
transformadores, cargas, generadores y configuración visual.

Las futuras vistas de caída de tensión, flujo de potencia, cortocircuito y
contingencias deben construirse sobre este snapshot, sin consultar OpenDSS
desde JavaScript.

## Regla de seguridad técnica

El HTML es una vista. No debe:

- cambiar impedancias;
- abrir/cerrar elementos en OpenDSS;
- resolver estudios eléctricos;
- inferir cumplimiento normativo por sí mismo.

Esas acciones pertenecen al MCP y al motor OpenDSS.
