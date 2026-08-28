"""Tools MCP públicas para IEC 60909 P4 que requieren integración con Workspace V4."""

from __future__ import annotations

from pathlib import Path

from . import (
    iec60909_single_phase_ground_suite,
    iec60909_two_phase_ground_suite,
    workspace,
    workspace_state,
    workspace_v4,
)


def _regenerate_workspace() -> dict:
    """Regenera el workspace y aplica V4 sin alterar la revisión del modelo."""
    result = workspace.safe_regenerate()
    if not result.get("ok") or result.get("skipped"):
        return result

    state = workspace.get_state()
    path = Path(state["config"]["ruta_salida"]).expanduser()
    if not path.exists():
        return {
            **result,
            "study_views": {
                "ok": True,
                "skipped": True,
                "reason": "workspace aún no generado",
            },
        }

    result["study_views"] = workspace_v4.enhance_file(
        path, workspace_state.snapshot()
    )
    return result


def ejecutar_cortocircuito_iec60909_1ph_ground(
    bus_falla: str,
    line_endtemp_degree_c: dict[str, float] | None = None,
    lv_tol_percent: int = 10,
) -> dict:
    """Ejecuta IEC 60909 1F-T MAX/MIN con Z0 explícita y registra V4.

    No hay despacho automático ni cross-check. La secuencia cero de fuente,
    líneas y transformadores debe estar declarada y proyectable; MIN exige
    ``endtemp_degree`` explícita por línea. Sk'', ip e Ith no se derivan ni se
    promocionan para 1F-T en P4C11C. La emisión profesional permanece
    deshabilitada.
    """
    result = iec60909_single_phase_ground_suite.ejecutar_1ph_ground_max_min(
        bus=bus_falla,
        line_endtemp_degree_c=line_endtemp_degree_c,
        lv_tol_percent=lv_tol_percent,
    )
    workspace_state.record_study(
        "iec60909_1ph_ground",
        result,
        action="ejecutar_cortocircuito_iec60909_1ph_ground",
    )
    _regenerate_workspace()
    return result


def ejecutar_cortocircuito_iec60909_2ph_ground(
    bus_falla: str,
    line_endtemp_degree_c: dict[str, float] | None = None,
    lv_tol_percent: int = 10,
) -> dict:
    """Ejecuta la extensión operacional 2F-T MAX/MIN y registra V4.

    Pandapower se usa exclusivamente para obtener Z1/Z0 del mismo modelo P4;
    la falla franca b-c-tierra se resuelve con el solver MCP de componentes
    simétricas auditado. ``results.ikss_ka`` representa la mayor corriente RMS
    de las fases en falla para uso técnico interno; ``ikss_contractual`` sigue
    siendo False hasta cerrar las validaciones normativas pendientes.
    """
    result = iec60909_two_phase_ground_suite.ejecutar_2ph_ground_max_min(
        bus=bus_falla,
        line_endtemp_degree_c=line_endtemp_degree_c,
        lv_tol_percent=lv_tol_percent,
    )
    workspace_state.record_study(
        "iec60909_2ph_ground",
        result,
        action="ejecutar_cortocircuito_iec60909_2ph_ground",
    )
    _regenerate_workspace()
    return result


def register(mcp) -> None:
    mcp.tool()(ejecutar_cortocircuito_iec60909_1ph_ground)
    mcp.tool()(ejecutar_cortocircuito_iec60909_2ph_ground)
