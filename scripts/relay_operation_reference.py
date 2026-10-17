"""Independent scalar expectations for generic IEC-style OC relay test cases.

Benchmark only; never imported by the application adapter or used as fallback.
"""
CURVE_PARAMETERS = {"standard_inverse": (.14, .02), "very_inverse": (13.5, 1),
                    "extremely_inverse": (80, 2), "long_inverse": (120, 1)}


def expected_time(kind, curve, current):
    if kind != "IDMT":
        if current > 1000:
            return .02
        if current > 500:
            return .4
    if kind == "DTOC" or current <= 100:
        return None
    k, exponent = CURVE_PARAMETERS[curve]
    return .1*k/((current/100)**exponent-1)+.05


def reference_package(kind="IDMT", curve="standard_inverse", scenario="sc", breaker_delay=.05):
    ref = "SYNTHETIC_CONSTANT_PRIMARY_CURRENT_REFERENCE_NOT_MANUFACTURER_DATA"
    if kind == "DTOC":
        settings = {"pickup_primary_a": 500, "high_set_primary_a": 1000, "delay_s": .4, "high_set_delay_s": .02}
    else:
        settings = {"pickup_primary_a": 100, "curve_type": curve, "time_multiplier": .1, "additive_delay_s": .05}
        if kind == "IDTOC":
            settings.update(inverse_pickup_primary_a=100, pickup_primary_a=500,
                            high_set_primary_a=1000, delay_s=.4, high_set_delay_s=.02)
    currents = [0, 99, 100, 101, 499, 500, 501, 999, 1000, 1001, 2000, 10000]
    cases = []
    for i,current in enumerate(currents):
        time = expected_time(kind,curve,current)
        cases.append({"id": f"point_{i}", "scenario": scenario,
                      "currents": {"R1": {"primary_rms_a": current, "source_reference": ref}},
                      "expectations": {"R1": {"trip": time is not None,
                          "maximum_relay_time_s": time+1e-6 if time is not None else None,
                          "maximum_total_clearing_time_s": time+breaker_delay+1e-6 if time is not None and breaker_delay is not None else None,
                          "source_reference": "INDEPENDENT_TEST_EXPECTATION_NOT_PROJECT_CRITERION"}},
                      "source_reference": ref})
    return {"schema": "MCP_ELECTRICO_RELAY_OPERATION_V1", "id": f"RELAY-REF-{kind}-{curve}",
            "source_reference": ref, "current_time_model": "CONSTANT_RMS_OVER_OPERATING_TIME",
            "relays": [{"id": "R1", "protected_element_reference": "EXPLICIT_TEST_FEEDER_NO_AUTOMATIC_MODEL_BINDING",
                        "type": kind, "settings": settings,
                        "breaker": {"clearing_delay_s": breaker_delay, "source_reference": ref if breaker_delay is not None else "TBC_NOT_SUPPLIED"},
                        "source_reference": ref}], "cases": cases}
