# Strategy selection: final-two-Prize Basic Psychic acquisition transaction v1

Recorded: 2026-07-21 JST  
Role: read-only Sol-Ultra strategy judge

## Decision

**SELECT exactly one rule-improvement hypothesis:** when exactly two own
Prizes remain, an unenergized Active Alakazam can end the game by attaching one
Basic Psychic Energy and then using Powerful Hand on the unchanged public
two-Prize Active, replace the parent's Enriching-to-Bench attachment with the
Basic Psychic attachment and explicitly lock the Powerful Hand continuation.
The lethal certificate must include every known public modifier; with Full
Metal Lab, use the conservative floor `20 * post_attach_hand - 30` against a
Metal target.

Proposed isolated destination:
`autonomous_gold_20260715/candidates/alakazam_certified_terminal_basic_psychic_powerful_hand_v1`.

This is a deterministic public-state, deck-theory transaction. It uses no
opponent identity, hidden-zone guess, replay action label, learned ranker, or
deck change.

### Exact implementation parent

Use the **current submitted source** as the exact implementation parent:

- `autonomous_gold_20260715/candidates/alakazam_public_h0_h1_turn_objective_guard_v1/main.py`
- SHA-256
  `23B89E347565F1782F44494E8ACD89FAB0FEED20C484B2DA14DE1195B908CBE9`.

Keep the byte-identical deck, SHA-256
`7B413177E5077777F2178143839C0155B03B92BBC8B3A6607621A7D43F351141`.

The formal guarded-Teleportation source
`4A95DCE0BB095A05F58085DFC450528C5939527E30B9D40E43A76B0CFCE2AE16`
remains the rollback and secondary shadow comparator, but it is **not** the
implementation parent. Starting from it would discard the deployed H0 action
that retained the win at `87140298/S103` and would make the new artifact differ
from the live agent by several old mechanisms. Starting from `23B...CBE9`
isolates the new source diff to this transaction. This parent ruling does not
formally adopt every H0/H1 branch; formal rollback remains `4A95...AE16`.

## Verified facts used

The authoritative synthesis is
`autonomous_gold_20260715/analysis/54861184_next_rule_20260721/ROOT_VERIFIED_EVIDENCE.md`,
SHA-256
`862D917C10D0B1195052810D41A2043211527F0DA9A82B21BEABF81D6D7AFAFA`.

- At the authenticated 05:53 JST checkpoint, submission `54861184` was
  `COMPLETE`, score `748.4`, public `13-8`, with quota `4/5` used.
- The correct-seat 22-current plus 20-control shadow
  `live/54861184/heartbeat_20260721_0553/all_new22_shadow.json`, SHA-256
  `44460B5A471D01A76F66E5710BD6A1E6DA77976093EDF7907881A7C0C11075F2`,
  has 2,593 callbacks, four classified differences, zero invalid actions, and
  zero duplicate mismatches. In the current 22, the submitted source differs
  from the formal rollback only in the intended H0 win `87140298/S103` and the
  outcome-neutral/protective Helmet END in loss `87142944/S152`; it equals the
  rollback in the other seven losses.
- Replay `87139766`, SHA-256
  `49866C2338E9CD969B9FC12F1FB42E28F16A1142ADD5E76B5FFC0FC7C6DE2E35`,
  proves the public start at S124: turn 9; own Prizes two; hand 21; attachment
  unused; complete Active Alakazam `743/s13`, 140 HP, zero Energy; clear Active
  Archaludon ex `190/s79`, 300 HP, three Basic Metal Energy, no Tool, worth two
  Prizes; Full Metal Lab `1244` in play. Basic Psychic-to-Active is legal `[2]`,
  Telepath-to-Active is `[9]`, and Enriching-to-Benched-Dudunsparce is `[20]`.
  Both live source and rollback choose `[20]` and the recorded game is lost.
- The root checked-engine artifact
  `analysis/54861184_next_rule_20260721/checked_engine_87139766_terminal_attach.json`,
  SHA-256
  `08CD802336B95A61CE821FFF3DAB54939A2B61837C76F5FBB39D3E762C70ED4A`,
  records PASS for `[2]` Basic Psychic, post-attach hand 20, `[14]` Powerful
  Hand, and `[0,1]` Prize selection: result is seat 0 and own Prizes are zero.
  Its reproducer has SHA-256
  `D05CE3BF1D28AB4DD579BED2C02A43B5A28D50A1F11F7A14E7F5B79FE26FDC8F`.
  The engine logs raw 400 damage; the public certificate must nevertheless use
  the stricter Full Metal Lab floor `400 - 30 = 370 >= 300`.
