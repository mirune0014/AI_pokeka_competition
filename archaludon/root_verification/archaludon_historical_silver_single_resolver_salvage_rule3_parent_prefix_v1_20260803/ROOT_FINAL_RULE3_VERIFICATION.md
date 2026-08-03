# Rule 3 Ultra Ball transaction repair: root final verification

Date: 2026-08-03 JST

## Decision

`archaludon_historical_silver_single_resolver_salvage_rule3_repair_v2` is
**ACCEPTED AS NON-DESTRUCTIVE**.

This decision means that Rule 3 is now integrated without reducing the frozen
Historical-Silver-based parent's measured strength on the fixed schedules. It
does not claim that Rule 3 is stronger on unseen states.

## Frozen identities

- Direct parent `main.py`:
  `D966E455E5110F9D5616195AEAAC8663E6A92F310DAFC4B7F79E4D37149A9C62`
- Accepted candidate `main.py`:
  `4287A616E1611F5697964D9F4065978EED1CEA72CDB48C9F63F1430D69106C35`
- Historical-Silver module:
  `F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E`
- Deck:
  `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`
- Rule 3 repair amendment:
  `196BD3C4F5324615BD6E01D2694C45850942D64001E7C4931D219836884716EB`
- Parent-prefix amendment:
  `C55458C1A8AD4649845BDAE707067DAD295EF7D1F938DF5371E2502EF263344C`

## Corrected implementation defect

The earlier implementation treated attack readiness as permission to end the
transaction immediately. It could therefore force Metal Defender before the
parent's useful Lillie, Poké Pad, Ultra Ball, Basic placement, and recovery
prefix. That was an implementation defect, not a failed Ultra Ball strategy.

The accepted implementation now:

1. starts the Active evolution route only after the first-own-turn evolution
   prohibition has passed;
2. preserves a viable parent Ultra Ball discard pair and recalculates the
   exact discarded/retained Metal allocation;
3. preserves the parent's physical same-card search copy and rebinds the
   actual card in hand to the actual legal evolution or placement option;
4. owns evolution/placement, Assemble Alloy or Turbo Flare attachments, and
   their physical target receipts;
5. after Active attack readiness, keeps the same owner while copying the
   Historical-Silver setup/effect prefix until the parent itself selects Metal
   Defender;
6. preserves the parent's exact Turbo Flare Basic Metal copies and order when
   the parent choice has the required cardinality; and
7. fails closed to the exact parent action on uncertainty. An irreversible
   transaction abort remains a test failure rather than an acceptable route.

## Focused and structural verification

- Rule 3 focused callback fixtures: `276/276` passed.
- Inherited Rule 1/4/5 fixtures: `28/28` passed.
- Compile/import, legal 60-card deck, exactly one ACE SPEC, one final `agent`,
  one resolver, one shared active transaction owner, and one parent call per
  callback passed.
- Candidate and parent package trees differ only in `main.py`.
- Implementation report SHA-256:
  `BAF074429CA05D8CCE7791478052A2095419E45A5AC83F2F80793536C57FD214`.

## Natural engine transactions

- Active route, seat 1, seed `271958323`, Shumpei Archaludon:
  Ultra Ball, exact discard/search, evolution, Assemble Alloy, Lillie,
  Poké Pad/search, a second Ultra Ball, Basic placement, and the parent's
  eventual Metal Defender all completed under one owner. Candidate and parent
  traces are byte-identical at 135 steps and the prior forced-attack loss is
  removed.
- Turbo route, seat 0, seed `271958324`, the same opponent:
  the searched Duraludon, Turbo Flare, three physical Basic Metals, all targets,
  and the terminal receipt completed. Candidate and parent traces are
  byte-identical.
- Former invalid first-turn route, seat 0, seed `271958318`, Arch Peak:
  Rule 3 does not start and all 133 trace rows remain parent-identical.
- Root natural report SHA-256:
  `34B1CFD0E78A1ADB6ABC99FA24704689B04C60235CBA3BD414B9FA372104E8CF`.

## Fixed 160

