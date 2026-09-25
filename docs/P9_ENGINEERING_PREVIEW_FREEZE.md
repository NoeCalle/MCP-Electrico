# P9D — Freeze MCP Eléctrico 0.9 Engineering Preview

## Objetivo

Congelar una base reproducible y estable antes de incorporar el caso industrial SE-MIN-01.

P9D no añade nuevos cálculos, motores, normas, defaults ni automatismos. Solo fija el estado ya validado por P7/P8/P9 y sus fronteras de uso.

## Baseline de entrada

- P7D: Engineering Preview habilitado.
- P8F: cadena de uso real controlado cerrada.
- P9A: portabilidad Windows/Python 3.12 con P7B sobre `dss.NewContext()`.
- P9C: tres ejecuciones consecutivas por una sola sesión MCP stdio, con integridad independiente, salidas collision-safe y cierre limpio.
- CI general y lanes P4/P7/P8/P9 verdes en los PR de hardening.

## Identidad congelada

```text
product_release       = MCP_ELECTRICO_0_9_ENGINEERING_PREVIEW
phase                 = P9D_FREEZE
allowed_use           = CONTROLLED_REAL_PROJECT_ENGINEERING_PREVIEW
professional_report   = false
professional_emission = false
automatic_defaults    = false
automatic_dispatch    = false
automatic_fault_binding = false
crosscheck            = false
p6_ieee1584           = DEFERRED
```

## Contratos que no deben cambiar durante el freeze

1. OpenDSS sigue siendo el motor principal del modelo.
2. P7B del dossier usa un contexto OpenDSS independiente, no un subprocess Python.
3. El contexto DSS activo y Workspace del servidor padre no se mutan durante P7B aislado.
4. IEC 60909 permanece limitado al alcance ya declarado y sin claim de conformidad total.
5. P5 conserva binding de falla explícito; no existe selección automática.
6. El dossier solo alcanza `DOSSIER_READY_ENGINEERING_PREVIEW` con integridad verificada.
7. Las entregas repetidas no sobrescriben silenciosamente dossiers anteriores.
8. Workspace V5 sigue siendo una vista del estado calculado, no una fuente de recálculo.
9. No se habilita emisión profesional.
10. P6 IEEE 1584 permanece diferido.

## Gate P9D

**Estado: CLOSED.** El freeze fue integrado mediante PR #109.

P9D se considera cerrado cuando:

- `main` incluye PR #106 y PR #107;
- todas las suites asociadas al head de PR #107 están verdes;
- la documentación de roadmap refleja P8 cerrado y P9D como freeze;
- no se introducen cambios de cálculo junto con el freeze;
- el siguiente trabajo funcional se abre como P10 / SE-MIN-01;
- PR #109 queda mergeado en `main` sin cambios de cálculo.

## Baseline de CI observada

En el head de PR #107 quedaron verdes, entre otras, las lanes:

- `tests`;
- `p8f4-windows-portability`;
- `p9c-stdio-repeatability`;
- `p8f4-first-use-operational`;
- `p8f5-final-real-use-gate`;
- `p8e2-real-project-dossier`;
- `p7d-engineering-preview`;
- `p4c11-workspace-v4`.

## Salida

```text
P9D = FROZEN
engineering_preview_0_9 = BASELINE_LOCKED
next_phase = P10_SE_MIN_01
```

La primera actividad de P10 será incorporar el proyecto minero de forma incremental, empezando por la arquitectura 22.9/4.16/0.48 kV y sus datos trazables, sin reabrir P9 salvo que aparezca una regresión real de plataforma.
