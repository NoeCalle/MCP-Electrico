# Q12A: auditoria y diagnostico industrial UNAM

Esta etapa conserva una referencia real incompleta como **incompleta**. No
cierra la calificacion de una instalacion real completa ni promueve otro modulo.
Verifica la traduccion de cuatro modelos diagnosticos declarados, derivados de
la topologia publicada, mediante OpenDSS/MCP y un oraculo AC Newton independiente.

## Fuente y alcance de la lectura

Henry Johany Garcia Arboleda, UNAM, 2017, tesina sobre ampliacion de un sistema
industrial. Se revisaron las paginas 44-54, 58-60, 65-72 y anexos C/D. El archivo
tiene 111 paginas; en esta copia el numero de pagina impreso coincide con el
indice PDF contando desde cero. Fuente:
https://tesiunamdocumentos.dgb.unam.mx/ptd2017/mayo/0759661/0759661.pdf

SHA256 del PDF revisado:
`c0a2c846f924c908cdee7ba1eee5b2583f6c57d6d38d6c3559155e39d3d9e20e`.

El repositorio conserva hechos numericos y referencias de pagina en
`examples/qualification/unam_industrial_2017.json`. No redistribuye el PDF,
sus capturas ni su texto. La procedencia del caso real es la declarada por el
autor; no se afirma haber inspeccionado o ensayado la instalacion en campo.

## Hallazgos que impiden aceptar la referencia completa

| Hallazgo | Tratamiento |
|---|---|
| CP09/CP10/CP11 tienen longitudes diferentes en unifilar y tabla D1 | Se ejecutan ambas versiones por separado; no se escoge la que mejor coincide. |
| El alimentador nuevo tiene identificadores CP02/CP08 en distintas partes | El modelo usa la aplicacion del anexo D como CP08 y conserva la discrepancia. |
| X de TR-SE-01 difiere entre tabla y figuras | Dos valores publicados generan dos versiones; se conserva su R y se calcula el uk correspondiente. |
| La tabla 6.13 rotula una suma de secuencias como Z0 | Se contrasta algebraicamente con Z0+Z1+Z2 del desarrollo; no se proyecta automaticamente a una fuente de falla. |
| El cambio de base de cables LV requiere distinguir 23 kV de 0.46 kV | Para potencia base igual, sus impedancias base difieren por 2500. El diagnostico parte de ohmios locales y tensiones nominales, no reutiliza indiscriminadamente una columna pu. |
| Las perdidas/corrientes del flujo implican resistencias diferentes a las de SC | Se calcula 3 I^2 R como comprobacion diagnostica; no se ajustan ni sustituyen entradas con esos resultados. |
| Faltan clocks, taps, excitacion y entradas exactas de ETAP | Se explicitan las convenciones del diagnostico y se bloquea la calificacion del proyecto original. |

Una discrepancia documental no demuestra por si sola que ETAP o la instalacion
esten mal. Puede representar versiones de diseno, temperaturas, paralelos,
opciones de modelado o errores de transcripcion. La auditoria conserva el
problema para su resolucion, sin atribuir una causa no demostrada.

## Cuatro diagnosticos reproducibles

El caso publicado tiene 14 etiquetas de barra. BUS-08 y BUS-09 estan unidos
por un interruptor cerrado ideal: se representan como una sola barra
equipotencial. Quedan **13 barras, cuatro transformadores, ocho lineas y cinco
cargas**; no se crea una linea de impedancia ficticia para el interruptor.
La rama abierta del grupo de emergencia queda excluida, sin inventar su modelo.

| Variante | Longitudes | Reactancia TR-SE-01 |
|---|---|---|
| `tables` | Anexo D / tabla 6.11 | Tabla 6.12 / D2 |
| `diagram_lengths` | Unifilar para CP09/10/11, por impedancia por longitud constante | Tabla |
| `figure_reactance` | Tabla | Figura 6.7 |
| `diagram_and_figure` | Unifilar para CP09/10/11 | Figura 6.7 |

Convenciones exclusivamente diagnosticas: fuente de flujo fija 23 kV/1 pu,
60 Hz; cargas trifasicas equilibradas PQ; capacitancia y excitacion excluidas
explicitamente; relacion nominal fija y grupo Dyn11. El clock no se deduce del
unifilar: por eso no se califican los angulos absolutos publicados. Las
resistencias derivadas de perdidas no se usan como entradas. Ninguna variante
se calibra con la respuesta ETAP.

Los datos originales, sin completar el grupo vectorial, fallan la admision P8B
antes de modificar el modelo. Solo se construyen las variantes que declaran
sus convenciones. Que un modelo diagnostico se pueda calcular no convierte
los supuestos en datos reales de placa.

## Pruebas y resultados

El banco contrasta cada variante con PYPOWER 5.1.21 AC Newton, construido desde
los hechos fuente. PYPOWER es una dependencia opcional de calificacion y nunca
una segunda ruta operativa. Se exigen convergencia e inventarios exactos.

Tolerancias de traduccion fijadas antes de ejecutar: 0.0002 pu, 0.05 kW/kvar
de perdidas, 0.05 A y 0.05 kW/kvar de flujo por alimentador. La comparacion con
las tablas ETAP se conserva como **diferencias diagnosticas**, sin convertirla
en una prueba aprobada de paridad. El primer modelo se reconstruye al terminar
para detectar contaminacion entre variantes.

El umbral de caida de 3% de esta demostracion es ilustrativo y explicito; no es
un criterio normativo ni de proyecto aprobado para esta instalacion.

Los trabajos `industrial-diagnostic` de Linux y Windows conservan entradas,
resultados MCP, oraculo, diferencias, admision del original, auditoria, versiones,
hashes y netlist reconstruido. La verificacion upstream comprueba el PDF entero
contra el SHA revisado; si cambia, exige revisar la transcripcion.

## Cortocircuito y protecciones

La comparacion de SC desarrollada en la tesina usa IEEE/ANSI C37 y equivalentes
de motores. No se presenta como concordancia IEC 60909. El enrutador debe
rechazar esa norma no implementada; una solicitud IEC sobre el modelo de flujo
no debe ejecutar calculos con una fuente cuasiideal ni sin los datos/revision
necesarios. Las protecciones permanecen bloqueadas sin su paquete de curvas,
ajustes y tiempos.

Sigue abierta la calificacion completa: resolver versiones, completar datos de
equipo y fuente, adoptar el metodo de SC pertinente y revisar protecciones
sobre el mismo modelo trazable. No se cambia el estado Q11 de los modulos ya
verificados ni se afirma una cobertura general del 90%.

## Reproduccion

```shell
python -m pip install -e ".[dev,qualification]"
python -m pytest tests/test_unam_industrial_diagnostic.py -q
python scripts/verify_unam_industrial_mcp.py --output outputs/unam-industrial --verify-upstream
```
