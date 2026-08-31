# P8 — Checklist para el primer proyecto real controlado

Este checklist corresponde al cierre P8F5 de MCP Eléctrico 0.9 Engineering Preview.

Su objetivo es preparar un expediente real antes de ejecutar:

```text
evaluar_admision_piloto_real
        ↓
generar_dossier_piloto_real
        ↓
verificar_integridad_dossier_real
```

El mismo checklist está disponible por MCP mediante:

```text
obtener_checklist_p8f5_datos_proyecto_real()
```

## Regla principal

No usar `examples/p8_first_use_manifest.json` como si fuera evidencia de proyecto. Es una plantilla ejecutable. Antes de una corrida real deben sustituirse sus magnitudes y referencias `EJEMPLO P8F4` por datos provenientes del expediente, SLD, fichas, estudios o cálculos controlados.

## 1. Identidad del proyecto

Debe existir:

- `project.id`;
- `project.name`;
- `project.source_reference`.

La referencia debe permitir identificar expediente, revisión, plano o paquete de información usado.

## 2. Red aguas arriba

Para la fuente se requieren como mínimo:

- barra de conexión;
- tensión nominal LL;
- frecuencia;
- Scc máxima y X/R máximo;
- Scc mínima y X/R mínimo cuando se solicita escenario MIN;
- referencia del estudio/utility.

No inferir Scc MIN desde MAX ni completar X/R con defaults silenciosos.

## 3. Topología y cargas

Preparar desde el SLD y documentos asociados:

- buses/barras;
- transformadores;
- líneas/cables;
- cargas;
- conexiones y tensiones coherentes;
- IDs estables para mantener trazabilidad entre P2/P3/P4/P5.

## 4. Secuencia positiva

### Transformadores

Revisar:

- kVA;
- kV HV/LV;
- `%Z` / `uk_percent`;
- grupo vectorial;
- X/R o evidencia equivalente soportada;
- pérdidas/taps cuando correspondan al alcance;
- referencia de placa, ficha o cálculo.

### Líneas/cables

Revisar:

- longitud;
- fases;
- R1;
- X1;
- C1 cuando se use;
- temperatura final explícita para IEC 60909 MIN cuando aplique;
- referencia de ficha/cálculo.

## 5. Secuencia cero para falla 1F-T

Si el scope incluye `IEC60909_1PH_GROUND_MAX_MIN`, preparar explícitamente:

- R0/X0 de la fuente para MAX/MIN;
- R0/X0/C0 de cada línea relevante;
- parámetros Z0 de transformadores;
- lado de neutro;
- modo de neutro;
- impedancia de neutro cuando corresponda;
- referencias de cálculo/ensayo/utility.

No asumir universalmente `Z0 = Z1`.

## 6. Ampacidad P3

Por alimentador/conductor preparar:

- `element_id`;
- código/identidad del conductor;
- ampacidad base;
- norma versionada;
- corriente de diseño `Ib`;
- corriente nominal de protección `In`;
- condición de instalación;
- factores de corrección con referencias, o confirmación explícita de condiciones base;
- referencia de ampacidad;
- referencia de instalación;
- referencia de `Ib`;
- referencia de `In`.

El proyecto puede usar `PROJECT_DATA`; no es obligatorio que el cable exista en la biblioteca interna.

## 7. Dispositivos de protección P5

Por dispositivo preparar:

- ID;
- tipo (`circuit_breaker` o `fuse` dentro del alcance actual);
- elemento protegido;
- In;
- Ue;
- norma;
- fabricante/modelo cuando se disponga;
- referencia de ficha/cuadro aprobado.

### Breaker

Mantener separados:

- Icu;
- Ics;
- Icw.

El chequeo de capacidad de corte usa Icu. Ics/Icw no deben sustituirla silenciosamente.

### Fuse

Usar `breaking_capacity_ka` con su semántica propia.

## 8. Dataset TCC numérico

Metadata de curva no basta. Para la ejecución P5 preparar:

