from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    file = Path(path)
    text = file.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"P3C10B patch refused: {path} expected 1 match, found {count}")
    file.write_text(text.replace(old, new, 1), encoding="utf-8")


# --- ampacity.py: integrar base normativa sin romper fallback P2 ---
replace_once(
    "mcp_electrico/ampacity.py",
    "from . import (\n    ampacity_factor_binding,",
    "from . import (\n    ampacity_base_binding,\n    ampacity_factor_binding,",
)

replace_once(
    "mcp_electrico/ampacity.py",
    "    referencia_condiciones_instalacion: str | None = None,\n    permitir_factores_dataset_secundarios: bool = False,\n) -> dict[str, Any]:",
    "    referencia_condiciones_instalacion: str | None = None,\n    permitir_factores_dataset_secundarios: bool = False,\n    base_normativa: dict[str, Any] | None = None,\n    permitir_base_dataset_secundaria: bool = False,\n) -> dict[str, Any]:",
)

replace_once(
    "mcp_electrico/ampacity.py",
    "    base = float(assignment.get(\"ampacidad_aplicada_a\") or 0)\n    if base <= 0:\n        raise ValueError(\"P3A016: ampacidad base P2 no disponible\")\n    total = prod(item[\"value\"] for item in validated) if validated else 1.0\n    evidence = ampacity_factor_binding.resumen_evidencia_factores(validated)\n",
    "    catalog_base = float(assignment.get(\"ampacidad_aplicada_a\") or 0)\n    if catalog_base <= 0:\n        raise ValueError(\"P3A016: ampacidad base P2 no disponible\")\n\n    normative_base = None\n    if base_normativa is not None:\n        normative_base = ampacity_base_binding.validar_base_dataset(\n            base_normativa,\n            permitir_secundario=permitir_base_dataset_secundaria,\n        )\n        if normative_base[\"norm_reference_id\"] != norm[\"id\"]:\n            raise ValueError(\"P3C10B001: Iz_base normativa pertenece a otra referencia normativa\")\n        if route and normative_base[\"profile_id\"] != route.get(\"profile_id\"):\n            raise ValueError(\"P3C10B002: Iz_base normativa pertenece a otro perfil P3A\")\n        base = float(normative_base[\"ampacity_a\"])\n    else:\n        base = catalog_base\n\n    base_evidence = ampacity_base_binding.resumen_evidencia_base(normative_base)\n    total = prod(item[\"value\"] for item in validated) if validated else 1.0\n    evidence = ampacity_factor_binding.resumen_evidencia_factores(validated)\n",
)

replace_once(
    "mcp_electrico/ampacity.py",
    "        \"base\": {\n            \"ampacity_a\": base,\n            \"catalog_installation\": assignment.get(\"instalacion\"),\n            \"catalog_conditions\": deepcopy(assignment.get(\"condiciones_ampacidad\")),\n            \"source\": deepcopy(assignment.get(\"fuente\")),\n            \"conductor_code\": assignment.get(\"codigo\"),\n        },",
    "        \"base\": {\n            \"ampacity_a\": base,\n            \"origin\": \"NORMATIVE_DATASET\" if normative_base else \"P2_CATALOG\",\n            \"catalog_ampacity_a\": catalog_base,\n            \"catalog_installation\": assignment.get(\"instalacion\"),\n            \"catalog_conditions\": deepcopy(assignment.get(\"condiciones_ampacidad\")),\n            \"source\": deepcopy(assignment.get(\"fuente\")),\n            \"conductor_code\": assignment.get(\"codigo\"),\n            \"normative_dataset\": deepcopy(normative_base),\n            \"evidence\": deepcopy(base_evidence),\n            \"allow_secondary\": bool(permitir_base_dataset_secundaria),\n        },",
)

