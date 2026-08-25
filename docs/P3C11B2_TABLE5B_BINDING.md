# P3C11B2 — Binding seguro Tabla 5B → Iz

## Resultado

P3C11B1 incorporó la Tabla 5B completa como evidencia primaria. B2 conecta esa familia al cálculo P3 sin relajar sus límites normativos.

La profundidad de enterramiento pasa a ser un dato explícito del routing P3A para método D cuando la resistividad del suelo difiere de 2,5 K·m/W.

## Iz_base primaria D

La fuente oficial pinneada confirma:

```text
Tabla 2
Método D
Cu
XLPE/EPR 90 °C
3 conductores cargados
70 mm²
Columna 25
Iz_base = 178 A
```

Tabla 3 confirma D + XLPE/EPR + 3 conductores → Tabla 2 Col. 25.

## Cadena real

Para ducto enterrado a 0,8 m y rho = 3 K·m/W:

```text
Iz_base = 178 A       Tabla 2 Col.25 PRIMARY_VERIFIED
k_rho   = 0.96        Tabla 5B PRIMARY_VERIFIED
Iz      = 170.88 A
```

El resultado se calcula en Python; no se almacena como valor normativo independiente.

## Fail-closed

Tabla 5B solo entra a Iz cuando coinciden exactamente:

- referencia normativa y perfil;
- método D;
- `environment=buried_duct`;
- `Iz_base` de Tabla 2;
- resistividad declarada y fila exacta de 5B;
- profundidad positiva y <= 0,8 m;
- `burial_depth_scope=up_to_0_8_m`.

Profundidad >0,8 m, ausencia de profundidad, `direct_buried` o resistividad no tabulada no se extrapolan.

## V3

La vista continúa sin calcular ingeniería. Para factores 5B muestra desde Python el `k`, la resistividad y el alcance de profundidad junto con Tabla/dataset.

## Roadmap

La familia 5B queda **cubierta y vinculada**. P3C11 continúa PENDING por 5A/5C parciales y 5D/5E pendientes. P4 sigue bloqueada.
