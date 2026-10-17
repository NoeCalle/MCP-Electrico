"""Presentation fixtures with explicit values; no claim of a new physical benchmark."""
from copy import deepcopy
import csv
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import pytest
from mcp_electrico import motor_study_report as report

ROOT = Path(__file__).resolve().parents[1]


def saved_case(folder, status="MODELICA_MOTOR_STUDIES_COMPLETED"):
    inputs = json.loads((ROOT/"examples/msl_motor_two.json").read_text(encoding="utf8"))
    inputs["source_reference"] = "PRESENTATION_FIXTURE_NOT_AN_ENGINE_SIMULATION"
    results = []
    for i,motor in enumerate(inputs["motors"]):
        motor["id"] = f"M{i+1}"
        rows = [{"time_s": .1+j*.02, "speed_rad_s": 10+j, "current_a":100+i*20+j,
                 "torque_nm": -20+j*15, "voltage_pu": .7+j*.05, "bus_voltage_pu":.95+j*.005,
                 "controller_voltage_reference_pu":1} for j in range(5)]
        results.append({"motor_id":motor["id"],"starting_method":"DOL","acceleration_time_s":.12+i*.1,
                        "minimum_voltage_pu":.7,"minimum_bus_voltage_pu":.95,
                        "maximum_cycle_rms_current_a":104+i*20,"criterion":{"passed":i==0},
                        "verification":{"passed":True},"trajectory":rows})
    result = {"status":status,"backend":"OPENMODELICA_MSL_4_0_0","results":results,
              "contract":{"historical_qualification":"DO_NOT_PROMOTE"}}
    folder.mkdir()
    (folder/"Inputs.json").write_text(json.dumps(inputs),encoding="utf8")
    result["files_sha256"] = {"Inputs.json":report._hash(folder/"Inputs.json")}
    (folder/"Results.json").write_text(json.dumps(result),encoding="utf8")
    return inputs,result


def rewrite(folder, inputs, result):
    (folder/"Inputs.json").write_text(json.dumps(inputs),encoding="utf8")
    result["files_sha256"] = {"Inputs.json":report._hash(folder/"Inputs.json")}
    (folder/"Results.json").write_text(json.dumps(result),encoding="utf8")


def generate(folder, output, name="Case"):
    return report.generate([{"case_id":name,"study_directory":str(folder)}],output)