replace_once(
    "mcp_electrico/ampacity.py",
    "    current_ampacity = float(assignment.get(\"ampacidad_aplicada_a\") or 0)\n    if abs(current_ampacity - float(base.get(\"ampacity_a\") or 0)) > 1e-9:\n        missing.append(\"ampacidad_base_modificada\")\n    return not missing, missing\n\n\ndef evaluar(nombre_elemento: str) -> dict[str, Any]:",
    "    current_ampacity = float(assignment.get(\"ampacidad_aplicada_a\") or 0)\n    expected_catalog_ampacity = float(\n        base.get(\"catalog_ampacity_a\", base.get(\"ampacity_a\")) or 0\n    )\n    if abs(current_ampacity - expected_catalog_ampacity) > 1e-9:\n        missing.append(\"ampacidad_base_modificada\")\n    return not missing, missing\n\n\ndef _revalidar_base_normativa(profile: dict[str, Any]) -> dict[str, Any] | None:\n    base = profile.get(\"base\") or {}\n    normative = base.get(\"normative_dataset\")\n    if not normative:\n        return None\n    return ampacity_base_binding.validar_base_dataset(\n        normative,\n        permitir_secundario=bool(base.get(\"allow_secondary\")),\n    )\n\n\ndef evaluar(nombre_elemento: str) -> dict[str, Any]:",
)

replace_once(
    "mcp_electrico/ampacity.py",
    "    route = _normative_routes.get(full.lower())\n    try:\n        _validate_route_for_profile(",
    "    try:\n        active_normative_base = _revalidar_base_normativa(profile)\n    except ValueError as exc:\n        return {\n            \"element\": full,\n            \"status\": \"DATOS_INSUFICIENTES\",\n            \"missing\": [\"iz_base_normativa\"],\n            \"maturity\": \"UNDER_VALIDATION\",\n            \"note\": str(exc),\n        }\n\n    route = _normative_routes.get(full.lower())\n    try:\n        _validate_route_for_profile(",
)

replace_once(
    "mcp_electrico/ampacity.py",
    "    in_a = float(profile[\"protection\"][\"in_a\"])\n    iz_base = float(profile[\"base\"][\"ampacity_a\"])\n    factor_total = float(profile[\"correction\"][\"factor_total\"])\n    iz = iz_base * factor_total\n    c1 = ib <= in_a\n    c2 = in_a <= iz\n    evidence = deepcopy(profile[\"correction\"].get(\"factor_evidence\") or {})\n    automatic_lookup = bool(profile[\"correction\"].get(\"automatic_normative_lookup\"))\n",
    "    in_a = float(profile[\"protection\"][\"in_a\"])\n    iz_base = float(\n        active_normative_base[\"ampacity_a\"]\n        if active_normative_base is not None\n        else profile[\"base\"][\"ampacity_a\"]\n    )\n    factor_total = float(profile[\"correction\"][\"factor_total\"])\n    iz = iz_base * factor_total\n    c1 = ib <= in_a\n    c2 = in_a <= iz\n    evidence = deepcopy(profile[\"correction\"].get(\"factor_evidence\") or {})\n    base_evidence = ampacity_base_binding.resumen_evidencia_base(active_normative_base)\n    automatic_lookup = bool(\n        base_evidence.get(\"professional_emission\")\n        and profile[\"correction\"].get(\"automatic_normative_lookup\")\n    )\n",
)

replace_once(
    "mcp_electrico/ampacity.py",
    "            \"iz_base\": deepcopy(profile[\"base\"][\"source\"]),\n            \"norm\": deepcopy(profile[\"norm\"]),",
    "            \"iz_base\": deepcopy(\n                active_normative_base\n                if active_normative_base is not None\n                else profile[\"base\"][\"source\"]\n            ),\n            \"iz_base_catalog_p2\": deepcopy(profile[\"base\"][\"source\"]),\n            \"norm\": deepcopy(profile[\"norm\"]),",
)

replace_once(
    "mcp_electrico/ampacity.py",
    "            \"correction_mode\": profile[\"correction\"][\"mode\"],\n        },\n        \"factor_evidence\": evidence,",
    "            \"correction_mode\": profile[\"correction\"][\"mode\"],\n            \"iz_base_origin\": base_evidence.get(\"origin\"),\n            \"iz_base_table\": base_evidence.get(\"table\"),\n        },\n        \"base_evidence\": deepcopy(base_evidence),\n        \"factor_evidence\": evidence,",
)

replace_once(
    "mcp_electrico/ampacity.py",
    "        \"automatic_normative_lookup\": bool(profiles) and all(\n            bool((item.get(\"correction\") or {}).get(\"automatic_normative_lookup\"))\n            for item in profiles\n        ),",
    "        \"automatic_normative_lookup\": bool(profiles) and all(\n            bool((item.get(\"base\") or {}).get(\"evidence\", {}).get(\"professional_emission\"))\n            and bool((item.get(\"correction\") or {}).get(\"automatic_normative_lookup\"))\n            for item in profiles\n        ),",
)

