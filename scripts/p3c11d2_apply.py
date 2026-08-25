from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# ---------------------------------------------------------------------------
# ampacity_profiles.py
# ---------------------------------------------------------------------------
p = ROOT / "mcp_electrico/ampacity_profiles.py"
text = p.read_text(encoding="utf-8")

anchor = '''def _segment_transition(value: str | None) -> str | None:\n'''
insert = '''_TABLE5D_BRANCH_ENVIRONMENT = {\n    "A_DIRECT_BURIED_CABLES": "direct_buried",\n    "B_MULTICORE_SINGLE_WAY_DUCTS": "buried_duct",\n    "C_SINGLE_CORE_SINGLE_WAY_DUCT_CIRCUITS": "buried_duct",\n}\n\n_TABLE5D_SPACING_IDS = {\n    "A_DIRECT_BURIED_CABLES": {"contact", "one_cable_diameter", "0_125_m", "0_25_m", "0_5_m"},\n    "B_MULTICORE_SINGLE_WAY_DUCTS": {"contact", "0_25_m", "0_5_m", "1_0_m"},\n    "C_SINGLE_CORE_SINGLE_WAY_DUCT_CIRCUITS": {"contact", "0_25_m", "0_5_m", "1_0_m"},\n}\n\ndef _table5d_branch(value: str | None) -> str | None:\n    if value is None or not str(value).strip():\n        return None\n    raw = str(value).strip().upper()\n    aliases = {\n        "A": "A_DIRECT_BURIED_CABLES",\n        "B": "B_MULTICORE_SINGLE_WAY_DUCTS",\n        "C": "C_SINGLE_CORE_SINGLE_WAY_DUCT_CIRCUITS",\n        **{key: key for key in _TABLE5D_BRANCH_ENVIRONMENT},\n    }\n    if raw not in aliases:\n        raise ValueError("P3P009: table5d_branch debe ser A | B | C o un ID canónico de Tabla 5D")\n    return aliases[raw]\n\ndef _table5d_spacing(branch: str, value: str | None) -> str | None:\n    if value is None or not str(value).strip():\n        return None\n    spacing = str(value).strip().lower().replace(".", "_")\n    aliases = {\n        "none": "contact", "ninguna": "contact", "contacto": "contact",\n        "one_diameter": "one_cable_diameter", "un_diametro": "one_cable_diameter",\n        "0_125": "0_125_m", "0_25": "0_25_m", "0_5": "0_5_m", "1_0": "1_0_m",\n    }\n    spacing = aliases.get(spacing, spacing)\n    if spacing not in _TABLE5D_SPACING_IDS[branch]:\n        raise ValueError(f"P3P010: spacing_id={spacing} no existe en la rama {branch} de Tabla 5D")\n    return spacing\n\n\n'''
if anchor not in text:
    raise SystemExit("ampacity_profiles helper anchor missing")
text = text.replace(anchor, insert + anchor, 1)

old_sig = '''    circuits_grouped: int = 1,\n    grouping_arrangement: str | None = None,\n    segment_count: int = 1,\n'''
new_sig = '''    circuits_grouped: int = 1,\n    grouping_arrangement: str | None = None,\n    table5d_branch: str | None = None,\n    grouping_spacing_id: str | None = None,\n    segment_count: int = 1,\n'''
if old_sig not in text:
    raise SystemExit("ampacity_profiles signature anchor missing")
text = text.replace(old_sig, new_sig, 1)

old_init = '''    axes: list[dict[str, Any]] = []\n    depth: float | None = None\n'''
new_init = '''    axes: list[dict[str, Any]] = []\n    depth: float | None = None\n    rho: float | None = None\n'''
text = text.replace(old_init, new_init, 1)

old_rho = '''                rho = float(soil_thermal_resistivity_k_m_per_w)\n                if rho <= 0:\n'''
new_rho = '''                rho = float(soil_thermal_resistivity_k_m_per_w)\n                if rho <= 0:\n'''
# explicit no-op anchor check for future drift
if old_rho not in text:
    raise SystemExit("buried rho anchor missing")

