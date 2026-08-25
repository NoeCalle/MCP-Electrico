# P3C11B1 — Tabla 5B primaria completa

Se incorporó la Tabla 5B completa del CNE Utilización a partir de la fuente oficial pinneada.

Fuente: `MINEM_CNE_UTIL_2006_OFFICIAL_PDF`, SHA-256 `2b3cbd457c519bf9d9aa2cf2754c72b6e531708e45ea2fdf91f839b1acccfd64`.

Página: PDF 564, `Tablas - Pág. 17 de 82`. La Regla 030-004(9), en PDF 37 / Sección 030 pág. 2 de 11, remite el método D a Tabla 5B cuando la resistividad térmica del suelo difiere de 2,5 K·m/W.

| Resistividad K·m/W | Factor |
| ---: | ---: |
| 1.0 | 1.18 |
| 1.5 | 1.10 |
| 2.0 | 1.05 |
| 2.5 | 1.00 |
| 3.0 | 0.96 |

La revisión visual fue realizada como `AI_VISUAL_REVIEW_USER_AUTHORIZED`, con `human_reviewer=null`.

## Límites preservados

- método D;
- cables en ductos soterrados;
- no se extrapola a cable directamente apoyado en tierra;
- profundidad máxima: **0,8 m**;
- precisión indicada: **±5 %**;
- para mayor precisión la norma remite a IEC 60287.

El lookup exige `environment=buried_duct` y `burial_depth_scope=up_to_0_8_m`; no interpola resistividades.

La tabla tiene `p3c11_family_coverage=true`, pero `automatic_binding_to_iz=false`. P3C11B2 añadirá profundidad al routing P3A y binding contextual hacia `Iz`. P3C11 global continúa `PENDING` y P4 bloqueada.
