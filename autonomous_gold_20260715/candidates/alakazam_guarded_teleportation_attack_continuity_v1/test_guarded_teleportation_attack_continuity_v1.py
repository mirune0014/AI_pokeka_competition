from __future__ import annotations

import ast
import copy
import difflib
import hashlib
import importlib.util
import json
import os
import random
import sys
import unittest
from contextlib import contextmanager
from pathlib import Path


CANDIDATE = Path(__file__).resolve().parent
ROOT = CANDIDATE.parents[2]
AUTONOMOUS = ROOT / "autonomous_gold_20260715"
PARENT = (
    AUTONOMOUS
    / "candidates/alakazam_parent_end_strict_prize_lead_retreat_ko_bridge_v3"
)
ENGINE = (
    ROOT
    / "analysis_outputs/cynthia_v9_vs_v11_poffin_role_selection_20260713"
    / "seeded_engine"
)
RAW = (
    AUTONOMOUS
    / "evaluations/alakazam_public_net_deck_delta_prize_clock_v1"
    / "fixed_phase0_20260719/raw/baseline_primary"
)
DECISION = (
    AUTONOMOUS
    / "decisions/20260719_1100_public_net_clock_reject_and_guarded_teleport_select.md"
)
LIVE_REPLAY = (
    AUTONOMOUS
    / "live/54802782/refresh_20260719_0838/replays/86774226.json"
)

sys.path.insert(0, str(ENGINE))
from cg.api import AreaType, CardType, OptionType, SelectContext, all_card_data
from cg.game import battle_finish, battle_select, battle_start


PARENT_HASHES = {
    "main.py": "49E954F53E043CD79D928DFB2340CCB5D85A17F33CCB824C871CCE153C0C9C95",
    "runtime/main.py": "9CA7A415451B84343165EF8A5CDC0D67BBF1B4969A13C984C09B142B4898CD9A",
    "deck.csv": "7B413177E5077777F2178143839C0155B03B92BBC8B3A6607621A7D43F351141",
}
DECISION_SHA256 = "FC0397EB673103F095650537C788385B38AB105CBD054F864B0AA593D196B9C7"
LIVE_REPLAY_SHA256 = "CCE322201C6C9525A80EAAE1390030A98717E29DB2A8E9BA78F88F02624A01B1"

OPPONENTS = {
    "historical_silver": AUTONOMOUS
    / "baseline/historical_silver_archaludon_54495224",
    "mega_lucario": ROOT / "meta_agents/mega_lucario_public_simple",
    "dragapult": ROOT / "meta_agents/dragapult_lumen_live_85038765_simple",
    "marnie_sota": ROOT / "meta_agents/marnie_sota_live_85033057_simple",
    "great_tusk": ROOT / "meta_agents/great_tusk_crustle_public",
    "kangaskhan_crustle": ROOT
    / "meta_agents/kangaskhan_crustle_mpgaming_v0_exact_simple",
    "alakazam_oselcoun": ROOT
    / "meta_agents/alakazam_oselcoun_live_85035844_simple",
    "alakazam_rmy": ROOT / "meta_agents/alakazam_rmy_live_85082271_simple",
}