- `curve_id`;
- `dataset_id`;
- `shape`;
- `time_semantics`;
- tipo y referencia de fuente;
- revisión;
- segmentos;
- puntos numéricos corriente-tiempo;
- método de digitalización si la curva fue digitalizada.

Para promover clearing time automáticamente debe existir `TOTAL_CLEARING_TIME` y la corriente ligada debe estar dentro del dominio del dataset.

## 9. Binding explícito P4 → P5

Por dispositivo indicar:

- `device_id`;
- `fault_bus`;
- `fault_type`;
- `case` MAX/MIN;
- `current_quantity=ikss_ka`;
- `operating_voltage_kv`;
- `source_reference` del binding.

Si se solicita chequeo térmico, agregar sección, coeficiente `k` y procedencias explícitas.

MCP no elige automáticamente barra, tipo de falla, caso ni magnitud.

## 10. Scope, targets y criterios

Antes de correr dejar explícitos:

- `requested_scope`;
- buses de cortocircuito;
- límites configurables como caída de tensión;
- cualquier criterio específico del estudio.

No presentar un valor configurable como requisito normativo universal si la norma/proyecto no lo establece.

## Preflight recomendado

Primero ejecutar:

```text
evaluar_admision_piloto_real(manifest)
```

Esperar:

```text
READY_TO_BUILD_MODEL
```

Si devuelve `BLOCKED_MISSING_INPUTS`, corregir el manifiesto. No saltar el gate.

## Ejecución

Cuando admisión y readiness sean válidos:

```text
generar_dossier_piloto_real(manifest, directorio_salida)
```

Un caso sano termina con:

```text
DOSSIER_READY_ENGINEERING_PREVIEW
```

La entrega incluye Workspace V5, snapshot/reconstrucción/reporte P7 y el índice P8F2.

## Verificación posterior

Ejecutar:

```text
verificar_integridad_dossier_real(ruta_indice)
```

Esperar:

```text
DOSSIER_INTEGRITY_VERIFIED
```

Si existe mismatch, no considerar el paquete una entrega íntegra.

## Repeticiones

P8F3 evita sobrescritura silenciosa. Si el directorio solicitado ya contiene una entrega, la siguiente usa `_2`, `_3`, etc.

Conservar el `dossier_integrity.json` de cada corrida junto con su propia entrega.

## Gate de producto antes de empezar

Puede consultarse:

```text
evaluar_cierre_p8f5_uso_real_controlado()
```

El estado esperado de esta release es:

```text
READY_FOR_CONTROLLED_REAL_PROJECT_USE
```

Esto significa que la ruta está lista para **uso real controlado bajo Engineering Preview**. No significa:

- certificación del software;
- conformidad normativa integral;
- validación de cualquier modelo que se ingrese;
- firma o responsabilidad profesional automática;
- autorización para emitir resultados sin revisión humana.

## Límites actuales

```text
automatic_defaults = false
automatic_dispatch = false
automatic_fault_binding = false
crosscheck = false
professional_emission = false
```

Además:

- OpenDSS es el motor por defecto;
- pandapower IEC 60909 es explícito y experimental dentro del alcance validado con limitaciones;
- no existe claim de conformidad completa IEC 60909-0:2026;
- P6 IEEE 1584 permanece `DEFERRED`;
- Workspace V5 no recalcula ingeniería en JavaScript.

## Primer expediente real

Para la primera aplicación real conviene comenzar con una red acotada y bien documentada —por ejemplo una subestación y uno o pocos alimentadores— y exigir procedencia clara para cada dato antes de ampliar el modelo.

La meta de la primera corrida no es producir automáticamente un informe profesional. Es comprobar que el expediente real recorre de forma trazable:

```text
expediente
→ admisión
→ modelo
→ P1/P3/P4/P5
→ Workspace V5
→ P7A/P7B/P7C
→ integridad P8F2
```

con revisión humana de ingeniería en cada punto crítico.
