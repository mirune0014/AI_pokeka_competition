from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
import sys
import unittest
from contextlib import contextmanager
from pathlib import Path


CANDIDATE = Path(__file__).resolve().parent
REPOSITORY = CANDIDATE.parents[2]
PARENT = (
    CANDIDATE.parent
    / "alakazam_parent_end_strict_prize_lead_retreat_ko_bridge_v3"
)
ENGINE = (
    REPOSITORY
    / "analysis_outputs/cynthia_v9_vs_v11_poffin_role_selection_20260713"
    / "seeded_engine"
)
if str(ENGINE) not in sys.path:
    sys.path.insert(0, str(ENGINE))
if str(REPOSITORY) not in sys.path:
    sys.path.insert(0, str(REPOSITORY))

from rl_ptcg.label_replay_rollout import replay_decisions  # noqa: E402


POSITIVE = {
    "path": REPOSITORY
    / "autonomous_gold_20260715/live/54802782/refresh_20260718_1805"
    / "replays/episode_86657890_replay.json",
    "sha256": "E4B18E0A357195BB35F8272A012AA7C48128D3FBDC40FCA18848B494A48FBABF",
    "seat": 0,
    "step": 133,
    "parent": [0, 1, 2, 3, 4],
    "candidate": [0, 1, 2, 3, 5],
}

NEGATIVES = (
    (
        REPOSITORY
        / "autonomous_gold_20260715/live/54802782/refresh_20260719_0048"
        / "increment_replays/replays/episode_86676249_replay.json",
        "3EFE24B75D2F519D579D046DC19D6655B42C7B8E89D41CE2EA6A02A18140B12D",
        1,
        39,
        [0, 1, 2, 3],
    ),
    (
        REPOSITORY
        / "autonomous_gold_20260715/live/54802782/refresh_20260719_0048"
        / "increment_replays/replays/episode_86674048_replay.json",
        "6CBA3B3AD397EDE0F78E07CBAAA5CC997E9545515B6A4397FCF88003383DE137",
        0,
        24,
        [0, 1, 2, 3, 4],
    ),
    (
        REPOSITORY
        / "autonomous_gold_20260715/live/54802782/refresh_20260719_0048"
        / "increment_replays/replays/episode_86666507_replay.json",
        "17D8A116CDF58F819CFD264AD8D70A889F5FF4E926C3347CE441E68426CD6867",
        0,
        108,
        list(range(14)),
    ),
    (
        REPOSITORY
        / "autonomous_gold_20260715/live/54802782/refresh_20260719_0048"
        / "increment_replays/replays/episode_86665439_replay.json",
        "0DF33550EBE6CEA7EB103F66CFE019A0DDE91C7EED52786891362B6E52204ABF",
        1,
        67,
        list(range(10)),
    ),
    (
        REPOSITORY
        / "autonomous_gold_20260715/live/54802782/refresh_20260719_0048"
        / "increment_replays/replays/episode_86665439_replay.json",
        "0DF33550EBE6CEA7EB103F66CFE019A0DDE91C7EED52786891362B6E52204ABF",
        1,
        137,
        [0, 1, 2, 3],
    ),
    (
        REPOSITORY
        / "autonomous_gold_20260715/live/54802782/refresh_20260718_1808"
        / "replays/episode_86660075_replay.json",
        "642C89293F08A052C5656F25AB7BD19C6CA05C4589EF74C41883DD473E4D8FF3",
        1,
        119,
        list(range(14)),
    ),
    (
        POSITIVE["path"],
        POSITIVE["sha256"],
        0,
        97,
        list(range(12)),
    ),
    (
        REPOSITORY
        / "autonomous_gold_20260715/live/54802782/refresh_20260718_1744"
        / "replays/episode_86656277_replay.json",
        "233CCD92BD5D44A4A9B1521B19AFBBBB0962ED23E358711EC1FD93AA77251BC4",
        0,
        56,
        [0, 1, 2, 3, 4],
    ),
    (
        REPOSITORY
        / "autonomous_gold_20260715/live/54802782/refresh_20260718_1744"
        / "replays/episode_86656277_replay.json",
        "233CCD92BD5D44A4A9B1521B19AFBBBB0962ED23E358711EC1FD93AA77251BC4",
        0,
        101,
        [0, 1],
    ),
)


