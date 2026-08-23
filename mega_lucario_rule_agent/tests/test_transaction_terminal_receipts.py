from dataclasses import replace

import pytest

from mega_lucario_rule_agent.resource_ledger import (
    prove_deck_availability_from_state,
)
from mega_lucario_rule_agent.state_view import (
    ActionSpec,
    AreaType,
    LogType,
    OptionType,
    PhysicalRef,
    PlayerView,
    PokemonView,
    PublicReceiptEvent,
    PublicState,
    SelectContext,
    SelectType,
    SemanticOption,
    SemanticOptionKey,
)
from mega_lucario_rule_agent.transactions import (
    ResumeStatus,
    StartStatus,
    TerminalReceiptProfile,
    TransactionStore,
    build_aura_jab_plan,
    build_boss_gust_plan,
    build_deck_search_plan,
    build_hariyama_gust_plan,
    build_lunar_cycle_plan,
    build_poke_pad_core_search_plan,
    build_switch_plan,
    build_ultra_ball_plan,
    build_wally_plan,
)


PROOF_DIGEST = "0" * 64


def _ref(card_id, serial, owner, zone, lineage=None):
    return PhysicalRef(
        card_id,
        serial,
        owner,
        int(zone),
        serial if lineage is None else lineage,
    )


def _pokemon(card_id, serial, owner, zone, *, hp=100, lineage=None, energies=()):
    return PokemonView(
        ref=_ref(card_id, serial, owner, zone, lineage),
        hp=hp,
        max_hp=100,
        appear_this_turn=False,
        energy_types=tuple(1 for _ in energies),
        energy_refs=tuple(energies),
        tool_refs=(),
        pre_evolution_refs=(),
    )


def _player(index, active, bench=(), hand=(), discard=(), deck_count=40):
    return PlayerView(
        index=index,
        active=(active,),
        active_slot_count=1,
        hidden_active_count=0,
        bench=tuple(bench),
        hand_refs=tuple(hand),
        discard_refs=tuple(discard),
        prize_refs=(),
        prize_count=6,
        deck_count=deck_count,
        hand_count=len(hand) if index == 0 else 5,
        bench_max=5,
        poisoned=False,
        burned=False,
        asleep=False,
        paralyzed=False,
        confused=False,
    )


def _state(own, opponent, *, turn=5, game_epoch=9, events=()):
    return PublicState(
        game_epoch=game_epoch,
        seat=0,
        turn=turn,
        turn_action_count=8,
        first_player=0,
        supporter_played=False,
        stadium_played=False,
        energy_attached=False,
        retreated=False,
        result=-1,
        own=own,
        opponent=opponent,
        stadium_refs=(),
        looking_refs=(),
        select_context=int(SelectContext.MAIN),
        min_count=1,
        max_count=1,
        effect_ref=None,
        context_ref=None,
        select_type=int(SelectType.MAIN),
        looking_open=False,
        select_deck_open=False,
        remaining_damage_counter=0,
        remaining_energy_cost=0,
        receipt_events=tuple(events),
    )


def _event(log_type, *, owner=0, ref_value=None, **changes):
    values = {
        "log_type": int(log_type),
        "player_index": owner,
        "card_id": None if ref_value is None else ref_value.card_id,
        "serial": None if ref_value is None else ref_value.serial,
        "from_area": None,
        "to_area": None,
        "card_id_target": None,
        "serial_target": None,
        "serial_bench": None,
        "attack_id": None,
        "value": None,
    }
    values.update(changes)
    return PublicReceiptEvent(**values)


def _action(option_type, source, *, target=None, attack_id=None):
    return ActionSpec.single(
        SemanticOptionKey(
            option_type=int(option_type),
            player_index=source.owner,
            card_id=source.card_id,
            card_serial=source.serial,
            source_zone=source.zone,
            source_lineage_serial=(
                source.lineage_serial
                if source.zone in (int(AreaType.ACTIVE), int(AreaType.BENCH))
                else None
            ),
            target_zone=None if target is None else target.zone,
            target_lineage_serial=(
                None if target is None else target.lineage_serial
            ),
            attack_id=attack_id,
        )
    )


