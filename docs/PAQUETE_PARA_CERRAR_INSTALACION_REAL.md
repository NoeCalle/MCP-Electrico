# Paquete concreto para cerrar la validación de una instalación real

Este es el trabajo pendiente de ingeniería, distinto de instalar o arrancar el
servidor MCP. El alcance solicitado es flujo, caídas/cargabilidad, SC y
protecciones sobre la misma revisión del modelo, con resultados contrastables.
La instalación completa permanece abierta hasta ejecutarlo y revisar diferencias.

## Entrega necesaria

Se puede usar una instalación propia anonimizada o una referencia pública
completa. Debe incluir equipos y ajustes reales o supuestos explícitamente
aceptados para un estudio de diseño. La ausencia de mediciones de campo no
impide contrastar un modelo de diseño; sí impide presentarlo como validado en campo.

| Archivo / exportación | Contenido necesario | Criterio de recepción |
|---|---|---|
| `00_revision` | ID de proyecto, revisión, fecha, frecuencia, alcance, inventario de fuentes y escenarios; entradas medidas, de placa o estimadas diferenciadas | Todos los estudios remiten a esta revisión; supuestos identificados y aceptados por el responsable |
| `01_unifilar` | Barras, extremos de ramas, equipos, interruptores abiertos/cerrados, neutros/tierra y estados normal/transferencia/emergencia solicitados | IDs únicos y correspondencia con tablas de entrada |
| `02_red` | R1/X1/C1 y R0/X0/C0, longitudes, temperatura de referencia, material/sección/paralelos; transformadores con potencia, tensiones, grupo, uk, X/R o pérdidas, vacío y taps | Sin longitudes/impedancias reconstruidas a partir de los resultados que se quiere verificar |
| `03_cargas_fuentes` | P/Q o placa y uso por barra/fase, dependencia de tensión, factores aplicados, compensadores y aportes de máquinas | Sin convertir cargas Z/I o motores en PQ de forma silenciosa |
| `04_equivalentes_sc` | Fuente MAX/MIN con Scc3/XR y secuencias, neutros, impedancia de falla, temperaturas, aportes y método/opciones normativas | MAX y MIN documentados; no usar el mismo valor por ausencia de uno |
| `05_protecciones` | ID, ubicación/elemento protegido, fabricante/modelo/unidad, TC/TP, ajustes, curvas con tolerancias y procedencia, capacidades a tensión aplicable, tiempos de apertura y despeje | No sustituir modelos; no tratar tiempo de relé como despeje total ni Ics/Icw como Icu |
| `06_referencia` | Exportaciones de entradas y resultados de flujo y SC por escenario, TCC/actuación para todos los puntos solicitados; versión del programa y bibliotecas | Comparación contra la misma revisión con tolerancias definidas antes de observar diferencias |

Formatos preferidos: tablas CSV/XLSX o informes legibles exportados del
programa, acompañados del unifilar PDF y del archivo nativo si está disponible.
Un archivo nativo aislado puede depender de una versión/biblioteca externa;
no sustituye las exportaciones ni la revisión de entradas.

## Aplicación al expediente Brno disponible

No hace falta volver a buscar la tesis o el ZIP: ya se obtuvieron y fijaron sus
hashes. Falta una exportación reconciliada del mismo proyecto:

- Aclarar `PhaseAngle=0` en flujo/SC frente a `30` en secuencia y el Dyn1
  documentado; aclarar la bobina Petersen en secundarios BT.
- Exportar los ajustes/curvas originales y sus sustituciones, con capacidad de
  corte y semántica de tiempos. La secuencia guardada solo cubre `Bus194`.
- Identificar longitudes, demanda y equipos estimados frente a reales; aportar
  los escenarios MAX/MIN y las maniobras correspondientes.
- Decidir si se reproduce el modelo académico con sus supuestos o se valida
  la instalación efectiva con datos corregidos. Son objetivos distintos.

La ampliación de SC3 para decaimiento/Ith con máquinas y de la puesta a tierra
compensada requiere desarrollo/calificación adicional si se mantiene el alcance
íntegro de esa fábrica. No se atribuye ese pendiente de software al usuario.

## Secuencia de aceptación cuando lleguen los datos

1. Ingresar el manifiesto P8 existente y verificar referencias, unidades y
   completitud. Publicar los bloqueos antes de calcular.
2. Materializar una revisión del modelo por herramientas MCP, guardar huella
   y derivar únicamente escenarios declarados. Un motor operativo por estudio.
3. Ejecutar flujo OpenDSS y SC pandapower en sus contratos admitidos;
   detener los estudios fuera de alcance hasta calificarlos.
4. Enlazar corrientes de esa revisión con dispositivos/elementos y curvas;
   verificar corte, conductor, sensibilidad y coordinación dentro del alcance.
5. Contrastar resultados con la referencia usando tolerancias previamente
   fijadas; investigar diferencias, sin ajustar entradas para obtener coincidencia.
6. Generar expediente de entradas, huellas, escenarios, resultados, fallos y
   limitaciones; revisión final por el ingeniero. Solo entonces cerrar el caso.

La solicitud de estos datos es una dependencia técnica, no una autorización
adicional para continuar el desarrollo ya encargado.
