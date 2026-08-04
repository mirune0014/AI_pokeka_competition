from mega_lucario_rule_agent.card_meta import ATTACK_META_BY_ID
from mega_lucario_rule_agent.card_meta import DECK_COUNTER
from mega_lucario_rule_agent.main import AgentRuntime
from mega_lucario_rule_agent.public_effects import (
    EFFECT_BINDINGS,
    EntryKind,
    build_public_effect_registry,
)
from mega_lucario_rule_agent.state_view import (
    AreaType,
    OptionType,
    SelectContext,
)
from mega_lucario_rule_agent.transactions import ResumeResult, ResumeStatus


def card(card_id, serial, player=0):
    return {"id": card_id, "serial": serial, "playerIndex": player}


def pokemon(
    card_id,
    serial,
    *,
    player=0,
    hp=100,
    max_hp=None,
    energy_cards=(),
    pre=(),
):
    maximum = hp if max_hp is None else max_hp
    return {
        "id": card_id,
        "serial": serial,
        "playerIndex": player,
        "hp": hp,
        "maxHp": maximum,
        "appearThisTurn": False,
        "energies": [6 for _ in energy_cards],
        "energyCards": [
            card(card_id_value, serial_value, player)
            for card_id_value, serial_value in energy_cards
        ],
        "tools": [],
        "preEvolution": list(pre),
    }


def observation(
    options,
    *,
    context=SelectContext.MAIN,
    min_count=1,
    max_count=1,
    own_active=None,
    own_bench=(),
    opponent_active=None,
    hand=(),
    turn=3,
):
    own_active_values = [] if own_active is None else [own_active]
    target = opponent_active or pokemon(676, 110, player=1, hp=110)
    return {
        "select": {
            "type": 0,
            "context": int(context),
            "minCount": min_count,
            "maxCount": max_count,
            "remainDamageCounter": 0,
            "remainEnergyCost": 0,
            "option": list(options),
            "deck": None,
            "contextCard": None,
            "effect": None,
        },
        "logs": [],
        "current": {
            "turn": turn,
            "turnActionCount": 0,
            "yourIndex": 0,
            "firstPlayer": 0,
            "supporterPlayed": False,
            "stadiumPlayed": False,
            "energyAttached": False,
            "retreated": False,
            "result": -1,
            "stadium": [],
            "looking": None,
            "players": [
                {
                    "active": own_active_values,
                    "bench": list(own_bench),
                    "benchMax": 5,
                    "deckCount": 40,
                    "discard": [],
                    "prize": [None] * 6,
                    "handCount": len(hand),
                    "hand": list(hand),
                    "poisoned": False,
                    "burned": False,
                    "asleep": False,
                    "paralyzed": False,
                    "confused": False,
                },
                {
                    "active": [target],
                    "bench": [],
                    "benchMax": 5,
                    "deckCount": 40,
                    "discard": [],
                    "prize": [None] * 6,
                    "handCount": 5,
                    "hand": None,
                    "poisoned": False,
                    "burned": False,
                    "asleep": False,
                    "paralyzed": False,
                    "confused": False,
                },
            ],
        },
    }


def empty_registry():
    return build_public_effect_registry((), ())


def aura_registry():
    binding = next(
        row
        for row in EFFECT_BINDINGS
        if row.entry_kind is EntryKind.ATTACK and row.entry_id == 982
    )
    cards = (
        {
            "cardId": 6,
            "cardType": 5,
            "name": "Basic Fighting Energy",
            "hp": 0,
            "energyType": 6,
            "weakness": None,
            "resistance": None,
            "basic": False,
            "stage1": False,
            "stage2": False,
            "ex": False,
            "megaEx": False,
            "tera": False,
            "attacks": [],
            "skills": [],
        },
        {
            "cardId": 678,
            "cardType": 0,
            "name": binding.card_name,
            "hp": 340,
            "energyType": 6,
            "weakness": None,
            "resistance": None,
            "basic": False,
            "stage1": True,
            "stage2": False,
            "ex": True,
            "megaEx": True,
            "tera": False,
            "attacks": [982],
            "skills": [],
        },
        {
            "cardId": 676,
            "cardType": 0,
            "name": "Solrock",
            "hp": 110,
            "energyType": 6,
            "weakness": None,
            "resistance": None,
            "basic": True,
            "stage1": False,
            "stage2": False,
            "ex": False,
            "megaEx": False,
            "tera": False,
            "attacks": [],
            "skills": [],
        },
    )
    attacks = (
        {
            "attackId": 982,
            "name": binding.entry_name,
            "text": ATTACK_META_BY_ID[982].effect_text,
            "damage": ATTACK_META_BY_ID[982].printed_damage,
            "energies": list(binding.energy_cost),
        },
    )
    return build_public_effect_registry(cards, attacks)


def test_deck_callback_returns_exact_fixed_deck_and_resets_runtime():
    runtime = AgentRuntime(registry=empty_registry())
    store_before = runtime.transactions
    epoch_before = runtime.game_epoch

    deck = runtime.act({"select": None})

    assert len(deck) == 60
    assert {card_id: deck.count(card_id) for card_id in set(deck)} == dict(
        DECK_COUNTER
    )
    assert runtime.game_epoch == epoch_before + 1
    assert runtime.transactions is not store_before
    assert runtime.setup_active_choice is None