@pytest.fixture
def receipt_cases():
    refs = {
        "poke": _ref(1152, 100, 0, AreaType.HAND),
        "gong": _ref(1142, 101, 0, AreaType.HAND),
        "lunar_cost": _ref(6, 102, 0, AreaType.HAND),
        "ultra": _ref(1121, 103, 0, AreaType.HAND),
        "cost1": _ref(1141, 104, 0, AreaType.HAND),
        "cost2": _ref(1159, 105, 0, AreaType.HAND),
        "boss": _ref(1182, 106, 0, AreaType.HAND),
        "hari_source": _ref(674, 107, 0, AreaType.HAND),
        "wally": _ref(1229, 108, 0, AreaType.HAND),
        "switch": _ref(1123, 109, 0, AreaType.HAND),
        "aura1": _ref(6, 110, 0, AreaType.DISCARD),
        "aura2": _ref(6, 111, 0, AreaType.DISCARD),
        "w_energy1": _ref(6, 112, 0, AreaType.ENERGY),
        "w_energy2": _ref(6, 113, 0, AreaType.ENERGY),
        "search_target": _ref(6, 900, 0, AreaType.DECK),
    }
    mega = _pokemon(678, 10, 0, AreaType.ACTIVE)
    lunar = _pokemon(675, 11, 0, AreaType.BENCH)
    makuhita = _pokemon(673, 12, 0, AreaType.BENCH)
    wally_target = _pokemon(
        674,
        13,
        0,
        AreaType.BENCH,
        hp=70,
        energies=(refs["w_energy1"], refs["w_energy2"]),
    )
    opponent_active = _pokemon(999, 20, 1, AreaType.ACTIVE)
    gust_target = _pokemon(998, 21, 1, AreaType.BENCH)
    own = _player(
        0,
        mega,
        (lunar, makuhita, wally_target),
        tuple(
            refs[name]
            for name in (
                "poke",
                "gong",
                "lunar_cost",
                "ultra",
                "cost1",
                "cost2",
                "boss",
                "hari_source",
                "wally",
                "switch",
            )
        ),
        (refs["aura1"], refs["aura2"]),
    )
    opponent = _player(1, opponent_active, (gust_target,))
    base = _state(own, opponent)
    energy_proof = prove_deck_availability_from_state(
        base, (6,), required_count=1
    )
    plans = {
        TerminalReceiptProfile.POKE_PAD_SEARCH: build_poke_pad_core_search_plan(
            base,
            refs["poke"],
            _action(OptionType.PLAY, refs["poke"]),
            ((6,),),
            energy_proof,
            PROOF_DIGEST,
        ),
        TerminalReceiptProfile.FIGHTING_GONG_SEARCH: build_deck_search_plan(
            base,
            refs["gong"],
            _action(OptionType.PLAY, refs["gong"]),
            ((6,),),
            energy_proof,
            PROOF_DIGEST,
        ),
        TerminalReceiptProfile.LUNAR_CYCLE: build_lunar_cycle_plan(
            base,
            lunar.ref,
            refs["lunar_cost"],
            _action(OptionType.SKILL, lunar.ref),
            PROOF_DIGEST,
        ),
        TerminalReceiptProfile.AURA_JAB: build_aura_jab_plan(
            base,
            _action(OptionType.ATTACK, mega.ref, attack_id=982),
            (refs["aura1"], refs["aura2"]),
            lunar.ref,
            PROOF_DIGEST,
        ),
        TerminalReceiptProfile.ULTRA_BALL: build_ultra_ball_plan(
            base,
            refs["ultra"],
            (refs["cost1"], refs["cost2"]),
            _action(OptionType.PLAY, refs["ultra"]),
            ((6,),),
            energy_proof,
            PROOF_DIGEST,
        ),
        TerminalReceiptProfile.BOSS_GUST: build_boss_gust_plan(
            base,
            refs["boss"],
            gust_target.ref,
            _action(OptionType.PLAY, refs["boss"]),
            PROOF_DIGEST,
        ),
        TerminalReceiptProfile.HARIYAMA_GUST: build_hariyama_gust_plan(
            base,
            refs["hari_source"],
            gust_target.ref,
            _action(OptionType.EVOLVE, refs["hari_source"], target=makuhita.ref),
            PROOF_DIGEST,
        ),
        TerminalReceiptProfile.WALLY_REBOOT: build_wally_plan(
            base,
            refs["wally"],
            wally_target.ref,
            refs["w_energy1"],
            _action(OptionType.PLAY, refs["wally"]),
            PROOF_DIGEST,
        ),
        TerminalReceiptProfile.SWITCH: build_switch_plan(
            base,
            refs["switch"],
            lunar.ref,
            _action(OptionType.PLAY, refs["switch"]),
            PROOF_DIGEST,
        ),
    }
    return base, refs, plans


