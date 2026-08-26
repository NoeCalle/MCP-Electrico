# Health check rápido — P3-v1

Después de instalar dependencias, puede comprobarse el cierre del gate P3 sin construir todavía un modelo:

```bash
python -c "from mcp_electrico import p3_completion; g=p3_completion.evaluar_cierre_p3(); print(g['phase_status'], g['next_phase'])"
```

Resultado esperado de la versión P3-v1:

```text
READY_WITH_LIMITATIONS P4_IEC_60909
```

Esta comprobación valida el estado del producto, no la aptitud de un modelo concreto. `professional_emission` permanece `false` y cada proyecto debe superar su propio readiness, evidencia normativa, QA y revisión profesional.

También puede consultarse la madurez declarada de ampacidad:

```bash
python -c "from mcp_electrico import validation_status; print(validation_status.get_module_status('ampacity')['status'])"
```

Resultado esperado:

```text
VALIDATED_WITH_LIMITATIONS
```

El cierre P3 no convierte `OpenDSS FaultStudy` en IEC 60909. El módulo `short_circuit` sigue `UNDER_VALIDATION` hasta completar P4.
