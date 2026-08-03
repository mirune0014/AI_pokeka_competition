from __future__ import annotations

import os
from pathlib import Path
import sys
import types
import unittest

from archaludon_rl.frozen_sources import (
    ENGINE_RUNTIME_MANIFEST_SHA256,
    LATEST_RECEIPTS,
    find_repo_root,
    latest_source_dir,
    seeded_engine_dir,
    sha256_file,
    verify_frozen_sources,
)
from archaludon_rl.catalog import catalog_from_cg
from archaludon_rl.effect_features import (
    FeatureStatus,
    extract_effect_features,
)
from archaludon_rl.public_state import project_public_state
from archaludon_rl.semantic_action import semantic_options, validate_engine_action
from archaludon_rl.teacher_adapter import LatestV1Teacher

from .helpers import observation


class FakeTeacherModule:
    def __init__(self):
        self.calls = 0
        self.pending = []

    def agent(self, obs):
        self.calls += 1
        self.pending.append({"callback": self.calls, "precedence_reason": "fake"})
        return [0]

    def drain_cumulative_telemetry(self):
        rows = list(self.pending)
        self.pending.clear()
        return rows


class SourceAndTeacherTests(unittest.TestCase):
    def test_frozen_receipts_and_deck_count(self):
        verified = verify_frozen_sources()
        self.assertEqual(
            verified["engine_runtime_manifest_sha256"],
            ENGINE_RUNTIME_MANIFEST_SHA256,
        )
        repo = find_repo_root()
        for receipt in LATEST_RECEIPTS:
            self.assertEqual(sha256_file(repo / receipt.relative_path), receipt.sha256)
        deck = [
            int(line)
            for line in (latest_source_dir() / "deck.csv").read_text().splitlines()
            if line.strip()
        ]
        self.assertEqual(len(deck), 60)

    def test_fake_teacher_exactly_once_stateful_and_restores_cwd(self):
        fake = FakeTeacherModule()
        before = Path.cwd()
        teacher = LatestV1Teacher(
            game_id="fake",
            seat=0,
            source_dir=latest_source_dir(),
            module=fake,
            verify_sources=False,
        )
        first = teacher.decide(observation())
        second = teacher.decide(observation())
        self.assertEqual(fake.calls, 2)
        self.assertEqual(teacher.call_count, 2)
        self.assertEqual(first.call_count, 1)
        self.assertEqual(first.telemetry[0]["callback"], 1)
        self.assertEqual(second.telemetry[0]["callback"], 2)
        self.assertEqual(Path.cwd(), before)

    def test_action_validation_rejects_bool_duplicate_range_and_count(self):
        obs = observation()
        for action in ([True], [0, 0], [2], []):
            with self.assertRaises((TypeError, ValueError), msg=repr(action)):
                validate_engine_action(obs, action)
        self.assertEqual(validate_engine_action(obs, [1]), [1])

    def test_actual_latest_load_deck_request_smoke(self):
        engine = seeded_engine_dir()
        sys.path.insert(0, str(engine))
        try:
            __import__("cg.api")
            teacher = LatestV1Teacher(game_id="actual-smoke", seat=None)
            result = teacher.decide(
                {
                    "select": None,
                    "logs": [],
                    "current": None,
                    "search_begin_input": "opaque",
                }
            )
            self.assertEqual(len(result.action), 60)
            self.assertEqual(result.telemetry[-1]["precedence_reason"], "rank0_deck_request_reset")
            self.assertTrue(teacher.engine_module_receipt["path"].endswith("cg\\api.py"))
        finally:
            if sys.path and sys.path[0] == str(engine):
                sys.path.pop(0)

    def test_checked_engine_catalog_is_conservative(self):
        engine = seeded_engine_dir()
        sys.path.insert(0, str(engine))
        try:
            from cg import api

            catalog = catalog_from_cg(api)
            cards = {int(card.cardId): card for card in api.all_card_data()}
            attacks = {
                int(attack.attackId): attack for attack in api.all_attack()
            }
            skill_card_id = next(
                card_id
                for card_id, card in cards.items()
                if tuple(card.skills or ())
            )
            text_attack_id = next(
                attack_id
                for attack_id, attack in attacks.items()
                if str(attack.text or "").strip()
            )
            basic_card_id = next(
                card_id
                for card_id, card in cards.items()
                if bool(card.basic) and int(card.cardType) == 0
            )
            self.assertFalse(
                catalog.cards[skill_card_id].damage_modifiers_known
            )
            self.assertEqual(
                catalog.attacks[text_attack_id].damage_kind,
                "unknown",
            )
            self.assertIsNone(catalog.attacks[text_attack_id].bench_damage)
            self.assertIsNone(
                catalog.attacks[text_attack_id].deterministic_energy_delta
            )
            self.assertEqual(
                catalog.cards[basic_card_id].board_bench_delta,
                1,
            )
        finally:
            if sys.path and sys.path[0] == str(engine):
                sys.path.pop(0)

    def test_basic_169_bench_delta_applies_to_play_not_attack_223(self):
        engine = seeded_engine_dir()
        sys.path.insert(0, str(engine))
        try:
            from cg import api

            catalog = catalog_from_cg(api)
            attack_obs = observation(
                options=[
                    {"type": 13, "attackId": 223},
                    {"type": 14},
                ]
            )
            attack_obs["current"]["players"][0]["active"][0]["id"] = 169
            attack_projection = project_public_state(attack_obs)
            attack_option = semantic_options(attack_obs)[0]
            attack_effects = extract_effect_features(
                attack_projection,
                attack_option,
                catalog,
            )
            self.assertFalse(
                attack_effects.fields["board_bench_delta"].status
                is FeatureStatus.KNOWN
                and attack_effects.fields["board_bench_delta"].value == 1
            )

            play_obs = observation(
                options=[
                    {"type": 7, "index": 0},
                    {"type": 14},
                ]
            )
            play_obs["current"]["players"][0]["hand"][0]["id"] = 169
            play_projection = project_public_state(play_obs)
            play_option = semantic_options(play_obs)[0]
            play_effects = extract_effect_features(
                play_projection,
                play_option,
                catalog,
            )
            self.assertEqual(
                play_effects.fields["board_bench_delta"].status,
                FeatureStatus.KNOWN,
            )
            self.assertEqual(
                play_effects.fields["board_bench_delta"].value,
                1,
            )
        finally:
            if sys.path and sys.path[0] == str(engine):
                sys.path.pop(0)


if __name__ == "__main__":
    unittest.main()
