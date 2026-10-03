"""Public MCP access to isolated static and balanced RMS motor studies."""

from __future__ import annotations

from . import (
    motor_starting_dossier,
    motor_starting_intake,
    motor_starting_profiles,
    motor_starting_sequences,
    motor_starting_static,
    motor_dynamics_intake,
    motor_dynamics_qualification,
    motor_dynamics,
    motor_dynamics_dossier,
    motor_soft_starting,
    motor_soft_starting_dossier,
    soft_starter_reference,
    motor_external_reference,
    modelica_motor_adapter,
)


def register(mcp) -> None:
    @mcp.tool()
    def obtener_contrato_dinamica_modelica() -> dict:
        """Alcance experimental MSL DOL/SCR; equivalente RL y datos explícitos."""
        return {**modelica_motor_adapter.contract(), "runtime": modelica_motor_adapter.runtime()}

    @mcp.tool()
    def configurar_dinamica_modelica(ruta_omc: str, directorio_msl: str) -> dict:
        """Registra OpenModelica 1.27.1/MSL 4.0.0 ya instalados; no instala software."""
        return modelica_motor_adapter.configure(ruta_omc, directorio_msl)

    @mcp.tool()
    def validar_dinamica_modelica(paquete_estudio: dict) -> dict:
        """Comprueba red equivalente, máquinas, carga, control y criterios explícitos."""
        return modelica_motor_adapter.validate(paquete_estudio)

    @mcp.tool()
    def ejecutar_dinamica_modelica(paquete_estudio: dict, directorio_salida: str) -> dict:
        """Ejecuta componentes MSL con red común y refinamiento numérico.

        Adaptador experimental; no traduce automáticamente el unifilar OpenDSS.
        Control SCR de referencia, sin validación de un fabricante.
        """
        return modelica_motor_adapter.execute(paquete_estudio, directorio_salida)
    @mcp.tool()
    def contrastar_dinamica_con_modelica(directorio_evidencia: str) -> dict:
        """Verifica expediente y compara RMS/par/velocidad con trazas externas Modelica.

        Solo el caso sintético declarado; no ejecuta ni certifica un simulador,
        no valida el controlador real ni concede aceptación de diseño.
        """
        return motor_external_reference.compare(directorio_evidencia)

    @mcp.tool()
    def contrastar_arranque_suave(paquete_comparacion: dict) -> dict:
        """Contrasta el equivalente SCR con referencia trifásica resistiva sin neutro.

        Compara igual ángulo e igual tensión fundamental; exige tolerancias
        ilustrativas explícitas. No calcula un motor ni valida un fabricante.
        """
        return soft_starter_reference.compare(paquete_comparacion)

    @mcp.tool()
    def obtener_contrato_arranque_suave() -> dict:
        """Describe dinámica SCR/RL aproximada, datos, criterios y límites explícitos."""
        return motor_soft_starting.contract()

    @mcp.tool()
    def validar_dinamica_arranque_suave(manifest_referencia_dol: dict, paquete_dinamico: dict,
                                       opciones: dict, arrancador: dict) -> dict:
        """Valida motor a tensión plena, control y procedencia de criterios sin resolver."""
        return motor_soft_starting.readiness(manifest_referencia_dol, paquete_dinamico, opciones, arrancador)

    @mcp.tool()
    def ejecutar_dinamica_arranque_suave(manifest_referencia_dol: dict, paquete_dinamico: dict,
                                        opciones: dict, arrancador: dict) -> dict:
        """Entrada retirada: devuelve la herramienta y contrato MSL de reemplazo."""
        return motor_soft_starting.execute(manifest_referencia_dol, paquete_dinamico, opciones, arrancador)

    @mcp.tool()
    def generar_dossier_arranque_suave(manifest_referencia_dol: dict, paquete_dinamico: dict,
                                      opciones: dict, arrancador: dict,
                                      directorio_salida: str = "mcp_electrico_soft_starter_dossier") -> dict:
        """Publica gráficas, CSV, límites, replay y evidencia íntegra del arranque suave aproximado."""
        return motor_soft_starting_dossier.generate(manifest_referencia_dol, paquete_dinamico, opciones, arrancador, directorio_salida)

    @mcp.tool()
    def verificar_integridad_dossier_arranque_suave(ruta_indice: str) -> dict:
        """Verifica conjunto exacto y SHA-256 del expediente SCR/RL portable."""
        return motor_soft_starting_dossier.verify(ruta_indice)

    @mcp.tool()
    def obtener_contrato_ejecucion_dinamica_motores() -> dict:
        """Publica alcance RMS, versiones, opciones y límites de dinámica mecánica."""
        return motor_dynamics.contrato()

    @mcp.tool()
    def validar_ejecucion_dinamica_motores(manifest: dict, paquete_dinamico: dict, opciones: dict) -> dict:
        """Verifica parámetros nominales/arranque, alcance y opciones antes de resolver."""
        return motor_dynamics.readiness(manifest, paquete_dinamico, opciones)

    @mcp.tool()
    def ejecutar_dinamica_motores(manifest: dict, paquete_dinamico: dict, opciones: dict) -> dict:
        """Entrada retirada: devuelve la herramienta y contrato MSL de reemplazo."""
        return motor_dynamics.execute(manifest, paquete_dinamico, opciones)

    @mcp.tool()
    def generar_dossier_dinamica_motores(manifest: dict, paquete_dinamico: dict, opciones: dict,
                                        directorio_salida: str = "mcp_electrico_dynamic_dossier") -> dict:
        """Genera trayectorias CSV/SVG/HTML, replay exacto y expediente íntegro."""
        return motor_dynamics_dossier.generate(manifest, paquete_dinamico, opciones, directorio_salida)

    @mcp.tool()
    def verificar_integridad_dossier_dinamica_motores(ruta_indice: str) -> dict:
        """Verifica file-set exacto y SHA-256 del expediente dinámico portable."""
        return motor_dynamics_dossier.verify(ruta_indice)

    @mcp.tool()
    def obtener_contrato_dinamica_motores() -> dict:
        """Describe datos físicos y controles requeridos antes de ejecutar dinámica."""
        return motor_dynamics_intake.obtener_contrato_p13f()

    @mcp.tool()
    def validar_datos_dinamica_motores(manifest: dict, paquete_dinamico: dict) -> dict:
        """Admite datos físicos explícitos; no materializa ni integra un motor."""
        return motor_dynamics_intake.evaluar_admision_dinamica(manifest, paquete_dinamico)

    @mcp.tool()
    def obtener_plan_validacion_dinamica_motores() -> dict:
        """Devuelve referencias de calificación RMS y límites de los candidatos."""
        return motor_dynamics_qualification.obtener_plan_validacion()

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
