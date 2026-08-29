# P7D release checklist

Release objetivo: `MCP_ELECTRICO_0_9_ENGINEERING_PREVIEW`.

El gate se considera cerrado solo si `evaluar_cierre_p7()` devuelve todos los criterios `DONE`, `engineering_preview_ready=true`, `internal_use_ready=true` y `professional_emission=false`.

La verificación automatizada vive en `tests/test_p7d_engineering_preview.py` y el ejemplo reproducible en `examples/evaluate_p7d_engineering_preview.py`.

Reglas de producto preservadas:

- OpenDSS continúa como motor por defecto;
- `automatic_dispatch=false`;
- `crosscheck=false`;
- coordinación P5 implementada únicamente dentro del alcance P5E;
- IEEE 1584 permanece diferido;
- reporte profesional y firma profesional no implementados;
- el siguiente paso después del gate es `REAL_SUBSTATION_PILOT`.
