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
| P11D | clean restore proof | restauración probada desde release limpia |

## P11A — Release manifest

**Estado: DONE.** PR #118.

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


## P11B — Contrato público del core

**Estado: DONE.** PR #119.

P11B no congela todas las tools internas del repositorio. Congela únicamente la superficie operativa recomendada para el primer uso controlado:

```text
evaluar_admision_piloto_real(manifest)
        ↓
generar_dossier_piloto_real(manifest, directorio_salida=...)
        ↓
verificar_integridad_dossier_real(ruta_indice)
```

El contrato versionado vive en `contracts/public_first_use_v1.json`.

### Qué protege

- nombre de las tres tools públicas;
- parámetros requeridos;
- default público de `directorio_salida`;
- orden operativo recomendado;
- estados de éxito;
- SHA-256 y conjunto exacto de archivos del dossier;
- política de no sobrescritura;
- invariantes fail-closed.

Un cambio incompatible exige una nueva versión contractual en vez de modificar silenciosamente V1.

### Qué no congela

Las tools de desarrollo de bajo nivel, helpers internos y detalles de implementación pueden evolucionar mientras preserven el contrato público o declaren una versión nueva.

### Criterios de cierre P11B

- el contrato JSON V1 coincide con las firmas MCP reales;
- las tres funciones continúan expuestas mediante `mcp.tool`;
- P8F4 conserva la misma secuencia pública;
- P8F2 conserva SHA-256, rutas relativas y file-set exacto;
- P8F3 conserva suffix increment y prohíbe overwrite;
- Linux/Python 3.11 y Windows/Python 3.12 pasan CI;
- `professional_emission=false`.


## P11C — Export portable para mirror independiente

**Estado: DONE.** PR #120.

P11C prepara un paquete verificable de la baseline `MCP_ELECTRICO_0_9_REFERENCE_VALIDATED` sin confundir un artifact de CI con un backup externo definitivo.

La herramienta `scripts/create_release_export.py` exige simultáneamente:

```text
ref resuelto
    =
expected_sha
    =
release_manifest.commit_sha
```

Si los tres valores no coinciden, el export falla antes de producir una entrega.

### Contenido del export

```text
source ZIP from exact Git commit
Git bundle
release_manifest.json
export_metadata.json
SHA256SUMS.txt
```

El ZIP se genera con `git archive`, por lo que no consume el working tree ni archivos locales no trackeados. El bundle permite reconstruir la historia alcanzable hasta el commit estable incluso sin acceso a GitHub.

### Frontera del mirror

```text
CI artifact = export staging
independent repository = final external backup
```

P11C no afirma que el mirror independiente ya exista. La creación del repositorio externo permanece como una acción separada; el procedimiento queda documentado en `docs/RELEASE_MIRROR_RUNBOOK.md`.

### Criterios de cierre P11C

- el export solo acepta el SHA estable exacto;
- el manifest debe apuntar al mismo SHA;
- el source ZIP no incorpora el working tree;
- `git bundle verify` debe pasar;
- los archivos de entrega quedan cubiertos por SHA-256;
- el paquete se prueba en Linux/Python 3.11 y Windows/Python 3.12;
- CI publica un artifact de staging con retención finita, sin llamarlo mirror;
- secretos y dossiers privados quedan fuera por diseño;
- `professional_emission=false`.

Al cerrar P11C, P11D reconstruirá una copia limpia únicamente desde el bundle y volverá a ejecutar un smoke operacional sobre esa restauración.


## P11D — Restauración limpia desde bundle

**Estado: DONE.** PR #121.

P11D prueba la recuperación sin depender de `main`, del working tree original ni de GitHub como fuente del código restaurado.

La secuencia es:

```text
P11C export
   ↓
verificar SHA-256
   ↓
git init vacío
   ↓
git bundle verify
   ↓
fetch desde bundle
   ↓
checkout main restaurado
   ↓
HEAD == SHA estable P10G
   ↓
working tree limpio
   ↓
sin remotes
   ↓
smoke P10G dossier
```

La restauración debe volver exactamente a:

```text
5228e358cf0716dc963f109a15b9e1a2d309f635
```

### Criterios de cierre P11D

- el checksum del export se verifica antes de restaurar;
- un export alterado es rechazado antes de crear la copia restaurada;
- `git bundle verify` pasa;
- el checkout restaurado coincide exactamente con el SHA estable;
- la copia restaurada no contiene remotes;
- el working tree queda limpio;
- las dependencias declaradas por la release restaurada se pueden instalar;
- el test integral P10G genera nuevamente Workspace V5 + dossier reproducible;
- la prueba pasa en Linux/Python 3.11 y Windows/Python 3.12;
- el mirror externo continúa separado de la copia de recuperación;
- `professional_emission=false`.

P11D quedó cerrado con restauración limpia y smoke integral sobre la copia recuperada.

## Estado de salida P11

```text
P11A = DONE
P11B = DONE
P11C = DONE
P11D = DONE
internal_release_safety = READY
independent_external_mirror = DEFERRED_BY_PROJECT_DECISION
professional_emission = false
```

La implementación interna de Release Safety queda cerrada. El único paso pendiente es operacional: crear el repositorio espejo independiente y cargar allí el export verificado siguiendo `docs/RELEASE_MIRROR_RUNBOOK.md`.

Ese mirror no modifica el core, no es una nueva fase de ingeniería y no debe bloquear el desarrollo técnico posterior.


## Current repository-only decision

The active recovery strategy remains in this repository:

```text
main = active development
stable/0.9-engineering-preview = frozen P9 recovery point
stable/0.9-reference-validated = validated P10 recovery point
exact commit SHAs = canonical recovery anchors
external mirror = deferred
```

Stable recovery branches are not feature branches and must never move implicitly with `main`.
