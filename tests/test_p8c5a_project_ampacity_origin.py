from __future__ import annotations

import pytest

from mcp_electrico import ampacity, conductor_library, core, visual_state, workspace_p3_view


NORM_ID = "IEC_60364_5_52_2009_A1_2024"


def _reset(circuit: str) -> None:
    core.crear_circuito(circuit, 22.9)
    visual_state.reset()
    conductor_library.reset()
    ampacity.reset()


def _define_p3(line: str, *, ib_a: float, in_a: float) -> dict:
    return ampacity.definir_condiciones(
        nombre_elemento=f"Line.{line}",
        norma_id=NORM_ID,
        in_proteccion_a=in_a,
        confirmar_condiciones_base=True,
        ib_diseno_a=ib_a,
        referencia_in="Protection schedule REV-A",
        referencia_ib="Load list + feeder sizing REV-A",
        referencia_condiciones_instalacion="Installation detail REV-A",
    )


def _snapshot_for(result: dict) -> dict:
    status = result.get("status")
    return {
        "status": {
            "studies": {
                "ampacity": {
                    "valid": True,
                    "result": {
                        "alimentadores": [result],
                        "summary": {
                            "total": 1,
                            "cumple": 1 if status == "CUMPLE" else 0,
                            "no_cumple": 1 if status == "NO_CUMPLE" else 0,
                            "datos_insuficientes": 1 if status == "DATOS_INSUFICIENTES" else 0,
                        },
                    },
                }
            }
        }
    }


def test_project_data_becomes_p2_project_through_p3_and_workspace_v3():
    _reset("p8c5a_project_origin")
    core.agregar_linea("project_feeder", "sourcebus", "b1", 0.1, r1_ohm_km=0.12, x1_ohm_km=0.08)
    assignment = conductor_library.registrar_asignacion_proyecto(
        "Line.project_feeder",
        "PROJECT-CABLE-01",
        500.0,
        "Approved cable ampacity calculation REV-A",
        "Installation detail REV-A",
        descripcion="PROJECT-CABLE-01 · feeder aprobado",
    )
    assert assignment["origen"] == "PROJECT_DATA"

    profile = _define_p3("project_feeder", ib_a=350.0, in_a=400.0)
    base = profile["base"]
    assert base["origin"] == "P2_PROJECT"
    assert base["assignment_origin"] == "PROJECT_DATA"
    assert base["assignment_ampacity_a"] == pytest.approx(500.0)
    assert base["assignment_installation"] == "project_explicit"
    assert base["catalog_ampacity_a"] is None
    assert base["catalog_installation"] is None
    assert base["catalog_conditions"] is None
    assert base["evidence"]["origin"] == "P2_PROJECT"

    result = ampacity.evaluar("Line.project_feeder")
    assert result["status"] == "CUMPLE"
    assert result["base_evidence"]["origin"] == "P2_PROJECT"
    assert result["installation"]["assignment_origin"] == "PROJECT_DATA"
    assert result["installation"]["catalog_installation"] is None
    assert result["sources"]["iz_base_project_p2"]["type"] == "PROJECT_DATA"
    assert result["sources"]["iz_base_catalog_p2"] is None

    label, css = workspace_p3_view._base_evidence_label(result)
    assert label == "PROYECTO P2"
    assert css == "p3-evidence-project"
    panel = workspace_p3_view._panel(_snapshot_for(result))
    assert "PROYECTO P2" in panel
    assert "CATÁLOGO P2" not in panel


def test_catalog_data_remains_p2_catalog_and_keeps_catalog_fields():
    _reset("p8c5a_catalog_origin")
    core.agregar_linea("catalog_feeder", "sourcebus", "b1", 0.1, r1_ohm_km=0.3, x1_ohm_km=0.1)
    assignment = conductor_library.aplicar_conductor(
        "Line.catalog_feeder",
        "NEXANS-N2XSY-18-30-CU-70-PH16",
        "air_trefoil_30c",
    )
    assert assignment["origen"] == "CATALOG_DATA"

    profile = _define_p3("catalog_feeder", ib_a=200.0, in_a=250.0)
    base = profile["base"]
    assert base["origin"] == "P2_CATALOG"
    assert base["assignment_origin"] == "CATALOG_DATA"
    assert base["assignment_ampacity_a"] == pytest.approx(296.0)
    assert base["catalog_ampacity_a"] == pytest.approx(296.0)
    assert base["catalog_installation"] == "air_trefoil_30c"
    assert base["catalog_conditions"] is not None
    assert base["evidence"]["origin"] == "P2_CATALOG"

    result = ampacity.evaluar("Line.catalog_feeder")
    assert result["status"] == "CUMPLE"
    assert result["base_evidence"]["origin"] == "P2_CATALOG"
    assert result["sources"]["iz_base_catalog_p2"] is not None
    assert result["sources"]["iz_base_project_p2"] is None

    label, css = workspace_p3_view._base_evidence_label(result)
    assert label == "CATÁLOGO P2"
    assert css == "p3-evidence-base"
    panel = workspace_p3_view._panel(_snapshot_for(result))
    assert "CATÁLOGO P2" in panel
    assert "PROYECTO P2" not in panel