def _remove_identity(refs, removed):
    return tuple(value for value in refs if value != removed)


def _positive_state(profile, base, refs, plan):
    own = base.own
    opponent = base.opponent
    events = []
    search_profiles = {
        TerminalReceiptProfile.POKE_PAD_SEARCH,
        TerminalReceiptProfile.FIGHTING_GONG_SEARCH,
        TerminalReceiptProfile.ULTRA_BALL,
    }
    if profile in search_profiles:
        source = plan.source_ref
        costs = plan.reserved_refs
        target = refs["search_target"]
        hand = _remove_identity(own.hand_refs, source)
        for cost in costs:
            hand = _remove_identity(hand, cost)
        hand += (_ref(target.card_id, target.serial, 0, AreaType.HAND),)
        own = replace(
            own,
            hand_refs=hand,
            hand_count=len(hand),
            discard_refs=own.discard_refs
            + (source,)
            + tuple(costs),
            deck_count=39,
        )
        events = [
            _event(LogType.PLAY, ref_value=source),
            _event(
                LogType.MOVE_CARD,
                ref_value=target,
                from_area=int(AreaType.DECK),
                to_area=int(AreaType.HAND),
            ),
        ]
    elif profile == TerminalReceiptProfile.LUNAR_CYCLE:
        cost = refs["lunar_cost"]
        hand = _remove_identity(own.hand_refs, cost)
        own = replace(
            own,
            hand_refs=hand,
            hand_count=len(hand) + 3,
            discard_refs=own.discard_refs + (cost,),
            deck_count=37,
        )
        events = [
            _event(
                LogType.MOVE_CARD,
                ref_value=cost,
                from_area=int(AreaType.HAND),
                to_area=int(AreaType.DISCARD),
            )
        ] + [
            _event(LogType.DRAW, ref_value=_ref(6, 920 + index, 0, AreaType.HAND))
            for index in range(3)
        ]
    elif profile == TerminalReceiptProfile.AURA_JAB:
        target = own.bench[0]
        attached = tuple(plan.reserved_refs)
        target = replace(target, energy_refs=attached, energy_types=(1, 1))
        own = replace(
            own,
            bench=(target,) + own.bench[1:],
            discard_refs=tuple(
                value for value in own.discard_refs if value not in attached
            ),
        )
        events = [
            _event(LogType.ATTACK, ref_value=plan.source_ref, attack_id=982)
        ] + [
            _event(
                LogType.ATTACH,
                ref_value=energy,
                serial_target=target.ref.serial,
                card_id_target=target.ref.card_id,
            )
            for energy in attached
        ]
    elif profile == TerminalReceiptProfile.BOSS_GUST:
        source = plan.source_ref
        hand = _remove_identity(own.hand_refs, source)
        own = replace(
            own,
            hand_refs=hand,
            hand_count=len(hand),
            discard_refs=own.discard_refs + (source,),
        )
        target = opponent.bench[0]
        opponent = replace(
            opponent,
            active=(replace(target, ref=replace(target.ref, zone=int(AreaType.ACTIVE))),),
            bench=(replace(opponent.active[0], ref=replace(opponent.active[0].ref, zone=int(AreaType.BENCH))),),
        )
        events = [
            _event(LogType.PLAY, ref_value=source),
            _event(LogType.SWITCH, owner=1, serial_bench=target.ref.serial),
        ]
    elif profile == TerminalReceiptProfile.HARIYAMA_GUST:
        source = plan.source_ref
        hand = _remove_identity(own.hand_refs, source)
        evolved = _pokemon(674, source.serial, 0, AreaType.BENCH, lineage=12)
        own = replace(
            own,
            hand_refs=hand,
            hand_count=len(hand),
            bench=(own.bench[0], evolved, own.bench[2]),
        )
        target = opponent.bench[0]
        opponent = replace(
            opponent,
            active=(replace(target, ref=replace(target.ref, zone=int(AreaType.ACTIVE))),),
            bench=(replace(opponent.active[0], ref=replace(opponent.active[0].ref, zone=int(AreaType.BENCH))),),
        )
        events = [
            _event(LogType.EVOLVE, ref_value=source, serial_target=12),
            _event(LogType.SWITCH, owner=1, serial_bench=target.ref.serial),
        ]
    elif profile == TerminalReceiptProfile.WALLY_REBOOT:
        source = plan.source_ref
        chosen, other = refs["w_energy1"], refs["w_energy2"]
        hand = _remove_identity(own.hand_refs, source) + (
            _ref(other.card_id, other.serial, 0, AreaType.HAND),
        )
        healed = replace(
            own.bench[2],
            hp=100,
            energy_refs=(_ref(chosen.card_id, chosen.serial, 0, AreaType.ENERGY),),
            energy_types=(1,),
        )
        own = replace(
            own,
            hand_refs=hand,
            hand_count=len(hand),
            discard_refs=own.discard_refs + (source,),
            bench=own.bench[:2] + (healed,),
        )
        events = [
            _event(LogType.PLAY, ref_value=source),
            _event(LogType.HP_CHANGE, ref_value=plan.target_refs[0], value=30),
            _event(LogType.MOVE_CARD, ref_value=chosen, from_area=int(AreaType.ENERGY), to_area=int(AreaType.HAND)),
            _event(LogType.MOVE_CARD, ref_value=other, from_area=int(AreaType.ENERGY), to_area=int(AreaType.HAND)),
            _event(LogType.ATTACH, ref_value=chosen, serial_target=plan.target_refs[0].serial),
        ]
    else:
        source = plan.source_ref
        hand = _remove_identity(own.hand_refs, source)
        target = own.bench[0]
        old_active = own.active[0]
        own = replace(
            own,
            hand_refs=hand,
            hand_count=len(hand),
            discard_refs=own.discard_refs + (source,),
            active=(replace(target, ref=replace(target.ref, zone=int(AreaType.ACTIVE))),),
            bench=(replace(old_active, ref=replace(old_active.ref, zone=int(AreaType.BENCH))),) + own.bench[1:],
        )
        events = [
            _event(LogType.PLAY, ref_value=source),
            _event(LogType.SWITCH, serial_bench=target.ref.serial),
        ]
    return _state(own, opponent, events=events)