@contextmanager
def pushd(path: Path):
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


def load_module(name: str, path: Path, *, cwd: Path):
    with pushd(cwd):
        spec = importlib.util.spec_from_file_location(name, path)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        return module


def call(module, observation: dict) -> list[int]:
    with pushd(CANDIDATE):
        return module.agent(copy.deepcopy(observation))


def frozen_observation(path: Path, seat: int, replay_step: int) -> dict:
    replay = json.loads(path.read_text(encoding="utf-8"))
    matches = [
        copy.deepcopy(observation)
        for step, observation, _ in replay_decisions(replay, seat)
        if step == replay_step
    ]
    assert len(matches) == 1
    return matches[0]


def retained_fingerprints(
    observation: dict, action: list[int]
) -> tuple[tuple[int, int], ...]:
    state = observation["current"]
    mine = state["players"][state["yourIndex"]]
    options = observation["select"]["option"]
    discarded_hand_indices = {options[index]["index"] for index in action}
    return tuple(
        (card["id"], card["serial"])
        for index, card in enumerate(mine["hand"])
        if index not in discarded_hand_indices
    )


class CandidateTestCase(unittest.TestCase):
    def load_candidate(self, suffix: str):
        return load_module(
            f"xerosic_single_swap_candidate_{suffix}",
            CANDIDATE / "main.py",
            cwd=CANDIDATE,
        )

    def load_parent(self, suffix: str):
        return load_module(
            f"xerosic_single_swap_parent_{suffix}",
            PARENT / "main.py",
            cwd=PARENT,
        )

    def assert_fails_closed(self, observation: dict, suffix: str) -> None:
        candidate = self.load_candidate(f"fail_{suffix}")
        parent = self.load_parent(f"fail_{suffix}")
        parent_action = call(parent, observation)
        typed = candidate.to_observation_class(copy.deepcopy(observation))
        self.assertIsNone(
            candidate._xerosic_immediate_ko_successor_single_swap(
                typed, parent_action
            )
        )
        self.assertEqual(call(candidate, observation), parent_action)


