# P8F4 — Primer uso operacional por MCP

P8F4 define la ruta recomendada para empezar a usar MCP Eléctrico 0.9 Engineering Preview con un paquete de datos de proyecto, sin llamar módulos Python internos.

> `examples/p8_first_use_manifest.json` es una **plantilla ejecutable de demostración**. Sus valores y referencias `EJEMPLO P8F4` no son evidencia de un proyecto real y deben reemplazarse antes de usarla con fines de ingeniería.

P6 IEEE 1584 permanece `DEFERRED` y no forma parte de esta ruta.

## 1. Prerrequisitos

Desde la raíz del repositorio:

```bash
python -m venv venv
```

Windows:

```powershell
venv\Scripts\activate
pip install -r requirements.txt
```

Linux/macOS:

```bash
source venv/bin/activate
pip install -r requirements.txt
```

Antes del piloto real sigue siendo recomendable completar la línea base descrita en `QUICKSTART.md`.

## 2. Smoke completo por el servidor MCP

El ejemplo P8F4 levanta `server.py` por stdio mediante el SDK MCP y llama exclusivamente tools públicas:

```bash
python examples/p8_first_use_mcp.py \
  --manifest examples/p8_first_use_manifest.json \
  --output-dir salida_p8_first_use/dossier
```

El cliente no importa `mcp_electrico`, OpenDSS, pandapower, P8D2 ni P8E2. La ingeniería ocurre detrás del servidor MCP ya registrado.

La secuencia pública es:

```text
evaluar_admision_piloto_real
        ↓
generar_dossier_piloto_real
        ↓
verificar_integridad_dossier_real
```

La tool `obtener_contrato_p8f4_primer_uso()` expone esta misma secuencia y sus estados de reparación.

### Aislamiento interno de P7B

La verificación de reconstrucción P7B usada por el dossier se ejecuta en un contexto OpenDSS independiente creado mediante `dss.NewContext()`. No se lanza un segundo proceso Python. El round-trip DSS sigue siendo canónico archivo por archivo, pero el circuito y el estado estructurado activos del servidor MCP permanecen en el contexto padre.

Esta separación es parte del contrato de portabilidad de P8F4 y se comprueba en CI tanto en la ruta Linux existente como en una lane Windows/Python 3.12. No habilita ejecución paralela automática ni cambia `automatic_dispatch=false` o `crosscheck=false`.

## 3. Resultado esperado

Una ejecución sana del smoke devuelve:

```text
ok = true
stage = COMPLETE
tool_transport = MCP_STDIO_SERVER_PY
intake_status = READY_TO_BUILD_MODEL
execution_status = DOSSIER_READY_ENGINEERING_PREVIEW
integrity_status = DOSSIER_INTEGRITY_VERIFIED
professional_emission = false
```

El resumen JSON queda, por defecto, como archivo hermano del directorio solicitado. No se escribe dentro del dossier para no alterar el conjunto congelado por P8F2.

El dossier contiene, entre otros:

```text
manifest.json
execution_p8d2.json
workspace_v5.html
project_snapshot_p7a.json
reconstruction_p7b.json
project_report_p7c.html
dossier_integrity.json
p7a_netlist/
p7b_reconstructed/
```

## 4. Qué sustituir para un proyecto real

No basta con cambiar `project.name`. Cada magnitud que interviene en ingeniería debe corresponder al expediente y conservar una procedencia identificable.

Revisar como mínimo:

- `project`: ID, nombre y referencia del expediente;
- `source`: tensión, Scc MAX/MIN, X/R y referencia de utility/estudio;
- `topology`: buses, transformadores, líneas/cables y cargas;
- `zero_sequence`: datos Z0 de fuente, líneas y transformadores cuando se solicita 1F-T;
- `ampacity`: conductor, ampacidad base, Ib, In, condiciones/factores y referencias;
- `protection.devices`: tipo, In, Ue y ratings con ficha/procedencia;
- `protection.tcc_datasets`: dataset numérico, semántica de tiempo y referencia;
- `protection.fault_bindings`: barra, tipo de falla, caso MAX/MIN, magnitud y tensión explícitas;
- `study_inputs`: buses de cortocircuito y criterios configurables declarados.

No se deben conservar textos `EJEMPLO P8F4` en un manifiesto presentado como datos de proyecto.

### Nota sobre breakers

Para `circuit_breaker`, P5 usa **Icu** para el chequeo de capacidad de corte. Ics e Icw permanecen separados. El campo genérico `breaking_capacity_ka` que aún exige la admisión histórica P8B solo puede actuar como alias legacy explícito igual a Icu; no reemplaza la semántica Icu en la ejecución P5.

## 5. Contrato de errores

### Admisión

```text
BLOCKED_MISSING_INPUTS
```

Revisar `issues`, `issue_count` y `study_input_readiness`. No se construye una entrega. Corregir el manifiesto y repetir P8B.

### Ejecución

```text
BLOCKED_BY_P8D2_EXECUTION
```

Revisar `p8d2_execution.execution_status`, `issues` y `next_gate`. No se crea dossier. La reparación debe ser explícita; no existe binding automático de fallas.

### Generación de artefactos

```text
DOSSIER_ARTIFACT_GENERATION_FAILED
```

El directorio parcial no se considera entrega válida. Revisar `error`, `output_directory` e `integrity_index_generated`.

### Integridad

```text
DOSSIER_INTEGRITY_MISMATCH
```

Revisar `issues`. No usar el paquete como entrega verificada; restaurarlo desde una fuente confiable o regenerarlo desde el manifiesto controlado.

P8F4 no repara ni reintenta automáticamente ninguno de estos estados.

## 6. Repetir una ejecución

P8F3 evita sobrescritura silenciosa. Si `salida_p8_first_use/dossier` ya existe y contiene una entrega, la nueva ejecución usa un sufijo incremental:

```text
dossier
dossier_2
dossier_3
...
```

El resultado devuelve:

- `requested_output_directory`;
- `output_directory`;
- `output_directory_collision_avoided`.

Cada dossier conserva su propio índice P8F2 y debe verificarse de manera independiente.

## 7. Qué significa la verificación SHA-256

`DOSSIER_INTEGRITY_VERIFIED` demuestra coherencia del conjunto de bytes respecto de `dossier_integrity.json`. Permite detectar archivos modificados, faltantes o extra y mantiene rutas relativas portables.

No demuestra autoría. SHA-256 no sustituye una firma digital, certificado, sello de tiempo confiable ni un futuro gate de emisión profesional.

## 8. Límites que permanecen cerrados

```text
automatic_defaults = false
automatic_dispatch = false
automatic_fault_binding = false
crosscheck = false
professional_emission = false
```

El backend pandapower IEC 60909 continúa siendo experimental y explícito dentro del alcance declarado; no se afirma conformidad completa con IEC 60909-0:2026.

El Workspace V5 es la ruta visual única del piloto. El navegador no recalcula ingeniería.