old_direct = '''        elif env == "direct_buried":\n            manual.append(\n                "P3A no extrapola la Tabla 5B a tendido directamente enterrado; "\n                "la rama automatizada de 030-004(9) se limita a conductores en ductos enterrados."\n            )\n'''
new_direct = '''        elif env == "direct_buried":\n            # Tabla 5B no se aplica automáticamente a enterramiento directo.\n            # Tabla 5D-A sí publica una rama explícita; D2 la valida más abajo.\n            if soil_thermal_resistivity_k_m_per_w is not None:\n                rho = float(soil_thermal_resistivity_k_m_per_w)\n                if rho <= 0:\n                    raise ValueError("P3P003: resistividad térmica del suelo debe ser positiva")\n'''
if old_direct not in text:
    raise SystemExit("direct buried anchor missing")
text = text.replace(old_direct, new_direct, 1)

old_group = '''        if method == "D":\n            if not arrangement:\n                missing.append("grouping_arrangement")\n            axes.append(_axis(\n                "grouping",\n                True,\n                "Tabla 5D — factores de reducción para más de un circuito en ductos enterrados",\n                (\n                    f"Se declararon {grouped} circuitos para método D; la Tabla 5D depende de la disposición "\n                    "y separación física de cables/ductos."\n                ),\n                MANUAL_REVIEW_REQUIRED,\n            ))\n            manual.append(\n                "P3A identifica Tabla 5D para método D, pero todavía no clasifica automáticamente sus ramas "\n                "por cable/ducto y separación; se requiere disposición explícita antes del lookup numérico."\n            )\n'''
new_group = '''        if method == "D":\n            branch5d = _table5d_branch(table5d_branch)\n            spacing5d = _table5d_spacing(branch5d, grouping_spacing_id) if branch5d else None\n            if branch5d is None or spacing5d is None:\n                if arrangement:\n                    axes.append(_axis(\n                        "grouping", True,\n                        "Tabla 5D — factores de reducción para más de un circuito en método D",\n                        f"Se declararon {grouped} circuitos con disposición libre '{arrangement}', todavía no clasificada en rama/espaciado 5D.",\n                        MANUAL_REVIEW_REQUIRED,\n                    ))\n                    manual.append(\n                        "P3C11D2 no interpreta grouping_arrangement libre. Declare table5d_branch y grouping_spacing_id para lookup automático."\n                    )\n                else:\n                    if branch5d is None:\n                        missing.append("table5d_branch: A | B | C")\n                    if spacing5d is None:\n                        missing.append("grouping_spacing_id")\n                    axes.append(_axis(\n                        "grouping", True,\n                        "Tabla 5D — factores de reducción para más de un circuito en método D",\n                        "Tabla 5D requiere rama física A/B/C y separación exacta.",\n                        TABLE_DATA_NOT_LOADED,\n                    ))\n            else:\n                expected_env = _TABLE5D_BRANCH_ENVIRONMENT[branch5d]\n                if env != expected_env:\n                    raise ValueError(\n                        f"P3P011: rama {branch5d} requiere environment={expected_env}, no {env or 'NONE'}"\n                    )\n                if depth is None:\n                    missing.append("burial_depth_m")\n                if rho is None:\n                    missing.append("soil_thermal_resistivity_k_m_per_w")\n                exact_depth = depth is not None and abs(depth - 0.7) <= 1e-12\n                exact_rho = rho is not None and abs(rho - 2.5) <= 1e-12\n                count_tabulated = 2 <= grouped <= 6\n                axis_status = TABLE_DATA_NOT_LOADED\n                if depth is not None and not exact_depth:\n                    axis_status = MANUAL_REVIEW_REQUIRED\n                    manual.append(\n                        f"Tabla 5D publica factores a 0,7 m; profundidad declarada={depth:g} m. No se extrapola automáticamente."\n                    )\n                if rho is not None and not exact_rho:\n                    axis_status = MANUAL_REVIEW_REQUIRED\n                    manual.append(\n                        f"Tabla 5D publica factores a ρ=2,5 K·m/W; valor declarado={rho:g}. La combinación 5B×5D queda fuera de D2."\n                    )\n                if not count_tabulated:\n                    axis_status = MANUAL_REVIEW_REQUIRED\n                    manual.append(\n                        f"Tabla 5D v1 tabula 2 a 6 circuitos/cables; se declararon {grouped}. No se extrapola."\n                    )\n                axes.append(_axis(\n                    "grouping", True,\n                    "Tabla 5D — factores de reducción para más de un circuito en método D",\n                    (f"Rama={branch5d}; separación={spacing5d}; circuitos/cables={grouped}; "\n                     + (f"profundidad={depth:g} m; " if depth is not None else "profundidad pendiente; ")\n                     + (f"ρ={rho:g} K·m/W." if rho is not None else "ρ pendiente.")),\n                    axis_status,\n                ))\n'''
if old_group not in text:
    raise SystemExit("method D grouping block anchor missing")
