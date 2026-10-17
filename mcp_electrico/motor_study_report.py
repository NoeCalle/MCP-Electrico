"""Offline presentation of saved MSL results; never runs or qualifies a solver."""
from copy import deepcopy
import csv
import hashlib
from html import escape
import json
from math import isfinite, pi
from pathlib import Path

SCHEMA = "MCP_ELECTRICO_MSL_REPORT_V1"
STATUSES = {"MODELICA_MOTOR_STUDIES_COMPLETED", "MODELICA_REFINEMENT_NOT_PASSED", "MODELICA_EXECUTION_FAILED"}
FIELDS = ("time_s", "speed_rad_s", "current_a", "torque_nm", "voltage_pu", "bus_voltage_pu", "controller_voltage_reference_pu")
SUMMARY = ("case_id", "motor_id", "frequency_hz", "starting_method", "start_time_s", "acceleration_time_s",
           "minimum_bus_voltage_pu", "minimum_voltage_pu", "maximum_cycle_rms_current_a", "numerical_verification", "design_criterion")


def contract():
    return {"schema": SCHEMA, "input": "1_TO_8_EXPLICIT_SAVED_MODELICA_STUDY_DIRECTORIES",
            "source_files": ["Inputs.json", "Results.json"], "solver_executed": False,
            "source_studies_modified": False, "qualification_promoted": False,
            "scope": "PER_MOTOR_CHARTS_AND_CASE_COMPARISON_OF_SAVED_RESULTS",
            "time_axis": "ABSOLUTE_STUDY_SECONDS; ACCELERATION_DURATION_FROM_START_COMMAND",
            "voltage_basis": "MINIMUM_LINE_TO_LINE_CYCLE_RMS_OVER_DECLARED_NETWORK_LL_RMS_BASE",
            "chart_reduction": "PER_BUCKET_EXTREMA; FULL_CYCLE_TRAJECTORY_IN_CSV_JSON",
            "source_hashes": "CAPTURED_AT_REPORT_CREATION; NOT_AUTHENTICATION_OF_ENGINE_OR_AUTHOR",
            "professional_emission": False}


def _number(value):
    return type(value) in (int, float) and isfinite(value)


def _text(value, unit=""):
    return f"{value:.6g}{unit}" if _number(value) else "No disponible"


def _label(value, criterion=False):
    if value is None:
        return "NO EVALUABLE"
    return ("CUMPLE" if value is True else "NO CUMPLE") if criterion else ("APROBADO" if value is True else "NO APROBADO")


def _hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _payload_hash(data):
    return hashlib.sha256(json.dumps(data,sort_keys=True,ensure_ascii=False,separators=(",",":"),allow_nan=False).encode("utf8")).hexdigest()


def _load(path):
    if path.stat().st_size > 64_000_000:
        raise ValueError("SOURCE_JSON_TOO_LARGE")
    def reject(value):
        raise ValueError("NONFINITE_SOURCE_JSON: " + value)
    def unique(pairs):
        data = {}
        for key, value in pairs:
            if key in data:
                raise ValueError("DUPLICATE_SOURCE_JSON_KEY")
            data[key] = value
        return data
    return json.loads(path.read_text(encoding="utf8"), parse_constant=reject, object_pairs_hook=unique)