def _ready_store(profile, base, refs, plan):
    store = TransactionStore()
    initiation_key = plan.initiation.action_spec.choices[0]
    started = store.start(plan, base, (SemanticOption(0, initiation_key),))
    assert started.status == StartStatus.STARTED
    action_specs = started.owner.semantic_action_specs
    if profile in {
        TerminalReceiptProfile.POKE_PAD_SEARCH,
        TerminalReceiptProfile.FIGHTING_GONG_SEARCH,
        TerminalReceiptProfile.ULTRA_BALL,
    }:
        target = refs["search_target"]
        action_specs += (
            ActionSpec.single(
                SemanticOptionKey(
                    option_type=int(OptionType.CARD),
                    player_index=0,
                    card_id=target.card_id,
                    card_serial=target.serial,
                    source_zone=int(AreaType.DECK),
                )
            ),
        )
    store._owner = replace(
        started.owner,
        step_index=len(plan.steps) - 1,
        semantic_action_specs=action_specs,
    )
    return store


def test_all_nine_builders_declare_distinct_exact_terminal_profiles(receipt_cases):
    _, _, plans = receipt_cases
    assert set(plans) == set(TerminalReceiptProfile)
    assert all(plan.terminal_receipt.profile == profile for profile, plan in plans.items())
    assert all(plan.initiation.irreversible_on_emit for plan in plans.values())
    assert all(plan.terminal_receipt.missing_callback_is_fault for plan in plans.values())
    assert all(
        plan.terminal_receipt.irreversible_fault_on_missing_receipt
        for plan in plans.values()
    )
    assert {
        profile
        for profile, plan in plans.items()
        if plan.terminal_receipt.allow_turn_transition
    } == {TerminalReceiptProfile.AURA_JAB}