# --- ampacity_tools.py: resolver base portable + pasarla a configuración ---
replace_once(
    "mcp_electrico/ampacity_tools.py",
    "    ampacity,\n    ampacity_datasets,",
    "    ampacity,\n    ampacity_base_binding,\n    ampacity_datasets,\n    ampacity_exact_lookup,",
)

replace_once(
    "mcp_electrico/ampacity_tools.py",
    "    @mcp.tool()\n    def definir_aplicabilidad_normativa_ampacidad(",
    "    @mcp.tool()\n    def resolver_base_normativa_ampacidad(\n        dataset_id: str,\n        consulta: dict,\n        permitir_dataset_secundario: bool = False,\n    ) -> dict:\n        \"\"\"Resuelve Tabla 1/2 exacta y devuelve ``base_p3`` portable si existe.\"\"\"\n        result = ampacity_exact_lookup.resolver_catalogo(\n            dataset_id,\n            consulta,\n            allow_secondary=permitir_dataset_secundario,\n        )\n        if result.get(\"status\") == ampacity_exact_lookup.RESOLVED_EXACT:\n            result = dict(result)\n            result[\"base_p3\"] = ampacity_base_binding.construir_base_desde_resultado(result)\n        record(\n            \"ampacity_base_lookup\",\n            result,\n            f\"resolver_base_normativa_ampacidad:{dataset_id}\",\n        )\n        return result\n\n    @mcp.tool()\n    def definir_aplicabilidad_normativa_ampacidad(",
)

replace_once(
    "mcp_electrico/ampacity_tools.py",
    "        referencia_condiciones_instalacion: str | None = None,\n        permitir_factores_dataset_secundarios: bool = False,\n    ) -> dict:",
    "        referencia_condiciones_instalacion: str | None = None,\n        permitir_factores_dataset_secundarios: bool = False,\n        base_normativa: dict | None = None,\n        permitir_base_dataset_secundaria: bool = False,\n    ) -> dict:",
)

replace_once(
    "mcp_electrico/ampacity_tools.py",
    "            referencia_condiciones_instalacion=referencia_condiciones_instalacion,\n            permitir_factores_dataset_secundarios=permitir_factores_dataset_secundarios,\n        )",
    "            referencia_condiciones_instalacion=referencia_condiciones_instalacion,\n            permitir_factores_dataset_secundarios=permitir_factores_dataset_secundarios,\n            base_normativa=base_normativa,\n            permitir_base_dataset_secundaria=permitir_base_dataset_secundaria,\n        )",
)

# --- readiness: una base P2 no puede convertirse en evidencia normativa primaria ---
replace_once(
    "mcp_electrico/ampacity_evidence_readiness.py",
    "    correction = profile.get(\"correction\") or {}\n    mode = str(correction.get(\"mode\") or \"\")\n    evidence = deepcopy(correction.get(\"factor_evidence\") or {})\n    factors = correction.get(\"factors\") or []\n",
    "    correction = profile.get(\"correction\") or {}\n    mode = str(correction.get(\"mode\") or \"\")\n    evidence = deepcopy(correction.get(\"factor_evidence\") or {})\n    factors = correction.get(\"factors\") or []\n    base_evidence = deepcopy((profile.get(\"base\") or {}).get(\"evidence\") or {})\n",
)

replace_once(
    "mcp_electrico/ampacity_evidence_readiness.py",
    "            \"factor_evidence\": evidence,\n            \"reasons\": [\n                \"Las condiciones base fueron confirmadas explícitamente; no existe todavía un lookup P3B primario que respalde factores automáticos.\"\n            ],",
    "            \"factor_evidence\": evidence,\n            \"base_evidence\": base_evidence,\n            \"reasons\": [\n                \"Las condiciones base fueron confirmadas explícitamente; no existe todavía un lookup P3B primario que respalde toda la cadena normativa.\"\n            ],",
)

replace_once(
    "mcp_electrico/ampacity_evidence_readiness.py",
    "            \"factor_evidence\": evidence,\n            \"reasons\": [\"La ficha no contiene un conjunto de factores con evidencia clasificable.\"],",
    "            \"factor_evidence\": evidence,\n            \"base_evidence\": base_evidence,\n            \"reasons\": [\"La ficha no contiene un conjunto de factores con evidencia clasificable.\"],",
)

