# P11 — Release safety y protección del core

## Objetivo

P11 comienza después del cierre integral de P10. No añade una nueva función eléctrica: protege una versión conocida del producto y reduce el riesgo de que una refactorización futura rompa silenciosamente contratos, políticas fail-closed o la ruta reproducible.

P11 parte de dos puntos de recuperación:

```text
P9 freeze:
stable/0.9-engineering-preview
6720da9183c45df299a584430fddea28f4060d7a

P10 validated:
stable/0.9-reference-validated
5228e358cf0716dc963f109a15b9e1a2d309f635
```

## Estrategia

| Subfase | Alcance | Gate |
| --- | --- | --- |
| P11A | release manifest + recovery anchors | SHA y políticas críticas registradas |
| P11B | core contract regression | cambios incompatibles rompen CI de forma explícita |
| P11C | export/mirror independiente | copia estable fuera del repo de desarrollo |
| P11D | stable release candidate | restauración probada desde release limpia |

## P11A — Release manifest

**Estado: IN PROGRESS.**

P11A incorpora `releases/mcp_electrico_0_9_reference_validated.json` como registro canónico del punto conocido-bueno después de P10.

El manifiesto fija:

- SHA exacto del cierre P10G;
- rama de recuperación;
- baseline P9 anterior;
- PRs P10 que forman la validación integral;
- políticas críticas que deben permanecer `false`;
- P6 IEEE 1584 aún diferido;
- estado del mirror independiente.

### Criterios de cierre P11A

- existe una rama estable apuntando exactamente al merge de P10G;
- el release manifest declara ese SHA, sin usar `main` como referencia ambigua;
- CI verifica el formato y los invariantes de seguridad;
- el contrato P8B sigue fail-closed;
- los scopes públicos de la Engineering Preview no cambian accidentalmente;
- una modificación deliberada de esos contratos requiere actualizar explícitamente el release contract;
- `professional_emission=false`.

## Principio

```text
Git history != release recovery policy
```

Git conserva historia, pero P11 define qué commits están aprobados como puntos de recuperación. Un commit nuevo en `main` no reemplaza automáticamente un punto estable.

## Mirror independiente

El repo espejo sigue planificado para P11C. Debe ser un repositorio separado del desarrollo normal y recibir únicamente snapshots estables. No debe contener secretos, credenciales ni dossiers privados.
