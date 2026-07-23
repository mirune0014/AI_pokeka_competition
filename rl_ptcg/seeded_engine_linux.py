"""Build a seeded Linux engine from the private Kaggle competition inputs.

The competition-only C++ source is verified, patched, and compiled in a
temporary directory. Source files are never copied into the output artifact.
"""
from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import tempfile
from typing import Any, Callable, Mapping


SCHEMA_VERSION = "ptcg_seeded_engine_linux.v1"
OFFICIAL_ENGINE_HASHES = {
    "Api.h": "786acae884631bdcbab0311471316bc75d62acb465b8011bf09dad05628bcafd",
    "Export.cpp": "1269f64671527d50b8560540473438e9781926fdbdb0c9383b344f0fb91bf82f",
}
PATCHED_ENGINE_HASHES = {
    "Api.h": "8c25f21fc3984682fbc2df667d4bb8abfdd8ff67763e9767ac49b35124efc2a8",
    "Export.cpp": "833025c84ab74da28066a57d58d3e08b08b0ebe27469589790227c6d8d2ec62d",
}
OFFICIAL_WRAPPER_HASHES = {
    "__init__.py": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "api.py": "593f1298e52a635f90f8f505a52113e9af114f444c293404e37906f18ee06ced",
    "game.py": "3bd3d4f4a369a11e6d2f5da9094cf15ebc410a2221835e6417b7cff4883f1fc2",
    "sim.py": "1555f57f5d22bf4c09d70e0e667a916e575e68c9dd1de9ead34ba5e7e4968655",
    "utils.py": "60f29665cee0a88525d6f0383bc45959a6262d16fe35ef380aece1e0ea13c49b",
}
PATCHED_WRAPPER_HASHES = {
    "__init__.py": OFFICIAL_WRAPPER_HASHES["__init__.py"],
    "api.py": "3bc75c7a66707e5aa944d8a65af8b0e960818bf2b3972c849082a4c3c0078fac",
    "game.py": "c01de4e903a23e0ecc8ccdbf059f899bbb7aed51a3b81f2df3f5b3bc7e61394b",
    "sim.py": "3bb7c98711a21f146a9d1c3b8c95ea24b070ae9de8084ef9993531fa85715eb2",
    "utils.py": OFFICIAL_WRAPPER_HASHES["utils.py"],
}
REQUIRED_SYMBOLS = (
    "AgentSeed", "BattleStartSeeded", "SearchBegin", "SearchEnd",
    "SearchRelease", "SearchStep",
)


def file_sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def canonical_sha256(value: Any) -> str:
    encoded = (json.dumps(
        value, sort_keys=True, ensure_ascii=True, separators=(",", ":"),
    ) + "\n").encode("ascii")
    return sha256(encoded).hexdigest()


def _self_hash(value: Mapping[str, Any]) -> str:
    return canonical_sha256({key: item for key, item in value.items() if key != "manifest_sha256"})


def _replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise ValueError("seed patch %s expected one match, found %d" % (label, count))
    return text.replace(old, new, 1)


def patch_api_header(text: str) -> str:
    text = _replace_once(
        text,
        "inline StartData ApiBattleStart(int* cards) {",
        "inline StartData ApiBattleStartConfigured(int* cards, uint32_t seed, bool deviceRand) {",
        "api-config-signature",
    )
    text = _replace_once(
        text,
        "\tstd::random_device rd;\n\tGameConfig config = {};\n\tconfig.seed = rd();\n"
        "\tconfig.recordLog = true;\n\tconfig.deviceRand = true;",
        "\tGameConfig config = {};\n\tconfig.seed = seed;\n"
        "\tconfig.recordLog = true;\n\tconfig.deviceRand = deviceRand;",
        "api-config-rng",
    )
    text = _replace_once(
        text,
        "\tdata->init(config);\n\tstd::seed_seq seq{ rd(), rd(), rd(), rd() };\n"
        "\tdata->game.rng = std::mt19937(seq);\n",
        "\tdata->init(config);\n",
        "api-random-device-reseed",
    )
    text = _replace_once(
        text,
        "}\n\ninline ApiData* ApiAgentStart() {",
        "}\n\ninline StartData ApiBattleStart(int* cards) {\n"
        "\treturn ApiBattleStartConfigured(cards, std::random_device()(), true);\n"
        "}\n\ninline StartData ApiBattleStartSeeded(int* cards, uint32_t seed) {\n"
        "\t// Game::init treats zero as \"choose a random seed\".\n"
        "\treturn ApiBattleStartConfigured(cards, seed == 0 ? 1 : seed, false);\n"
        "}\n\ninline ApiData* ApiAgentStart() {",
        "api-battle-wrappers",
    )
    text = _replace_once(
        text,
        "\treturn data;\n}\n\ninline void ApiBattleFinish(ApiData* data) {",
        "\treturn data;\n}\n\ninline void ApiAgentSeed(ApiData* data, uint32_t seed) {\n"
        "\tuint32_t value = seed == 0 ? 1 : seed;\n"
        "\tdata->game.config.seed = value;\n"
        "\tdata->game.config.deviceRand = false;\n"
        "\tdata->game.rng = std::mt19937(value);\n"
        "}\n\ninline void ApiBattleFinish(ApiData* data) {",
        "api-agent-seed",
    )
    return text