def test_runtime_connects_setup_first_and_active_priority():
    runtime = AgentRuntime(registry=empty_registry())
    choose_first = observation(
        [
            {"type": int(OptionType.NO)},
            {"type": int(OptionType.YES)},
        ],
        context=SelectContext.IS_FIRST,
        own_active=None,
    )
    assert runtime.act(choose_first) == [1]

    hand = (
        card(677, 40),
        card(676, 42),
        card(676, 41),
        card(675, 43),
        card(673, 44),
        card(677, 45),
    )
    setup_active = observation(
        [
            {
                "type": int(OptionType.CARD),
                "area": int(AreaType.HAND),
                "index": index,
                "playerIndex": 0,
            }
            for index in range(len(hand))
        ],
        context=SelectContext.SETUP_ACTIVE_POKEMON,
        own_active=None,
        hand=hand,
    )
    assert runtime.act(setup_active) == [2]
    assert runtime.setup_active_choice.card_id == 676
    assert runtime.setup_active_choice.card_serial == 41

    intermediate = observation(
        [{"type": int(OptionType.NUMBER), "number": 1}],
        context=SelectContext.DRAW_COUNT,
        min_count=1,
        max_count=1,
        own_active=None,
        hand=hand,
    )
    intermediate["current"]["players"][0]["active"] = [None]
    intermediate["current"]["players"][1]["active"] = [None]
    assert runtime.act(intermediate) == [0]
    assert runtime.setup_active_choice.card_serial == 41

    bench_hand = (
        card(677, 40),
        card(676, 42),
        card(675, 43),
        card(673, 44),
        card(677, 45),
    )
    setup_bench = observation(
        [
            {
                "type": int(OptionType.CARD),
                "area": int(AreaType.HAND),
                "index": index,
                "playerIndex": 0,
            }
            for index in range(len(bench_hand))
        ],
        context=SelectContext.SETUP_BENCH_POKEMON,
        min_count=0,
        max_count=5,
        own_active=None,
        hand=bench_hand,
    )
    setup_bench["current"]["players"][0]["active"] = [None]
    setup_bench["current"]["players"][1]["active"] = [None]

    assert runtime.act(setup_bench) == [0, 2, 3]
    assert runtime.setup_active_choice.card_id == 676

    runtime.act({"select": None})
    assert runtime.setup_active_choice is None


def test_stable_main_without_attack_uses_checked_pass():
    runtime = AgentRuntime(registry=empty_registry())
    obs = observation(
        [{"type": int(OptionType.END)}],
        own_active=pokemon(676, 10, hp=110),
    )

    assert runtime.act(obs) == [0]
    assert not runtime.runtime_fault_latched


def test_runtime_uses_checked_registry_for_certified_aura_attack():
    runtime = AgentRuntime(registry=aura_registry())
    riolu = card(677, 9)
    active = pokemon(
        678,
        10,
        hp=340,
        max_hp=340,
        energy_cards=((6, 51),),
        pre=(riolu,),
    )
    obs = observation(
        [{"type": int(OptionType.ATTACK), "attackId": 982}],
        own_active=active,
        opponent_active=pokemon(676, 110, player=1, hp=110),
    )

    assert runtime.act(obs) == [0]
    history = runtime.history.snapshot(0, 3)
    assert len(history.last_attack_by_lineage) == 1
    assert history.last_attack_by_lineage[0].attack_id == 982
    assert not runtime.runtime_fault_latched


def test_malformed_state_latches_fault_and_uses_deterministic_raw_attack():
    runtime = AgentRuntime(registry=empty_registry())
    malformed = {
        "select": {
            "type": 0,
            "context": int(SelectContext.MAIN),
            "minCount": 1,
            "maxCount": 1,
            "option": [
                {"type": int(OptionType.END)},
                {"type": int(OptionType.ATTACK), "attackId": 982},
            ],
        },
        "current": {"turn": 1, "result": -1},
    }

    assert runtime.act(malformed) == [1]
    assert runtime.act(malformed) == [1]
    assert runtime.runtime_fault_latched


def test_transaction_reissue_precedes_setup_rule():
    class DuplicateResumeStore:
        owner = None

        @staticmethod
        def resume(state, legal_options):
            return ResumeResult(
                ResumeStatus.DUPLICATE_REISSUE,
                None,
                (0,),
                None,
                (),
            )

    runtime = AgentRuntime(registry=empty_registry())
    runtime._transactions = DuplicateResumeStore()
    choose_first = observation(
        [
            {"type": int(OptionType.NO)},
            {"type": int(OptionType.YES)},
        ],
        context=SelectContext.IS_FIRST,
        own_active=None,
    )

    assert runtime.act(choose_first) == [0]


def test_turn_regression_replaces_per_game_state():
    runtime = AgentRuntime(registry=empty_registry())
    first = observation(
        [{"type": int(OptionType.END)}],
        own_active=pokemon(676, 10, hp=110),
        turn=5,
    )
    second = observation(
        [{"type": int(OptionType.END)}],
        own_active=pokemon(676, 11, hp=110),
        turn=1,
    )
    epoch_before = runtime.game_epoch
    store_before = runtime.transactions

    assert runtime.act(first) == [0]
    assert runtime.act(second) == [0]
    assert runtime.game_epoch == epoch_before + 1
    assert runtime.transactions is not store_before
