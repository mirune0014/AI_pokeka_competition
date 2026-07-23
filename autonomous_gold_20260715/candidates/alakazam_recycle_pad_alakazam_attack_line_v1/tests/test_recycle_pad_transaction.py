from __future__ import annotations

import copy
import hashlib
import importlib.util
import os
import sys
import unittest
from pathlib import Path


CANDIDATE = Path(__file__).resolve().parents[1]
REPOSITORY = CANDIDATE.parents[2]
os.chdir(CANDIDATE)
sys.path.insert(0, str(CANDIDATE))

import main as agent  # noqa: E402
from cg.api import (  # noqa: E402
    AreaType,
    Card,
    EnergyType,
    Observation,
    Option,
    OptionType,
    PlayerState,
    Pokemon,
    SelectContext,
    SelectData,
    SelectType,
    State,
)


def make_card(card_id: int, serial: int, player: int) -> Card:
    return Card(id=card_id, serial=serial, playerIndex=player)


def make_pokemon(
    card_id: int,
    serial: int,
    player: int,
    *,
    hp: int | None = None,
    max_hp: int | None = None,
    appear: bool = False,
    energy_cards: list[Card] | None = None,
    tools: list[Card] | None = None,
    pre_evolution: list[Card] | None = None,
) -> Pokemon:
    data = agent.card_table[card_id]
    energy_cards = list(energy_cards or [])
    pokemon = Pokemon(
        id=card_id,
        serial=serial,
        hp=data.hp if hp is None else hp,
        maxHp=data.hp if max_hp is None else max_hp,
        appearThisTurn=appear,
        energies=[EnergyType.PSYCHIC for _ in energy_cards],
        energyCards=energy_cards,
        tools=list(tools or []),
        preEvolution=list(pre_evolution or []),
    )
    return pokemon


def select_data(
    select_type: SelectType,
    context: SelectContext,
    options: list[Option],
    *,
    minimum: int = 1,
    maximum: int = 1,
    deck: list[Card] | None = None,
    context_card: Card | None = None,
    effect: Card | None = None,
) -> SelectData:
    return SelectData(
        type=select_type,
        context=context,
        minCount=minimum,
        maxCount=maximum,
        remainDamageCounter=0,
        remainEnergyCost=0,
        option=options,
        deck=deck,
        contextCard=context_card,
        effect=effect,
    )


