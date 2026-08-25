# P3C11D2 — binding seguro Tabla 5D → Iz

P3C11D2 conecta la Tabla 5D primaria completa con el cálculo de `Iz` sin inferir la disposición física desde texto libre.

## Routing estructurado

Para método D con más de un circuito se incorporan dos campos explícitos:

- `table5d_branch`: `A`, `B`, `C` o su ID canónico;
- `grouping_spacing_id`: separación exacta tabulada.

`grouping_arrangement` libre se conserva por compatibilidad, pero **no se interpreta automáticamente** y mantiene el caso en revisión manual.

## Política de compatibilidad

Un factor Tabla 5D puede entrar a `Iz` solo si coinciden exactamente:

- perfil y referencia normativa;
- método D;
- `Iz_base` de Tabla 2;
- ambiente de la rama;
- rama A/B/C;
- separación;
- número de circuitos/cables;
- profundidad `0.7 m`;
- resistividad térmica `2.5 K·m/W`.

D2 no valida todavía la combinación automática de 5B y 5D para resistividades distintas de 2.5 K·m/W. Esa combinación permanece fail-closed.

## Cadena primaria de regresión

Caso B, cable multipolar en ducto de una vía, 3 circuitos, separación 0.25 m:

```text
Iz_base Tabla 2 col.25 = 178 A
k_grouping Tabla 5D-B = 0.85
Iz = 178 × 0.85 = 151.30 A
```

## V3

V3 sigue siendo read-only y muestra datos ya calculados/revalidados por Python:

- Tabla 5D;
- rama A/B/C;
- número de circuitos;
- separación;
- ρ;
- profundidad;
- dataset primario.

El navegador no realiza lookup ni recalcula `Iz`.
