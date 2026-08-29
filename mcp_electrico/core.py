"""
Motor eléctrico desacoplado del transporte MCP.

Las funciones de este módulo pueden probarse directamente sin arrancar un
servidor MCP. OpenDSS conserva el modelo activo en memoria del proceso.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from opendssdirect import dss


_cargas_criticas: set[str] = set()
_voltage_bases: set[float] = set()
_bus_voltage_bases_ll: dict[str, float] = {}


def _bus_key(raw: str) -> str:
    return str(raw).split(".")[0].strip().lower()


def _record_bus_voltage_base(bus: str, kv_ll: float, *, overwrite: bool = False) -> None:
    """Registra un nivel nominal LL explícito para una barra conocida."""
    if kv_ll <= 0:
        return
    key = _bus_key(bus)
    if not key:
        return
    if overwrite or key not in _bus_voltage_bases_ll:
        _bus_voltage_bases_ll[key] = float(kv_ll)


def _recalcular_bases_de_tension() -> None:
    """Recalcula bases y luego fija las barras con niveles nominales conocidos.

    ``CalcVoltageBases`` conserva el comportamiento general de OpenDSS. Los
    niveles bus->kVLL registrados explícitamente por el MCP se vuelven a aplicar
    después mediante ``SetkVBase`` para que una inferencia del motor no gane
    sobre la tensión declarada por circuito, transformador, carga o generador.
    """
    if not _voltage_bases:
        return
    niveles = ",".join(str(v) for v in sorted(_voltage_bases, reverse=True))
    dss(f"Set VoltageBases=[{niveles}]")
    dss("CalcVoltageBases")
    for bus, kv_ll in sorted(_bus_voltage_bases_ll.items()):
        dss(f"SetkVBase Bus={bus} kVLL={kv_ll}")


def _elemento_existe(nombre_elemento: str) -> bool:
    """Activa un elemento y devuelve True si OpenDSS lo encontró."""
    try:
        return bool(dss.Circuit.SetActiveElement(nombre_elemento))
    except Exception:
        return False


def _estado_elemento_abierto(nombre_elemento: str) -> bool:
    if not _elemento_existe(nombre_elemento):
        raise ValueError(f"Elemento no encontrado en el circuito: {nombre_elemento}")
    return bool(dss.CktElement.IsOpen(1, 0))


def _voltajes_bus_pu(bus: str) -> list[float]:
    dss.Circuit.SetActiveBus(bus)
    return [float(v) for v in dss.Bus.puVmagAngle()[0::2]]


def _estado_cargas_criticas() -> list[dict[str, Any]]:
    """
    Resume si cada carga crítica conserva tensión.

    El umbral de 0.1 pu solo distingue una barra esencialmente desenergizada
    de una barra con tensión; NO es un criterio de cumplimiento de calidad.
    """
    estados: list[dict[str, Any]] = []
    for nombre in sorted(_cargas_criticas):
        if nombre not in dss.Loads.AllNames():
            continue
        dss.Loads.Name(nombre)
        buses = dss.CktElement.BusNames()
        if not buses:
            continue
        bus = buses[0].split(".")[0]
        vpu = _voltajes_bus_pu(bus)
        estados.append(
            {
                "carga": nombre,
                "bus": bus,
                "voltajes_pu": [round(v, 4) for v in vpu],
                "energizada": bool(vpu) and max(vpu) >= 0.1,
            }
        )
    return estados


def crear_circuito(nombre: str, kv_base: float, frecuencia: int = 60) -> str:
    """Crea un circuito nuevo y limpia también el estado auxiliar del MCP."""
    if kv_base <= 0:
        raise ValueError("kv_base debe ser mayor que cero.")
    if frecuencia <= 0:
        raise ValueError("frecuencia debe ser mayor que cero.")

    dss("Clear")
    dss(
        f"New Circuit.{nombre} basekv={kv_base} Frequency={frecuencia}"
    )

    global _voltage_bases, _bus_voltage_bases_ll
    _voltage_bases = {float(kv_base)}
    _bus_voltage_bases_ll = {"sourcebus": float(kv_base)}
    _cargas_criticas.clear()
    _recalcular_bases_de_tension()
    return f"Circuito '{nombre}' creado a {kv_base} kV, {frecuencia} Hz"


def agregar_linea(
    nombre: str,
    bus1: str,
    bus2: str,
    longitud_km: float,
    fases: int = 3,
    r1_ohm_km: float = 0.3,
    x1_ohm_km: float = 0.4,
) -> str:
    if longitud_km <= 0:
        raise ValueError("longitud_km debe ser mayor que cero.")
    if fases not in (1, 2, 3):
        raise ValueError("fases debe ser 1, 2 o 3.")

    dss(
        f"New Line.{nombre} Bus1={bus1} Bus2={bus2} Length={longitud_km} "
        f"Units=km Phases={fases} R1={r1_ohm_km} X1={x1_ohm_km}"
    )
    key1, key2 = _bus_key(bus1), _bus_key(bus2)
    if key1 in _bus_voltage_bases_ll and key2 not in _bus_voltage_bases_ll:
        _record_bus_voltage_base(bus2, _bus_voltage_bases_ll[key1])
    elif key2 in _bus_voltage_bases_ll and key1 not in _bus_voltage_bases_ll:
        _record_bus_voltage_base(bus1, _bus_voltage_bases_ll[key2])
    _recalcular_bases_de_tension()
    return f"Línea '{nombre}' agregada: {bus1} -> {bus2} ({longitud_km} km)"


def agregar_transformador(
    nombre: str,
    bus_primario: str,
    bus_secundario: str,
    kva: float,
    kv_primario: float,
    kv_secundario: float,
    conexion_primario: str = "delta",
    conexion_secundario: str = "wye",
) -> str:
    if min(kva, kv_primario, kv_secundario) <= 0:
        raise ValueError("kva y tensiones nominales deben ser mayores que cero.")
    conexiones = {"delta", "wye"}
    if conexion_primario.lower() not in conexiones or conexion_secundario.lower() not in conexiones:
        raise ValueError("Las conexiones admitidas son 'delta' y 'wye'.")

    dss(
        f"New Transformer.{nombre} Phases=3 Windings=2 "
        f"wdg=1 bus={bus_primario} conn={conexion_primario} "
        f"kv={kv_primario} kva={kva} "
        f"wdg=2 bus={bus_secundario} conn={conexion_secundario} "
        f"kv={kv_secundario} kva={kva}"
    )
    _voltage_bases.update({float(kv_primario), float(kv_secundario)})
    _record_bus_voltage_base(bus_primario, kv_primario, overwrite=True)
    _record_bus_voltage_base(bus_secundario, kv_secundario, overwrite=True)
    _recalcular_bases_de_tension()
    return (
        f"Transformador '{nombre}' agregado: {kva} kVA, "
        f"{kv_primario}kV/{kv_secundario}kV"
    )


def agregar_carga(
    nombre: str,
    bus: str,
    kw: float,
    kvar: float = 0,
    fases: int = 3,
    kv: float = 0.22,
    critica: bool = False,
) -> str:
    if kv <= 0:
        raise ValueError("kv debe ser mayor que cero.")
    if fases not in (1, 2, 3):
        raise ValueError("fases debe ser 1, 2 o 3.")

    dss(
        f"New Load.{nombre} Bus1={bus} Phases={fases} kV={kv} "
        f"kW={kw} kvar={kvar}"
    )
    _voltage_bases.add(float(kv))
    _record_bus_voltage_base(bus, kv)
    _recalcular_bases_de_tension()
    if critica:
        _cargas_criticas.add(nombre)
    else:
        _cargas_criticas.discard(nombre)
    etiqueta = " [CRÍTICA]" if critica else ""
    return f"Carga '{nombre}' agregada en {bus}: {kw} kW, {kvar} kVAR{etiqueta}"


def agregar_generador_respaldo(
    nombre: str, bus: str, kw: float, kv: float, fases: int = 3
) -> str:
    """
    Agrega un grupo electrógeno/modelo Generator de OpenDSS.

    No se presenta como modelo de UPS: una UPS basada en inversor requiere
    supuestos específicos de control y contribución a cortocircuito.
    """
    if kw <= 0 or kv <= 0:
        raise ValueError("kw y kv deben ser mayores que cero.")
    dss(
        f"New Generator.{nombre} Bus1={bus} Phases={fases} kV={kv} kW={kw}"
    )
    _voltage_bases.add(float(kv))
    _record_bus_voltage_base(bus, kv)
    _recalcular_bases_de_tension()
    return f"Generador de respaldo '{nombre}' agregado en {bus}: {kw} kW"


def ejecutar_flujo_potencia() -> dict[str, Any]:
    _recalcular_bases_de_tension()
    dss("Solve")

    voltajes: dict[str, dict[str, Any]] = {}
    for bus in dss.Circuit.AllBusNames():
        dss.Circuit.SetActiveBus(bus)
        voltajes[bus] = {
            "kv_base": round(float(dss.Bus.kVBase()), 3),
            "voltajes_pu": [
                round(float(v), 4) for v in dss.Bus.puVmagAngle()[0::2]
            ],
        }

    perdidas_kw, perdidas_kvar = dss.Circuit.Losses()
    return {
        "convergio": bool(dss.Solution.Converged()),
        "voltajes_por_bus": voltajes,
        "perdidas_totales_kw": round(float(perdidas_kw) / 1000, 3),
        "perdidas_totales_kvar": round(float(perdidas_kvar) / 1000, 3),
    }


def ejecutar_cortocircuito(bus_falla: str) -> dict[str, Any]:
    if bus_falla.lower() not in {b.lower() for b in dss.Circuit.AllBusNames()}:
        raise ValueError(f"Bus no encontrado en el circuito: {bus_falla}")

    dss("Solve Mode=FaultStudy")
    dss.Circuit.SetActiveBus(bus_falla)
    raw = dss.Bus.Isc()
    reales = raw[0::2]
    imaginarias = raw[1::2]
    magnitudes = [
        (float(re) ** 2 + float(im) ** 2) ** 0.5
        for re, im in zip(reales, imaginarias)
    ]
    return {
        "bus": bus_falla,
        "corriente_falla_amperios": [round(m, 2) for m in magnitudes],
    }


def abrir_elemento(nombre_elemento: str) -> dict[str, Any]:
    if not _elemento_existe(nombre_elemento):
        raise ValueError(f"Elemento no encontrado en el circuito: {nombre_elemento}")
    dss(f"Open {nombre_elemento} term=1")
    dss("Solve")
    return {
        "elemento": nombre_elemento,
        "abierto": _estado_elemento_abierto(nombre_elemento),
        "convergio": bool(dss.Solution.Converged()),
    }


def cerrar_elemento(nombre_elemento: str) -> dict[str, Any]:
    if not _elemento_existe(nombre_elemento):
        raise ValueError(f"Elemento no encontrado en el circuito: {nombre_elemento}")
    dss(f"Close {nombre_elemento} term=1")
    dss("Solve")
    return {
        "elemento": nombre_elemento,
        "abierto": _estado_elemento_abierto(nombre_elemento),
        "convergio": bool(dss.Solution.Converged()),
    }


def simular_perdida_alimentador(
    nombre_elemento: str, restaurar: bool = True
) -> dict[str, Any]:
    """
    Simula una contingencia N-1 y mantiene coherente topología + solución.

    Si restaurar=True, el elemento vuelve exactamente a su estado inicial y
    OpenDSS se resuelve otra vez antes de retornar. Si restaurar=False, queda
    abierto y resuelto para permitir inspección o generación del unifilar.
    """
    if not _elemento_existe(nombre_elemento):
        raise ValueError(f"Elemento no encontrado en el circuito: {nombre_elemento}")

    estaba_abierto = _estado_elemento_abierto(nombre_elemento)

    dss(f"Open {nombre_elemento} term=1")
    dss("Solve")

    convergio_contingencia = bool(dss.Solution.Converged())
    perdidas_kw, _ = dss.Circuit.Losses()
    criticas = _estado_cargas_criticas()

    resultado: dict[str, Any] = {
        "elemento_abierto": nombre_elemento,
        "convergio": convergio_contingencia,
        "perdidas_kw": (
            round(float(perdidas_kw) / 1000, 3)
            if convergio_contingencia
            else None
        ),
        "cargas_criticas": criticas,
        "cargas_criticas_sin_tension": [
            item["carga"] for item in criticas if not item["energizada"]
        ],
        "estado_inicial_elemento": "abierto" if estaba_abierto else "cerrado",
        "restaurar_solicitado": restaurar,
    }

    if restaurar:
        if estaba_abierto:
            dss(f"Open {nombre_elemento} term=1")
        else:
            dss(f"Close {nombre_elemento} term=1")
        dss("Solve")
        resultado["estado_final_elemento"] = (
            "abierto" if estaba_abierto else "cerrado"
        )
        resultado["convergio_estado_restaurado"] = bool(dss.Solution.Converged())
        resultado["estado_modelo"] = "restaurado_y_resuelto"
    else:
        resultado["estado_final_elemento"] = "abierto"
        resultado["estado_modelo"] = "contingencia_activa_y_resuelta"

    return resultado


def listar_elementos() -> dict[str, list[str]]:
    return {
        "buses": dss.Circuit.AllBusNames(),
        "lineas": dss.Lines.AllNames(),
        "transformadores": dss.Transformers.AllNames(),
        "cargas": dss.Loads.AllNames(),
        "generadores": dss.Generators.AllNames(),
    }


def listar_cargas_criticas() -> list[str]:
    return sorted(_cargas_criticas)


def obtener_netlist(directorio: str = "temp_export") -> dict[str, Any]:
    """
    Exporta el circuito y devuelve los archivos DSS con su contenido.

    Nunca borra una exportación anterior. Si el destino ya contiene
    archivos DSS, crea un directorio hermano con sufijo incremental.
    """
    solicitado = Path(directorio).expanduser().resolve()
    destino = solicitado

    # Nunca borramos una exportación anterior. Si el destino ya contiene
    # archivos DSS, elegimos un directorio hermano con sufijo incremental.
    if destino.exists() and any(
        p.is_file() and p.suffix.lower() == ".dss" for p in destino.iterdir()
    ):
        indice = 2
        while True:
            candidato = destino.with_name(f"{destino.name}_{indice}")
            if not candidato.exists():
                destino = candidato
                break
            indice += 1

    destino.mkdir(parents=True, exist_ok=True)
    comando = dss(f'Save Circuit Dir="{destino}"')

    archivos = []
    for archivo in sorted(
        (p for p in destino.iterdir() if p.is_file() and p.suffix.lower() == ".dss"),
        key=lambda p: p.name.lower(),
    ):
        archivos.append(
            {
                "nombre": archivo.name,
                "ruta": str(archivo),
                "contenido": archivo.read_text(encoding="utf-8", errors="replace"),
            }
        )

    if not archivos:
        raise RuntimeError(
            "OpenDSS no generó archivos DSS en el directorio solicitado. "
            f"Respuesta del comando: {comando!r}"
        )

    master = next(
        (a["nombre"] for a in archivos if a["nombre"].lower() == "master.dss"),
        None,
    )
    return {
        "directorio": str(destino),
        "archivo_master": master,
        "cantidad_archivos": len(archivos),
        "archivos": archivos,
        "respuesta_opendss": comando,
    }


def estimar_arc_flash_lee(
    voltaje_kv: float,
    corriente_falla_ka: float,
    tiempo_despeje_s: float,
    distancia_trabajo_mm: float = 455,
) -> dict[str, Any]:
    """
    Estimación educativa por método de Lee.

    Devuelve energía incidente y frontera de arco, pero deliberadamente NO
    asigna categorías PPE. IEEE 1584 no es una norma de selección de EPP y
    el modelo completo IEEE 1584-2018 no se implementa aquí.
    """
    valores = {
        "voltaje_kv": voltaje_kv,
        "corriente_falla_ka": corriente_falla_ka,
        "tiempo_despeje_s": tiempo_despeje_s,
        "distancia_trabajo_mm": distancia_trabajo_mm,
    }
    if any(float(v) <= 0 for v in valores.values()):
        raise ValueError("Todos los parámetros de arc flash deben ser mayores que cero.")

    energia_j_cm2 = (
        2.142e6
        * float(voltaje_kv)
        * float(corriente_falla_ka)
        * float(tiempo_despeje_s)
        / (float(distancia_trabajo_mm) ** 2)
    )
    energia_cal_cm2 = energia_j_cm2 / 4.184

    energia_frontera_j_cm2 = 5.02
    frontera_mm = (
        2.142e6
        * float(voltaje_kv)
        * float(corriente_falla_ka)
        * float(tiempo_despeje_s)
        / energia_frontera_j_cm2
    ) ** 0.5

    advertencias = [
        "Estimación educativa por método de Lee; no es un estudio normado.",
        "No implementa el modelo empírico IEEE 1584-2018.",
    ]
    if 0.208 <= float(voltaje_kv) <= 15:
        advertencias.append(
            "La tensión está dentro del rango cubierto por IEEE 1584-2018; "
            "esta ecuación de Lee no sustituye ese modelo."
        )

    return {
        "energia_incidente_cal_cm2": round(energia_cal_cm2, 3),
        "energia_incidente_J_cm2": round(energia_j_cm2, 3),
        "frontera_arco_mm": round(frontera_mm, 1),
        "frontera_arco_in": round(frontera_mm / 25.4, 1),
        "categoria_ppe": None,
        "nota_epp": (
            "No se asigna categoría PPE a partir de esta energía. "
            "La selección de EPP requiere aplicar el método y la edición "
            "vigentes de la norma de seguridad correspondiente."
        ),
        "metodo": "Lee simplificado; estimación educativa.",
        "advertencias": advertencias,
        "parametros_entrada": valores,
    }


def calcular_arc_flash(
    voltaje_kv: float,
    corriente_falla_ka: float,
    tiempo_despeje_s: float,
    distancia_trabajo_mm: float = 455,
) -> dict[str, Any]:
    """Alias compatible con versiones anteriores; usa estimar_arc_flash_lee."""
    resultado = estimar_arc_flash_lee(
        voltaje_kv,
        corriente_falla_ka,
        tiempo_despeje_s,
        distancia_trabajo_mm,
    )
    resultado["alias_compatibilidad"] = "calcular_arc_flash"
    return resultado