def patch_export_cpp(text: str) -> str:
    text = _replace_once(
        text,
        "  GAME_API StartData BattleStart(int* cards) {\n"
        "    return ApiBattleStart(cards);\n  }\n\n"
        "  GAME_API ApiData* AgentStart() {",
        "  GAME_API StartData BattleStart(int* cards) {\n"
        "    return ApiBattleStart(cards);\n  }\n\n"
        "  GAME_API StartData BattleStartSeeded(int* cards, uint32_t seed) {\n"
        "    return ApiBattleStartSeeded(cards, seed);\n  }\n\n"
        "  GAME_API ApiData* AgentStart() {",
        "export-battle-seed",
    )
    text = _replace_once(
        text,
        "  GAME_API ApiData* AgentStart() {\n"
        "    return ApiAgentStart();\n  }\n\n"
        "  GAME_API void BattleFinish(ApiData* data) {",
        "  GAME_API ApiData* AgentStart() {\n"
        "    return ApiAgentStart();\n  }\n\n"
        "  GAME_API void AgentSeed(ApiData* data, uint32_t seed) {\n"
        "    if (data->apiDataType != 2) {\n      return;\n    }\n"
        "    ApiAgentSeed(data, seed);\n  }\n\n"
        "  GAME_API void BattleFinish(ApiData* data) {",
        "export-agent-seed",
    )
    return text


def patch_api_py(text: str) -> str:
    return _replace_once(
        text,
        "    return to_dataclass(obs, Observation)\n\n"
        "def search_begin(agent_observation: Observation,",
        "    return to_dataclass(obs, Observation)\n\n"
        "def search_seed(seed: int) -> None:\n"
        "    \"\"\"Reset the local Search API RNG when the engine exposes AgentSeed.\"\"\"\n"
        "    global agent_ptr\n"
        "    if \"agent_ptr\" not in globals():\n        agent_ptr = lib.AgentStart()\n"
        "    if not hasattr(lib, \"AgentSeed\"):\n"
        "        raise RuntimeError(\"This local engine does not expose AgentSeed.\")\n"
        "    value = int(seed) & 0xFFFFFFFF\n"
        "    lib.AgentSeed(agent_ptr, ctypes.c_uint32(value if value != 0 else 1))\n\n"
        "def search_begin(agent_observation: Observation,",
        "python-search-seed",
    )


def patch_sim_py(text: str) -> str:
    text = _replace_once(
        text,
        "lib.BattleStart.restype = StartData\n"
        "lib.BattleStart.argtypes = [ctypes.POINTER(ctypes.c_int)]\n\n"
        "lib.AgentStart.restype = ctypes.c_void_p\n",
        "lib.BattleStart.restype = StartData\n"
        "lib.BattleStart.argtypes = [ctypes.POINTER(ctypes.c_int)]\n\n"
        "if hasattr(lib, \"BattleStartSeeded\"):\n"
        "    lib.BattleStartSeeded.restype = StartData\n"
        "    lib.BattleStartSeeded.argtypes = [ctypes.POINTER(ctypes.c_int), ctypes.c_uint32]\n\n"
        "lib.AgentStart.restype = ctypes.c_void_p\n",
        "python-battle-seed-signature",
    )
    return _replace_once(
        text,
        "lib.AgentStart.restype = ctypes.c_void_p\n\n"
        "lib.BattleFinish.argtypes = [ctypes.c_void_p]\n",
        "lib.AgentStart.restype = ctypes.c_void_p\n\n"
        "if hasattr(lib, \"AgentSeed\"):\n"
        "    lib.AgentSeed.argtypes = [ctypes.c_void_p, ctypes.c_uint32]\n\n"
        "lib.BattleFinish.argtypes = [ctypes.c_void_p]\n",
        "python-agent-seed-signature",
    )


