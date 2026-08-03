# v1 runtime fix5 semantic-certificate contract

## Status

This contract authorizes one combined fix5 derived from
`alakazam_newdeck_v1_package_runtime_certified_fix4`.

Fix4 is retained as `SUPERSEDED_FORMAL_RUNTIME_FAULT`. Its complete formal
safety run finished 700/700 games, but exact raw auditing found seven Enhanced
Hammer transaction faults and two Boss's Orders transaction faults. No
Comparison B result may be produced from fix4.

The combined fix is a certificate-completeness correction, not strategic
tuning. It must not change setup, board construction, search order, Energy or
hand policy, candidate priority, attack-continuity policy, prize policy,
finishing policy, or unrelated disruption behavior.

## Frozen parent evidence

- Parent candidate:
  `alakazam_staged_20260729/versions/alakazam_newdeck_v1_package_runtime_certified_fix4`
- Parent policy closure SHA-256:
  `48EEF98CD6054882FFB19E45D061AE90C739E5415A0F3F028A7981669589CA79`
- Parent planner SHA-256:
  `04DA4A797D48CFA3786778F9EAE2690780152417AB12F22CF5ADE65A151A3EA2`
- Parent unit tests: `134/134`
- Formal raw suite:
  `alakazam_staged_20260729/metrics/formal_v1_runtime_certified_fix4_7opp_50seed`
- Formal games: `700/700`
- Formal callbacks: `45,461` starts and `45,461` ends
- Formal transactions: `444` starts and `435` completes
- Formal transaction faults: `9`
- Runner, invalid-action, timeout, max-step, structural, unknown-route, and
  candidate-owned fallback counts: all `0`

The engine runtime tree is frozen at SHA-256
`466638706BD5C6915E25D1B3CB9E3D966390FBC263F4ED3153108E29C0194FFF`.
`Export.lib` is frozen at SHA-256
`2758FBAAA51557D72E1EBBEF71AFBA1F6FCE9BB73162154301A322A4515C0223`.

## Single hypothesis

Closing two identified public-semantic omissions before irreversible v1
actions will eliminate all nine fix4 transaction faults while preserving all
unrelated policy behavior:

1. Grow Grass Energy changes HP only when attached to a Grass Pokémon.
2. Repelling Veil prevents Powerful Hand's damage-counter effect on a Basic
   Team Rocket Pokémon.

The two corrections must remain separable in helpers, fixtures, and mutation
tests.

## Authorized Hammer correction

Before returning the Enhanced Hammer PLAY action, `_candidate_hammer` must:

1. Resolve one exact target row from `public["opponent_active"]` or
   `public["opponent_bench"]`.
2. Bind area, field index, Pokémon serial, Energy index, Energy ID, Energy
   serial, owner, and the complete bridge fingerprint.
3. Validate target card metadata fail-closed:
   - `cardId` exactly matches the target ID;
   - `cardType` is exactly Pokémon;
   - `energyType` is an integer, not a boolean, and is exactly one member of
     the engine's `EnergyType` values.
4. Compute the complete expected target fingerprint after removing the exact
   selected Energy:
   - remove the bound Energy unit and Energy-card row;
   - if the selected card is Grow Grass Energy ID `18` and the target type is
     Grass, subtract `20` from current and maximum HP and require
     `0 < next_hp <= next_max_hp`;
   - if ID `18` is attached to an exact non-Grass target, preserve current and
     maximum HP;
   - preserve every other fingerprint field exactly.
5. Store the complete before and expected-after fingerprints in the
   transaction before the irreversible PLAY action.

Missing, mismatched, boolean, out-of-enum, malformed, or otherwise
uncertifiable target metadata makes the candidate non-fire before Hammer is
played.

`_advance_hammer` must continue to bind the exact target and Energy and must
confirm that the live target still equals the stored before fingerprint.

`_verify_hammer` must use the stored complete expected-after fingerprint. It
must not recompute removal semantics after the irreversible discard. All
existing exact checks remain:

- prompt envelope;
- action count;
- own hand and discard deltas;
- exact target area rows;
- unchanged other target area;
- opponent discard delta;
- exact move log;
- mode recheck;
- protected serials.

Do not change Hammer eligibility, the unique-special-Energy rule, mode
arbitration, backup readiness, candidate priority, or the child selection
contract.

## Authorized Repelling Veil correction

Add a local v1 wrapper around the inherited Powerful Hand target-clear helper.
Do not modify `_cumulative_parent.py`.

The wrapper must inspect only the target owner's public Active and Bench.
Articuno on the attacking side is irrelevant.

An Articuno source is exact only when all of the following match:

- card ID `414`;
- name `Team Rocket's Articuno`;
- Pokémon card type;
- `basic is True`, `stage1 is False`, `stage2 is False`;
- exactly one skill;
- skill name ` Repelling Veil`, including the leading space;
- skill text:
  `Prevent all effects of attacks used by your opponent’s Pokémon done to your Basic Team Rocket’s Pokémon. (Existing effects are not removed. Damage is not an effect.)`
- the public Pokémon object is structurally complete for its owner.