def _case(spec):
    if not isinstance(spec, dict) or set(spec) != {"case_id", "study_directory"}:
        raise ValueError("EXPLICIT_CASE_ID_AND_STUDY_DIRECTORY_REQUIRED")
    if not isinstance(spec["case_id"], str) or not spec["case_id"].strip():
        raise ValueError("NONEMPTY_CASE_ID_REQUIRED")
    folder = Path(spec["study_directory"]).expanduser().resolve()
    inputs, result = _load(folder/"Inputs.json"), _load(folder/"Results.json")
    if inputs.get("schema") != "MCP_ELECTRICO_MSL_MOTOR_STUDY_V1" or result.get("status") not in STATUSES:
        raise ValueError("UNSUPPORTED_SAVED_STUDY")
    motors = inputs.get("motors")
    if not isinstance(motors, list) or not 1 <= len(motors) <= 8:
        raise ValueError("INVALID_INPUT_MOTORS")
    ids = [m["id"] for m in motors]
    if any(not isinstance(key, str) or not key for key in ids) or len(set(ids)) != len(ids):
        raise ValueError("INVALID_MOTOR_IDENTIFIERS")
    results = result.get("results", [])
    if not isinstance(results, list) or any(r.get("motor_id") not in ids for r in results):
        raise ValueError("RESULT_MOTOR_NOT_IN_INPUTS")
    if len({r["motor_id"] for r in results}) != len(results):
        raise ValueError("DUPLICATE_RESULT_MOTOR")
    expected = result.get("files_sha256", {}).get("Inputs.json")
    input_hash = _hash(folder/"Inputs.json")
    if expected and expected != input_hash:
        raise ValueError("INPUTS_HASH_MISMATCH")
    for r in results:
        trajectory = r.get("trajectory", [])
        if not isinstance(trajectory, list) or len(trajectory) > 100_000:
            raise ValueError("INVALID_CYCLE_TRAJECTORY")
        times = [row.get("time_s") for row in trajectory]
        if any(not _number(t) for t in times) or any(a >= b for a,b in zip(times, times[1:])):
            raise ValueError("INVALID_TRAJECTORY_TIME")
        if any(value is not None and not _number(value) for row in trajectory for key,value in row.items() if key in FIELDS):
            raise ValueError("INVALID_TRAJECTORY_MEASUREMENT")
    return {"case_id": spec["case_id"], "inputs": inputs, "result": result,
            "source_hashes": {"Inputs.json": input_hash, "Results.json": _hash(folder/"Results.json")},
            "input_pairing": "MATCHES_RECORDED_HASH" if expected else "NO_PREEXISTING_INPUT_HASH"}


def _indices(rows, fields, buckets=320):
    """Keep each series' min/max in every bucket; missing values keep a gap."""
    if len(rows) <= buckets*2:
        return list(range(len(rows)))
    selected = {0, len(rows)-1}
    width = (len(rows)+buckets-1)//buckets
    for left in range(0, len(rows), width):
        indices = range(left, min(left+width,len(rows)))
        for field in fields:
            valid = [i for i in indices if _number(rows[i].get(field))]
            if valid:
                selected.update((min(valid,key=lambda i:rows[i][field]), max(valid,key=lambda i:rows[i][field])))
            for i in indices:
                if not _number(rows[i].get(field)):
                    selected.update((max(left,i-1), i, min(len(rows)-1,i+1)))
    return sorted(selected)


