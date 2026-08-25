"""Tools MCP para P3 ampacidad foundation.

Las tools de este módulo no convierten tablas de fabricante en norma. Exponen
la configuración trazable Ib/In/Iz y registran resultados estructurados para
el workspace V3.
"""

from __future__ import annotations

from pathlib import Path

from . import ampacity, ampacity_norms


def _record_default(name: str, result: dict, action: str) -> None:
    """Registra el estudio y refresca el workspace sin recalcular en navegador."""
    from . import workspace, workspace_state, workspace_studies_view

    workspace_state.record_study(name, result, action=action)
    refreshed = workspace.safe_regenerate()
    if not refreshed.get("ok") or refreshed.get("skipped"):
        return
    path = Path(workspace.get_state()["config"]["ruta_salida"]).expanduser()
    if path.exists():
        workspace_studies_view.enhance_file(path, workspace_state.snapshot())


def register(mcp, on_study=None) -> None:
    def record(name: str, result: dict, action: str) -> None:
        if on_study is not None:
            on_study(name, result, action)
        else:
            _record_default(name, result, action)

    @mcp.tool()
    def listar_referencias_ampacidad() -> list[dict]:
        """Lista referencias P3 registradas sin afirmar que sus tablas estén automatizadas."""
        return ampacity_norms.listar_referencias()

    @mcp.tool()
    def obtener_estado_ampacidad() -> dict:
        """Devuelve perfiles P3 configurados y madurez de la foundation."""
        return ampacity.snapshot()

    @mcp.tool()
    def definir_condiciones_ampacidad(
        nombre_elemento: str,
        norma_id: str,
        in_proteccion_a: float,
        factores: list[dict] | None = None,
        confirmar_condiciones_base: bool = False,
        ib_diseno_a: float | None = None,
        usar_corriente_flujo_como_ib: bool = False,
        referencia_in: str | None = None,
        referencia_ib: str | None = None,
        referencia_condiciones_instalacion: str | None = None,
    ) -> dict:
        """Configura Ib/In/Iz con referencias explícitas; no asume factores ni In."""
        result = ampacity.definir_condiciones(
            nombre_elemento=nombre_elemento,
            norma_id=norma_id,
            in_proteccion_a=in_proteccion_a,
            factores=factores,
            confirmar_condiciones_base=confirmar_condiciones_base,
            ib_diseno_a=ib_diseno_a,
            usar_corriente_flujo_como_ib=usar_corriente_flujo_como_ib,
            referencia_in=referencia_in,
            referencia_ib=referencia_ib,
            referencia_condiciones_instalacion=referencia_condiciones_instalacion,
        )
        record("ampacity_config", ampacity.snapshot(), f"definir_condiciones_ampacidad:{nombre_elemento}")
        return result

    @mcp.tool()
    def evaluar_ampacidad(nombre_elemento: str | None = None) -> dict:
        """Evalúa Ib <= In <= Iz para un alimentador o todos los perfiles configurados."""
        result = ampacity.evaluar(nombre_elemento) if nombre_elemento else ampacity.evaluar_todos()
        payload = result if not nombre_elemento else {
            "study": "ampacity",
            "status": result.get("status"),
            "criterion": "Ib <= In <= Iz",
            "alimentadores": [result],
            "summary": {
                "total": 1,
                "cumple": int(result.get("status") == "CUMPLE"),
                "no_cumple": int(result.get("status") == "NO_CUMPLE"),
                "datos_insuficientes": int(result.get("status") == "DATOS_INSUFICIENTES"),
            },
            "maturity": "UNDER_VALIDATION",
            "automatic_normative_lookup": False,
        }
        record("ampacity", payload, f"evaluar_ampacidad:{nombre_elemento or 'todos'}")
        return result
