# Frozen implementation specification — integrated override admissibility gate v1

Sol-Ultra verdict: **AUTHORIZE implementation**.

Implement exactly one coherent fail-closed rule. Every affected change rejects
an integrated override whose exact public successor is either strategically
uncertified or board-terminal. Add no positive tactical heuristic, replay ID,
opponent identity, deck change, or inherited-policy repair.

## Parent and destination

- Direct parent: `candidates/alakazam_integrated_domain_turn_planner_v1`.
- Parent `main.py` SHA-256:
  `93E2567F4352EE4C4FCEEB3D32B954119F3DC4E8F96DF5498317E781C5804086`.
- Embedded cumulative fallback SHA-256:
  `65527AEE74AED600B94C4A555BE9464A48E53E118C9FD674DB6403208706325D`.
- Destination:
  `candidates/alakazam_integrated_override_admissibility_gate_v1`.
- Implementation evidence destination:
  `implementation/alakazam_integrated_override_admissibility_gate_v1`.
- Deck remains SHA-256:
  `A7B6C7972915D09F6314C42633AA89D82B55DDF0A7199F7138E681FA52516529`,
  legal 60, Handheld Fan `1161 x2`, Lucky Helmet `1156 x1`.

The parent directory is read-only. All inherited retreat, promotion,
attachment, Enhanced Hammer, matchup, opening, Boss, terminal, Fan, and clock
behavior remains unchanged.

## Exact predicate

Apply this predicate only at the integrated override boundary:

```text
admit(plan) =
    existing_admission(plan)
    AND (
        kind != INTEGRATED_SETUP_STOP_ATTACK
        OR exact_immediate_prize_or_terminal(attack)
        OR exact_lethal_floor_guard(attack, cumulative_parent_action)
    )
    AND (
        kind != RUN_AWAY_SETUP_CLOCK
        OR exact_post_resolution_surviving_board
    )
```

Definitions:

- `exact_immediate_prize_or_terminal`: the current unique attack has a
  certified public typed outcome taking at least one Prize now or ending the
  game now.
- `exact_lethal_floor_guard`: an exact current H0 lethal floor already exists,
  the candidate is that exact attack, and deterministic public simulation
  proves the cumulative-parent action would cross below the required floor.
  Unknown or approximate simulation is false.
- A legal attack, a 14-16-hit lane, chip damage, a shorter current-Active lane,
  or unconditional `preserve_H0_lethal=True` is insufficient.
- Dedicated terminal and `POWERFUL_HAND_FLOOR` builders retain ownership and
  classification. Do not reclassify them as setup-stop.
- `exact_post_resolution_surviving_board`: after removing the Run Away source,
  at least one publicly known own Pokemon remains in play and can supply the
  promotion. Empty Bench is false; never assume a drawn Basic rescues the
  board.
- Every rejected candidate returns the exact cumulative-parent action, never
  an emergency substitute.

## Mandatory repaired callbacks

These exact submitted-replay callbacks must equal the cumulative parent:

- `87328101/S20` -> Dawn.
- `87328994/S18` -> Fezandipiti ex.
- `87333954/S32` -> Bench Dunsparce.
- `87335926/S52` -> Run Away Draw.
- `87336304/S39` -> Bench Dunsparce.
- `87330854/S25` -> END.

## Mandatory preservation

- `87329461/S19` remains `RUN_AWAY_SETUP_CLOCK` with a surviving Bench.
- `87329922/S58` and `87331334/S58` remain
  `POWERFUL_HAND_FLOOR`.
- Original terminal, Boss, retreat-handoff, Fan, clock, duplicate, and package
  fixtures retain exact actions and route kinds.
- Live-19 shadow covers exactly 967 correct-seat callbacks. Historical shadow
  covers its immutable 11,866 callbacks. Every new first difference must be
  traced specifically to this gate.
- Both shadows require zero invalid actions, duplicate mismatches, parent-call
  mismatches, unclassified overrides, missing traces, emergencies, and
  mandatory fallbacks.

## Breakage-only execution gate

Reuse the existing fixed smoke schedule: Historical-Silver, Mega Lucario,
mirror, and Starmie; both seats; seed `2026101741`; duplicate executions; max
1,000 steps. Nonzero exit, action error, max-step hit, or nondeterminism blocks
the live probe. Wins and losses are reported but do not block the
user-authorized diagnostic probe and are not adoption evidence.

Produce exact source/module/deck/test hashes, a parent diff, focused raw
outputs, live/historical shadow JSONs, fixed-smoke raw summaries, compile and
import checks, legal60/ACE1, loader-last, cache-free tree, and deterministic
valid-action evidence. Do not package or submit; root alone owns Kaggle writes.

