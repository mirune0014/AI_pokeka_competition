from __future__ import annotations

import csv
import importlib.util
from pathlib import Path
import sys
import unittest
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[2]
CANDIDATE = ROOT / "candidates" / "archaludon_public_prize_race_threat_control_t9_v1"
IMPLEMENTATION = ROOT / "implementation/archaludon_deterministic_public_effect_registry_phase1_v1"
sys.path.insert(0, str(CANDIDATE))
SPEC = importlib.util.spec_from_file_location("dper_phase1", CANDIDATE / "main.py")
main = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(main)


def card(card_id: int, serial: int, player: int = 0) -> dict:
    return {"id": card_id, "serial": serial, "playerIndex": player}


def pokemon(
    card_id: int,
    serial: int,
    *,
    player: int = 0,
    energies: tuple[int, ...] = (),
    energy_ids: tuple[int, ...] | None = None,
    hp: int | None = None,
    max_hp: int | None = None,
    tools: tuple[dict, ...] = (),
    previous: tuple[dict, ...] = (),
    appear: bool = False,
) -> dict:
    data = main.CARD_DB[card_id]
    maximum = int(data.hp) if max_hp is None else max_hp
    ids = energies if energy_ids is None else energy_ids
    assert len(ids) == len(energies)
    return {
        "id": card_id,
        "serial": serial,
        "playerIndex": player,
        "hp": maximum if hp is None else hp,
        "maxHp": maximum,
        "appearThisTurn": appear,
        "energies": list(energies),
        "energyCards": [
            card(card_id_value, serial * 100 + position + 1, player)
            for position, card_id_value in enumerate(ids)
        ],
        "tools": list(tools),
        "preEvolution": list(previous),
    }


def direct_evolution(source_id: int, serial: int = 9000) -> dict:
    source_name = main._dper_normalize(main.CARD_DB[source_id].name)
    data = next(
        row for row in main.CARD_DB.values()
        if main._dper_normalize(getattr(row, "evolvesFrom", None)) == source_name
    )
    return card(data.cardId, serial)


def rare_candy_line() -> tuple[dict, dict]:
    for stage2 in main.CARD_DB.values():
        if not stage2.stage2:
            continue
        stage1 = next(
            (
                row for row in main.CARD_DB.values()
                if row.stage1
                and main._dper_normalize(row.name)
                == main._dper_normalize(stage2.evolvesFrom)
            ),
            None,
        )
        if stage1 is None:
            continue
        basic = next(
            (
                row for row in main.CARD_DB.values()
                if row.basic
                and main._dper_normalize(row.name)
                == main._dper_normalize(stage1.evolvesFrom)
            ),
            None,
        )
        if basic is not None:
            return pokemon(basic.cardId, 9100), card(stage2.cardId, 9101)
    raise AssertionError("no Rare Candy line in catalog")