text = text.replace(old_group, new_group, 1)

old_context = '''        "grouping_context": {\n            "circuits_grouped": grouped,\n            "arrangement": arrangement,\n            "route": method_info["grouping_route"],\n        },\n'''
new_context = '''        "grouping_context": {\n            "circuits_grouped": grouped,\n            "arrangement": arrangement,\n            "route": method_info["grouping_route"],\n            "table5d_branch": (_table5d_branch(table5d_branch) if method == "D" and table5d_branch else None),\n            "grouping_spacing_id": (\n                _table5d_spacing(_table5d_branch(table5d_branch), grouping_spacing_id)\n                if method == "D" and table5d_branch and grouping_spacing_id else None\n            ),\n        },\n'''
if old_context not in text:
    raise SystemExit("grouping context anchor missing")
text = text.replace(old_context, new_context, 1)

old_burial = '''        "burial_context": {\n            "burial_depth_m": depth,\n            "table_5b_max_automatic_depth_m": 0.8 if method == "D" and env == "buried_duct" else None,\n        },\n'''
new_burial = '''        "burial_context": {\n            "burial_depth_m": depth,\n            "table_5b_max_automatic_depth_m": 0.8 if method == "D" and env == "buried_duct" else None,\n            "table_5d_automatic_depth_m": 0.7 if method == "D" else None,\n            "table_5d_automatic_soil_thermal_resistivity_k_m_per_w": 2.5 if method == "D" else None,\n        },\n'''
text = text.replace(old_burial, new_burial, 1)
p.write_text(text, encoding="utf-8")

# ---------------------------------------------------------------------------
# ampacity.py
# ---------------------------------------------------------------------------
p = ROOT / "mcp_electrico/ampacity.py"
text = p.read_text(encoding="utf-8")
old = '''    circuitos_agrupados: int = 1,\n    disposicion_agrupamiento: str | None = None,\n    numero_tramos: int = 1,\n'''
new = '''    circuitos_agrupados: int = 1,\n    disposicion_agrupamiento: str | None = None,\n    rama_tabla_5d: str | None = None,\n    separacion_tabla_5d_id: str | None = None,\n    numero_tramos: int = 1,\n'''
if old not in text: raise SystemExit("ampacity signature anchor")
text = text.replace(old, new, 1)
old = '''        circuits_grouped=circuitos_agrupados,\n        grouping_arrangement=disposicion_agrupamiento,\n        segment_count=numero_tramos,\n'''
new = '''        circuits_grouped=circuitos_agrupados,\n        grouping_arrangement=disposicion_agrupamiento,\n        table5d_branch=rama_tabla_5d,\n        grouping_spacing_id=separacion_tabla_5d_id,\n        segment_count=numero_tramos,\n'''
text = text.replace(old, new, 1)
old = '''            "grouping_arrangement": str(disposicion_agrupamiento or "").strip() or None,\n'''
new = '''            "grouping_arrangement": str(disposicion_agrupamiento or "").strip() or None,\n            "table5d_branch": str(rama_tabla_5d or "").strip() or None,\n            "grouping_spacing_id": str(separacion_tabla_5d_id or "").strip() or None,\n'''
text = text.replace(old, new, 1)
p.write_text(text, encoding="utf-8")