def _svg(rows, series, title, unit, start, threshold=None):
    fields = [field for field,_,_ in series]
    numbers = [r[field] for r in rows for field in fields if _number(r.get(field))]
    if not numbers:
        return '<p class="missing">Sin mediciones disponibles para este gráfico.</p>', None
    lo, hi = min(0,min(numbers)), max(numbers)
    if _number(threshold):
        lo, hi = min(lo,threshold), max(hi,threshold)
    hi = max(hi, lo+1e-9)
    span = hi-lo
    hi += .1*span
    xmin, xmax = min(start if _number(start) else rows[0]["time_s"], rows[0]["time_s"]), rows[-1]["time_s"]
    xmax = max(xmax, xmin+1e-9)
    def x(value): return 96+760*(value-xmin)/(xmax-xmin)
    def y(value): return 242-202*(value-lo)/(hi-lo)
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 292" style="font:22px system-ui" role="img" aria-label="{escape(title,quote=True)}"><title>{escape(title)} ({escape(unit)})</title><rect width="900" height="292" fill="white"/>']
    for i in range(5):
        value = lo+(hi-lo)*i/4
        parts.append(f'<path d="M96 {y(value):.3f} H856" stroke="#dbe3ec"/><text x="88" y="{y(value)+4:.3f}" text-anchor="end">{value:.3g}</text>')
        at = xmin+(xmax-xmin)*i/4
        parts.append(f'<text x="{x(at):.3f}" y="266" text-anchor="middle">{at:.3g}</text>')
    parts += ['<path d="M76 38 V242 H856" stroke="#7c8da1" fill="none"/>',
              f'<text x="96" y="22">{escape(unit)}</text><text x="466" y="286" text-anchor="middle">Tiempo del estudio (s)</text>']
    if _number(threshold):
        parts.append(f'<path d="M76 {y(threshold):.3f} H856" stroke="#a35100" stroke-dasharray="3 5"/><text x="852" y="{y(threshold)-5:.3f}" text-anchor="end">Criterio: {threshold:.4g}</text>')
    indices = _indices(rows, fields)
    for field,label,color in series:
        segment = []
        def flush():
            if segment:
                parts.append(f'<polyline aria-label="{escape(label,quote=True)}" points="{" ".join(segment)}" fill="none" stroke="{color}" stroke-width="2"'+(' stroke-dasharray="8 4"' if field=="bus_voltage_pu" else '')+'/>')
                segment.clear()
        for i in indices:
            value = rows[i].get(field)
            if not _number(value):
                flush()
            else:
                segment.append(f'{x(rows[i]["time_s"]):.3f},{y(value):.3f}')
        flush()
    parts.append('</svg>')
    svg = ''.join(parts)
    legend = ' · '.join(escape(label)+(' (sin datos)' if not any(_number(r.get(field)) for r in rows) else '') for field,label,_ in series)
    return f'<div class="legend">{legend}</div><div class="plot">'+svg+f'</div><p class="mobilehint note">Deslice el gráfico para ver el eje completo, o descargue el SVG.</p><p class="note">{len(rows)} muestras por ciclo; vista de {len(indices)} puntos. CSV/JSON conserva la trayectoria completa.</p>', svg


def _json(path, data):
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False),encoding="utf8")


def _csv(path, fields, rows):
    def cell(value):
        if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")):
            return "'"+value
        return value
    with path.open("w",newline="",encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream,fieldnames=fields,extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key:cell(value) for key,value in row.items()})