CASES = (
    ("fresh_general", "great_tusk", "p0", 2026101802, 42, "attack_negative"),
    ("fresh_general", "kangaskhan_crustle", "p1", 2026101804, 31, "play_dead_end"),
    ("known_target", "alakazam_oselcoun", "p0", 2026071600, 25, "positive"),
    ("known_target", "alakazam_rmy", "p0", 2026071600, 24, "positive"),
    ("known_target", "dragapult", "p0", 2026071593, 95, "attack_negative"),
    ("known_target", "dragapult", "p0", 2026071600, 30, "positive"),
    ("known_target", "historical_silver", "p1", 2026071599, 56, "positive"),
    ("known_target", "kangaskhan_crustle", "p0", 2026071599, 27, "attack_negative"),
    ("known_target", "marnie_sota", "p0", 2026071599, 25, "attack_negative"),
    ("known_target", "marnie_sota", "p0", 2026071600, 29, "play_dead_end"),
    ("known_target", "mega_lucario", "p0", 2026071593, 44, "positive"),
    ("known_target", "mega_lucario", "p0", 2026071600, 28, "positive"),
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def read_deck(path: Path) -> list[int]:
    return [int(row) for row in path.read_text(encoding="utf-8").splitlines() if row]


@contextmanager
def cwd(path: Path):
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


_module_counter = 0


def load_module(path: Path, *, runtime: bool = False):
    global _module_counter
    _module_counter += 1
    source = path / "runtime/main.py" if runtime else path / "main.py"
    spec = importlib.util.spec_from_file_location(
        f"guarded_teleport_test_{_module_counter}", source
    )
    if spec is None or spec.loader is None:
        raise ImportError(source)
    module = importlib.util.module_from_spec(spec)
    with cwd(path):
        spec.loader.exec_module(module)
    return module


def selected_option(observation: dict, action: list[int]) -> dict:
    return observation["select"]["option"][action[0]]


def compact_option(option: dict) -> dict:
    keys = (
        "type",
        "area",
        "index",
        "playerIndex",
        "cardId",
        "attackId",
        "inPlayArea",
        "inPlayIndex",
        "inPlayPlayerIndex",
        "targetArea",
        "targetIndex",
        "targetPlayerIndex",
        "energyIndex",
        "toolIndex",
        "number",
    )
    return {key: option.get(key) for key in keys if key in option}


def trace_path(block: str, opponent: str, seat: str, seed: int) -> Path:
    return (
        RAW
        / block
        / opponent
        / seat
        / f"seed_{seed}"
        / "traces/game_0000.jsonl"
    )


def trace_rows(block: str, opponent: str, seat: str, seed: int) -> list[dict]:
    return [
        json.loads(row)
        for row in trace_path(block, opponent, seat, seed)
        .read_text(encoding="utf-8")
        .splitlines()
    ]


def reconstruct_to_step(case, *, module=None):
    block, opponent, seat, seed, target_step, _ = case
    policy_index = 0 if seat == "p0" else 1
    rows = trace_rows(block, opponent, seat, seed)
    target_row = rows[target_step]
    assert target_row["step"] == target_step
    assert target_row["player"] == policy_index
    policy_deck = read_deck(PARENT / "deck.csv")
    opponent_deck = read_deck(OPPONENTS[opponent] / "deck.csv")
    deck_a, deck_b = (
        (policy_deck, opponent_deck)
        if policy_index == 0
        else (opponent_deck, policy_deck)
    )
    random.seed(seed)
    observation, start_data = battle_start(deck_a, deck_b, seed=seed)
    if not observation:
        raise AssertionError(
            f"battle_start failed {case}: {start_data.errorPlayer}/{start_data.errorType}"
        )
    try:
        for step, frozen in enumerate(rows):
            if step > target_step:
                break
            current = observation["current"]
            select = observation["select"]
            assert current["yourIndex"] == frozen["player"]
            assert int(select["context"]) == frozen["context"]
            actual_options = [
                compact_option(option) for option in select["option"]
            ]
            assert actual_options == frozen["options"], (
                case,
                step,
                actual_options,
                frozen["options"],
            )
            if step == target_step:
                action = module.agent(copy.deepcopy(observation)) if module else None
                return copy.deepcopy(observation), action, frozen
            if module is not None and current["yourIndex"] == policy_index:
                assert module.agent(copy.deepcopy(observation)) == frozen["action"]
            observation = battle_select(frozen["action"])
        raise AssertionError(f"target step not reached: {case}")
    except Exception:
        battle_finish()
        raise


def finish_reconstruction() -> None:
    battle_finish()


def pokemon_for_switch_option(observation: dict, action: list[int]) -> dict:
    option = selected_option(observation, action)
    mine = observation["current"]["players"][
        observation["current"]["yourIndex"]
    ]
    return mine["bench"][option["index"]]


class IdentityAndPrefixTests(unittest.TestCase):
    def test_hashes_compile_ast_import_and_legal_byte_identical_deck(self) -> None:
        self.assertEqual(DECISION.stat().st_size, 7474)
        self.assertEqual(sha256(DECISION), DECISION_SHA256)
        for relative, expected in PARENT_HASHES.items():
            self.assertEqual(sha256(PARENT / relative), expected)
        self.assertEqual(
            (CANDIDATE / "deck.csv").read_bytes(),
            (PARENT / "deck.csv").read_bytes(),
        )
        source = (CANDIDATE / "main.py").read_text(encoding="utf-8")
        runtime = (CANDIDATE / "runtime/main.py").read_text(encoding="utf-8")
        compile(source, str(CANDIDATE / "main.py"), "exec")
        compile(runtime, str(CANDIDATE / "runtime/main.py"), "exec")
        ast.parse(source)
        ast.parse(runtime)
        self.assertEqual(len(load_module(CANDIDATE).my_deck), 60)
        self.assertTrue(callable(load_module(CANDIDATE, runtime=True).agent))

        deck = read_deck(CANDIDATE / "deck.csv")
        self.assertEqual(len(deck), 60)
        cards = {card.cardId: card for card in all_card_data()}
        self.assertTrue(all(card_id in cards for card_id in deck))
        self.assertEqual(sum(cards[card_id].aceSpec for card_id in deck), 1)
        counts = {card_id: deck.count(card_id) for card_id in set(deck)}
        self.assertTrue(
            all(
                count <= 4
                or cards[card_id].cardType == CardType.BASIC_ENERGY
                for card_id, count in counts.items()
            )
        )

    def test_exact_parent_normalized_policy_prefix_and_scoring_body(self) -> None:
        parent = (PARENT / "main.py").read_text(encoding="utf-8")
        candidate = (CANDIDATE / "main.py").read_text(encoding="utf-8")
        normalized_diff = list(
            difflib.ndiff(parent.splitlines(), candidate.splitlines())
        )
        self.assertFalse(any(row.startswith("- ") for row in normalized_diff))
        parent_agent = parent[parent.index("def agent(obs_dict: dict)") :]
        candidate_agent = candidate[candidate.index("def agent(obs_dict: dict)") :]
        prefix_end = "    op_active_hp = op_active.hp if op_active else 9999\n"
        self.assertEqual(
            parent_agent[: parent_agent.index(prefix_end) + len(prefix_end)],
            candidate_agent[: candidate_agent.index(prefix_end) + len(prefix_end)],
        )
        scoring_start = "    had_stranded_retreat_latch = bool(_stranded_retreat_ko_latch)\n"
        scoring_end = "    chosen_action = desc_indices[:select.maxCount]\n"
        parent_scoring = parent_agent[
            parent_agent.index(scoring_start) : parent_agent.index(scoring_end)
            + len(scoring_end)
        ]
        candidate_scoring = candidate_agent[
            candidate_agent.index(scoring_start) : candidate_agent.index(scoring_end)
            + len(scoring_end)
        ]
        self.assertEqual(parent_scoring, candidate_scoring)

    def test_specialization_scan_excludes_rejected_rule_families(self) -> None:
        source = (CANDIDATE / "main.py").read_text(encoding="utf-8")
        parent = (PARENT / "main.py").read_text(encoding="utf-8")
        additions = "\n".join(
            row[2:]
            for row in difflib.ndiff(parent.splitlines(), source.splitlines())
            if row.startswith("+ ")
        )
        for rejected in (
            "public_net",
            "xerosic",
            "reserve_clock",
            "stage_up",
            "deck_delta",
        ):
            self.assertNotIn(rejected, additions.lower())


class CensusTests(unittest.TestCase):
    def test_all_twelve_frozen_census_callbacks(self) -> None:
        seen = []
        for case in CASES:
            with self.subTest(case=case):
                module = load_module(CANDIDATE)
                observation, action, frozen = reconstruct_to_step(
                    case, module=module
                )
                try:
                    frozen_option = frozen["options"][frozen["action"][0]]
                    self.assertEqual(frozen_option["type"], int(OptionType.RETREAT))
                    self.assertTrue(
                        any(
                            option.get("type") == int(OptionType.ATTACK)
                            and option.get("attackId") == module.ATTACK_TELEPORTATION
                            for option in frozen["options"]
                        )
                    )
                    selected = selected_option(observation, action)
                    if case[-1] == "positive":
                        self.assertEqual(selected["type"], int(OptionType.ATTACK))
                        self.assertEqual(
                            selected["attackId"], module.ATTACK_TELEPORTATION
                        )
                        self.assertEqual(module._guarded_teleportation_latch["target_id"], module.Kadabra)
                        target = observation["current"]["players"][
                            observation["current"]["yourIndex"]
                        ]["bench"][module._guarded_teleportation_latch["target_index"]]
                        self.assertEqual(target["serial"], module._guarded_teleportation_latch["target_serial"])
                        self.assertEqual(target["energyCards"], [])
                        self.assertEqual(module._guarded_teleportation_latch["target_score"], 30)
                    else:
                        self.assertEqual(action, frozen["action"])
                        self.assertEqual(selected["type"], int(OptionType.RETREAT))
                        self.assertFalse(module._guarded_teleportation_latch)
                    seen.append((case[1], case[2], case[3], case[4], case[-1]))
                finally:
                    finish_reconstruction()
        self.assertEqual(len(seen), 12)
        self.assertEqual(sum(row[-1] == "positive" for row in seen), 6)
        self.assertEqual(sum(row[-1] == "attack_negative" for row in seen), 4)
        self.assertEqual(sum(row[-1] == "play_dead_end" for row in seen), 2)

    def test_live_86774226_control_if_full_observation_is_present(self) -> None:
        self.assertTrue(LIVE_REPLAY.is_file())
        self.assertEqual(sha256(LIVE_REPLAY), LIVE_REPLAY_SHA256)
        replay = json.loads(LIVE_REPLAY.read_text(encoding="utf-8"))
        controls = []
        for step_index, step in enumerate(replay["steps"]):
            for row in step:
                observation = row.get("observation") or {}
                select = observation.get("select") or {}
                options = select.get("option") or []
                if (
                    row.get("status") == "ACTIVE"
                    and options
                    and any(
                        option.get("type") == int(OptionType.RETREAT)
                        for option in options
                    )
                    and any(
                        option.get("type") == int(OptionType.ATTACK)
                        and option.get("attackId") == 1070
                        for option in options
                    )
                ):
                    parent_action = load_module(PARENT).agent(
                        copy.deepcopy(observation)
                    )
                    if (
                        len(parent_action) == 1
                        and selected_option(observation, parent_action)["type"]
                        == int(OptionType.RETREAT)
                    ):
                        controls.append(
                            (step_index, copy.deepcopy(observation), parent_action)
                        )
        self.assertEqual(len(controls), 1)
        step_index, observation, parent_action = controls[0]
        candidate_action = load_module(CANDIDATE).agent(copy.deepcopy(observation))
        self.assertEqual(selected_option(observation, parent_action)["type"], int(OptionType.RETREAT))
        self.assertEqual(selected_option(observation, candidate_action)["type"], int(OptionType.ATTACK))
        self.assertGreater(step_index, 0)


class FocusedFailClosedTests(unittest.TestCase):
    POSITIVE_CASE = CASES[5]

    def observation(self) -> dict:
        observation, _, _ = reconstruct_to_step(self.POSITIVE_CASE)
        finish_reconstruction()
        return observation

    def assert_parent_exact(self, observation: dict) -> None:
        candidate = load_module(CANDIDATE)
        parent = load_module(PARENT)
        self.assertEqual(
            candidate.agent(copy.deepcopy(observation)),
            parent.agent(copy.deepcopy(observation)),
        )
        self.assertFalse(candidate._guarded_teleportation_latch)

    def test_tied_prediction_ready_target_and_no_bench_fail_closed(self) -> None:
        tied = self.observation()
        mine = tied["current"]["players"][0]
        duplicate = mine["bench"][2]
        duplicate.update(id=742, hp=80, maxHp=80, energies=[], energyCards=[])
        self.assert_parent_exact(tied)

        ready = self.observation()
        target = ready["current"]["players"][0]["bench"][1]
        target["energies"] = [5]
        target["energyCards"] = [
            {"id": 5, "serial": 999901, "playerIndex": 0}
        ]
        self.assert_parent_exact(ready)

        no_bench = self.observation()
        no_bench["current"]["players"][0]["bench"] = []
        self.assert_parent_exact(no_bench)

    def test_forceably_ready_and_other_main_continuation_compute_parent_first(self) -> None:
        forceable = self.observation()
        mine = forceable["current"]["players"][0]
        mine["hand"].append(
            {"id": 5, "serial": 999902, "playerIndex": 0}
        )
        mine["handCount"] += 1
        forceable["current"]["energyAttached"] = False
        forceable["select"]["option"].insert(
            0,
            {
                "type": int(OptionType.ATTACH),
                "area": int(AreaType.HAND),
                "index": len(mine["hand"]) - 1,
                "playerIndex": 0,
                "inPlayArea": int(AreaType.BENCH),
                "inPlayIndex": 1,
            },
        )
        self.assert_parent_exact(forceable)

        continuation = self.observation()
        continuation["select"]["option"].insert(
            0,
            {
                "type": int(OptionType.ABILITY),
                "area": int(AreaType.BENCH),
                "index": 2,
            },
        )
        self.assert_parent_exact(continuation)

    def test_non_abra_illegal_attack_status_and_unknown_effect_fail_closed(self) -> None:
        non_abra = self.observation()
        active = non_abra["current"]["players"][0]["active"][0]
        active.update(id=305, hp=70, maxHp=70)
        self.assert_parent_exact(non_abra)

        illegal_attack = self.observation()
        illegal_attack["select"]["option"] = [
            option
            for option in illegal_attack["select"]["option"]
            if option.get("attackId") != 1070
        ]
        self.assert_parent_exact(illegal_attack)

        status = self.observation()
        status["current"]["players"][0]["confused"] = True
        self.assert_parent_exact(status)

        unknown = self.observation()
        unknown["current"]["players"][1]["active"][0]["tools"].append(
            {"id": 999999, "serial": 999903, "playerIndex": 1}
        )
        self.assert_parent_exact(unknown)

        retaliation = self.observation()
        retaliation["current"]["players"][1]["active"][0]["tools"].append(
            {"id": 1167, "serial": 999904, "playerIndex": 1}
        )
        self.assert_parent_exact(retaliation)

    def test_unexpected_main_callback_clears_marks_and_delegates(self) -> None:
        observation = self.observation()
        candidate = load_module(CANDIDATE)
        first = candidate.agent(copy.deepcopy(observation))
        self.assertEqual(selected_option(observation, first)["attackId"], 1070)
        unexpected = copy.deepcopy(observation)
        unexpected["current"]["turnActionCount"] += 1
        candidate_action = candidate.agent(copy.deepcopy(unexpected))
        parent_action = load_module(PARENT).agent(copy.deepcopy(unexpected))
        self.assertEqual(candidate_action, parent_action)
        self.assertFalse(candidate._guarded_teleportation_latch)
        self.assertEqual(
            candidate._guarded_teleportation_semantic_failure["reason"],
            "unexpected_or_stale_switch",
        )


class TransactionAndDeterminismTests(unittest.TestCase):
    POSITIVE_CASE = CASES[5]

    def test_complete_checked_attack_to_recorded_switch(self) -> None:
        module = load_module(CANDIDATE)
        observation, attack_action, _ = reconstruct_to_step(
            self.POSITIVE_CASE, module=module
        )
        try:
            target_serial = module._guarded_teleportation_latch["target_serial"]
            target_index = module._guarded_teleportation_latch["target_index"]
            self.assertEqual(selected_option(observation, attack_action)["attackId"], 1070)
            switch_observation = battle_select(attack_action)
            self.assertEqual(
                switch_observation["select"]["context"], int(SelectContext.SWITCH)
            )
            switch_action = module.agent(copy.deepcopy(switch_observation))
            chosen = pokemon_for_switch_option(switch_observation, switch_action)
            self.assertEqual(chosen["serial"], target_serial)
            self.assertEqual(chosen["id"], module.Kadabra)
            self.assertEqual(
                selected_option(switch_observation, switch_action)["index"],
                target_index,
            )
            self.assertFalse(module._guarded_teleportation_latch)
            after_switch = battle_select(switch_action)
            mine = after_switch["current"]["players"][0]
            self.assertEqual(mine["active"][0]["serial"], target_serial)
        finally:
            finish_reconstruction()

    def test_option_order_and_repeated_callback_determinism(self) -> None:
        observation, _, _ = reconstruct_to_step(self.POSITIVE_CASE)
        finish_reconstruction()

        module = load_module(CANDIDATE)
        first = module.agent(copy.deepcopy(observation))
        self.assertEqual(module.agent(copy.deepcopy(observation)), first)
        self.assertEqual(selected_option(observation, first)["attackId"], 1070)

        reordered = copy.deepcopy(observation)
        reordered["select"]["option"].reverse()
        reordered_module = load_module(CANDIDATE)
        reordered_action = reordered_module.agent(reordered)
        self.assertEqual(selected_option(reordered, reordered_action)["attackId"], 1070)
        self.assertEqual(
            reordered_module._guarded_teleportation_latch["target_serial"],
            module._guarded_teleportation_latch["target_serial"],
        )

    def test_switch_option_order_and_repeated_callback_determinism(self) -> None:
        module = load_module(CANDIDATE)
        observation, attack_action, _ = reconstruct_to_step(
            self.POSITIVE_CASE, module=module
        )
        try:
            target_serial = module._guarded_teleportation_latch["target_serial"]
            switch_observation = battle_select(attack_action)
            switch_observation["select"]["option"].reverse()
            first = module.agent(copy.deepcopy(switch_observation))
            chosen = pokemon_for_switch_option(switch_observation, first)
            self.assertEqual(chosen["serial"], target_serial)
            self.assertEqual(module.agent(copy.deepcopy(switch_observation)), first)
        finally:
            finish_reconstruction()

    def test_stale_switch_clears_marks_and_delegates_exact_parent(self) -> None:
        module = load_module(CANDIDATE)
        observation, attack_action, _ = reconstruct_to_step(
            self.POSITIVE_CASE, module=module
        )
        try:
            target_serial = module._guarded_teleportation_latch["target_serial"]
            switch_observation = battle_select(attack_action)
            mine = switch_observation["current"]["players"][
                switch_observation["current"]["yourIndex"]
            ]
            target_index = next(
                index
                for index, pokemon in enumerate(mine["bench"])
                if pokemon["serial"] == target_serial
            )
            switch_observation["select"]["option"] = [
                option
                for option in switch_observation["select"]["option"]
                if option["index"] != target_index
            ]
            candidate_action = module.agent(copy.deepcopy(switch_observation))
            parent_action = load_module(PARENT).agent(copy.deepcopy(switch_observation))
            self.assertEqual(candidate_action, parent_action)
            self.assertFalse(module._guarded_teleportation_latch)
            self.assertEqual(
                module._guarded_teleportation_semantic_failure["reason"],
                "recorded_target_unavailable",
            )
        finally:
            finish_reconstruction()

    def test_source_runtime_parity(self) -> None:
        observation, _, _ = reconstruct_to_step(self.POSITIVE_CASE)
        source = load_module(CANDIDATE)
        runtime = load_module(CANDIDATE, runtime=True)
        try:
            left = source.agent(copy.deepcopy(observation))
            right = runtime.agent(copy.deepcopy(observation))
            self.assertEqual(left, right)
            self.assertEqual(selected_option(observation, left)["attackId"], 1070)
            switch_observation = battle_select(left)
            left_switch = source.agent(copy.deepcopy(switch_observation))
            right_switch = runtime.agent(copy.deepcopy(switch_observation))
            self.assertEqual(left_switch, right_switch)
            self.assertEqual(
                pokemon_for_switch_option(switch_observation, left_switch)["id"],
                source.Kadabra,
            )
        finally:
            finish_reconstruction()


if __name__ == "__main__":
    unittest.main(verbosity=2)
