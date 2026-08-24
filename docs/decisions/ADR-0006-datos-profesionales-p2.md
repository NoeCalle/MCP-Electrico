# ADR-0006 — Datos profesionales P2 y proyección multi-motor

## Estado

Aceptado para P2 v1.

## Contexto

El modelo inicial de MCP Eléctrico podía crear transformadores con potencia, tensiones y conexión, dejando varios parámetros eléctricos en defaults del solver. Ese enfoque es útil para prototipos, pero insuficiente para una plataforma que pretende entregar estudios trazables. La incorporación de pandapower añade además un segundo consumidor con requisitos de datos distintos.

## Decisión 1 — El dato profesional es independiente del solver

Los datos de placa/proyecto se guardan en una estructura P2. OpenDSS y pandapower reciben proyecciones de esa estructura. Ningún objeto de solver se considera por sí mismo la fuente canónica de procedencia.

## Decisión 2 — Ausencia no significa cero

`None` / `NOT_AVAILABLE` conserva su significado de dato no suministrado. Si un solver mantiene un default porque el dato no existe, la proyección se marca incompleta y el supuesto se expone. El default no se reescribe como si fuera un dato del usuario o fabricante.

## Decisión 3 — Transformador P2 v1

Se soportan transformadores trifásicos de dos devanados con potencia/tensiones, uk%, grupo vectorial y separación R/X trazable. La separación requiere X/R o pérdidas de carga. Datos contradictorios bloquean la creación.

El reparto de R total en OpenDSS se realiza 50/50 entre devanados mientras no exista un dato explícito por devanado; esta es una regla de proyección documentada, no un dato de placa.

## Decisión 4 — pandapower no recibe ceros inventados

`create_transformer_from_parameters` requiere pérdidas de hierro y corriente de vacío. Si P0/I0 no existen, el transformador P2 puede permanecer utilizable dentro del alcance OpenDSS correspondiente, pero la proyección pandapower se rechaza con diagnóstico explícito.

## Decisión 5 — Red equivalente positiva-secuencia

P2 v1 representa máximo/mínimo mediante Scc3 y X/R. El escenario activo se proyecta a la fuente OpenDSS. Scc3 no se usa para inventar Z0; secuencia cero queda pendiente.

## Decisión 6 — QA depende del estudio

La severidad de un dato faltante depende del uso. Una carencia tolerable para flujo puede ser BLOCKER para cortocircuito, protección o Arc Flash. La madurez del algoritmo y la completitud del modelo siguen siendo controles separados.

## Decisión 7 — V2 es parte de P2

El workspace debe mostrar la procedencia y completitud de transformador/fuente. El navegador no calcula. Los mismos IDs canónicos continúan vinculando unifilar, tabla e inspector.

## Decisión 8 — No cross-check / no router automático

P2 amplía los datos compartidos por los motores, pero no introduce selección automática ni comparación OpenDSS-pandapower. Esas funciones requieren una fase específica posterior.

## Consecuencias

- modelos legados continúan disponibles, pero se identifican como incompletos P2;
- ciertos modelos antes aceptados por defaults ahora son rechazados por pandapower;
- los estudios futuros pueden elevar requisitos sin cambiar silenciosamente los datos existentes;
- P2 todavía no se considera completo hasta cubrir cables/instalaciones, secuencia cero y mayor diversidad de equipos.
