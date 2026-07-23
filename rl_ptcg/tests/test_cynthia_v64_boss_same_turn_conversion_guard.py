"""Focused contract checks for Cynthia Garchomp v64's Boss conversion guard."""

import ast
import copy
import difflib
import hashlib
import importlib.util
import json
import sys
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
V63_DIR = ROOT / "meta_agents" / "cynthia_garchomp_nasuo445_v63_crustle_spiritomb_counter"
V64_DIR = ROOT / "meta_agents" / "cynthia_garchomp_nasuo445_v64_boss_same_turn_conversion_guard"
REPLAY_DIR = ROOT / "analysis_outputs" / "kaggle_live" / "submission_54673338_cynthia_v63"
V63_MAIN_SHA256 = "464e04a37dc71499605c3f2bac9d3f5c33f596c11a93b31768efb8707357a4d8"
DECK_SHA256 = "606b44f7d6181c57c6ccdd7ee493c72baf39e684b264886bc01631dbee8d349c"
REPLAY_CASES = {
    85872552: {
        "sha256": "ae7f462a03230d162cb5b15ce107df0852f7dd0ae6c1dcc3baf29dfd57a00b0f",
        "steps": (49,),
        "player": 1,
    },
    85874127: {
        "sha256": "b125ab6e27ecb96e20c51d90eb1c4b296bb63cf4936a086633581d1868926983",
        "steps": (54, 55, 56, 57, 58),
        "player": 0,
    },
}
OPTION_FIELDS = (
    "area",
    "index",
    "playerIndex",
    "inPlayArea",
    "inPlayIndex",
    "attackId",
    "number",
)

PLAIN_TARGET = 9001
FIGHTING_RESIST_EX = 9002
PREVENT_TARGET = 9003
REDUCTION_STADIUM = 9004
GENERIC_ACTIVE = 9005


def skill(name, text):
    return types.SimpleNamespace(name=name, text=text)


def card_data(
    card_id,
    name,
    *,
    hp=0,
    energy_type=0,
    resistance=None,
    ex=False,
    mega_ex=False,
    attacks=(),
    skills=(),
):
    return types.SimpleNamespace(
        cardId=card_id,
        name=name,
        hp=hp,
        energyType=energy_type,
        resistance=resistance,
        weakness=None,
        ex=ex,
        megaEx=mega_ex,
        tera=False,
        attacks=list(attacks),
        skills=list(skills),
    )


