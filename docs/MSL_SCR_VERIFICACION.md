# Arranque suave SCR: ejecución experimental con MSL

## Confiabilidad técnica y responsabilidad del ingeniero — Q3

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

## Cierre vigente de módulos — Q2, 4 de octubre de 2026

Consultar el [registro de cierre](ESTADO_CIERRE_MODULOS.md): estados, alcance, evidencia y condiciones finitas pendientes. La integración verificada, los datos del proyecto, los criterios de diseño, la conformidad normativa y la aprobación del informe se evalúan por separado.

**Actualización Q2 (4 de octubre):** DOL01–DOL03 están cerrados por contraste con el ejemplo original MSL y regresión MCP; ver [evidencia DOL](MSL_DOL_VERIFICACION.md). La prioridad pasa a SCR01–SCR03. Bancos estáticos, P5 y P7 conservan sus cierres por alcance. Arc Flash sigue diferido.


Actualizado: 4 de octubre de 2026.

## Qué se cerró

`ejecutar_dinamica_modelica` ejecuta una máquina delta, red trifásica equilibrada
con equivalente RL declarado, componentes MSL de conmutación, controlador
`SoftStartControl`, realimentación de corriente y bypass automático.
El MCP admite entradas, conecta componentes, invoca OpenModelica y procesa las
trazas. No contiene un nuevo modelo físico del arrancador ni integra la máquina.

La ejecución anterior se cerraba con el solucionador algebraico seleccionado
automáticamente. El perfil comprobado usa DASSL y `-nls=newton`. Este solucionador
de OpenModelica está documentado como **prototipo**. SCR conserva su condición
de verificación pendiente porque aún faltan evidencias SCR01–SCR03, no por esa
palabra aislada. Las alternativas que no completaron las pruebas tampoco se
habilitan como reemplazo ni fallback automático.

El procesamiento RMS conserva los estados de ambos lados de las conmutaciones;
integra las trazas lineales por tramos, sin difuminar los saltos sobre una
cuadrícula arbitraria. Una traza incompleta se rechaza.

## Pruebas reales mediante MCP

`scripts/verify_msl_scr_mcp.py` hace once llamadas MCP stdio y ejecuta tres
casos sintéticos. Cada caso se ejecuta con tolerancia y paso nominales y
refinados. Todos los controles numéricos aprobaron.

La regresión Q3 añade una interrupción deliberada de compilación por tiempo
límite. El MCP debe devolver `failure_kind=TIMEOUT`, la etapa, los logs y
`design_assessment=NOT_EVALUATED`, sin resultados eléctricos. Una traza parcial
se conserva como diagnóstico y no se publica como estudio calculado.

## Investigación del perfil numérico — Q3

`scripts/verify_msl_scr_solver_profiles.py` prueba perfiles nativos sobre un caso
compilado mediante MCP. Antes de ejecutar verifica que el `.mo` coincide con el
adaptador vigente, registra hashes, ventanas y criterios; copia el ejecutable
y sus dependencias a directorios aislados. No cambia MSL, las entradas ni la
calificación del módulo y no instala un fallback automático.

KINSOL completa la ventana de 0,2 s. En la ventana de 5 s, el cierre del bypass
ocurre cerca de 4,212835 s y la ejecución termina por un fallo algebraico cerca
de 4,212875 s. Esto identifica una dificultad numérica de la combinación de
eventos/componentes con ese perfil; no demuestra un defecto de la red. En el
caso sin aceleración ni cierre de bypass, KINSOL sí completó ambas resoluciones;
los errores de corriente y tensión terminal fueron 1,82e-6 relativos y
0,000134 pu absolutos.

Los ensayos acotados de `mixed` y `homotopy` no completaron la ventana de 5 s
en 90 s de ejecución. Inhibir el disparo después del bypass en una copia de
pruebas tampoco resolvió la dificultad. Esa variante no se incorporó al MCP.
La regresión operacional conserva DASSL/Newton y completa los tres casos con
refinamiento; la calificación SCR01–SCR03 continúa pendiente por motivos técnicos.

La palabra *prototipo* en la documentación del solver es un dato de procedencia,
no una prueba de error. Para cerrar SCR01 faltan robustez demostrada en el rango
declarado y una justificación cuantitativa del perfil elegido o su sustitución.
SCR02 exige el contraste del circuito/control completo con la referencia MSL
original; SCR03 exige comprobar la referencia de disparo. Estas son pruebas
técnicas de la herramienta que se realizan para cerrar cada integración.

Reproducción del diagnóstico de KINSOL después de la regresión MCP:

