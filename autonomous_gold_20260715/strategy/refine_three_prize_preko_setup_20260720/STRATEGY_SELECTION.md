# Frozen strategy selection: certified three-prize pre-KO setup transaction v2

## Judgment

**Reject broad v1** (`7C06F05A...43BB`). It retained the fixed panel exactly
at 38/72 with zero faults and zero regressions, but seven of ten causal first
changes attacked before deterministic setup/recovery that preserved the same
three-prize KO. Numerical parity cannot override this qualitative failure.

Implement the successor directly from the exact submitted parent
`alakazam_exposed_dudunsparce_run_away_ready_alakazam_ko_transaction_v1`,
source SHA-256
`CB52F1737417EAEEAEF226CFF79ABD4FA58119E3F2AF1D448DFBE5D68722E213`.
Do not stack or edit broad v1.

## One invariant

With an exact currently lethal Powerful Hand against the unchanged public
three-prize Active, permit at most one certified setup/recovery route whose
worst-case public post-route hand count still KOs that target; then lock
Powerful Hand. Otherwise attack immediately.

Let `H` be the exact own hand length, `R = ceil(target.hp / 20)`, and `D` the
exact public deck count. The base certificate requires exact MAIN, live result,
turn at least two, no `looking`, `minCount=maxCount=1`, exact Active Alakazam,
one uniquely encoded and payable Powerful Hand, exact hand, stacks, max HP,
status, visible effects/protection, and `prize_count(target)==3`, with `H>=R`.
All inherited latches and merge quarantine must be clear before and after the
exact parent call. If the base certificate fails, return exact parent identity.

Precedence when the base certificate passes:

1. Attack immediately if the three prizes take every remaining own prize.
2. Attack immediately if the exact parent action is Boss's Orders and would
   switch away the lethal Active.
3. Attack immediately if the exact parent action is unclassified, has hidden
   or uncertain hand consequences, or its conservative route floor is `<R`.
4. Otherwise execute exactly one certified route below and force Powerful Hand
   immediately after exact resolution.

## Certified route variants

### Dudunsparce evolution and Run Away Draw

The exact parent chose a bench Dunsparce-to-Dudunsparce evolution. Metadata and
visible effects certify Run Away Draw, attachment return counts are exact,
`LB = H - 1 + min(3,D) >= R`, and the projected nonterminal deck
`D-min(3,D)+returned_components >= 1`.

Stages:
`await_evolution_resolution -> await_run_away_main -> await_run_away_resolution -> await_attack -> await_attack_resolution`.

At the next MAIN, force the unique Run Away Draw option tied to the evolved
serial, with no intervening action. Verify the fixed draw count, carried-hand
subset, exact source stack and attached cards returned to deck, freed bench
slot, unchanged attacker and target, then force the unique attack.

### Kadabra on-evolve Psychic Draw

The exact parent chose a bench Abra-to-Kadabra evolution. Psychic Draw metadata
and absence of visible ability suppression are certified,
`LB = H - 1 + min(2,D) >= R`, and projected nonterminal deck
`D-min(2,D) >= 1`.

Stages:
`await_evolution_activate -> await_psychic_draw_resolution -> await_attack -> await_attack_resolution`.

Require the exact ACTIVATE yes/no callback for the evolved Kadabra, force the
unique YES, verify exactly two draws and otherwise unchanged public board, then
force Powerful Hand.

### Night Stretcher recovery

The exact parent chose Night Stretcher; visible discard contains at least one
exact legal Pokemon or Basic Energy recovery, target prompt is mandatory
`minCount=maxCount=1`, and `LB=H`.

Stages:
`await_stretcher_target -> await_stretcher_resolution -> await_attack -> await_attack_resolution`.

Allow the parent to select any exact legal visible recovery. Verify Night
Stretcher hand-to-discard and exactly one selected card discard-to-hand, with
deck and combat state unchanged, then force Powerful Hand.

### Narrow safe-spend tail

One exact parent-selected Abra or Dunsparce bench play with no triggered effect,
or exact Sacred Ash resolution, may proceed only when `H-1 >= R`.

- Basic stages: `await_basic_resolution -> await_attack`.
- Sacred Ash stages:
  `await_ash_selection -> await_ash_resolution -> await_attack`.
  Accept the parent's exact legal visible discard selection; verify only those
  Pokemon move discard-to-deck and retain the `H-1` hand floor.