class Route:
    def __init__(
        self,
        seat: int,
        variant: int,
        own_prizes: int = 4,
        opponent_prizes: int = 3,
    ):
        self.seat = seat
        self.other = 1 - seat
        self.variant = variant
        self.own_prizes = own_prizes
        self.opponent_prizes = opponent_prizes
        offset = seat * 1000 + variant * 100
        self.pad = make_card(agent.Poke_Pad, 101 + offset, seat)
        self.ash = make_card(agent.Sacred_Ash, 102 + offset, seat)
        self.dawn = make_card(agent.Dawn, 103 + offset, seat)
        self.energy = make_card(agent.Basic_Psychic_Energy, 201 + offset, seat)
        self.abra_under = make_card(agent.Abra, 202 + offset, seat)
        self.source = make_pokemon(
            agent.Kadabra,
            203 + offset,
            seat,
            hp=70,
            appear=False,
            energy_cards=[self.energy],
            pre_evolution=[self.abra_under],
        )
        self.bench = make_pokemon(agent.Dunsparce, 204 + offset, seat)
        self.target = make_card(agent.Alakazam, 301 + offset, seat)
        discard = [
            self.target,
            make_card(agent.Abra, 302 + offset, seat),
            make_card(agent.Dunsparce, 303 + offset, seat),
            make_card(agent.Kadabra, 304 + offset, seat),
            make_card(agent.Shaymin, 305 + offset, seat),
            make_card(agent.Psyduck, 306 + offset, seat),
        ]
        if variant:
            discard = [discard[4], discard[2], discard[5], discard[1], discard[3], discard[0]]
        self.start_discard = discard
        self.opponent = make_pokemon(agent.Dunsparce, 401 + offset, self.other)
        hand = [self.pad, self.ash, self.dawn]
        if variant:
            hand = [self.dawn, self.ash, self.pad]
        self.start_hand = hand
        self.turn = 9 + seat
        self.start_actions = 10
        self.start_deck = 20
        self.selected_cards: list[Card] = []
        self.discard_after_ash: list[Card] = []
        self.trace: list[tuple[str, tuple[int, ...]]] = []

    def player(
        self,
        *,
        active: Pokemon,
        hand: list[Card],
        discard: list[Card],
        deck_count: int,
    ) -> PlayerState:
        return PlayerState(
            active=[active],
            bench=[copy.deepcopy(self.bench)],
            benchMax=5,
            deckCount=deck_count,
            discard=copy.deepcopy(discard),
            prize=[None] * self.own_prizes,
            handCount=len(hand),
            hand=copy.deepcopy(hand),
            poisoned=False,
            burned=False,
            asleep=False,
            paralyzed=False,
            confused=False,
        )

    def opponent_player(self) -> PlayerState:
        return PlayerState(
            active=[copy.deepcopy(self.opponent)],
            bench=[],
            benchMax=5,
            deckCount=30,
            discard=[],
            prize=[None] * self.opponent_prizes,
            handCount=5,
            hand=None,
            poisoned=False,
            burned=False,
            asleep=False,
            paralyzed=False,
            confused=False,
        )

    def observation(
        self,
        *,
        active: Pokemon,
        hand: list[Card],
        discard: list[Card],
        deck_count: int,
        turn_actions: int,
        select: SelectData,
    ) -> Observation:
        mine = self.player(
            active=copy.deepcopy(active),
            hand=hand,
            discard=discard,
            deck_count=deck_count,
        )
        opponent = self.opponent_player()
        players = [None, None]
        players[self.seat] = mine
        players[self.other] = opponent
        state = State(
            turn=self.turn,
            turnActionCount=turn_actions,
            yourIndex=self.seat,
            firstPlayer=0,
            supporterPlayed=False,
            stadiumPlayed=False,
            energyAttached=True,
            retreated=False,
            result=-1,
            stadium=[],
            looking=None,
            players=players,
        )
        return Observation(select=select, logs=[], current=state)

    def start_observation(self) -> tuple[Observation, int, int]:
        options = []
        for index, card in enumerate(self.start_hand):
            options.append(Option(type=OptionType.PLAY, index=index))
        options.append(Option(type=OptionType.END))
        select = select_data(SelectType.MAIN, SelectContext.MAIN, options)
        observation = self.observation(
            active=self.source,
            hand=self.start_hand,
            discard=self.start_discard,
            deck_count=self.start_deck,
            turn_actions=self.start_actions,
            select=select,
        )
        pad_option = self.start_hand.index(self.pad)
        ash_option = self.start_hand.index(self.ash)
        return observation, pad_option, ash_option

    def begin(self) -> Observation:
        observation, pad_option, ash_option = self.start_observation()
        action = agent._start_recycle_pad_alakazam_attack_line(
            observation, pad_option
        )
        assert action == [ash_option]
        self.trace.append(("ash", tuple(action)))
        return observation

    def choose_to_deck(self) -> Observation:
        hand = [card for card in self.start_hand if card.serial != self.ash.serial]
        options = [
            Option(
                type=OptionType.CARD,
                area=AreaType.DISCARD,
                index=index,
                playerIndex=self.seat,
            )
            for index in range(len(self.start_discard))
        ]
        if self.variant:
            options = list(reversed(options))
        select = select_data(
            SelectType.CARD,
            SelectContext.TO_DECK,
            options,
            minimum=0,
            maximum=5,
            effect=self.ash,
        )
        observation = self.observation(
            active=self.source,
            hand=hand,
            discard=self.start_discard,
            deck_count=self.start_deck,
            turn_actions=self.start_actions + 1,
            select=select,
        )
        action = agent._recycle_pad_alakazam_overlay(observation)
        assert action is not None and len(action) == 5
        selected_options = [options[index] for index in action]
        self.selected_cards = [
            self.start_discard[option.index] for option in selected_options
        ]
        assert self.target.serial in {card.serial for card in self.selected_cards}
        self.trace.append(("to_deck", tuple(action)))
        return observation

    def play_pad(self) -> Observation:
        hand = [card for card in self.start_hand if card.serial != self.ash.serial]
        selected = {card.serial for card in self.selected_cards}
        self.discard_after_ash = [
            card for card in self.start_discard if card.serial not in selected
        ] + [self.ash]
        options = [
            Option(type=OptionType.PLAY, index=index)
            for index, _ in enumerate(hand)
        ] + [Option(type=OptionType.END)]
        select = select_data(SelectType.MAIN, SelectContext.MAIN, options)
        observation = self.observation(
            active=self.source,
            hand=hand,
            discard=self.discard_after_ash,
            deck_count=self.start_deck + 5,
            turn_actions=self.start_actions + 2,
            select=select,
        )
        action = agent._recycle_pad_alakazam_overlay(observation)
        expected = next(
            index
            for index, option in enumerate(options)
            if option.type == OptionType.PLAY
            and hand[option.index].serial == self.pad.serial
        )
        assert action == [expected]
        self.trace.append(("pad", tuple(action)))
        return observation

    def search_target(self) -> Observation:
        hand = [
            card
            for card in self.start_hand
            if card.serial not in (self.ash.serial, self.pad.serial)
        ]
        revealed = list(self.selected_cards)
        if self.variant:
            revealed = [revealed[-1], *revealed[:-1]]
        options = [
            Option(
                type=OptionType.CARD,
                area=AreaType.DECK,
                index=index,
                playerIndex=self.seat,
            )
            for index in range(len(revealed))
        ]
        select = select_data(
            SelectType.CARD,
            SelectContext.TO_HAND,
            options,
            deck=revealed,
            effect=self.pad,
        )
        observation = self.observation(
            active=self.source,
            hand=hand,
            discard=self.discard_after_ash,
            deck_count=self.start_deck + 5,
            turn_actions=self.start_actions + 3,
            select=select,
        )
        action = agent._recycle_pad_alakazam_overlay(observation)
        expected = next(
            index
            for index, option in enumerate(options)
            if revealed[option.index].serial == self.target.serial
        )
        assert action == [expected]
        self.trace.append(("search", tuple(action)))
        return observation

    def evolve_active(self) -> Observation:
        hand = [
            card
            for card in self.start_hand
            if card.serial not in (self.ash.serial, self.pad.serial)
        ] + [self.target]
        discard = self.discard_after_ash + [self.pad]
        target_index = next(
            index for index, card in enumerate(hand) if card.serial == self.target.serial
        )
        options = [
            Option(
                type=OptionType.EVOLVE,
                area=AreaType.HAND,
                index=target_index,
                playerIndex=self.seat,
                inPlayArea=AreaType.ACTIVE,
                inPlayIndex=0,
            ),
            Option(type=OptionType.END),
        ]
        select = select_data(SelectType.MAIN, SelectContext.MAIN, options)
        observation = self.observation(
            active=self.source,
            hand=hand,
            discard=discard,
            deck_count=self.start_deck + 4,
            turn_actions=self.start_actions + 4,
            select=select,
        )
        action = agent._recycle_pad_alakazam_overlay(observation)
        assert action == [0]
        self.trace.append(("evolve", tuple(action)))
        return observation

    def evolved(self, *, mutate_energy: bool = False) -> Pokemon:
        energy_cards = [self.energy]
        if mutate_energy:
            energy_cards = [make_card(agent.Basic_Psychic_Energy, 9991, self.seat)]
        return make_pokemon(
            agent.Alakazam,
            self.target.serial,
            self.seat,
            hp=130,
            max_hp=140,
            appear=True,
            energy_cards=energy_cards,
            pre_evolution=[self.abra_under, make_card(agent.Kadabra, self.source.serial, self.seat)],
        )

    def accept_draw(self, *, context_card: Card | None = None, mutate_energy: bool = False) -> Observation:
        hand = [
            card
            for card in self.start_hand
            if card.serial not in (self.ash.serial, self.pad.serial)
        ]
        discard = self.discard_after_ash + [self.pad]
        options = [Option(type=OptionType.YES), Option(type=OptionType.NO)]
        select = select_data(
            SelectType.YES_NO,
            SelectContext.ACTIVATE,
            options,
            context_card=self.target if context_card is None else context_card,
        )
        observation = self.observation(
            active=self.evolved(mutate_energy=mutate_energy),
            hand=hand,
            discard=discard,
            deck_count=self.start_deck + 4,
            turn_actions=self.start_actions + 5,
            select=select,
        )
        action = agent._recycle_pad_alakazam_overlay(observation)
        if context_card is None and not mutate_energy:
            assert action == [0]
            self.trace.append(("draw_yes", tuple(action)))
        return observation

    def resolve_draw(self, *, deck_delta: int = 3, mutate_energy: bool = False) -> Observation:
        hand = [
            card
            for card in self.start_hand
            if card.serial not in (self.ash.serial, self.pad.serial)
        ] + [
            make_card(agent.Battle_Cage, 701 + self.seat * 1000 + self.variant * 100, self.seat),
            make_card(agent.Hilda, 702 + self.seat * 1000 + self.variant * 100, self.seat),
            make_card(agent.Basic_Psychic_Energy, 703 + self.seat * 1000 + self.variant * 100, self.seat),
        ]
        discard = self.discard_after_ash + [self.pad]
        select = select_data(
            SelectType.MAIN,
            SelectContext.MAIN,
            [Option(type=OptionType.ATTACK, attackId=agent.ATTACK_POWERFUL_HAND), Option(type=OptionType.END)],
        )
        observation = self.observation(
            active=self.evolved(mutate_energy=mutate_energy),
            hand=hand,
            discard=discard,
            deck_count=self.start_deck + 4 - deck_delta,
            turn_actions=self.start_actions + 6,
            select=select,
        )
        action = agent._recycle_pad_alakazam_overlay(observation)
        if deck_delta == 3 and not mutate_energy:
            assert action is None
            assert not agent._recycle_pad_alakazam_latch
            assert agent._recycle_pad_blocked_turn == (self.turn, self.seat)
            self.trace.append(("delegate", tuple()))
        return observation

    def complete(self) -> tuple[tuple[str, tuple[int, ...]], ...]:
        self.begin()
        self.choose_to_deck()
        self.play_pad()
        self.search_target()
        self.evolve_active()
        self.accept_draw()
        self.resolve_draw()
        return tuple(self.trace)


