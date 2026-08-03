from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[4]
BASE_SPEC_PATH = ROOT / (
    "autonomous_gold_20260715/evaluation_specs/"
    "archaludon_historical_silver_single_resolver_salvage_v1_rule1/"
    "fixed160_spec.json"
)
OUTPUT_ROOT = Path(__file__).resolve().parent / "mismatch_diagnostics_raw_repair1"
V2_TARGET = ROOT / (
    "autonomous_gold_20260715/candidates/"
    "archaludon_historical_silver_single_resolver_salvage_rule3_repair_v2"
)
V2_DIAGNOSTIC = Path(__file__).resolve().parent / "diagnostic_v2"
V3_TARGET = ROOT / (
    "autonomous_gold_20260715/candidates/"
    "archaludon_certified_late_boundary_ultra_ball_route_v3_repair1"
)
V3_DIAGNOSTIC = ROOT / (
    "autonomous_gold_20260715/implementation/"
    "archaludon_certified_late_boundary_ultra_ball_route_v3_repair1/"
    "diagnostic_agent"
)

EXPECTED = {
    BASE_SPEC_PATH: "E2B8986663A43A7F6F52888E487F39B8D059CDCDDF441A3E87D8C093DF15274C",
    V2_TARGET / "main.py": "4287A616E1611F5697964D9F4065978EED1CEA72CDB48C9F63F1430D69106C35",
    V2_TARGET / "deck.csv": "08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A",
    V2_DIAGNOSTIC / "main.py": "246DF2154D752572F5AC14BFBD66E48E0C0EF2ABBEEC66F82BDD509CBA438F28",
    V2_DIAGNOSTIC / "deck.csv": "08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A",
    V3_TARGET / "main.py": "3D95357E75E0B00CB679C1A31F6612AD1FA0EF44914E8ECA8C272CE9220027C3",
    V3_TARGET / "deck.csv": "08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A",
    V3_DIAGNOSTIC / "main.py": "24B28C41BF65B0CA5E4069895BD7DDA2322D0DAE5BA2B6A4DED7E5A431A981D8",
    V3_DIAGNOSTIC / "deck.csv": "08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A",
}

OPPONENTS = {
    "historical_silver": (
        "_local_generated/analysis_outputs/reference_agents/historical_silver_archaludon_54495224",
        "F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E",
        "08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A",
    ),
    "arch_peak": (
        "submission_archaludon_gtmidguard_lucariobev_crustledeckguard_archattach_ruleinline_20260710",
        "9F4A35D7CC2365AC2A9A5B1A684E4C66618FEF08E6DD0635D75EA49AF423313D",
        "08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A",
    ),
    "marnie_kazuki_live": (
        "opponents/meta_agents/marnie_kazuki_live_85083586_simple",
        "B2317C6CD6A031912BCFE89D5498B33A056F1D9583C7631E046E4F8ABAD9E59D",
        "F75CB0C32939525FF083FCB5C4D6052D413E21644FDAFF81DE717F9121EAEE1B",
    ),
}

JOBS = [
    ("historical_silver", 314159278),
    ("arch_peak", 314159278),
    ("historical_silver", 314159282),
    ("arch_peak", 314159282),
    ("marnie_kazuki_live", 314159282),
    ("historical_silver", 314159294),
    ("arch_peak", 314159294),
    ("historical_silver", 314159302),
    ("arch_peak", 314159302),
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def validate() -> dict:
    for path, expected in EXPECTED.items():
        if not path.is_file() or sha256(path) != expected:
            raise AssertionError((path, expected, sha256(path) if path.is_file() else None))
    base = json.loads(BASE_SPEC_PATH.read_text(encoding="utf-8"))
    for runner in base["runners"].values():
        path = ROOT / runner["path"]
        if sha256(path) != runner["sha256"]:
            raise AssertionError(path)
    for relative, expected in base["engine"]["files"].items():
        path = ROOT / base["engine"]["path"] / relative
        if sha256(path) != expected:
            raise AssertionError(path)
    for _label, (relative, main_hash, deck_hash) in OPPONENTS.items():
        if sha256(ROOT / relative / "main.py") != main_hash:
            raise AssertionError(relative)
        if sha256(ROOT / relative / "deck.csv") != deck_hash:
            raise AssertionError(relative)
    return base


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    base = validate()
    if OUTPUT_ROOT.exists():
        raise AssertionError(f"refusing existing destination: {OUTPUT_ROOT}")
    print(json.dumps({"jobs": JOBS, "execute": args.execute}, indent=2))
    if not args.execute:
        return
    OUTPUT_ROOT.mkdir(parents=True)
    manifest = []
    wrapper = ROOT / base["runners"]["trace_preservation_wrapper"]["path"]
    python = ROOT / base["python"]
    engine = ROOT / base["engine"]["path"]
    for index, (label, seed) in enumerate(JOBS):
        relative = OPPONENTS[label][0]
        output = OUTPUT_ROOT / f"{index:02d}_{seed}_{label}"
        command = [
            str(python),
            str(wrapper),
            "--engine-dir",
            str(engine),
            "--baseline",
            str(V2_DIAGNOSTIC),
            "--candidate",
            str(V3_DIAGNOSTIC),
            "--opponent",
            f"{label}={ROOT / relative}",
            "--games-per-seat",
            "1",
            "--seed-base",
            str(seed),
            "--max-steps",
            "1000",
            "--output-dir",
            str(output),
        ]
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["RULE3_V2_TELEMETRY"] = str(output / "v2_telemetry.jsonl")
        env["RULE3_V3_TELEMETRY"] = str(output / "v3_telemetry.jsonl")
        completed = subprocess.run(command, cwd=ROOT, env=env, check=False)
        if completed.returncode:
            raise SystemExit(completed.returncode)
        report = json.loads((output / "report.json").read_text(encoding="utf-8"))
        if report.get("valid") is not True or report.get("invalid_reasons"):
            raise AssertionError(report)
        manifest.append(
            {
                "opponent": label,
                "seed": seed,
                "output": str(output),
                "report_sha256": sha256(output / "report.json"),
                "paired_results_sha256": sha256(output / "paired_results.csv"),
                "v2_telemetry_sha256": sha256(output / "v2_telemetry.jsonl"),
                "v3_telemetry_sha256": sha256(output / "v3_telemetry.jsonl"),
            }
        )
    (OUTPUT_ROOT / "diagnostic_manifest.jsonl").write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in manifest),
        encoding="utf-8",
    )
    print(json.dumps({"completed_jobs": len(manifest)}, indent=2))


if __name__ == "__main__":
    main()
