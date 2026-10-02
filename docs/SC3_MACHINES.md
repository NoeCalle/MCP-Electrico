# Máquinas y corrientes por rama en cortocircuito trifásico

## Alcance implementado

La proyección 3F de pandapower 3.5.4 incorpora **motores de inducción de
conexión directa** y **generadores síncronos**, mediante fichas explícitas.
Calcula corriente RMS simétrica inicial `Ik''`, `Sk''`, Rk/Xk y corrientes
iniciales en ambos extremos de líneas y transformadores para una barra de
falla concreta. No transforma ese resultado en aprobación de protecciones.

El modelo de operación OpenDSS no se cambia al registrar las fichas SC.
La proyección de máquinas se utiliza exclusivamente en el cálculo 3F.
El flujo OpenDSS continúa disponible. El puente de flujo pandapower y las
otras fallas bloquean fichas SC de máquinas para evitar omisiones silenciosas;
su ampliación requiere validación propia.

## Herramientas MCP

| Herramienta | Entradas / comportamiento |
| --- | --- |
| `definir_motor_cortocircuito_3ph` | `Load.nombre`, potencia **mecánica nominal** MW, kV nominal, eficiencia y fp nominales, corriente de rotor bloqueado en pu de corriente nominal, R/X y referencia |
| `clasificar_carga_cortocircuito_3ph` | `ESTATICA` o `VARIADOR_NO_MODELADO`, con referencia; los variadores activos bloquean cálculo |
| `definir_generador_cortocircuito_3ph` | `Vsource.source` o `Generator.nombre`, MVA/kV nominales, Xd'' pu sobre la base propia, R'' ohm, fp nominal, pg% y referencia |
| `obtener_fichas_maquinas_cortocircuito_3ph` | Fichas, estado enabled/open/barra real, cargas sin clasificar y faltantes; no resuelve |
| `eliminar_ficha_maquina_cortocircuito_3ph` | Retira una ficha/clasificación e invalida la revisión y resultados anteriores |

Una ficha de motor representa el motor identificado en esa carga, o un
equivalente agregado **justificado explícitamente por su referencia**.
Los MW/fp de un proceso no justifican por sí solos una ficha equivalente.
Desagregar las cargas y registrar los motores reales cuando sus parámetros
o conexiones son diferentes. El consumo eléctrico de `Load` se conserva;
no se añade demanda ni se interpreta su kW como potencia mecánica nominal.

## Proyección y fórmulas

Para inducción directa:

```
Sn_motor = Pn_mecánica / ((ηn/100) × fpn)
|Zm| = Vn² / (Sn_motor × Irotor_bloqueado_pu)
Xm = |Zm| / sqrt(1 + (R/X)²)
Rm = (R/X) × Xm
```

La ficha se proyecta a `net.motor` con todos los parámetros de cortocircuito.
**MAX incluye** el aporte de los motores disponibles y conectados.
**MIN excluye** motores de inducción según la política implementada por el
backend IEC. Esta diferencia es explícita en cada resultado; MIN no representa
la corriente instantánea real de todos los motores durante una falla.

Para generador síncrono:

```
X''_ohm = xdss_pu × Vn_gen² / Sn_gen
Zg = R''_ohm + j X''_ohm
Zg_corregida = Kg × Zg
```

`net.gen` aplica K_G. Si se declara unidad generador–transformador, se aplican
K_S (OLTC) o K_SO (sin OLTC), en lugar de corregir por separado el transformador
como un transformador de red ordinario. La unidad exige el ID de transformador
P2, LV en la misma barra del generador, `oltc` booleano y `pt_percent` explícito.
`pg_percent` también es explícito: declarar cero requiere una justificación.
Las fichas deben corresponder al nivel nominal de la barra; esta versión no
acepta una diferencia de tensión nominal de máquina sin validación adicional.

Una ficha síncrona en `Vsource.source` **sustituye** el `ext_grid` de esa fuente.
Los antiguos Scc MAX/MIN P2 no aportan corriente adicional ni sustituyen Xd''.
Una ficha en un `Generator` existente añade su contribución al sistema con
su estado actual. No se admite más de un generador síncrono por barra en este
alcance, debido a la estructura de correcciones del backend.

## Control previo obligatorio

1. Registrar topología, líneas/cables, transformadores, fuentes y cargas.
2. Clasificar las cargas y aportar las fichas de máquinas. Al usar esta
   extensión se exige una decisión explícita para **todas** las cargas.
