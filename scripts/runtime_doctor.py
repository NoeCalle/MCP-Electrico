"""Diagnóstico de runtime que solo usa la biblioteca estándar.

Puede ejecutarse incluso cuando todavía faltan las dependencias eléctricas/MCP.
No instala paquetes ni modifica el entorno.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import sys

SCHEMA = "MCP_ELECTRICO_RUNTIME_DOCTOR_V1"
MIN_PYTHON = (3, 10)

DEPENDENCIES = [
    ("mcp", "mcp"),
    ("opendssdirect.py", "opendssdirect"),
    ("networkx", "networkx"),
    ("pandapower", "pandapower"),
]


def diagnose() -> dict:
    root = Path(__file__).resolve().parents[1]
    dependencies = []
    for package, module in DEPENDENCIES:
        available = importlib.util.find_spec(module) is not None
        dependencies.append(
            {
                "package": package,
                "module": module,
                "available": available,
            }
        )

    python_ok = sys.version_info[:2] >= MIN_PYTHON
    missing = [item["package"] for item in dependencies if not item["available"]]
    ready = python_ok and not missing

    return {
        "schema": SCHEMA,
        "python": {
            "version": ".".join(str(x) for x in sys.version_info[:3]),
            "minimum": ".".join(str(x) for x in MIN_PYTHON),
            "compatible": python_ok,
            "executable": sys.executable,
        },
        "repository": {
            "root": str(root),
            "server_entrypoint": str(root / "server.py"),
            "pyproject_present": (root / "pyproject.toml").is_file(),
            "server_present": (root / "server.py").is_file(),
        },
        "dependencies": dependencies,
        "missing_packages": missing,
        "runtime_ready": ready,
        "installation_performed": False,
        "recommended_install_command": f'"{sys.executable}" -m pip install -e .',
        "recommended_server_command": f'"{sys.executable}" server.py',
        "note": (
            "Este diagnóstico no instala dependencias. Un entorno que prohíba instalaciones "
            "debe usar una instalación MCP ya preparada o un runtime remoto; el repositorio "
            "no puede ejecutar OpenDSS sin su dependencia nativa."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Devuelve código != 0 cuando el runtime no está listo.",
    )
    args = parser.parse_args()

    result = diagnose()
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["runtime_ready"] or not args.strict else 2


if __name__ == "__main__":
    raise SystemExit(main())