def _render(cases, folder):
    summaries, trajectories, sections = [], [], []
    for case_index, case in enumerate(cases):
        inputs, result, case_id = case["inputs"], case["result"], case["case_id"]
        folder_case = folder/f"case-{case_index+1:02d}"
        folder_case.mkdir()
        _json(folder_case/"Inputs.json", inputs)
        _json(folder_case/"Results.json", result)
        usable = result["status"] != "MODELICA_EXECUTION_FAILED"
        by_id = {r["motor_id"]:r for r in result.get("results", [])} if usable else {}
        status_label = {"MODELICA_MOTOR_STUDIES_COMPLETED":"Ejecución completada", "MODELICA_REFINEMENT_NOT_PASSED":"Refinamiento no aprobado", "MODELICA_EXECUTION_FAILED":"Fallo de ejecución"}[result["status"]]
        header = f'<section><div class="casehead"><h2>{escape(case_id)}</h2><p>Estudio: {escape(str(inputs.get("id","Sin ID")))} · <strong>{status_label}</strong></p>'
        pairing = "Entradas coinciden con el hash guardado" if case["input_pairing"] == "MATCHES_RECORDED_HASH" else "Sin hash previo de entradas; se conserva la copia leída"
        header += f'<p class="note">Frecuencia: {_text(inputs.get("network",{}).get("frequency_hz")," Hz")} · Datos: {escape(str(inputs.get("source_reference","Sin referencia")))} · {pairing}</p>'
        if not usable:
            header += '<p class="missing">Sin resultado verificado. El fallo de ejecución no demuestra incumplimiento del diseño.</p><p>'+escape(str(result.get("message","")))+' · Etapa: '+escape(str(result.get("failed_stage","No disponible")))+' · Último tiempo emitido: '+_text(result.get("last_emitted_time_s")," s")+'</p>'
        header += '</div>'
        cards = []
        for motor_index, motor in enumerate(inputs["motors"]):
            r = by_id.get(motor["id"], {})
            criteria = motor.get("criteria", {})
            start = motor.get("starting",{}).get("time_s")
            verification = r.get("verification",{}).get("passed")
            complete_criteria = all(_number(criteria.get(key)) for key in (
                "target_speed_fraction", "maximum_acceleration_time_s", "minimum_terminal_voltage_pu")) and isinstance(criteria.get("source_reference"),str) and bool(criteria["source_reference"].strip())
            observed = bool(r.get("trajectory")) and _number(r.get("minimum_voltage_pu")) and "acceleration_time_s" in r
            criterion = r.get("criterion",{}).get("passed") if verification is True and complete_criteria and observed and result["status"] == "MODELICA_MOTOR_STUDIES_COMPLETED" else None
            summary = {"case_id":case_id,"motor_id":motor["id"],"frequency_hz":inputs.get("network",{}).get("frequency_hz"),
                       "starting_method":motor.get("starting",{}).get("method"),"start_time_s":motor.get("starting",{}).get("time_s"),
                       **{key:r.get(key) for key in SUMMARY[5:9]},
                       "numerical_verification":_label(verification),"design_criterion":_label(criterion,True)}
            summaries.append(summary)
            title = f'<article id="case-{case_index+1:02d}-motor-{motor_index+1:02d}"><h3>{escape(case_id)} / {escape(motor["id"])} · {escape(str(summary["starting_method"]))}</h3>'
            title += '<p class="printonly">'+escape(case_id)+' · '+_text(summary['frequency_hz'],' Hz')+' · '+escape(str(inputs.get('source_reference','Sin referencia')))+'</p>'
            acceleration = _text(r.get("acceleration_time_s")," s")
            if "acceleration_time_s" in r and r["acceleration_time_s"] is None:
                acceleration = "Objetivo no alcanzado en el horizonte observado"
            title += '<div class="metrics">'+''.join(f'<div><span>{label}</span><strong>{text}</strong></div>' for label,text in [
                ("Refinamiento numérico",_label(verification)),("Criterios del estudio",_label(criterion,True)),
                ("Aceleración desde la orden",acceleration),("Orden de arranque (tiempo del estudio)",_text(summary["start_time_s"]," s")),
                ("Mínimo de barra",_text(r.get("minimum_bus_voltage_pu")," pu")),("Mínimo terminal",_text(r.get("minimum_voltage_pu")," pu")),
                ("Corriente RMS máxima de línea",_text(r.get("maximum_cycle_rms_current_a")," A")),
                ("Bypass (tiempo del estudio)","No aplica — DOL" if summary["starting_method"]=="DOL" else _text(r.get("bypass_time_s")," s"))])+'</div>'
            if verification is not True:
                title += '<p class="missing">Datos ausentes o refinamiento no aprobado: sin aceptación de diseño. Las curvas disponibles son diagnósticas.</p>'
            if not complete_criteria:
                title += '<p class="missing">Faltan criterios o su referencia: el cumplimiento no es evaluable.</p>'
            title += '<h4>Criterios declarados</h4><p>Velocidad objetivo: '+_text(criteria.get("target_speed_fraction")," × síncrona")+' · Aceleración máxima: '+_text(criteria.get("maximum_acceleration_time_s")," s")+' · Tensión terminal mínima: '+_text(criteria.get("minimum_terminal_voltage_pu")," pu")+'</p><p>Fuente: '+escape(str(criteria.get("source_reference","No disponible")))+'</p>'
            title += '<p class="note">Los criterios anteriores son los evaluados por el adaptador. No se infiere un límite de corriente o tensión de barra. Referencia de datos del motor: '+escape(str(motor.get("source_reference","No disponible")))+'</p>'
            rows = r.get("trajectory", [])
            frequency = summary["frequency_hz"]
            poles = motor.get("electrical",{}).get("pole_pairs")
            fraction = criteria.get("target_speed_fraction")
            target = 2*pi*frequency/poles*fraction if all(_number(v) and v>0 for v in (frequency,poles,fraction)) else None
            if rows:
                charts = []
                definitions = [([("current_a","Máximo RMS de las tres corrientes de línea","#087e8b")],"Corriente de línea por ciclo","A",None),
                               ([("speed_rad_s","Velocidad al final del ciclo","#087e8b")],"Velocidad mecánica","rad/s",target),
                               ([("torque_nm","Par electromagnético medio por ciclo","#087e8b")],"Par electromagnético","N·m",None),
                               ([("voltage_pu","Terminal — continua","#087e8b"),("bus_voltage_pu","Barra — discontinua","#6c4cb5")],"Tensión de barra y terminal","pu",criteria.get("minimum_terminal_voltage_pu"))]
                for chart_index,(series,name,unit,threshold) in enumerate(definitions):
                    graphic, svg = _svg(rows,series,name,unit,start,threshold)
                    if svg:
                        filename = f"motor-{motor_index+1:02d}-chart-{chart_index+1}.svg"
                        (folder_case/filename).write_text(svg,encoding="utf8")
                        link = f'<a href="case-{case_index+1:02d}/{filename}" download>Descargar SVG</a>'
                    else:
                        link = ""
                    charts.append('<figure><figcaption>'+name+'</figcaption>'+graphic+link+'</figure>')
                title += '<div class="charts">'+''.join(charts)+'</div>'
                trajectories += [{"case_id":case_id,"motor_id":motor["id"],**{key:row.get(key) for key in FIELDS}} for row in rows]
            else:
                title += '<p class="missing">Sin trayectoria disponible para este motor.</p>'
            cards.append(title+'</article>')
        sections.append(header+''.join(cards)+'</section>')
    _csv(folder/"Comparison.csv",SUMMARY,summaries)
    _csv(folder/"Trajectories.csv",("case_id","motor_id",*FIELDS),trajectories)
    _json(folder/"ReportData.json",{"schema":SCHEMA,"contract":contract(),"cases":cases,"comparison":summaries})
    headings = ["Caso","Motor","Hz","Método","Orden (s)","Aceleración (s)","Barra mín. (pu)","Terminal mín. (pu)","Corriente máx. (A)","Refinamiento","Criterios"]
    table = '<div class="table"><table><thead><tr>'+''.join('<th scope="col">'+h+'</th>' for h in headings)+'</tr></thead><tbody>'
    for summary in summaries:
        table += '<tr>'+''.join('<td>'+(_text(summary[key]) if key in SUMMARY[2:3]+SUMMARY[4:9] else escape(str(summary[key])))+'</td>' for key in SUMMARY)+'</tr>'
    table += '</tbody></table></div>'
    css = '''*{box-sizing:border-box}.plot{overflow-x:auto}.mobilehint,.printonly{display:none}body{margin:0;background:#edf2f7;color:#172c40;font:15px system-ui;line-height:1.5}main{max-width:1400px;margin:auto;padding:28px}h1{font-size:30px;line-height:1.2}h2{font-size:24px}h3{font-size:21px}h4{margin-bottom:4px}section,article,.intro{background:white;border:1px solid #d5e0e8;border-radius:12px;padding:22px;margin:18px 0}article{background:#fafcfe}.note,.legend{font-size:13px;color:#405a72}.missing{background:#fff4df;border-left:4px solid #b56b13;padding:12px}.metrics,.charts{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}.metrics>div{border:1px solid #d5e0e8;background:white;padding:12px;border-radius:8px}.metrics span{display:block;font-size:13px}.metrics strong{font-size:18px}figure{margin:0;padding:12px;background:white;border:1px solid #d5e0e8;border-radius:8px;min-width:0}figcaption{font-weight:700;font-size:17px;margin-bottom:8px}svg{display:block;width:100%;height:auto;font:12px system-ui;min-width:0}a{color:#006d77;overflow-wrap:anywhere}button{font:inherit;padding:9px 16px;border:1px solid #698397;border-radius:7px;background:white;cursor:pointer}.table{overflow:auto}table{border-collapse:collapse;width:100%;font-size:13px}th,td{text-align:left;padding:10px;border-bottom:1px solid #d5e0e8}th{background:#edf2f7;white-space:nowrap}p{overflow-wrap:anywhere}@media(max-width:740px){main{padding:12px}section,article,.intro{padding:14px}.metrics,.charts{grid-template-columns:1fr}h1{font-size:25px}.plot svg{min-width:650px}.mobilehint{display:block}}@page{size:A4 landscape;margin:12mm}@media print{body{background:white;font-size:10pt}main{max-width:none;padding:0}button,.downloads{display:none}section,article,.intro{border-radius:0;padding:10px}.metrics{grid-template-columns:repeat(3,minmax(0,1fr))}.charts{grid-template-columns:repeat(2,minmax(0,1fr))}figure,.metrics>div{break-inside:avoid}.table{overflow:visible}table{font-size:8pt;table-layout:fixed}th{white-space:normal}td,th{overflow-wrap:anywhere;padding:4px}thead{display:table-header-group}h2,h3,h4{break-after:avoid}svg{max-height:34mm}.casehead{display:none}.printonly{display:block;font-size:7.5pt}.charts .note,figure a{display:none}.plot{overflow:visible}.plot svg{min-width:0}.metrics{grid-template-columns:repeat(4,minmax(0,1fr));gap:6px}.metrics>div{padding:6px}.metrics strong{font-size:12pt}.metrics span{font-size:8pt}.charts{gap:8px}figure{padding:6px}figcaption{font-size:10pt}.legend,.note{font-size:8pt}article{break-inside:avoid}article p{margin:6px 0}.intro{padding:8px;margin:8px 0}.intro p{margin:6px 0}h1{font-size:22pt;margin:0}h2{font-size:16pt;margin:8px 0}h3{font-size:14pt;margin:6px 0}h4{margin:4px 0}th,td{padding:3px;font-size:7.5pt}section{margin:0;padding:0;border:0}article{margin:0;padding:4px;border:0;break-before:page;break-inside:avoid}}'''
    html = '<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Comparación de arranques — Modelica</title><style>'+css+'</style></head><body><main><header><h1>Arranque de motores</h1><p>Resultados guardados · OpenModelica / MSL · Informe Q9</p></header><div class="intro"><p>Equivalente RL trifásico equilibrado de barra común; alcance del estudio guardado. Los criterios son propios de cada caso. Comparar casos con distinta red, motor, frecuencia o criterio no demuestra superioridad de un método.</p><p>Tiempo en gráficos: segundos desde el inicio del estudio. Aceleración: duración desde la orden de cada motor. Corrientes RMS y par medio por ciclo; velocidad al final del ciclo. Tensiones: mínimo RMS entre pares de líneas dividido por la tensión LL base declarada; barra y terminal son mediciones diferentes.</p><p>Cada caso conserva sus resultados y su calificación original. El informe incluye copias de las entradas, resultados y hashes para su trazabilidad. La revisión y aprobación del estudio corresponden al ingeniero.</p><button id="print">Imprimir / guardar PDF</button><p class="downloads"><a href="Comparison.csv" download>Comparación CSV</a> · <a href="Trajectories.csv" download>Trayectorias CSV</a> · <a href="ReportData.json" download>Datos y fuentes JSON</a> · <a href="Integrity.json">Integridad</a></p></div><h2>Comparación entre casos</h2>'+table+''.join(sections)+'</main><script>document.getElementById("print").addEventListener("click",()=>window.print());</script></body></html>'
    (folder/"Informe.html").write_text(html,encoding="utf8")
    return summaries