def patch_game_py(text: str) -> str:
    text = _replace_once(
        text,
        "def battle_start(deck0: list[int], deck1: list[int]) -> tuple[dict, StartData]:",
        "def battle_start(deck0: list[int], deck1: list[int], seed: int | None = None) -> tuple[dict, StartData]:",
        "python-battle-start-signature",
    )
    return _replace_once(
        text,
        "    start_data = lib.BattleStart(arg)\n",
        "    if seed is None:\n        start_data = lib.BattleStart(arg)\n"
        "    elif hasattr(lib, \"BattleStartSeeded\"):\n"
        "        start_data = lib.BattleStartSeeded(arg, ctypes.c_uint32(seed))\n"
        "    else:\n"
        "        raise RuntimeError(\"This local engine does not expose BattleStartSeeded.\")\n",
        "python-battle-start-call",
    )


ENGINE_PATCHERS: Mapping[str, Callable[[str], str]] = {
    "Api.h": patch_api_header,
    "Export.cpp": patch_export_cpp,
}
WRAPPER_PATCHERS: Mapping[str, Callable[[str], str]] = {
    "api.py": patch_api_py,
    "game.py": patch_game_py,
    "sim.py": patch_sim_py,
}


def _verify_hashes(root: Path, expected: Mapping[str, str], label: str) -> None:
    for name, digest in expected.items():
        path = root / name
        if not path.is_file() or file_sha256(path) != digest:
            raise ValueError("%s input hash mismatch: %s" % (label, name))


def _source_tree_binding(root: Path) -> dict[str, str]:
    return {
        str(path.relative_to(root)).replace("\\", "/"): file_sha256(path)
        for path in sorted(root.rglob("*")) if path.is_file()
    }


def _patch_file(path: Path, patcher: Callable[[str], str], expected_hash: str) -> None:
    patched = patcher(path.read_text(encoding="utf-8"))
    path.write_text(patched, encoding="utf-8", newline="\n")
    if file_sha256(path) != expected_hash:
        raise ValueError("patched output hash mismatch: %s" % path.name)


def _verify_symbols(binary: Path) -> None:
    completed = subprocess.run(
        ["nm", "-D", "--defined-only", str(binary)],
        check=False, capture_output=True, text=True,
    )
    if completed.returncode != 0:
        raise RuntimeError("could not inspect seeded engine symbols: %s" % completed.stderr[-2000:])
    exported = {
        line.split()[-1] for line in completed.stdout.splitlines() if line.split()
    }
    missing = [name for name in REQUIRED_SYMBOLS if name not in exported]
    if missing:
        raise ValueError("seeded engine is missing symbols: %s" % ", ".join(missing))


def verify_seeded_engine_linux(output_dir: str | Path) -> dict[str, Any]:
    output = Path(output_dir).resolve()
    manifest_path = output / "engine_build_manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="ascii"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("could not read seeded engine manifest") from error
    if (
        not isinstance(manifest, dict)
        or manifest.get("schema_version") != SCHEMA_VERSION
        or manifest.get("manifest_sha256") != _self_hash(manifest)
    ):
        raise ValueError("seeded engine manifest self-hash mismatch")
    cg = output / "cg"
    _verify_hashes(cg, manifest["output_files_sha256"], "seeded engine output")
    forbidden = [
        path for path in output.rglob("*")
        if path.is_file() and path.suffix.lower() in {".h", ".cpp", ".cc", ".cxx"}
    ]
    if forbidden:
        raise ValueError("competition source leaked into engine output")
    if platform.system() == "Linux":
        _verify_symbols(cg / "libcg.so")
    return {
        "verified": True,
        "manifest_sha256": manifest["manifest_sha256"],
        "binary_sha256": manifest["output_files_sha256"]["libcg.so"],
        "output_dir": str(output),
    }