class PositiveRouteTests(unittest.TestCase):
    def setUp(self) -> None:
        agent._clear_emergency_state(clear_cache=True)

    def test_four_multistep_routes_and_determinism(self) -> None:
        traces = {}
        for seat in (0, 1):
            for variant in (0, 1):
                with self.subTest(seat=seat, variant=variant):
                    agent._clear_emergency_state(clear_cache=True)
                    first = Route(seat, variant).complete()
                    agent._clear_emergency_state(clear_cache=True)
                    second = Route(seat, variant).complete()
                    self.assertEqual(first, second)
                    self.assertEqual([name for name, _ in first], [
                        "ash", "to_deck", "pad", "search", "evolve", "draw_yes", "delegate"
                    ])
                    traces[(seat, variant)] = first
        self.assertEqual(len(traces), 4)

    def test_completion_prevents_same_turn_refire(self) -> None:
        route = Route(0, 0)
        route.complete()
        observation, pad_option, _ = route.start_observation()
        self.assertIsNone(
            agent._start_recycle_pad_alakazam_attack_line(observation, pad_option)
        )

    def test_relaxed_prize_boundaries_complete(self) -> None:
        for own_prizes, opponent_prizes in ((2, 3), (1, 4), (4, 1), (4, 4)):
            with self.subTest(
                own_prizes=own_prizes,
                opponent_prizes=opponent_prizes,
            ):
                agent._clear_emergency_state(clear_cache=True)
                trace = Route(
                    0,
                    0,
                    own_prizes=own_prizes,
                    opponent_prizes=opponent_prizes,
                ).complete()
                self.assertEqual(trace[-1], ("delegate", tuple()))


