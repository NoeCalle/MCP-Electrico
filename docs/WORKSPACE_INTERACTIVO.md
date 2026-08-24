# Workspace interactivo — inspector técnico

Esta fase extiende el workspace persistente con selección e inspección local.
No cambia la arquitectura de control: ChatGPT sigue siendo el canal para
modificar el circuito.

## Qué puede hacer

El workspace permite seleccionar:

- barras y buses;
- alimentadores;
- transformadores;
- cargas;
- generadores.

La selección puede hacerse desde el unifilar, desde la tabla Datos o desde el
selector del panel lateral.

## Qué muestra

### Alimentador

- referencia MCP;
- nombre OpenDSS;
- origen y destino;
- longitud;
- R1 y X1;
- conductor documentado;
- protección documentada;
- estado abierto/cerrado.

### Transformador

- referencia MCP;
- buses;
- kVA;
- relación de tensión;
- conexión;
- estado.

### Carga

- referencia MCP;
- bus;
- tipo visual;
- kW;
- kvar;
- criticidad.

### Bus

Cuando existe un flujo vigente:

- tensión base LN;
- tensiones pu por fase;
- indicador de que el resultado corresponde a la revisión actual.

### Generador

- referencia MCP;
- bus;
- kW;
- kV.

## Referencia conversacional

El panel muestra siempre un identificador inequívoco, por ejemplo:

`Line.f_motor`

Esto permite decir en ChatGPT:

> Cambia F-01 (`Line.f_motor`) a un cable de 95 mm².

El rótulo humano puede cambiar sin perder la identidad del elemento.

## Importante: el HTML no edita el circuito

El inspector es deliberadamente read-only. No existen formularios que
modifiquen OpenDSS desde JavaScript.

Flujo de modificación:

1. usuario pide el cambio en ChatGPT;
2. ChatGPT llama la tool MCP;
3. MCP modifica OpenDSS;
4. se incrementa la revisión;
5. se regenera el workspace;
6. el usuario recarga el archivo si ya estaba abierto.

## Enlace con el SVG

El workspace usa el catálogo estable del snapshot y enlaza las etiquetas
visibles del SVG con esos IDs. Cuando existe un rótulo explícito como `F-01`,
la etiqueta y el símbolo asociado se vuelven seleccionables.

Si un elemento no tiene una etiqueta visual inequívoca, el selector y la tabla
siguen funcionando como rutas deterministas.

## Exportación

El comportamiento previo se conserva:

- `Imprimir / PDF` usa `window.print()`;
- `Descargar SVG` serializa el SVG actual;
- el panel interactivo se oculta al imprimir.

## Próxima fase

La siguiente evolución natural es reutilizar estos mismos IDs para overlays de
estudio:

- tensión por bus;
- caída porcentual por alimentador;
- corriente y cargabilidad;
- pérdidas;
- cortocircuito.

No debe crearse un segundo sistema de identidad para los resultados.