- Exact schedule: 160 unique keys.
- Parent/candidate wins: `100/160 = 100/160`.
- Paired gains/regressions/ties: `0/0/160`.
- Candidate-parent trace equality: `160/160`.
- Faults, invalid actions, exceptions, max-step hits, and duplicate mismatch:
  all zero.
- Independent report SHA-256:
  `E8E49D3AF720706F869148BB39BBE4A3B529351ED14CDC8BAE0F54BA3916AEAE`.

## Fixed 760

- Spec SHA-256:
  `AD0C31C9DF83ADD924D30129A3A99961CFA10F89019731C6CFC61BEBBB02B4D8`.
- 760 unique keys and exact schedule equality.
- Parent/candidate wins: `480/760 = 480/760`.
- Paired gains/regressions/ties: `0/0/760`.
- Seat 0: `245/380 = 245/380`; seat 1: `235/380 = 235/380`.
- Historical-Silver mirror: `100/200 = 100/200`.
- Adjacent population: `380/560 = 380/560`.
- Every opponent and opponent-seat cell is equal.
- Action errors, start faults, exceptions, max-step hits, and duplicate
  mismatches are zero; duplicate parent trace control is `760/760`.
- Candidate-parent byte traces are `755/760`; all five differing traces have
  the same result and step count.
- Independent numerical report SHA-256:
  `00F7299714851FE41270B3C9EFBAB410350F12437EBEE9352C09A2875E130F48`.

The retention threshold is passed. The strengthened threshold is not:
`480 < 486`. Therefore this is a non-destructive integration, not evidence of
a strength increase.

## Complete Rule 3 lifecycle scan

The candidate alone was replayed over the same 760 opponent/seat/seed keys to
record Rule 3 lifecycle events that can be invisible in candidate-parent action
comparison.

- Provisional starts: 11.
- Committed routes: 10.
- Committed completions: `10/10`.
- Aborts: 0.
- Irreversible abort faults: 0.
- Max-step hits: 0.

The eleventh start was Kang/Crustle, candidate seat 1, seed `271958343`.
Rule 3 initially emitted the exact parent Ultra Ball. At the discard prompt,
the parent's physical cost pair could not retain the route and the target was
not publicly guaranteed in deck. While `committed=false` and
`irreversible=false`, Rule 3 returned the exact parent cost action and cleared
the owner with
`rule3_provisional_release:target_not_proven_before_cost_override`. The full
game trace is parent-identical. This is the designed provisional fail-closed
path, not an incomplete committed transaction.

- Lifecycle scanner SHA-256:
  `18E16B2FC169E49134E93E8D51A896DA8DAE99B0FB73CBC93FA5C45E79372646`.
- Lifecycle rows SHA-256:
  `B7BBEB5A714EA87305B3250DD671DAAB1456DFBA7047D315917145054F32F9A6`.
- Kang full telemetry SHA-256:
  `43C5A8972542679AC2B5A2463F510C6AC3224CECE9058C75943389EBE2032927`.

## Five changed fixed-760 traces

- Historical-Silver seat 0 seeds `271828212` and `271828275`, and Cynthia
  seats 0/1 seeds `271958313` and `271958330`: Rule 3 advances the guaranteed
  Active evolution and Assemble Alloy before parent setup. Its parent-prefix
  then realizes every displaced parent setup action, including the exact
  Duraludon serial, before the same Metal Defender. Physical state and action
  reconverge before attack. These are safe, neutral reorderings in the audited
  states.
- Marnie seat 1 seed `271958346`: only interchangeable Basic Metal physical
  serials differ. Energy count, source, target, attack readiness, action
  sequence, board, prizes, and result are unchanged, and the serialized suffix
  reconverges.

No audited first difference is a clear bad move. These judgments apply only to
the exact observed states and are not generalized to unseen states.

## Final judgment

The independent Sol-Ultra rule judge returned **ACCEPTED AS NON-DESTRUCTIVE**.
Rule 3 has corrected the transaction-continuation defect and may become the
accepted parent for later work. No Kaggle package or submission is part of this
decision.
