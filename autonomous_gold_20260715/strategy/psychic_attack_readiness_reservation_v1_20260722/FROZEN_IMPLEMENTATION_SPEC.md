# Frozen implementation specification — Psychic attack-readiness reservation v1

Frozen by root on 2026-07-22 JST after the 38-public-game checkpoint for
Kaggle submission `54888159`.

## Parent and destination

- Exact parent directory:
  `autonomous_gold_20260715/candidates/alakazam_integrated_override_admissibility_gate_v1`
- Parent `planner_final_policy.py` SHA-256:
  `974C4EACFA730D4CC0FAB7A84F82A0E5F004CC3443B39AF517673B630AB98CE1`
- Parent `main.py` SHA-256:
  `93E2567F4352EE4C4FCEEB3D32B954119F3DC4E8F96DF5498317E781C5804086`
- Parent `_cumulative_parent.py` SHA-256:
  `65527AEE74AED600B94C4A555BE9464A48E53E118C9FD674DB6403208706325D`
- Parent `deck.csv` SHA-256:
  `A7B6C7972915D09F6314C42633AA89D82B55DDF0A7199F7138E681FA52516529`
- Fresh candidate:
  `autonomous_gold_20260715/candidates/alakazam_psychic_attack_readiness_reservation_v1`
- Fresh implementation evidence:
  `autonomous_gold_20260715/implementation/alakazam_psychic_attack_readiness_reservation_v1`

The exact submitted admissibility child is the implementation parent. Do not
roll back to the direct integrated parent. Copy the parent tree first, preserve
the unchanged 60-card deck, and implement exactly one unified rule. No Boss,
immunity, survival, acquisition, deck-list, or matchup-specific change belongs
in this candidate.

## Hypothesis

When the finalized parent is about to consume the turn's manual attachment on
a non-Psychic/non-attacker route, attaches the reserved Psychic elsewhere, or
ends the turn, reserve one visible Basic or Telepath Psychic Energy for the
unique public Abra-line attacker. Form H0 when that attacker is Active now;
otherwise form H1 on the Bench and preserve it through a forced promotion.
The transaction is successful only when it converts the reserved Energy into
an exact, strictly positive public attack.

## Initiation certificate

Initiate only when all conditions are exact and public:

1. Selection context is ordinary `MAIN`, game turn is at least two, own hand is
   fully materialized and matches `handCount`, the manual attachment is unused,
   and action/status metadata is unambiguous.
2. No transaction owner exists before or after the single finalized-parent
   call. Existing terminal-Prize, exact Boss, Powerful Hand floor,
   stranded-retreat, guarded Teleportation, recovery, Hilda/Enriching, Fez,
   Run Away, Fan, and admissibility transactions have precedence.
3. H0 is the unique Active Kadabra or Alakazam that cannot currently pay its
   sole Psychic attack but becomes payable after one visible hand Basic or
   Telepath Psychic Energy:
   - Kadabra: Super Psy Bolt `1071`;
   - Alakazam: Powerful Hand `1072`, using the post-attachment hand count.
4. The resulting attack has a strictly positive exact public outcome. Reject
   Mist, Rock/Fighting protection, Psychic resistance, unknown modifiers,
   effect prevention, or any ambiguous attack/payment metadata.
5. If no H0 exists, H1 may be the exactly one publicly complete Bench Kadabra
   or Alakazam satisfying the same one-Psychic and positive-outcome test, only
   while own Active is not an Abra-line attacker, exposes no legal attack, and
   has no legal `RETREAT` before attachment.
6. Choose H0 before H1. Choose Basic Psychic before Telepath, then ascending
   physical serial and stable option key. Enriching Energy and Tools never
   satisfy this reservation.

Start only if the parent selects the same certified attachment, selects a
different Energy attachment that consumes the budget, attaches the reserved
Psychic to another Pokemon, or selects `END`. Ordinary PLAY, EVOLVE, ABILITY,
Supporter, Stadium, and other setup actions remain parent-owned; reconsider on
the next ordinary MAIN callback. Never initiate Hilda acquisition or override
Dawn or Boss.

## Transaction stages

H0 stages:

`await_attach_resolution -> optional_telepath_prompt -> await_attack -> await_resolution`

- If the parent chose the same attachment, return the exact parent action and
  install the latch as `PSYCHIC_READINESS_PARENT_IDENTICAL`.
- Otherwise restore the complete pre-parent mutable snapshot, return the exact
  certified attachment, and install only this transaction.
- Suppress only an exact optional Telepath Basic-search prompt with `[]`. If the
  prompt is mandatory or semantically incomplete, abort to the already-called
  parent.