def install_api_stub():
    api = types.ModuleType("cg.api")
    api.AreaType = types.SimpleNamespace(
        DECK=1,
        HAND=2,
        DISCARD=3,
        ACTIVE=4,
        BENCH=5,
        PRIZE=6,
        STADIUM=7,
        LOOKING=12,
    )
    api.OptionType = types.SimpleNamespace(
        NUMBER=0,
        YES=1,
        NO=2,
        CARD=3,
        TOOL_CARD=4,
        ENERGY_CARD=5,
        ENERGY=6,
        PLAY=7,
        ATTACH=8,
        EVOLVE=9,
        ABILITY=10,
        DISCARD=11,
        RETREAT=12,
        ATTACK=13,
        END=14,
    )
    api.SelectContext = types.SimpleNamespace(
        MAIN=0,
        SETUP_ACTIVE_POKEMON=1,
        SETUP_BENCH_POKEMON=2,
        SWITCH=3,
        TO_ACTIVE=4,
        TO_BENCH=5,
        TO_HAND=7,
        DISCARD=8,
        TO_DECK=9,
        TO_DECK_BOTTOM=10,
        DAMAGE=15,
        HEAL=17,
        ATTACH_FROM=21,
        ATTACH_TO=22,
        LOOK=24,
        DISCARD_CARD_OR_ATTACHED_CARD=29,
        IS_FIRST=41,
    )
    api.all_attack = lambda: [
        types.SimpleNamespace(attackId=475, name="Spike Sting", damage=20, energies=[0], text=""),
        types.SimpleNamespace(attackId=476, name="Leaf Step", damage=80, energies=[1, 0, 0], text=""),
        types.SimpleNamespace(attackId=529, name="Rock Hurl", damage=20, energies=[6], text=""),
        types.SimpleNamespace(attackId=530, name="Dragonslice", damage=40, energies=[6], text=""),
        types.SimpleNamespace(attackId=531, name="Corkscrew Dive", damage=100, energies=[6], text=""),
        types.SimpleNamespace(attackId=532, name="Draconic Buster", damage=260, energies=[6, 6], text=""),
        types.SimpleNamespace(attackId=540, name="Raging Curse", damage=0, energies=[0], text=""),
    ]
    api.all_card_data = lambda: [
        card_data(6, "Basic Fighting Energy", energy_type=6),
        card_data(20, "Rock Fighting Energy", energy_type=6),
        card_data(341, "Cynthia's Roselia", hp=70, energy_type=1, attacks=(475,)),
        card_data(
            342,
            "Cynthia's Roserade",
            hp=130,
            energy_type=1,
            attacks=(476,),
            skills=(skill("Cheer On to Glory", "Attacks do 30 more damage."),),
        ),
        card_data(379, "Cynthia's Gible", hp=70, energy_type=6, attacks=(529,)),
        card_data(380, "Cynthia's Gabite", hp=100, energy_type=6, attacks=(530,)),
        card_data(
            381,
            "Cynthia's Garchomp ex",
            hp=330,
            energy_type=6,
            ex=True,
            attacks=(531, 532),
        ),
        card_data(387, "Cynthia's Spiritomb", hp=70, energy_type=7, attacks=(540,)),
        card_data(
            104,
            "Froslass",
            hp=90,
            energy_type=3,
            skills=(skill("Freezing Shroud", "Put 1 damage counter during Pokemon Checkup."),),
        ),
        card_data(861, "Mega Froslass ex", hp=310, energy_type=3, mega_ex=True),
        card_data(1030, "Staryu", hp=70, energy_type=3),
        card_data(1031, "Mega Starmie ex", hp=330, energy_type=3, mega_ex=True),
        card_data(1182, "Boss's Orders"),
        card_data(1261, "Forest of Vitality", skills=(skill("Forest", "Grass Pokemon can evolve."),)),
        card_data(PLAIN_TARGET, "Plain target", hp=500, energy_type=3),
        card_data(
            FIGHTING_RESIST_EX,
            "Resistant target ex",
            hp=300,
            energy_type=3,
            resistance=6,
            ex=True,
        ),
        card_data(
            PREVENT_TARGET,
            "Prevent target",
            hp=90,
            energy_type=3,
            skills=(skill("Barrier", "Prevent all damage from attacks."),),
        ),
        card_data(
            REDUCTION_STADIUM,
            "Reduction Stadium",
            skills=(skill("Reduction", "Pokemon take 30 less damage from attacks."),),
        ),
        card_data(GENERIC_ACTIVE, "Generic active", hp=500, energy_type=3),
    ]
    api.to_observation_class = lambda observation: observation
    sys.modules["cg"] = types.ModuleType("cg")
    sys.modules["cg.api"] = api


def load_agent_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def to_object(value):
    if isinstance(value, dict):
        return types.SimpleNamespace(**{key: to_object(item) for key, item in value.items()})
    if isinstance(value, list):
        return [to_object(item) for item in value]
    return value


class BossSameTurnConversionGuardTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        install_api_stub()
        cls.v63 = load_agent_module("cynthia_v63_for_v64_test", V63_DIR / "main.py")
        cls.v64 = load_agent_module("cynthia_v64_main", V64_DIR / "main.py")

    @staticmethod
    def card(card_id, *, serial=1):
        return types.SimpleNamespace(id=card_id, serial=serial, playerIndex=0)

    @classmethod
    def pokemon(
        cls,
        card_id,
        *,
        hp=70,
        max_hp=None,
        energy_ids=(),
        energy_types=None,
        serial=1,
    ):
        max_hp = hp if max_hp is None else max_hp
        energy_cards = [
            cls.card(energy_id, serial=500 + index)
            for index, energy_id in enumerate(energy_ids)
        ]
        if energy_types is None:
            energy_types = [6 for _energy_id in energy_ids]
        return types.SimpleNamespace(
            id=card_id,
            hp=hp,
            maxHp=max_hp,
            energies=list(energy_types),
            energyCards=energy_cards,
            tools=[],
            preEvolution=[],
            serial=serial,
            appearThisTurn=False,
        )

    @staticmethod
    def option(
        option_type,
        *,
        area=None,
        index=None,
        player_index=None,
        in_play_area=None,
        in_play_index=None,
        attack_id=None,
    ):
        return types.SimpleNamespace(
            type=option_type,
            area=area,
            index=index,
            playerIndex=player_index,
            inPlayArea=in_play_area,
            inPlayIndex=in_play_index,
            attackId=attack_id,
            number=None,
        )

    @classmethod
    def observation(
        cls,
        *,
        active,
        targets,
        options,
        hand,
        bench=(),
        energy_attached=True,
        stadium=(),
        context=0,
        effect=None,
    ):
        mine = types.SimpleNamespace(
            active=[active],
            bench=list(bench),
            hand=list(hand),
            handCount=len(hand),
            discard=[],
            prize=[None] * 6,
            deckCount=30,
            benchMax=5,
            poisoned=False,
            burned=False,
            asleep=False,
            paralyzed=False,
            confused=False,
        )
        foe = types.SimpleNamespace(
            active=[cls.pokemon(GENERIC_ACTIVE, hp=500, max_hp=500, serial=90)],
            bench=list(targets),
            hand=None,
            handCount=5,
            discard=[],
            prize=[None] * 6,
            deckCount=30,
            benchMax=5,
            poisoned=False,
            burned=False,
            asleep=False,
            paralyzed=False,
            confused=False,
        )
        return types.SimpleNamespace(
            current=types.SimpleNamespace(
                yourIndex=0,
                players=[mine, foe],
                energyAttached=energy_attached,
                supporterPlayed=False,
                stadiumPlayed=False,
                retreated=False,
                stadium=list(stadium),
                looking=None,
                turn=7,
                result=-1,
            ),
            select=types.SimpleNamespace(
                option=list(options),
                context=context,
                minCount=1,
                maxCount=1,
                deck=None,
                effect=effect,
                contextCard=None,
            ),
        )

    @staticmethod
    def replay_observation(episode_id, step):
        case = REPLAY_CASES[episode_id]
        replay_path = REPLAY_DIR / f"episode_{episode_id}_replay.json"
        replay_bytes = replay_path.read_bytes()
        if hashlib.sha256(replay_bytes).hexdigest() != case["sha256"]:
            raise AssertionError(f"unexpected replay hash for {episode_id}")
        replay = json.loads(replay_bytes)
        obs = to_object(replay["steps"][step][case["player"]]["observation"])
        for option in obs.select.option:
            for field in OPTION_FIELDS:
                if not hasattr(option, field):
                    setattr(option, field, None)
        return obs

    def assert_false_boss_is_held(self, obs, boss_index=0):
        self.assertEqual(self.v63.score_option(obs, obs.select.option[boss_index])[1], "Boss for KO")
        self.assertEqual(self.v63.choose_options(obs), [boss_index])
        self.assertNotEqual(self.v64.choose_options(obs), [boss_index])

    def spiritomb_conversion_observation(
        self,
        *,
        energy_ids=None,
        attack_exposed=True,
        energy_attached=True,
        target_id=PLAIN_TARGET,
        target_hp=90,
    ):
        a = self.v64
        energy_ids = (a.BASIC_FIGHTING,) if energy_ids is None else energy_ids
        active = self.pokemon(
            a.SPIRITOMB,
            hp=70,
            energy_ids=energy_ids,
            energy_types=[6 for _energy in energy_ids],
            serial=10,
        )
        roserade = self.pokemon(a.ROSERADE, hp=50, max_hp=130, serial=11)
        target = self.pokemon(target_id, hp=target_hp, max_hp=max(target_hp, 90), serial=20)
        hand = [self.card(a.BOSS, serial=30)]
        options = [self.option(a.OptionType.PLAY, index=0)]
        if attack_exposed:
            options.append(self.option(a.OptionType.ATTACK, attack_id=a.RAGING_CURSE))
        options.append(self.option(a.OptionType.END))
        return self.observation(
            active=active,
            targets=[target],
            options=options,
            hand=hand,
            bench=[roserade],
            energy_attached=energy_attached,
            context=a.SelectContext.MAIN,
        )

    def test_replay_85872552_attaches_then_bosses_froslass_then_attacks(self):
        a = self.v64
        obs = self.replay_observation(85872552, 49)
        self.assertEqual(obs.current.turn, 8)
        self.assertEqual(a.active_pokemon(obs).id, a.SPIRITOMB)
        self.assertEqual(a.energy_count(a.active_pokemon(obs)), 0)
        self.assertEqual([pokemon.id for pokemon in a.opponent(obs).bench], [861, 104])
        self.assertEqual(a.hp(a.opponent(obs).bench[1]), 90)
        self.assertEqual(self.v63.choose_options(obs), [2])
        self.assertEqual(a.choose_options(obs), [0])
        self.assertEqual(obs.select.option[0].inPlayArea, a.AreaType.ACTIVE)

        attached = copy.deepcopy(obs)
        energy_option = attached.select.option[0]
        energy = a.option_card(attached, energy_option)
        active = a.active_pokemon(attached)
        active.energyCards = [energy]
        active.energies = [6]
        a.me(attached).hand.pop(energy_option.index)
        a.me(attached).handCount = len(a.me(attached).hand)
        attached.current.energyAttached = True
        boss_index = next(index for index, card in enumerate(a.me(attached).hand) if card.id == a.BOSS)
        attached.select.option = [
            self.option(a.OptionType.PLAY, index=boss_index),
            self.option(a.OptionType.ATTACK, attack_id=a.RAGING_CURSE),
            self.option(a.OptionType.END),
        ]
        self.assertEqual(a.choose_options(attached), [0])

        target_selection = copy.deepcopy(attached)
        target_selection.select.context = a.SelectContext.SWITCH
        target_selection.select.effect = self.card(a.BOSS, serial=116)
        target_selection.select.option = [
            self.option(a.OptionType.CARD, area=a.AreaType.BENCH, index=0, player_index=0),
            self.option(a.OptionType.CARD, area=a.AreaType.BENCH, index=1, player_index=0),
        ]
        self.assertEqual(a.choose_options(target_selection), [1])

        after_gust = copy.deepcopy(target_selection)
        foe = a.opponent(after_gust)
        selected_target = foe.bench.pop(1)
        old_active = foe.active[0]
        foe.active = [selected_target]
        foe.bench.append(old_active)
        after_gust.select.context = a.SelectContext.MAIN
        after_gust.select.effect = None
        after_gust.select.option = [
            self.option(a.OptionType.END),
            self.option(a.OptionType.ATTACK, attack_id=a.RAGING_CURSE),
        ]
        self.assertGreaterEqual(
            a.conservative_public_damage(after_gust, a.opponent_active(after_gust), a.RAGING_CURSE),
            a.hp(a.opponent_active(after_gust)),
        )
        self.assertEqual(a.choose_options(after_gust), [1])

    def test_replay_85874127_never_treats_unpayable_leaf_step_as_conversion(self):
        a = self.v64
        states = {step: self.replay_observation(85874127, step) for step in REPLAY_CASES[85874127]["steps"]}
        obs = states[54]
        self.assertEqual(obs.current.turn, 5)
        self.assertEqual(a.active_pokemon(obs).id, a.ROSERADE)
        self.assertEqual(a.energy_count(a.active_pokemon(obs)), 0)
        self.assertTrue(obs.current.energyAttached)
        self.assertFalse(any(option.type == a.OptionType.ATTACK for option in obs.select.option))
        self.assertEqual(self.v63.choose_options(obs), [0])
        self.assertEqual(a.choose_options(obs), [2])
        self.assertEqual(getattr(a.option_card(obs, obs.select.option[2]), "id", None), a.GIBLE)

        for step in (55, 56, 57, 58):
            with self.subTest(step=step):
                self.assertEqual(a.choose_options(states[step]), self.v63.choose_options(states[step]))

    def test_legitimate_current_garchomp_and_spiritomb_boss_kos_remain_valid(self):
        a = self.v64
        spiritomb = self.spiritomb_conversion_observation()

        garchomp = self.pokemon(
            a.GARCHOMP_EX,
            hp=330,
            max_hp=330,
            energy_ids=(a.BASIC_FIGHTING,),
            energy_types=(6,),
            serial=40,
        )
        roserade = self.pokemon(a.ROSERADE, hp=130, max_hp=130, serial=41)
        target = self.pokemon(PLAIN_TARGET, hp=120, max_hp=500, serial=42)
        hand = [self.card(a.BOSS, serial=43)]
        garchomp_obs = self.observation(
            active=garchomp,
            targets=[target],
            hand=hand,
            bench=[roserade],
            options=[
                self.option(a.OptionType.PLAY, index=0),
                self.option(a.OptionType.ATTACK, attack_id=a.CORKSCREW_DIVE),
                self.option(a.OptionType.END),
            ],
            energy_attached=True,
            context=a.SelectContext.MAIN,
        )

        for name, obs in (("Spiritomb", spiritomb), ("Garchomp", garchomp_obs)):
            with self.subTest(attacker=name):
                self.assertEqual(self.v63.choose_options(obs), [0])
                self.assertEqual(a.choose_options(obs), [0])

    def test_ordinary_boss_pressure_including_active_roserade_is_v63_equivalent(self):
        a = self.v64
        cases = [
            self.pokemon(a.ROSERADE, hp=130, max_hp=130, serial=50),
            self.pokemon(
                a.GARCHOMP_EX,
                hp=330,
                max_hp=330,
                energy_ids=(a.BASIC_FIGHTING, a.ROCK_FIGHTING),
                energy_types=(6, 6),
                serial=51,
            ),
        ]
        for active in cases:
            with self.subTest(active=active.id):
                target = self.pokemon(PLAIN_TARGET, hp=500, max_hp=500, serial=52)
                hand = [self.card(a.BOSS, serial=53)]
                obs = self.observation(
                    active=active,
                    targets=[target],
                    hand=hand,
                    options=[self.option(a.OptionType.PLAY, index=0), self.option(a.OptionType.END)],
                    bench=[],
                    energy_attached=True,
                    context=a.SelectContext.MAIN,
                )
                self.assertEqual(self.v63.score_play(obs, obs.select.option[0]), (3600, "Boss pressure"))
                self.assertEqual(a.score_play(obs, obs.select.option[0]), (3600, "Boss pressure"))
                self.assertEqual(a.choose_options(obs), self.v63.choose_options(obs))

    def test_projected_route_requires_exact_typed_active_attachment_and_unused_attach(self):
        a = self.v64
        target = self.pokemon(PLAIN_TARGET, hp=70, max_hp=500, serial=60)
        roserade = self.pokemon(
            a.ROSERADE,
            hp=130,
            max_hp=130,
            energy_ids=(a.BASIC_FIGHTING, a.ROCK_FIGHTING),
            energy_types=(6, 6),
            serial=61,
        )
        boss = self.card(a.BOSS, serial=62)
        energy = self.card(a.BASIC_FIGHTING, serial=63)

        gible = self.card(a.GIBLE, serial=64)
        typed_mismatch = self.observation(
            active=roserade,
            targets=[target],
            hand=[boss, energy, gible],
            options=[
                self.option(a.OptionType.PLAY, index=0),
                self.option(
                    a.OptionType.ATTACH,
                    area=a.AreaType.HAND,
                    index=1,
                    in_play_area=a.AreaType.ACTIVE,
                    in_play_index=0,
                ),
                self.option(a.OptionType.PLAY, index=2),
                self.option(a.OptionType.END),
            ],
            energy_attached=False,
            context=a.SelectContext.MAIN,
        )
        self.assert_false_boss_is_held(typed_mismatch)
        self.assertEqual(a.choose_options(typed_mismatch), [2])

        spiritomb = self.pokemon(a.SPIRITOMB, hp=70, serial=65)
        damaged_roserade = self.pokemon(a.ROSERADE, hp=50, max_hp=130, serial=66)
        non_active = self.observation(
            active=spiritomb,
            targets=[self.pokemon(PLAIN_TARGET, hp=90, max_hp=500, serial=67)],
            hand=[boss, energy, gible],
            bench=[damaged_roserade],
            options=[
                self.option(a.OptionType.PLAY, index=0),
                self.option(
                    a.OptionType.ATTACH,
                    area=a.AreaType.HAND,
                    index=1,
                    in_play_area=a.AreaType.BENCH,
                    in_play_index=0,
                ),
                self.option(a.OptionType.PLAY, index=2),
                self.option(a.OptionType.END),
            ],
            energy_attached=False,
            context=a.SelectContext.MAIN,
        )
        self.assert_false_boss_is_held(non_active)
        self.assertEqual(a.choose_options(non_active), [2])

        already_used = copy.deepcopy(non_active)
        already_used.select.option[1].inPlayArea = a.AreaType.ACTIVE
        already_used.select.option[1].inPlayIndex = 0
        already_used.current.energyAttached = True
        self.assert_false_boss_is_held(already_used)

    def test_highest_unchanged_active_attach_score_wins_projected_route(self):
        a = self.v64
        active = self.pokemon(a.GIBLE, hp=70, max_hp=70, serial=70)
        roserade = self.pokemon(a.ROSERADE, hp=130, max_hp=130, serial=71)
        target = self.pokemon(PLAIN_TARGET, hp=50, max_hp=500, serial=72)
        hand = [
            self.card(a.BOSS, serial=73),
            self.card(a.BASIC_FIGHTING, serial=74),
            self.card(a.ROCK_FIGHTING, serial=75),
        ]
        options = [
            self.option(a.OptionType.PLAY, index=0),
            self.option(
                a.OptionType.ATTACH,
                area=a.AreaType.HAND,
                index=1,
                in_play_area=a.AreaType.ACTIVE,
                in_play_index=0,
            ),
            self.option(
                a.OptionType.ATTACH,
                area=a.AreaType.HAND,
                index=2,
                in_play_area=a.AreaType.ACTIVE,
                in_play_index=0,
            ),
            self.option(a.OptionType.END),
        ]
        obs = self.observation(
            active=active,
            targets=[target],
            hand=hand,
            bench=[roserade],
            options=options,
            energy_attached=False,
            context=a.SelectContext.MAIN,
        )
        self.assertGreater(a.score_attach(obs, options[2])[0], a.score_attach(obs, options[1])[0])
        self.assertEqual(a.score_attach(obs, options[2]), self.v63.score_attach(obs, options[2]))
        self.assertEqual(a.choose_options(obs), [2])

    def test_actual_attack_exposure_status_effect_damage_and_buster_guard_fail_closed(self):
        a = self.v64
        no_attack = self.spiritomb_conversion_observation(attack_exposed=False)
        self.assert_false_boss_is_held(no_attack)

        for status in ("poisoned", "burned", "asleep", "paralyzed", "confused"):
            with self.subTest(status=status):
                obs = self.spiritomb_conversion_observation()
                setattr(a.me(obs), status, True)
                self.assert_false_boss_is_held(obs)

        uncertain = self.spiritomb_conversion_observation()
        a.active_pokemon(uncertain).effects = ["unknown public effect"]
        self.assert_false_boss_is_held(uncertain)

        prevention = self.spiritomb_conversion_observation(target_id=PREVENT_TARGET)
        self.assert_false_boss_is_held(prevention)

        reduction = self.spiritomb_conversion_observation()
        reduction.current.stadium = [self.card(REDUCTION_STADIUM, serial=80)]
        self.assert_false_boss_is_held(reduction)

        garchomp = self.pokemon(
            a.GARCHOMP_EX,
            hp=330,
            max_hp=330,
            energy_ids=(a.BASIC_FIGHTING, a.ROCK_FIGHTING),
            energy_types=(6, 6),
            serial=81,
        )
        roserade = self.pokemon(a.ROSERADE, hp=130, max_hp=130, serial=82)
        target = self.pokemon(PLAIN_TARGET, hp=200, max_hp=500, serial=83)
        hand = [self.card(a.BOSS, serial=84)]

        shortfall = self.observation(
            active=garchomp,
            targets=[target],
            hand=hand,
            bench=[roserade],
            options=[
                self.option(a.OptionType.PLAY, index=0),
                self.option(a.OptionType.ATTACK, attack_id=a.CORKSCREW_DIVE),
                self.option(a.OptionType.END),
            ],
            energy_attached=True,
            context=a.SelectContext.MAIN,
        )
        self.assert_false_boss_is_held(shortfall)

        buster_guard = copy.deepcopy(shortfall)
        buster_guard.select.option[1].attackId = a.DRACONIC_BUSTER
        self.assertGreaterEqual(a.conservative_public_damage(buster_guard, target, a.DRACONIC_BUSTER), 200)
        self.assertFalse(a.buster_guard_passes_for_target(buster_guard, a.opponent(buster_guard).bench[0]))
        self.assert_false_boss_is_held(buster_guard)

    def test_boss_target_selection_cannot_swap_to_higher_scored_uncertified_target(self):
        a = self.v64
        active = self.pokemon(
            a.GARCHOMP_EX,
            hp=330,
            max_hp=330,
            energy_ids=(a.BASIC_FIGHTING, a.ROCK_FIGHTING),
            energy_types=(6, 6),
            serial=90,
        )
        bench = [
            self.pokemon(a.ROSERADE, hp=130, max_hp=130, serial=91),
            self.pokemon(a.ROSERADE, hp=130, max_hp=130, serial=92),
        ]
        resistant = self.pokemon(FIGHTING_RESIST_EX, hp=300, max_hp=300, serial=93)
        certified = self.pokemon(PLAIN_TARGET, hp=100, max_hp=500, serial=94)
        options = [
            self.option(a.OptionType.CARD, area=a.AreaType.BENCH, index=0, player_index=1),
            self.option(a.OptionType.CARD, area=a.AreaType.BENCH, index=1, player_index=1),
        ]
        obs = self.observation(
            active=active,
            targets=[resistant, certified],
            hand=[],
            bench=bench,
            options=options,
            energy_attached=True,
            context=a.SelectContext.SWITCH,
            effect=self.card(a.BOSS, serial=95),
        )
        self.assertGreater(a.boss_target_score(obs, resistant)[0], a.boss_target_score(obs, certified)[0])
        self.assertEqual(self.v63.choose_options(obs), [0])
        self.assertEqual(a.choose_options(obs), [1])
        self.assertFalse(a.attack_certifies_target(obs, resistant, a.DRACONIC_BUSTER))
        self.assertTrue(a.attack_certifies_target(obs, certified, a.CORKSCREW_DIVE))

    def test_source_diff_is_additive_and_preserves_v63_crustle_and_deck(self):
        baseline_files = {
            path.relative_to(V63_DIR)
            for path in V63_DIR.rglob("*")
            if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
        }
        candidate_files = {
            path.relative_to(V64_DIR)
            for path in V64_DIR.rglob("*")
            if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
        }
        self.assertEqual(candidate_files, baseline_files)

        baseline_main = (V63_DIR / "main.py").read_bytes()
        candidate_main = (V64_DIR / "main.py").read_bytes()
        self.assertEqual(hashlib.sha256(baseline_main).hexdigest(), V63_MAIN_SHA256)
        opcodes = difflib.SequenceMatcher(
            a=baseline_main.decode().splitlines(),
            b=candidate_main.decode().splitlines(),
        ).get_opcodes()
        self.assertTrue(all(tag in {"equal", "insert"} for tag, *_indices in opcodes), opcodes)

        baseline_tree = ast.parse(baseline_main)
        candidate_tree = ast.parse(candidate_main)
        helper_names = {
            "normalized_energy_type",
            "public_energy_types",
            "attached_card_energy_type",
            "attack_cost_is_payable",
            "attack_is_published_for_active",
            "card_effect_text",
            "visible_damage_state_is_deterministic",
            "conservative_public_damage",
            "buster_guard_passes_for_target",
            "attack_certifies_target",
            "target_is_visible_on_opponent_bench",
            "certified_bench_targets",
            "boss_same_turn_conversion_guard",
            "certified_boss_target_index",
        }
        baseline_existing = [
            node
            for node in baseline_tree.body
            if not isinstance(node, ast.FunctionDef) or node.name != "choose_options"
        ]
        candidate_existing = [
            node
            for node in candidate_tree.body
            if not isinstance(node, ast.FunctionDef)
            or node.name not in helper_names | {"choose_options"}
        ]
        self.assertEqual(
            [ast.dump(node, include_attributes=False) for node in candidate_existing],
            [ast.dump(node, include_attributes=False) for node in baseline_existing],
        )

        baseline_crustle = next(
            node
            for node in baseline_tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "crustle_spiritomb_counter_index"
        )
        candidate_crustle = next(
            node
            for node in candidate_tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "crustle_spiritomb_counter_index"
        )
        self.assertEqual(
            ast.get_source_segment(baseline_main.decode(), baseline_crustle),
            ast.get_source_segment(candidate_main.decode(), candidate_crustle),
        )

        candidate_choose = next(
            node
            for node in candidate_tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "choose_options"
        )
        expected_first = ast.parse(
            "counter_index = crustle_spiritomb_counter_index(obs)\n"
            "if counter_index is not None:\n"
            "    return [counter_index]\n"
        ).body
        self.assertEqual(
            [ast.dump(node, include_attributes=False) for node in candidate_choose.body[:2]],
            [ast.dump(node, include_attributes=False) for node in expected_first],
        )
        for forbidden in ("85872552", "85874127", "TeamNames", "replay", "episode", "submission"):
            self.assertNotIn(forbidden, candidate_main.decode())

        baseline_deck = (V63_DIR / "deck.csv").read_bytes()
        candidate_deck = (V64_DIR / "deck.csv").read_bytes()
        self.assertEqual(candidate_deck, baseline_deck)
        self.assertEqual(hashlib.sha256(candidate_deck).hexdigest(), DECK_SHA256)
        self.assertEqual(len([line for line in candidate_deck.splitlines() if line.strip()]), 60)


if __name__ == "__main__":
    unittest.main()
