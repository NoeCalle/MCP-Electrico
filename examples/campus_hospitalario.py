"""
Ejemplo: campus hospitalario con múltiples edificios/tableros.

Modela un hospital más realista que hospital_basico.py: una sola
acometida en MT alimenta tres transformadores independientes, cada uno
sirviendo un edificio/área distinta con sus propias cargas:

  - Quirófanos      (300 kVA) -> 2 quirófanos (críticos)
  - Hospitalización (400 kVA) -> UCI (crítica) + 2 pisos generales
  - Administración  (150 kVA) -> oficinas + cafetería

Un generador de respaldo protege específicamente el tablero de
quirófanos (donde están las cargas más críticas del campus).

Genera un diagrama unifilar interactivo mostrando todos los tableros,
transformadores, cargas (resaltando las críticas) y el generador.

Uso:
    python3 examples/campus_hospitalario.py
"""

import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import server


def main():
    print("=" * 60)
    print("CASO DE ESTUDIO: Campus hospitalario multi-tablero")
    print("=" * 60)

    print("\n--- 1. Circuito y acometida MT ---")
    print(server.crear_circuito("campus_hospitalario", kv_base=13.2))

    print("\n--- 2. Transformadores por edificio ---")
    print(
        server.agregar_transformador(
            "trafo_quirofanos", "sourcebus", "tablero_quirofanos",
            kva=300, kv_primario=13.2, kv_secundario=0.4,
        )
    )
    print(
        server.agregar_transformador(
            "trafo_hospitalizacion", "sourcebus", "tablero_hospitalizacion",
            kva=400, kv_primario=13.2, kv_secundario=0.4,
        )
    )
    print(
        server.agregar_transformador(
            "trafo_administracion", "sourcebus", "tablero_administracion",
            kva=150, kv_primario=13.2, kv_secundario=0.4,
        )
    )

    print("\n--- 3. Cargas por tablero ---")
    print(server.agregar_carga("quirofano_1", "tablero_quirofanos", 35, 15, critica=True))
    print(server.agregar_carga("quirofano_2", "tablero_quirofanos", 35, 15, critica=True))
    print(server.agregar_carga("uci", "tablero_hospitalizacion", 60, 25, critica=True))
    print(server.agregar_carga("piso_2", "tablero_hospitalizacion", 40, 15))
    print(server.agregar_carga("piso_3", "tablero_hospitalizacion", 40, 15))
    print(server.agregar_carga("oficinas", "tablero_administracion", 25, 8))
    print(server.agregar_carga("cafeteria", "tablero_administracion", 15, 5))

    print("\n--- 4. Generador de respaldo (protege el tablero más crítico) ---")
    print(
        server.agregar_generador_respaldo(
            "ge_criticos", "tablero_quirofanos", kw=150, kv=0.4
        )
    )

    print("\n--- 5. Flujo de potencia ---")
    resultado = server.ejecutar_flujo_potencia()
    print(f"Convergió: {resultado['convergio']}")
    print(f"Pérdidas: {resultado['perdidas_totales_kw']} kW / {resultado['perdidas_totales_kvar']} kVAR")
    for bus, datos in resultado["voltajes_por_bus"].items():
        print(f"  {bus}: {datos['voltajes_pu']} pu (base {datos['kv_base']} kV)")

    print("\n--- 6. Diagrama unifilar ---")
    diagrama = server.generar_diagrama_unifilar("diagrama_campus.html")
    print(json.dumps(diagrama, indent=2, ensure_ascii=False))
    print("\nAbre diagrama_campus.html en tu navegador para ver el resultado.")

    print("\n--- 7. Análisis N-1: ¿qué pasa si falla el trafo de hospitalización? ---")
    contingencia = server.simular_perdida_alimentador("Transformer.trafo_hospitalizacion")
    print(json.dumps(contingencia, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
