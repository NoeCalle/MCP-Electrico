"""Diagnóstico local reproducible para MCP Eléctrico.

Distingue fallos de entorno/dependencias de fallos del producto antes de
`primer_uso.py` y REF-01. Genera un JSON autocontenido para soporte.
"""

from __future__ import annotations

import argparse
import importlib
import importlib.metadata
import json
from pathlib import Path
import platform
import struct
import subprocess
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SCHEMA = "MCP_ELECTRICO_LOCAL_DIAGNOSTIC_V1"
MIN_PYTHON = (3, 11)
TESTED_PYTHON_MAX = (3, 13)


def _exc(exc: BaseException) -> str:
    return f"{type(exc).__name__}: {exc}"


def _version(distribution: str) -> str | None:
    try:
        return importlib.metadata.version(distribution)
    except importlib.metadata.PackageNotFoundError:
        return None


def _check(
    cid: str,
    name: str,
    status: str,
    required: bool,
    detail: str,
    suggestion: str | None = None,
    data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if status not in {"OK", "WARN", "FAIL"}:
        raise ValueError(f"Estado inválido: {status}")
    return {
        "id": cid,
        "name": name,
        "status": status,
        "required": required,
        "detail": detail,
        "suggestion": suggestion,
        "data": data or {},
    }


def _package_check(distribution: str, module: str) -> tuple[dict[str, Any], dict[str, Any]]:
    version = _version(distribution)
    info = {
        "distribution": distribution,
        "module": module,
        "version": version,
        "import_ok": False,
        "error": None,
    }
    try:
        importlib.import_module(module)
        info["import_ok"] = True
        return (
            _check(
                f"package_{module.replace('.', '_')}",
                f"Import de {distribution}",
                "OK",
                True,
                f"{distribution} importable; versión={version or 'UNKNOWN'}.",
                data={"version": version, "module": module},
            ),
            info,
        )
    except Exception as exc:
        info["error"] = _exc(exc)
        return (
            _check(
                f"package_{module.replace('.', '_')}",
                f"Import de {distribution}",
                "FAIL",
                True,
                f"No se pudo importar {module}: {_exc(exc)}",
                "Activa el mismo venv que usarás con MCP y ejecuta: python -m pip install -r requirements.txt",
                data={"version": version, "module": module},
            ),
            info,
        )


def _git_check() -> tuple[dict[str, Any], dict[str, Any]]:
    try:
        done = subprocess.run(
            ["git", "--version"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        text = (done.stdout or done.stderr).strip()
        if done.returncode == 0:
            return _check("git_cli", "Git CLI", "OK", False, text), {
                "available": True,
                "version_text": text,
            }
        return _check(
            "git_cli",
            "Git CLI",
            "WARN",
            False,
            f"git --version devolvió {done.returncode}: {text}",
            "Git no bloquea un circuito ya clonado, pero sí actualizaciones y trazabilidad de revisiones.",
        ), {"available": False, "version_text": text}
    except Exception as exc:
        return _check(
            "git_cli",
            "Git CLI",
            "WARN",
            False,
            f"Git no está disponible desde este entorno: {_exc(exc)}",
            "Instala Git o agrega git.exe al PATH si necesitas actualizar el repositorio.",
        ), {"available": False, "error": _exc(exc)}


def _opendss_smoke() -> tuple[dict[str, Any], dict[str, Any]]:
    try:
        from opendssdirect import dss

        dss("Clear")
        dss("New Circuit.diag_local BasekV=0.48 pu=1.0 phases=3 bus1=sourcebus")
        dss(
            "New Load.diag_load bus1=sourcebus.1.2.3 phases=3 conn=wye model=1 "
            "kV=0.48 kW=10 kvar=2"
        )
        dss("Solve")
        converged = bool(dss.Solution.Converged())
        circuit = str(dss.Circuit.Name() or "")
        dss("Clear")
        if not converged:
            return _check(
                "opendss_direct_smoke",
                "Smoke directo OpenDSS",
                "FAIL",
                True,
                "OpenDSS cargó, pero el circuito mínimo no convergió.",
                "Conserva el JSON y revisa instalación/binarios antes de ejecutar estudios.",
            ), {"converged": False, "circuit": circuit}
        return _check(
            "opendss_direct_smoke",
            "Smoke directo OpenDSS",
            "OK",
            True,
            f"Circuito mínimo '{circuit}' convergió.",
        ), {"converged": True, "circuit": circuit}
    except Exception as exc:
        return _check(
            "opendss_direct_smoke",
            "Smoke directo OpenDSS",
            "FAIL",
            True,
            f"No se pudo ejecutar OpenDSSDirect: {_exc(exc)}",
            "Verifica que python y pip pertenezcan al mismo entorno y reinstala requirements.txt.",
        ), {"converged": False, "error": _exc(exc)}


def _server_smoke() -> tuple[dict[str, Any], dict[str, Any]]:
    """Comprueba solo la API pública realmente usada para el flujo mínimo.

    La matriz de motores se valida por separado en `engine_selection`; no se
    exige que `server.py` duplique ese contrato interno.
    """
    try:
        server = importlib.import_module("server")
        required_api = ("crear_circuito", "agregar_carga", "ejecutar_flujo_potencia")
        missing = [name for name in required_api if not callable(getattr(server, name, None))]
        if missing:
            return _check(
                "server_public_api",
                "API pública MCP",
                "FAIL",
                True,
                f"server.py importó, pero faltan tools públicas requeridas: {missing}",
                "Confirma que estás usando una copia completa y actualizada de main.",
            ), {"import_ok": True, "missing_api": missing, "converged": False}

        server.crear_circuito("diagnostico_local_public_api", 0.48)
        server.agregar_carga("diag_load", "sourcebus", 5.0, 1.0, kv=0.48)
        flow = server.ejecutar_flujo_potencia()
        converged = bool(flow.get("convergio"))
        if not converged:
            return _check(
                "server_public_api",
                "API pública MCP",
                "FAIL",
                True,
                "La API pública importó, pero su flujo mínimo no convergió.",
                "Conserva el JSON y ejecuta primer_uso.py para aislar el fallo.",
            ), {"import_ok": True, "missing_api": [], "converged": False}
        return _check(
            "server_public_api",
            "API pública MCP",
            "OK",
            True,
            "server.py importable y flujo mínimo por API pública convergente.",
        ), {"import_ok": True, "missing_api": [], "converged": True}
    except Exception as exc:
        return _check(
            "server_public_api",
            "API pública MCP",
            "FAIL",
            True,
            f"No se pudo importar/ejecutar server.py: {_exc(exc)}",
            "Ejecuta desde la raíz del repo con el venv activo y requirements.txt instalado.",
        ), {"import_ok": False, "converged": False, "error": _exc(exc)}


def run(output: str | Path = "diagnostico_local.json") -> dict[str, Any]:
    output_path = Path(output).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    checks: list[dict[str, Any]] = []

    runtime = {
        "python_version": platform.python_version(),
        "python_executable": sys.executable,
        "platform": platform.platform(),
        "system": platform.system(),
        "machine": platform.machine(),
        "architecture_bits": struct.calcsize("P") * 8,
        "cwd": str(Path.cwd().resolve()),
        "repo_root": str(ROOT),
        "filesystem_encoding": sys.getfilesystemencoding(),
        "stdout_encoding": getattr(sys.stdout, "encoding", None),
        "virtualenv_active": sys.prefix != getattr(sys, "base_prefix", sys.prefix),
    }

    py_now = sys.version_info[:2]
    if py_now < MIN_PYTHON:
        checks.append(_check(
            "python_version", "Versión de Python", "FAIL", True,
            f"Python {platform.python_version()} es menor que 3.11.",
            "Instala Python 3.11 o superior y recrea el entorno virtual.",
        ))
    elif py_now > TESTED_PYTHON_MAX:
        checks.append(_check(
            "python_version", "Versión de Python", "WARN", False,
            f"Python {platform.python_version()} supera la matriz CI probada actualmente (hasta 3.13).",
            "Si aparece un error de dependencia, repite con una versión dentro de la matriz probada.",
        ))
    else:
        checks.append(_check(
            "python_version", "Versión de Python", "OK", True,
            f"Python {platform.python_version()} dentro de la matriz soportada para este diagnóstico.",
        ))

    bits = runtime["architecture_bits"]
    checks.append(_check(
        "python_architecture",
        "Arquitectura Python",
        "OK" if bits == 64 else "FAIL",
        True,
        f"Intérprete de {bits} bits.",
        None if bits == 64 else "Usa Python de 64 bits para dependencias científicas/OpenDSS.",
    ))

    checks.append(_check(
        "virtualenv",
        "Entorno virtual",
        "OK" if runtime["virtualenv_active"] else "WARN",
        False,
        "Entorno virtual activo." if runtime["virtualenv_active"] else "No se detectó venv/virtualenv activo.",
        None if runtime["virtualenv_active"] else "Recomendado: python -m venv venv y activar antes de instalar requirements.txt.",
    ))

    required_paths = [ROOT / "server.py", ROOT / "requirements.txt", ROOT / "mcp_electrico"]
    missing_paths = [str(path) for path in required_paths if not path.exists()]
    checks.append(_check(
        "repo_layout",
        "Estructura del repositorio",
        "FAIL" if missing_paths else "OK",
        True,
        f"Faltantes: {missing_paths}" if missing_paths else "server.py, requirements.txt y mcp_electrico/ presentes.",
        "Ejecuta desde una copia completa del repositorio." if missing_paths else None,
    ))

    try:
        probe = output_path.parent / ".mcp_electrico_write_probe"
        probe.write_text("ok\n", encoding="utf-8")
        probe.unlink(missing_ok=True)
        checks.append(_check(
            "output_write", "Permiso de escritura", "OK", True,
            f"Se puede escribir en {output_path.parent}.",
        ))
    except Exception as exc:
        checks.append(_check(
            "output_write", "Permiso de escritura", "FAIL", True,
            f"No se puede escribir en {output_path.parent}: {_exc(exc)}",
            "Elige una carpeta local con permisos de escritura.",
        ))

    git_check, git = _git_check()
    checks.append(git_check)

    packages: dict[str, Any] = {}
    for distribution, module in (
        ("mcp", "mcp"),
        ("opendssdirect.py", "opendssdirect"),
        ("pandapower", "pandapower"),
        ("networkx", "networkx"),
    ):
        check, info = _package_check(distribution, module)
        checks.append(check)
        packages[distribution] = info

    dss_check, opendss_smoke = _opendss_smoke()
    checks.append(dss_check)
    server_check, server_smoke = _server_smoke()
    checks.append(server_check)

    engine_policy: dict[str, Any] = {}
    try:
        from mcp_electrico import engine_selection

        capabilities = engine_selection.obtener_capacidades_motores()
        iec60909 = (capabilities.get("studies") or {}).get("iec60909") or {}
        engine_policy = {
            "automatic_dispatch": capabilities.get("automatic_dispatch"),
            "crosscheck": capabilities.get("crosscheck"),
            "default_engine": capabilities.get("default_engine"),
            "iec60909_preferred": iec60909.get("preferred"),
            "iec60909_implemented": iec60909.get("implemented"),
        }
        policy_ok = (
            engine_policy["automatic_dispatch"] is False
            and engine_policy["crosscheck"] is False
            and engine_policy["default_engine"] == "opendss"
            and engine_policy["iec60909_preferred"] == "pandapower"
            and engine_policy["iec60909_implemented"] is False
        )
        checks.append(_check(
            "engine_policy", "Política determinista de motores",
            "OK" if policy_ok else "FAIL", True,
            "Matriz E coherente: OpenDSS default, sin despacho/cross-check y IEC 60909 aún no implementado."
            if policy_ok else f"Política inesperada: {engine_policy}",
            None if policy_ok else "No ejecutes estudios hasta confirmar la revisión instalada.",
        ))
    except Exception as exc:
        engine_policy = {"error": _exc(exc)}
        checks.append(_check(
            "engine_policy", "Política determinista de motores", "FAIL", True,
            f"No se pudo leer la matriz E: {_exc(exc)}",
            "Verifica dependencias y consistencia entre server.py y mcp_electrico/.",
        ))

    p3_gate: dict[str, Any] = {}
    maturity: dict[str, Any] = {}
    try:
        from mcp_electrico import p3_completion, validation_status

        gate = p3_completion.evaluar_cierre_p3()
        p3_gate = {
            "phase_status": gate.get("phase_status"),
            "ready_for_next_phase": gate.get("ready_for_next_phase"),
            "next_phase": gate.get("next_phase"),
            "professional_emission": gate.get("professional_emission"),
            "pending_criteria": gate.get("pending_criteria"),
        }
        gate_ok = (
            p3_gate["phase_status"] == "READY_WITH_LIMITATIONS"
            and p3_gate["ready_for_next_phase"] is True
            and p3_gate["next_phase"] == "P4_IEC_60909"
            and p3_gate["professional_emission"] is False
        )
        checks.append(_check(
            "p3_gate", "Gate P3", "OK" if gate_ok else "FAIL", True,
            "P3-v1 cerrada con limitaciones y P4 formalmente habilitada; emisión global sigue bloqueada."
            if gate_ok else f"Gate P3 inesperado: {p3_gate}",
            None if gate_ok else "Confirma que estás en main actualizado y conserva este JSON.",
        ))

        maturity = {
            "ampacity": validation_status.get_module_status("ampacity"),
            "short_circuit": validation_status.get_module_status("short_circuit"),
        }
        maturity_ok = (
            maturity["ampacity"].get("status") == "VALIDATED_WITH_LIMITATIONS"
            and maturity["short_circuit"].get("status") == "UNDER_VALIDATION"
        )
        checks.append(_check(
            "maturity_barrier", "Barrera de madurez",
            "OK" if maturity_ok else "FAIL", True,
            "Ampacidad validada con limitaciones; cortocircuito continúa UNDER_VALIDATION hasta P4."
            if maturity_ok else f"Madurez inesperada: {maturity}",
            None if maturity_ok else "No presentes FaultStudy como IEC 60909.",
        ))
    except Exception as exc:
        p3_gate = {"error": _exc(exc)}
        maturity = {"error": _exc(exc)}
        checks.append(_check(
            "p3_gate", "Gate P3", "FAIL", True,
            f"No se pudo evaluar P3/madurez: {_exc(exc)}",
            "Verifica que datasets y módulos mcp_electrico estén completos.",
        ))

    fatal = [c for c in checks if c["required"] and c["status"] == "FAIL"]
    warnings = [c for c in checks if c["status"] == "WARN"]
    nonfatal = [c for c in checks if not c["required"] and c["status"] == "FAIL"]
    ok = not fatal
    overall_status = "FAIL" if not ok else ("OK_WITH_WARNINGS" if warnings or nonfatal else "OK")

    result = {
        "schema": SCHEMA,
        "ok": ok,
        "overall_status": overall_status,
        "summary": {
            "total_checks": len(checks),
            "ok_checks": sum(c["status"] == "OK" for c in checks),
            "warnings": len(warnings),
            "fatal_failures": len(fatal),
            "nonfatal_failures": len(nonfatal),
        },
        "runtime": runtime,
        "git": git,
        "packages": packages,
        "opendss_smoke": opendss_smoke,
        "server_smoke": server_smoke,
        "engine_policy": engine_policy,
        "p3_gate": p3_gate,
        "maturity": maturity,
        "checks": checks,
        "recommended_next_steps": [
            "Si ok=true, ejecutar: python examples/primer_uso.py",
            "Después ejecutar: python examples/caso_referencia_01.py",
            "Si cualquiera falla, conservar este JSON junto con los JSON de esas pruebas.",
        ],
        "outputs": {"diagnostic_json": str(output_path)},
        "professional_emission": False,
    }
    output_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    return result


def _print_summary(result: dict[str, Any]) -> None:
    print("MCP Eléctrico — diagnóstico local")
    print(f"Resultado: {result['overall_status']}")
    for item in result["checks"]:
        marker = {"OK": "[OK]", "WARN": "[WARN]", "FAIL": "[FAIL]"}[item["status"]]
        print(f"{marker} {item['name']}: {item['detail']}")
    print(f"JSON: {result['outputs']['diagnostic_json']}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Diagnóstico local de MCP Eléctrico")
    parser.add_argument(
        "--output",
        default="diagnostico_local.json",
        help="Ruta del JSON de diagnóstico (default: diagnostico_local.json)",
    )
    args = parser.parse_args()
    result = run(args.output)
    _print_summary(result)
    if not result["ok"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
