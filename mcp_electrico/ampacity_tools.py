"""Tools MCP para P3/P3A/P3B ampacidad.

Las tools de este módulo no convierten tablas de fabricante en norma. Exponen
la configuración trazable Ib/In/Iz, el router P3A, datasets P3B y el gate de
evidencia primaria. No existe una tool que promueva automáticamente datasets.
"""

from __future__ import annotations

from pathlib import Path

from . import (
    ampacity,
    ampacity_datasets,
    ampacity_evidence,
    ampacity_norms,
    ampacity_profiles,
)


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
    def listar_perfiles_normativos_ampacidad() -> list[dict]:
        """Lista perfiles P3A y su madurez de routing/tablas."""
        return ampacity_profiles.listar_perfiles()

    @mcp.tool()
    def listar_datasets_numericos_ampacidad() -> list[dict]:
        """Lista datasets P3B con procedencia y política de uso visibles."""
        return ampacity_datasets.listar_datasets()

    @mcp.tool()
    def listar_fuentes_primarias_ampacidad() -> list[dict]:
        """Lista fuentes oficiales candidatas y su estado de pin/hash."""
        return ampacity_evidence.listar_fuentes()

    @mcp.tool()
    def verificar_archivo_fuente_ampacidad(source_id: str, ruta_archivo: str) -> dict:
        """Calcula SHA-256 de una copia local de fuente; no verifica tablas ni promueve datasets."""
        return ampacity_evidence.verificar_archivo(source_id, ruta_archivo)

    @mcp.tool()
    def construir_evidencia_primaria_ampacidad(
        source_id: str,
        ruta_archivo: str,
        tablas_verificadas: list[str],
        referencias_pagina: list[str],
        revisor: str,
        comparacion_manual_confirmada: bool,
        notas: str | None = None,
    ) -> dict:
        """Hashea el PDF local y construye un paquete de evidencia para revisión por PR."""
        file_evidence = ampacity_evidence.verificar_archivo(source_id, ruta_archivo)
        return ampacity_evidence.construir_paquete_evidencia(
            source_id=source_id,
            file_evidence=file_evidence,
            tables_checked=tablas_verificadas,
            page_references=referencias_pagina,
            reviewer=revisor,
            manual_comparison_confirmed=comparacion_manual_confirmada,
            notes=notas,
        )

    @mcp.tool()
    def evaluar_promocion_dataset_ampacidad(dataset_id: str, evidencia: dict) -> dict:
        """Evalúa si la evidencia permite proponer una nueva revisión PRIMARY_VERIFIED.

        Nunca modifica el dataset existente ni habilita emisión por sí sola.
        """
        return ampacity_evidence.evaluar_promocion_dataset(dataset_id, evidencia)

    @mcp.tool()
    def resolver_factor_agrupamiento_ampacidad(
        nombre_elemento: str,
        circuitos_agrupados: int,
        disposicion_id: str,
        permitir_dataset_secundario: bool = False,
    ) -> dict:
        """Resuelve factor de agrupamiento P3B para el routing P3A vinculado.

        Por defecto no devuelve valores de transcripciones secundarias. El opt-in
        explícito permite usarlas únicamente para desarrollo/benchmark y el
        resultado conserva ``professional_emission=false``.
        """
        route = ampacity.obtener_aplicabilidad_normativa(nombre_elemento)
        if not route:
            raise ValueError("P3B010: el alimentador no tiene routing P3A vinculado")
        result = ampacity_datasets.resolver_grouping_for_route(
            route=route,
            circuits_grouped=circuitos_agrupados,
            arrangement_id=disposicion_id,
            allow_secondary=permitir_dataset_secundario,
        )
        record(
            "ampacity_numeric_lookup",
            result,
            f"resolver_factor_agrupamiento_ampacidad:{nombre_elemento}",
        )
        return result

    @mcp.tool()
    def definir_aplicabilidad_normativa_ampacidad(
        nombre_elemento: str,
        perfil_normativo_id: str,
        metodo_instalacion: str,
        ambiente: str | None = None,
        temperatura_ambiente_c: float | None = None,
        resistividad_termica_suelo_k_m_w: float | None = None,
        circuitos_agrupados: int = 1,
        disposicion_agrupamiento: str | None = None,
        numero_tramos: int = 1,
        transicion_tramos: str | None = None,
        solicitar_excepcion_tramo_corto: bool = False,
    ) -> dict:
        """Identifica tabla base/ejes CNE o limitación IEC sin devolver factores no cargados."""
        result = ampacity.definir_aplicabilidad_normativa(
            nombre_elemento=nombre_elemento,
            perfil_normativo_id=perfil_normativo_id,
            metodo_instalacion=metodo_instalacion,
            ambiente=ambiente,
            temperatura_ambiente_c=temperatura_ambiente_c,
            resistividad_termica_suelo_k_m_w=resistividad_termica_suelo_k_m_w,
            circuitos_agrupados=circuitos_agrupados,
            disposicion_agrupamiento=disposicion_agrupamiento,
            numero_tramos=numero_tramos,
            transicion_tramos=transicion_tramos,
            solicitar_excepcion_tramo_corto=solicitar_excepcion_tramo_corto,
        )
        record(
            "ampacity_normative_applicability",
            ampacity.snapshot(),
            f"definir_aplicabilidad_normativa_ampacidad:{nombre_elemento}",
        )
        return result

    @mcp.tool()
    def obtener_estado_ampacidad() -> dict:
        """Devuelve perfiles P3, routing P3A y madurez vigente."""
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
        """Configura Ib/In/Iz con referencias explícitas; no asume factores ni In.

        Si existe un routing P3A vinculado, cada factor requerido debe declarar
        ``axis`` para demostrar que cubre el eje normativo identificado.
        """
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
