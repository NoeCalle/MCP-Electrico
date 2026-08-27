"""Caso reproducible P4C11A para el workspace V4.

La temperatura final de 20 °C es un dato explícito de este fixture matemático
para conservar K_L=1 en el caso mínimo. No es una recomendación de diseño.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import server
from mcp_electrico import professional_data, workspace_state


def main() -> None:
    server.configurar_workspace(
        "workspace_p4_3ph.html",
        titulo="P4 — Workspace V4 IEC 60909",
        auto_regenerar=True,
    )
    server.crear_circuito("workspace_p4_3ph", 22.9)
    server.agregar_linea(
        "f1",
        "sourcebus",
        "bus1",
        0.25,
        fases=3,
        r1_ohm_km=0.18,
        x1_ohm_km=0.09,
    )
    server.agregar_carga("carga1", "bus1", 100.0, 25.0, fases=3, kv=22.9)
    server.configurar_bus_unifilar("bus1", rol="barra", etiqueta="BARRA DE FALLA")
    server.configurar_alimentador_unifilar(
        "Line.f1",
        etiqueta="F-01",
        proteccion="breaker",
        conductor="fixture R1/X1 explícito",
    )

    # professional_tools expone esta misma operación como tool MCP; el ejemplo
    # Python usa la capa de dominio directamente y sincroniza la revisión.
    professional_data.definir_red_equivalente(
        kv_ll=22.9,
        scc_max_mva=500.0,
        x_r_max=10.0,
        scc_min_mva=250.0,
        x_r_min=5.0,
        fuente_referencia="P4C11A fixture versionado",
    )
    workspace_state.mark_model_changed("workspace_p4_fixture:definir_red_equivalente")

    server.ejecutar_flujo_potencia()
    result = server.ejecutar_cortocircuito_iec60909_3ph(
        "bus1",
        line_endtemp_degree_c={"Line.f1": 20.0},
        calcular_ip_ith=True,
        topology="radial",
        tk_s=0.2,
        kappa_method="C",
    )
    print({
        "ok": result["ok"],
        "bus": result["bus"],
        "max": result["scenarios"]["max"].get("results"),
        "min": result["scenarios"]["min"].get("results"),
        "professional_emission": result["professional_emission"],
    })


if __name__ == "__main__":
    main()
