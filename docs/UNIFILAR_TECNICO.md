# Unifilar técnico — reglas visuales v1

El objetivo de esta capa no es producir todavía un plano CAD contractual, sino
un **diagrama unifilar reconocible como tal**, evitando la apariencia de grafo
o esquema genérico.

## Reglas de representación

1. El flujo principal de energía se lee de arriba hacia abajo.
2. Cada bus se representa como una barra horizontal claramente visible.
3. Cada alimentador sale de la barra mediante una única línea vertical.
4. Todo alimentador tiene un interruptor en cabecera.
5. Las derivaciones son ortogonales; no se usan aristas diagonales de grafo.
6. Los símbolos mantienen tamaño y orientación consistentes.
7. El nombre del bus, tensión nominal y estado pu se muestran junto a la barra.
8. Los alimentadores usan identificadores `F-01`, `F-02`, etc., salvo que el
   usuario configure una etiqueta explícita.
9. Un elemento abierto se representa en rojo y con interruptor abierto.
10. Una barra sin camino eléctrico hacia la fuente se representa desenergizada.

## Biblioteca de símbolos v1

- fuente / red;
- interruptor;
- transformador;
- barra;
- tablero;
- motor;
- carga genérica;
- ATS;
- UPS;
- grupo electrógeno;
- tierra.

La biblioteca vive en `mcp_electrico/visual_symbols.py` y utiliza SVG puro para
mantener la salida vectorial y evitar una dependencia gráfica adicional.

## ATS y UPS

En esta versión ATS y UPS son **anotaciones de representación** sobre un
alimentador. Esto permite que el unifilar sea legible y técnicamente familiar
sin afirmar que OpenDSS está modelando todavía el comportamiento interno de una
UPS o de un sistema de transferencia.

Por tanto:

- la anotación ATS/UPS no cambia impedancias ni resultados de flujo;
- una fuente alterna puede asociarse visualmente a un ATS usando un `Generator`
  existente;
- el resultado debe interpretarse como documentación visual del modelo y sus
  metadatos, no como un modelo detallado de la electrónica de potencia.

## Salida

`generar_diagrama_unifilar()` genera SVG vectorial. Si se solicita una ruta
`.html`, también crea un archivo `.svg` compañero y embebe el mismo SVG en un
wrapper HTML.