def generate(studies, output_directory):
    try:
        if not isinstance(studies,list) or not 1 <= len(studies) <= 8:
            raise ValueError("ONE_TO_EIGHT_EXPLICIT_CASES_REQUIRED")
        cases = [_case(spec) for spec in studies]
        ids = [c["case_id"].casefold() for c in cases]
        if len(set(ids)) != len(ids):
            raise ValueError("DUPLICATE_CASE_ID")
    except (OSError, ValueError, KeyError, TypeError, AttributeError, OverflowError) as exc:
        return {"status":"BLOCKED_MSL_REPORT_INPUTS","message":str(exc),"solver_executed":False}
    folder = Path(output_directory).expanduser().resolve()
    try:
        folder.mkdir(parents=True,exist_ok=False)
    except OSError as exc:
        return {"status":"BLOCKED_MSL_REPORT_OUTPUT","message":str(exc),"solver_executed":False}
    try:
        summaries = _render(deepcopy(cases),folder)
        files = {str(p.relative_to(folder).as_posix()):_hash(p) for p in sorted(folder.rglob("*")) if p.is_file()}
        payload = {"schema":SCHEMA,"files_sha256":files,"report_source_sha256":_hash(__file__)}
        _json(folder/"Integrity.json",{"payload":payload,"payload_sha256":_payload_hash(payload)})
        return {"status":"MSL_REPORT_CREATED","output_directory":str(folder),"report":str(folder/"Informe.html"),
                "case_count":len(cases),"motor_count":len(summaries),"files_sha256":files,
                "solver_executed":False,"source_studies_modified":False,"professional_emission":False}
    except (OSError, ValueError, KeyError, TypeError, OverflowError) as exc:
        return {"status":"MSL_REPORT_FAILED","message":str(exc),"output_directory":str(folder),"solver_executed":False}