@pytest.mark.parametrize("profile", tuple(TerminalReceiptProfile))
def test_exact_terminal_receipt_completes_each_profile(receipt_cases, profile):
    base, refs, plans = receipt_cases
    plan = plans[profile]
    store = _ready_store(profile, base, refs, plan)
    result = store.resume(_positive_state(profile, base, refs, plan), ())
    assert result.status == ResumeStatus.COMPLETED
    assert not store.has_owner
    assert not store.run_fault_latched


@pytest.mark.parametrize("profile", tuple(TerminalReceiptProfile))
def test_one_decisive_missing_receipt_faults_each_profile(receipt_cases, profile):
    base, refs, plans = receipt_cases
    plan = plans[profile]
    post = _positive_state(profile, base, refs, plan)
    post = replace(post, receipt_events=post.receipt_events[:-1])
    store = _ready_store(profile, base, refs, plan)
    result = store.resume(post, ())
    assert result.status == ResumeStatus.IRREVERSIBLE_FAULT
    assert store.run_fault_latched


@pytest.mark.parametrize("profile", tuple(TerminalReceiptProfile))
def test_only_complete_aura_may_finish_after_turn_transition(receipt_cases, profile):
    base, refs, plans = receipt_cases
    plan = plans[profile]
    post = replace(_positive_state(profile, base, refs, plan), turn=6)
    store = _ready_store(profile, base, refs, plan)
    result = store.resume(post, ())
    expected = (
        ResumeStatus.COMPLETED
        if profile == TerminalReceiptProfile.AURA_JAB
        else ResumeStatus.IRREVERSIBLE_FAULT
    )
    assert result.status == expected
    assert store.run_fault_latched == (profile != TerminalReceiptProfile.AURA_JAB)


@pytest.mark.parametrize("profile", tuple(TerminalReceiptProfile))
def test_game_epoch_transition_faults_every_profile(receipt_cases, profile):
    base, refs, plans = receipt_cases
    plan = plans[profile]
    post = replace(_positive_state(profile, base, refs, plan), game_epoch=10)
    store = _ready_store(profile, base, refs, plan)
    result = store.resume(post, ())
    assert result.status == ResumeStatus.IRREVERSIBLE_FAULT
    assert store.run_fault_latched


def test_incomplete_aura_turn_transition_and_missing_attach_fault(receipt_cases):
    base, refs, plans = receipt_cases
    profile = TerminalReceiptProfile.AURA_JAB
    plan = plans[profile]
    post = _positive_state(profile, base, refs, plan)
    post = replace(post, turn=6, receipt_events=post.receipt_events[:-1])
    store = _ready_store(profile, base, refs, plan)
    result = store.resume(post, ())
    assert result.status == ResumeStatus.IRREVERSIBLE_FAULT
    assert store.run_fault_latched


def _wally_return_state(base, refs, plan, *, events):
    source = plan.source_ref
    energy1 = refs["w_energy1"]
    energy2 = refs["w_energy2"]
    hand = _remove_identity(base.own.hand_refs, source) + (
        _ref(6, energy1.serial, 0, AreaType.HAND),
        _ref(6, energy2.serial, 0, AreaType.HAND),
    )
    healed = replace(
        base.own.bench[2],
        hp=100,
        energy_refs=(),
        energy_types=(),
    )
    own = replace(
        base.own,
        hand_refs=hand,
        hand_count=len(hand),
        discard_refs=base.own.discard_refs + (source,),
        bench=base.own.bench[:2] + (healed,),
    )
    return _state(own, base.opponent, events=events)