3. Ejecutar `evaluar_preparacion_cortocircuito_3ph` con barra, temperaturas
   de MIN y parámetros del estudio. Revisar faltantes, fuentes sin traducción,
   variadores, fichas huérfanas y conexiones. Una barra aislada de fuentes
   disponibles se bloquea antes del cálculo.
4. Comunicar los supuestos propuestos al usuario y obtener su aceptación
   antes de ejecutar un caso real. No inventar datos para superar el control.
5. Pasar `revision_modelo` con el SHA y el alcance que devuelve el control:
   `APORTE_FUENTES_Y_MAQUINAS_DECLARADAS`, calidad, referencia de revisión,
   lista de supuestos aceptados y todos los ítems revisados.
6. Ejecutar MAX/MIN. Cambios de fichas, enabled/open, conexiones, barra de
   falla o solicitud invalidan la revisión. Cambiar una ficha mediante MCP
   invalida los estudios registrados.

El modo anterior sin fichas se conserva como `APORTE_FUENTES_EQUIVALENTES`:
su revisión debe aceptar expresamente el modelo parcial. No se considera un
modelo completo porque el solver haya convergido. El MCP no puede descubrir
un motor/cable omitido de un plano que no fue incorporado al modelo.

## Resultados y límites

`branch_results.lines` publica `ikss_from_ka` / `ikss_to_ka`;
`branch_results.transformers` publica `ikss_hv_ka` / `ikss_lv_ka`.
Estas corrientes pueden diferir de la corriente total en la barra de falla
por aportes locales y por relación de transformación. Un extremo sin dato
finito se muestra como no disponible, sin rellenarlo con una corriente ficticia.
El workspace muestra la tabla de ramas y el alcance de máquinas declarado.

Pendientes deliberados:

- Variadores/convertidores: requieren modelo y datos propios del fabricante;
  no se tratan como motores directos ni se les asigna aporte cero.
- Decaimiento, corriente de corte Ib y corriente permanente Ik.
- ip/Ith **con máquinas**: ejecución bloqueada hasta validar el decaimiento;
  la capacidad anterior de ip/Ith sin máquinas permanece separada.
- Despacho/régimen de operación de generador, capacidad de MW/Mvar y dinámica:
  no se deducen de un estudio de corriente inicial de falla.
- Validación de Icu/Ics/Icw, I²t del cable, CT, ajustes, tiempos y selectividad:
  requiere sus datos y estudios. `protection_validation_supported=false`.
- Conformidad integral con una edición de IEC 60909: no se afirma.

Las fichas se incluyen en el hash del proyecto y en el snapshot exportado.
Como los demás datos profesionales P2, la reconstrucción P7B requiere un
**rebind explícito**; no promueve las fichas guardadas a vigentes. Crear un
circuito nuevo, incluso con el mismo nombre, limpia las fichas anteriores.

## Verificación independiente

`tests/test_sc_machines.py` verifica los resultados usando impedancias
complejas calculadas fuera del backend: paralelos fuente–motor y
fuente–generador, generador aislado K_G, unidad generador–transformador con
y sin OLTC, falla remota con cable y corrientes en ambos extremos.
Incluye 50/60 Hz, MIN sin inducción, equipos abiertos/deshabilitados,
clasificaciones faltantes, variadores, SHA obsoleto, límites de datos,
snapshot/reinicio y bloqueo de otras fallas.

`examples/validate_sc_machines_mcp.py --output-dir <directorio>` ejecuta
herramientas públicas mediante **MCP stdio**, comprueba catálogo, bloqueo sin
revisión y cuatro referencias MAX/MIN independientes. Sus entradas son
sintéticas para validar software, no supuestos aprobados de un proyecto real.

Referencias primarias del backend (las ecuaciones efectivas se verifican
también contra el código instalado 3.5.4, no solamente una página `latest`):

- [Ficha de motor](https://pandapower.readthedocs.io/en/v3.5.1/elements/motor.html).
- [Ficha de generador](https://pandapower.readthedocs.io/en/stable/elements/gen.html).
- [Cálculo y unidades generador–transformador](https://pandapower.readthedocs.io/en/stable/shortcircuit/run.html).
- Código 3.5.4: `build_bus._add_motor_impedances_ppc` y
  `shortcircuit.ppc_conversion._add_gen_sc_z_kg_ks`.