def verify(directory):
    issues = []
    folder = Path(directory).expanduser().resolve()
    try:
        index = _load(folder/"Integrity.json")
        data = index["payload"]
        if data["schema"] != SCHEMA or index["payload_sha256"] != _payload_hash(data):
            issues.append("INDEX_PAYLOAD_MISMATCH")
        entries = data["files_sha256"]
        if not isinstance(entries, dict) or not {"Informe.html","Comparison.csv","Trajectories.csv","ReportData.json"} <= set(entries):
            raise ValueError("INVALID_REPORT_INVENTORY")
        actual = {p.relative_to(folder).as_posix() for p in folder.rglob("*") if p.is_file() and p != folder/"Integrity.json"}
        if actual != set(entries):
            issues.append("EXACT_FILE_SET_MISMATCH")
        for name,digest in entries.items():
            relative = Path(name)
            if relative.is_absolute() or ".." in relative.parts or "\\" in name or ":" in name:
                issues.append("UNSAFE_REPORT_PATH")
                continue
            path = folder/relative
            if any(parent.is_symlink() for parent in [path,*path.parents] if parent != folder.parent):
                issues.append("SYMLINK_REPORT_PATH")
            elif not path.is_file() or _hash(path) != digest:
                issues.append("FILE_HASH_MISMATCH: "+name)
    except (OSError, ValueError, KeyError, TypeError, AttributeError, OverflowError) as exc:
        issues.append(str(exc))
    return {"ok":not issues,"issues":issues,"solver_executed":False,"professional_emission":False}


def execute_with_report(package, directory):
    """MCP orchestration only; keep the evidence-pinned physical adapter intact."""
    from . import modelica_motor_adapter
    result = modelica_motor_adapter.execute(package,directory)
    if result.get("status") not in STATUSES:
        return result
    presentation = generate([{"case_id":package["id"],"study_directory":str(directory)}], Path(directory)/"Report")
    return {**result,"presentation":presentation}


def register(mcp):
    @mcp.tool()
    def obtener_contrato_informe_dinamica_modelica() -> dict:
        """Informe de resultados MSL guardados: curvas por motor, criterios y comparación sin recalcular."""
        return contract()

    @mcp.tool()
    def generar_informe_dinamica_modelica(estudios: list[dict], directorio_salida: str) -> dict:
        """Recibe case_id/study_directory por caso. Copia fuentes, grafica y exporta CSV/HTML/SVG con hashes."""
        return generate(estudios,directorio_salida)

    @mcp.tool()
    def verificar_informe_dinamica_modelica(directorio_informe: str) -> dict:
        """Comprueba inventario exacto y hashes del informe; no autentica autor ni recalifica el estudio."""
        return verify(directorio_informe)
