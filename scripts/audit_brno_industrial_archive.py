"""Read public ETAP report databases; never execute ETAP or an electrical engine.

An audit match means that the pinned archive was inspected reproducibly. It is
deliberately separate from acceptance of the installation or its study results.
Only three pinned SQLite members are read; embedded scripts/MDF are not run.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import sqlite3
import tempfile
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
FACTS = ROOT / "examples/qualification/brno_industrial_2026.json"
MAX_DOWNLOAD = 32 * 1024 * 1024
MAX_MEMBER = 4 * 1024 * 1024
TABLES = ("Headr", "IBus", "Icable", "IXFMR2", "IConnect", "Isummary")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def download(source: dict) -> bytes:
    request = urllib.request.Request(source["url"], headers={"User-Agent": "MCP-Electrico-source-audit/1"})
    with urllib.request.urlopen(request, timeout=60) as response:
        data = response.read(MAX_DOWNLOAD + 1)
    require(len(data) <= MAX_DOWNLOAD, "Source exceeds download limit")
    require(len(data) == source["bytes"], "Source byte count changed")
    require(sha256(data) == source["sha256"], "Source SHA256 changed")
    return data


def read_database(path: Path, extra: tuple[str, ...] = ()) -> dict:
    # immutable/read-only, no extension loading, no source-supplied SQL or views.
    connection = sqlite3.connect(path.resolve().as_uri() + "?mode=ro&immutable=1", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute("PRAGMA trusted_schema=OFF")
        result = {}
        for table in TABLES + extra:
            exists = connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
            ).fetchone()
            require(bool(exists), f"Missing physical report table: {table}")
            result[table] = [dict(row) for row in connection.execute(f'SELECT * FROM "{table}"')]
        return result
    finally:
        connection.close()


def read_archive(path: Path, facts: dict) -> dict:
    require(path.stat().st_size == facts["archive"]["bytes"], "Archive byte count changed")
    require(sha256(path.read_bytes()) == facts["archive"]["sha256"], "Archive SHA256 changed")
    databases = {}
    with zipfile.ZipFile(path) as archive, tempfile.TemporaryDirectory() as temporary:
        for name, digest in facts["archive"]["members"].items():
            matches = [info for info in archive.infolist() if PurePosixPath(info.filename).name == name]
            require(len(matches) == 1, f"Missing or ambiguous archive member: {name}")
            member = matches[0]
            require(member.file_size <= MAX_MEMBER, f"Oversized SQLite member: {name}")
            data = archive.read(member)
            require(sha256(data) == digest, f"SQLite SHA256 changed: {name}")
            require(data.startswith(b"SQLite format 3\0"), f"Not SQLite: {name}")
            # Use our literal basename, never an archive-supplied extraction path.
            target = Path(temporary) / name
            target.write_bytes(data)
            extra = ("SeqOfOper", "SeqOfOperFaultSpec") if name.endswith("SQ2S") else ()
            databases[name.rsplit(".", 1)[1]] = read_database(target, extra)
    return databases


def observations(databases: dict) -> dict:
    lf, sc, sq = (databases[ext] for ext in ("LF1S", "SI1S", "SQ2S"))
    geometry_fields = ("ID", "FromBus", "ToBus", "Size", "Length", "No/Ph")

    def geometry(database: dict) -> list:
        return sorted(tuple(row[field] for field in geometry_fields) for row in database["Icable"])

    return {
        "counts": {ext: {table: len(db[table]) for table in ("IBus", "Icable", "IXFMR2", "IConnect")}
                   for ext, db in databases.items()},
        "phase_angles_raw_degrees": {ext: sorted({row["PhaseAngle"] for row in db["IXFMR2"]})
                                     for ext, db in databases.items()},
        "cable_temperatures_raw_c": {ext: sorted({row["TempOp"] for row in db["Icable"]})
                                     for ext, db in databases.items()},
        "lf_only_cables_vs_sc": sorted({row["ID"] for row in lf["Icable"]} -
                                       {row["ID"] for row in sc["Icable"]}),
        "fault_locations_in_sequence_export": sorted({row["BusID"] for row in sq["SeqOfOperFaultSpec"]}),
        "sequence_rows": len(sq["SeqOfOper"]),
        "did_not_trip_rows": sum(row["Condition2"] == "DID NOT TRIP" for row in sq["SeqOfOper"]),
        "transformers_with_secondary_petersen_coil": {
            ext: sum(row["SecGrdType"] == "Petersen Coil" for row in db["IXFMR2"])
            for ext, db in databases.items()},
        "sc_sq_cable_geometry_equal": geometry(sc) == geometry(sq),
    }


def audit(path: Path, facts: dict, thesis_verified: bool) -> dict:
    databases = read_archive(path, facts)
    observed = observations(databases)
    require(observed == facts["expected_observations"], "Archive observations differ from reviewed facts")
    # A reference is blocked even when every source/observation check passes.
    require(facts["admission"]["installation_validation_closed"] is False, "Audit cannot close a plant")
    return {
        "schema": facts["schema"], "case_id": facts["case_id"],
        "audit_reproduced": True, "archive_sha256": facts["archive"]["sha256"],
        "electrical_calculation_performed": False,
        "source_audit_does_not_recompute_pf_replay": True,
        "member_sha256": facts["archive"]["members"],
        "thesis_source_verified": thesis_verified,
        "observations": observed,
        "report_headers": {ext: db["Headr"] for ext, db in databases.items()},
        "raw_sequence_results": databases["SQ2S"]["SeqOfOper"],
        "sequence_time_units_verified": False,
        "sequence_results_recomputed": False,
        "metadata_match_proves_same_electrical_model": False,
        "admission": facts["admission"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, help="Previously downloaded pinned ZIP")
    parser.add_argument("--verify-upstream", action="store_true", help="Download and hash the official thesis and ZIP")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    require(args.archive is not None or args.verify_upstream, "Provide --archive or --verify-upstream")
    facts = json.loads(FACTS.read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory() as temporary:
        path = args.archive
        if args.verify_upstream:
            thesis = download(facts["thesis"])
            require(thesis.startswith(b"%PDF"), "Thesis source is not PDF")
            path = Path(temporary) / "source.zip"
            path.write_bytes(download(facts["archive"]))
        result = audit(path, facts, args.verify_upstream)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"audit_reproduced": result["audit_reproduced"],
                      "installation_validation_closed": False,
                      "status": result["admission"]["status"]}))


if __name__ == "__main__":
    main()