def test_report_preserves_per_motor_values_units_snapshots_and_exact_integrity(tmp_path):
    source = tmp_path/"source"
    inputs,result = saved_case(source)
    before = {p.name:p.read_bytes() for p in source.iterdir()}
    output = tmp_path/"report"
    generated = generate(source,output)
    assert generated["status"] == "MSL_REPORT_CREATED" and generated["motor_count"] == 2
    assert not generated["solver_executed"] and not generated["source_studies_modified"]
    assert before == {p.name:p.read_bytes() for p in source.iterdir()}
    data = json.loads((output/"ReportData.json").read_text(encoding="utf8"))
    assert data["cases"][0]["result"] == result
    assert data["comparison"][0]["minimum_bus_voltage_pu"] == .95
    assert data["comparison"][0]["minimum_voltage_pu"] == .7
    assert data["comparison"][0]["design_criterion"] == "CUMPLE"
    assert data["comparison"][1]["design_criterion"] == "NO CUMPLE"
    with (output/"Trajectories.csv").open(encoding="utf-8-sig",newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 10 and float(rows[5]["current_a"]) == 120
    assert float(rows[0]["bus_voltage_pu"]) != float(rows[0]["voltage_pu"])
    svgs = list(output.rglob("*.svg"))
    assert len(svgs) == 8
    for path in svgs:
        svg = ET.fromstring(path.read_text(encoding="utf8"))
        assert svg.attrib["viewBox"] == "0 0 900 292"
    voltage = (output/"case-01/motor-01-chart-4.svg").read_text(encoding="utf8")
    assert "Terminal" in voltage and "Barra" in voltage and 'stroke-dasharray="8 4"' in voltage
    assert report.verify(output)["ok"]
    (output/"Comparison.csv").write_text("corrupt")
    assert not report.verify(output)["ok"]


@pytest.mark.parametrize("fault",["execution","refinement","missing_criteria","missing_verification","missing_motor","missing_measurement"])
def test_unavailable_or_unverified_values_never_look_like_design_acceptance(tmp_path,fault):
    source = tmp_path/"source"
    inputs,result = saved_case(source)
    if fault == "execution":
        result.update(status="MODELICA_EXECUTION_FAILED",failed_stage="REFINED_SIMULATION",last_emitted_time_s=.12)
    elif fault == "refinement":
        result["status"] = "MODELICA_REFINEMENT_NOT_PASSED"
        result["results"][0]["verification"]["passed"] = False
    elif fault == "missing_criteria":
        del inputs["motors"][0]["criteria"]
    elif fault == "missing_verification":
        del result["results"][0]["verification"]
    elif fault == "missing_motor":
        result["results"].pop(0)
    else:
        for row in result["results"][0]["trajectory"]:
            del row["bus_voltage_pu"]
        del result["results"][0]["minimum_bus_voltage_pu"]
    rewrite(source,inputs,result)
    output = tmp_path/"report"
    assert generate(source,output)["status"] == "MSL_REPORT_CREATED"
    data = json.loads((output/"ReportData.json").read_text(encoding="utf8"))
    if fault != "missing_measurement":
        assert data["comparison"][0]["design_criterion"] == "NO EVALUABLE"
    else:
        assert data["comparison"][0]["minimum_bus_voltage_pu"] is None
    if fault == "execution":
        assert not list(output.rglob("*.svg"))
        assert "fallo de ejecución no demuestra" in (output/"Informe.html").read_text(encoding="utf8")


@pytest.mark.parametrize("fault",["input_hash","unknown_motor","duplicate_motor","unordered_time","nonfinite","wrong_schema"])
def test_mismatched_or_malformed_sources_block_before_creating_report(tmp_path,fault):
    source = tmp_path/"source"
    inputs,result = saved_case(source)
    if fault == "input_hash":
        result["files_sha256"]["Inputs.json"] = "bad"
    elif fault == "unknown_motor":
        result["results"][0]["motor_id"] = "UNKNOWN"
    elif fault == "duplicate_motor":
        result["results"].append(deepcopy(result["results"][0]))
    elif fault == "unordered_time":
        result["results"][0]["trajectory"][1]["time_s"] = 0
    elif fault == "nonfinite":
        result["results"][0]["trajectory"][0]["current_a"] = float("nan")
    else:
        inputs["schema"] = "UNKNOWN"
        rewrite(source,inputs,result)
    (source/"Results.json").write_text(json.dumps(result),encoding="utf8")
    output = tmp_path/"report"
    assert generate(source,output)["status"] == "BLOCKED_MSL_REPORT_INPUTS"
    assert not output.exists()


def test_long_chart_keeps_each_series_extremes_and_missing_value_gaps():
    rows = [{"time_s":i*.02,"current_a":1,"torque_nm":0} for i in range(10000)]
    rows[123]["current_a"] = 999
    rows[125]["torque_nm"] = -789
    rows[127]["current_a"] = None
    indices = report._indices(rows,["current_a","torque_nm"])
    assert {123,125,126,127,128} <= set(indices) and len(indices) < 1000
    html,svg = report._svg(rows,[("current_a","I","#087e8b")],"Current","A",0)
    root = ET.fromstring(svg)
    assert len(root.findall("{http://www.w3.org/2000/svg}polyline")) == 2


def test_html_csv_identifiers_are_literal_and_case_comparison_is_explicit(tmp_path):
    source = tmp_path/"source"
    inputs,result = saved_case(source)
    inputs["motors"][0]["id"] = result["results"][0]["motor_id"] = '=HYPERLINK("example")<script>bad</script>'
    inputs["motors"][0]["criteria"]["source_reference"] = '<img src=x onerror="bad">'
    rewrite(source,inputs,result)
    output = tmp_path/"report"
    generated = generate(source,output,'<script>case</script>')
    assert generated["status"] == "MSL_REPORT_CREATED"
    html = (output/"Informe.html").read_text(encoding="utf8")
    assert '<script>case' not in html and '<img src=x' not in html
    assert '&lt;script&gt;case' in html
    csv_text = (output/"Comparison.csv").read_text(encoding="utf-8-sig")
    assert "'=HYPERLINK" in csv_text
    assert generate(source,output)["status"] == "BLOCKED_MSL_REPORT_OUTPUT"
    assert report.generate([{"case_id":"A","study_directory":str(source)},{"case_id":"a","study_directory":str(source)}],tmp_path/"bad")["status"] == "BLOCKED_MSL_REPORT_INPUTS"
    (output/"extra.txt").write_text("unexpected")
    assert "EXACT_FILE_SET_MISMATCH" in report.verify(output)["issues"]


def test_successful_adapter_execution_adds_report_without_an_extra_engine_run(tmp_path,monkeypatch):
    from mcp_electrico import modelica_motor_adapter as adapter
    source = tmp_path/"fixture"
    inputs,result = saved_case(source)
    library = tmp_path/"library"
    for name in ["Modelica/Electrical/Machines/BasicMachines/InductionMachines/IM_SquirrelCage.mo",
                 "Modelica/Electrical/PowerConverters/ACAC/Control/SoftStartControl.mo",
                 "Modelica/Electrical/PowerConverters/ACAC/PolyphaseTriac.mo"]:
        file = library/name
        file.parent.mkdir(parents=True,exist_ok=True)
        file.write_text("presentation integration fixture")
    monkeypatch.setattr(adapter,"runtime",lambda:{"ready":True,"library":str(library),"executable":str(tmp_path/"omc")})
    monkeypatch.setattr(adapter,"_summaries",lambda *args:deepcopy(result["results"]))
    calls = []
    def run(command,folder,*args):
        calls.append(command)
        if command[0].endswith("omc"):
            (folder/("MotorStudy.exe" if adapter.platform.system()=="Windows" else "MotorStudy")).write_text("fixture")
        for argument in command:
            if argument.startswith("-r="):
                Path(argument[3:]).write_text("time\n0\n")
        return {"returncode":0,"execution_status":"COMPLETED","stdout":"The simulation finished successfully."}
    monkeypatch.setattr(adapter,"_run",run)
    output = tmp_path/"study"
    generated = adapter.execute(inputs,output)
    assert generated["status"] == "MODELICA_MOTOR_STUDIES_COMPLETED"
    assert generated["presentation"]["status"] == "MSL_REPORT_CREATED"
    assert len(calls) == 3  # Compilation, nominal, refined; presentation never calls the engine.
    canonical = json.loads((output/"Results.json").read_text(encoding="utf8"))
    assert canonical == {key:value for key,value in generated.items() if key != "presentation"}
    assert canonical["results"][0]["trajectory"] == result["results"][0]["trajectory"]
    assert report.verify(output/"Report")["ok"]
