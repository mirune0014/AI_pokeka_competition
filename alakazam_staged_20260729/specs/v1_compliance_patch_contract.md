# V1 compliance patch contract

## Status

This is the immutable implementation contract for `V1_COMPLIANCE_PATCH`.

It closes three gaps found by the independent deliverable audit:

1. use the added Alakazam as a narrowly certified ready bench attacker;
2. use Boss's Orders to remove the unique publicly ready bench attacker;
3. remove the five deleted cards from v1 own-side policy routes.

This is an implementation authorization, not an adoption decision.

## Frozen inputs

- Repository HEAD before the patch: `54f09edb2b3f6dd2def7c2c49efde16dfeda97c9`.
- Source v1 directory:
  `alakazam_staged_20260729/versions/alakazam_newdeck_v1_package`.
- Source v1 policy closure:
  `856D8D200BF23F2368C4014351652D49DD89B9DFDEF7C87EF5B5BB39411E5F48`.
- Source v1 deck SHA-256:
  `F598F5E578D0440C96DC0492EAECF2E19739B7A23225BE57114A724EF7D0FB94`.
- Required normalized deck hash:
  `4414e8995e50c7a00d4b6aa7d9229f63c1dff5261643ec7cd86c4e329113ed69`.
- Frozen v0 closure:
  `D9ADBC03054AB1D2FFD1E1955D734DB1D14DA74C9D1088249A271F98EBCECD46`.
- Frozen historical implementation tree must remain byte-identical.
- Destination:
  `alakazam_staged_20260729/versions/alakazam_newdeck_v1_package_compliance`.

The destination must be created as an isolated copy of the source v1.
No source v0, source v1, report, evaluation, metric, or Kaggle file may be
modified by the implementation worker.

## Single hypothesis

Only card-package-specific routes that are provable from public information
are added. General H1 construction, post-KO recovery, matchup rules, learned
ranking, replay imitation, seed logic, and opponent-policy proxies are
forbidden.

## Ownership and priority

The existing priority of raw/parsed mismatch, parent transaction, inherited
duplicate owner, v1 duplicate rebinding, and an in-progress v1 transaction is
unchanged.

New arbitration is allowed only on an unowned MAIN callback.

When the inherited v0 action is a certified Powerful Hand KO, the order is:

1. terminal KO against the current Active;
2. `V1_BOSS_TERMINAL_PRIZE_KO`;
3. `V1_BOSS_UNIQUE_READY_ATTACKER_STOP`;
4. `V1_ALAKAZAM_4TH_READY_BENCH`;
5. the exact inherited nonterminal Powerful Hand KO.

When the inherited v0 action is not a certified KO, preserve the existing
order exactly:

1. terminal Boss;
2. Nighttime Mine;
3. Active Kadabra recovery;
4. Xerosic;
5. Lana;
6. Enhanced Hammer.

The new routes must not preempt the existing Xerosic, Lana, Hammer, Mine, or
Active-Kadabra corridors outside the explicit KO arbitration above.

## Narrow added-Alakazam route

Rule: `V1_ALAKAZAM_4TH_READY_BENCH`.

All conditions are required:

- The Active is a ready Alakazam.
- The inherited action is a nonterminal Powerful Hand KO against the current
  opposing Active.
- Exactly one bench Pokemon is a mature, not-appeared-this-turn, complete
  `Abra -> Kadabra` lineage.
- That Kadabra already has sufficient Psychic Energy to use Powerful Hand
  immediately after evolution.
- The Alakazam EVOLVE option is unique and targets that physical bench serial.
- Three other Alakazam physical serials are publicly present in the owner's
  discard or in-play evolution stacks.
- The exact deck certificate fixes the total Alakazam count at four.
- Deck count before the optional Ability is at least four.
- `Hfinal = Hbefore - 1 + 3 = Hbefore + 2` remains at least
  `Hreq = ceil(current_target_remaining_hp / 20)`.
- Attacker, bench lineage, target, option, and all protected component serials
  are unique.

Transaction:

`await_backup_alakazam_ability -> await_backup_alakazam_attack -> await_added_attack_verify`

Each child callback must rebind by stable option and physical serial, verify
the unchanged public board, hand/deck deltas, attacker, backup, and target,
and finish with the same frozen H0 Powerful Hand attack.

Reason tags:

- `V1_ALAKAZAM_4TH_READY_BENCH`
- `V1_ALAKAZAM_4TH_PUBLICLY_PROVEN`
- `V1_ALAKAZAM_H0_FLOOR_BLOCK`
- `V1_ALAKAZAM_PUBLIC_MUTATION_ABORT`

Existing Active-Kadabra recovery remains. It may use
`V1_ALAKAZAM_4TH_PUBLICLY_PROVEN` only when three other Alakazam serials are
publicly proven. Otherwise identical-card-copy attribution remains
`UNKNOWN_IDENTICAL_CARD_ID`.