# ---------------------------------------------------------------------------
# ampacity_tools.py
# ---------------------------------------------------------------------------
p = ROOT / "mcp_electrico/ampacity_tools.py"
text = p.read_text(encoding="utf-8")
old = '''        circuitos_agrupados: int = 1,\n        disposicion_agrupamiento: str | None = None,\n        numero_tramos: int = 1,\n'''
new = '''        circuitos_agrupados: int = 1,\n        disposicion_agrupamiento: str | None = None,\n        rama_tabla_5d: str | None = None,\n        separacion_tabla_5d_id: str | None = None,\n        numero_tramos: int = 1,\n'''
if old not in text: raise SystemExit("tools signature anchor")
text = text.replace(old, new, 1)
old = '''            circuitos_agrupados=circuitos_agrupados,\n            disposicion_agrupamiento=disposicion_agrupamiento,\n            numero_tramos=numero_tramos,\n'''
new = '''            circuitos_agrupados=circuitos_agrupados,\n            disposicion_agrupamiento=disposicion_agrupamiento,\n            rama_tabla_5d=rama_tabla_5d,\n            separacion_tabla_5d_id=separacion_tabla_5d_id,\n            numero_tramos=numero_tramos,\n'''
text = text.replace(old, new, 1)
p.write_text(text, encoding="utf-8")

# ---------------------------------------------------------------------------
# factor binding
# ---------------------------------------------------------------------------
p = ROOT / "mcp_electrico/ampacity_factor_binding.py"
text = p.read_text(encoding="utf-8")
text = text.replace(
    'if axis not in {"ambient_temperature", "soil_thermal_resistivity"}:',
    'if axis not in {"ambient_temperature", "soil_thermal_resistivity", "grouping"}:',
    1,
)
anchor = '''    # P3C11B2 — Tabla 5B.\n'''
block = '''    # P3C11D2 — Tabla 5D. Legacy 5C no pasa por exact_rows_v1.\n    if axis == "grouping":\n        if str(factor.get("table_or_clause") or "") != "Tabla 5D":\n            raise ValueError("P3C11D2001: grouping exact_rows_v1 automático requiere Tabla 5D")\n        if expected_method != "D":\n            raise ValueError("P3C11D2002: Tabla 5D automática requiere método D")\n        if str(normative_base.get("table") or "") != "Tabla 2":\n            raise ValueError("P3C11D2003: Tabla 5D v1 requiere Iz_base de Tabla 2")\n        grouping = route.get("grouping_context") or {}\n        branch = str(grouping.get("table5d_branch") or "")\n        spacing = str(grouping.get("grouping_spacing_id") or "")\n        if not branch or not spacing:\n            raise ValueError("P3C11D2004: routing P3A no contiene rama/espaciado estructurado de Tabla 5D")\n        if str(query.get("table5d_branch") or "") != branch:\n            raise ValueError("P3C11D2005: rama Tabla 5D del factor no coincide con routing P3A")\n        if str(query.get("spacing_id") or "") != spacing:\n            raise ValueError("P3C11D2006: separación Tabla 5D del factor no coincide con routing P3A")\n        if int(query.get("circuits_grouped") or 0) != int(grouping.get("circuits_grouped") or 0):\n            raise ValueError("P3C11D2007: número de circuitos/cables 5D no coincide con routing P3A")\n        if str(query.get("environment") or "") != str(route.get("environment") or ""):\n            raise ValueError("P3C11D2008: ambiente de la rama 5D no coincide con routing P3A")\n        depth = declared.get("burial_depth_m")\n        rho5d = declared.get("soil_thermal_resistivity_k_m_per_w")\n        if not _same_number(query.get("burial_depth_m"), depth) or not _same_number(depth, 0.7):\n            raise ValueError("P3C11D2009: Tabla 5D automática requiere profundidad exacta de 0,7 m")\n        if not _same_number(query.get("soil_thermal_resistivity_k_m_per_w"), rho5d) or not _same_number(rho5d, 2.5):\n            raise ValueError("P3C11D2010: Tabla 5D automática requiere resistividad exacta de 2,5 K·m/W")\n        return {\n            "status": "COMPATIBLE_EXACT_FACTOR",\n            "compatible": True,\n            "policy": "P3C11D2_TABLE_5D_EXACT_CONTEXT_V1",\n            "axis": axis,\n            "dataset_id": meta.get("id"),\n            "base_dataset_id": base_meta.get("id"),\n            "checked": {\n                "norm_reference_id": factor_norm,\n                "profile_id": factor_profile,\n                "installation_method": expected_method,\n                "environment": route.get("environment"),\n                "table5d_branch": branch,\n                "spacing_id": spacing,\n                "circuits_grouped": grouping.get("circuits_grouped"),\n                "burial_depth_m": float(depth),\n                "soil_thermal_resistivity_k_m_per_w": float(rho5d),\n                "base_table": normative_base.get("table"),\n            },\n        }\n\n'''
if anchor not in text: raise SystemExit("binding insertion anchor")
text = text.replace(anchor, block + anchor, 1)
p.write_text(text, encoding="utf-8")

