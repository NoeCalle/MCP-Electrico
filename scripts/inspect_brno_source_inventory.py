"""Bounded inspection of pinned ETAP reports; no ETAP/MDF code is executed."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sqlite3
import tempfile
import zipfile

import audit_brno_industrial_archive as source

INTEREST = re.compile(r"bus|cable|xfmr|trans|power|grid|gen|motor|breaker|relay|lvcb|hvcb|tcc|star|setting|study|case|connect|load|option|scen", re.I)
SECRET = re.compile(r"password|token|license|credential|connectionstring|secret", re.I)


def quote(name):
    return '"' + name.replace('"', '""') + '"'


def printable(value, column):
    if SECRET.search(column):
        return "REDACTED"
    if isinstance(value, bytes):
        return {"binary_bytes": len(value), "sha256": hashlib.sha256(value).hexdigest()}
    if isinstance(value, str) and len(value) > 160:
        return {"text_length": len(value), "prefix": value[:160]}
    return value


def inspect_database(path):
    connection = sqlite3.connect(path.resolve().as_uri() + "?mode=ro&immutable=1", uri=True)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA trusted_schema=OFF")
    try:
        tables = connection.execute("SELECT name, sql FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
        source.require(len(tables) <= 2048, "Excessive table count")
        result = []
        for table in tables:
            name = table["name"]
            if not str(table["sql"] or "").lstrip().upper().startswith("CREATE TABLE"):
                continue
            count = connection.execute("SELECT COUNT(*) FROM " + quote(name)).fetchone()[0]
            columns = [dict(row) for row in connection.execute("PRAGMA table_info(" + quote(name) + ")")]
            item = {"table": name, "row_count": count, "columns": columns}
            if count:
                item["samples"] = [
                    {key: printable(row[key], key) for key in row.keys()}
                    for row in connection.execute("SELECT * FROM " + quote(name) + " LIMIT 2")
                ]
                print("BRNO_TABLE=" + json.dumps(item, ensure_ascii=False, allow_nan=False))
            result.append(item)
        return result
    finally:
        connection.close()


def main(output, mdf_copy=None):
    output.mkdir(parents=True, exist_ok=False)
    facts = json.loads(source.FACTS.read_text(encoding="utf8"))
    data = source.download(facts["archive"])
    with tempfile.TemporaryDirectory() as temp:
        archive_path = Path(temp) / "source.zip"
        archive_path.write_bytes(data)
        inventory, databases = [], {}
        with zipfile.ZipFile(archive_path) as archive:
            source.require(sum(i.file_size for i in archive.infolist()) <= 512 * 1024 * 1024, "Excessive archive expansion")
            for info in archive.infolist():
                if info.is_dir():
                    continue
                name = PurePosixPath(info.filename).name
                record = {"path": info.filename, "bytes": info.file_size, "compressed_bytes": info.compress_size}
                if name.lower().endswith((".mdf", ".ldf")):
                    with archive.open(info) as handle:
                        header = handle.read(8192)
                    record["header_first_16_hex"] = header[:16].hex()
                    record["first_page_sha256"] = hashlib.sha256(header).hexdigest()
                inventory.append(record)
                if mdf_copy is not None and name in ("BKLRSKPRCAMDLZ.MDF", "BKLRSKPRCAMDLZ_log.LDF"):
                    source.require(info.file_size <= 64 * 1024 * 1024, "Excessive database size")
                    mdf_copy.mkdir(parents=True, exist_ok=True)
                    blob = archive.read(info)
                    (mdf_copy / name).write_bytes(blob)
                    print("BRNO_DATABASE_COPY=" + json.dumps({"name": name, "bytes": len(blob), "sha256": source.sha256(blob)}))
            print("BRNO_ARCHIVE_MEMBERS=" + json.dumps(inventory, ensure_ascii=False))
            for name, digest in facts["archive"]["members"].items():
                matches = [i for i in archive.infolist() if PurePosixPath(i.filename).name == name]
                source.require(len(matches) == 1 and matches[0].file_size <= source.MAX_MEMBER, "Invalid SQLite member")
                blob = archive.read(matches[0])
                source.require(source.sha256(blob) == digest, "Pinned SQLite changed")
                path = Path(temp) / name
                path.write_bytes(blob)
                print("BRNO_DATABASE=" + name)
                databases[name] = inspect_database(path)
    result = {"schema": "BRNO_DEEP_REPORT_INVENTORY_V1", "archive_sha256": facts["archive"]["sha256"],
              "archive_members": inventory, "databases": databases,
              "electrical_calculation_performed": False, "mdf_executed_or_attached": False,
              "installation_validation_closed": False}
    (output / "inventory.json").write_text(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False), encoding="utf8")
    print("BRNO_INVENTORY_DONE=" + json.dumps({"databases": len(databases), "members": len(inventory), "installation_validation_closed": False}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--mdf-copy", type=Path)
    args = parser.parse_args()
    main(args.output, args.mdf_copy)