replace_once(
    "mcp_electrico/ampacity_evidence_readiness.py",
    "            \"factor_evidence\": evidence,\n            \"reasons\": [\"El resumen de evidencia no cubre todos los factores configurados.\"],",
    "            \"factor_evidence\": evidence,\n            \"base_evidence\": base_evidence,\n            \"reasons\": [\"El resumen de evidencia no cubre todos los factores configurados.\"],",
)

replace_once(
    "mcp_electrico/ampacity_evidence_readiness.py",
    "    elif primary == total and bool(evidence.get(\"automatic_normative_lookup\")):\n        status = PRIMARY_EVIDENCE_READY\n        ready = True\n        reasons = [\n            \"Todos los factores provienen de datasets P3B primarios/verificados y el binding conserva su trazabilidad.\"\n        ]",
    "    elif primary == total and bool(evidence.get(\"automatic_normative_lookup\")):\n        if bool(base_evidence.get(\"professional_emission\")):\n            status = PRIMARY_EVIDENCE_READY\n            ready = True\n            reasons = [\n                \"Iz_base y todos los factores provienen de datasets P3B primarios/verificados con binding trazable.\"\n            ]\n        else:\n            status = EVIDENCE_INCOMPLETE\n            ready = False\n            reasons = [\n                \"Los factores son primarios, pero Iz_base todavía no dispone de evidencia normativa primaria.\"\n            ]",
)

replace_once(
    "mcp_electrico/ampacity_evidence_readiness.py",
    "        \"factor_evidence\": evidence,\n        \"reasons\": reasons,",
    "        \"factor_evidence\": evidence,\n        \"base_evidence\": base_evidence,\n        \"reasons\": reasons,",
)

# --- V3: mostrar origen de Iz_base separado de evidencia de factores ---
replace_once(
    "mcp_electrico/workspace_p3_view.py",
    "def _panel(snapshot: dict[str, Any]) -> str:",
    "def _base_evidence_label(item: dict[str, Any]) -> tuple[str, str]:\n    evidence = item.get(\"base_evidence\") or {}\n    if str(evidence.get(\"origin\") or \"") == \"P2_CATALOG\":\n        return \"CATÁLOGO P2\", \"p3-evidence-base\"\n    if bool(evidence.get(\"primary\")):\n        return \"PRIMARIA\", \"p3-evidence-primary\"\n    if bool(evidence.get(\"normative_base\")):\n        return \"SECUNDARIA\", \"p3-evidence-secondary\"\n    return \"INCOMPLETA\", \"p3-evidence-incomplete\"\n\n\ndef _panel(snapshot: dict[str, Any]) -> str:",
)

replace_once(
    "mcp_electrico/workspace_p3_view.py",
    "        evidence_label, evidence_css = _evidence_label(item)\n        rows.append(",
    "        evidence_label, evidence_css = _evidence_label(item)\n        base_label, base_css = _base_evidence_label(item)\n        rows.append(",
)

replace_once(
    "mcp_electrico/workspace_p3_view.py",
    "            f'<td>{_fmt(values.get(\"iz_base_a\"), 2, \" A\")}</td>'\n            f'<td>{_fmt(values.get(\"factor_total\"), 4)}</td>'",
    "            f'<td>{_fmt(values.get(\"iz_base_a\"), 2, \" A\")}</td>'\n            f'<td><span class=\"p3-evidence-badge {base_css}\">{escape(base_label)}</span></td>'\n            f'<td>{_fmt(values.get(\"factor_total\"), 4)}</td>'",
)