class NegativeFailClosedTests(unittest.TestCase):
    def setUp(self) -> None:
        agent._clear_emergency_state(clear_cache=True)

    def assert_start_rejects(self, mutator) -> None:
        route = Route(0, 0)
        observation, pad_option, _ = route.start_observation()
        pad_option = mutator(route, observation, pad_option)
        self.assertIsNone(
            agent._start_recycle_pad_alakazam_attack_line(observation, pad_option)
        )
        self.assertFalse(agent._recycle_pad_alakazam_latch)

    def test_28_start_and_transition_fail_closed_cases(self) -> None:
        start_mutators = [
            lambda r, o, p: (setattr(o.current.players[0], "deckCount", 0) or p),
            lambda r, o, p: (setattr(o.current.players[1], "prize", [None] * 5) or p),
            lambda r, o, p: (setattr(o.current.players[0], "prize", [None] * 5) or p),
            lambda r, o, p: (setattr(o.current.players[1], "prize", []) or p),
            lambda r, o, p: (setattr(o.current.players[0], "prize", []) or p),
            lambda r, o, p: (setattr(o.current.players[1], "prize", [None] * 6) or p),
            lambda r, o, p: (setattr(o.current.players[0], "prize", [None] * 6) or p),
            lambda r, o, p: (setattr(o.current.players[0].active[0], "appearThisTurn", True) or p),
            lambda r, o, p: (setattr(o.current.players[0].active[0], "energyCards", []) or setattr(o.current.players[0].active[0], "energies", []) or p),
            lambda r, o, p: (setattr(o.current.players[0], "discard", [c for c in o.current.players[0].discard if c.id != agent.Alakazam]) or p),
            lambda r, o, p: (o.current.players[0].bench.append(make_pokemon(agent.Alakazam, 9901, 0)) or p),
            lambda r, o, p: (setattr(o.current.players[0], "hand", [c for c in o.current.players[0].hand if c.id != agent.Sacred_Ash]) or setattr(o.current.players[0], "handCount", 2) or p),
            lambda r, o, p: 2,
            lambda r, o, p: (setattr(o.current.players[0].bench[0], "serial", o.current.players[0].active[0].serial) or p),
            lambda r, o, p: (setattr(o.select, "context", SelectContext.TO_HAND) or p),
            lambda r, o, p: (setattr(o.current.players[0].active[0], "serial", 0) or p),
            lambda r, o, p: (agent._hilda_source_latch.update(turn=r.turn, player=0) or p),
            lambda r, o, p: (o.select.option.insert(0, copy.deepcopy(o.select.option[p])) or (p + 1)),
        ]
        for case, mutator in enumerate(start_mutators):
            with self.subTest(start_case=case):
                agent._clear_emergency_state(clear_cache=True)
                self.assert_start_rejects(mutator)
                agent._clear_emergency_state(clear_cache=True)

        transition_cases = []

        def to_deck_case(mutator):
            route = Route(0, 0)
            route.begin()
            hand = [c for c in route.start_hand if c.serial != route.ash.serial]
            options = [Option(type=OptionType.CARD, area=AreaType.DISCARD, index=i, playerIndex=0) for i in range(len(route.start_discard))]
            obs = route.observation(active=route.source, hand=hand, discard=route.start_discard, deck_count=route.start_deck, turn_actions=route.start_actions + 1, select=select_data(SelectType.CARD, SelectContext.TO_DECK, options, minimum=0, maximum=5, effect=route.ash))
            mutator(route, obs)
            return route, obs

        transition_cases.extend([
            lambda: to_deck_case(lambda r, o: setattr(o.select.effect, "serial", 9999)),
            lambda: to_deck_case(lambda r, o: setattr(o.current.players[0], "deckCount", 1)),
            lambda: to_deck_case(lambda r, o: setattr(o.current.players[0], "prize", [None] * 3)),
            lambda: to_deck_case(lambda r, o: setattr(o.select, "context", SelectContext.TO_HAND)),
            lambda: to_deck_case(lambda r, o: setattr(o.select, "option", [x for x in o.select.option if o.current.players[0].discard[x.index].id != agent.Alakazam])),
            lambda: to_deck_case(lambda r, o: setattr(o.current.players[0].bench[0], "hp", 1)),
            lambda: to_deck_case(lambda r, o: setattr(o.current.players[0].bench[0], "serial", o.current.players[0].active[0].serial)),
            lambda: to_deck_case(lambda r, o: o.current.players[0].hand.append(make_card(agent.Hilda, 9998, 0)) or setattr(o.current.players[0], "handCount", len(o.current.players[0].hand))),
            lambda: to_deck_case(lambda r, o: setattr(o.current, "turn", r.turn + 2)),
            lambda: to_deck_case(lambda r, o: setattr(o.select, "maxCount", 4)),
        ])

        for case, builder in enumerate(transition_cases):
            with self.subTest(transition_case=case):
                agent._clear_emergency_state(clear_cache=True)
                route, observation = builder()
                self.assertIsNone(agent._recycle_pad_alakazam_overlay(observation))
                self.assertFalse(agent._recycle_pad_alakazam_latch)
                self.assertEqual(
                    agent._recycle_pad_blocked_turn,
                    (observation.current.turn, observation.current.yourIndex),
                )

    def test_inter_callback_prize_shift_aborts(self) -> None:
        for shifted_player, shifted_count in ((0, 3), (1, 2)):
            with self.subTest(
                shifted_player=shifted_player,
                shifted_count=shifted_count,
            ):
                agent._clear_emergency_state(clear_cache=True)
                route = Route(0, 0, own_prizes=2, opponent_prizes=3)
                route.begin()
                hand = [
                    card
                    for card in route.start_hand
                    if card.serial != route.ash.serial
                ]
                options = [
                    Option(
                        type=OptionType.CARD,
                        area=AreaType.DISCARD,
                        index=index,
                        playerIndex=0,
                    )
                    for index in range(len(route.start_discard))
                ]
                observation = route.observation(
                    active=route.source,
                    hand=hand,
                    discard=route.start_discard,
                    deck_count=route.start_deck,
                    turn_actions=route.start_actions + 1,
                    select=select_data(
                        SelectType.CARD,
                        SelectContext.TO_DECK,
                        options,
                        minimum=0,
                        maximum=5,
                        effect=route.ash,
                    ),
                )
                observation.current.players[shifted_player].prize = (
                    [None] * shifted_count
                )
                self.assertIsNone(
                    agent._recycle_pad_alakazam_overlay(observation)
                )
                self.assertFalse(agent._recycle_pad_alakazam_latch)
                self.assertEqual(
                    agent._recycle_pad_blocked_turn,
                    (route.turn, route.seat),
                )