- The same engine branch proves that merely choosing the correct attachment is
  insufficient: the current `23B...CBE9` source then chooses Active Lucky
  Helmet `[8]`, not the legal Powerful Hand `[14]`. The new rule must own the
  attach-to-attack continuation rather than rely on inherited H0.
- Replay `87146132`, SHA-256
  `333DFD0F1637D44B27F17C026AF1AAD8A1525A208A1483E414EF0840F070EAA7`,
  has the secondary lone-Dudunsparce reserve defect at S63, but it only proves
  a survival opportunity, not a winning continuation.
- Direct inspection of the other requested losses found no competing
  root-checked same-turn loss-to-win conversion: `87144532`
  `DFCE07BE...DB9323F`, `87141882` `19448863...AF9342B`, `87138714`
  `94257B67...933D1A3`, `87137658` `A914C476...4E67D54`, and `87136609`
  `169EA275...2A18E`. Their visible gaps require board survival, setup, deck
  clock, or multi-turn attack continuity. They remain evidence for later rules,
  not justification to widen this transaction.

## Why this rule wins the comparison

The S124 branch is an exact public resource-to-Prize conversion, not a forecast.
All required cards, payment, hand cost, target HP, Prize value, stadium, and
legal actions are visible before commitment, and the checked engine proves the
counterfactual ends the game. The rule therefore evaluates the whole deck plan
coherently:

- setup and board formation are already sufficient because the game ends;
- attacker readiness is repaired with the only missing Basic Psychic unit;
- the hand falls only from 21 to 20, leaving 400 raw and a conservative 370;
- deck, Bench, recovery, Boss, disruption, and future Energy are irrelevant
  after the certified terminal attack;
- attack continuity is made atomic, preventing the observed Helmet detour;
- the two-Prize exchange is final, so no backup attacker or hidden opponent
  response is assumed;
- the main regression domain is implementation state leakage, not strategic
  tradeoff, and can be bounded by an exact semantic certificate.

The S63 reserve alternative is weaker: it prevents immediate board-out but
does not certify an attacker, Prize, or win, and it interacts with Run Away
Draw and promotion. The remaining losses likewise offer no stronger checked
terminal mechanism. Do not combine reserve survival, mill-clock recovery, or a
general Full Metal Lab H0 rewrite with this rule.

## Frozen behavioral contract

Implement one fail-closed state machine with semantic resolution. Option
indices below identify the positive fixture only and must never be hard-coded.

### Start certificate

Every clause is mandatory:

1. Exact ordinary MAIN callback: `result == -1`, `looking is None`, turn at
   least two, `SelectContext.MAIN`, `minCount == maxCount == 1`, zero remaining
   damage/Energy costs, and exactly one fully encoded END. Raw and parsed
   current/select/log fields, ownership, counts, serials, and option metadata
   must agree.
2. No inherited transaction owns the callback at entry or after stale-state
   preparation: Hilda, Enriching reserve, Fez bridge, Active-Psychic KO,
   stranded retreat, guarded Teleportation, or turn-objective recovery. A
   callback that cleared a stale owner is delegated for the whole callback.
3. Own field has exactly one Active Alakazam `743`, with a complete unique
   Abra-line stack, exact 140 max/current HP, clear status/effects, no Tool,
   and **zero attached Energy cards/units**. `appearThisTurn` must be an exact
   boolean but may be true, as it is in S124. `energyAttached` must be false.
4. Own hand is fully visible, serial-complete, duplicate-free, and
   `len(hand) == handCount == H`. Basic Psychic Energy `5` and Powerful Hand
   `1072` metadata must match the checked runtime exactly. There must be exactly
   one physical Basic Psychic serial and exactly one fully encoded legal
   ATTACH of that serial from hand to this Active. Telepath Psychic, Enriching
   Energy, a future search, or Energy on another Pokemon does not satisfy this
   source requirement.
5. Own remaining Prizes are exactly two. The opponent has exactly one complete
   unchanged Active whose public stack, HP, max HP, types, ownership, Energy,
   Tools, status, and effects are exact; it is worth exactly two Prizes after
   every public modifier. Legacy/special Energy, Tool, Prize, HP, prevention,
   stack, or effect ambiguity fails closed.
6. Stadium is either absent or exactly Full Metal Lab `1244` with its checked
   text and one unique public serial. No other Stadium is admitted in v1. Let
   `R = 30` when that Lab applies to the Metal target and `R = 0` otherwise.
   Require `D = 20 * (H - 1) - R >= target.hp`. Do not rely on the engine's raw
   damage-counter log to omit the reduction; the public certificate always
   uses this conservative floor.
7. Exact attack metadata proves that one Basic Psychic unit pays Powerful Hand
   after attachment. Weakness, Resistance, special conditions, attack
   prevention, target skills, attached-card effects, or any other unresolved
   damage modifier vetoes the start.