replace_once(
    "mcp_electrico/workspace_p3_view.py",
    "<div class=\"p3-note\"><strong>UNDER_VALIDATION.</strong> La columna Evidencia distingue procedencia de los factores: PRIMARIA, SECUNDARIA, MANUAL, BASE o MIXTA. Esta etiqueta no cambia el criterio Ib ≤ In ≤ Iz ni habilita emisión por sí sola. El navegador no calcula factores ni clasifica evidencia.</div>\n<div class=\"table-wrap\"><table class=\"study-table\"><thead><tr><th>Alimentador</th><th>Perfil / método</th><th>Routing</th><th>Ib</th><th>In</th><th>Iz base</th><th>∏k</th><th>Iz</th><th>Evidencia</th><th>Estado</th></tr></thead><tbody>{''.join(rows) or '<tr><td colspan=\"10\">No existen perfiles P3 evaluados.</td></tr>'}</tbody></table></div>",
    "<div class=\"p3-note\"><strong>UNDER_VALIDATION.</strong> V3 separa el origen de Iz base de la evidencia de factores. CATÁLOGO P2 no equivale a base normativa; PRIMARIA/SECUNDARIA se prepara en Python. El navegador no resuelve tablas, multiplica factores ni clasifica evidencia.</div>\n<div class=\"table-wrap\"><table class=\"study-table\"><thead><tr><th>Alimentador</th><th>Perfil / método</th><th>Routing</th><th>Ib</th><th>In</th><th>Iz base</th><th>Origen Iz base</th><th>∏k</th><th>Iz</th><th>Evid. factores</th><th>Estado</th></tr></thead><tbody>{''.join(rows) or '<tr><td colspan=\"11\">No existen perfiles P3 evaluados.</td></tr>'}</tbody></table></div>",
)

# --- tests P3C10B ---
Path("tests/test_ampacity_normative_base_p3c10b.py").write_text(r'''from copy import deepcopy

import pytest

from mcp_electrico import (
    ampacity,
    ampacity_base_binding,
    conductor_library,
    core,
    visual_state,
    workspace_p3_view,
)


PRIMARY_BASE_RESULT = {
    "status": "RESOLVED_EXACT",
    "dataset_id": "TEST_TABLE_2_PRIMARY",
    "profile_id": "PERU_CNE_UTIL_2006_030_004",
    "norm_reference_id": "PERU_CNE_UTILIZACION_2006",
    "table": "Tabla 2",
    "axis": "base_ampacity",
    "query": {"installation_method": "B2", "section_mm2": 70.0},
    "value": 250.0,
    "verification_status": "PRIMARY_VERIFIED",
    "professional_emission": True,
    "automatic_normative_lookup": True,
    "provenance": {"source_type": "primary_official"},
}


def _linea():
    core.crear_circuito("p3c10b", 22.9)
    visual_state.reset()
    conductor_library.reset()
    ampacity.reset()
    core.agregar_linea("f_base", "sourcebus", "b1", 0.1, r1_ohm_km=0.3, x1_ohm_km=0.1)
    return conductor_library.aplicar_conductor(
        "Line.f_base",
        "NEXANS-N2XSY-18-30-CU-70-PH16",
        "air_trefoil_30c",
    )


def _mock_primary(monkeypatch, result=None):
    payload = deepcopy(result or PRIMARY_BASE_RESULT)
    monkeypatch.setattr(
        ampacity_base_binding.ampacity_exact_lookup,
        "resolver_catalogo",
        lambda *_args, **_kwargs: deepcopy(payload),
    )
    return ampacity_base_binding.construir_base_desde_resultado(payload)


def test_iz_base_normativa_entra_al_calculo_y_preserva_catalogo_p2(monkeypatch):
    assignment = _linea()
    assert assignment["ampacidad_aplicada_a"] == pytest.approx(296.0)
    base = _mock_primary(monkeypatch)

    ampacity.definir_condiciones(
        "Line.f_base",
        "PERU_CNE_UTILIZACION_2006",
        220.0,
        factores=[{"id": "k_manual", "axis": "temperature", "value": 0.90, "reference": "caso sintético"}],
        ib_diseno_a=180.0,
        referencia_in="QF1",
        referencia_ib="memoria",
        referencia_condiciones_instalacion="caso sintético P3C10B",
        base_normativa=base,
    )

    result = ampacity.evaluar("Line.f_base")
    assert result["values"]["iz_base_a"] == pytest.approx(250.0)
    assert result["values"]["iz_a"] == pytest.approx(225.0)
    assert result["base_evidence"]["primary"] is True
    assert result["installation"]["iz_base_origin"] == "P3B_BASE_DATASET"
    assert result["sources"]["iz_base_catalog_p2"] is not None
    assert result["automatic_normative_lookup"] is False


def test_base_de_otra_referencia_normativa_se_rechaza(monkeypatch):
    _linea()
    other = deepcopy(PRIMARY_BASE_RESULT)
    other["norm_reference_id"] = "OTRA_NORMA"
    base = _mock_primary(monkeypatch, other)

    with pytest.raises(ValueError, match="P3C10B001"):
        ampacity.definir_condiciones(
            "Line.f_base",
            "PERU_CNE_UTILIZACION_2006",
            220.0,
            factores=[{"id": "k", "value": 1.0, "reference": "sintético"}],
            ib_diseno_a=180.0,
            referencia_in="QF1",
            referencia_ib="memoria",
            referencia_condiciones_instalacion="sintético",
            base_normativa=base,
        )


def test_cambio_del_dataset_base_invalida_evaluacion(monkeypatch):
    _linea()
    base = _mock_primary(monkeypatch)
    ampacity.definir_condiciones(
        "Line.f_base",
        "PERU_CNE_UTILIZACION_2006",
        220.0,
        factores=[{"id": "k", "value": 1.0, "reference": "sintético"}],
        ib_diseno_a=180.0,
        referencia_in="QF1",
        referencia_ib="memoria",
        referencia_condiciones_instalacion="sintético",
        base_normativa=base,
    )

    changed = deepcopy(PRIMARY_BASE_RESULT)
    changed["value"] = 249.0
    monkeypatch.setattr(
        ampacity_base_binding.ampacity_exact_lookup,
        "resolver_catalogo",
        lambda *_args, **_kwargs: deepcopy(changed),
    )
    result = ampacity.evaluar("Line.f_base")
    assert result["status"] == "DATOS_INSUFICIENTES"
    assert result["missing"] == ["iz_base_normativa"]


def test_v3_distingue_catalogo_p2_de_base_normativa():
    assert workspace_p3_view._base_evidence_label({
        "base_evidence": {"origin": "P2_CATALOG", "primary": False}
    })[0] == "CATÁLOGO P2"
    assert workspace_p3_view._base_evidence_label({
        "base_evidence": {"origin": "P3B_BASE_DATASET", "normative_base": True, "primary": True}
    })[0] == "PRIMARIA"
''', encoding="utf-8")

