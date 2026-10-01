# Primer uso en esta PC

1. Recargue o reinicie Codex para actualizar el catálogo de **mcp-electrico**.
   Abra un chat local con este servidor conectado. Codex inicia automáticamente
   el proceso; el modo stdio no requiere abrir el servidor HTTP.
2. Para una demostración, solicite: «Usa mcp-electrico para validar y ejecutar
   el ejemplo RMS de motores de examples/p13_dynamic_rms_manifest.json,
   p13_dynamic_rms_package.json y p13_dynamic_rms_options.json. Genera su dossier
   en una carpeta nueva y abre el informe». Son datos sintéticos de referencia.
3. Para su proyecto, adjunte el unifilar y las tablas de fuente, transformadores,
   cables, cargas y protecciones. Indique frecuencia, tensiones y estudios
   deseados. Valide primero el manifiesto y los datos ausentes. Construya Rev.0,
   ejecute el flujo y revise el Workspace antes de los siguientes estudios.

Cada proceso conserva su propio modelo activo. Los estudios aislados de motores
y escenarios no reemplazan ese modelo. Guarde manifiestos, resultados y dossiers
en carpetas del proyecto; indique nombres nuevos para las exportaciones.

## Navegación

Busque equipos por nombre o identificador. Use **Vista legible** y **Centrar
selección** para redes grandes; arrastre el diagrama o use las flechas para
moverse. **Ver red completa** restaura el conjunto. El inspector corresponde
al equipo seleccionado. **exportar_laminas_unifilar** genera láminas A3 con solape.

El informe dinámico ofrece velocidad, corriente, par y tensión, valores del
criterio, tabla de muestras y CSV. Compruebe por separado estado de ejecución,
criterios y verificación del dossier.

## Datos para motores

El arranque estático usa los datos declarados del motor. La dinámica requiere
además parámetros eléctricos por fase, velocidad nominal, inercias, curva de
par resistente y procedencia. Los campos ausentes bloquean la ejecución; no se
rellenan con el ejemplo. El alcance dinámico es RMS equilibrado, un motor de
arranque directo por estudio. No incluye transitorios de flujo, VFD ni térmica.

Arc Flash IEEE 1584 permanece pendiente. La entrega conserva la clasificación
Engineering Preview y `professional_emission=false`; los informes muestran los
límites de cada cálculo.