def test_wally_never_issues_reattach_before_exact_return_receipt(receipt_cases):
    base, refs, plans = receipt_cases
    plan = plans[TerminalReceiptProfile.WALLY_REBOOT]
    store = TransactionStore()
    key = plan.initiation.action_spec.choices[0]
    started = store.start(plan, base, (SemanticOption(0, key),))
    store._owner = replace(started.owner, step_index=0)

    missing = store.resume(_wally_return_state(base, refs, plan, events=()), ())
    assert missing.status == ResumeStatus.IRREVERSIBLE_FAULT
    assert "WALLY_REATTACH_BEFORE_RETURN_RECEIPT" in missing.reasons

    exact_events = (
        _event(LogType.PLAY, ref_value=plan.source_ref),
        _event(LogType.HP_CHANGE, ref_value=plan.target_refs[0], value=30),
        _event(
            LogType.MOVE_CARD,
            ref_value=refs["w_energy1"],
            from_area=int(AreaType.ENERGY),
            to_area=int(AreaType.HAND),
        ),
        _event(
            LogType.MOVE_CARD,
            ref_value=refs["w_energy2"],
            from_area=int(AreaType.ENERGY),
            to_area=int(AreaType.HAND),
        ),
    )
    exact_store = TransactionStore()
    started = exact_store.start(plan, base, (SemanticOption(0, key),))
    exact_store._owner = replace(started.owner, step_index=0)
    reattach_key = plan.steps[-1].action_spec.choices[0]
    issued = exact_store.resume(
        _wally_return_state(base, refs, plan, events=exact_events),
        (SemanticOption(0, reattach_key),),
    )
    assert issued.status == ResumeStatus.ADVANCED_ISSUE
    assert issued.action_spec == plan.steps[-1].action_spec


def _aura_next_target_state(base, refs, plan, *, include_attach, context_energy=None):
    energy = refs["aura1"]
    context_energy = energy if context_energy is None else context_energy
    target = base.own.bench[0]
    if include_attach:
        target = replace(target, energy_refs=(energy,), energy_types=(1,))
    own = replace(
        base.own,
        bench=(target,) + base.own.bench[1:],
        discard_refs=tuple(
            value
            for value in base.own.discard_refs
            if not (include_attach and value == energy)
        ),
    )
    events = (
        _event(LogType.ATTACK, ref_value=plan.source_ref, attack_id=982),
    )
    if include_attach:
        events += (
            _event(
                LogType.ATTACH,
                ref_value=energy,
                serial_target=plan.target_refs[0].serial,
            ),
        )
    return replace(
        _state(own, base.opponent, events=events),
        select_type=int(SelectType.CARD),
        select_context=int(SelectContext.ATTACH_FROM),
        effect_ref=plan.source_ref,
        context_ref=context_energy,
    )


def test_aura_requires_preceding_attach_before_next_target_callback(receipt_cases):
    base, refs, plans = receipt_cases
    plan = plans[TerminalReceiptProfile.AURA_JAB]
    key = plan.initiation.action_spec.choices[0]

    missing_store = TransactionStore()
    started = missing_store.start(plan, base, (SemanticOption(0, key),))
    missing_store._owner = replace(started.owner, step_index=1)
    missing = missing_store.resume(
        _aura_next_target_state(
            base, refs, plan, include_attach=False, context_energy=refs["aura2"]
        ),
        (SemanticOption(0, plan.steps[2].action_spec.choices[0]),),
    )
    assert missing.status == ResumeStatus.IRREVERSIBLE_FAULT
    assert "AURA_PRECEDING_ATTACH_RECEIPT_MISSING" in missing.reasons

    exact_store = TransactionStore()
    started = exact_store.start(plan, base, (SemanticOption(0, key),))
    exact_store._owner = replace(started.owner, step_index=1)
    issued = exact_store.resume(
        _aura_next_target_state(
            base, refs, plan, include_attach=True, context_energy=refs["aura2"]
        ),
        (SemanticOption(0, plan.steps[2].action_spec.choices[0]),),
    )
    assert issued.status == ResumeStatus.ADVANCED_ISSUE