class ProvenanceAndRuntimeTests(unittest.TestCase):
    def test_exact_parent_and_deck_provenance(self) -> None:
        parent = REPOSITORY / "autonomous_gold_20260715" / "packages" / "alakazam_parent_end_strict_prize_lead_retreat_ko_bridge_v3_20260718" / "staging_clean"
        self.assertEqual(
            hashlib.sha256((parent / "main.py").read_bytes()).hexdigest().upper(),
            "49E954F53E043CD79D928DFB2340CCB5D85A17F33CCB824C871CCE153C0C9C95",
        )
        expected_deck_hash = "7B413177E5077777F2178143839C0155B03B92BBC8B3A6607621A7D43F351141"
        self.assertEqual(hashlib.sha256((parent / "deck.csv").read_bytes()).hexdigest().upper(), expected_deck_hash)
        self.assertEqual(hashlib.sha256((CANDIDATE / "deck.csv").read_bytes()).hexdigest().upper(), expected_deck_hash)
        deck = [int(row) for row in (CANDIDATE / "deck.csv").read_text().splitlines() if row.strip()]
        self.assertEqual(len(deck), 60)
        self.assertEqual(sum(bool(agent.card_table[card_id].aceSpec) for card_id in deck), 1)

    def test_standard_runtime_wrapper_imports(self) -> None:
        wrapper = CANDIDATE / "runtime" / "main.py"
        specification = importlib.util.spec_from_file_location("candidate_runtime_test", wrapper)
        self.assertIsNotNone(specification)
        self.assertIsNotNone(specification.loader)
        module = importlib.util.module_from_spec(specification)
        specification.loader.exec_module(module)
        self.assertTrue(callable(module.agent))


if __name__ == "__main__":
    unittest.main(verbosity=2)
