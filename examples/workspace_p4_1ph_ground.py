"""Caso reproducible P4C11C para Workspace V4 con falla 1F-T.

La temperatura final de 20 °C y los parámetros Z0/C0 son datos explícitos del
fixture de validación. No constituyen valores típicos ni recomendación de diseño.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import server
from mcp_electrico import (
    iec60909_tools,
    professional_data,
    workspace_state,
    zero_sequence,
)


def main() -> None:
    server.configurar_workspace(
        "workspace_p4_1ph_ground.html",
        titulo="P4 — Workspace V4 IEC 60909 1F-T",
        auto_regenerar=True,
    )
    server.crear_circuito("workspace_p4_1ph_ground", 22.9)
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
    server.configurar_bus_unifilar("bus1", rol="barra", etiqueta="BARRA DE FALLA 1F-T")

    professional_data.definir_red_equivalente(
        kv_ll=22.9,
        scc_max_mva=500.0,
        x_r_max=10.0,
        scc_min_mva=250.0,
        x_r_min=5.0,
        fuente_referencia="P4C11C fixture versionado",
    )
    zero_sequence.definir_fuente(
        r0_max_ohm=0.30,
        x0_max_ohm=0.90,
        r0_min_ohm=0.50,
        x0_min_ohm=1.20,
        fuente_referencia="P4C11C fixture Z0 fuente",
    )
    zero_sequence.definir_linea(
        "Line.f1",
        r0_ohm_km=0.60,
        x0_ohm_km=0.30,
        c0_nf_km=10.0,
        fuente_referencia="P4C11C fixture Z0/C0 línea",
    )
    workspace_state.mark_model_changed("workspace_p4_1ph_ground_fixture:datos_p2_z0")

    server.ejecutar_flujo_potencia()
    result = iec60909_tools.ejecutar_cortocircuito_iec60909_1ph_ground(
        "bus1",
        line_endtemp_degree_c={"Line.f1": 20.0},
        lv_tol_percent=10,
    )
    print({
        "ok": result["ok"],
        "fault": result["fault"],
        "bus": result["bus"],
        "max": result["scenarios"]["max"].get("results"),
        "min": result["scenarios"]["min"].get("results"),
        "negative_sequence_policy": result["negative_sequence_policy"],
        "zero_sequence_policy": result["zero_sequence_policy"],
        "professional_emission": result["professional_emission"],
    })


if __name__ == "__main__":
    main()
