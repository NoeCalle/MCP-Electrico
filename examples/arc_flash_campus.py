"""
Demostración educativa del método de Lee sobre dos tableros del campus.

IMPORTANTE:
- No es un estudio IEEE 1584-2018.
- Los tableros de 0.4 kV están dentro del rango donde un estudio real debe
  aplicar el modelo vigente correspondiente; aquí Lee se usa solo para
  ilustrar sensibilidad a corriente, tiempo y distancia.
- No se asignan categorías PPE.
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import server


def construir_campus():
    server.crear_circuito("campus_hospitalario", kv_base=13.2)
    server.agregar_transformador(
        "trafo_quirofanos",
        "sourcebus",
        "tablero_quirofanos",
        kva=300,
        kv_primario=13.2,
        kv_secundario=0.4,
    )
    server.agregar_transformador(
        "trafo_hospitalizacion",
        "sourcebus",
        "tablero_hospitalizacion",
        kva=400,
        kv_primario=13.2,
        kv_secundario=0.4,
    )
    server.agregar_carga(
        "quirofano_1", "tablero_quirofanos", 35, 15, kv=0.4, critica=True
    )
    server.agregar_carga(
        "uci", "tablero_hospitalizacion", 60, 25, kv=0.4, critica=True
    )


def main():
    print("=" * 60)
    print("DEMOSTRACIÓN ARC FLASH — MÉTODO DE LEE")
    print("=" * 60)
    print("\n⚠ Solo aprendizaje. No usar para selección de EPP.\n")

    construir_campus()
    server.ejecutar_flujo_potencia()

    escenarios = [
        {
            "bus": "tablero_quirofanos",
            "voltaje_kv": 0.4,
            "tiempo_s": 0.2,
            "nota": "tiempo de despeje ilustrativo 0.2 s",
        },
        {
            "bus": "tablero_hospitalizacion",
            "voltaje_kv": 0.4,
            "tiempo_s": 0.5,
            "nota": "tiempo de despeje ilustrativo 0.5 s",
        },
    ]

    for esc in escenarios:
        print(f"\n--- {esc['bus']} ({esc['nota']}) ---")
        sc = server.ejecutar_cortocircuito(esc["bus"])
        corriente_ka = max(sc["corriente_falla_amperios"]) / 1000
        print(f"Corriente de falla trifásica: {corriente_ka:.2f} kA")

        resultado = server.estimar_arc_flash_lee(
            voltaje_kv=esc["voltaje_kv"],
            corriente_falla_ka=corriente_ka,
            tiempo_despeje_s=esc["tiempo_s"],
            distancia_trabajo_mm=455,
        )
        print(json.dumps(resultado, indent=2, ensure_ascii=False))

    print(
        "\nLa comparación ilustra que, manteniendo los demás parámetros, "
        "la energía estimada aumenta con el tiempo de exposición/despeje. "
        "La conclusión didáctica no sustituye una coordinación TCC ni un "
        "estudio de arc flash normado."
    )


if __name__ == "__main__":
    main()
