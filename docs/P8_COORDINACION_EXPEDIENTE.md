# P8 — Coordinación temporal incluida en el expediente

La evaluación continua P5E puede solicitarse en
`protection.coordination_ranges` del manifiesto. P8D2 reutiliza los resultados
P4 de la misma ejecución, evalúa cada par declarado una sola vez y agrega su
criterio a `design_checks.json`. No añade un motor, no recalcula cortocircuitos
dentro de P5 y no deduce la relación entre dispositivos.

## Declaración

Además de `PROTECTION_TCC`, el manifiesto debe solicitar el scope P4 que
corresponda: `IEC60909_3PH_MAX_MIN` o `IEC60909_1PH_GROUND_MAX_MIN`.
Ambas barras límite deben estar en `study_inputs.short_circuit_buses`.
Ejemplo de un registro dentro de `protection.coordination_ranges`:

```json
{
  "id": "PAR_ALIMENTADOR_GENERAL",
  "downstream_device_id": "QF_alimentador",
  "upstream_device_id": "QF_general",
  "upstream_to_downstream_ratio": 1,
  "required_margin_s": 0.2,
  "relationship_source_reference": "Unifilar, revisión y relación en serie confirmada",
  "currents_source_reference": "Escenario P4 y justificación del factor constante",
  "current_bounds": {
    "minimum": {
      "fault_bus": "barra_carga",
      "fault_type": "3ph",
      "case": "min",
      "current_quantity": "ikss_ka",
      "operating_voltage_kv": 0.48
    },
    "maximum": {
      "fault_bus": "barra_carga",
      "fault_type": "3ph",
      "case": "max",
      "current_quantity": "ikss_ka",
      "operating_voltage_kv": 0.48
    }
  }
}
```

Los valores ilustran el formato; no son recomendaciones de ajuste ni datos
de una instalación. Identificador, dos dispositivos distintos, factor, margen
y referencias son obligatorios. Se rechazan campos desconocidos y duplicados.
Solo se admite `ikss_ka`, convertido explícitamente a amperios para las TCC.
Los límites deben referir a la misma barra, tipo de falla y tensión declarada.
No se ordenan ni intercambian silenciosamente: MIN debe producir una corriente
menor que MAX para que exista un intervalo utilizable.

El factor constante también es obligatorio cuando vale 1. Debe justificarse
para ese par y escenario; no se deduce de un transformador, TC o corrientes de
barras diferentes. Una relación variable requiere otro estudio apropiado.

## Comportamiento

| Situación | Entrega |
| --- | --- |
| Campo ausente o lista vacía | `NOT_REQUESTED`; no agrega un criterio ni afirma coordinación |
| Solicitud mal formada, dispositivos o referencias no declarados | Bloqueo previo a ejecutar P8D1 |
| P4 incompleto, referencia no resuelta o rango invertido/degenerado | No hay rango válido ni dossier listo |
| Hueco TCC, semántica distinta de TOTAL_CLEARING_TIME, excepción o salida inválida | P8D2 parcial; no se genera un dossier listo |
| Margen insuficiente con cálculo completo | Dossier con `DECLARED_CHECKS_FAILED`; conserva FAIL y el peor punto |
| Todos los criterios declarados pasan | `DECLARED_CHECKS_PASSED` para esos criterios, sin aprobación automática |

Un estado `DOSSIER_READY_ENGINEERING_PREVIEW` significa que la entrega es
completa y verificable; puede contener un diseño fallido. No significa que la
instalación cumpla. Los resultados de rango se validan también contra el par,
intervalo y criterio solicitados antes de promoverlos.

## Evidencia y lectura

El dossier incluye `coordination_ranges.json`, inventariado por el índice de
integridad SHA-256. Contiene solicitudes, resultados P5E, procedencia de ambos
límites P4, SHA del manifiesto y revisión. La respuesta MCP devuelve su ruta y
resumen; `execution_p8d2.json` conserva la misma evidencia.
`design_checks.json` identifica cada criterio con
`scope=TEMPORAL_COORDINATION_RANGE` e identificador del par.

El visor y el informe imprimible muestran una tabla con par, intervalo,
factor, criterio, peor margen y corriente crítica. Renderizan los datos
congelados: no calculan ingeniería en el navegador ni promueven resultados
históricos a vigentes.

La comprobación sigue siendo temporal sobre curvas log-log declaradas,
con los [límites P5E](P5E_COORDINACION_INTERVALO.md). No acredita selectividad
integral, no actuación del dispositivo upstream, energía pasante, Icw,
sensibilidad en todas las ubicaciones o conformidad completa. El intervalo de
un escenario no equivale a todas las fallas posibles de una instalación.

## Banco reproducible

`examples/p10_reference_coordination_range.json` es un ejemplo sintético:
agrega dos dispositivos declarados en serie en el mismo alimentador BT de P10.
No utiliza la protección del ramal MT como si estuviera en serie con BT.
Las curvas son `TEST_DATA`; no representan equipos comerciales.

```text
python -m pytest tests/test_p8_coordination_ranges.py -q
python scripts/verify_coordination_dossier_mcp.py --output outputs/coordination-dossier
```

La lane `engineering-acceptance` ejecuta las pruebas y el script MCP en
Windows/Linux. Los casos cubren éxito, diseño fallido, referencias 3F/1F-T,
preflight sin cálculo, hueco interno, salidas inválidas, hashes, HTML y copia
alterada. El script conserva llamadas, resultados y hashes; `tamper-check` es
una prueba negativa, no una entrega utilizable. Este banco no cierra Brno ni
la validación de una instalación real completa.
