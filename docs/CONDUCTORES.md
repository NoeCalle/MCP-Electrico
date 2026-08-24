# Biblioteca de conductores BT/MT

La biblioteca permite seleccionar productos comerciales trazables y aplicarlos a alimentadores `Line.*` sin que ChatGPT invente R, X o ampacidades.

## Tools MCP

### `listar_conductores(nivel=None, familia=None)`

Ejemplos conceptuales:

```text
listar conductores MT
listar N2XSY disponibles
```

Devuelve código estable, nivel, familia, sección, instalaciones disponibles y fuente.

### `obtener_conductor(codigo)`

Devuelve la ficha completa, incluyendo:

- fabricante y referencia;
- tensión Uo/U (Um);
- material y aislamiento;
- sección de conductor;
- pantalla cuando aplica;
- Rdc20;
- Rca90 y X60 cuando están publicados;
- ampacidades por instalación;
- condiciones de cálculo;
- normas;
- URL y fecha de consulta.

### `aplicar_conductor(nombre_elemento, codigo, instalacion, actualizar_impedancia=True)`

Asigna el producto a un `Line.*`.

Ejemplo MT:

```text
aplicar conductor NEXANS-N2XSY-18-30-CU-95-PH16 a Line.f_mt
instalación air_trefoil_30c
```

Para este producto el fabricante publica Rca90 y X60 en trébol, por lo que el MCP puede actualizar:

```text
Line.R1
Line.X1
Line.NormAmps
```

El workspace queda `MODIFIED`; los resultados anteriores dejan de ser vigentes hasta volver a ejecutar el flujo.

Ejemplo BT:

```text
aplicar NEXANS-N2XOH-0.6-1-CU-70 a Line.f_motor
instalación air_flat_30c
```

La ficha v1 dispone de Rdc20 y ampacidad, pero no de un par Rca90/X60 verificado. Por ello:

- `NormAmps` sí se actualiza;
- el rótulo y la ficha visual sí se actualizan;
- R1/X1 anteriores se conservan;
- el resultado informa `impedancia_actualizada=false`.

Esta conducta es intencional.

## Instalaciones disponibles

### N2XOH BT

- `air_flat_30c`
- `air_trefoil_30c`
- `buried_duct_20c`

### N2XSY MT

- `air_flat_30c`
- `air_trefoil_30c`
- `buried_flat_20c`
- `buried_trefoil_20c`

No se acepta una instalación no publicada en el registro del producto.

## Catálogo inicial

### Baja tensión

| Código | Producto | Sección |
|---|---|---:|
| `NEXANS-N2XOH-0.6-1-CU-50` | N2XOH 0.6/1 kV Cu XLPE | 50 mm² |
| `NEXANS-N2XOH-0.6-1-CU-70` | N2XOH 0.6/1 kV Cu XLPE | 70 mm² |
| `NEXANS-N2XOH-0.6-1-CU-95` | N2XOH 0.6/1 kV Cu XLPE | 95 mm² |

### Media tensión

| Código | Producto | Sección | Pantalla |
|---|---|---:|---:|
| `NEXANS-N2XSY-18-30-CU-70-PH16` | N2XSY 18/30 (36) kV | 70 mm² | 16 mm² |
| `NEXANS-N2XSY-18-30-CU-95-PH16` | N2XSY 18/30 (36) kV | 95 mm² | 16 mm² |
| `NEXANS-N2XSY-18-30-CU-120-PH12` | N2XSY 18/30 (36) kV | 120 mm² | 12 mm² |
| `NEXANS-N2XSY-18-30-CU-150-PH12` | N2XSY 18/30 (36) kV | 150 mm² | 12 mm² |
| `NEXANS-N2XSY-18-30-CU-185-PH12` | N2XSY 18/30 (36) kV | 185 mm² | 12 mm² |
| `NEXANS-N2XSY-18-30-CU-240-PH12` | N2XSY 18/30 (36) kV | 240 mm² | 12 mm² |

## Fuentes

La versión inicial usa fichas técnicas actuales de Nexans Perú / INDECO by Nexans. Cada registro guarda la URL concreta del producto y la fecha de consulta. Los productos MT declaran cumplimiento con NTP-IEC 60228 y NTP-IEC 60502-2, y el fabricante publica condiciones de cálculo de ampacidad basadas en NTP-IEC 60502-2 Anexo B.

La biblioteca está en:

```text
mcp_electrico/data/conductors_nexans_peru_v1.json
```

## Regla de seguridad técnica

`null` significa **dato no disponible en la fuente cargada**. No significa cero y no autoriza a sustituirlo por un valor típico.

Cuando falta un parámetro imprescindible para modificar la impedancia de OpenDSS, el MCP conserva la impedancia previa y lo informa de forma explícita.

## Próximos pasos previstos

- ampliar secciones BT;
- incorporar N2XY y familias MT adicionales;
- incorporar aluminio;
- calcular/validar geometrías para obtener matrices y secuencia cero;
- modelar pantallas y sus esquemas de puesta a tierra;
- añadir factores de corrección normativos para condiciones distintas de catálogo;
- mostrar fuente e instalación de conductor directamente en el inspector HTML.