No other simple-spend class is admitted. Poke Pad receives no speculative +1;
without an independent public worst-case target guarantee, its floor is `H-1`.

## State, rollback, and duplicate contract

Freeze turn/player/action count, route, exact hand/deck/prize counts, attacker
payment and fingerprint, target serial/stack/HP/max-HP/tools/Energies/prize
value, both public boards, stadium/effect/status fingerprints, route source and
action-card fingerprints, and expected log/zone deltas.

- Recheck attacker, target, protection, required damage, and prize value at
  every stage.
- Never predict hidden draw identities. Check only fixed draw count,
  carried-hand membership, unique serials, and exact zone-count deltas.
- Visible ability lock, draw prevention, unknown effect text, inadequate deck
  reserve, missing/duplicate route option, or callback mismatch disallows setup
  and chooses immediate attack while the base attack remains certified.
- If the base attack becomes ambiguous, clear the outer latch and return the
  exact unquarantined parent.
- Snapshot every inherited latch/cache and the exposed-Dudunsparce state.
  Speculative parent reruns use balanced merge quarantine and commit only a
  clean desired-action rerun state.
- A failed continuation clears the outer latch and recomputes the genuine
  unquarantined parent fallback. Never keep a quarantined fallback state and
  never pretend an emitted game action can be rolled back.
- Identical duplicate callbacks return the cached action without rerunning the
  parent or advancing a stage. Clear cache on a distinct observation,
  turn/seat/game boundary, stale latch, or exception.
- The final public callable must remain `agent`; no helper may follow it.

## Required positives

- `86991375/53/s1`, `86968875/97/s0`, `86969947/60/s1`,
  `86898285/57/s0`, `86909242/107/s0`: allow Dunsparce evolution, force Run
  Away Draw, then attack.
- `86972084/130/s1`: allow Kadabra evolution, force Psychic Draw YES, then
  attack.
- `86981695/121/s0`: allow Night Stretcher and one visible recovery, then
  attack before later Boss.
- `87002204/105`: allow Sacred Ash resolution, then attack.
- `87002733/103`: allow Dunsparce bench play, then attack.
- `86974207/77/s0` and `/81`: attack immediately because Lucky Helmet crosses
  below lethal.
- `86976336/85/s1`: attack immediately because Abra crosses below lethal.
- `86901033/155/s1`: attack immediately because the KO ends the game.
- `86981695/138/s0`: attack immediately before exact Boss.
- `86998420/101`: attack immediately because Poke Pad has no public guaranteed
  refund.

Runtime must contain no episode IDs, team names, target names, or
opponent-policy keys.

## Mandatory negatives

Retain exact parent behavior for non-MAIN prompts, non-three-prize targets,
insufficient current damage, Hero's Cape 440 HP at 320/300/360, Legacy Energy
reducing prizes to two, Mist/Rock/protection, unclear HP/stack/hand,
unpaid/ambiguous Powerful Hand, status/effect ambiguity, inherited ownership,
the Enhanced Hammer prompt, the two-Mist Crustle state, deferred attach/draw
routes, and the Archaludon Boss-target prompt. Add malformed callbacks and
visible ability-suppression/draw-prevention/short-deck mutations for every
route stage.

## Minimum gates

- Focused fresh-module tests for every anchor, every route stage, malformed
  callbacks, public ambiguity, inherited ownership, duplicates, failed witness,
  compile/import, legal 60 cards/one ACE SPEC, Kaggle last callable, cache-free
  tree, and both-seat Historical-Silver smoke.
- Shadow the historical 9,266 callbacks plus refreshed full-42 both seats.
  Require zero invalid actions and enumerate every first change. The seven
  broad-v1 setup starts must no longer attack immediately; immediate/Boss/
  Poke-Pad guards must remain.
- Exact compact-72 parent/candidate/duplicate schedule: 216/216 exits zero,
  exact keys and duplicates, no action errors/max-step hits/trace mismatches,
  at least 38/72 overall, 20/36 p0, 18/36 p1, and no opponent below its paired
  parent.
- Adoption requires at least 40/72, zero paired regressions, Historical-Silver
  at least 4/8 with no seat regression, plus at least two completed full-engine
  transactions spanning both seats and including both a setup route and an
  immediate guard. Retention alone is insufficient.
- If compact-72 does not exercise the primary mechanism, run an immutable
  both-seat Historical-Silver plus Mega-Lucario extension with at least 16
  paired seeds per opponent and exact transaction-stage telemetry. Do not
  promote without primary-anchor movement.
