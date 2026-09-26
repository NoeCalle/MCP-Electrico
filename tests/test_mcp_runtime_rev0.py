from __future__ import annotations

import inspect
import json
from pathlib import Path
import subprocess
import sys

from mcp_electrico import (
    core,
    model_placeholders,
    model_qa,
    real_model_materializer,
    real_model_tools,
)


ROOT = Path(__file__).resolve().parents[1]


class FakeMCP:
    def __init__(self):
        self.tools = {}

    def tool(self):
        def decorator(fn):
            assert fn.__name__ not in self.tools
            self.tools[fn.__name__] = fn
            return fn
        return decorator


def _manifest() -> dict:
    path = ROOT / "examples" / "p10_reference_substation_stage1.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_rev0_registry_exposes_safe_construction_path():
    mcp = FakeMCP()
    real_model_tools.register(mcp)

    assert {
        "obtener_contrato_construccion_rev0",
        "validar_construccion_rev0",
        "construir_modelo_rev0",
        "registrar_placeholder_modelo",
        "obtener_placeholders_modelo",
    } <= set(mcp.tools)

    contract = mcp.tools["obtener_contrato_construccion_rev0"]()
    assert contract["solve_performed"] is False
    assert contract["workspace_file_written"] is False
    assert contract["automatic_defaults"] is False
    assert contract["professional_emission"] is False


def test_rev0_preflight_and_build_do_not_solve_or_claim_study_readiness():
    manifest = _manifest()
    preflight = real_model_materializer.evaluar_preflight_materializacion(manifest)

    assert preflight["ready_to_materialize"] is True
    assert preflight["model_mutation_performed"] is False
    assert preflight["solve_performed"] is False
    assert preflight["workspace_file_written"] is False

    result = real_model_materializer.materializar_modelo(manifest)

    assert result["materializer_status"] == "MODEL_BUILT_NOT_EXECUTED"
    assert result["electrical_calculation_performed"] is False
    assert result["solve_performed"] is False
    assert result["workspace_file_written"] is False
    assert result["study_readiness_evaluated"] is False
    assert result["model_ready_for_study"] is False
    assert result["model_placeholders"]["count"] == 0


def test_model_placeholder_is_non_solver_and_blocks_qa():
    real_model_materializer.materializar_modelo(_manifest())

    item = model_placeholders.registrar(
        element_id="Transformer.TR_AUX_TBC",
        element_type="TRANSFORMER",
        known_data={
            "bus_hv": "bus_4k16",
            "bus_lv": "bus_480_tbc",
            "kva": 1500.0,
        },
        missing_fields=["uk_percent", "vector_group"],
        source_reference="SLD Rev.0",
        note="Auxiliary transformer data pending vendor/design confirmation.",
    )

    assert item["status"] == "MODEL_PLACEHOLDER_TBC"
    assert item["solver_materialized"] is False
    assert item["blocks_study_readiness"] is True

    audit = model_qa.auditar_modelo(["power_flow"])
    findings = [x for x in audit["findings"] if x["code"] == "QA050"]
    assert len(findings) == 1
    assert findings[0]["severity"] == "BLOCKER"
    assert findings[0]["element"] == "Transformer.TR_AUX_TBC"
    assert audit["summary"]["model_data_ok"] is False


def test_no_solve_state_change_supports_open_tie_preparation():
    core.crear_circuito("rev0_tie", 4.16, bus_fuente="bus_a")
    core.agregar_linea(
        "tie",
        "bus_a",
        "bus_b",
        0.001,
        fases=3,
        r1_ohm_km=0.001,
        x1_ohm_km=0.001,
    )

    opened = core.cambiar_estado_elemento_sin_resolver("Line.tie", abierto=True)
    assert opened["estado"] == "OPEN"
    assert opened["abierto"] is True
    assert opened["solve_performed"] is False
    assert opened["electrical_calculation_performed"] is False

    closed = core.cambiar_estado_elemento_sin_resolver("Line.tie", abierto=False)
    assert closed["estado"] == "CLOSED"
    assert closed["abierto"] is False
    assert closed["solve_performed"] is False


def test_server_signature_exposes_source_bus_and_no_solve_tools():
    import server

    signature = inspect.signature(server.crear_circuito)
    assert "bus_fuente" in signature.parameters
    assert hasattr(server, "abrir_elemento_sin_resolver")
    assert hasattr(server, "cerrar_elemento_sin_resolver")
    assert callable(server.main)


def test_runtime_doctor_runs_without_install_side_effects():
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "runtime_doctor.py"), "--strict"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    result = json.loads(proc.stdout)
    assert result["runtime_ready"] is True
    assert result["installation_performed"] is False
    assert result["repository"]["pyproject_present"] is True
