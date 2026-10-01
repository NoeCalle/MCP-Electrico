"""Exercise the installed server through its public MCP protocol."""
from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamable_http_client

ROOT = Path(__file__).resolve().parents[1]


def fixture(name: str) -> dict:
    return json.loads((ROOT / "examples" / name).read_text(encoding="utf-8"))


async def verify(session: ClientSession, output: Path) -> dict:
    await session.initialize()
    names = {tool.name for tool in (await session.list_tools()).tools}
    required = {
        "construir_modelo_rev0", "ejecutar_flujo_potencia",
        "generar_dossier_piloto_real", "generar_dossier_escenarios_operativos",
        "generar_dossier_arranque_motores", "ejecutar_secuencias_arranque_motores",
        "verificar_integridad_dossier_arranque_motores",
        "obtener_contrato_dinamica_motores", "validar_datos_dinamica_motores",
        "obtener_plan_validacion_dinamica_motores",
        "generar_dossier_dinamica_motores", "ejecutar_dinamica_motores",
        "validar_ejecucion_dinamica_motores", "verificar_integridad_dossier_dinamica_motores",
        "exportar_laminas_unifilar",
    }
    if missing := required - names:
        raise RuntimeError(f"Missing public MCP tools: {sorted(missing)}")

    async def call(name: str, **arguments) -> dict:
        result = await session.call_tool(name, arguments=arguments)
        if result.isError:
            raise RuntimeError(f"{name}: {result.content}")
        data = result.structuredContent
        if data is None:
            data = json.loads(next(item.text for item in result.content if item.type == "text"))
        return data

    def expect(data: dict, key: str, value):
        if data.get(key) != value:
            raise RuntimeError(f"Expected {key}={value!r}, received {data}")

    output.mkdir(parents=True, exist_ok=True)
    manifest = fixture("p10_reference_substation_stage1.json")
    built = await call("construir_modelo_rev0", manifest=manifest)
    expect(built, "materializer_status", "MODEL_BUILT_NOT_EXECUTED")
    flow = await call("ejecutar_flujo_potencia")
    expect(flow, "convergio", True)
    sheets = await call("exportar_laminas_unifilar", ruta_html=str(output / "unifilar_laminas.html"))
    expect(sheets, "status", "VISUAL_SHEETS_READY")
    real = await call(
        "generar_dossier_piloto_real",
        manifest=fixture("p10_reference_substation_stage5.json"),
        directorio_salida=str(output / "reference_dossier"),
    )
    expect(real, "status", "DOSSIER_READY_ENGINEERING_PREVIEW")
    expect(real, "p8d2_execution_status", "PROTECTION_EXECUTION_COMPLETED")
    real_check = await call("verificar_integridad_dossier_real", ruta_indice=real["integrity"]["index_path"])
    expect(real_check, "ok", True)
    scenarios = await call(
        "generar_dossier_escenarios_operativos", manifest=manifest,
        paquete_escenarios=fixture("p12e_alternative_source_transfer_reference.json"),
        directorio_salida=str(output / "scenario_dossier"),
    )
    expect(scenarios, "status", "SCENARIO_DOSSIER_READY")
    scenario_check = await call("verificar_integridad_dossier_escenarios", ruta_indice=scenarios["integrity"]["index_path"])
    expect(scenario_check, "ok", True)
    before = await call("obtener_estado_workspace")
    motor_manifest = fixture("p13_motor_starting_multi_stage3.json")
    dynamic_contract = await call("obtener_contrato_dinamica_motores")
    expect(dynamic_contract, "ready_for_execution", False)
    dynamic_admission = await call(
        "validar_datos_dinamica_motores", manifest=motor_manifest,
        paquete_dinamico=fixture("p13_motor_dynamics_reference.json"),
    )
    expect(dynamic_admission, "data_ready", True)
    expect(dynamic_admission, "ready_for_execution", False)
    expect(dynamic_admission, "dynamic_integration_performed", False)
    qualification = await call("obtener_plan_validacion_dinamica_motores")
    expect(qualification, "selected_backend", "MCP_BALANCED_RMS_RK4_V1")
    expect(qualification, "backend_benchmarks_run", True)
    dynamic_dossier = await call(
        "generar_dossier_dinamica_motores", manifest=fixture("p13_dynamic_rms_manifest.json"),
        paquete_dinamico=fixture("p13_dynamic_rms_package.json"), opciones=fixture("p13_dynamic_rms_options.json"),
        directorio_salida=str(output / "dynamic_dossier"),
    )
    expect(dynamic_dossier, "status", "DYNAMIC_DOSSIER_READY")
    dynamic_check = await call("verificar_integridad_dossier_dinamica_motores", ruta_indice=dynamic_dossier["index_path"])
    expect(dynamic_check, "ok", True)
    if before != await call("obtener_estado_workspace"):
        raise RuntimeError("P13F1 preparation mutated the parent workspace")
    (output / "dynamic_preparation.json").write_text(
        json.dumps({"admission": dynamic_admission, "qualification_plan": qualification}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    profiles = fixture("p13_motor_starting_multi_profiles_stage3.json")
    sequences = fixture("p13_motor_starting_sequence_stage3.json")
    contract = await call("obtener_contrato_arranque_motores")
    expect(contract, "dynamic_integration_performed", False)
    await call("validar_arranque_motores", manifest=motor_manifest)
    static = await call("ejecutar_arranque_motores", manifest=motor_manifest)
    expect(static, "execution_status", "STATIC_MOTOR_STARTING_COMPLETED")
    await call("validar_perfiles_arranque_motores", manifest=motor_manifest, paquete_perfiles=profiles)
    profile_result = await call("ejecutar_perfiles_arranque_motores", manifest=motor_manifest, paquete_perfiles=profiles)
    expect(profile_result, "execution_status", "STATIC_STARTING_PROFILE_COMPLETED")
    await call("validar_secuencias_arranque_motores", manifest=motor_manifest, paquete_perfiles=profiles, paquete_secuencias=sequences)
    sequence_result = await call("ejecutar_secuencias_arranque_motores", manifest=motor_manifest, paquete_perfiles=profiles, paquete_secuencias=sequences)
    expect(sequence_result, "execution_status", "STATIC_MOTOR_SEQUENCE_COMPLETED")
    motors = await call(
        "generar_dossier_arranque_motores",
        manifest=motor_manifest,
        paquete_perfiles=profiles,
        paquete_secuencias=sequences,
        directorio_salida=str(output / "motor_dossier"),
    )
    expect(motors, "status", "MOTOR_STARTING_DOSSIER_READY")
    expect(motors, "parent_context_mutated", False)
    expect(motors["replay"], "match", True)
    after = await call("obtener_estado_workspace")
    if before != after:
        raise RuntimeError("Motor study mutated the parent workspace")
    motor_check = await call("verificar_integridad_dossier_arranque_motores", ruta_indice=motors["integrity"]["index_path"])
    expect(motor_check, "ok", True)
    summary = {
        "status": "LOCAL_MCP_VERIFIED", "public_tool_count": len(names),
        "powerflow_converged": True, "motor_replay_match": True,
        "parent_workspace_preserved": True, "all_dossier_hashes_verified": True,
        "dynamic_input_preparation_verified": True, "dynamic_backend_qualified": True,
        "dynamic_backend_scope": "BALANCED_RMS_QUASI_STEADY_ELECTROMECHANICAL",
        "rms_dynamic_execution_verified": True, "rms_dynamic_replay_verified": True,
        "professional_emission": False,
        "dossiers": {"reference": real, "scenarios": scenarios, "motors": motors, "dynamic_motors": dynamic_dossier},
    }
    (output / "verification.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


async def run(url: str | None, output: Path) -> dict:
    if url:
        async with streamable_http_client(url) as (read, write, _):
            async with ClientSession(read, write) as session:
                return await verify(session, output)
    env = dict(os.environ, PYTHONUTF8="1")
    parameters = StdioServerParameters(command=sys.executable, args=[str(ROOT / "server.py")], cwd=str(output.parent), env=env)
    async with stdio_client(parameters) as (read, write):
        async with ClientSession(read, write) as session:
            return await verify(session, output)


def main() -> None:
    parser = argparse.ArgumentParser(description="Verifica MCP Eléctrico desde un cliente real")
    parser.add_argument("--url", help="Endpoint local HTTP; sin este argumento utiliza stdio")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "local_data" / "verification")
    args = parser.parse_args()
    output = args.output_dir.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    result = asyncio.run(run(args.url, output))
    print(json.dumps({key: value for key, value in result.items() if key != "dossiers"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