class ExactReplayTests(CandidateTestCase):
    def test_positive_is_exactly_one_swap_with_retained_serials(self) -> None:
        self.assertEqual(
            hashlib.sha256(POSITIVE["path"].read_bytes()).hexdigest().upper(),
            POSITIVE["sha256"],
        )
        observation = frozen_observation(
            POSITIVE["path"], POSITIVE["seat"], POSITIVE["step"]
        )
        parent = self.load_parent("positive")
        candidate = self.load_candidate("positive")
        parent_action = call(parent, observation)
        candidate_action = call(candidate, observation)
        self.assertEqual(parent_action, POSITIVE["parent"])
        self.assertEqual(candidate_action, POSITIVE["candidate"])
        self.assertEqual(set(parent_action) - set(candidate_action), {4})
        self.assertEqual(set(candidate_action) - set(parent_action), {5})
        self.assertEqual(
            retained_fingerprints(observation, parent_action),
            ((1079, 31), (66, 18), (5, 57)),
        )
        self.assertEqual(
            retained_fingerprints(observation, candidate_action),
            ((743, 11), (66, 18), (5, 57)),
        )

    def test_repeated_callback_caches_only_the_repaired_action(self) -> None:
        observation = frozen_observation(
            POSITIVE["path"], POSITIVE["seat"], POSITIVE["step"]
        )
        candidate = self.load_candidate("repeat")
        first = call(candidate, observation)
        first_latches = tuple(
            dict(latch)
            for latch in (
                candidate._hilda_source_latch,
                candidate._enriching_reserve_latch,
                candidate._fez_ko_bridge_latch,
                candidate._active_psychic_ko_latch,
                candidate._stranded_retreat_ko_latch,
            )
        )
        second = call(candidate, observation)
        self.assertEqual(first, POSITIVE["candidate"])
        self.assertEqual(second, POSITIVE["candidate"])
        self.assertEqual(candidate._last_decision_action, tuple(POSITIVE["candidate"]))
        self.assertEqual(
            candidate._exact_v3_parent_action(copy.deepcopy(observation)),
            POSITIVE["candidate"],
        )
        self.assertEqual(
            first_latches,
            tuple(
                dict(latch)
                for latch in (
                    candidate._hilda_source_latch,
                    candidate._enriching_reserve_latch,
                    candidate._fez_ko_bridge_latch,
                    candidate._active_psychic_ko_latch,
                    candidate._stranded_retreat_ko_latch,
                )
            ),
        )

    def test_option_order_invariance_retains_the_same_serials(self) -> None:
        observation = frozen_observation(
            POSITIVE["path"], POSITIVE["seat"], POSITIVE["step"]
        )
        observation["select"]["option"] = list(
            reversed(observation["select"]["option"])
        )
        parent = self.load_parent("reordered")
        candidate = self.load_candidate("reordered")
        parent_action = call(parent, observation)
        candidate_action = call(candidate, observation)
        parent_retained = set(retained_fingerprints(observation, parent_action))
        candidate_retained = set(
            retained_fingerprints(observation, candidate_action)
        )
        retained_candy = {
            fingerprint
            for fingerprint in parent_retained
            if fingerprint[0] == 1079
        }
        self.assertEqual(len(retained_candy), 1)
        self.assertEqual(
            candidate_retained,
            (parent_retained - retained_candy) | {(743, 11)},
        )
        self.assertEqual(len(set(parent_action) - set(candidate_action)), 1)
        self.assertEqual(len(set(candidate_action) - set(parent_action)), 1)

    def test_all_nine_frozen_negatives_are_exact_parent(self) -> None:
        for case_index, (path, digest, seat, step, expected) in enumerate(
            NEGATIVES
        ):
            with self.subTest(episode=path.name, step=step):
                self.assertEqual(
                    hashlib.sha256(path.read_bytes()).hexdigest().upper(),
                    digest,
                )
                observation = frozen_observation(path, seat, step)
                parent = self.load_parent(f"negative_{case_index}")
                candidate = self.load_candidate(f"negative_{case_index}")
                parent_action = call(parent, observation)
                self.assertEqual(parent_action, expected)
                self.assertEqual(call(candidate, observation), parent_action)


