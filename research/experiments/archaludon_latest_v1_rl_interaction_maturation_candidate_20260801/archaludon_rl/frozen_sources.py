"""Frozen, repository-relative source receipts for Phase 0.

Only declared source files participate in execution.  Generated ``__pycache__``
files are deliberately excluded from the engine receipt.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
from typing import Iterable


LATEST_DIR = (
    "_local_generated/analysis_outputs/"
    "archaludon_historical_vs_general_visible_counterattack_ready_rotation_20260731/"
    "inputs/candidate_exact"
)
LATEST_ARCHIVE = (
    "autonomous_gold_20260715/packages/"
    "archaludon_general_visible_counterattack_ready_rotation_v1_clean_20260731_0457/"
    "submission_archaludon_general_visible_counterattack_ready_rotation_v1_20260731.tar.gz"
)
SEEDED_ENGINE_DIR = (
    "_local_generated/analysis_outputs/cynthia_v9_vs_v11_poffin_role_selection_20260713/"
    "seeded_engine"
)
HISTORICAL_ENGINE_TREE_SHA256 = (
    "586B92FDEA892CBB147D4C6A113575CCD98E4FC90528BABB6E8F7294D0CBEBF2"
)


@dataclass(frozen=True)
class FileReceipt:
    relative_path: str
    sha256: str
    size: int | None = None


LATEST_RECEIPTS = (
    FileReceipt(
        f"{LATEST_DIR}/main.py",
        "AC70708082882C7BA01CFBF81D29F534B95166DFF6BAD11E1EF1FA001A5F79D2",
        503633,
    ),
    FileReceipt(
        f"{LATEST_DIR}/deck.csv",
        "08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A",
        250,
    ),
    FileReceipt(
        LATEST_ARCHIVE,
        "B2992E4A5F97A14127F6E75D4D3F3F528725E34ABC9854F06592B82D8EA24C95",
    ),
)

# Explicit immutable runtime surface.  This avoids treating interpreter-created
# bytecode as source while still rejecting undeclared engine/runtime files.
ENGINE_RECEIPTS = (
    FileReceipt(f"{SEEDED_ENGINE_DIR}/cg/Export.lib", "2758FBAAA51557D72E1EBBEF71AFBA1F6FCE9BB73162154301A322A4515C0223", 246290),
    FileReceipt(f"{SEEDED_ENGINE_DIR}/cg/__init__.py", "E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855", 0),
    FileReceipt(f"{SEEDED_ENGINE_DIR}/cg/api.py", "C31AA24E63BF0E71779D97F6286D10A2BF23CB4A3B9449C977F63577704FBE6C", 27358),
    FileReceipt(f"{SEEDED_ENGINE_DIR}/cg/cg.dll", "0C6153F9206366F2588E5C601AB086EA997A66E80E4FEB6D95635B2987C9929B", 2238464),
    FileReceipt(f"{SEEDED_ENGINE_DIR}/cg/cg.pdb", "79072C72B247E175A52B7F8C9DC8BBEA545CA896A24E131F9BF5A4A7C87C5E6C", 11149312),
    FileReceipt(f"{SEEDED_ENGINE_DIR}/cg/game.py", "B88E6E0223FF8FCB789F6B2B094B9556B2725A624AC69AE5C367CE822F1E3BC2", 2481),
    FileReceipt(f"{SEEDED_ENGINE_DIR}/cg/libcg-arm64.so", "030B4728CE9FB9E90B75830B7CF7236F71859732A05EC4A377078EEE0421BBE5", 1300584),
    FileReceipt(f"{SEEDED_ENGINE_DIR}/cg/libcg.dylib", "77BB978A8129B094452679E0DAF0DA69593AFDA7331685F4642C0D4A94D39D82", 1245544),
    FileReceipt(f"{SEEDED_ENGINE_DIR}/cg/libcg.so", "FFD89BF923525A3E6FEB5E6201E96A866C0F456895499ED5C4A566303CAAE67C", 1342400),
    FileReceipt(f"{SEEDED_ENGINE_DIR}/cg/sim.py", "3096ED0CBB13CAEB1FA6DFBC78515642F833DC5D3F6847F757937CFDCB5410D4", 2533),
    FileReceipt(f"{SEEDED_ENGINE_DIR}/cg/utils.py", "60F29665CEE0A88525D6F0383BC45959A6262D16FE35EF380AECE1E0EA13C49B", 1970),
)
ENGINE_RUNTIME_MANIFEST_SHA256 = (
    "DAAD95164512EA3F210B4679840FE2CD631300044A6E5F49C41642EABD823089"
)


def find_repo_root(start: Path | None = None) -> Path:
    cursor = (start or Path(__file__)).resolve()
    if cursor.is_file():
        cursor = cursor.parent
    for candidate in (cursor, *cursor.parents):
        if (candidate / "AGENTS.md").is_file() and (candidate / ".git").exists():
            return candidate
    raise FileNotFoundError("repository root containing AGENTS.md and .git not found")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def _verify_receipts(root: Path, receipts: Iterable[FileReceipt]) -> dict[str, str]:
    verified: dict[str, str] = {}
    for receipt in receipts:
        path = root / receipt.relative_path
        if not path.is_file():
            raise FileNotFoundError(f"frozen source missing: {receipt.relative_path}")
        if receipt.size is not None and path.stat().st_size != receipt.size:
            raise ValueError(f"size mismatch: {receipt.relative_path}")
        actual = sha256_file(path)
        if actual != receipt.sha256:
            raise ValueError(
                f"SHA256 mismatch for {receipt.relative_path}: "
                f"expected {receipt.sha256}, got {actual}"
            )
        verified[receipt.relative_path] = actual
    return verified


def engine_runtime_manifest_sha256(root: Path | None = None) -> str:
    repo = (root or find_repo_root()).resolve()
    engine = repo / SEEDED_ENGINE_DIR
    declared: list[tuple[str, Path]] = []
    for receipt in ENGINE_RECEIPTS:
        path = repo / receipt.relative_path
        declared.append((path.relative_to(engine).as_posix(), path))
    rows = [
        f"{relative}\0{path.stat().st_size}\0{sha256_file(path)}\n".encode("utf-8")
        for relative, path in sorted(declared)
    ]
    return hashlib.sha256(b"".join(rows)).hexdigest().upper()


def verify_frozen_sources(
    root: Path | None = None, *, reject_unexpected_engine_files: bool = True
) -> dict[str, object]:
    repo = (root or find_repo_root()).resolve()
    latest = _verify_receipts(repo, LATEST_RECEIPTS)
    engine = _verify_receipts(repo, ENGINE_RECEIPTS)
    manifest_hash = engine_runtime_manifest_sha256(repo)
    if manifest_hash != ENGINE_RUNTIME_MANIFEST_SHA256:
        raise ValueError(
            "seeded engine immutable manifest mismatch: "
            f"expected {ENGINE_RUNTIME_MANIFEST_SHA256}, got {manifest_hash}"
        )
    if reject_unexpected_engine_files:
        engine_root = repo / SEEDED_ENGINE_DIR
        actual = {
            path.relative_to(engine_root).as_posix()
            for path in engine_root.rglob("*")
            if path.is_file() and "__pycache__" not in path.parts
        }
        declared = {
            (repo / receipt.relative_path).relative_to(engine_root).as_posix()
            for receipt in ENGINE_RECEIPTS
        }
        if actual != declared:
            raise ValueError(
                f"undeclared engine files: extra={sorted(actual - declared)}, "
                f"missing={sorted(declared - actual)}"
            )
    return {
        "latest": latest,
        "engine": engine,
        "engine_runtime_manifest_sha256": manifest_hash,
        "historical_engine_tree_sha256": HISTORICAL_ENGINE_TREE_SHA256,
    }


def latest_source_dir(root: Path | None = None) -> Path:
    return (root or find_repo_root()) / LATEST_DIR


def seeded_engine_dir(root: Path | None = None) -> Path:
    return (root or find_repo_root()) / SEEDED_ENGINE_DIR


def checkpoint_source_hashes() -> dict[str, str]:
    """Receipts that bind a policy checkpoint to teacher and static catalog."""

    hashes = {
        receipt.relative_path: receipt.sha256 for receipt in LATEST_RECEIPTS
    }
    hashes["seeded_engine_runtime_manifest"] = ENGINE_RUNTIME_MANIFEST_SHA256
    return hashes
