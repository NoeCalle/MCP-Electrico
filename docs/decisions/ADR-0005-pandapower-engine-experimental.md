# ADR-0005 — Pandapower como segundo motor experimental

## Estado

Aceptado para implementación experimental.

## Contexto

MCP Eléctrico nació con OpenDSS como motor eléctrico principal. El roadmap profesional requiere incorporar capacidades que OpenDSS no pretende cubrir de forma normativa o integrada, especialmente IEC 60909 y protección industrial. Pandapower 3.5.x ofrece flujo de potencia, cortocircuito conforme DIN/IEC EN 60909 y módulos de protección, por lo que es un candidato natural para complementar a OpenDSS.

La incorporación prematura de un modelo canónico completo, selección automática de motor y cross-check entre solvers aumentaría significativamente el alcance y el riesgo arquitectónico antes de disponer de datos profesionales de transformadores, fuentes equivalentes y secuencias.

## Decisión

Se incorpora pandapower como segundo motor **experimental y explícito** con las siguientes reglas:

1. OpenDSS sigue siendo el motor por defecto.
2. Pandapower se invoca mediante una tool separada: `ejecutar_flujo_pandapower()`.
3. No existe router automático de estudios en esta fase.
4. No existe cross-check OpenDSS/pandapower en esta fase.
5. El puente pandapower lee el modelo activo como entrada, pero no consume resultados de flujo OpenDSS.
6. Se crea una red pandapower nueva en memoria para cada ejecución.
7. El alcance inicial se limita a redes trifásicas balanceadas, de un único nivel de tensión, con `Line + Load` y fuente ideal en `sourcebus`.
8. Elementos fuera de alcance se rechazan mediante códigos explícitos `PPxxx`; no se aproximan silenciosamente.
9. Los transformadores se rechazan hasta que P2 disponga de %Z, componente resistiva/pérdidas, taps, grupo vectorial y procedencia trazable.
10. La madurez del módulo se declara `EXPERIMENTAL` aunque los casos iniciales pasen pruebas numéricas.
11. El resultado pandapower se registra como estudio secundario y no reemplaza la solución base OpenDSS del workspace.

## Consecuencias positivas

- MCP Eléctrico obtiene acceso real a un segundo solver sin una refactorización masiva.
- Se evita mantener dos modelos editados manualmente.
- La arquitectura queda preparada para aprovechar IEC 60909 y protección de pandapower posteriormente.
- Los límites del bridge son verificables y auditables.
- P2 podrá decidir con datos reales qué partes del modelo deben convertirse en un modelo canónico independiente.

## Consecuencias y deuda aceptada

- El bridge v1 todavía depende del modelo activo almacenado en OpenDSS para obtener topología y parámetros de entrada.
- No es todavía una arquitectura multi-engine completamente desacoplada.
- No admite transformadores ni múltiples niveles de tensión.
- No existe validación cruzada entre motores.
- No se implementa todavía IEC 60909 pese a que pandapower lo soporta.

Estas limitaciones son deliberadas y se consideran preferibles a introducir complejidad o datos supuestos antes de P2.

## Criterio de evolución

La siguiente ampliación de pandapower deberá ocurrir después de que P2 formalice al menos:

- datos profesionales de transformadores;
- red equivalente externa;
- metadatos de fuente para cada parámetro crítico.

Solo entonces se evaluará añadir transformadores y, posteriormente, cortocircuito IEC 60909.
