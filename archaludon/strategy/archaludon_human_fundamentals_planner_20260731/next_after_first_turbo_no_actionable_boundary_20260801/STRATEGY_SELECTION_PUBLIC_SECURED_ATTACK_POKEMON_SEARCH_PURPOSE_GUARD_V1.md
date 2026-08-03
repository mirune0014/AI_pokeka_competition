# Strategy selection: public secured-attack Pokémon-search purpose guard v1

Status: `PRE_EDIT_CENSUS_ONLY`

No source edit is authorized until the immutable census below passes.

## Bound lineage

- formal parent `main.py`: `558EE5DB29E001428B0D59813613FABEE8E15B96E422746C104BDFAB4DC22DB6`
- formal parent `deck.csv`: `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`
- source manifest: `90A512D5C9AE5EAD8DF92F370C32716959EC0929F9465451E7BB0926DBEB5A68`
- first-Turbo stop report: `7277B8ECD82C577CF775CCF2C058DACAAA01435F00A9A99B9041C1889B21F458`

The first-Turbo hypothesis stopped with 133 natural transactions but only ten
semantic differences, all overfill reductions. This successor does not stack
that stopped rule.

## Verified motivation

The parent assigns a broad high score to generic Items. It has narrow positive
transactions for H3, PFC, and Pokégear-to-Boss, but it does not have a general
purpose guard for Pokémon-search Items. Root action-frequency evidence records
Poké Pad in 372 plays across 310 turns and Ultra Ball in 229 plays across 223
turns. A read-only orientation scan suggested a broad surface of clear-MAIN
snapshots containing an exact attack and one of those search Items, but the root
must reproduce the surface before using it.

## Single hypothesis

At an owner-free clear `MAIN` callback, call the exact parent once. Intervene
only when the parent selects a legal Pokémon-search Trainer identified by its
normalized public effect and all of the following are proven from the current
public state:

1. A unique exact payable attack is legal now.
2. The current attacker is ready and an independent executable backup or
   zero-retreat continuation already exists.
3. No visible deficit remains for setup, an evolution chassis, donk protection,
   a one-Prize wall, a backup attacker, or the current Prize route.
4. The search cannot improve a certified current terminal, KO, Prize take,
   attack legality, survival boundary, or guaranteed next attack.
5. Conserving the search card and any required discard cost strictly dominates
   playing it on this public vector:

`terminal -> current prizes -> current KO -> attack this turn -> guaranteed next attack -> prize exposure -> protected reserve`

If and only if all five conditions hold, emit the unique exact attack semantic.
Otherwise return the exact parent action.

This rule does not predict search results, draws, Prize cards, opponent hands,
or future deck order. It does not use opponent identity, replay identity, or
action imitation.

## Positive boundaries

- Poké Pad is selected, a unique legal attack is already certified, a ready
  independent successor is visible, Bench/line roles are complete, and the
  search cannot change KO, Prize, survival, or next-attack continuity: attack.
- Ultra Ball is selected under the same complete public board, while every
  legal discard pair consumes protected attack/continuity reserve and no public
  search target can improve the certified route: attack and preserve all three
  resources.
- Repeated identical snapshots must produce the same semantic attack and are
  deduplicated only after semantic equality is proven.

## Negative boundaries

Return the exact parent when any of these holds:

- H3, PFC, PCRD, cumulative arbitration, DPER action ownership, Pokégear-Boss,
  or any other transaction/watch/action owner is live.
- Search creates the only backup, prevents a one-Pokémon loss, establishes a
  required Duraludon/evolution chassis, supplies a one-Prize wall, or has a
  unique public purpose for the current Prize route.
- Ultra Ball has a unique safe public discard pair and an executable public
  target purpose.
- Search can upgrade current terminal, KO, Prize take, attack legality, public
  survival, or guaranteed next attack.
- No unique payable attack exists, multiple attacks are incomparable, an attack
  or effect is unsupported, or any conclusion needs hidden information.
- The comparison ties.

The guard creates no multi-callback transaction. If it does not replace the
parent's current search action with the current certified attack, later search
callbacks remain wholly parent-owned.

## Required immutable pre-edit evidence

Freeze callback-level rows containing at least:

- replay name/hash, target seat, step, turn, turn-action count, snapshot hash;
- context and game epoch;
- owner set before and after the one parent call;
- legal option semantics and exact parent semantic;
- normalized public search family/effect and public discard requirement;
- all legal exact attack semantics and the selected unique attack;
- current attack readiness, current KO/Prize result, terminal status;
- visible Bench roles, evolution deficits, backup readiness, one-Pokémon-loss
  risk, one-Prize-wall deficit, and next-attack continuity;
- protected hand/field/discard reserve and all legal Ultra Ball discard-pair
  semantics visible at the current callback;
- public outcome vectors for parent search and attack;
- predicted semantic difference, classification, rejection reason, validity,
  hidden-information use, owner collision, duplicate status, and error.

Deduplicate by `(replay_sha256, seat, stage, snapshot_sha256)` only after
identical parent/contract semantics and owner state are proven.

## Immutable implement/stop gate

Implementation is authorized only when the census has all of the following:

- exact bound hashes, 207 replay files, 209 target seats, 25,880 parent calls,
  and zero manifest mismatches, duplicate output keys, invalid parent actions,
  or owner-state mismatches;
- the root reproduces or explicitly explains the orientation surface;
- at least 80 classifiable eligible turns across 50 replays and both seats;
- at least 24 predicted direct semantic differences across 16 replays and both
  seats;
- at least eight zero-discard-cost search no-purpose differences and at least
  eight discard-cost no-purpose or unsafe-reserve differences;
- at least 24 purposeful-search parent-equal controls across 16 replays,
  covering both search families and inherited-owner controls;
- root inspection labels every predicted difference `GOOD_CAUSAL` and every
  sampled hold `CORRECT_HOLD`;
- zero hidden-information assumptions, opponent/deck/replay-ID predicates,
  semantic-copy noise, stale nonidentical retries, or non-MAIN changes.

Any failed gate is:

`STOP__PUBLIC_SECURED_ATTACK_SEARCH_GUARD_NOT_BROADLY_ACTIONABLE`

The thresholds must not be weakened.

## Regression risks

The main risks are suppressing backup formation, donk protection, safe Ultra
Ball fuel, evolution setup, a one-Prize wall, or a search-enabled Prize upgrade;
mistaking a hidden-zone possibility for a public purpose; and colliding with an
existing transaction. Same-turn attack availability alone is insufficient.
Both the no-purpose certificate and strict protected-resource dominance are
required.

If this pre-edit census passes, one isolated Sol-xhigh worker may implement the
guard directly from the formal parent. Adoption would still require exact
callback tests, legal 60-card/ACE checks, both seats, identical seeds, historical
Silver strength, adjacent-matchup floors, completed changed positions, zero
errors/max-step regressions, and a final Sol-Ultra accept/reject judgment.