This v1 route must not bench Abra, use Rare Candy, attach Energy, recover a
card, retreat, promote, search a hidden zone, or continue after a future KO.
Those operations remain exclusively in v2.

## Narrow Boss attack-stop route

Rule: `V1_BOSS_UNIQUE_READY_ATTACKER_STOP`.

All conditions are required:

- The inherited action is a nonterminal Powerful Hand KO against the current
  opposing Active.
- Card, attack, Energy, attack-cost, and current cost-modifier metadata are
  exact for every opposing in-play Pokemon.
- With only currently attached Energy, exactly one opposing Pokemon can
  attack now.
- That unique ready Pokemon is on the bench.
- After Boss, `Hbefore - 1` is sufficient to KO that target with Powerful
  Hand.
- The KO is nonterminal.
- Removing the target leaves no publicly ready opposing Pokemon.
- Boss option, SWITCH child, attacker, old Active, and target serials are all
  unique.

Unknown metadata, multiple ready attackers, an active ready attacker,
ambiguous Energy, an unresolved attack condition or cost modifier, multiple
targets, or an H-floor miss must not fire.

Reuse the existing Boss transaction:

`await_boss_child -> await_boss_attack -> await_added_attack_verify`

Add `mode=UNIQUE_READY_ATTACKER_STOP` and reverify the ready-set proof before
the final attack.

Reason tags:

- `V1_BOSS_UNIQUE_READY_ATTACKER_STOP`
- `V1_BOSS_READY_SET_AMBIGUOUS`
- `V1_BOSS_H_MINUS_1_FLOOR_BLOCK`
- `V1_BOSS_PUBLIC_MUTATION_ABORT`

The claim is limited to removing the only currently public ready attacker.
Do not predict a future draw, attachment, evolution, switch, or opponent
policy.

## Semantic removal of deleted own-side routes

Define one denylist:

`REMOVED_OWN_CARD_IDS = {142, 858, 1156, 1161, 1264}`

It covers Genesect, Psyduck, Lucky Helmet, Handheld Fan, and Battle Cage.

Within the isolated v1 candidate, these IDs must not participate in owner-side:

- setup, reserve, search, or retreat priority;
- PLAY or ATTACH scoring;
- reservation or transaction creation;
- thin-deck/draw-clock guards;
- own Stadium play/replacement scoring;
- own protected-source assumptions.

Opponent-side card interpretation and public Stadium effect interpretation
must remain intact.

Optional prompts must exclude deleted own cards. In a deliberately corrupted
forced prompt where no other legal choice exists, do not create a special
strategic route; choose the deterministic lowest physical serial and tag
`V1_REMOVED_CARD_FORCED_PROMPT_ONLY`.

The exact candidate `deck.csv` and `runtime/deck.csv` must contain zero copies
of all five IDs. The frozen v0 directory and closure must remain unchanged.

## Fail-closed invariants

- The inherited v1 delegate is called exactly once on each nonduplicate
  callback.
- Nonfire preserves inherited action, Reason Code, transaction, duplicate
  state, and all parent mutable state exactly.
- A child prompt mutation or public-state mutation aborts before an
  irreversible follow-up action.
- No first-legal fallback is introduced.
- No new generic fallback is introduced.
- No matchup label, seed, saved replay action, learned score, or hidden-zone
  order may influence the action.
- The deck remains byte-identical to the source v1.

## Required fixtures

- Terminal current KO precedes all new routes.
- Terminal Boss precedes a nonterminal current KO.
- Boss unique-ready positive case.
- Boss multiple-ready, active-ready, H-floor, metadata ambiguity, cost
  modifier, child reorder, and public mutation negative cases.
- A case in which two Boss copies are public/discarded and the remaining copy
  is used for terminal KO and for attack-stop.
- Existing Active-Kadabra recovery with three other Alakazam publicly proven.
- Ready Active Alakazam plus mature energized bench Kadabra plus three other
  public Alakazam serials.
- Alakazam public-copy shortage, immature Kadabra, missing Energy, multiple
  EVOLVE options, deck count at most three, and terminal H0 negative cases.
- One own-route nonfire fixture for each of the five deleted IDs.
- Opponent/public interpretation fixtures for Genesect, Psyduck, tool
  metadata, and Battle Cage.
- For every nonfire fixture, exact inherited v1 action, transaction, parent
  state, Reason Code, and fallback equality.
- Three repetitions of every changed positive fixture with identical action
  and trace.
- All inherited v0 and v1 tests.
- Frozen v0 and source-v1 closure hashes unchanged after implementation.

## Implementation handoff

The worker returns:

- changed files;
- exact tests and results;
- candidate policy closure and file count;
- SHA-256 for every changed or added file;
- deck byte-equality proof;
- frozen v0/source-v1 hash recheck;
- known unimplemented or UNKNOWN conditions.

No evaluation, adoption recommendation, report rewrite, packaging, or Kaggle
operation belongs to this implementation task.
