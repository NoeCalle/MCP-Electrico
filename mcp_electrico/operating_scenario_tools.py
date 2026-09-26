"""P12D — tools MCP para escenarios operativos explícitos.

Esta capa solo expone el contrato P12 y delega validación/ejecución al módulo
operating_scenarios. No selecciona contingencias, maniobras ni cargas.
"""

from __future__ import annotations

from . import operating_scenarios

SCHEMA = "MCP_ELECTRICO_P12D_MCP_SCENARIO_ENTRYPOINT_V1"


def obtener_contrato_p12d() -> dict:
    return {
        "schema": SCHEMA,
        "engine_contract": operating_scenarios.obtener_contrato(),
        "tools": [
            "obtener_contrato_p12_escenarios_operativos",
            "validar_escenarios_operativos",
            "ejecutar_escenarios_operativos",
        ],
        "recommended_sequence": [
            "obtener_contrato_p12_escenarios_operativos",
            "validar_escenarios_operativos",
            "ejecutar_escenarios_operativos",
        ],
        "automatic_contingency_selection": False,
        "automatic_switching": False,
        "automatic_load_shedding": False,
        "automatic_retry": False,
        "crosscheck": False,
        "professional_emission": False,
    }


def register(mcp) -> None:
    @mcp.tool()
    def obtener_contrato_p12_escenarios_operativos() -> dict:
        """Devuelve alcance, acciones y fronteras fail-closed de P12."""
        return obtener_contrato_p12d()

    @mcp.tool()
    def validar_escenarios_operativos(
        manifest: dict,
        paquete_escenarios: dict,
    ) -> dict:
        """Valida escenarios explícitos sin construir ni calcular el modelo."""
        return operating_scenarios.validar_paquete(manifest, paquete_escenarios)

    @mcp.tool()
    def ejecutar_escenarios_operativos(
        manifest: dict,
        paquete_escenarios: dict,
    ) -> dict:
        """Ejecuta únicamente las maniobras/estados declarados en el paquete P12."""
        return operating_scenarios.ejecutar_paquete(manifest, paquete_escenarios)
