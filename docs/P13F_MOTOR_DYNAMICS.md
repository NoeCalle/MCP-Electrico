# P13F — Dinámica mecánica de motores con red RMS equilibrada

## Estado al 2026-09-30

**P13F1–P13F5: operativos con limitaciones explícitas.** El backend
`MCP_BALANCED_RMS_RK4_V1` integra velocidad, ángulo y energías mediante RK4.
En cada etapa resuelve una red OpenDSS aislada con el circuito equivalente
del motor a su deslizamiento actual. La parte eléctrica es cuasiestacionaria
RMS: no integra flujos magnéticos ni ondas de energización EMT.

| Paso | Estado | Evidencia |
| --- | --- | --- |
| F1 — Entradas físicas | DONE | contrato SI, procedencia, SHA y rechazo de datos incompletos |
| F2 — Calificación | DONE con límites RMS | soluciones cerradas mecánicas; KCL/KVL independiente delta/estrella; versiones fijadas |
| F3 — Red aislada | DONE | carga de marcha seleccionada retirada; I/P nativas contrastadas; padre intacto |
| F4 — Estudios | DONE | trayectorias, energía, tres mallas, objetivo inalcanzable y fallo de convergencia explícitos |
| F5 — Visual y dossier | DONE | gráficas, tabla, CSV, replay e inventario SHA-256 portátil |

La calificación cubre un motor de jaula trifásico equilibrado por estudio,
arranque directo desde reposo y curva resistente explícita. Los demás motores
permanecen como cargas de marcha declaradas. VFD, soft starter, conmutaciones,
EMT desequilibrado, saturación, temperatura variable y secuencias dinámicas
simultáneas quedan fuera del alcance de esta entrega local. Arc Flash IEEE 1584
es el bloque del roadmap expresamente aplazado por el usuario.

## Herramientas y flujo

P13 mantiene nueve herramientas estáticas y tres de preparación. La admisión
física F1 conserva `ready_for_execution=false`: requiere calibración y opciones.
Se añaden cinco herramientas:

1. `obtener_contrato_ejecucion_dinamica_motores()` publica alcance y opciones.
2. `validar_ejecucion_dinamica_motores(manifest, paquete_dinamico, opciones)`
   comprueba admisión, consistencia nominal/rotor bloqueado y entorno, sin resolver red.
3. `ejecutar_dinamica_motores(...)` calcula tres mallas, verificaciones y criterios.
4. `generar_dossier_dinamica_motores(..., directorio_salida)` ejecuta y repite
   el estudio y publica resultados numéricamente verificados.
5. `verificar_integridad_dossier_dinamica_motores(ruta_indice)` verifica archivos.

`DYNAMIC_STUDIES_COMPLETED` significa que la ejecución superó los controles
numéricos. `criterion.passed` indica por separado si el motor cumplió tensión
mínima y tiempo máximo del proyecto. Un motor bloqueado puede tener una ejecución
válida y un criterio incumplido. Un fallo numérico impide generar el dossier.
`professional_emission=false` permanece explícito.

## Datos y opciones requeridos

El paquete se vincula al manifiesto P13 mediante `project_id` y SHA-256 del JSON
canónico UTF-8 (claves ordenadas, sin NaN, separadores compactos). Requiere:

| Grupo | Datos | Unidades y alcance |
| --- | --- | --- |
| Eléctrico | Rs/Rr, Lσs/Lσr/Lm, frecuencia, pares de polos, conexión | Ω/H por fase; rotor referido al estator; resistencias a temperatura fija declarada |
| Mecánico | Jmotor/Jcarga, amortiguamiento y curva resistente | kg·m², N·m·s/rad, puntos rad/s y N·m referidos al eje; interpolación lineal sin extrapolación |
| Inicial y tiempo | reposo explícito, duración, paso y límite | energización RMS instantánea equilibrada; RK4 fijo; hasta 200000 pasos sumando las tres mallas |
| Criterios | velocidad objetivo, tiempo máximo y tensión mínima | criterios del proyecto |
| Procedencia | referencias de datos, criterios y tolerancias | no autentica fabricante ni sustituye datos ausentes |

Las opciones seleccionan backend, modelo RMS, refinamiento obligatorio y fracción
de velocidad nominal. Incluyen tolerancias de corriente/PF de arranque, potencia
nominal, desequilibrio, energía, trayectorias y tiempo de aceleración. No se ajustan
parámetros automáticamente para hacer pasar un caso. Versiones calificadas:
opendssdirect.py 0.9.4, dss-python 0.15.7 y dss-python-backend 0.14.5.

El balance incluye energía cinética, pérdidas de cobre/amortiguamiento y trabajo
resistente. No incluye almacenamiento magnético ni pérdidas de hierro/adicionales.
Velocidad inversa o síncrona, desequilibrio excesivo y valores fuera del dominio
bloquean la ejecución. Las temperaturas permanecen fijas.

## Referencia y verificación

Los archivos `examples/p13_dynamic_rms_manifest.json`,
`p13_dynamic_rms_package.json` y `p13_dynamic_rms_options.json` contienen datos
sintéticos marcados. Sus valores nominales y de arranque proceden de una
formulación independiente de admitancias; no representan fabricante. El antiguo
`p13_motor_dynamics_reference.json` sigue siendo una referencia de preparación;
su falta de calibración bloquea la ejecución.

`tests/test_p13f_rms_dynamics.py` cubre B01–B07: soluciones mecánicas cerradas,
KCL/KVL independiente, energía, refinamiento, bloqueo/fallo y replay aislado.
`tests/test_p13f_dynamic_dossier.py` comprueba portabilidad y adulteración.
La integración MCP llama las herramientas mediante clientes reales stdio/HTTP.
El caso sintético alcanza 90 % de velocidad síncrona en 1.79 s, con tensión
mínima 0.9312 pu; estos valores corresponden exclusivamente a ese ejemplo.

Las relaciones del circuito por fase, deslizamiento, potencia y par se apoyan en
[ETH Zürich — Electrical Machines: Induction Machine Theory](https://ethz.ch/content/dam/ethz/special-interest/itet/power-electronic-systems-lab/images/Education/lab-courses/electric-machines/EM3_Theory_en.pdf).
[OpenDSS IndMach012](https://dss-extensions.org/dss-format/IndMach012.html) y
[Modelica IM_SquirrelCage](https://doc.modelica.org/Modelica%204.0.0/Resources/helpWSM/Modelica/Modelica.Electrical.Machines.BasicMachines.InductionMachines.IM_SquirrelCage.html)
permanecen como candidatos sin calificar; esta implementación no ejecuta esos modelos.
