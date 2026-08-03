# Strategy clarification: preserve S81 evolution; lock at S83

## Decision

**AMEND under option A; do not reject the hypothesis.** The selected rule
remains the nonterminal prize-lead one-Prize Active KO lock at destination
`autonomous_gold_20260715/candidates/alakazam_certified_prize_lead_one_prize_active_ko_lock_v1`.

This immutable clarification supersedes every statement in
`STRATEGY_SELECTION.md` (SHA-256
`82B26E25D1C8B45FF09522C25AD3168A5C5D7D43BAE2AC233A5F343ACFE8A2C1`)
that treats `87079669/S81` as a positive or as an optional Psychic Draw
action. The original report must not be implemented alone. All other
fail-closed requirements and numerical gates remain in force.

The amended second positive is `87079669/S83`: preserve the S81 evolution and
S82 Psychic Draw exactly, then replace the parent's S83 Poke Pad with the
unique lethal Powerful Hand. No evolution exception is permitted.

## Verified facts used

Root's focused verifier and result are:

- `analysis/54853109_first9_losses_20260720/verify_root_s81_s83.py`, SHA-256
  `7CDE4134CB4D5F8DB97CF419FCC2A65DD82F8466C5458C791D0CB91D813A7AA3`;
- `analysis/54853109_first9_losses_20260720/ROOT_VERIFIED_S81_S83.json`,
  SHA-256
  `43F10137E4E702724263B2E0D4F156DA1A4967879E0FE9C23CC62737F146A54E`.

It re-executed all 78 target-seat callbacks from replay `87079669` (replay
SHA-256
`8DA69F2A56C3B701B6FB98F5B2D490D1DF6B5EE5C49265DAC7CE203AE0F39506`)
with zero invalid actions and zero candidate-parent differences. The exact
sequence is:

1. S81, turn 13 action 1: hand `4`, deck `11`, Prizes `4/6`; Active old paid
   Alakazam `743/s11` has unique Powerful Hand option `9` for `80` into Abra
   `741/s77` at `50` HP. The parent's `[0]` is raw type-9 EVOLVE: Alakazam
   `743/s12` from hand onto Bench Kadabra `742/s9`. It is not Psychic Draw.
2. S82: hand `3`, deck `11`; the new Bench Alakazam `s12` exists and
   `appearThisTurn == true`. The parent takes the forced Psychic Draw YES
   callback `[0]`. This must remain parent-identical.
3. S83, turn 13 action 3: hand `6`, deck `8`, Prizes `4/6`; the same Active
   `s11` remains paid and Abra `s77` remains at `50` HP. Powerful Hand option
   `14` now deals `120`. The formed Bench contains Alakazam `s12` and the
   pre-existing Alakazam `s13`; the opponent has two Benched Pokemon. The
   parent's `[6]` is Poke Pad `1152/s23`. This is the first eligible resource
   detour and the corrected positive action is Powerful Hand `14`.

The earlier mirror analysis correctly diagnosed the later resource-spend
sequence but attached its first-action label too early. The raw S81 option and
selection objects control; prose calling S81 Psychic Draw does not.

## Why amendment A remains coherent

The correction strengthens rather than changes the deck-theory mechanism.
Setup and board formation are completed first: the useful evolution is kept,
its fixed three-card draw is taken, and a second complete backup Alakazam is
formed. The old Active attacker remains ready throughout. At S83 the immediate
one-Prize KO is overdetermined (`120 >= 50`) while the player leads by two
remaining Prizes; only then does the rule stop additional optional resource
processing.

Thus attacker readiness, backup formation, hand damage, and immediate Prize
conversion coexist. The candidate saves Poke Pad and all downstream tools,
draw/recovery, Energy, and Boss expenditure while preserving the setup that
made the board resilient. It does not predict a draw, skip an evolution, or
trade board formation for tempo. Attack continuity after the KO remains an
evaluation question because the formed backups are not proven paid; the
existing both-seat, repeated-bucket, and absolute-strength gates therefore
remain mandatory.

The evidence still supplies three independent reachable nonterminal anchors
across both seats: `87076890/S173`, corrected `87079669/S83`, and
`87087306/S82`. S81 and S82 in episode `87079669` are prerequisites to the
second anchor, not activations. Prize-terminal S147 remains prior-art retention
only.

## Amended implementation contract

Apply the base certificate, nonterminal `P >= 2` condition, formed-backup
guard, one-Prize target, prize-lead guard, exact legality/damage certificate,
no-higher-Prize route, cache/state rules, and terminal exclusion from the
original report, subject to these controlling changes:

1. Evaluate the new helper only on an ordinary MAIN callback after the guarded
   parent has finalized its semantic action. It is stateless and re-evaluates
   each distinct observation; it carries no “attack later” latch.
