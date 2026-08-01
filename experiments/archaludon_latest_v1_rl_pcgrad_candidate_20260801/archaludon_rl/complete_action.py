"""Complete legal-action candidates and permutation-invariant set scoring.

The game engine consumes one ``list[int]`` per decision.  A candidate in this
module is that complete list, not one option inside it.  Unordered selections
are canonicalized by semantic option identity; each equivalence class keeps a
deterministic engine-valid representative.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from itertools import combinations, permutations
import json
from typing import Any, Mapping, Sequence

import torch

from .public_state import enum_int, get_field
from .semantic_action import semantic_options, validate_engine_action


COMPLETE_ACTION_SCHEMA_VERSION = "complete-legal-action-candidate-v1"
SET_POOLING_MODE = "sum_of_selected_option_embeddings"

# SKILL_ORDER is explicitly ordered by the public API.  TO_DECK and
# TO_DECK_BOTTOM are conservatively kept ordered because the destination order
# can be observable.  Other multi-select contexts in the current data are
# set-valued selections.
ORDER_SENSITIVE_CONTEXTS = frozenset({9, 10, 34})


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _option_identity(option: Mapping[str, Any]) -> str:
    identity = option.get("identity")
    if isinstance(identity, str) and identity:
        return identity
    payload = option.get("payload")
    if not isinstance(payload, Mapping):
        raise ValueError("semantic option payload is missing")
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _selected_payload(option: Mapping[str, Any]) -> dict[str, Any]:
    engine_index = option.get("engine_index")
    if not isinstance(engine_index, int) or isinstance(engine_index, bool):
        raise ValueError("semantic option engine_index must be a plain int")
    execution = option.get("execution_payload")
    semantic = option.get("payload")
    if not isinstance(semantic, Mapping):
        raise ValueError("semantic option payload is missing")
    return {
        "engine_index": engine_index,
        "semantic_identity": _option_identity(option),
        "semantic_payload": dict(semantic),
        "execution_payload": (
            dict(execution)
            if isinstance(execution, Mapping)
            else {
                "engine_index": engine_index,
                "semantic_payload": dict(semantic),
            }
        ),
    }


def _action_identity(
    options: Sequence[Mapping[str, Any]],
    action: Sequence[int],
    *,
    order_sensitive: bool,
) -> str:
    identities = [_option_identity(options[index]) for index in action]
    if not order_sensitive:
        identities.sort()
    payload = {
        "order_sensitive": bool(order_sensitive),
        "selected_semantic_option_identities": identities,
    }
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class CompleteActionCandidate:
    """One complete engine action and its full recorded payload."""

    candidate_index: int
    action: tuple[int, ...]
    canonical_identity: str
    selected_options: tuple[dict[str, Any], ...]
    order_sensitive: bool

    @property
    def selection_count(self) -> int:
        return len(self.action)


@dataclass(frozen=True)
class CompleteActionSet:
    candidates: tuple[CompleteActionCandidate, ...]
    option_count: int
    minimum: int
    maximum: int
    context: int | None
    order_sensitive: bool
    raw_candidate_count: int
    duplicate_canonical_action_count: int

    def candidate_index_for(
        self,
        options: Sequence[Mapping[str, Any]],
        action: Sequence[int],
    ) -> int | None:
        if len(set(action)) != len(action):
            return None
        if not self.minimum <= len(action) <= self.maximum:
            return None
        if any(
            not isinstance(index, int)
            or isinstance(index, bool)
            or index < 0
            or index >= self.option_count
            for index in action
        ):
            return None
        identity = _action_identity(
            options,
            action,
            order_sensitive=self.order_sensitive,
        )
        for candidate in self.candidates:
            if candidate.canonical_identity == identity:
                return candidate.candidate_index
        return None


def enumerate_complete_actions(
    options: Sequence[Mapping[str, Any]],
    *,
    minimum: int,
    maximum: int,
    context: int | None,
    legal_option_mask: Sequence[bool] | None = None,
) -> CompleteActionSet:
    """Enumerate every legal complete selection and remove semantic duplicates."""

    if (
        not isinstance(minimum, int)
        or isinstance(minimum, bool)
        or not isinstance(maximum, int)
        or isinstance(maximum, bool)
        or not 0 <= minimum <= maximum
    ):
        raise ValueError("invalid complete-action selection bounds")
    option_count = len(options)
    mask = (
        tuple(bool(value) for value in legal_option_mask)
        if legal_option_mask is not None
        else tuple(True for _ in options)
    )
    if len(mask) != option_count:
        raise ValueError("complete-action legal mask length mismatch")
    eligible = tuple(index for index, allowed in enumerate(mask) if allowed)
    if maximum > len(eligible):
        raise ValueError("selection maximum exceeds legal option count")
    order_sensitive = context in ORDER_SENSITIVE_CONTEXTS
    unique: dict[str, tuple[int, ...]] = {}
    raw_count = 0
    for count in range(minimum, maximum + 1):
        iterator = (
            permutations(eligible, count)
            if order_sensitive and count > 1
            else combinations(eligible, count)
        )
        for raw_action in iterator:
            action = tuple(raw_action)
            raw_count += 1
            identity = _action_identity(
                options,
                action,
                order_sensitive=order_sensitive,
            )
            unique.setdefault(identity, action)
    if not unique:
        raise ValueError("complete-action surface has no legal candidate")
    candidates = tuple(
        CompleteActionCandidate(
            candidate_index=index,
            action=action,
            canonical_identity=identity,
            selected_options=tuple(_selected_payload(options[value]) for value in action),
            order_sensitive=order_sensitive,
        )
        for index, (identity, action) in enumerate(unique.items())
    )
    return CompleteActionSet(
        candidates=candidates,
        option_count=option_count,
        minimum=minimum,
        maximum=maximum,
        context=context,
        order_sensitive=order_sensitive,
        raw_candidate_count=raw_count,
        duplicate_canonical_action_count=raw_count - len(candidates),
    )


def recorded_complete_actions(decision: Mapping[str, Any]) -> CompleteActionSet:
    projection = decision.get("public_projection") or {}
    select = projection.get("select") or {}
    options = decision.get("legal_semantic_options") or ()
    return enumerate_complete_actions(
        options,
        minimum=int(select["min_count"]),
        maximum=int(select["max_count"]),
        context=(None if select.get("context") is None else int(select["context"])),
        legal_option_mask=decision.get("legal_option_mask"),
    )


def observation_complete_actions(observation: Any) -> CompleteActionSet:
    """Build candidates directly from a live observation, including raw payload."""

    select = get_field(observation, "select")
    if select is None:
        raise ValueError("deck requests are not option-selection action candidates")
    raw_options = list(get_field(select, "option", ()) or ())
    semantic = semantic_options(observation)
    option_rows: list[dict[str, Any]] = []
    for raw, option in zip(raw_options, semantic):
        execution_fields = {
            name: enum_int(get_field(raw, name))
            for name in ("index", "number", "area", "playerIndex", "toolIndex", "energyIndex", "count", "inPlayArea", "inPlayIndex", "attackId", "cardId", "specialConditionType")
        }
        option_rows.append(
            {
                "engine_index": option.engine_index,
                "identity": option.identity,
                "payload": option.identity_payload,
                "execution_payload": {
                    "engine_index": option.engine_index,
                    "option_type": option.option_type,
                    "fields": execution_fields,
                    "source_card_id": option.source_card_id,
                    "target_card_id": option.target_card_id,
                },
            }
        )
    result = enumerate_complete_actions(
        option_rows,
        minimum=int(enum_int(get_field(select, "minCount"))),
        maximum=int(enum_int(get_field(select, "maxCount"))),
        context=enum_int(get_field(select, "context")),
    )
    for candidate in result.candidates:
        validate_engine_action(observation, list(candidate.action))
    return result


def candidate_membership_tensor(
    candidates: CompleteActionSet,
    *,
    device: torch.device | str,
    dtype: torch.dtype,
) -> torch.Tensor:
    membership = torch.zeros(
        (len(candidates.candidates), candidates.option_count),
        device=device,
        dtype=dtype,
    )
    for row, candidate in enumerate(candidates.candidates):
        if candidate.action:
            membership[row, list(candidate.action)] = 1.0
    return membership


def complete_action_logits(
    model: Any,
    state_vector: torch.Tensor,
    option_vectors: torch.Tensor,
    candidates: CompleteActionSet,
) -> torch.Tensor:
    """Score complete actions with DeepSets-style sum pooling over options."""

    if state_vector.ndim != 1 or option_vectors.ndim != 2:
        raise ValueError("complete-action scorer expects state [S], options [O,D]")
    if option_vectors.shape[0] != candidates.option_count:
        raise ValueError("complete-action option tensor/count mismatch")
    state_hidden = model.state_encoder(state_vector.unsqueeze(0)).squeeze(0)
    option_hidden = model.action_encoder(option_vectors)
    membership = candidate_membership_tensor(
        candidates,
        device=option_hidden.device,
        dtype=option_hidden.dtype,
    )
    pooled = membership @ option_hidden
    expanded_state = state_hidden.unsqueeze(0).expand(pooled.shape[0], -1)
    logits = model.residual_head(torch.cat((expanded_state, pooled), dim=-1)).squeeze(-1)
    if logits.ndim != 1 or logits.shape[0] != len(candidates.candidates):
        raise AssertionError("complete-action scorer output shape drift")
    if not bool(torch.isfinite(logits).all()):
        raise ValueError("complete-action actor logits are non-finite")
    return logits


def estimated_inference_tensor_bytes(
    model: Any,
    candidates: CompleteActionSet,
    *,
    bytes_per_float: int = 4,
) -> int:
    """Conservative live-tensor estimate for one float32 decision forward."""

    hidden = int(model.config.hidden_dim)
    state_dim = int(model.config.state_dim)
    action_dim = int(model.config.action_dim)
    option_count = int(candidates.option_count)
    candidate_count = len(candidates.candidates)
    float_count = (
        state_dim
        + option_count * action_dim
        + candidate_count * option_count  # membership
        + hidden  # state hidden
        + option_count * hidden
        + candidate_count * hidden  # pooled
        + candidate_count * hidden * 2  # concatenation
        + candidate_count * hidden  # residual-head hidden
        + candidate_count  # logits
        + candidate_count  # softmax probabilities
    )
    return float_count * bytes_per_float

