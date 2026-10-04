"""Researched candidates; this catalogue does not install or execute engines."""

RESEARCH_DATE = "2026-10-02"

EXTERNAL_ENGINES = {
    "opendss+indmach012": {
        "role": "Existing induction-machine component in the current OpenDSS backend",
        "models": ["IndMach012", "OpenDSS Dynamics mode"],
        "strengths": ["distribution-network electromechanical dynamics", "symmetrical-component induction-machine model"],
        "limits": ["not per-phase SCR switching", "starting from rest and mechanical load law require a scoped pilot", "current MCP motor-dynamics tools do not execute IndMach012"],
        "license": "OpenDSS BSD-style; DSS-Extensions dependency licenses separate",
        "windows": "current OpenDSS backend installed; this dynamic study not qualified",
        "integration_status": "LIBRARY_PRESENT_ADAPTER_PENDING",
        "sources": ["https://opendss.epri.com/Dynamics.html", "https://opendss.epri.com/IndMach012.html", "https://opendss.epri.com/OpenDSSDynamicsMode.html"],
    },
    "openmodelica+msl": {
        "role": "Modelica runtime + electrical/machine/converter component library",
        "models": ["IM_SquirrelCage", "PolyphaseTriac", "SoftStartControl", "Signal2mPulse", "VfController"],
        "strengths": ["motor electrical/mechanical dynamics", "per-phase SCR switching", "connected machines and converters"],
        "limits": ["requires network, controller and initialization configuration", "no manufacturer validation implied"],
        "license": "MSL 4.0.0: BSD-3-Clause; runtime/dependency licenses separate",
        "windows": "OpenModelica 1.27.1/MSL 4.0.0: DOL adapter verified in declared common-bus RL scope; SCR gates remain pending",
        "integration_status": "SCOPED_EXPERIMENTAL_DOL_MCP_ADAPTER",
        "sources": ["https://github.com/modelica/ModelicaStandardLibrary/tree/v4.0.0", "https://doc.modelica.org/Modelica%204.0.0/Resources/helpWSM/Modelica/Modelica.Electrical.PowerConverters.Examples.ACAC.SoftStarter.html"],
    },
    "andes": {
        "role": "Python power-system simulation engine",
        "models": ["GENROU", "GENCLS", "exciters", "governors", "Motor3", "Motor5"],
        "strengths": ["network transient stability", "eigenvalue analysis", "dynamic loads and generator controls"],
        "limits": ["phasor models do not resolve SCR switching waveforms", "case-specific dynamic parameters required"],
        "license": "GPL-3.0-or-later",
        "windows": "documented Python/conda installation; not tested on this PC",
        "integration_status": "RESEARCH_ONLY",
        "sources": ["https://github.com/CURENT/andes", "https://github.com/CURENT/andes/tree/master/andes/models/motor", "https://raw.githubusercontent.com/CURENT/andes/master/LICENSE"],
    },
    "openmodelica+openipsl": {
        "role": "Modelica phasor power-system model library; requires a runtime",
        "models": ["CIM5 single/double-cage induction motor", "synchronous machines", "exciters", "governors"],
        "strengths": ["network electromechanical dynamics", "inspectable Modelica component models"],
        "limits": ["OpenIPSL is not a standalone solver", "OpenModelica compatibility must be checked per model", "not SCR waveform modelling"],
        "license": "BSD-3-Clause (library); runtime/dependencies separate",
        "windows": "existing OpenModelica runtime; library not tested locally",
        "integration_status": "RESEARCH_ONLY",
        "sources": ["https://github.com/OpenIPSL/OpenIPSL", "https://raw.githubusercontent.com/OpenIPSL/OpenIPSL/master/OpenIPSL/Electrical/Machines/PSSE/CIM5.mo"],
    },
    "veragrid": {
        "role": "Python grid analysis engine (formerly GridCal)",
        "models": ["ContinuationPowerFlowDriver", "RMS models", "EMT induction motor template"],
        "strengths": ["continuation power flow", "network planning", "RMS and ABC EMT APIs"],
        "limits": ["specific model/API version and benchmark required", "general short circuit is not an IEC 60909 conformance claim"],
        "license": "MPL-2.0 (current repository; pin and recheck at integration)",
        "windows": "official Windows distribution and Python engine; not tested locally",
        "integration_status": "RESEARCH_ONLY",
        "sources": ["https://github.com/SanPen/VeraGrid", "https://raw.githubusercontent.com/SanPen/VeraGrid/master/LICENSE.md", "https://veragrid.readthedocs.io/en/latest/md_source/emt_simulations.html"],
    },
    "dpsim": {
        "role": "C++ simulation engine with Python API",
        "models": ["RLC", "network branches", "synchronous generators", "averaged inverter models"],
        "strengths": ["electromagnetic transients", "dynamic phasors", "real-time/co-simulation in supported builds"],
        "limits": ["Windows wheel excludes VILLASnode, real-time and Sundials/ODE generator", "no verified turnkey SCR motor starter in this review"],
        "license": "MPL-2.0",
        "windows": "official x86-64 wheels include CPython 3.12; reduced feature set; not tested locally",
        "integration_status": "RESEARCH_ONLY",
        "sources": ["https://github.com/sogno-platform/dpsim", "https://dpsim.fein-aachen.org/docs/user-guide/install/", "https://dpsim.fein-aachen.org/docs/reference/model-availability/"],
    },
    "pandapower_protection": {
        "role": "Existing protection library within pandapower",
        "models": ["OCRelay DTOC/IDMT/IDTOC", "Fuse"],
        "strengths": ["overcurrent relay operation", "reuse of existing protection calculations"],
        "limits": ["does not establish complete selectivity or manufacturer coordination", "current MCP P5 is not an OCRelay adapter"],
        "license": "BSD-3-Clause (pandapower)",
        "windows": "source verified in local pandapower 3.5.4; protection adapter not implemented",
        "integration_status": "LIBRARY_PRESENT_ADAPTER_PENDING",
        "sources": ["https://pandapower.readthedocs.io/en/v3.3.3/protection/oc_relay.html", "https://github.com/e2nIEE/pandapower/tree/v3.5.4/pandapower/protection"],
    },
}