# ---------------------------------------------------------------------------
# workspace V3
# ---------------------------------------------------------------------------
p = ROOT / "mcp_electrico/workspace_p3_view.py"
text = p.read_text(encoding="utf-8")
old = '''        if query.get("burial_depth_scope") == "up_to_0_8_m":\n            context.append("prof. ≤0.8 m")\n'''
new = '''        if query.get("burial_depth_scope") == "up_to_0_8_m":\n            context.append("prof. ≤0.8 m")\n        if query.get("table5d_branch") is not None:\n            branch_labels = {\n                "A_DIRECT_BURIED_CABLES": "5D-A directa",\n                "B_MULTICORE_SINGLE_WAY_DUCTS": "5D-B multipolar/ducto",\n                "C_SINGLE_CORE_SINGLE_WAY_DUCT_CIRCUITS": "5D-C unipolar/ducto",\n            }\n            context.append(branch_labels.get(str(query.get("table5d_branch")), str(query.get("table5d_branch"))))\n        if query.get("spacing_id") is not None:\n            spacing_labels = {\n                "contact": "sep. contacto", "one_cable_diameter": "sep. 1 diámetro",\n                "0_125_m": "sep. 0.125 m", "0_25_m": "sep. 0.25 m",\n                "0_5_m": "sep. 0.5 m", "1_0_m": "sep. 1.0 m",\n            }\n            context.append(spacing_labels.get(str(query.get("spacing_id")), str(query.get("spacing_id"))))\n        if query.get("burial_depth_m") is not None:\n            context.append(f"prof.={_fmt(query.get('burial_depth_m'), 2)} m")\n'''
if old not in text: raise SystemExit("workspace factor context anchor")
text = text.replace(old, new, 1)
p.write_text(text, encoding="utf-8")

# ---------------------------------------------------------------------------
# Dataset policy
# ---------------------------------------------------------------------------
p = ROOT / "mcp_electrico/data/ampacity_p3b_numeric_datasets.json"
payload = json.loads(p.read_text(encoding="utf-8"))
dataset_id = "PERU_CNE_UTIL_2006_TABLE_5D_GROUPING_METHOD_D_PRIMARY_V1"
d = next(x for x in payload["datasets"] if x["id"] == dataset_id)
d["usage_policy"]["automatic_binding_to_iz"] = True
d["usage_policy"]["note"] = "Tabla 5D completa; P3C11D2 habilita binding solo con rama/espaciado estructurados y condiciones exactas 0.7 m / 2.5 K.m/W."
p.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

