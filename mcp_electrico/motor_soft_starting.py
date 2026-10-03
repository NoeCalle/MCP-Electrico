"""Compatibility notice: the MCP-owned SCR/RL physical surrogate is retired."""
from .motor_dynamics import contrato, readiness as _readiness, execute as _execute

BACKEND = "RETIRED_MCP_SCR_RL_SURROGATE_RMS_RK4_V1"


def contract():
    return {**contrato(), "backend": BACKEND}


def readiness(manifest, package, options, starter):
    return {**_readiness(manifest, package, options), **contract()}


def execute(manifest, package, options, starter):
    return {**_execute(manifest, package, options), **contract()}