```powershell
.venv/Scripts/python.exe scripts/verify_msl_scr_solver_profiles.py `
  --reference ../Confiabilidad-SCR-MCP/Regresion-MCP/scr `
  --output ../Confiabilidad-SCR-MCP/Perfiles-numericos-nuevos `
  --solvers kinsol --timeout 90
```

### Regresión operativa con el perfil vigente

| Caso | Resultado mecánico | Bypass, tiempo absoluto | Tensión mínima barra | Tensión mínima terminal |
|---|---|---|---|---|
| 60 Hz, ángulo fuente +15° | 90 % de velocidad síncrona en 3,728814 s desde el arranque | 4,212835 s | 0,855537 pu | 0,356260 pu |
| Inercia sintética enorme, observación de 0,95 s desde arranque | No alcanza el objetivo dentro de la ventana | No cierra | 0,863048 pu | 0,356261 pu |
| 50 Hz, ángulo fuente −27° | 90 % de velocidad síncrona en 2,459408 s desde el arranque | 3,081998 s | 0,860609 pu | 0,340225 pu |

Estos mínimos pueden ocurrir en instantes diferentes. El SCR reduce la tensión
del motor intencionalmente; la tensión de terminal no equivale a la tensión de
barra ni a una caída atribuible únicamente a la red.

Los casos usan paso de salida/interno máximo de 12,5 µs y tolerancia 1e-7;
el refinamiento usa 6,25 µs y 1e-8. Las diferencias de tensión terminal están
por debajo de 0,000159 pu (criterio declarado: 0,001 pu). También se verifican
corriente RMS, velocidad, par medio, aceleración y tiempo de bypass con las
tolerancias explícitas de cada paquete.

La rampa se detiene por la realimentación de corriente y después continúa;
no se reprodujo una señal de control impuesta. El bypass exige referencia de
tensión completa, umbral de velocidad y tiempo de permanencia.
La consigna de 2,5 pu **no garantiza un techo de corriente**: el primer caso
alcanza 2,542151 pu RMS por ciclo. MSL detiene la rampa; no implementa el control
de un fabricante ni limita toda sobrecorriente instantánea.

Los tres casos rechazan el criterio ilustrativo de tensión terminal mínima
de 0,70 pu. Ese criterio se conserva deliberadamente para verificar que el
éxito numérico no se convierta en aprobación del diseño. No es un mínimo
normativo ni un criterio de aceptación industrial del arrancador.

## Referencia independiente del componente

`scripts/verify_msl_triac_reference.py` ejecuta los mismos componentes abiertos
de conmutación/disparo sobre tres cargas resistivas independientes con neutro,
sin máquina. Para 100 V RMS de fuente y disparo de 60°:

`Vrms = V * sqrt(1 - alpha/pi + sin(2*alpha)/(2*pi))`

El valor de referencia es 89,693862 V. MSL produce aproximadamente 89,693723 V
en la ejecución nominal y 89,693802 V en la refinada. El error relativo máximo
refinado es 6,66e-7. La fórmula sólo es un oráculo de pruebas; no calcula un
motor ni valida el controlador de red cerrada por sí sola.

## Alcance que permanece pendiente

- Máquina en estrella y varias máquinas cuando alguna usa SCR: bloqueadas.
- Validación de un arrancador/control real de fabricante y datos de la bomba.
- Traducción automática del unifilar completo, cargas de potencia constante,
  pérdidas térmicas, saturación y variadores.
- Sincronización con tensión distorsionada de barra: el disparo actual usa la
  referencia sinusoidal de la fuente aguas arriba, indicada en el contrato.
- Contraste técnico del circuito/control completo y robustez numérica: pendientes.

Los ejemplos no representan las bombas M1/M2 del usuario. Los solucionadores
propios retirados siguen bloqueados. El selector general recomienda MSL pero
no convierte un pedido genérico en una ejecución sin el paquete admitido.

## Fuentes y reproducción

- [Componentes y ejemplo MSL 4.0.0](https://doc.modelica.org/Modelica%204.0.0/Resources/helpWSM/Modelica/Modelica.Electrical.PowerConverters.Examples.ACAC.SoftStarter.html).
- [Opciones de ejecución de OpenModelica](https://openmodelica.org/doc/OpenModelicaUsersGuide/latest/simulationflags.html): revisar también la ayuda del ejecutable 1.27.1 fijado; la documentación web puede describir versiones posteriores.
- Bibliotecas MSL y compilador instalados se verifican mediante hashes; no se
  modificaron sus fuentes para obtener los resultados.

La CI ordinaria comprueba contratos y admisión mediante MCP. Las simulaciones
físicas requieren el runtime local y son evidencia separada, no ejecuciones
físicas de la CI ordinaria.