A target is an exact Basic Team Rocket Pokémon only when:

- card metadata exists and `cardId` exactly matches;
- card type is Pokémon;
- `basic is True`, `stage1 is False`, `stage2 is False`;
- `evolvesFrom is None`;
- the public target has no pre-evolution cards;
- the canonical name begins with the exact anchored namespace
  `Team Rocket's ` and has a nonempty suffix.

Do not normalize punctuation, use substring matching, infer affiliation from
Energy type, or scan skill and attack text for affiliation.

Use tri-state semantics:

- exact protected state: block the Powerful Hand KO certificate;
- exact non-applicable state: defer to the inherited target-clear result;
- malformed or ambiguous relevant Articuno/target metadata: fail the v1
  certificate closed.

Apply the wrapper to every v1 Powerful Hand KO certificate:

- `_powerful_hand_ko`;
- the current and virtual target checks in `_hammer_enables_current_ko`;
- `_target_powerful_hand_ko`;
- the active-evolution Alakazam candidate;
- the ready-bench Alakazam candidate.

Keep `_exact_attack_resolution` and every attack-resolution verifier unchanged.
The correction must prevent the irreversible supporter/evolution/item route
from arming; it must not accept a zero-counter attack as a successful KO.

## Mandatory regression fixtures

### Hammer

- Grass Crustle ID `345` plus Grow Grass ID `18`:
  `140/170 -> 120/150`.
- Colorless Mega Kangaskhan ex ID `756` plus ID `18`:
  HP and maximum HP unchanged.
- Kangaskhan with Hero's Cape:
  `140/400 -> 140/400`.
- The complete expected fingerprint exists before PLAY and the verifier uses
  that stored fingerprint without semantic recomputation.
- Wrong Energy index, serial, owner, or row fails.
- Duplicate target serial fails.
- Changed before fingerprint, changed stored expected fingerprint, and
  unexpected post-area row fail.
- Missing target metadata, card-ID mismatch, non-Pokémon card type, missing or
  invalid Energy type, boolean Energy type, out-of-enum Energy type, and an
  invalid Grass post-HP result all produce no Hammer candidate before PLAY.
- Existing child-prompt, discard/log, other-area, and both Hammer-mode mutation
  fixtures continue to fail closed.

### Repelling Veil

- Exact Articuno on Active and Bench is tested separately.
- Exact Articuno plus Basic Team Rocket's Mewtwo ex blocks:
  `_target_powerful_hand_ko`, `_powerful_hand_ko`, the Hammer virtual-clear
  route, and both Alakazam candidate routes.
- No-Articuno Mewtwo control remains admissible.
- Articuno plus a non-Team-Rocket Basic or an evolved Team Rocket target does
  not add a Repelling Veil block.
- Articuno on the attacking side does not protect the opponent.
- ID `414` mutations in name, leading-space skill name, skill text, skill
  count, basic flag, or card type fail closed.
- Malformed public Articuno fails closed.
- Canonical-name near misses, a curly apostrophe, suffix-only `Team Rocket`,
  and a skill-text-only mention do not create a false Team Rocket
  classification.
- In the protected Boss fixture, no Boss supporter is played and no v1
  transaction starts.

## Source boundaries

Destination:

`alakazam_staged_20260729/versions/alakazam_newdeck_v1_package_runtime_certified_fix5`

The implementation worker owns only that new destination directory.

Allowed behavioral source:

- `planner_deck_adaptation_v1.py`

Allowed tests:

- existing top-level `test_*.py` files inside the new destination;
- one new top-level `test_*.py` file inside the new destination if needed.

All other candidate Python, runtime, configuration, and deck files must remain
byte-identical to fix4. `deck.csv` must remain:

- raw SHA-256:
  `F598F5E578D0440C96DC0492EAECF2E19739B7A23225BE57114A724EF7D0FB94`;
- normalized deck hash:
  `4414e8995e50c7a00d4b6aa7d9229f63c1dff5261643ec7cd86c4e329113ed69`.

Do not edit adapters, shared tools, reports, earlier versions, or earlier
evaluation outputs.

## Acceptance gates

1. Every fix4 test and all new positive, negative, and mutation fixtures pass.
2. The exact seven Hammer cases complete using stored non-Grass fingerprints.
3. The exact two Boss cases reject the certificate before Boss PLAY.
4. A pre-Articuno Mewtwo positive control remains admissible.
5. A fresh immutable targeted replay run has zero safety fault.
6. A fresh 140-game seven-opponent smoke has zero safety fault.
7. A fresh 700-game seven-opponent formal run has:
   - exactly 700 completed games and 70 completed blocks;
   - callback starts equal callback ends;
   - transaction starts equal transaction completes;
   - zero pending transaction, invalid action, exception, timeout, max-step,
     structural fault, duplicate-control violation, unknown removed-card route,
     candidate-owned fallback, and irreversible fault.
8. Changed traces must show the intended mechanism. Merely suppressing all
   Hammer, Boss, or Alakazam candidates is a failure.

Partial results must not be interpreted. Comparison B remains blocked until all
eight gates pass.
