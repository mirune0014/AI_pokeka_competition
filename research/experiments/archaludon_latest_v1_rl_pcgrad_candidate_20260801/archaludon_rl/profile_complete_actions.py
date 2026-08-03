"""Read-only representability and practicality gate for complete actions."""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import statistics
import time
from typing import Any, Mapping, Sequence

import torch

from .complete_action import (
    COMPLETE_ACTION_SCHEMA_VERSION,
    SET_POOLING_MODE,
    complete_action_logits,
    estimated_inference_tensor_bytes,
    recorded_complete_actions,
)
from .model import load_checkpoint, sha256_checkpoint


PROFILE_SCHEMA_VERSION = "complete-action-existing-data-gate-v1"


def _nearest_rank(values: Sequence[float | int], fraction: float) -> float:
    if not values:
        raise ValueError("percentile requires at least one value")
    ordered = sorted(float(value) for value in values)
    index = max(0, math.ceil(fraction * len(ordered)) - 1)
    return ordered[index]


def _distribution(values: Sequence[float | int]) -> dict[str, float]:
    if not values:
        raise ValueError("distribution requires at least one value")
    return {
        "median": float(statistics.median(values)),
        "p95": _nearest_rank(values, 0.95),
        "p99": _nearest_rank(values, 0.99),
        "maximum": float(max(values)),
    }


def _episode_paths(directory: Path) -> list[Path]:
    paths = sorted(directory.glob("*.json"))
    if not paths:
        raise ValueError("episode directory has no JSON files")
    return paths


