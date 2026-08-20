"""
Ejemplo: estudio de arc flash (simplificado) en el campus hospitalario.

Usa el método de Lee (ecuación adoptada por IEEE 1584-2002 para
configuraciones al aire libre / fuera del rango del modelo empírico
completo de 1584-2018) para estimar la energía incidente en cada tablero
BT del campus, a partir de la corriente de cortocircuito que ya calcula
OpenDSS.

ADVERTENCIA: esto es un método simplificado para aprendizaje y
estimación de orden de magnitud. NO es un estudio de arc flash normado
— para EPP real se necesita el modelo empírico completo de IEEE
1584-2018 (ETAP u otro software validado) más las curvas TCC reales de
las protecciones instaladas, que este MCP todavía no modela.

Uso:
    python3 examples/arc_flash_campus.py
"""

import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import server


def construir_campus():
    server.crear_circuito("campus_hospitalario", kv_base=13.2)
    server.agregar_transformador(
        "trafo_quirofanos", "sourcebus", "tablero_quirofanos",
        kva=300, kv_primario=13.2, kv_secundario=0.4,
    )
    server.agregar_transformador(
        "trafo_hospitalizacion", "sourcebus", "tablero_hospitalizacion",
        kva=400, kv_primario=13.2, kv_secundario=0.4,
    )
    server.agregar_carga("quirofano_1", "tablero_quirofanos", 35, 15, critica=True)
    server.agregar_carga("uci", "tablero_hospitalizacion", 60, 25, critica=True)


def main():
    print("=" * 60)
    print("ESTUDIO DE ARC FLASH (simplificado) — Campus hospitalario")
    print("=" * 60)
    print("\n⚠ Método de Lee — solo para aprendizaje, no para EPP real.\n")

    construir_campus()
    server.ejecutar_flujo_potencia()

    # Tiempo de despeje asumido por tipo de protección — dato de entrada,
    # ya que este MCP no modela curvas TCC reales todavía.
    escenarios = [
        {"bus": "tablero_quirofanos", "voltaje_kv": 0.4, "tiempo_s": 0.2,
         "nota": "Interruptor termomagnético rápido"},
        {"bus": "tablero_hospitalizacion", "voltaje_kv": 0.4, "tiempo_s": 0.5,
         "nota": "Fusible de tiempo intermedio"},
    ]

    for esc in escenarios:
        print(f"\n--- {esc['bus']} ({esc['nota']}) ---")
        sc = server.ejecutar_cortocircuito(esc["bus"])
        corriente_ka = max(sc["corriente_falla_amperios"]) / 1000
        print(f"Corriente de falla trifásica: {corriente_ka:.2f} kA")

        resultado = server.calcular_arc_flash(
            voltaje_kv=esc["voltaje_kv"],
            corriente_falla_ka=corriente_ka,
            tiempo_despeje_s=esc["tiempo_s"],
            distancia_trabajo_mm=455,
        )
        print(json.dumps(resultado, indent=2, ensure_ascii=False))

    print(
        "\nCompara los dos escenarios: mismo campus, distinto tiempo de "
        "despeje — nota cómo la energía incidente escala directamente "
        "con el tiempo. Esta es la razón por la que la coordinación de "
        "protecciones rápida es una de las formas más efectivas de "
        "reducir el riesgo de arco eléctrico."
    )


if __name__ == "__main__":
    main()
