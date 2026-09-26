# MCP runtime y construcción Rev.0

## Problema que resuelve

Un agente que inspecciona el repositorio desde un entorno limpio puede encontrar
`server.py`, pero eso no significa que el runtime tenga instalados
`mcp`, `opendssdirect`, `networkx` y `pandapower`.

Además, las tools históricas de construcción fueron diseñadas cuando el
workspace era parte central de la interacción y pueden regenerar archivos o
resolver al abrir/cerrar elementos. Esa ruta no es ideal para construir una
revisión inicial del modelo de forma estrictamente declarativa.

Esta capa añade una ruta explícita para agentes y para uso manual.

## 1. Diagnóstico sin dependencias

```bash
python scripts/runtime_doctor.py
```

El doctor usa solo la biblioteca estándar. No instala nada y reporta:

- versión de Python;
- dependencias disponibles/faltantes;
- presencia de `pyproject.toml` y `server.py`;
- comando de instalación recomendado;
- comando de arranque recomendado.

Si el entorno prohíbe instalaciones, el resultado correcto es declarar
`runtime_ready=false`. El repositorio no intenta descargar paquetes de forma
silenciosa.

## 2. Instalación reproducible del proyecto

El repositorio es ahora un proyecto Python instalable:

```bash
python -m pip install -e .
```

Para desarrollo:

```bash
python -m pip install -e ".[dev]"
```

Después puede iniciarse con:

```bash
mcp-electrico
```

o de forma compatible:

```bash
python server.py
```

## 3. Ruta MCP recomendada para Rev.0

```text
obtener_contrato_construccion_rev0
            ↓
validar_construccion_rev0
            ↓
construir_modelo_rev0
            ↓
registrar_placeholder_modelo  (solo si hay TBC)
            ↓
auditar_modelo
            ↓
evaluar preparación del estudio
            ↓
ejecutar estudio explícito
```

`construir_modelo_rev0` delega al materializador determinista P8C3B ya
validado. Por contrato:

```text
solve_performed = false
workspace_file_written = false
automatic_defaults = false
automatic_dispatch = false
professional_emission = false
model_ready_for_study = false
```

Construir el modelo no equivale a aprobarlo para un estudio.

## 4. TBC / MODEL_PLACEHOLDER

Cuando un equipo todavía no tiene parámetros obligatorios, no se rellena con un
valor típico. Se registra de forma explícita:

```text
status = MODEL_PLACEHOLDER_TBC
solver_materialized = false
blocks_study_readiness = true
```

Ejemplos razonables:

- transformador auxiliar con %Z o grupo vectorial TBC;
- bus tie cuya representación eléctrica al cerrar aún no está definida;
- equipo futuro del SLD que debe aparecer en Rev.0 pero no participar en el solver.

`auditar_modelo` genera el blocker `QA050` mientras exista cualquier
placeholder.

## 5. Topología sin resolver

Las tools:

- `abrir_elemento_sin_resolver`;
- `cerrar_elemento_sin_resolver`;

cambian el estado del elemento y marcan el modelo como modificado, pero no
ejecutan `Solve` ni regeneran el archivo workspace.

Son adecuadas para preparar un tie inicialmente OPEN cuando el elemento ya
tiene una representación eléctrica explícita. Si la impedancia/modelo del tie
es TBC, debe usarse `MODEL_PLACEHOLDER` en lugar de inventar una conexión
ideal.

## 6. Barra de fuente

`crear_circuito` expone ahora `bus_fuente`. El default `sourcebus` se
mantiene únicamente por compatibilidad histórica; un flujo profesional debe
declarar la barra de fuente explícitamente.

## Frontera de esta mejora

Esta capa no convierte un entorno sin dependencias en un runtime OpenDSS
mágicamente autosuficiente. Para entornos donde no se permite instalar nada, la
solución futura correcta es un runtime MCP previamente instalado o remoto, no
auto-instalar paquetes desde `server.py`.