def profile(
    *,
    episodes_dir: Path,
    checkpoint_path: Path,
    max_candidates: int,
    p99_candidates: int,
    p99_generation_ms: float,
    max_variable_tensor_mib: float,
) -> dict[str, Any]:
    torch.set_num_threads(1)
    model, _, _ = load_checkpoint(checkpoint_path, device="cpu")
    model.eval()
    model_parameter_bytes = sum(
        parameter.numel() * parameter.element_size()
        for parameter in model.parameters()
    )
    episodes = [json.loads(path.read_text(encoding="utf-8")) for path in _episode_paths(episodes_dir)]
    rows = [decision for episode in episodes for decision in episode.get("decisions") or ()]
    if not rows:
        raise ValueError("existing episode data has no decisions")

    candidate_counts: list[int] = []
    raw_candidate_counts: list[int] = []
    generation_ms: list[float] = []
    inference_ms: list[float] = []
    variable_tensor_bytes: list[int] = []
    representable = 0
    exact_representative = 0
    optional_surfaces = 0
    optional_empty_teacher = 0
    multiple_teacher = 0
    optional_or_multiple = 0
    duplicate_total = 0
    duplicate_rows = 0
    order_sensitive_rows = 0
    family_counts: Counter[str] = Counter()
    missing: list[dict[str, Any]] = []

    with torch.no_grad():
        for row_index, decision in enumerate(rows):
            select = (decision.get("public_projection") or {}).get("select") or {}
            teacher = tuple(decision.get("teacher_action") or ())
            options = decision.get("legal_semantic_options") or ()
            started = time.perf_counter_ns()
            candidates = recorded_complete_actions(decision)
            generation_ms.append((time.perf_counter_ns() - started) / 1_000_000.0)
            candidate_counts.append(len(candidates.candidates))
            raw_candidate_counts.append(candidates.raw_candidate_count)
            duplicate_total += candidates.duplicate_canonical_action_count
            duplicate_rows += int(candidates.duplicate_canonical_action_count > 0)
            order_sensitive_rows += int(candidates.order_sensitive)
            teacher_index = candidates.candidate_index_for(options, teacher)
            if teacher_index is not None:
                representable += 1
                exact_representative += int(candidates.candidates[teacher_index].action == teacher)
            else:
                missing.append(
                    {
                        "row_index": row_index,
                        "decision_index": decision.get("decision_index"),
                        "teacher_action": list(teacher),
                        "minimum": select.get("min_count"),
                        "maximum": select.get("max_count"),
                        "option_count": len(options),
                    }
                )
            is_optional = int(select.get("min_count", -1)) == 0
            is_multiple = len(teacher) > 1
            optional_surfaces += int(is_optional)
            optional_empty_teacher += int(is_optional and len(teacher) == 0)
            multiple_teacher += int(is_multiple)
            optional_or_multiple += int(is_optional or is_multiple)
            selected_types = sorted(
                {
                    str(options[index]["payload"]["option_type"])
                    for index in teacher
                }
            )
            family_counts["empty" if not selected_types else "+".join(selected_types)] += 1

            state = torch.tensor(decision["state_vector"], dtype=torch.float32)
            action_vectors = torch.tensor(decision["action_vectors"], dtype=torch.float32)
            infer_started = time.perf_counter_ns()
            logits = complete_action_logits(model, state, action_vectors, candidates)
            probabilities = torch.softmax(logits, dim=0)
            if not bool(torch.isfinite(probabilities).all()):
                raise ValueError("complete-action softmax produced non-finite probabilities")
            inference_ms.append((time.perf_counter_ns() - infer_started) / 1_000_000.0)
            variable_tensor_bytes.append(estimated_inference_tensor_bytes(model, candidates))

    row_count = len(rows)
    candidate_distribution = _distribution(candidate_counts)
    generation_distribution = _distribution(generation_ms)
    inference_distribution = _distribution(inference_ms)
    memory_distribution = _distribution(variable_tensor_bytes)
    representability = representable / row_count
    max_variable_mib = max(variable_tensor_bytes) / (1024.0 * 1024.0)
    gates = {
        "teacher_canonical_representability_100_percent": representability == 1.0,
        "maximum_candidate_count_at_most_threshold": max(candidate_counts) <= max_candidates,
        "p99_candidate_count_at_most_threshold": candidate_distribution["p99"] <= p99_candidates,
        "p99_generation_ms_at_most_threshold": generation_distribution["p99"] <= p99_generation_ms,
        "maximum_variable_tensor_mib_at_most_threshold": max_variable_mib <= max_variable_tensor_mib,
    }
    gates["overall_pass"] = all(gates.values())
    return {
        "schema_version": PROFILE_SCHEMA_VERSION,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "passed" if gates["overall_pass"] else "failed",
        "scope": {
            "read_only_existing_data": True,
            "new_rollout_collected": False,
            "bc_training_performed": False,
            "ppo_training_performed": False,
            "state_encoder_changed": False,
            "reward_changed": False,
            "episode_count": len(episodes),
            "decision_count": row_count,
        },
        "action_structure": {
            "schema_version": COMPLETE_ACTION_SCHEMA_VERSION,
            "unit": "one_complete_engine_list_int_action",
            "unordered_canonicalization": "sorted semantic option identity multiset",
            "set_pooling": SET_POOLING_MODE,
            "teacher_fallback_on_missing": False,
            "missing_teacher_action_is_representability_failure": True,
        },
        "inputs": {
            "episodes_dir": str(episodes_dir),
            "checkpoint_path": str(checkpoint_path),
            "checkpoint_sha256": sha256_checkpoint(checkpoint_path),
        },
        "candidate_counts_after_canonical_deduplication": {
            **candidate_distribution,
            "total": sum(candidate_counts),
        },
        "candidate_counts_before_canonical_deduplication": {
            **_distribution(raw_candidate_counts),
            "total": sum(raw_candidate_counts),
        },
        "teacher_representability": {
            "canonical_action_present_count": representable,
            "canonical_action_present_rate": representability,
            "exact_representative_engine_tuple_count": exact_representative,
            "exact_representative_engine_tuple_rate": exact_representative / row_count,
            "representability_failure_count": len(missing),
            "failure_examples": missing[:10],
            "interpretation": "Canonical-equivalent actions are one candidate by design; exact duplicate-card indices and unordered permutations need not equal the retained representative.",
        },
        "teacher_action_surface": {
            "optional_surface_count": optional_surfaces,
            "optional_surface_rate": optional_surfaces / row_count,
            "optional_empty_teacher_action_count": optional_empty_teacher,
            "optional_empty_teacher_action_rate": optional_empty_teacher / row_count,
            "multiple_selection_teacher_action_count": multiple_teacher,
            "multiple_selection_teacher_action_rate": multiple_teacher / row_count,
            "optional_or_multiple_count": optional_or_multiple,
            "optional_or_multiple_rate": optional_or_multiple / row_count,
            "teacher_action_family_counts": dict(sorted(family_counts.items())),
            "order_sensitive_surface_count": order_sensitive_rows,
        },
        "canonical_duplicates": {
            "duplicate_canonical_action_count": duplicate_total,
            "rows_with_duplicate_canonical_actions": duplicate_rows,
            "row_rate": duplicate_rows / row_count,
        },
        "candidate_generation_time_ms": {
            **generation_distribution,
            "total": sum(generation_ms),
        },
        "scorer_inference_time_ms_cpu_single_thread": {
            **inference_distribution,
            "total": sum(inference_ms),
        },
        "inference_memory": {
            "method": "analytical_live_float32_tensor_upper_bound_excluding_python_metadata_and_allocator_cache",
            "model_parameter_bytes": model_parameter_bytes,
            "model_parameter_mib": model_parameter_bytes / (1024.0 * 1024.0),
            "variable_tensor_bytes": memory_distribution,
            "maximum_variable_tensor_mib": max_variable_mib,
            "maximum_model_plus_variable_mib": (model_parameter_bytes + max(variable_tensor_bytes)) / (1024.0 * 1024.0),
        },
        "gate_thresholds": {
            "maximum_candidate_count": max_candidates,
            "p99_candidate_count": p99_candidates,
            "p99_generation_ms": p99_generation_ms,
            "maximum_variable_tensor_mib": max_variable_tensor_mib,
        },
        "gate": gates,
        "next_step": (
            "collect_new_2000_teacher_games"
            if gates["overall_pass"]
            else "stop_before_new_rollout_and_fix_complete_action_representation"
        ),
    }