# ---------------------------------------------------------------------------
# Add structured reference case
# ---------------------------------------------------------------------------
p = ROOT / "mcp_electrico/data/ampacity_p3a_reference_cases.json"
payload = json.loads(p.read_text(encoding="utf-8"))
case_id = "cne_method_d_table5d_structured_exact_context"
payload["cases"] = [x for x in payload["cases"] if x.get("id") != case_id]
payload["cases"].insert(3, {
    "id": case_id,
    "input": {
        "profile_id": "PERU_CNE_UTIL_2006_030_004",
        "installation_method": "D",
        "environment": "buried_duct",
        "ambient_temperature_c": 20.0,
        "soil_thermal_resistivity_k_m_per_w": 2.5,
        "burial_depth_m": 0.7,
        "circuits_grouped": 3,
        "table5d_branch": "B",
        "grouping_spacing_id": "0_25_m"
    },
    "expected": {
        "base_ampacity_table": "Tabla 2",
        "status": "REQUIREMENTS_IDENTIFIED",
        "required_axes": ["grouping"],
        "missing_parameters": [],
        "unresolved_numeric_factors": True
    }
})
p.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
p = ROOT / "tests/test_ampacity_table5d_binding_p3c11d2.py"
p.write_text(r'''import pytest

from mcp_electrico import (
    ampacity, ampacity_base_binding, ampacity_exact_lookup, ampacity_factor_binding,
    conductor_library, core, visual_state, workspace_p3_view,
)

BASE_D = "PERU_CNE_UTIL_2006_TABLE_2_COL25_D_XLPE_3C_CU_70MM2_PRIMARY_V1"
FACTOR_5D = "PERU_CNE_UTIL_2006_TABLE_5D_GROUPING_METHOD_D_PRIMARY_V1"


def base_d():
    r = ampacity_exact_lookup.resolver_catalogo(BASE_D, {
        "installation_method": "D", "conductor_material": "Cu", "insulation": "XLPE_EPR",
        "temperature_c": 90, "loaded_conductors": 3, "section_mm2": 70.0,
    })
    assert r["status"] == "RESOLVED_EXACT"
    return ampacity_base_binding.construir_base_desde_resultado(r)


def factor5d(branch="B_MULTICORE_SINGLE_WAY_DUCTS", env="buried_duct", circuits=3, spacing="0_25_m"):
    r = ampacity_exact_lookup.resolver_catalogo(FACTOR_5D, {
        "installation_method": "D", "environment": env, "table5d_branch": branch,
        "burial_depth_m": 0.7, "soil_thermal_resistivity_k_m_per_w": 2.5,
        "circuits_grouped": circuits, "spacing_id": spacing,
    })
    assert r["status"] == "RESOLVED_EXACT"
    return ampacity_factor_binding.construir_factor_desde_resultado(r)


def setup_b(depth=0.7, rho=2.5, spacing="0_25_m"):
    core.crear_circuito("p3c11d2", 22.9); visual_state.reset(); conductor_library.reset(); ampacity.reset()
    core.agregar_linea("f_d", "sourcebus", "b1", 0.1, r1_ohm_km=0.3, x1_ohm_km=0.1)
    conductor_library.aplicar_conductor("Line.f_d", "NEXANS-N2XSY-18-30-CU-70-PH16", "buried_flat_20c")
    return ampacity.definir_aplicabilidad_normativa(
        "Line.f_d", "PERU_CNE_UTIL_2006_030_004", "D",
        ambiente="buried_duct", temperatura_ambiente_c=20.0,
        resistividad_termica_suelo_k_m_w=rho, profundidad_enterramiento_m=depth,
        circuitos_agrupados=3, rama_tabla_5d="B", separacion_tabla_5d_id=spacing,
    )


def test_cadena_100pct_primaria_d_tabla5d_b_llega_hasta_iz_y_v3():
    route = setup_b()
    assert route["status"] == "REQUIREMENTS_IDENTIFIED"
    assert route["grouping_context"]["table5d_branch"] == "B_MULTICORE_SINGLE_WAY_DUCTS"
    assert route["grouping_context"]["grouping_spacing_id"] == "0_25_m"
    profile = ampacity.definir_condiciones(
        "Line.f_d", "PERU_CNE_UTILIZACION_2006", 150.0,
        factores=[factor5d()], base_normativa=base_d(), ib_diseno_a=120.0,
        referencia_in="QF-D 150 A", referencia_ib="memoria P3C11D2",
        referencia_condiciones_instalacion="D / 5D-B / 3 circuitos / sep. 0.25 m / 0.7 m / rho 2.5",
    )
    check = profile["correction"]["compatibility_checks"][0]
    assert check["policy"] == "P3C11D2_TABLE_5D_EXACT_CONTEXT_V1"
    assert check["checked"]["spacing_id"] == "0_25_m"
    result = ampacity.evaluar("Line.f_d")
    assert result["status"] == "CUMPLE"
    assert result["values"]["iz_base_a"] == pytest.approx(178.0)
    assert result["values"]["factor_total"] == pytest.approx(0.85)
    assert result["values"]["iz_a"] == pytest.approx(151.3)
    assert result["automatic_normative_lookup"] is True
    detail = workspace_p3_view._factor_detail(result)
    assert "Tabla 5D" in detail
    assert "3 circuitos" in detail
    assert "5D-B multipolar/ducto" in detail
    assert "sep. 0.25 m" in detail
    assert "ρ=2.5 K·m/W" in detail
    assert "prof.=0.7 m" in detail


def test_routing_libre_legacy_permanece_manual_y_no_se_reinterpreta():
    core.crear_circuito("legacy5d", 22.9); visual_state.reset(); conductor_library.reset(); ampacity.reset()
    core.agregar_linea("f", "sourcebus", "b1", 0.1, r1_ohm_km=0.3, x1_ohm_km=0.1)
    route = ampacity.definir_aplicabilidad_normativa(
        "Line.f", "PERU_CNE_UTIL_2006_030_004", "D", ambiente="buried_duct",
        temperatura_ambiente_c=20, resistividad_termica_suelo_k_m_w=2.5,
        profundidad_enterramiento_m=0.7, circuitos_agrupados=3,
        disposicion_agrupamiento="descripcion libre histórica",
    )
    assert route["status"] == "MANUAL_REVIEW_REQUIRED"
    assert route["grouping_context"]["table5d_branch"] is None


def test_routing_5d_sin_clasificacion_estructurada_queda_missing_inputs():
    core.crear_circuito("missing5d", 22.9); visual_state.reset(); conductor_library.reset(); ampacity.reset()
    core.agregar_linea("f", "sourcebus", "b1", 0.1, r1_ohm_km=0.3, x1_ohm_km=0.1)
    route = ampacity.definir_aplicabilidad_normativa(
        "Line.f", "PERU_CNE_UTIL_2006_030_004", "D", ambiente="buried_duct",
        temperatura_ambiente_c=20, resistividad_termica_suelo_k_m_w=2.5,
        profundidad_enterramiento_m=0.7, circuitos_agrupados=3,
    )
    assert route["status"] == "MISSING_INPUTS"
    assert any("table5d_branch" in x for x in route["missing_parameters"])
    assert "grouping_spacing_id" in route["missing_parameters"]


def test_5d_no_se_vincula_fuera_de_07m_ni_rho25():
    route = setup_b(depth=0.8, rho=2.5)
    assert route["status"] == "MANUAL_REVIEW_REQUIRED"
    with pytest.raises(ValueError, match="P3C11D2009"):
        ampacity_factor_binding.validar_compatibilidad_contexto(factor5d(), route, base_d())
    route = setup_b(depth=0.7, rho=3.0)
    assert route["status"] == "MANUAL_REVIEW_REQUIRED"
    with pytest.raises(ValueError, match="P3C11D2010"):
        ampacity_factor_binding.validar_compatibilidad_contexto(factor5d(), route, base_d())


def test_factor_5d_debe_coincidir_con_rama_espaciado_y_numero():
    route = setup_b()
    with pytest.raises(ValueError, match="P3C11D2006"):
        ampacity_factor_binding.validar_compatibilidad_contexto(
            factor5d(spacing="0_5_m"), route, base_d()
        )
    with pytest.raises(ValueError, match="P3C11D2007"):
        ampacity_factor_binding.validar_compatibilidad_contexto(
            factor5d(circuits=2), route, base_d()
        )


def test_rama_a_direct_buried_es_explicita_y_no_se_confunde_con_5b():
    core.crear_circuito("direct5d", 22.9); visual_state.reset(); conductor_library.reset(); ampacity.reset()
    core.agregar_linea("f", "sourcebus", "b1", 0.1, r1_ohm_km=0.3, x1_ohm_km=0.1)
    route = ampacity.definir_aplicabilidad_normativa(
        "Line.f", "PERU_CNE_UTIL_2006_030_004", "D", ambiente="direct_buried",
        temperatura_ambiente_c=20, resistividad_termica_suelo_k_m_w=2.5,
        profundidad_enterramiento_m=0.7, circuitos_agrupados=2,
        rama_tabla_5d="A", separacion_tabla_5d_id="one_cable_diameter",
    )
    assert route["status"] == "REQUIREMENTS_IDENTIFIED"
    assert not any("Tabla 5B" in x for x in route["manual_review"])
    check = ampacity_factor_binding.validar_compatibilidad_contexto(
        factor5d("A_DIRECT_BURIED_CABLES", "direct_buried", 2, "one_cable_diameter"),
        route, base_d(),
    )
    assert check["policy"] == "P3C11D2_TABLE_5D_EXACT_CONTEXT_V1"


def test_rama_y_ambiente_incompatibles_se_rechazan_en_router():
    core.crear_circuito("bad5d", 22.9); visual_state.reset(); conductor_library.reset(); ampacity.reset()
    core.agregar_linea("f", "sourcebus", "b1", 0.1, r1_ohm_km=0.3, x1_ohm_km=0.1)
    with pytest.raises(ValueError, match="P3P011"):
        ampacity.definir_aplicabilidad_normativa(
            "Line.f", "PERU_CNE_UTIL_2006_030_004", "D", ambiente="buried_duct",
            temperatura_ambiente_c=20, resistividad_termica_suelo_k_m_w=2.5,
            profundidad_enterramiento_m=0.7, circuitos_agrupados=2,
            rama_tabla_5d="A", separacion_tabla_5d_id="contact",
        )
''', encoding="utf-8")