class RegistryPhase1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.old_attack_id = main._opp_last_attack_id
        self.old_attack_serial = main._opp_last_attack_serial
        main._opp_last_attack_id = None
        main._opp_last_attack_serial = None

    def tearDown(self) -> None:
        main._opp_last_attack_id = self.old_attack_id
        main._opp_last_attack_serial = self.old_attack_serial

    def test_01_manifest_is_34_semantics_37_exact_bindings_and_no_name_only_row(self) -> None:
        status = main._dper_registry_status()
        self.assertEqual(status["effect_count"], 34)
        self.assertEqual(status["binding_count"], 37)
        self.assertTrue(status["all_admitted"])
        self.assertEqual(len(status["handler_types"]), 14)
        for row in main._DPER_BINDINGS:
            self.assertIsInstance(row.card_id, int)
            self.assertIn(row.entry_kind, {"ATTACK", "SKILL"})
            self.assertEqual(len(row.text_hash), 64)
            self.assertTrue(row.consumers)
            self.assertTrue(main._dper_binding_admitted(row))
            self.assertFalse(main._dper_binding_admitted(row._replace(text_hash="0" * 64)))
        with (IMPLEMENTATION / "effect_registry_manifest.csv").open(
            newline="", encoding="utf-8"
        ) as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), 34)
        self.assertEqual({row["effect_id"] for row in rows}, {row.effect_id for row in main._DPER_BINDINGS})
        with (IMPLEMENTATION / "effect_production_reachability_manifest.csv").open(
            newline="", encoding="utf-8"
        ) as handle:
            reachability = list(csv.DictReader(handle))
        self.assertEqual(len(reachability), 34)
        self.assertEqual(
            {row["effect_id"] for row in reachability},
            {row.effect_id for row in main._DPER_BINDINGS},
        )
        self.assertTrue(all(row["call_site"].startswith("main.py:") for row in reachability))
        self.assertTrue(all(row["agent_ownership"].startswith("PCRD_V2_DIRECT_ONCE") for row in reachability))

    def test_02_memory_dive_visible_paid_text_cost_and_hidden_unpaid_locked_negatives(self) -> None:
        prior = card(305, 102)
        source = pokemon(66, 101, energies=(8,), previous=(prior,))
        relicanth = pokemon(57, 103)
        positive = main._dper_memory_dive_access(
            source, {"memory_dive_sources": (relicanth,)}
        )
        self.assertEqual(positive["status"], "EXACT")
        by_id = {
            row["attack_id"]: row
            for row in positive["after"]["attack_certificates"]
        }
        self.assertIn(423, by_id)
        self.assertEqual(by_id[423]["printed_energy_cost"], (0,))
        self.assertIn("switch this pokemon", by_id[423]["normalized_attack_text"])
        hidden = main._dper_memory_dive_access(source, {"memory_dive_sources": ()})
        self.assertNotIn(423, [row[0] for row in hidden["after"]["attack_rows"]])
        unpaid = pokemon(66, 104, previous=(card(305, 105),))
        unpaid_result = main._dper_memory_dive_access(
            unpaid, {"memory_dive_sources": (relicanth,)}
        )
        self.assertNotIn(423, [row[0] for row in unpaid_result["after"]["attack_rows"]])
        locked_source = pokemon(
            678, 106, energies=(6, 6), previous=(card(677, 107),)
        )
        locked = main._dper_memory_dive_access(
            locked_source, {
                "memory_dive_sources": (relicanth,),
                "public_log": {
                    "attacker_serial": 106,
                    "attack_id": 981,
                    "attack_turn": 5,
                    "current_turn": 7,
                },
            }
        )
        self.assertNotIn(981, [row[0] for row in locked["after"]["attack_rows"]])

    def test_03_shadow_bullet_and_flower_curtain_keep_bench_damage_separate_from_reply_routes(self) -> None:
        source = pokemon(648, 201, energies=(7, 7))
        target = pokemon(169, 202)
        normal_bench = pokemon(169, 203, player=1)
        rule_box_bench = pokemon(190, 204, player=1)
        flower = pokemon(343, 205, player=1)
        result = main._dper_combat_oracle(
            source,
            937,
            target,
            {
                "target_bench": (normal_bench, rule_box_bench),
                "target_flower_curtain_sources": (flower,),
            },
        )
        self.assertEqual(result["status"], "EXACT")
        self.assertEqual(result["final_damage"], 180)
        self.assertEqual([row["damage"] for row in result["bench_components"]], [0, 30])
        self.assertEqual(result["exact_public_reply_routes"], ())
        absent = main._dper_combat_oracle(
            source, 937, target,
            {"target_bench": (normal_bench,), "target_flower_curtain_sources": ()},
        )
        self.assertEqual(absent["bench_components"][0]["damage"], 30)
        no_target = main._dper_combat_oracle(
            source, 937, target,
            {"target_bench": (), "target_flower_curtain_sources": (flower,)},
        )
        self.assertEqual(no_target["bench_components"], ())

    def test_04_adrena_brain_and_battle_cage_boundaries(self) -> None:
        positive = main._dper_effect_transition("ADRENA_BRAIN", {
            "source_has_darkness": True,
            "source_damage_counters": 3,
            "target_damage_counters": 1,
            "target_zone": "ACTIVE",
            "requested_counters": 2,
            "unused_this_turn": True,
        })
        self.assertEqual(positive["status"], "EXACT")
        self.assertEqual(positive["after"]["source_damage_counters"], 1)
        self.assertEqual(positive["after"]["target_damage_counters"], 3)
        no_dark = dict(positive["before"], source_has_darkness=False)
        self.assertEqual(main._dper_effect_transition("ADRENA_BRAIN", no_dark)["status"], "UNKNOWN")
        cage = dict(positive["before"], target_zone="BENCH", battle_cage=True)
        self.assertEqual(main._dper_effect_transition("ADRENA_BRAIN", cage)["status"], "UNKNOWN")
        for target_zone, expected in (("BENCH", 0), ("ACTIVE", 2)):
            result = main._dper_effect_transition("BATTLE_CAGE", {
                "placement_kind": "DAMAGE_COUNTERS",
                "target_zone": target_zone,
                "from_opponent_attack_or_ability": True,
                "requested_counters": 2,
            })
            self.assertEqual(result["after"]["placed_counters"], expected)

    def test_05_spiky_wheel_counts_darkness_only_and_next_payable_is_exact(self) -> None:
        target = pokemon(169, 302)
        mixed = pokemon(649, 301, energies=(7,), energy_ids=(7,))
        result = main._dper_combat_oracle(
            mixed, 938, target, {"allow_unpayable_certificate": True}
        )
        self.assertEqual(result["final_damage"], 60)
        self.assertFalse(result["next_payable_attack"])
        ready = pokemon(649, 303, energies=(7, 7, 7))
        ready_result = main._dper_combat_oracle(ready, 938, target)
        self.assertEqual(ready_result["final_damage"], 140)
        self.assertEqual(ready_result["next_payable_attack_ids"], (938,))

    def test_06_rock_fighting_and_mist_prevent_effect_not_damage(self) -> None:
        source = pokemon(169, 401, energies=(8,))
        rock_target = pokemon(
            677, 402, energies=(6,), energy_ids=(20,)
        )
        rock = main._dper_combat_oracle(source, 223, rock_target)
        self.assertTrue(rock["target_attack_effects_prevented"])
        self.assertGreater(rock["final_damage"], 0)
        plain = main._dper_combat_oracle(source, 223, pokemon(677, 403))
        self.assertFalse(plain.get("target_attack_effects_prevented", False))
        mist_target = pokemon(169, 404, energies=(0,), energy_ids=(11,))
        mist = main._dper_combat_oracle(source, 223, mist_target)
        self.assertTrue(mist["target_attack_effects_prevented"])
        self.assertGreater(mist["final_damage"], 0)

    def test_07_premium_power_pro_and_cheer_on_to_glory_are_exact_pre_weakness_modifiers(self) -> None:
        target = pokemon(169, 502)
        fighting = pokemon(677, 501, energies=(6,))
        proof = {
            "card_id": 1141,
            "card_serial": 999,
            "activated_turn": 7,
            "current_turn": 7,
        }
        powered = main._dper_combat_oracle(
            fighting, 981, target, {"premium_power_pro_proof": proof}
        )
        self.assertEqual(powered["final_damage"], 60)
        stacked = dict(proof)
        stacked.pop("card_serial")
        stacked["card_serials"] = (998, 999)
        self.assertEqual(
            main._dper_combat_oracle(
                fighting, 981, target,
                {"premium_power_pro_proof": stacked},
            )["final_damage"],
            90,
        )
        expired = dict(proof, current_turn=8)
        self.assertEqual(
            main._dper_combat_oracle(
                fighting, 981, target,
                {"premium_power_pro_proof": expired},
            )["status"],
            "UNKNOWN",
        )
        non_fighting = pokemon(169, 503, energies=(8,))
        no_bonus = main._dper_combat_oracle(
            non_fighting, 223, target,
            {"premium_power_pro_proof": proof},
        )
        self.assertEqual(no_bonus["final_damage"], 30)
        cynthia = pokemon(342, 504, energies=(1, 1, 1))
        cheer = pokemon(342, 505)
        cheered = main._dper_combat_oracle(
            cynthia, 476, target, {"cheer_on_sources": (cheer,)}
        )
        self.assertEqual(cheered["final_damage"], 80)
        not_cynthia = main._dper_combat_oracle(
            fighting, 981, target, {"cheer_on_sources": (cheer,)}
        )
        self.assertEqual(not_cynthia["final_damage"], 30)

    def test_08_attack_locks_need_immediate_public_log_and_allow_other_or_later_attack(self) -> None:
        target = pokemon(169, 602)
        for card_id, attack_id, energy_count in ((677, 981, 1), (678, 983, 2)):
            source = pokemon(
                card_id, 600 + card_id,
                energies=(6,) * energy_count,
            )
            proof = {
                "attacker_serial": source["serial"],
                "attack_id": attack_id,
                "attack_turn": 5,
                "current_turn": 7,
            }
            self.assertEqual(
                main._dper_combat_oracle(
                    source, attack_id, target,
                    {"public_log": proof},
                )["status"],
                "UNKNOWN",
            )
            later = dict(proof, current_turn=9)
            self.assertEqual(
                main._dper_combat_oracle(
                    source, attack_id, target,
                    {"public_log": later},
                )["status"],
                "EXACT",
            )
        lucario = pokemon(678, 699, energies=(6, 6))
        same_lock = {
            "attacker_serial": 699,
            "attack_id": 983,
            "attack_turn": 5,
            "current_turn": 7,
        }
        self.assertEqual(
            main._dper_combat_oracle(
                lucario, 982, target,
                {"public_log": same_lock},
            )["status"],
            "EXACT",
        )

    def test_09_spiky_energy_returns_after_ko_and_only_after_active_attack_damage(self) -> None:
        source = pokemon(381, 701, energies=(6, 6))
        target = pokemon(
            169, 702, energies=(0,), energy_ids=(14,)
        )
        ko = main._dper_combat_oracle(
            source, 532, target, {"target_zone": "ACTIVE"}
        )
        self.assertTrue(ko["ko"])
        self.assertEqual(ko["post_damage_counter_return"], 2)
        bench = main._dper_combat_oracle(
            source, 532, target, {"target_zone": "BENCH"}
        )
        self.assertEqual(bench["post_damage_counter_return"], 0)
        zero_source = pokemon(387, 703, energies=(7,))
        zero = main._dper_combat_oracle(
            zero_source, 540, target,
            {"source_bench": (), "target_zone": "ACTIVE"},
        )
        self.assertEqual(zero["final_damage"], 0)
        self.assertEqual(zero["post_damage_counter_return"], 0)

    def test_10_grow_grass_and_power_weight_preserve_damage_and_move_ko_boundary(self) -> None:
        grass = pokemon(
            343, 801, energies=(1,), energy_ids=(18,),
            max_hp=100, hp=90,
        )
        self.assertEqual(main._dper_expected_max_hp(grass), 100)
        plain_grass = pokemon(343, 802, hp=70)
        self.assertEqual(main._dper_expected_max_hp(plain_grass), 80)
        weighted = pokemon(
            342, 803, max_hp=200, hp=170,
            tools=(card(1173, 804),),
        )
        self.assertEqual(main._dper_expected_max_hp(weighted), 200)
        plain = pokemon(342, 805, hp=100)
        self.assertEqual(main._dper_expected_max_hp(plain), 130)
        non_cynthia_weight = pokemon(
            169, 807, max_hp=130, hp=130,
            tools=(card(1173, 808),),
        )
        self.assertEqual(main._dper_expected_max_hp(non_cynthia_weight), 130)
        source = pokemon(169, 806, energies=(8,))
        grass_hit = main._dper_combat_oracle(source, 223, grass)
        plain_hit = main._dper_combat_oracle(source, 223, plain_grass)
        self.assertGreater(grass_hit["remaining_hp"], plain_hit["remaining_hp"])

    def test_11_mysterious_rock_inn_superb_scissors_and_full_metal_lab_order(self) -> None:
        crustle = pokemon(345, 902)
        pokemon_ex = pokemon(190, 901, energies=(8, 8, 8))
        prevented = main._dper_combat_oracle(pokemon_ex, 253, crustle)
        self.assertEqual(prevented["final_damage"], 0)
        non_ex = pokemon(840, 903, energies=(8, 8, 8))
        not_prevented = main._dper_combat_oracle(non_ex, 1212, crustle)
        self.assertGreater(not_prevented["final_damage"], 0)
        scissors = pokemon(345, 904, energies=(1, 1, 1))
        metal = pokemon(169, 905)
        lab = main._dper_combat_oracle(
            scissors, 479, metal,
            {"full_metal_lab": True, "target_coated_prevention": True},
        )
        self.assertEqual(lab["final_damage"], 90)
        self.assertNotIn("full_metal_lab_minus_30", [row["step"] for row in lab["pipeline"]])

    def test_12_draconic_buster_and_raging_curse_resource_and_counter_ledgers(self) -> None:
        target = pokemon(169, 1002)
        garchomp = pokemon(381, 1001, energies=(6, 6))
        buster = main._dper_combat_oracle(garchomp, 532, target)
        self.assertEqual(buster["post_attack_resource_ledger"]["source_energy"], ())
        self.assertFalse(buster["next_payable_attack"])
        non_discard = main._dper_combat_oracle(
            pokemon(678, 1003, energies=(6, 6)), 983, target
        )
        self.assertTrue(non_discard["post_attack_resource_ledger"]["source_energy"])
        spiritomb = pokemon(387, 1004, energies=(7,), hp=40)
        bench = (
            pokemon(342, 1005, hp=100),
            pokemon(381, 1006, hp=310),
            pokemon(169, 1007, hp=100),
        )
        curse = main._dper_combat_oracle(
            spiritomb, 540, target, {"source_bench": bench}
        )
        self.assertEqual(curse["final_damage"], 50)
        zero = main._dper_combat_oracle(
            spiritomb, 540, target,
            {"source_bench": (pokemon(169, 1008),)},
        )
        self.assertEqual(zero["final_damage"], 0)

    def test_13_full_metal_lab_is_symmetric_and_nonmetal_or_absent_is_unchanged(self) -> None:
        for source_player, target_player in ((0, 1), (1, 0)):
            source = pokemon(666, 1101 + source_player, player=source_player, energies=(8,))
            metal = pokemon(169, 1110 + target_player, player=target_player)
            without = main._dper_combat_oracle(source, 965, metal)
            with_lab = main._dper_combat_oracle(
                source, 965, metal, {"full_metal_lab": True}
            )
            self.assertEqual(without["final_damage"] - with_lab["final_damage"], 30)
            nonmetal = main._dper_combat_oracle(
                source, 965, pokemon(677, 1120 + target_player, player=target_player),
                {"full_metal_lab": True},
            )
            no_stadium = main._dper_combat_oracle(
                source, 965, pokemon(677, 1130 + target_player, player=target_player)
            )
            self.assertEqual(nonmetal["final_damage"], no_stadium["final_damage"])

    def test_14_acceleration_callbacks_are_both_seat_order_duplicate_and_hidden_safe(self) -> None:
        for effect_id in ("PUNK_UP", "ASSEMBLE_ALLOY", "AURA_JAB", "TURBO_FLARE"):
            for seat in (0, 1):
                transaction = main._dper_begin_callback(effect_id, {
                    "seat": seat, "turn": 9, "source_serial": 1200 + seat,
                })
                rows = ((1301, 8, 1402), (1301, 8, 1401))
                first = main._dper_resume_callback(transaction, {
                    "seat": seat, "turn": 9, "source_serial": 1200 + seat,
                    "resolved": True,
                    "post_callback_attachments": rows,
                })
                self.assertEqual(first["status"], "EXACT")
                self.assertEqual(first["callback_stage"], "COMPLETE")
                duplicate = main._dper_resume_callback(transaction, {
                    "seat": seat, "turn": 9, "source_serial": 1200 + seat,
                    "resolved": True,
                    "post_callback_attachments": tuple(reversed(rows)),
                })
                self.assertTrue(duplicate["duplicate"])
        hidden = main._dper_effect_transition("PUNK_UP", {
            "evolution_callback_resolved": False,
            "post_callback_attachments": None,
        })
        self.assertEqual(hidden["status"], "UNKNOWN")

    def test_15_switch_family_requires_legal_public_target_and_never_removes_last(self) -> None:
        bench = (pokemon(169, 1501), pokemon(677, 1502))
        for effect_id in (
            "TRADING_PLACES", "TELEPORTATION_ATTACK", "SWITCH", "SURFER"
        ):
            state = {"legal_bench": bench, "public_card_available": True}
            if effect_id == "SURFER":
                state.update({
                    "source_hand_count_after_play": 4,
                    "source_deck_count": 20,
                })
            positive = main._dper_effect_transition(effect_id, state)
            self.assertEqual(positive["status"], "EXACT")
            self.assertEqual(len(positive["after"]["legal_active_routes"]), 2)
            negative_state = {
                "legal_bench": (), "public_card_available": True,
            }
            if effect_id == "SURFER":
                negative_state.update({
                    "source_hand_count_after_play": 4,
                    "source_deck_count": 20,
                })
            negative = main._dper_effect_transition(effect_id, negative_state)
            self.assertEqual(negative["status"], "UNKNOWN")
        for effect_id in ("SWITCH", "SURFER"):
            hidden = main._dper_effect_transition(
                effect_id,
                {"legal_bench": bench, "public_card_available": False},
            )
            self.assertEqual(hidden["status"], "UNKNOWN")
        run = main._dper_effect_transition("RUN_AWAY_DRAW", {
            "legal_bench": bench, "own_pokemon_count": 3,
        })
        self.assertEqual(run["status"], "EXACT")
        last = main._dper_effect_transition("RUN_AWAY_DRAW", {
            "legal_bench": bench, "own_pokemon_count": 1,
        })
        self.assertEqual(last["status"], "UNKNOWN")

    def test_16_run_away_reply_routes_are_exact_not_fixed_and_need_deck_and_bench(self) -> None:
        source = pokemon(169, 1601, energies=(8,))
        target = pokemon(66, 1602)
        bench = (pokemon(169, 1603, player=1),)
        positive = main._dper_combat_oracle(source, 223, target, {
            "target_bench": bench,
            "target_own_pokemon_count": 2,
            "target_deck_count": 3,
            "run_away_available": True,
        })
        self.assertTrue(positive["run_away_draw_executable"])
        self.assertFalse(positive["persistent_progress"])
        self.assertEqual(positive["exact_public_reply_routes"][0]["kind"], "RUN_AWAY_DRAW_PROMOTION")
        no_bench = main._dper_combat_oracle(source, 223, target, {
            "target_bench": (),
            "target_own_pokemon_count": 1,
            "target_deck_count": 3,
            "run_away_available": True,
        })
        self.assertFalse(no_bench["run_away_draw_executable"])
        for deck_count in (1, 2):
            partial = main._dper_combat_oracle(source, 223, target, {
                "target_bench": bench,
                "target_own_pokemon_count": 2,
                "target_deck_count": deck_count,
                "run_away_available": True,
            })
            self.assertTrue(partial["run_away_draw_executable"])
            step = next(
                row for row in partial["pipeline"]
                if row["step"] == "run_away_draw_exact_leave_play"
            )
            self.assertEqual(step["draw"], deck_count)
        empty_deck = main._dper_combat_oracle(source, 223, target, {
            "target_bench": bench,
            "target_own_pokemon_count": 2,
            "target_deck_count": 0,
            "run_away_available": True,
        })
        self.assertFalse(empty_deck["run_away_draw_executable"])

    def test_17_aura_jab_and_turbo_flare_accelerate_following_turn_only(self) -> None:
        rows = ((1701, 6, 1702),)
        for effect_id in ("AURA_JAB", "TURBO_FLARE"):
            result = main._dper_effect_transition(effect_id, {
                "attack_resolved": True,
                "post_callback_attachments": rows,
            })
            self.assertEqual(result["status"], "EXACT")
            self.assertEqual(result["after"]["current_attack_payment_delta"], 0)
            self.assertEqual(result["after"]["following_turn_readiness"], rows)
            unresolved = main._dper_effect_transition(effect_id, {
                "attack_resolved": False,
                "post_callback_attachments": None,
            })
            self.assertEqual(unresolved["status"], "UNKNOWN")

    def test_18_ascension_rare_candy_and_forest_obey_stage_access_and_turn(self) -> None:
        eevee = pokemon(43, 1801, appear=True)
        eevee_evolution = direct_evolution(43, 1802)
        ascension = main._dper_effect_transition("ASCENSION", {
            "source": eevee,
            "public_evolutions": (eevee_evolution,),
            "first_turn": False,
            "appear_this_turn": True,
        })
        self.assertEqual(ascension["status"], "EXACT")
        self.assertEqual(
            main._dper_effect_transition("ASCENSION", {
                "source": eevee, "public_evolutions": (), "first_turn": False,
            })["status"],
            "UNKNOWN",
        )
        basic, stage2 = rare_candy_line()
        candy = main._dper_effect_transition("RARE_CANDY", {
            "source": basic,
            "public_evolutions": (stage2,),
            "first_turn": False,
            "appear_this_turn": False,
        })
        self.assertEqual(candy["status"], "EXACT")
        candy_new = main._dper_effect_transition("RARE_CANDY", {
            "source": basic,
            "public_evolutions": (stage2,),
            "first_turn": False,
            "appear_this_turn": True,
        })
        self.assertEqual(candy_new["status"], "UNKNOWN")
        grass_source = pokemon(68, 1803, appear=True)
        grass_evolution = direct_evolution(68, 1804)
        forest = main._dper_effect_transition("FOREST_OF_VITALITY", {
            "source": grass_source,
            "public_evolutions": (grass_evolution,),
            "first_turn": False,
            "appear_this_turn": True,
        })
        self.assertEqual(forest["status"], "EXACT")
        first = main._dper_effect_transition("FOREST_OF_VITALITY", {
            "source": grass_source,
            "public_evolutions": (grass_evolution,),
            "first_turn": True,
            "appear_this_turn": True,
        })
        self.assertEqual(first["status"], "UNKNOWN")

    def test_19_wally_and_jumbo_require_public_legal_damaged_target(self) -> None:
        mega = pokemon(
            678, 1901, energies=(6, 6, 6), hp=200
        )
        wally = main._dper_effect_transition("WALLYS_COMPASSION", {
            "public_card_available": True,
            "target": mega,
            "target_zone": "ACTIVE",
        })
        self.assertEqual(wally["status"], "EXACT")
        self.assertEqual(wally["after"]["target_hp"], 340)
        self.assertEqual(len(wally["after"]["energy_returned_to_hand"]), 3)
        hidden = main._dper_effect_transition("WALLYS_COMPASSION", {
            "public_card_available": False,
            "target": mega,
            "target_zone": "ACTIVE",
        })
        self.assertEqual(hidden["status"], "UNKNOWN")
        jumbo = main._dper_effect_transition("JUMBO_ICE_CREAM", {
            "public_card_available": True,
            "target": mega,
            "target_zone": "ACTIVE",
        })
        self.assertEqual(jumbo["after"]["target_hp"], 280)
        bench = main._dper_effect_transition("JUMBO_ICE_CREAM", {
            "public_card_available": True,
            "target": mega,
            "target_zone": "BENCH",
        })
        self.assertEqual(bench["status"], "UNKNOWN")

    def test_20_legacy_turbo_fml_ice_and_runaway_critical_fields_are_parity_gated(self) -> None:
        cinderace = pokemon(666, 2001, energies=(8,))
        target = pokemon(169, 2002)
        legacy = main._dper_legacy_combat_oracle(cinderace, 965, target, {})
        registry = main._pcrd_public_combat_oracle(cinderace, 965, target, {})
        for key in (
            "status", "final_damage", "ko", "prize_yield",
            "persistent_effects", "persistent_progress",
            "run_away_draw_executable",
        ):
            self.assertEqual(registry[key], legacy[key])
        damaged = pokemon(169, 2003, energies=(8, 8, 8), hp=40)
        self.assertEqual(
            main._pcrd_ice_projection(damaged),
            main._dper_legacy_ice_projection(damaged),
        )

    def test_21_production_oracle_changes_named_certificate_and_fail_closes_unknown(self) -> None:
        source = pokemon(649, 2101, energies=(7, 7, 7))
        target = pokemon(169, 2102)
        legacy = main._dper_legacy_combat_oracle(source, 938, target, {})
        registry = main._pcrd_public_combat_oracle(source, 938, target, {})
        self.assertEqual(legacy["status"], "UNKNOWN")
        self.assertEqual(registry["status"], "EXACT")
        self.assertEqual(registry["final_damage"], 140)
        original = main._DPER_BINDINGS
        try:
            bad = list(original)
            index = next(i for i, row in enumerate(bad) if row.effect_id == "SPIKY_WHEEL")
            bad[index] = bad[index]._replace(text_hash="0" * 64)
            main._DPER_BINDINGS = tuple(bad)
            rejected = main._pcrd_public_combat_oracle(source, 938, target, {})
            self.assertEqual(rejected["status"], "UNKNOWN")
        finally:
            main._DPER_BINDINGS = original

    def test_22_surfer_projects_draw_counts_but_switch_does_not(self) -> None:
        bench = (pokemon(169, 2201),)
        surfer = main._dper_effect_transition("SURFER", {
            "legal_bench": bench, "public_card_available": True,
            "source_hand_count_after_play": 2, "source_deck_count": 10,
        })
        self.assertEqual(surfer["status"], "EXACT")
        self.assertEqual(surfer["after"]["draw_count"], 3)
        self.assertEqual(surfer["after"]["source_hand_count"], 5)
        switch = main._dper_effect_transition("SWITCH", {
            "legal_bench": bench, "public_card_available": True,
        })
        self.assertEqual(switch["status"], "EXACT")
        self.assertNotIn("draw_count", switch["after"])
        self.assertEqual(
            main._dper_effect_transition("SURFER", {
                "legal_bench": bench, "public_card_available": True,
            })["status"],
            "UNKNOWN",
        )

    def test_23_grow_grass_on_non_grass_is_exact_no_hp_modifier(self) -> None:
        metal = pokemon(
            169, 2301, energies=(1,), energy_ids=(18,),
            max_hp=main.CARD_DB[169].hp, hp=main.CARD_DB[169].hp,
        )
        self.assertNotEqual(main.CARD_DB[169].energyType, 1)
        self.assertEqual(
            main._dper_expected_max_hp(metal), main.CARD_DB[169].hp
        )

    def test_24_adrena_production_enumerates_active_and_battle_cage_blocks_bench(self) -> None:
        munkidori = pokemon(
            112, 2401, player=1, energies=(7,), energy_ids=(7,),
        )
        donor = pokemon(
            169, 2404, player=1, hp=main.CARD_DB[169].hp - 30,
        )
        our_active = pokemon(169, 2402, player=0)
        our_bench = pokemon(169, 2403, player=0)
        mine = SimpleNamespace(active=[our_active], bench=[our_bench], prize=[])
        opponent = SimpleNamespace(active=[munkidori], bench=[donor], prize=[])
        obs = SimpleNamespace(
            current=SimpleNamespace(yourIndex=0, players=[mine, opponent])
        )
        result = main._dper_adrena_public_moves(
            obs, our_active, {"battle_cage": True}
        )
        self.assertEqual(result["status"], "EXACT")
        self.assertEqual(
            {row["placed_counters"] for row in result["battle_cage_records"]},
            {0},
        )
        self.assertEqual(
            {row["donor_counters_after"] for row in result["battle_cage_records"]},
            {3},
        )
        self.assertEqual(
            {move[:2] for row in result["move_sets"] for move in row["moves"]},
            {(2401, 2404)},
        )
        self.assertEqual(
            {
                dict(row["placed_by_target"])[2402]
                for row in result["move_sets"]
                if 2402 in dict(row["placed_by_target"])
            },
            {1, 2, 3},
        )

    def test_25_ascension_callback_duplicate_and_log_cache_game_reset(self) -> None:
        source = pokemon(43, 2501, appear=True)
        evolution = direct_evolution(43, 2502)
        transaction = main._dper_begin_callback("ASCENSION", {
            "seat": 0, "turn": 3, "source_serial": 2501,
        })
        state = {
            "seat": 0, "turn": 3, "source_serial": 2501,
            "resolved": True, "source": source,
            "public_evolutions": (evolution,), "first_turn": False,
            "appear_this_turn": True,
        }
        first = main._dper_resume_callback(transaction, state)
        second = main._dper_resume_callback(transaction, state)
        self.assertEqual(first["status"], "EXACT")
        self.assertFalse(first["duplicate"])
        self.assertTrue(second["duplicate"])
        main._dper_seen_log_fingerprints.add(("old-game",))
        main._dper_current_turn_plays[(9, 0, 1141)] = {999}
        main._dper_last_log_turn = 9
        main._dper_reset_runtime("fixture_new_game")
        self.assertEqual(main._dper_seen_log_fingerprints, set())
        self.assertEqual(main._dper_current_turn_plays, {})
        self.assertIsNone(main._dper_last_log_turn)

    def test_26_adrena_recomputes_donor_attack_and_sturdy_from_projected_hp(self) -> None:
        target_max = main.CARD_DB[533].hp
        source_counters = (target_max - 80) // 10
        donor_attacker = pokemon(
            169, 2601, player=1, energies=(8, 8, 8),
            hp=main.CARD_DB[169].hp - 10 * source_counters,
        )
        sturdy = pokemon(533, 2602, player=0)
        state = {"allow_unpayable_certificate": True}
        old = main._pcrd_public_combat_oracle(
            donor_attacker, 224, sturdy, state
        )
        self.assertTrue(old["sturdy_applied"])
        old = dict(old)
        old["payment"] = main._pcrd_attack_payment(
            donor_attacker, main.ALL_ATTACKS[224]
        )
        old["readiness"] = main._PCRD_READY_NOW
        old["_dper_source_snapshot"] = donor_attacker
        old["_dper_effect_state"] = state
        transition = main._dper_effect_transition("ADRENA_BRAIN", {
            "source_has_darkness": True,
            "source_damage_counters": source_counters,
            "target_damage_counters": 0, "target_zone": "ACTIVE",
            "requested_counters": 1, "unused_this_turn": True,
        })
        route = {
            "tier": main._PCRD_READY_NOW,
            "sequence": (("STAY_ACTIVE", 2601),),
            "source_id": 169, "source_serial": 2601,
            "target_id": 533, "target_serial": 2602,
            "attack_id": 224, "certificate": old,
            "prize_yield": old["prize_yield"], "terminal": False,
            "public_resource": None, "certain": True,
        }
        route_obs = SimpleNamespace(current=SimpleNamespace(
            yourIndex=0,
            players=[
                SimpleNamespace(bench=[]),
                SimpleNamespace(active=[donor_attacker], bench=[]),
            ],
        ))
        result = main._dper_adrena_route_variants(
            route_obs, (route,), ({
                "moves": ((2600, 2601, 2602, 1, "ACTIVE"),),
                "transitions": (transition,),
                "donor_counters_after": ((2601, source_counters - 1),),
                "target_counters_after": ((2602, 1),),
                "placed_by_target": ((2602, 1),),
            },), sturdy, 6,
        )
        self.assertEqual(result["unsupported"], 0)
        certificate = result["variants"][0]["certificate"]
        self.assertEqual(certificate["final_damage"], target_max - 10)
        self.assertFalse(certificate["sturdy_applied"])
        self.assertTrue(certificate["ko"])

    def test_27_mist_and_rock_prevent_counter_placement_before_ko(self) -> None:
        source = pokemon(743, 2701, energies=(5,))
        plain = pokemon(677, 2702)
        mist = pokemon(677, 2703, energies=(0,), energy_ids=(11,))
        rock = pokemon(677, 2704, energies=(6,), energy_ids=(20,))
        original = main._pcrd_supported_skill_modes
        main._pcrd_supported_skill_modes = lambda pokemon_value, unsupported: ()
        try:
            state = {"source_hand_count": 2}
            self.assertEqual(
                main._dper_combat_oracle(source, 1072, plain, state)["remaining_hp"],
                plain["hp"] - 40,
            )
            for protected in (mist, rock):
                result = main._dper_combat_oracle(
                    source, 1072, protected, state
                )
                self.assertEqual(result["remaining_hp"], protected["hp"])
                self.assertFalse(result["ko"])
                self.assertEqual(result["prize_yield"], 0)
                self.assertTrue(result["target_attack_effects_prevented"])
        finally:
            main._pcrd_supported_skill_modes = original

    def test_28_shadow_routes_choose_one_bench_and_optional_attack_effects_do_not_erase_attack(self) -> None:
        source = pokemon(648, 2801, energies=(7, 7))
        target = pokemon(169, 2802, player=1)
        bench = (
            pokemon(169, 2803, player=1),
            pokemon(190, 2804, player=1),
        )
        routes = main._pcrd_attack_routes_for_source(
            source, target, tier=main._PCRD_READY_NOW, sequence=(),
            effect_state={"target_bench": bench}, opponent_prizes=6,
        )
        shadow = [route for route in routes if route["attack_id"] == 937]
        self.assertEqual(len(shadow), 2)
        self.assertEqual(
            {route["sequence"][-1][1] for route in shadow},
            {2803, 2804},
        )
        self.assertTrue(all(
            len(route["certificate"]["bench_components"]) == 1
            for route in shadow
        ))
        dunsparce = pokemon(853, 2805, energies=(1,))
        no_bench_switch = main._pcrd_attack_routes_for_source(
            dunsparce, target, tier=main._PCRD_READY_NOW, sequence=(),
            effect_state={"source_bench": ()}, opponent_prizes=6,
        )
        self.assertTrue(any(route["attack_id"] == 1231 for route in no_bench_switch))
        eevee = pokemon(344, 2806, energies=(1,))
        ascension = main._pcrd_attack_routes_for_source(
            eevee, target, tier=main._PCRD_READY_NOW, sequence=(),
            effect_state={"public_evolutions": ()}, opponent_prizes=6,
        )
        route = next(row for row in ascension if row["attack_id"] == 478)
        self.assertEqual(
            route["certificate"]["saved_callback_transaction"]["stage"],
            "AWAITING_PUBLIC_DECK_SEARCH_OPTIONS",
        )

    def test_29_post_action_board_uses_surviving_active_and_bound_shadow_target(self) -> None:
        raw_active = pokemon(169, 2901, player=1)
        projected_active = pokemon(169, 2901, player=1, hp=70)
        bench_a = pokemon(169, 2902, player=1)
        bench_b = pokemon(169, 2903, player=1)
        mine = SimpleNamespace(active=[pokemon(169, 2904)], bench=[], prize=[])
        opponent = SimpleNamespace(
            active=[raw_active], bench=[bench_a, bench_b], prize=[],
        )
        obs = SimpleNamespace(
            current=SimpleNamespace(yourIndex=0, players=[mine, opponent])
        )
        result = main._dper_post_action_observation(
            obs, projected_active, False, {
                "bench_components": ({
                    "target_serial": 2902, "damage": 30,
                    "choice_semantics": "ONE_BENCH_TARGET_ALTERNATIVE",
                },),
            },
        )
        self.assertEqual(result["status"], "EXACT")
        projected_opp = result["observation"].current.players[1]
        self.assertEqual(projected_opp.active[0]["hp"], 70)
        self.assertEqual(projected_opp.bench[0]["hp"], bench_a["hp"] - 30)
        self.assertEqual(projected_opp.bench[1]["hp"], bench_b["hp"])
        removed = main._dper_post_action_observation(
            obs, raw_active, True, {"bench_components": ()}
        )
        self.assertEqual(removed["observation"].current.players[1].active, [])

    def test_30_adrena_distributes_multiple_abilities_and_combines_bench_ko_prizes(self) -> None:
        ability_a = pokemon(112, 3001, player=1, energies=(7,), energy_ids=(7,))
        ability_b = pokemon(112, 3002, player=1, energies=(7,), energy_ids=(7,))
        donor = pokemon(169, 3003, player=1, hp=110)
        active = pokemon(169, 3004, hp=10)
        bench = pokemon(169, 3005, hp=10)
        mine = SimpleNamespace(active=[active], bench=[bench], prize=[None, None])
        opponent = SimpleNamespace(
            active=[ability_a], bench=[ability_b, donor], prize=[],
        )
        obs = SimpleNamespace(
            current=SimpleNamespace(yourIndex=0, players=[mine, opponent])
        )
        moves = main._dper_adrena_public_moves(
            obs, active, {"battle_cage": False}
        )
        split = next(
            row for row in moves["move_sets"]
            if dict(row["placed_by_target"]) == {3004: 1, 3005: 1}
            and dict(row["donor_counters_after"])[3003] == 0
        )
        variants = main._dper_adrena_route_variants(
            obs, (), (split,), active, 2
        )
        self.assertEqual(variants["unsupported"], 0)
        ability_ko = variants["variants"][0]
        self.assertEqual(ability_ko["certificate"]["prize_yield"], 2)
        self.assertTrue(ability_ko["terminal"])
        nonterminal = main._dper_adrena_route_variants(
            obs, (), (split,), active, 3
        )
        self.assertEqual(nonterminal["variants"], ())
        self.assertEqual(nonterminal["unsupported"], 1)

    def test_31_spiky_return_projects_reply_hp_and_self_ko_fails_closed(self) -> None:
        active = pokemon(169, 3101, hp=30)
        opponent_active = pokemon(169, 3102, player=1)
        mine = SimpleNamespace(active=[active], bench=[], prize=[])
        opponent = SimpleNamespace(
            active=[opponent_active], bench=[], prize=[], deckCount=10,
        )
        obs = SimpleNamespace(
            current=SimpleNamespace(yourIndex=0, players=[mine, opponent])
        )
        captured = {}
        legacy = main._dper_legacy_threat_graph
        switch = main._dper_public_switch_and_heal_routes
        adrena = main._dper_adrena_public_moves
        variants = main._dper_adrena_route_variants
        try:
            def fake_graph(observation, **kwargs):
                captured["hp"] = kwargs["our_active"]["hp"]
                return {"complete": True, "routes": (), "unsupported_text": ()}
            main._dper_legacy_threat_graph = fake_graph
            main._dper_public_switch_and_heal_routes = lambda *args, **kwargs: ()
            main._dper_adrena_public_moves = lambda *args, **kwargs: {
                "status": "EXACT", "move_sets": (),
                "battle_cage_records": (),
            }
            main._dper_adrena_route_variants = lambda *args, **kwargs: {
                "variants": (), "unsupported": 0,
            }
            graph = main._pcrd_threat_graph(
                obs, our_active=active, opponent_active=opponent_active,
                opponent_active_ko=False,
                attack_certificate={
                    "post_damage_counter_return": 2,
                    "bench_components": (), "persistent_effects": {},
                },
                stadium={"full_metal_lab": False, "battle_cage": False},
            )
            self.assertTrue(graph["complete"])
            self.assertEqual(captured["hp"], 10)
            ko_graph = main._pcrd_threat_graph(
                obs, our_active=pokemon(169, 3103, hp=20),
                opponent_active=opponent_active, opponent_active_ko=False,
                attack_certificate={"post_damage_counter_return": 2},
                stadium={"full_metal_lab": False, "battle_cage": False},
            )
            self.assertFalse(ko_graph["complete"])
            self.assertIn("promotion", ko_graph["unsupported_text"][0])
        finally:
            main._dper_legacy_threat_graph = legacy
            main._dper_public_switch_and_heal_routes = switch
            main._dper_adrena_public_moves = adrena
            main._dper_adrena_route_variants = variants

    def test_32_adrena_unsupported_variant_controls_graph_completeness(self) -> None:
        active = pokemon(169, 3201)
        opponent_active = pokemon(169, 3202, player=1)
        mine = SimpleNamespace(active=[active], bench=[], prize=[])
        opponent = SimpleNamespace(
            active=[opponent_active], bench=[], prize=[], deckCount=10,
        )
        obs = SimpleNamespace(
            current=SimpleNamespace(yourIndex=0, players=[mine, opponent])
        )
        legacy = main._dper_legacy_threat_graph
        switch = main._dper_public_switch_and_heal_routes
        adrena = main._dper_adrena_public_moves
        variants = main._dper_adrena_route_variants
        unsupported = {"count": 0}
        try:
            main._dper_legacy_threat_graph = lambda *args, **kwargs: {
                "complete": True, "routes": (), "unsupported_text": (),
            }
            main._dper_public_switch_and_heal_routes = lambda *args, **kwargs: ()
            main._dper_adrena_public_moves = lambda *args, **kwargs: {
                "status": "EXACT", "move_sets": (),
                "battle_cage_records": (),
            }
            main._dper_adrena_route_variants = lambda *args, **kwargs: {
                "variants": (), "unsupported": unsupported["count"],
            }
            exact_graph = main._pcrd_threat_graph(
                obs, our_active=active, opponent_active=opponent_active,
                opponent_active_ko=False,
                attack_certificate={
                    "post_damage_counter_return": 0,
                    "bench_components": (), "persistent_effects": {},
                },
                stadium={"full_metal_lab": False, "battle_cage": False},
            )
            self.assertTrue(exact_graph["complete"])
            self.assertEqual(
                exact_graph["registry_adrena_variants_not_admitted"], 0
            )
            unsupported["count"] = 1
            incomplete_graph = main._pcrd_threat_graph(
                obs, our_active=active, opponent_active=opponent_active,
                opponent_active_ko=False,
                attack_certificate={
                    "post_damage_counter_return": 0,
                    "bench_components": (), "persistent_effects": {},
                },
                stadium={"full_metal_lab": False, "battle_cage": False},
            )
            self.assertFalse(incomplete_graph["complete"])
            self.assertEqual(
                incomplete_graph["registry_adrena_variants_not_admitted"], 1
            )
            self.assertIn(
                "dper_adrena_variant_not_admitted",
                incomplete_graph["unsupported_text"],
            )
        finally:
            main._dper_legacy_threat_graph = legacy
            main._dper_public_switch_and_heal_routes = switch
            main._dper_adrena_public_moves = adrena
            main._dper_adrena_route_variants = variants


if __name__ == "__main__":
    unittest.main()
