# P7 — MCP Eléctrico 0.9 Engineering Preview


**Ampliación Q5 (4 de octubre):** dos motores SCR delta sobre red RL común verificados mediante siete estudios, 50/60 Hz, cargas distintas y bypass independientes. Ver [alcance y evidencia](MSL_SCR_DOS_MOTORES.md). Más de dos SCR, mezcla DOL/SCR y estrella siguen fuera del alcance.

## Confiabilidad técnica y responsabilidad del ingeniero — Q5

El MCP es una herramienta de cálculo para el ingeniero. Su desarrollo debe demostrar
que las entradas se traducen correctamente, que los resultados son reproducibles
y contrastados, y que los datos faltantes, supuestos, límites y errores se informan.
El ingeniero selecciona los criterios del proyecto, revisa los resultados,
aprueba el estudio y lo firma. Esa aprobación es una responsabilidad externa;
no es un módulo numérico pendiente de implementar.

Los campos históricos `professional_emission=false` y `professional_report=false`
indican que el software no aprueba ni firma automáticamente. No prohíben el uso
profesional del cálculo ni la firma del ingeniero. Una firma digital integrada
sería una mejora documental opcional y no una condición para verificar un solver.
Los estados experimentales se conservan exclusivamente cuando falta evidencia
técnica de la integración o del alcance. Arc Flash permanece diferido.

## Cierre vigente de módulos — Q5, 4 de octubre de 2026

Consultar el [registro de cierre](ESTADO_CIERRE_MODULOS.md): estados, alcance, evidencia y condiciones finitas pendientes. La integración verificada, los datos del proyecto, los criterios de diseño, la conformidad normativa y la aprobación del informe se evalúan por separado.

**Actualización Q4 (4 de octubre):** DOL01–DOL03 y SCR01–SCR03 están cerrados dentro de sus alcances MSL publicados. Ver [evidencia DOL](MSL_DOL_VERIFICACION.md) y [contraste SCR original](MSL_SCR_REFERENCIA_ORIGINAL.md). Bancos estáticos, P5 y P7 conservan sus cierres por alcance. Arc Flash sigue diferido.


## Estado

P7 cierra el expediente mínimo reproducible necesario para iniciar uso interno controlado de MCP Eléctrico.

```text
P7A  snapshot reproducible + SHA-256             DONE
P7B  reconstrucción verificable del netlist DSS DONE
P7C  reporte técnico reproducible HTML/PDF-print DONE
P7D  gate Engineering Preview 0.9                IMPLEMENTED

P6 IEEE 1584 Arc Flash = DEFERRED
professional_report    = false
professional_emission  = false
```

El gate P7D no promociona por decreto la madurez de P1–P7. Solo comprueba que la cadena mínima operacional existe y conserva sus limitaciones.

## Release habilitada por P7D

Cuando todos los criterios P7D están `DONE`:

```text
product_release           = MCP_ELECTRICO_0_9_ENGINEERING_PREVIEW
engineering_preview_ready = true
internal_use_ready         = true
allowed_use                = CONTROLLED_INTERNAL_ENGINEERING_PREVIEW
next_activity              = REAL_SUBSTATION_PILOT
professional_emission      = false
```

`engineering_preview_ready=true` significa que el sistema puede empezar a utilizarse en proyectos piloto reales con revisión del ingeniero. No significa certificación, firma, conformidad normativa integral ni autorización automática para emitir entregables profesionales.

## P7A — snapshot reproducible

P7A congela por contenido:

- netlist DSS;
- revisión del modelo y workspace;
- datos profesionales P2;
- secuencia cero;
- ampacidad P3;
- protección y datasets TCC P5;
- estudios registrados;
- matriz de madurez;
- selección de motores y versiones de runtime.

El snapshot usa SHA-256 determinista. Rutas de exportación y timestamps transitorios conocidos no forman parte del contenido canónico.

## P7B — reconstrucción verificable

P7B exige `HASH_MATCH` antes de escribir y realiza un round-trip canónico del netlist DSS.

La reconstrucción v1 restaura únicamente el netlist eléctrico verificado. P2/P3/P5/TCC requieren rebind explícito y los estudios históricos requieren recálculo. Ningún resultado almacenado se promociona silenciosamente a resultado vigente.

## P7C — reporte técnico reproducible

P7C genera un HTML determinista desde un snapshot P7A verificado.

El reporte incluye:

- SHA-256 del snapshot fuente;
- hash propio del reporte;
- revisión de modelo;
- estudios vigentes e históricos separados;
- datos P2/P3/P5;
- madurez y limitaciones;
- motores y versiones;
- estado P5;
- advertencias de producto.

El navegador no recalcula ingeniería. `Imprimir / Guardar PDF` utiliza únicamente `window.print()` (`BROWSER_PRINT`).

El reporte P7C es un resumen técnico reproducible que el ingeniero puede revisar,
incorporar a su estudio y firmar. El software no añade una firma automática.

## P7D — gate de producto

Schema:

```text
MCP_ELECTRICO_P7D_ENGINEERING_PREVIEW_GATE_V1
```

Criterios obligatorios:

1. P5 `READY_WITH_LIMITATIONS` y ruta operacional habilitada.
2. P7A snapshot reproducible implementado.
3. P7B reconstrucción fail-closed implementada.
4. P7C reporte reproducible con `HASH_MATCH`, sin recálculo y `BROWSER_PRINT`.
5. Workspace V5 persistente disponible.
6. Política de motores determinista: OpenDSS por defecto, `automatic_dispatch=false`, `crosscheck=false` y P5 reconocido como implementado.
7. P6 IEEE 1584 explícitamente `DEFERRED` y no ejecutable.
8. Responsabilidades declaradas: `professional_report=EXTERNAL_RESPONSIBILITY`;
   el software documenta sus verificaciones y el ingeniero revisa, aprueba y firma.

Si un criterio falla, el gate devuelve:

```text
phase_status              = NOT_READY
ready_for_release         = false
engineering_preview_ready = false
product_release           = null
```

No existe bypass automático.

## Alcance recomendado del primer piloto

El primer piloto debe ser una subestación pasiva alimentada desde red, representativa del uso objetivo del producto, por ejemplo una subestación MT/BT industrial, hospitalaria o minera con:

- equivalente de red MAX/MIN;
- uno o más transformadores con datos P2 completos;
- alimentadores/cables trazables;
- secuencia cero y puesta a tierra explícitas cuando se estudien fallas a tierra;
- flujo de potencia y caída de tensión;
- ampacidad P3 donde exista evidencia normativa suficiente;
- IEC 60909 dentro del alcance declarado;
- protección/TCC P5;
- Workspace V5;
- snapshot P7A y reporte P7C.

El propósito del piloto es encontrar fricción de modelado, UX, trazabilidad y reporte antes de endurecer MCP Eléctrico 1.0.

## Fuera de alcance de la 0.9

Continúan fuera de la promesa de producto:

- IEEE 1584 Arc Flash formal;
- emisión profesional automática;
- firma digital automática integrada;
- conformidad normativa integral no demostrada;
- generación dominante de motores/generadores/conversores fuera del alcance validado;
- cross-check automático entre motores;
- despacho automático de backend.

Los campos históricos de emisión no condicionan el uso ni la firma del ingeniero;
los límites técnicos y la suficiencia de datos se evalúan por estudio.