- Revalidate turn/player, H0 lineage and serial, Energy ID/serial, opposing
  target, hand count, public effects, attack payment, and unique legal attack;
  then attack immediately.

H1 stages:

`await_attach_resolution -> optional_telepath_prompt -> reserved_until_exposure`

- Do not initiate retreat and do not force an ordinary switch.
- Pass ordinary finalized-parent actions while the reservation remains exact.
- When the original Active has disappeared and the engine exposes an exact
  forced `SWITCH/TO_ACTIVE` prompt, promote the reserved payable H1, reclassify
  it as H0, and use its unique positive attack at the following MAIN callback.
- If a later own MAIN arrives while another Active remains, complete the latch;
  the energized H1 remains ordinary parent state.

If any higher-precedence parent owner appears, clear only this latch and
preserve the parent's route.

## Parent reconciliation, aborts, and duplicates

- Check this candidate's duplicate identity before any parent call. Identical
  callbacks return the cached action without stage advancement or a second
  parent call.
- On each first-seen callback, freeze the entire parent mutable state and call
  the finalized parent exactly once to obtain a validated fallback.
- Before commitment, certificate failure returns the exact parent action and
  post-state with no new mutation.
- A successful override restores the full pre-parent state before installing
  only this transaction.
- During continuation, invalid or stale state clears only this latch and
  returns the already-computed parent action/post-state. Never broadly clear,
  resurrect, or reverse an already materialized world action.

Required trace classifications:

- `PSYCHIC_READINESS_COMMIT_H0`
- `PSYCHIC_READINESS_COMMIT_H1`
- `PSYCHIC_READINESS_PARENT_IDENTICAL`
- `PSYCHIC_READINESS_PROMOTE`
- `PSYCHIC_READINESS_ATTACK`
- `PSYCHIC_READINESS_COMPLETE`
- `PSYCHIC_READINESS_ABORT`
- `PSYCHIC_READINESS_DUPLICATE`

Every transaction trace records stage, H0/H1 lineage and serial, selected
Energy ID/serial, intended attack, exact parent and returned actions, public
snapshot hash, and an exact reason code.

## Mandatory positives

Test each original and semantic-seat-swapped state:

- `87368866/S77`: Basic Psychic to Active Alakazam, then Powerful Hand.
- `87355030/S73`: Telepath Psychic to Active Kadabra, then Super Psy Bolt.
- `87351582/S34`: Telepath Psychic to Bench Alakazam, never Psyduck.
- `87356191/S28`: Telepath Psychic to Bench Kadabra, never Genesect.
- `87365156/S71-S72`: retain the existing Basic-to-Kadabra attachment and
  attack action-identically.
- Checked-engine H1 continuation in both semantic seats: opponent KO, forced
  promotion of the reserved attacker, then exact next-MAIN attack.

## Mandatory negatives and retention

The following remain exact-parent-identical:

- `87352178/S23`, `87351582/S70`, and `87365156/S86`, because no visible
  Basic/Telepath Psychic is available.
- Protected or zero-outcome states including `87368297/S36` and `87367596`.
- Multiple H1 candidates, an already legal retreat, spent attachment, status
  lock, incomplete hand or metadata, ambiguous options, stale serials, a
  required Telepath search, and every existing transaction owner.

Retention is conjunctive: all admissibility-gate repair/retention anchors,
terminal `87139766/S124`, Boss routes `87214287/S128-S129` and
`87220395/S126`, and the existing Run Away, Fan, stranded-retreat, terminal,
Boss, duplicate, and package-loader suites remain unchanged.

## Breakage-only release gate

Local wins and losses are diagnostic and nonblocking for this user-authorized
exploratory live probe. Packaging is forbidden on any structural or mechanism
failure:

1. Compile/import, unchanged legal 60-card deck with one ACE, sole/last public
   callable, dependency closure, source/runtime parity, and cache-free tree.
2. All mandatory positive, negative, owner-precedence, rollback, stale-state,
   and duplicate tests pass in both semantic seats.
3. Current-38 plus adjacent historical callback shadows have zero invalid
   actions, duplicate mismatches, extra parent calls, emergencies, missing
   traces, or unclassified first forks. Every candidate-parent first fork is a
   certified Psychic-readiness classification.
4. Checked-engine H0 and H1 transactions complete in both seats, including H1
   forced promotion and immediate next-MAIN attack.
5. Clean extraction is byte-bound and dependency-complete. Duplicate both-seat
   smoke against Historical-Silver, mirror, Starmie, and Mega Lucario has zero
   action errors and max-step hits. Report wins, but do not use them as a
   release gate.

Primary risks are premature low-value attacks, skipped useful setup, H1 latch
collision, and protected-target attacks. Do not broaden a condition to make a
fixture pass.