2. **Every semantic EVOLVE is absolute parent identity**, including raw type
   `9`, every card/target/zone encoding, Rare Candy, and every Active or Bench
   evolution. If the parent selected EVOLVE, return the exact parent action,
   emit no lock-start telemetry, and do not mutate inherited state or cache
   ownership. There is no exception for a currently lethal attack.
3. Every evolution-owned selection or Ability callback also remains exact
   parent behavior. In particular, S82's Psychic Draw YES is not a MAIN
   decision and cannot start this rule. Finish the transaction, then permit a
   fresh certificate on the next ordinary MAIN observation.
4. At S83, after S81 and S82 resolve parent-identically, the ordinary MAIN
   certificate is evaluated afresh. Because the finalized parent action is the
   Poke Pad resource detour and all other guards pass, return the unique legal
   Powerful Hand option. Resolve actions semantically; never hard-code replay
   indices `6` or `14`, episode IDs, steps, serials, teams, or opponents.
5. Keep the original prohibition on overriding evolution, Poffin/Rare Candy/
   Basic setup, Energy attachment, Hammer, Stadium, retreat, END, another
   attack, or an unclassified action. This amendment does not weaken any
   negative or add an evolution exception.
6. If an implementation cannot produce exact parent identity at S81 and S82
   followed by its first difference at S83 using the public-state rule alone,
   reject it. Do not repair it with replay-specific state, an episode/step
   condition, or a persistent sequence flag.

## Corrected focused and shadow gates

Mandatory positives are now exactly:

- `87076890/S173`: Dawn `0` -> Powerful Hand `4`;
- `87079669/S83`: Poke Pad `6` -> Powerful Hand `14`;
- `87087306/S82`: Poke Pad `30` -> Powerful Hand `38`.

Mandatory retention checks added or clarified:

- `87079669/S81`: exact parent EVOLVE `[0]`, Alakazam `s12` onto Kadabra `s9`;
- `87079669/S82`: exact parent Psychic Draw YES `[0]`, including hand/deck
  transition `3/11 -> 6/8` and formed Alakazam `s12`;
- all EVOLVE actions in the focused and historical corpus, regardless of
  whether Powerful Hand is legal or lethal;
- S147 and all other Prize-terminal/board-terminal prior-art fixtures.

Focused exact-engine execution must prove the whole local sequence, not three
disconnected snapshots:

`S81 parent EVOLVE -> S82 parent YES/draw -> S83 candidate Powerful Hand -> KO
-> mandatory Prize callback`.

Require unchanged ownership/serial/zone transitions through S82, no inherited
latch or cache mutation, legal S83 attack resolution, the one-Prize KO, and the
saved Poke Pad still in hand before attack resolution. Perturb option ordering
and equivalent physical cards so semantic resolution, not frozen indices,
controls the result.

On the frozen public/historical shadow, the reachable first differences must
be exactly S173, corrected S83, and the seat-1 S82 recurrence. Any difference
at `87079669/S81` or `/S82`, any lost evolution/draw, any terminal-only start,
or any unclassified difference is an immediate semantic rejection regardless
of aggregate wins.

The compact-72 retention and formal-promotion thresholds in the original
report are unchanged. Numerical success cannot cure a failed sequence gate.
For the corrected episode, mechanism telemetry must demonstrate that board
formation happened parent-identically and the observed savings begin with
Poke Pad at S83. This is the discriminating proof that the candidate implements
the intended “setup first, then lock” rule rather than an attack-before-setup
shortcut.

## Regression risks and exact evidence needed next

The corrected rule deliberately spends three deck cards at S82 before the KO;
that cost buys a formed backup and six-card hand, but it can shorten the draw
clock. Conversely, attacking at S83 may forgo a useful Poke Pad search or later
setup despite the already mature board. The two backups are formed but not
shown paid at this boundary, so disruption and next-attacker readiness remain
the principal outcome risks. These uncertainties are why the rule is amended,
not accepted for adoption.

Next require, in order:

1. one isolated implementation diff from the exact guarded parent, with no
   EVOLVE or selection-callback exception and no terminal branch;
2. root-verified focused traces proving S81/S82 identity and S83 first
   difference plus the other two corrected positives and all negatives;
3. full frozen shadow classification showing no lost setup transaction or
   out-of-domain action;
4. the unchanged compact-72 schedule, duplicate controls, raw traces, zero
   action errors/max-step hits, and independent Sol-Ultra numerical audit;
5. only if retention passes, repeated nonterminal mechanism-linked outcomes,
   both-seat/adjacent-population safety, and the original full-144 adoption
   gates before a new rule-level accept/reject judgment.

