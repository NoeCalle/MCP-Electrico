"""Tools MCP para P3/P3A/P3B ampacidad.

Las tools de este módulo no convierten tablas de fabricante en norma. Exponen
la configuración trazable Ib/In/Iz, el router P3A, datasets P3B, evidencia y
el gate formal de salida P3. No existe una tool que promueva automáticamente
datasets ni eleve la madurez del módulo.
"""

from __future__ import annotations

from pathlib import Path

from . import (
    ampacity,
    ampacity_base_binding,
    ampacity_datasets,
    ampacity_exact_lookup,
    ampacity_evidence,
    ampacity_evidence_readiness,
    ampacity_factor_binding,
    ampacity_norms,
    ampacity_profiles,
    p3_completion,
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
        return ampacity_norms.listar_referencias()

    @mcp.tool()
    def listar_perfiles_normativos_ampacidad() -> list[dict]:
        return ampacity_profiles.listar_perfiles()

    @mcp.tool()
    def listar_datasets_numericos_ampacidad() -> list[dict]:
        return ampacity_datasets.listar_datasets()

    @mcp.tool()
    def listar_fuentes_primarias_ampacidad() -> list[dict]:
        return ampacity_evidence.listar_fuentes()

    @mcp.tool()
    def verificar_archivo_fuente_ampacidad(source_id: str, ruta_archivo: str) -> dict:
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
        return ampacity_evidence.evaluar_promocion_dataset(dataset_id, evidencia)

    @mcp.tool()
    def evaluar_evidencia_normativa_ampacidad() -> dict:
        """Clasifica evidencia de factores sin cambiar READY_DATA ni madurez P3."""
        return ampacity_evidence_readiness.evaluar()

    @mcp.tool()
    def evaluar_cierre_p3() -> dict:
        """Evalúa el gate formal P3; hoy debe bloquear avance mientras falte evidencia/cobertura normativa."""
        return p3_completion.evaluar_cierre_p3()

    @mcp.tool()
    def resolver_factor_agrupamiento_ampacidad(
        nombre_elemento: str,
        circuitos_agrupados: int,
        disposicion_id: str,
        permitir_dataset_secundario: bool = False,
    ) -> dict:
        """Resuelve agrupamiento y, si existe valor, devuelve ``factor_p3`` trazable."""
        route = ampacity.obtener_aplicabilidad_normativa(nombre_elemento)
        if not route:
            raise ValueError("P3B010: el alimentador no tiene routing P3A vinculado")
        result = ampacity_datasets.resolver_grouping_for_route(
            route=route,
            circuits_grouped=circuitos_agrupados,
            arrangement_id=disposicion_id,
            allow_secondary=permitir_dataset_secundario,
        )
        if result.get("status") in {
            ampacity_datasets.RESOLVED_PRIMARY,
            ampacity_datasets.RESOLVED_SECONDARY,
        }:
            result = dict(result)
            result["factor_p3"] = ampacity_factor_binding.construir_factor_desde_resultado(result)
        record(
            "ampacity_numeric_lookup",
            result,
            f"resolver_factor_agrupamiento_ampacidad:{nombre_elemento}",
        )
        return result

    @mcp.tool()
    def resolver_factor_normativo_ampacidad(
        dataset_id: str,
        consulta: dict,
        permitir_dataset_secundario: bool = False,
    ) -> dict:
        """Resuelve un factor ``exact_rows_v1`` y devuelve ``factor_p3`` portable.

        La resolución exacta no basta para aplicarlo: ``definir_condiciones_ampacidad``
        revalida después su compatibilidad con routing P3A e Iz_base normativa.
        """
        result = ampacity_exact_lookup.resolver_catalogo(
            dataset_id,
            consulta,
            allow_secondary=permitir_dataset_secundario,
        )
        if result.get("status") == ampacity_exact_lookup.RESOLVED_EXACT:
            result = dict(result)
            result["factor_p3"] = ampacity_factor_binding.construir_factor_desde_resultado(result)
        record(
            "ampacity_factor_lookup",
            result,
            f"resolver_factor_normativo_ampacidad:{dataset_id}",
        )
        return result

    @mcp.tool()
    def resolver_base_normativa_ampacidad(
        dataset_id: str,
        consulta: dict,
        permitir_dataset_secundario: bool = False,
    ) -> dict:
        """Resuelve Tabla 1/2 exacta y devuelve ``base_p3`` portable si existe."""
        result = ampacity_exact_lookup.resolver_catalogo(
            dataset_id,
            consulta,
            allow_secondary=permitir_dataset_secundario,
        )
        if result.get("status") == ampacity_exact_lookup.RESOLVED_EXACT:
            result = dict(result)
            result["base_p3"] = ampacity_base_binding.construir_base_desde_resultado(result)
        record(
            "ampacity_base_lookup",
            result,
            f"resolver_base_normativa_ampacidad:{dataset_id}",
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
        profundidad_enterramiento_m: float | None = None,
        circuitos_agrupados: int = 1,
        disposicion_agrupamiento: str | None = None,
        rama_tabla_5d: str | None = None,
        separacion_tabla_5d_id: str | None = None,
        numero_tramos: int = 1,
        transicion_tramos: str | None = None,
        solicitar_excepcion_tramo_corto: bool = False,
    ) -> dict:
        result = ampacity.definir_aplicabilidad_normativa(
            nombre_elemento=nombre_elemento,
            perfil_normativo_id=perfil_normativo_id,
            metodo_instalacion=metodo_instalacion,
            ambiente=ambiente,
            temperatura_ambiente_c=temperatura_ambiente_c,
            resistividad_termica_suelo_k_m_w=resistividad_termica_suelo_k_m_w,
            profundidad_enterramiento_m=profundidad_enterramiento_m,
            circuitos_agrupados=circuitos_agrupados,
            disposicion_agrupamiento=disposicion_agrupamiento,
            rama_tabla_5d=rama_tabla_5d,
            separacion_tabla_5d_id=separacion_tabla_5d_id,
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
        permitir_factores_dataset_secundarios: bool = False,
        base_normativa: dict | None = None,
        permitir_base_dataset_secundaria: bool = False,
    ) -> dict:
        """Configura Ib/In/Iz; factores P3B secundarios requieren opt-in explícito."""
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
            permitir_factores_dataset_secundarios=permitir_factores_dataset_secundarios,
            base_normativa=base_normativa,
            permitir_base_dataset_secundaria=permitir_base_dataset_secundaria,
        )
        record("ampacity_config", ampacity.snapshot(), f"definir_condiciones_ampacidad:{nombre_elemento}")
        return result

    @mcp.tool()
    def evaluar_ampacidad(nombre_elemento: str | None = None) -> dict:
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
            "automatic_normative_lookup": bool(result.get("automatic_normative_lookup")),
            "professional_emission": False,
        }
        record("ampacity", payload, f"evaluar_ampacidad:{nombre_elemento or 'todos'}")
        return result
