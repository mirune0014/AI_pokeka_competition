# Strategy selection: public role-complete Pokemon-commitment dominance v1

Status: `PRE_EDIT_CENSUS_ONLY`

No candidate source is authorized until every immutable actionability gate
passes.

## Bound lineage and stopped predecessor

- formal parent `main.py` SHA-256:
  `558EE5DB29E001428B0D59813613FABEE8E15B96E422746C104BDFAB4DC22DB6`
- formal parent deck SHA-256:
  `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`
- source manifest SHA-256:
  `90A512D5C9AE5EAD8DF92F370C32716959EC0929F9465451E7BB0926DBEB5A68`
- stopped terminal census root report SHA-256:
  `DC8A74945964896603583AECA068B80661DD231FE9759C05BE3441EFCE56D77E`
- stopped terminal independent audit SHA-256:
  `F41954FFA3538D77B1495FDAF153EC15F9FE1499BFF7E27CF220FBD718B57B69`

The formal parent gives a playable Basic Pokemon a strong generic play score.
The frozen corpus contains 700 parent `PLAY_POKEMON` selections over 523 turns
and 201 replays; 696 are owner-free.  Existing formation rules protect setup,
donk prevention, and first executable backup, but no final accepted rule proves
that a later Basic commitment has a concrete public role before spending both
the hand card and Bench slot.

The stopped terminal-attack rule is not reproduced or stacked.  This rule is
only about a nonterminal current attack versus a role-redundant Basic play.

## Single human-play principle

Capture the complete public observation and pre-owner vector, then invoke the
formal parent exactly once.  Never unwind or replay parent state.

Return the exact parent for result/reset/deck states, forced or mandatory
callbacks, non-clear MAIN, invalid parent output, any inherited or newly armed
owner/watch/callback, an inherited terminal/Boss line, or any current exact
terminal attack.

Only an owner-free clear MAIN parent choice that plays a Basic Pokemon is
eligible.  Compare two public plans independently of the parent's score:

1. `ATTACK_NOW`;
2. `PLAY_BASIC -> SAME_ATTACK`.

Admit a comparison only when exactly one semantic nonterminal attack is
currently legal, payable, and `EXACT` under the final public combat oracle, and
the complete legal Basic-play set can be projected without hidden information.
After each Basic play, the same attacker and attack must remain legal and have
identical payment, final damage, KO, Prize yield, public effect, and finishing
clock.

A Basic play is never redundant when it supplies any exact public role:

- prevents losing from a one-Pokemon board;
- creates the first executable backup attacker;
- is a current Turbo Flare or other exact acceleration recipient;
- supplies a public evolution chassis whose visible evolution plus exact
  attachments makes an executable attack route;
- supplies a useful promotion or retreat pivot;
- supplies a one-Prize wall that changes the Prize clock;
- changes current-attacker survival or an exact public terminal reply;
- increases the ready-attacker set, next payable attack, or attack-chain depth.

Unknown future draws, topdecks, hidden Prize identities, speculative future
evolutions, and hidden opponent cards prove neither a role nor redundancy.
Incomplete attack, effect, or reply semantics return the parent.

If every currently playable Basic is role-redundant, the parent selected one of
them, and retaining that physical card plus Bench slot is strictly better in
the public resource ledger, emit the unique exact nonterminal attack.  Otherwise
return the parent.

This rule owns no transaction.  Identical retries still call the parent once,
then rebind the same semantic attack only when snapshot, option multiset,
parent semantic, and pre/post owner fingerprints agree.  A retry never advances
counters.  No replay, opponent, deck, seed, matchup, or option-index predicate
is permitted.

## Precedence

1. Legality, result/reset/deck and mandatory/forced selection.
2. Existing parent terminal, Boss, owner, watch, effect, and callback handling.
3. Exact current terminal attack remains outside this rule and returns parent.
4. Public role-complete Basic-play comparison.
5. Exact formal-parent action.

## Frozen pre-edit census

Replay the formal parent over the bound manifest in exact order and write:

- `all_callback_rows.csv`;
- `pokemon_commitment_opportunities.csv`;
- `causal_first_differences.csv`;
- copied `source_manifest.json`;
- `summary.json`.

Required evidence records provenance, schedule identity, callback state,
pre/post owners, parent action and family, complete option semantics, Basic card
ID/serial, Bench and lineage inventory, current attack/payment/oracle, terminal
exclusion, projected post-play attack equality, board-out protection, first
backup, acceleration recipient, evolution/attachment conversion, pivot/wall,
reply/survival, ready-attacker and chain-depth deltas, resource-ledger delta,
contract action/semantic/validity, rejection/classification, retry identity,
first causal difference, unreachable-after-difference, hidden-information flag,
collision and error.

Only the earliest predicted difference per replay-seat is causal.  Later
baseline callbacks after the first change are unreachable and do not inflate
frequency.

## Immutable implement/stop gates

Require every item:

- exact bound hashes, 207 replays, 209 target seats, 25,880 unique scheduled
  parent calls, and zero manifest mismatch;
- reproduce 700 parent Pokemon plays, 523 turns, 201 replays, all Duraludon,
  and 696 owner-free rows, or record the discrepancy and stop;
- at least 64 fully classifiable role comparisons across 40 replays and both
  seats;
- at least 32 earliest causal differences across 24 replays, at least 12 from
  each seat;
- at least 48 independent `PLAY_HAS_PUBLIC_ROLE` controls across 32 replays and
  both seats;
- controls cover at least three of: first backup, board-out protection,
  acceleration recipient, executable evolution/attachment conversion,
  pivot/one-Prize route, exact reply improvement;
- differences cover at least two nonterminal attack semantics and both current
  KO and non-KO states;
- root labels every causal difference `GOOD_CAUSAL` and sampled positive holds
  `CORRECT_HOLD`;
- zero terminal-rule recreation, owner collision, mandatory-callback change,
  hidden-information use, unsupported prediction, invalid action,
  semantic-copy difference, stale retry, or error.

Any failure is:

`STOP__PUBLIC_ROLE_COMPLETE_POKEMON_COMMITMENT_NOT_BROADLY_ACTIONABLE`

Thresholds must not be lowered.

## Regression risks

Critical risks are calling a future attacker redundant, suppressing donk
protection, missing a visible acceleration recipient or evolution conversion,
undervaluing a one-Prize wall/pivot, assuming an unsupported opponent reply is
harmless, interfering with PFC or Explorer formation, and indirectly recreating
the stopped terminal rule.  Complete public role proof and reply equality are
mandatory.
