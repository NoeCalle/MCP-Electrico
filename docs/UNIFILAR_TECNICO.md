# Unifilar técnico — reglas visuales v2

El objetivo de esta capa es producir un **diagrama unifilar reconocible como
ingeniería eléctrica**, no un grafo de la topología OpenDSS. Todavía no es un
plano CAD contractual, pero el renderer interpreta el modelo antes de dibujarlo.

## Principio central

**Un bus de OpenDSS no equivale necesariamente a una barra física.**

La versión v2 distingue:

- **barra física**: TGBT, MCC, tablero seccional u otra barra que deba aparecer
  explícitamente;
- **conexión lógica**: bus interno necesario para el cálculo que puede omitirse
  como barra del dibujo.

En modo `auto`, el renderer conserva como barra la cabecera, salidas de
transformador y puntos reales de distribución. Un bus terminal con una única
carga suele colapsarse y el alimentador termina directamente en el equipo.

El usuario puede forzar el criterio:

```python
configurar_bus_unifilar("mcc_01", rol="barra", etiqueta="MCC-01")
configurar_bus_unifilar("nodo_aux", rol="conexion")
```

## Reglas visuales v2

1. Flujo jerárquico de la fuente hacia las cargas.
2. Barra principal con mayor espesor que barras secundarias.
3. Conductores y auxiliares con menor peso gráfico que las barras.
4. Alimentadores ortogonales y espaciado regular.
5. Protección dibujada en la cabecera del alimentador.
6. No se inventa una protección nueva al atravesar un bus lógico intermedio.
7. Un bus terminal con una sola carga se representa como conexión, no como otra
   barra más un circuito ficticio.
8. ATS de doble fuente muestra entrada normal y grupo electrógeno lateral.
9. Etiquetas de ingeniería se separan de los nombres internos OpenDSS.
10. Solo se muestran datos técnicos selectivos para conservar legibilidad.

## Simbología

La biblioteca `mcp_electrico/visual_symbols.py` incluye:

- fuente / red;
- interruptor genérico;
- MCCB;
- ACB;
- fusible;
- seccionador;
- transformador;
- barra;
- tablero;
- motor;
- carga genérica;
- ATS;
- UPS;
- grupo electrógeno;
- tierra.

MCCB y ACB comparten el símbolo de contacto y se distinguen mediante su sigla,
una convención habitual en diagramas unifilares.

## Etiquetado técnico

Puede definirse un nombre de presentación sin cambiar el elemento OpenDSS:

```python
configurar_etiqueta_carga_unifilar(
    "motor_bomba",
    "M-01 · BOMBA AGUA",
)
```

Para un alimentador:

```python
configurar_alimentador_unifilar(
    "Line.f_motor",
    etiqueta="F-01",
    proteccion="mccb",
    conductor="3×70 mm² Cu",
    corriente_nominal_a=160,
    capacidad_ruptura_ka=25,
)
```

El dibujo puede mostrar, por ejemplo:

```text
F-01
MCCB 160 A · 25 kA
3×70 mm² Cu
```

Estos campos son **metadatos gráficos**; no alteran los parámetros eléctricos
de OpenDSS.

## Modos de salida

### Ingeniería

Es el modo por defecto:

```python
generar_diagrama_unifilar(
    "unifilar.svg",
    modo="ingenieria",
)
```

Prioriza:

- rótulos técnicos;
- tensión nominal;
- simbología;
- legibilidad.

No muestra nombres internos de OpenDSS ni valores pu salvo que sean necesarios
para indicar una condición anormal.

### Diagnóstico

```python
generar_diagrama_unifilar(
    "diagnostico.svg",
    modo="diagnostico",
)
```

Añade:

- nombres internos de líneas;
- tensión pu;
- información útil para depurar el modelo.

## Leyenda, reglas y branding

El modo de producción es limpio:

```python
mostrar_leyenda=False
mostrar_marca=False
mostrar_reglas=False
```

Para una lámina de demostración pueden activarse explícitamente:

```python
generar_diagrama_unifilar(
    "demo.svg",
    mostrar_leyenda=True,
    mostrar_reglas=True,
    mostrar_marca=True,
)
```

## Orientación

Se admiten:

```python
orientacion="vertical"
orientacion="horizontal"
```

La vertical sigue siendo la referencia principal para edificios, hospitales y
redes con muchas derivaciones. La horizontal permite leer redes profundas de
izquierda a derecha.

## ATS y UPS

ATS y UPS siguen siendo **anotaciones de representación** sobre un alimentador.
Una fuente alterna puede asociarse a un ATS usando un `Generator` existente.

Esto no significa que OpenDSS esté modelando el comportamiento interno de una
UPS, la lógica de transferencia o sus límites electrónicos. La capa visual no
modifica el cálculo.

## Salida

`generar_diagrama_unifilar()` genera SVG vectorial. Si se solicita `.html`,
también genera el SVG compañero y lo embebe en un wrapper HTML.

La salida declara:

- barras físicas dibujadas;
- buses lógicos que no se mostraron como barra;
- modo;
- orientación;
- buses desenergizados;
- cantidad de cargas, generadores y transformadores.
