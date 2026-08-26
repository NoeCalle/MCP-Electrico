# Validación integral de línea base local

Después de clonar e instalar dependencias, `examples/validar_linea_base.py` permite ejecutar en **un solo comando** las cuatro comprobaciones previas al trabajo con datos reales:

```bash
python examples/validar_linea_base.py
```

Por defecto crea `salida_validacion_local/` y ejecuta, en procesos Python separados:

1. `diagnostico_local.py` — entorno, dependencias, OpenDSS, API pública y gates;
2. `primer_uso.py` — smoke integral y workspace;
3. `caso_referencia_01.py` — referencia numérica independiente P1;
4. `ejecutar_caso_minimo.py` — plantilla JSON editable radial P1.

El orquestador **no añade lógica eléctrica**. Cada etapa usa el ejecutable que ya tiene su propio contrato y validación.

## Resultado esperado

```text
MCP_ELECTRICO_LOCAL_BASELINE_V1
status = PASS
passed = 4
failed = 0
```

El script termina con exit code 0 solo cuando las cuatro etapas tienen:

- exit code 0;
- su campo semántico de éxito (`ok=true` o `pass=true`);
- JSON legible;
- todos los artefactos esenciales presentes.

Si una etapa falla, las demás se ejecutan igualmente para obtener una fotografía diagnóstica más completa, y el orquestador termina con exit code 2.

## Estructura de salida

```text
salida_validacion_local/
├── 01_diagnostico/
│   └── diagnostico_local.json
├── 02_primer_uso/
│   ├── resultado_primer_uso.json
│   └── workspace_primer_uso.html
├── 03_ref01/
│   └── resultado_caso_referencia_01.json
├── 04_caso_minimo/
│   ├── resultado_caso_minimo.json
│   ├── caso_entrada_normalizado.json
│   └── workspace_caso_minimo.html
└── manifiesto_linea_base.json
```

## Manifiesto

`manifiesto_linea_base.json` registra:

- versión de Python y plataforma;
- commit Git, cuando Git está disponible;
- estado PASS/FAIL de cada etapa;
- comando ejecutado y código de retorno;
- schema del JSON producido;
- cola de stdout/stderr para diagnóstico;
- existencia, tamaño y SHA-256 de cada artefacto;
- política global del orquestador.

La política se conserva explícitamente:

```json
{
  "electrical_logic_added_by_orchestrator": false,
  "automatic_dispatch": false,
  "crosscheck": false,
  "professional_emission": false
}
```

## Sobre los hashes

`sha256_raw_file` identifica exactamente el archivo producido en **esa ejecución**. Algunos JSON/HTML contienen rutas absolutas del equipo local; por ello esos hashes sirven como huella del artefacto, pero no se usan para exigir que dos computadoras produzcan el mismo hash byte a byte.

La equivalencia numérica entre equipos se comprueba específicamente con REF-01 y sus tolerancias publicadas, no comparando hashes de HTML o JSON que contienen rutas locales.

## Carpeta personalizada

```bash
python examples/validar_linea_base.py --output-dir C:\MCP_Electrico\validacion
```

En Linux/macOS puede usarse cualquier ruta escribible.

## Timeout

Cada etapa tiene por defecto un máximo de 180 segundos:

```bash
python examples/validar_linea_base.py --timeout 300
```

El timeout es individual por etapa, no para toda la suite.

## Uso recomendado

Ejecutar esta suite:

- inmediatamente después del primer clon;
- después de cambiar Python o recrear el entorno virtual;
- después de actualizar dependencias importantes;
- cuando un resultado local parezca distinto al esperado;
- antes de atribuir a un caso eléctrico un problema que podría ser de instalación.

Un `PASS` demuestra que la línea base instalada es funcional dentro de los alcances ya publicados. No valida un proyecto real, no habilita IEC 60909, coordinación/TCC ni IEEE 1584, y mantiene `professional_emission=false`.