class CertificateBoundaryTests(CandidateTestCase):
    def setUp(self) -> None:
        self.base = frozen_observation(
            POSITIVE["path"], POSITIVE["seat"], POSITIVE["step"]
        )

    def test_opponent_not_ko_capable_and_energy_unpaid_fail_closed(self) -> None:
        weak = copy.deepcopy(self.base)
        weak["current"]["players"][1]["handCount"] = 6
        self.assert_fails_closed(weak, "not_ko")

        unpaid = copy.deepcopy(self.base)
        opponent = unpaid["current"]["players"][1]["active"][0]
        opponent["energies"] = []
        opponent["energyCards"] = []
        self.assert_fails_closed(unpaid, "unpaid")

    def test_status_and_ambiguous_visible_modifier_fail_closed(self) -> None:
        asleep = copy.deepcopy(self.base)
        asleep["current"]["players"][1]["asleep"] = True
        self.assert_fails_closed(asleep, "status")

        mist = copy.deepcopy(self.base)
        target = mist["current"]["players"][0]["active"][0]
        target["energies"].append(0)
        target["energyCards"].append(
            {"id": 11, "serial": 901, "playerIndex": 0}
        )
        self.assert_fails_closed(mist, "modifier")

    def test_new_or_multiple_kadabra_and_ready_alakazam_fail_closed(self) -> None:
        newly_evolved = copy.deepcopy(self.base)
        newly_evolved["current"]["players"][0]["bench"][0][
            "appearThisTurn"
        ] = True
        self.assert_fails_closed(newly_evolved, "new_kadabra")

        multiple = copy.deepcopy(self.base)
        successor = copy.deepcopy(
            multiple["current"]["players"][0]["bench"][0]
        )
        successor["serial"] = 902
        successor["preEvolution"][0]["serial"] = 903
        successor["energyCards"][0]["serial"] = 904
        multiple["current"]["players"][0]["bench"].append(successor)
        self.assert_fails_closed(multiple, "multiple_kadabra")

        ready = copy.deepcopy(self.base)
        ready_alakazam = copy.deepcopy(
            ready["current"]["players"][0]["active"][0]
        )
        ready_alakazam["serial"] = 905
        ready_alakazam["preEvolution"] = [
            {"id": 741, "serial": 906, "playerIndex": 0},
            {"id": 742, "serial": 907, "playerIndex": 0},
        ]
        ready_alakazam["energyCards"] = [
            {"id": 19, "serial": 908, "playerIndex": 0}
        ]
        ready_alakazam["energies"] = [5]
        ready_alakazam["tools"] = []
        ready["current"]["players"][0]["bench"].append(ready_alakazam)
        self.assert_fails_closed(ready, "ready_alakazam")

    def test_live_rare_candy_target_in_either_branch_fails_closed(self) -> None:
        live_abra = copy.deepcopy(self.base)
        live_abra["current"]["players"][0]["bench"].append(
            {
                "appearThisTurn": False,
                "energies": [],
                "energyCards": [],
                "hp": 50,
                "id": 741,
                "maxHp": 50,
                "playerIndex": 0,
                "preEvolution": [],
                "serial": 909,
                "tools": [],
            }
        )
        self.assert_fails_closed(live_abra, "live_abra")

    def test_multiple_swap_candidates_and_victims_fail_closed(self) -> None:
        multiple_alakazam = copy.deepcopy(self.base)
        multiple_alakazam["current"]["players"][0]["hand"][0]["id"] = 743
        self.assert_fails_closed(multiple_alakazam, "multiple_alakazam")

        multiple_candy = copy.deepcopy(self.base)
        multiple_candy["current"]["players"][0]["hand"][6]["id"] = 1079
        self.assert_fails_closed(multiple_candy, "multiple_candy")

    def test_malformed_callback_certificates_fail_closed(self) -> None:
        mutations = []
        wrong_context = copy.deepcopy(self.base)
        wrong_context["select"]["context"] = 7
        mutations.append(wrong_context)
        wrong_effect = copy.deepcopy(self.base)
        wrong_effect["select"]["effect"]["id"] = 1231
        mutations.append(wrong_effect)
        wrong_owner = copy.deepcopy(self.base)
        wrong_owner["select"]["effect"]["playerIndex"] = 0
        mutations.append(wrong_owner)
        nonpositive_effect = copy.deepcopy(self.base)
        nonpositive_effect["select"]["effect"]["serial"] = 0
        mutations.append(nonpositive_effect)
        wrong_hand_count = copy.deepcopy(self.base)
        wrong_hand_count["current"]["players"][0]["handCount"] += 1
        mutations.append(wrong_hand_count)
        wrong_count = copy.deepcopy(self.base)
        wrong_count["select"]["minCount"] = 4
        mutations.append(wrong_count)
        missing_option = copy.deepcopy(self.base)
        missing_option["select"]["option"].pop()
        mutations.append(missing_option)
        duplicate_mapping = copy.deepcopy(self.base)
        duplicate_mapping["select"]["option"][1]["index"] = 0
        mutations.append(duplicate_mapping)
        for index, observation in enumerate(mutations):
            with self.subTest(index=index):
                self.assert_fails_closed(observation, f"malformed_{index}")


class ImportParityTests(CandidateTestCase):
    def test_source_runtime_import_parity_and_initial_deck(self) -> None:
        observation = frozen_observation(
            POSITIVE["path"], POSITIVE["seat"], POSITIVE["step"]
        )
        source = self.load_candidate("source_parity")
        runtime = load_module(
            "xerosic_single_swap_runtime_parity",
            CANDIDATE / "runtime/main.py",
            cwd=CANDIDATE / "runtime",
        )
        self.assertEqual(call(source, observation), POSITIVE["candidate"])
        self.assertEqual(call(runtime, observation), POSITIVE["candidate"])

        initial = copy.deepcopy(observation)
        initial["select"] = None
        source_deck = call(source, initial)
        runtime_deck = call(runtime, initial)
        self.assertEqual(source_deck, runtime_deck)
        self.assertEqual(len(source_deck), 60)


if __name__ == "__main__":
    unittest.main(verbosity=2)
