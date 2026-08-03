# Root verification: Bench-damage future-value audit

## Verified immutable inputs

- Audit:
  `BENCH_DAMAGE_FUTURE_VALUE_AUDIT.md`
- Audit SHA-256:
  `74C135E9F005F9BADC8C94933FF069F4F23B584183683D7AB0B2811F04F83A9C`
- Replay:
  `autonomous_gold_20260715/evidence/live_54927163_refresh_20260729_0344/episode_88247531_replay.json`
- Replay SHA-256:
  `26D1D7054A5C67ED89261B4CA391445A3EA46C5FC8D4AE314E63A577CFC7434E`
- Historical-Silver policy SHA-256:
  `F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E`
- Historical-Silver deck SHA-256:
  `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`

## Root raw-state recomputation

Root independently read the raw replay and reran
`tools/inspect_agent_replay_decisions.py` against the exact historical policy
with team `rurumi`.

The following facts match the audit:

1. `rurumi` is seat `1`; the episode result for seat `1` is a loss.
2. At step `111`, opposing Active Marnie's Grimmsnarl ex `648#28` had
   Darkness `7#8,7#11`; attack `937` was a legal option.
3. The raw logs at steps `112-113` record `-180` to Active Duraludon `169#64`
   and `-30` to Bench Duraludon `169#66`. The Bench target changes from
   `40/130` to `10/130`.
4. At forced promotion step `114`, seat `1` had healthy `169#63` with one
   Metal `8#122` and damaged `169#66` with three Metals
   `8#116,8#113,8#93`. Both promotion options scored `8000`; the parent
   promoted `#63`. Promotion is therefore a control, not the proposed
   evolution-target mechanism.
5. At the first ordinary Main callback, step `115`, the hand contained
   non-ex Archaludon `840#92`, Metal `8#115`, and Archaludon ex `190#67`.
   The damaged Bench Duraludon remained `10/130` with three Metals.
6. The exact historical scorer reproduced:
   - option `4`, `190#67 ->` Active `169#63`: `36000`,
     `evolve Active Duraludon`;
   - option `5`, `190#67 ->` Bench `169#66`: `18000`,
     `evolve Bench Duraludon`;
   - option `2`, attach `8#115 -> 169#63`: `13800`;
   - Hammer In `223`: `30`.
   The exact parent selected option `4`.
7. Steps `116-120` confirm Assemble Alloy attached recovered Metals
   `8#112,8#121` to the evolved Active. The damaged three-Metal Bench
   Duraludon remained at 10 HP. Metal Defender `253` was then selected.
8. Step `121` shows opposing Munkidori `112#15` with Darkness `7#12` and
   Grimmsnarl ex at `100/320` after receiving 220 damage. Steps `121-125`
   resolve the public damage-counter movement that KOs `169#66` and discards
   its three Metals. The opponent then takes a Prize.

## Exact arithmetic and boundary

At step `115`, `169#66` carried `120` retained damage.

- Archaludon ex max HP `300` gives `180` current HP after evolution.
- One observed 30-damage Bench event leaves `150`.
- The public 30-plus-30 package described by the audit leaves `120`.
- Non-ex Archaludon max HP `180` gives `60` current HP and therefore does not
  survive the full 60 package.

Root therefore confirms the local public-state failure: the parent spent the
available ex evolution on the healthy Active while a three-Energy Bench
lineage sat inside an already payable Bench-damage breakpoint, even though the
same ex evolution was legal on that Bench target and crossed the survival
threshold.

Root does **not** verify an alternate match win. The only replay-backed
counterfactual action is step `115` option `5`. Whether the unmodified parent
then attaches both Alloy Metals to Active `169#63`, makes Raging Hammer legal,
and completes the turn must be established in both logical seats by an exact
engine branch. Attachment, promotion, or opponent targeting must not be added
to the same candidate merely to make that branch succeed.

## Root decision

`ACCEPT_AS_VERIFIED_STRATEGY_EVIDENCE_ONLY`

The evidence is sufficient for a later Sol-Ultra selection decision on one
isolated Archaludon-ex evolution-target survival rule. It is not yet an
implementation contract, strength result, package, live candidate, or formal
parent change.
