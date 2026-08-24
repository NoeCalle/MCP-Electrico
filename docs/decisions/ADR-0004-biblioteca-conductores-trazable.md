# ADR-0004 — Biblioteca trazable de conductores BT y MT

- Estado: Aceptado
- Fecha: 2026-08-23
- Alcance: PR #7

## Contexto

MCP Eléctrico ya calcula flujo de potencia, caída de tensión y cargabilidad relativa cuando existe una corriente nominal explícita. Hasta ahora, conductor y ampacidad podían introducirse como metadatos manuales. Ese esquema sirve para prototipado, pero no es suficiente para una herramienta de ingeniería porque no responde de forma reproducible a preguntas como: ¿de dónde salió R?, ¿de dónde salió X?, ¿bajo qué método de instalación vale esta ampacidad? o ¿qué producto comercial representa el alimentador?

## Decisión 1 — Catálogo y asignación son objetos distintos

Un `CableType` describe un producto publicado por fabricante: familia, tensión, material, sección, pantalla, parámetros eléctricos, ampacidades, normas y fuente.

Una asignación describe cómo se usa ese producto en el circuito: `Line.*`, método de instalación/formación y valores que efectivamente se aplicaron a OpenDSS.

No se mezclan ambos conceptos para evitar que una propiedad de instalación se convierta accidentalmente en propiedad universal del cable.

## Decisión 2 — Ningún dato faltante se inventa

Los campos no publicados se almacenan como `null`. En particular, la primera biblioteca BT N2XOH dispone de Rdc20 y ampacidades verificadas, pero no de una X60 de fabricante para las fichas cargadas. Por ello, asignar esos productos BT:

- actualiza `NormAmps`;
- actualiza la ficha visual;
- **no reemplaza R1/X1** si falta un par R/X trazable.

El resultado devuelve `impedancia_actualizada=false` y explica la razón.

## Decisión 3 — MT puede actualizar directamente R1/X1 cuando la ficha lo publica

Para N2XSY 18/30 (36) kV de Nexans Perú, las fichas verificadas publican resistencia CA a 90 °C y reactancia inductiva a 60 Hz para formación plana y triangular. Esos pares se consideran adecuados para alimentar `R1` y `X1` de la representación positiva simplificada de `Line` en esta fase.

No se afirma que esto equivalga a un modelo completo de secuencia cero, pantalla o geometría multicondutor.

## Decisión 4 — La ampacidad siempre lleva condiciones

Una ampacidad no se guarda como propiedad aislada. Cada valor incluye una clave de instalación y, cuando la fuente lo publica, temperatura ambiente/terreno, formación, profundidad, resistividad térmica de terreno y condición de puesta a tierra de pantallas.

El catálogo inicial MT sigue las condiciones publicadas por Nexans basadas en NTP-IEC 60502-2 Anexo B: conductor 90 °C, aire 30 °C, terreno 20 °C, profundidad 0.8 m, resistividad térmica 1.5 K·m/W y pantallas a tierra en ambos extremos para los casos enterrados.

## Decisión 5 — Fuente y confianza forman parte del dato

Cada producto almacena:

- `source.type`;
- `source.url`;
- `source.accessed_at`;
- `source.confidence`.

La biblioteca inicial usa únicamente fichas de Nexans Perú / INDECO by Nexans y marca esos registros como `HIGH` porque los valores provienen directamente del fabricante.

## Decisión 6 — La primera biblioteca es deliberadamente pequeña

El catálogo v1 no intenta cubrir todas las marcas ni secciones del mercado peruano. Incluye:

### BT — N2XOH 0.6/1 kV Cu XLPE

- 50 mm²
- 70 mm²
- 95 mm²

### MT — N2XSY 18/30 (36) kV Cu XLPE-TR

- 70 mm² PH16
- 95 mm² PH16
- 120 mm² PH12
- 150 mm² PH12
- 185 mm² PH12
- 240 mm² PH12

Se prioriza calidad y trazabilidad sobre volumen.

## Decisión 7 — OpenDSS sigue siendo el motor, no la biblioteca

La biblioteca únicamente suministra datos de entrada y registra procedencia. El flujo eléctrico continúa siendo resuelto por OpenDSS.

Al aplicar un conductor:

1. se valida el `Line.*`;
2. se valida producto e instalación;
3. se actualiza `NormAmps`;
4. si existe Rca90 + X60 para la formación, se actualizan `R1` y `X1`;
5. se preservan etiqueta/protección visual existentes;
6. el servidor incrementa la revisión del modelo e invalida estudios previos.

## Decisión 8 — Alcance eléctrico explícito

En esta fase no se modelan todavía:

- R0/X0;
- corrientes de pantalla en el flujo normal;
- pérdidas por pantalla calculadas explícitamente;
- single-point bonding, cross-bonding o sheath voltage limiters;
- geometría `LineGeometry` / `CNData` / `TSData`;
- factores de corrección por agrupamiento o temperatura distintos de los publicados;
- ampacidad calculada automáticamente para condiciones arbitrarias.

Estos datos pueden almacenarse progresivamente, pero no se simulan hasta que exista un método documentado y probado.

## Consecuencias

### Positivas

- trazabilidad auditable;
- evita parámetros inventados por el LLM;
- permite cambiar cables conversacionalmente;
- MT puede modificar realmente R/X y, por tanto, flujo y caída de tensión;
- la cargabilidad usa una ampacidad asociada a condiciones explícitas.

### Costos / limitaciones

- la biblioteca crecerá más lentamente;
- un producto BT puede quedar parcialmente aplicado hasta disponer de X/impedancia validada;
- todavía se requiere modelado adicional para estudios de secuencia cero y pantallas.

## Criterio para ampliar el catálogo

Un nuevo registro no debe incorporarse sin:

1. producto identificable;
2. fuente primaria o norma claramente citada;
3. condiciones de ampacidad explícitas;
4. distinguir dato publicado de dato derivado;
5. tests de consistencia del esquema.