8. The exact live parent has finalized one ordinary ATTACH of Enriching Energy
   `13` from hand to a serial-distinct **non-Active** own Pokemon. Its card and
   draw-effect metadata, source serial, target serial, and unique legal option
   must be exact. This is the only replaceable parent action in v1. If the
   parent chose PLAY, EVOLVE, Ability, Basic/Telepath attachment, Tool,
   RETREAT, ATTACK, END, Boss, another transaction, or any ambiguous action,
   retain it unchanged.
9. Snapshot every existing policy latch/flag and the complete semantic
   fingerprints needed across the boundary. Starting the transaction must not
   mutate any inherited latch, ability flag, quarantine, or parent state.

### Action and continuation

At the certified start, create a new transaction owner and return the unique
Basic Psychic-to-Active ATTACH. On an identical callback, return the same
cached semantic action without advancing state.

On the next callback, run this transaction overlay before ordinary scoring,
the H0/H1 guard, and the thin-deck Helmet guard. Require the same turn/player,
the exact expected action-count transition, attachment used, hand `H - 1`, the
same Active/target/stadium/Prizes/board, and movement of the frozen Basic
Psychic serial from hand to the Active with no other unexplained zone or log
change. Resolve exactly one legal Powerful Hand option with exact metadata,
recompute the same conservative lethal floor, and return that attack. This
explicitly replaces the inherited post-attach Lucky Helmet choice.

If the engine presents the exact two-card Prize prompt, select both unique
Prize options and then clear the new transaction state at terminal resolution.
All other post-attack resolution remains exact parent behavior. Repeated
post-attach or Prize callbacks must be idempotent through the existing decision
cache plus the new stage signature.

Do **not** broaden `_two_prize_stadium_is_clear`, the existing H0/H1 helper, or
Helmet logic. Do not import or copy behavior from another candidate. The new
helper owns only this start and its forced continuation.

### Abort and failure behavior

Before attachment, any exception, malformed field, serial collision, option
ambiguity, failed modifier calculation, failed state-snapshot equality, or
certificate miss returns byte-identical live-parent behavior and creates no
state. After attachment, any unexpected selection context, turn/player/action
count, target/stadium/hand/board change, missing unique Powerful Hand, or state
restoration disagreement clears only the new transaction and delegates; it
must not restart on that callback. An emitted attachment cannot be rolled back,
so all strategic safety checks occur before it.

## Frozen positives, negatives, and mutations

### Required positive

- `87139766/S124/seat0`: parent Enriching-to-Benched-Dudunsparce `[20]` becomes
  semantic Basic Psychic-to-Active `[2]`; exact post-attach state becomes
  Powerful Hand `[14]`; exact two-Prize prompt selects both; checked terminal
  result is seat 0 with own Prizes `2 -> 0`.

Reindex this fixture to seat 1, permute every option order, and substitute
serial-distinct equivalent physical cards. The semantic transaction and
terminal result must be identical. Duplicate every start/continuation/prize
callback and verify identical actions with no double advancement.

### Mandatory parent-identity controls

- `87140298/S103`: retain the submitted H0 Powerful Hand win.
- `87142944/S152`: retain submitted thin-deck END, not Helmet.
- `87146132/S63`: retain END; reserve survival is a separate future rule.
- `87144532`, `87141882`, `87138714`, `87137658`, and `87136609`: no start and
  exact live-parent action identity at every reachable recorded callback.
- All 20 prior controls in the frozen 42-episode shadow retain existing live
  behavior unless a newly observed first difference independently satisfies
  every generic clause above.

Synthetic no-start boundaries include: own Prizes 0/1/3; target Prizes 0/1/3;
post-attach damage one below HP; hand incomplete; Active not Alakazam, damaged,
statused, already energized, or ambiguously stacked; attachment already used;
only Telepath available; zero or multiple Basic Psychic source/attach options;
target with Tool, special Energy, prevention, unknown effect, or incomplete
lineage; unknown/wrong/multiple Stadium; Full Metal Lab floor below HP; parent
choice not exact Enriching-to-non-Active ATTACH; active transaction owner;
stale-owner cleanup; non-MAIN or selection prompt; option permutation;
duplicate callback; changed turn/player; exception injection. Every case must
return exact live-parent behavior and leave all state unchanged.

## Falsifiable gates

### Implementation and mechanism gates

1. Candidate is one isolated copy of `23B...CBE9`; deck and runtime are
   byte-identical. Static diff contains only the new transaction, cache/stage
   signature, diagnostics, and focused tests. Any change to existing H0/H1,
   Helmet, Teleportation, scoring, deck, or runtime rejects it.
2. Python 3.11 compile/import, deterministic deck action, exact legal 60 cards
   with one ACE SPEC, last/only callable public loader entrypoint, cache-free
   tree, and exception fallback all pass.