# ---------------------------------------------------------------------------
# Docs / roadmap
# ---------------------------------------------------------------------------
p = ROOT / "docs/P3C11D2_TABLE5D_BINDING.md"
p.write_text('''# P3C11D2 — binding seguro Tabla 5D → Iz

P3C11D2 conecta la Tabla 5D primaria completa con el cálculo de `Iz` sin inferir la disposición física desde texto libre.

## Routing estructurado

Para método D con más de un circuito se incorporan dos campos explícitos:

- `table5d_branch`: `A`, `B`, `C` o su ID canónico;
- `grouping_spacing_id`: separación exacta tabulada.

`grouping_arrangement` libre se conserva por compatibilidad, pero **no se interpreta automáticamente** y mantiene el caso en revisión manual.

## Política de compatibilidad

Un factor Tabla 5D puede entrar a `Iz` solo si coinciden exactamente:

- perfil y referencia normativa;
- método D;
- `Iz_base` de Tabla 2;
- ambiente de la rama;
- rama A/B/C;
- separación;
- número de circuitos/cables;
- profundidad `0.7 m`;
- resistividad térmica `2.5 K·m/W`.

D2 no valida todavía la combinación automática de 5B y 5D para resistividades distintas de 2.5 K·m/W. Esa combinación permanece fail-closed.

## Cadena primaria de regresión

Caso B, cable multipolar en ducto de una vía, 3 circuitos, separación 0.25 m:

```text
Iz_base Tabla 2 col.25 = 178 A
k_grouping Tabla 5D-B = 0.85
Iz = 178 × 0.85 = 151.30 A
```

## V3

V3 sigue siendo read-only y muestra datos ya calculados/revalidados por Python:

- Tabla 5D;
- rama A/B/C;
- número de circuitos;
- separación;
- ρ;
- profundidad;
- dataset primario.

El navegador no realiza lookup ni recalcula `Iz`.
''', encoding="utf-8")

p = ROOT / "docs/ROADMAP_PROFESIONAL.md"
text = p.read_text(encoding="utf-8")
old = "5B y 5D ya disponen de cobertura primaria completa; 5B además tiene binding seguro hacia Iz; 5A/5C parciales y 5E pendiente"
new = "5B y 5D ya disponen de cobertura primaria completa y binding seguro hacia Iz; 5A/5C parciales y 5E pendiente"
if old not in text: raise SystemExit("roadmap D2 anchor missing")
text = text.replace(old, new, 1)
p.write_text(text, encoding="utf-8")