def markdown(result: Mapping[str, Any]) -> str:
    candidates = result["candidate_counts_after_canonical_deduplication"]
    raw = result["candidate_counts_before_canonical_deduplication"]
    representability = result["teacher_representability"]
    surface = result["teacher_action_surface"]
    timing = result["candidate_generation_time_ms"]
    memory = result["inference_memory"]
    gate = result["gate"]
    return f"""# 完全合法行動候補: 既存データgate

既存{result['scope']['episode_count']} episode・{result['scope']['decision_count']}局面だけを読み取り、完全行動候補の表現可能性と実用性を測定した。新規rollout、BC、PPOは実施していない。

| 指標 | 結果 |
|---|---:|
| 候補数 median / p95 / p99 / max | {candidates['median']:.0f} / {candidates['p95']:.0f} / {candidates['p99']:.0f} / {candidates['maximum']:.0f} |
| canonical化前候補総数 | {raw['total']} |
| canonical化後候補総数 | {candidates['total']} |
| duplicate canonical action | {result['canonical_duplicates']['duplicate_canonical_action_count']} |
| teacher canonical表現可能率 | {representability['canonical_action_present_count']}/{result['scope']['decision_count']} ({representability['canonical_action_present_rate']:.2%}) |
| optional surface | {surface['optional_surface_count']}/{result['scope']['decision_count']} ({surface['optional_surface_rate']:.2%}) |
| multiple teacher action | {surface['multiple_selection_teacher_action_count']}/{result['scope']['decision_count']} ({surface['multiple_selection_teacher_action_rate']:.2%}) |
| optionalまたはmultiple | {surface['optional_or_multiple_count']}/{result['scope']['decision_count']} ({surface['optional_or_multiple_rate']:.2%}) |
| 候補生成 ms median / p95 / p99 / max | {timing['median']:.4f} / {timing['p95']:.4f} / {timing['p99']:.4f} / {timing['maximum']:.4f} |
| 推論可変tensor max | {memory['maximum_variable_tensor_mib']:.3f} MiB |
| model + 可変tensor max | {memory['maximum_model_plus_variable_mib']:.3f} MiB |

## 判定

- gate: **{'PASS' if gate['overall_pass'] else 'FAIL'}**
- unordered multiple selectionはsemantic identityのmultisetとしてcanonical化し、actorは選択option embeddingのsum poolingで完全行動1候補をscoreする。
- teacher actionが候補にない場合はfallbackで隠さずrepresentability failureとして数える。本データでのfailureは{representability['representability_failure_count']}件。
- {'候補数・生成時間・メモリは固定閾値内であり、次は8相手・両席・分散seedの新規2,000 teacher試合へ進める。' if gate['overall_pass'] else '既存データgateが通らないため、新規2,000試合は開始しない。'}
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--episodes-dir", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-md", type=Path, required=True)
    parser.add_argument("--max-candidates", type=int, default=4096)
    parser.add_argument("--p99-candidates", type=int, default=1024)
    parser.add_argument("--p99-generation-ms", type=float, default=10.0)
    parser.add_argument("--max-variable-tensor-mib", type=float, default=64.0)
    args = parser.parse_args()
    result = profile(
        episodes_dir=args.episodes_dir,
        checkpoint_path=args.checkpoint,
        max_candidates=args.max_candidates,
        p99_candidates=args.p99_candidates,
        p99_generation_ms=args.p99_generation_ms,
        max_variable_tensor_mib=args.max_variable_tensor_mib,
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.output_md.write_text(markdown(result), encoding="utf-8")
    print(json.dumps({"status": result["status"], "gate": result["gate"]}, ensure_ascii=False))
    return 0 if result["gate"]["overall_pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
