"""Tools MCP operativas para el flujo real P8.

Estas entradas no introducen un dispatcher nuevo: delegan en los contratos P8
ya validados y conservan sus políticas fail-closed. OpenDSS sigue siendo el
motor P1, pandapower se invoca explícitamente por P4 y P5 consume bindings de
falla declarados por el manifiesto.
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from . import (
    real_integrated_readiness,
    real_project_dossier,
    real_protection_execution,
    workspace,
    workspace_state,
    workspace_v5,
)


def _refresh_workspace_v5() -> dict[str, Any]:
    """Regenera la vista del estado ya calculado; nunca recalcula ingeniería."""
    base = workspace.regenerate()
    if not base.get("ok"):
        return base
    state = workspace.get_state()
    path = Path(state["config"]["ruta_salida"]).expanduser()
    if not path.is_file():
        return {**base, "study_views": {"ok": False, "reason": "workspace HTML no encontrado"}}
    return {
        **base,
        "study_views": workspace_v5.enhance_file(path, workspace_state.snapshot()),
    }


def evaluar_readiness(manifest: dict[str, Any]) -> dict[str, Any]:
    """Materializa el manifiesto real y evalúa readiness P1/P3/P4/P5 sin estudios."""
    return real_integrated_readiness.evaluar_readiness_integral(deepcopy(manifest))


def ejecutar_controlado(manifest: dict[str, Any]) -> dict[str, Any]:
    """Ejecuta P1/P3/P4/P5 con binding explícito y refresca Workspace V5 cuando procede."""
    result = real_protection_execution.ejecutar_protecciones(deepcopy(manifest))
    enriched = deepcopy(result)
    should_refresh = bool(result.get("electrical_calculation_performed")) or result.get(
        "execution_status"
    ) in {
        real_protection_execution.STATUS_COMPLETED,
        real_protection_execution.STATUS_PARTIAL,
    }
    enriched["workspace_view"] = _refresh_workspace_v5() if should_refresh else {
        "ok": True,
        "skipped": True,
        "reason": "ejecución bloqueada antes de producir resultados eléctricos",
    }
    return enriched


def generar_dossier(
    manifest: dict[str, Any],
    directorio_salida: str = "mcp_electrico_real_dossier",
) -> dict[str, Any]:
    """Genera Workspace V5 + P7A/P7B/P7C del proyecto real en un directorio trazable."""
    return real_project_dossier.generar_dossier(
        deepcopy(manifest),
        directorio_salida=directorio_salida,
    )


def register(mcp) -> None:
    """Registra las tres entradas operativas P8 en el servidor MCP existente."""

    @mcp.tool()
    def evaluar_readiness_proyecto_real(manifest: dict) -> dict:
        """Materializa un manifiesto real y valida readiness integral sin ejecutar estudios.

        Puede reconstruir el modelo activo como parte del contrato P8C, pero no
        ejecuta flujo, ampacidad, cortocircuito ni protección.
        """
        return evaluar_readiness(manifest)

    @mcp.tool()
    def ejecutar_proyecto_real_controlado(manifest: dict) -> dict:
        """Ejecuta de forma fail-closed P1/P3/P4/P5 y actualiza el mismo Workspace V5.

        El manifiesto debe incluir bindings P5 explícitos por dispositivo. No hay
        dispatch automático, selección silenciosa de falla ni cross-check.
        """
        return ejecutar_controlado(manifest)

    @mcp.tool()
    def generar_dossier_proyecto_real(
        manifest: dict,
        directorio_salida: str = "mcp_electrico_real_dossier",
    ) -> dict:
        """Ejecuta el proyecto real y genera Workspace V5, P7A, P7B aislado y P7C."""
        return generar_dossier(manifest, directorio_salida)
