# Uso profesional controlado y aceptación de cálculos

Actualizado: 21 de octubre de 2026. Este perfil describe cómo usar y verificar
las capacidades calificadas del MCP. No cambia la física ni las exclusiones
del registro de módulos y no representa una certificación de la instalación.

## Entrega concreta

El MCP tiene una cadena integral para flujo, caída, ampacidad, cortocircuito
3F/1F-T MAX/MIN y comprobaciones de dispositivos con curvas explícitas. El
manifiesto P8 reúne las entradas de la misma revisión. El caso P10 recorre esa
cadena completa con datos sintéticos controlados; los bancos Q10/Q11 y Q12
añaden contrastes externos dentro de sus alcances publicados.

La aceptación de un cálculo se distingue del cumplimiento de su diseño:

| Situación | Comportamiento exigido |
| --- | --- |
| No convergencia, NaN, excepción o salida incompleta | Detener P8D1; no pasar a P5 ni generar un dossier listo |
| Falta una barra/caso MAX/MIN solicitado | Rechazar el agregado, aunque otra barra o caso haya funcionado |
| Cambia la revisión durante el cálculo | Detener la cadena; no promover los resultados a vigentes |
| Falta un rating aplicable o una verificación térmica solicitada | P5 queda parcial; no generar entrega lista |
| Icu insuficiente, caída excesiva o ampacidad insuficiente | Conservar el cálculo válido y mostrar el incumplimiento de diseño |
| Se repite una entrega | Directorio nuevo; conservar y verificar el anterior |
| Se modifica un archivo de un dossier | El verificador de integridad debe rechazarlo |

`CONTROLLED_EXECUTION_FAILED_INVALID_RESULT` identifica el primer cálculo
inválido, las comprobaciones incumplidas, los estudios válidos anteriores y
los pendientes. No hay reparación, segundo solver ni reintento automático.
Los valores no finitos rechazados se conservan como diagnóstico identificado,
sin introducir NaN/Infinity en las respuestas JSON o en el workspace.

P5 admite resultados `PASS` y `FAIL` como comprobaciones completas. Estados
como `NOT_APPLICABLE_VOLTAGE` o `SECTION_MISMATCH` no son comprobaciones
completadas. Un tiempo de despeje disponible no suple esas carencias.

## Secuencia de uso

1. Preparar el manifiesto con la [misma revisión y procedencia de entradas](PAQUETE_PARA_CERRAR_INSTALACION_REAL.md).
2. Llamar a `evaluar_admision_piloto_real(manifest)` y resolver los faltantes.
3. Llamar a `generar_dossier_piloto_real(manifest, directorio_salida)`.
4. Revisar `status`, `design_assessment`, los resultados y las limitaciones.
5. Llamar a `verificar_integridad_dossier_real(ruta_indice)` antes de compartir
   una copia. Revisar el modelo y los criterios antes de aprobar el estudio.

Ejemplo de cadena completa reproducible:
`examples/p10_reference_substation_stage5.json`. Es un ejemplo sintético de
producto y debe sustituirse por las entradas trazables del proyecto.

Cada dossier completo incorpora `design_checks.json` dentro del conjunto de
artefactos verificado por SHA-256. Su `manifest_sha256` y `model_revision`
deben coincidir con la ejecución y la entrega. Sus estados son:

- `DECLARED_CHECKS_PASSED`: pasan los criterios solicitados que aparecen en la lista.
- `DECLARED_CHECKS_FAILED`: al menos un criterio solicitado falla; el informe conserva el fallo.
- `NOT_EVALUABLE`: no se ha confirmado la validez/completitud necesaria.

Estos estados no afirman selectividad integral, sensibilidad para todo punto
de falla ni conformidad completa de la instalación. Las verificaciones no
solicitadas no se transforman en PASS.

## Un motor por estudio

`ejecutar_estudio` conserva las rutas públicas y sus validadores. Incluye
`falla_terminal_motor` / `motor_terminal_fault_emt`, que invoca exclusivamente
`ejecutar_falla_terminal_motor_modelica` con el paquete explícito Q13A. No
traduce el unifilar completo a Modelica ni sustituye el Ith IEC bloqueado.

La soportabilidad térmica P8D2 que usa Ikss y un despeje explícito declara
`DECLARED_IKSS_CONSTANT_RMS_NOT_IEC60909_ITH`: es un chequeo con corriente RMS
constante, sin componente DC ni decaimiento de máquinas. Para equipos
limitadores debe usarse el I²t total publicado mediante la ruta Q12C cuando
corresponda; no se intercambian esas magnitudes silenciosamente.

## Verificación reproducible

El workflow `.github/workflows/engineering-acceptance.yml` ejecuta en Windows
y Linux los fallos inyectados en las fronteras de cálculo y una conexión MCP
stdio real. Recorre un diseño de referencia, otro con fallo de capacidad de
corte, una repetición, una entrada incompleta, una copia alterada y el gate
de la nueva ruta de falla terminal de motor. Conserva `Summary.json`, logs,
expedientes y hashes como artefactos de CI. Los directorios `tamper-check` son
pruebas negativas y no entregas utilizables.

Comandos del banco:

```text
python -m pytest tests/test_execution_quality.py tests/test_p10g_reference_dossier.py -q
python scripts/verify_engineering_acceptance_mcp.py --output outputs/engineering-acceptance
```

La suite general y las demás lanes conservan las regresiones numéricas y los
contrastes externos. Este gate comprueba integración, completitud, fallos,
trazabilidad e integridad; no reemplaza los bancos físicos de cada solver.

## Pendientes que permanecen abiertos

La fábrica Brno necesita reconciliar revisiones, tierra y protecciones antes
de poder validar ese proyecto completo. Permanecen excluidos el Ith IEC con
máquinas, la tierra compensada de ese caso, las rutas Modelica no calificadas
y la selectividad integral. Arc Flash IEEE 1584 sigue diferido por decisión
del proyecto. El detalle normativo pendiente está en
[VALIDACIONES_PENDIENTES.md](VALIDACIONES_PENDIENTES.md).

El uso profesional de los alcances verificados requiere datos y criterios
revisados para el estudio. `professional_emission=false` expresa que el MCP no
aprueba ni firma automáticamente; no prohíbe el uso de sus cálculos por el
ingeniero. No se convierte el número de herramientas o tests en un porcentaje
de cobertura del mercado.
