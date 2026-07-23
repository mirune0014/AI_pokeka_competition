# Strategy selection: Alakazam EVOLVE_ACTIVE_READY source transition v2

Selected: 2026-07-19 JST  
Owner: root  
Status: one isolated implementation is authorized; evaluation and Kaggle write are not yet authorized

## Immutable evidence boundary

- parent: `candidates/alakazam_parent_end_strict_prize_lead_retreat_ko_bridge_v3`;
- parent source/runtime/deck SHA-256:
  `49E954F53E043CD79D928DFB2340CCB5D85A17F33CCB824C871CCE153C0C9C95` /
  `9CA7A415451B84343165EF8A5CDC0D67BBF1B4969A13C984C09B142B4898CD9A` /
  `7B413177E5077777F2178143839C0155B03B92BBC8B3A6607621A7D43F351141`;
- historical turn-plan source, used only as a code reference:
  `candidates/alakazam_certified_turn_plan_conversion_v1/main.py`, SHA-256
  `E9EF903AE8593758DE76C3911096781E342A0170F3434D9CB35639C991EA7920`;
- current-42 shadow raw SHA-256:
  `319C29CC1C8D0D4C98FC182661B207E764D0B109D5A4303DDD09400E4E149FA1`;
- shadow schedule: 42 episodes, 2,840 unique callbacks, zero invalid actions,
  zero exact-v3/recorded mismatches;
- shadow exposure: seven EVOLVE differences, five first common-prefix starts and
  two state-local starts. The five first starts are episodes `86842681`,
  `86852441`, `86854662`, `86856317`, and `86857388`.

The shadow proves repeated public exposure and the v1 transition defect. It
does not execute candidate-divergent continuations and is not win-rate or
promotion evidence.

## Selected rule

Build exactly one exact-v3 sibling named
`alakazam_evolve_active_ready_source_transition_v2`. Port only the mature
`EVOLVE_ACTIVE_READY` transaction. `BUFFER_READY_RESERVE` and
`RETREAT_CONVERT_NOW` must be unable to start.

The transaction may replace exact-v3's final ordinary MAIN choice only when:

1. the parent selected the sole held evolution card for an unenergized Bench
   Abra/Kadabra;
2. a Psychic-energized, turn-ready Active Abra/Kadabra has exactly one legal
   option using that same card;
3. the public attack certificate strictly improves without consuming a held
   copy needed by the parent's visible two-line setup; and
4. all ownership, uniqueness, hand, deck, board, target, prize, status, and
   protected-serial checks pass.

After the Active evolves, ACTIVATE must locate the unique top-level Active by
the expected evolution serial and ID. It must verify the old source chain as
the exact nested `preEvolution`, rather than search the old source serial at
top level. Damage, `appearThisTurn`, energy units/cards, tools, both boards,
hand, deck, discard, prize, stadium, status, turn, player, target, and context
card remain frozen. A unique legal YES is selected only after every check.

At post-draw MAIN, the exact draw count, frozen-hand prefix, evolved Active,
nested source chain, target, and attack certificate are revalidated. The latch
is then cleared and the entire callback is delegated to exact-v3. The overlay
must never force an immediate attack; episode `86852441` is the adjacent
control that must retain a possible second Kadabra evolution/setup. Success
and failure both cache the parent's action for the post-clear signature so a
repeated callback cannot restart the transaction.

Any ambiguity, missing or duplicate object/option, wrong area or serial,
nested-chain mismatch, or state mutation fails closed: clear once and delegate
once, with no alternative candidate action.

## Mandatory implementation gates

- byte-identical parent `deck.csv` and `runtime/main.py`;
- compile/import, legal 60 cards with one ACE, deterministic valid actions,
  and zero cache artifacts;
- checked-engine/live-serialization positive transactions:
  `86631653/P0/S57-S59`, `86633287/P0/S17-S19`,
  `86638181/P1/S26-S28`, and `86643047/P1/S21-S23`;
- positive route holds the latch through ACTIVATE, owns the unique YES, clears
  only after post-draw validation, and returns exact-v3's whole callback;
- `86852441/S47` preserves the parent's post-draw setup choice;
- `86842681/S24` recorded Bench continuation fails closed as wrong destination;
- `86844870/S35` is a clean no-start;
- `86617263/S99/S101` remains parent-identical with multiple held evolution
  copies;
- fail-closed fixtures cover nested-source missing/duplicate/order mismatch,
  duplicate evolution serial, energy/tool/damage/board/hand/deck/target
  mutation, missing/duplicate YES or ATTACK, and repeated callbacks at every
  transaction stage;
- current-42 shadow has exactly seven exact-v3 differences, all EVOLVE (five
  common-prefix plus two state-local), with zero BUFFER, RETREAT, unrelated,
  invalid, or empty-action differences.

## Frozen fixed-144 decision gate

Use schedule SHA-256
`4271E31503F37EFE4B1BBB9ED2D3569D79D9C1E9B2A20387CCAC131F28346010`
in both seats on identical seeds. Compare a fresh v2 execution only against the
frozen exact-v3 baseline.

- 144 exact unique keys; zero exit, action, max-step, schema, duplicate, or
  schedule faults;
- total at least `88/144`, P0 at least `47/72`, P1 at least `41/72`;
- known at least `45/72`, fresh at least `43/72`;
- Historical-Silver at least `8/16`, Marnie at least `10/16`;
- every non-Marnie opponent meets its exact-v3 floor;
- paired gains at least three and regressions at most one; the only permitted
  regression is `known_target/marnie_sota/p0/2026071600`;
- first differences are exactly the known 17 `EVOLVE_ACTIVE_READY` starts;
  17/17 own ACTIVATE and then delegate after post-draw validation; incomplete,
  fail-open, unrelated, BUFFER, or RETREAT differences are zero.

Historical score `781.7` and the old `88/144` are prioritization evidence only.
Fresh v2 raw execution, independent Sol-Ultra numerical audit, root
recomputation, and a final Sol-Ultra accept/reject judgment remain mandatory.