def planned_route(preferred, alternatives, reason, requirements):
    """A recommendation cannot become executable merely by experimental opt-in."""
    return {
        "preferred": preferred, "alternatives": alternatives, "module": None,
        "implemented": False, "professional_emission_candidate": False,
        "requires_active_model": False, "planning_only": True,
        "integration_status": "ADAPTER_NOT_IMPLEMENTED",
        "reason": reason, "requirements": requirements,
    }


PLANNED_STUDIES = {
    "motor_dynamics_dol": planned_route(
        "openmodelica+msl", ["opendss+indmach012", "andes", "openmodelica+openipsl", "veragrid"],
        "Para dinámica eléctrica/mecánica de arranque directo se prioriza MSL: componentes ejecutados localmente; falta adaptador MCP. Las alternativas fasoriales requieren otro alcance/modelo explícito.",
        ["adaptador de ejecución MCP", "parámetros eléctricos del motor y conexión", "inercia y curva de par de carga", "red y condiciones iniciales", "benchmark del caso completo"]),
    "motor_dynamics_soft_starter_scr": planned_route(
        "openmodelica+msl", [],
        "MSL dispone de máquina, triacs y control de arranque. El estudio SCR requiere conexiones y controlador realimentado; una traza externa no equivale a integración. No se sustituye por un motor fasorial.",
        ["adaptador de ejecución MCP", "parámetros motor/red/carga", "control de disparo SCR y límites explícitos", "lógica y evento de bypass", "benchmark con red y control cerrados"]),
    "motor_dynamics_simultaneous": planned_route(
        "openmodelica+msl", ["opendss+indmach012", "andes", "openmodelica+openipsl"],
        "Se propone conectar máquinas existentes a una red común en Modelica. La dinámica simultánea no está probada ni integrada; las alternativas fasoriales requieren comprobar la representación de cada máquina.",
        ["adaptador MCP multimáquina", "red común y eventos de cada arranque", "ficha e inercia de cada motor", "estado de máquinas ya en marcha", "benchmark de interacción entre máquinas"]),
    "motor_dynamics_vfd": planned_route(
        "openmodelica+msl", [],
        "MSL aporta máquinas y convertidores; la configuración de un variador específico y su control aún debe probarse. No existe un estudio VFD MCP ejecutable por esta recomendación.",
        ["adaptador MCP", "topología y control del variador", "modelo promedio o conmutado explícito", "motor/carga/red", "benchmark del conjunto"]),
    "transient_stability": planned_route(
        "andes", ["openmodelica+openipsl", "veragrid"],
        "ANDES ofrece simulación temporal de estabilidad con máquinas, excitadores y gobernadores. Preferencia propuesta para dinámica fasorial de red; no cubre por sí sola conmutación SCR ni EMT.",
        ["instalación aislada y versión fijada", "adaptador MCP y conversión de red", "flujo inicial convergente", "fichas dinámicas y eventos", "benchmark independiente"]),
    "small_signal_stability": planned_route(
        "andes", ["veragrid"],
        "ANDES incluye análisis de autovalores del sistema dinámico para pequeña señal. La selección es de integración pendiente, sin resultados de estabilidad todavía.",
        ["adaptador MCP", "punto de operación e inicialización dinámica", "máquinas y controles", "benchmark modal"]),
    "voltage_stability_cpf": planned_route(
        "veragrid", ["andes"],
        "VeraGrid expone flujo continuado para estudiar margen de carga/tensión. ANDES también ofrece CPF. La preferencia es una ruta de integración para planificación; no prueba superioridad numérica ni garantiza solución del caso.",
        ["adaptador MCP y versión fijada", "modelo estático compatible", "dirección de incremento de demanda/generación", "límites reactivos y criterio de parada", "benchmark CPF"]),
    "electromagnetic_transients": planned_route(
        "openmodelica+msl", ["dpsim", "veragrid"],
        "Para transitorios eléctricos por fase se propone MSL por su ejecución local previa y componentes disponibles. DPsim y VeraGrid son candidatos EMT; la elección ejecutable exige verificar componentes, plataforma y caso.",
        ["adaptador MCP", "componentes que representen el fenómeno solicitado", "parámetros por fase e inicialización", "eventos, paso/tolerancia y convergencia", "benchmark EMT"]),
}
