"""Public MCP access to the existing, isolated P13 static motor studies."""

from __future__ import annotations

from . import (
    motor_starting_dossier,
    motor_starting_intake,
    motor_starting_profiles,
    motor_starting_sequences,
    motor_starting_static,
)


def register(mcp) -> None:
    @mcp.tool()
    def obtener_contrato_arranque_motores() -> dict:
        """Devuelve contratos de arranque estático, perfiles y secuencias P13."""
        return {
            "schema": "MCP_ELECTRICO_P13_MCP_ENTRYPOINT_V1",
            "static": motor_starting_intake.obtener_contrato_p13a(),
            "profiles": motor_starting_profiles.obtener_contrato_p13c(),
            "sequences": motor_starting_sequences.obtener_contrato_p13d(),
            "dynamic_integration_performed": False,
            "professional_emission": False,
        }

    @mcp.tool()
    def validar_arranque_motores(manifest: dict) -> dict:
        """Evalúa admisión y preparación P13 sin resolver la red."""
        return motor_starting_static.evaluar_readiness(manifest)

    @mcp.tool()
    def ejecutar_arranque_motores(manifest: dict) -> dict:
        """Ejecuta estudios estáticos explícitos en contextos OpenDSS aislados."""
        return motor_starting_static.ejecutar_estudios(manifest)

    @mcp.tool()
    def validar_perfiles_arranque_motores(manifest: dict, paquete_perfiles: dict) -> dict:
        """Valida los puntos de perfil declarados sin ejecutar estudios."""
        return motor_starting_profiles.validar_perfiles(manifest, paquete_perfiles)

    @mcp.tool()
    def ejecutar_perfiles_arranque_motores(manifest: dict, paquete_perfiles: dict) -> dict:
        """Resuelve únicamente los puntos explícitos de los perfiles P13C."""
        return motor_starting_profiles.ejecutar_perfiles(manifest, paquete_perfiles)

    @mcp.tool()
    def validar_secuencias_arranque_motores(
        manifest: dict, paquete_perfiles: dict, paquete_secuencias: dict,
    ) -> dict:
        """Valida secuencias multi-motor sin inferir orden ni tiempos."""
        return motor_starting_sequences.validar_secuencias(
            manifest, paquete_perfiles, paquete_secuencias,
        )

    @mcp.tool()
    def ejecutar_secuencias_arranque_motores(
        manifest: dict, paquete_perfiles: dict, paquete_secuencias: dict,
    ) -> dict:
        """Ejecuta las secuencias estáticas declaradas en contextos aislados."""
        return motor_starting_sequences.ejecutar_secuencias(
            manifest, paquete_perfiles, paquete_secuencias,
        )

    @mcp.tool()
    def generar_dossier_arranque_motores(
        manifest: dict, paquete_perfiles: dict, paquete_secuencias: dict,
        directorio_salida: str = "mcp_electrico_motor_dossier",
    ) -> dict:
        """Genera Workspace y dossier P13 con replay e integridad SHA-256."""
        return motor_starting_dossier.generar_dossier(
            manifest, paquete_perfiles, paquete_secuencias, directorio_salida,
        )

    @mcp.tool()
    def verificar_integridad_dossier_arranque_motores(ruta_indice: str) -> dict:
        """Verifica el inventario y los hashes del dossier P13."""
        return motor_starting_dossier.verificar_integridad(ruta_indice)
