# Ejercicio operativo — flujo de carga de referencia

## Objetivo

Este ejercicio demuestra el uso operativo del camino P8/P10 ya validado. No
crea una fase nueva ni modifica el motor eléctrico.

Usa el fixture controlado:

`examples/p10_reference_substation_stage1.json`

con:

- fuente 22.9 kV / 60 Hz;
- transformador principal 5 MVA, 22.9/4.16 kV;
- transformador auxiliar 1 MVA, 4.16/0.48 kV;
- alimentador MT de 0.4 km;
- alimentador BT de 0.08 km;
- carga MT de 2000 kW + 900 kvar;
- carga BT de 500 kW + 200 kvar;
- criterio de caída de tensión del proyecto: 5 %.

Los datos son `CONTROLLED_REFERENCE_DATA`; no representan todavía el proyecto
minero del usuario ni una selección comercial.

## Cadena ejecutada

```text
manifest
   ↓
P8B intake fail-closed
   ↓
P8C readiness/materialization
   ↓
P8D controlled execution
   ↓
OpenDSS POWER_FLOW
   ↓
OpenDSS VOLTAGE_DROP
   ↓
resumen JSON legible
```

El script reutilizable es:

```text
python examples/run_operational_powerflow_reference.py
```

También puede guardar el resultado:

```text
python examples/run_operational_powerflow_reference.py \
  --output artifacts/reference_powerflow_result.json
```

## Salida

El resumen expone:

- convergencia;
- pérdidas kW/kvar;
- tensiones mínimas/promedio/máximas por bus;
- corriente y flujo P/Q por alimentador;
- caída de tensión por alimentador;
- peor caída;
- tensión mínima del sistema;
- cumplimiento del criterio de proyecto.

## Fronteras

```text
automatic_defaults = false
automatic_dispatch = false
crosscheck = false
professional_emission = false
```

La prueba CI se ejecuta en Linux/Python 3.11 y Windows/Python 3.12 y vuelve a
correr primero la regresión P10B antes del ejercicio operativo.
