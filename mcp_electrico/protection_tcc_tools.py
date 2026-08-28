"""Tools MCP P5B para datasets y evaluación numérica TCC."""

from __future__ import annotations

from . import protection_curves


def register(mcp, on_model_change=None, on_result=None) -> None:
    def changed(action: str) -> None:
        if on_model_change is not None:
            on_model_change(action)

    def recorded(name: str, result: dict, action: str) -> dict:
        if on_result is not None:
            on_result(name, result, action)
        return result

    @mcp.tool()
    def registrar_dataset_curva_tcc_p5b(
        dataset_id: str,
        curve_id: str,
        shape: str,
        time_semantics: str,
        segments: list[dict],
        source_type: str,
        source_reference: str,
        source_url: str | None = None,
        revision: str | None = None,
        digitization_method: str | None = None,
    ) -> dict:
        """Registra puntos TCC explícitos; no digitaliza ni inventa curvas."""
        return protection_curves.registrar_dataset(
            dataset_id=dataset_id,
            curve_id=curve_id,
            shape=shape,
            time_semantics=time_semantics,
            segments=segments,
            source_type=source_type,
            source_reference=source_reference,
            source_url=source_url,
            revision=revision,
            digitization_method=digitization_method,
        )

    @mcp.tool()
    def listar_datasets_curva_tcc_p5b() -> list[dict]:
        return protection_curves.listar_datasets()

    @mcp.tool()
    def vincular_dataset_curva_tcc_p5b(dispositivo: str, dataset_id: str) -> dict:
        result = protection_curves.vincular_dataset_dispositivo(dispositivo, dataset_id)
        changed(f"vincular_dataset_curva_tcc_p5b:{dispositivo}")
        return result

    @mcp.tool()
    def evaluar_curva_tcc_p5b(dispositivo: str, current_a: float) -> dict:
        """Evalúa la curva vinculada solo dentro del dominio publicado."""
        result = protection_curves.evaluar_dispositivo(dispositivo, current_a)
        return recorded(
            "protection_tcc_evaluation",
            result,
            f"evaluar_curva_tcc_p5b:{dispositivo}",
        )

    @mcp.tool()
    def evaluar_dataset_tcc_p5b(dataset_id: str, current_a: float) -> dict:
        result = protection_curves.evaluar_dataset(dataset_id, current_a)
        return recorded(
            "protection_tcc_evaluation",
            result,
            f"evaluar_dataset_tcc_p5b:{dataset_id}",
        )