3. Focused fresh-module tests pass the positive, both-seat reindexing, option
   permutations, duplicate callbacks, every anti-anchor/mutation, stale-owner
   case, and state-snapshot checks.
4. Extend the root checked-engine reproducer to the candidate. In both semantic
   seats it must choose Basic Psychic, then Powerful Hand rather than Helmet,
   reach the exact two-Prize prompt, and terminate with the candidate seat as
   winner and zero own Prizes. The first mechanism must be this transaction.
5. Candidate-versus-live-parent shadow over the complete frozen current 22 plus
   20 controls must have S124 as the intended first difference, zero invalid
   actions, zero duplicate mismatches, and no unclassified first difference.
   Every later recorded-path difference after S124 is counterfactual and must
   fail closed without latch leakage. Candidate-versus-formal shadow must
   preserve the four already classified live/formal differences plus this new
   one; especially, Helmet S152 must remain END.
6. Run the existing 136-row/186-seat historical shadow. Any extra first
   difference must satisfy the full generic certificate and receive qualitative
   review. Any mechanism-first loss, nonterminal activation, opponent-id
   dependence, invalid action, or unclassified difference rejects the build.
7. Package-local Historical-Silver smoke completes in both candidate seats
   with zero action errors and zero max-step hits; duplicate runs have identical
   actions/results. Archive membership, source/runtime/deck hashes, loader,
   legality, and zero caches are root-verified.

### Final pre-reset slot permission

The exact S124 checked-engine loss-to-win is the required **major break**. A
single pre-reset exploratory submission may be permitted only if all seven
fast gates above pass simultaneously, the packaged candidate reproduces the
same win in both semantic seats, every difference is classified, and a final
root refresh confirms the intended hash, `COMPLETE`/non-recovering live state,
no execution error, and one valid UTC-day slot. Equality or no exposure in
ordinary smoke games is safety only; it does not replace the S124 engine win.

Any failed/ambiguous gate, source drift, post-attach Helmet action, loss of the
existing S103 H0 win, change to S152 Helmet behavior, invalid action, duplicate
nondeterminism, max-step hit, or unclassified shadow start means **do not use
the final slot**. Packaging alone is never submission authority; the root owns
the Kaggle write.

This permission is an exploratory live probe, not formal adoption. Formal
promotion after reset requires the immutable compact comparison from
`evaluations/alakazam_active_psychic_immediate_ko_transaction_v1/PHASE0_SCHEDULE.csv`
(SHA-256
`4271E31503F37EFE4B1BBB9ED2D3569D79D9C1E9B2A20387CCAC131F28346010`):
use seeds `2026071586`, `2026071600`, `2026101801`, `2026101804`, all nine
opponents and both seats, exact live parent/candidate/candidate-duplicate (216
commands). Formal eligibility requires candidate at least `41/72`, at least
two wins above the exact live parent, `>=2G/0R`, no seat/block/opponent decline,
Historical Silver at least `4/8` and at least one mechanism-linked gain, starts
in both seats and at least two seeds, 72/72 duplicate identity, and zero faults.
No-start/equality is not formal promotion. A later full-144 judgment must still
check practical absolute strength, primary-anchor movement, both-seat and
repeated-bucket behavior, adjacent-population floors, action errors/max-step
hits, and that gains begin with this exact transaction.

## Regression risks and exact evidence needed next

The strategic counterfactual is certain at S124; uncertainty is concentrated
in implementation generalization. Main risks are a latch surviving a game or
turn, semantic option mis-resolution, relaxing the existing stadium fail-close,
misapplying Full Metal Lab, or allowing the ordinary Helmet guard to preempt
the continuation. The rule may also be rare, so a safe live probe can be
practically inert outside the proven position. Using `23B...CBE9` preserves the
strongest deployed behavior but does not erase its exploratory status.

Needed next, in order:

1. Sol-xhigh implementation receipt with exact parent/candidate/runtime/deck
   hashes, static diff, and proof that no existing rule changed;
2. focused test output and hashed two-seat checked-engine artifact showing the
   candidate-owned Basic Psychic -> Powerful Hand -> two-Prize terminal path;
3. complete current-42 and historical shadow outputs, callback counts,
   duplicate controls, and semantic classification of every first difference;
4. compile/import, legality, loader, cache, package membership, archive hash,
   and packaged both-seat smoke evidence with zero faults;
5. a fresh root-authenticated live/quota/hash check and a final Sol-Ultra
   accept/reject audit of those raw artifacts before any write;
6. after any exploratory submission, replay IDs, correct-seat action traces,
   errors/max-step status, and enough repeated public evidence to distinguish
   intended terminal conversion from score noise.

