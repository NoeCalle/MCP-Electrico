# Investigación de casos externos: transformadores

Fecha de revisión: 17 de octubre de 2026.

## Casos admitidos al banco numérico

IEEE Four Node Test Feeder: referencia pública para conexiones de
transformadores, con dos líneas y un banco de 6 MVA. Se eligieron ocho
combinaciones de elevación/reducción, estrella aterrizada–estrella aterrizada
y delta–estrella aterrizada, demanda equilibrada/desequilibrada.

La página IEEE actual no pudo descargarse en esta revisión. Se contrastaron
la descripción IEEE disponible, la implementación documentada de LBNL
Buildings y las tablas IEEE transcritas por Power Grid Model IO. Estas últimas
se fijaron a un commit y se conservaron sin modificación en el banco.
No se afirma haber descargado un archivo original IEEE inaccesible.

- IEEE: https://ewh.ieee.org/soc/pes/dsacom/testfeeders/testfeeders.pdf
- LBNL: https://simulationresearch.lbl.gov/modelica/releases/v5.0.1/help/Buildings_Electrical_AC_ThreePhasesUnbalanced_Validation_IEEETests_Test4NodesFeeder_BalancedStepDown.html
- Datos fijados: https://github.com/PowerGridModel/power-grid-model-io/tree/4cb5f85c7e361bd68243036ca255d2100ed0a937/_network_data_generation/ieee_4_node

Es un benchmark, no un proyecto construido ni una prueba de aceptación en campo.

## Instalaciones y tesis localizadas

| Fuente | Revisión realizada | Decisión para reproducción |
|---|---|---|
| Tena Ortega e Iza Guananga, UPS, 2025; subestación interior de 300 kVA para edificio público | Ficha, PDF completo de 106 páginas, figuras de flujo de la página PDF 71 y descripción de entradas en páginas PDF 70–71 | Candidato real documentado. No admitido todavía como comparación ETAP completa: las entradas aparecen en capturas pequeñas; no se obtuvo un inventario numérico completo y legible de impedancias de cables, fuente y transformador, y cargas por barra. |
| Mendez Huaman y Tapia Ccoyso, UNSAAC, 2019; transferencia Pisac 05–Urubamba 04 | Ficha del repositorio y descripción de alcance | Candidato. La ficha declara acceso cerrado y el adjunto es pequeño; no se dispone del paquete completo para repetir las simulaciones DIgSILENT. |
| UCSM; interconexión de centrales Ángel I, II y III al SEIN | Metadatos y resumen de búsqueda: transformación 33/138 kV, 105 MVA | Preselección; documento completo y parámetros aún no auditados. No ejecutado ni validado. |
| Henry Johany García Arboleda, UNAM, 2017; optimización de un sistema industrial | Índice y apartados de cortocircuito del PDF de 111 páginas; anexos C/D de flujo y parámetros | Candidato prioritario para la siguiente etapa industrial. Publica parámetros y equivalentes, pero el apartado revisado compara IEEE/ANSI C37: no se debe etiquetar como concordancia IEC 60909. La tabla 6.13 rotula como Z0 una suma de secuencias utilizada antes; requiere reconciliar tabla y desarrollo antes de automatizarla. No ejecutado todavía. |

Fuentes de los candidatos:

- UPS: https://dspace.ups.edu.ec/handle/123456789/29791
- PDF UPS: https://dspace.ups.edu.ec/bitstream/123456789/29791/1/UPS-GT006047.pdf
- UNSAAC: https://repositorio.unsaac.edu.pe/items/e79fa933-d3b0-4ca4-9f32-07d19de4d73a
- UCSM: https://repositorio.ucsm.edu.pe/items/779fcff3-4e58-49ef-a5fd-0355c9baf1d3
- UNAM: https://tesiunamdocumentos.dgb.unam.mx/ptd2017/mayo/0759661/0759661.pdf

La tesis UPS describe diseño, ampliación y simulación; eso no demuestra que
la instalación propuesta se haya construido o ensayado. Sus valores de
impedancia del apartado de puesta a tierra no se trasladaron al modelo de
flujo sin aclarar bases, unidades y correspondencia con las capturas ETAP.

## Regla de admisión y siguiente trabajo

Un caso completo requiere topología, frecuencia, tensiones y referencia de
fuente, carga por barra/fase y modelo, R/X o pérdidas y uk del transformador,
conexiones y tap, impedancias/longitudes de líneas, y resultados con las mismas
condiciones. Para cortocircuito se agregan equivalentes MAX/MIN, secuencias,
puesta a tierra y aportes de máquinas. Para protecciones se requieren curvas,
ajustes, equipos y tiempos trazables.

La ausencia de un dato se registra; no se completan datos de una tesis con
valores por defecto para luego declarar concordancia. El banco Q11 resuelve
la verificación de transformadores en un alcance acotado. La calificación de
una instalación real completa y su revisión de ingeniería siguen abiertas.
