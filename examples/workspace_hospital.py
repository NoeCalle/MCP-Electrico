"""Ejemplo integral del workspace persistente con estudios operativos.

Construye un circuito hospitalario mediante las mismas tools que usa MCP,
resuelve el flujo, analiza caída de tensión y deja `workspace_hospital.html`
como visor técnico estable con pestañas de estudios.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import server


def main() -> None:
    server.configurar_workspace(
        "workspace_hospital.html",
        titulo="Hospital — Workspace eléctrico",
        auto_regenerar=True,
    )
    server.crear_circuito("hospital_workspace", 22.9)
    server.agregar_transformador(
        "tr_01",
        "sourcebus",
        "tgbt",
        kva=500,
        kv_primario=22.9,
        kv_secundario=0.48,
        conexion_primario="delta",
        conexion_secundario="wye",
    )
    server.agregar_linea(
        "f_motor", "tgbt", "mcc_01", 0.035, r1_ohm_km=0.25, x1_ohm_km=0.12
    )
    server.agregar_linea(
        "f_critico", "tgbt", "tcrit_01", 0.040, r1_ohm_km=0.22, x1_ohm_km=0.11
    )
    server.agregar_carga(
        "motor_bomba", "mcc_01", 75, 30, kv=0.48, tipo_visual="motor"
    )
    server.agregar_carga(
        "cargas_criticas",
        "tcrit_01",
        80,
        25,
        kv=0.48,
        critica=True,
        tipo_visual="tablero",
    )
    server.configurar_etiqueta_carga_unifilar("motor_bomba", "M-01 · BOMBA AGUA")
    server.configurar_etiqueta_carga_unifilar("cargas_criticas", "TABLERO CRÍTICO")
    server.configurar_alimentador_unifilar(
        "Line.f_motor",
        etiqueta="F-01",
        proteccion="mccb",
        conductor="3x70 mm2 Cu XLPE",
        corriente_nominal_a=160,
        capacidad_ruptura_ka=25,
    )
    server.configurar_alimentador_unifilar(
        "Line.f_critico",
        etiqueta="F-02",
        proteccion="mccb",
        conductor="3x50 mm2 Cu XLPE",
        corriente_nominal_a=125,
        capacidad_ruptura_ka=25,
    )

    server.ejecutar_flujo_potencia()
    caida = server.analizar_caida_tension(limite_pct=3.0)
    estado = server.obtener_estado_workspace()
    print({"caida_tension": caida, "estado_workspace": estado})


if __name__ == "__main__":
    main()
