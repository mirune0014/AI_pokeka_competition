from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
import unittest
from pathlib import Path


CANDIDATE = Path(__file__).resolve().parent
REPOSITORY = CANDIDATE.parents[2]
PARENT = (
    CANDIDATE.parent
    / "alakazam_parent_end_strict_prize_lead_retreat_ko_bridge_v3"
)
ANCHORS = (
    (
        REPOSITORY
        / "archaludon/live/54802782/refresh_20260718_1805"
        / "replays/episode_86657890_replay.json",
        133,
        "E4B18E0A357195BB35F8272A012AA7C48128D3FBDC40FCA18848B494A48FBABF",
        [0, 2, 3, 5, 7],
        ((1225, 50), (743, 11), (66, 18)),
        ((1079, 31), (66, 18), (5, 57)),
    ),
    (
        REPOSITORY
        / "archaludon/live/54802782/refresh_20260719_0048"
        / "increment_replays/replays/episode_86666507_replay.json",
        108,
        "17D8A116CDF58F819CFD264AD8D70A889F5FF4E926C3347CE441E68426CD6867",
        [0, 1, 2, 3, 4, 5, 8, 9, 10, 12, 13, 14, 15, 16],
        ((66, 17), (1231, 46), (19, 61)),
        ((1079, 33), (1079, 32), (305, 16)),
    ),
)

os.chdir(CANDIDATE)
import main as candidate  # noqa: E402


def load_module(name: str, path: Path):
    previous = Path.cwd()
    try:
        os.chdir(CANDIDATE)
        spec = importlib.util.spec_from_file_location(name, path)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        os.chdir(previous)


def active_observation(path: Path, observation_step: int) -> dict:
    replay = json.loads(path.read_text(encoding="utf-8"))
    matches = [
        record["observation"]
        for step in replay["steps"]
        for record in step
        if record.get("status") == "ACTIVE"
        and record.get("observation", {}).get("step") == observation_step
    ]
    assert len(matches) == 1
    return copy.deepcopy(matches[0])


def selected_retained_fingerprints(observation: dict, action: list[int]) -> tuple:
    select = observation["select"]
    mine = observation["current"]["players"][observation["current"]["yourIndex"]]
    discarded_hand_indices = {
        select["option"][option_index]["index"] for option_index in action
    }
    return tuple(
        (card["id"], card["serial"])
        for hand_index, card in enumerate(mine["hand"])
        if hand_index not in discarded_hand_indices
    )


def rank_for_fingerprints(observation: dict, fingerprints: tuple) -> tuple:
    typed = candidate.to_observation_class(observation)
    mine = typed.current.players[typed.current.yourIndex]
    wanted = set(fingerprints)
    retained = tuple(
        card for card in mine.hand if (card.id, card.serial) in wanted
    )
    assert len(retained) == 3
    return candidate._xerosic_retained_triple_rank(typed, retained)


class ExactReplayAnchorTests(unittest.TestCase):
    def setUp(self) -> None:
        candidate._clear_emergency_state(clear_cache=True)
        candidate.pre_turn = 0
        candidate.ability_used_dudunsparce = False
        candidate.ability_used_fezandipiti = False

    def test_exact_anchors_actions_retained_triples_and_rank_gain(self) -> None:
        for path, step, digest, expected_action, expected_retained, parent_retained in ANCHORS:
            with self.subTest(episode=path.name, step=step):
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest().upper(), digest)
                observation = active_observation(path, step)
                action = candidate.agent(copy.deepcopy(observation))
                self.assertEqual(action, expected_action)
                self.assertEqual(
                    selected_retained_fingerprints(observation, action),
                    expected_retained,
                )
                self.assertGreater(
                    rank_for_fingerprints(observation, expected_retained),
                    rank_for_fingerprints(observation, parent_retained),
                )
                self.assertEqual(
                    len(action), observation["select"]["maxCount"]
                )
                self.assertEqual(len(set(action)), len(action))
                self.assertTrue(all(
                    0 <= index < len(observation["select"]["option"])
                    for index in action
                ))

    def test_exact_anchors_are_deterministic_and_differ_from_parent(self) -> None:
        for case_index, (path, step, _, expected_action, expected_retained, _) in enumerate(ANCHORS):
            with self.subTest(episode=path.name, step=step):
                observation = active_observation(path, step)
                first = candidate.agent(copy.deepcopy(observation))
                second = candidate.agent(copy.deepcopy(observation))
                self.assertEqual(first, second)
                self.assertEqual(first, expected_action)

                parent = load_module(f"parent_anchor_{case_index}", PARENT / "main.py")
                parent_action = parent.agent(copy.deepcopy(observation))
                self.assertNotEqual(first, parent_action)
                self.assertEqual(
                    selected_retained_fingerprints(observation, first),
                    expected_retained,
                )

    def test_option_order_permutation_keeps_exact_card_serials(self) -> None:
        for path, step, _, _, expected_retained, _ in ANCHORS:
            with self.subTest(episode=path.name, step=step):
                observation = active_observation(path, step)
                observation["select"]["option"] = list(
                    reversed(observation["select"]["option"])
                )
                candidate._clear_emergency_state(clear_cache=True)
                action = candidate.agent(copy.deepcopy(observation))
                self.assertEqual(
                    selected_retained_fingerprints(observation, action),
                    expected_retained,
                )


class CertificationBoundaryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.base = active_observation(ANCHORS[0][0], ANCHORS[0][1])

    def helper(self, observation: dict):
        return candidate._xerosic_certified_retained_triple(
            candidate.to_observation_class(observation)
        )

    def test_wrong_effect_fails_closed(self) -> None:
        observation = copy.deepcopy(self.base)
        observation["select"]["effect"]["id"] = candidate.Dawn
        self.assertIsNone(self.helper(observation))

    def test_non_discard_context_fails_closed(self) -> None:
        observation = copy.deepcopy(self.base)
        observation["select"]["context"] = int(candidate.SelectContext.TO_HAND)
        self.assertIsNone(self.helper(observation))

    def test_non_own_hand_and_malformed_mapping_fail_closed(self) -> None:
        mutations = []
        wrong_owner = copy.deepcopy(self.base)
        wrong_owner["select"]["option"][0]["playerIndex"] = 1
        mutations.append(wrong_owner)
        wrong_area = copy.deepcopy(self.base)
        wrong_area["select"]["option"][0]["area"] = int(candidate.AreaType.DECK)
        mutations.append(wrong_area)
        duplicate = copy.deepcopy(self.base)
        duplicate["select"]["option"][1]["index"] = 0
        mutations.append(duplicate)
        missing = copy.deepcopy(self.base)
        missing["select"]["option"].pop()
        mutations.append(missing)
        duplicate_serial = copy.deepcopy(self.base)
        duplicate_serial["current"]["players"][0]["hand"][1]["serial"] = (
            duplicate_serial["current"]["players"][0]["hand"][0]["serial"]
        )
        mutations.append(duplicate_serial)
        for index, observation in enumerate(mutations):
            with self.subTest(mutation=index):
                self.assertIsNone(self.helper(observation))

    def test_wrong_discard_count_or_not_exact_three_fails_closed(self) -> None:
        unequal = copy.deepcopy(self.base)
        unequal["select"]["minCount"] -= 1
        self.assertIsNone(self.helper(unequal))
        retains_four = copy.deepcopy(self.base)
        retains_four["select"]["minCount"] -= 1
        retains_four["select"]["maxCount"] -= 1
        self.assertIsNone(self.helper(retains_four))

    def test_unsafe_deck_does_not_certify_dudunsparce_draw_role(self) -> None:
        observation = copy.deepcopy(self.base)
        observation["current"]["players"][0]["deckCount"] = 4
        typed = candidate.to_observation_class(observation)
        retained = tuple(
            card for card in typed.current.players[0].hand
            if (card.id, card.serial) in {(1225, 50), (743, 11), (66, 18)}
        )
        rank = candidate._xerosic_retained_triple_rank(typed, retained)
        self.assertEqual(rank[3], 0)

    def test_absent_visible_evolution_route_removes_alakazam_bonus(self) -> None:
        observation = copy.deepcopy(self.base)
        mine = observation["current"]["players"][0]
        mine["bench"] = [pokemon for pokemon in mine["bench"] if pokemon["id"] != candidate.Kadabra]
        typed = candidate.to_observation_class(observation)
        retained = tuple(
            card for card in typed.current.players[0].hand
            if (card.id, card.serial) in {(1225, 50), (743, 11), (66, 18)}
        )
        rank = candidate._xerosic_retained_triple_rank(typed, retained)
        self.assertEqual(rank[1], 0)
        self.assertEqual(rank[2], 0)


class ParentEquivalenceTests(unittest.TestCase):
    def test_actual_replay_corpus_is_parent_equal_outside_exact_xerosic(self) -> None:
        corpus = []
        for path, target, *_ in ANCHORS:
            replay = json.loads(path.read_text(encoding="utf-8"))
            for step in replay["steps"]:
                for record in step:
                    observation = record.get("observation")
                    if record.get("status") != "ACTIVE" or observation is None:
                        continue
                    if observation.get("step") == target:
                        continue
                    corpus.append(copy.deepcopy(observation))
                    if len(corpus) >= 24:
                        break
                if len(corpus) >= 24:
                    break
            if len(corpus) >= 24:
                break
        self.assertEqual(len(corpus), 24)

        for index, observation in enumerate(corpus):
            with self.subTest(index=index, step=observation.get("step")):
                candidate_module = load_module(
                    f"candidate_equivalence_{index}", CANDIDATE / "main.py"
                )
                parent_module = load_module(
                    f"parent_equivalence_{index}", PARENT / "main.py"
                )
                self.assertEqual(
                    candidate_module.agent(copy.deepcopy(observation)),
                    parent_module.agent(copy.deepcopy(observation)),
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)