def build_seeded_engine_linux(
    engine_source_dir: str | Path,
    wrapper_source_dir: str | Path,
    output_dir: str | Path,
    *,
    compiler: str = "g++",
) -> dict[str, Any]:
    if platform.system() != "Linux":
        raise RuntimeError("seeded Linux engine builds must run on Linux")
    engine_source = Path(engine_source_dir).resolve()
    wrapper_source = Path(wrapper_source_dir).resolve()
    output = Path(output_dir).resolve()
    if (output / "engine_build_manifest.json").is_file():
        return verify_seeded_engine_linux(output)
    if output.exists() and any(output.iterdir()):
        raise FileExistsError("refusing to populate non-empty engine output: %s" % output)
    _verify_hashes(engine_source, OFFICIAL_ENGINE_HASHES, "official engine")
    _verify_hashes(wrapper_source, OFFICIAL_WRAPPER_HASHES, "official wrapper")
    source_binding = _source_tree_binding(engine_source)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="ptcg_seeded_engine_", dir=output.parent) as directory:
        temporary = Path(directory)
        build_source = temporary / "source"
        staged_output = temporary / "output"
        staged_cg = staged_output / "cg"
        shutil.copytree(engine_source, build_source)
        staged_cg.mkdir(parents=True)
        for name in OFFICIAL_WRAPPER_HASHES:
            shutil.copy2(wrapper_source / name, staged_cg / name)
        for name, patcher in ENGINE_PATCHERS.items():
            _patch_file(build_source / name, patcher, PATCHED_ENGINE_HASHES[name])
        for name, patcher in WRAPPER_PATCHERS.items():
            _patch_file(staged_cg / name, patcher, PATCHED_WRAPPER_HASHES[name])
        command = [
            compiler, "-std=c++20", "-O2", "-DNDEBUG", "-fPIC", "-shared",
            "Export.cpp", "-o", str(staged_cg / "libcg.so"),
        ]
        completed = subprocess.run(
            command, cwd=build_source, check=False, capture_output=True, text=True,
        )
        if completed.returncode != 0:
            raise RuntimeError("seeded engine build failed:\n%s" % completed.stderr[-4000:])
        _verify_symbols(staged_cg / "libcg.so")
        compiler_version = subprocess.run(
            [compiler, "--version"], check=True, capture_output=True, text=True,
        ).stdout.splitlines()[0]
        output_hashes = {
            name: file_sha256(staged_cg / name)
            for name in sorted((*PATCHED_WRAPPER_HASHES, "libcg.so"))
        }
        if {name: output_hashes[name] for name in PATCHED_WRAPPER_HASHES} != PATCHED_WRAPPER_HASHES:
            raise ValueError("patched Python wrapper hashes changed")
        manifest = {
            "schema_version": SCHEMA_VERSION,
            "official_engine_inputs_sha256": dict(sorted(OFFICIAL_ENGINE_HASHES.items())),
            "official_wrapper_inputs_sha256": dict(sorted(OFFICIAL_WRAPPER_HASHES.items())),
            "official_engine_source_tree_sha256": canonical_sha256(source_binding),
            "patched_engine_files_sha256": dict(sorted(PATCHED_ENGINE_HASHES.items())),
            "output_files_sha256": output_hashes,
            "required_symbols": list(REQUIRED_SYMBOLS),
            "compiler": compiler_version,
            "compile_command": [
                compiler, "-std=c++20", "-O2", "-DNDEBUG", "-fPIC", "-shared",
                "Export.cpp", "-o", "cg/libcg.so",
            ],
            "platform": platform.platform(),
            "source_retained": False,
        }
        manifest["manifest_sha256"] = _self_hash(manifest)
        (staged_output / "engine_build_manifest.json").write_text(
            json.dumps(manifest, sort_keys=True, ensure_ascii=True, indent=2) + "\n",
            encoding="ascii", newline="\n",
        )
        if output.exists():
            output.rmdir()
        os.replace(staged_output, output)
    return verify_seeded_engine_linux(output)