# Documentar integración sin declarar gate cerrado.
doc = Path("docs/P3C10_BASE_AMPACITY_STRATEGY.md")
text = doc.read_text(encoding="utf-8")
text = text.replace(
    "## Próximo bloque — P3C10B\n\nConectar este binding al cálculo P3:\n\n- permitir que `definir_condiciones_ampacidad()` reciba una base normativa trazable;\n- revalidarla en cada evaluación;\n- comparar/retener también la asignación P2 activa para detectar cambios de conductor;\n- calcular `Iz = Iz_base_normativa × ∏k` cuando corresponda;\n- llevar al resultado y al workspace V3 el origen de `Iz_base` (`CATÁLOGO P2` vs `NORMATIVA PRIMARIA/SECUNDARIA`);\n- mantener el navegador en modo read-only de ingeniería.\n\nP3C10 solo podrá cerrar cuando exista al menos una estrategia/dataset Tabla 1/2 `PRIMARY_VERIFIED` que satisfaga el gate formal y sus benchmarks correspondientes.\n",
    "## P3C10B — integración al cálculo y V3\n\n**IMPLEMENTADO COMO INFRAESTRUCTURA. P3C10 CONTINÚA PENDIENTE DE DATOS PRIMARIOS Tabla 1/2.**\n\nEl cálculo P3 puede recibir ahora una `base_normativa` portable producida por P3C10A. La base se revalida contra el catálogo activo antes de configurar y nuevamente al evaluar. La asignación P2 se conserva en paralelo para detectar cambios de conductor/instalación y para mostrar la diferencia entre catálogo y norma.\n\nCuando existe base normativa:\n\n```text\nIz = Iz_base_normativa × ∏k\n```\n\nEl resultado expone `base_evidence`, la fuente normativa de `Iz_base` y la fuente de catálogo P2 por separado. V3 añade la columna **Origen Iz base**, con clasificación preparada por Python: `CATÁLOGO P2`, `PRIMARIA`, `SECUNDARIA` o `INCOMPLETA`. El navegador continúa sin resolver tablas ni recalcular ingeniería.\n\nLa readiness de evidencia también exige base primaria: factores primarios con `Iz_base` todavía de catálogo P2 ya no pueden clasificarse como evidencia normativa profesional completa.\n\nP3C10 solo podrá cerrar cuando exista al menos una estrategia/dataset Tabla 1/2 `PRIMARY_VERIFIED` real que satisfaga el gate formal y sus benchmarks correspondientes.\n"
)
doc.write_text(text, encoding="utf-8")

print("P3C10B patch applied")
