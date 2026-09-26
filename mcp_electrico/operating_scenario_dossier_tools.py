"""P12F — tools MCP para dossier reproducible de escenarios."""

from __future__ import annotations

from . import operating_scenario_dossier

SCHEMA = "MCP_ELECTRICO_P12F_MCP_SCENARIO_DOSSIER_V1"


def obtener_contrato_p12f() -> dict:
    return {
        "schema": SCHEMA,
        "tools": [
            "generar_dossier_escenarios_operativos",
            "verificar_integridad_dossier_escenarios",
        ],
        "dossier_schema": operating_scenario_dossier.SCHEMA,
        "integrity_schema": operating_scenario_dossier.INTEGRITY_SCHEMA,
        "collision_safe_output": True,
        "browser_engineering_calculation": False,
        "automatic_contingency_selection": False,
        "automatic_source_selection": False,
        "automatic_transfer": False,
        "professional_report": False,
        "professional_emission": False,
    }


def register(mcp) -> None:
    @mcp.tool()
    def generar_dossier_escenarios_operativos(
        manifest: dict,
        paquete_escenarios: dict,
        directorio_salida: str = "mcp_electrico_scenario_dossier",
    ) -> dict:
        """Genera dossier P12 reproducible desde escenarios explícitos."""
        return operating_scenario_dossier.generar_dossier(
            manifest,
            paquete_escenarios,
            directorio_salida=directorio_salida,
        )

    @mcp.tool()
    def verificar_integridad_dossier_escenarios(ruta_indice: str) -> dict:
        """Verifica SHA-256 y file-set del dossier P12."""
        return operating_scenario_dossier.verificar_integridad(ruta_indice)
