# Strategy selection: public unique terminal-attack dominance v1

Status: `PRE_EDIT_CENSUS_ONLY`

No candidate source is authorized until the immutable census gate passes.

## Bound lineage and gap

- formal parent `main.py`: `558EE5DB29E001428B0D59813613FABEE8E15B96E422746C104BDFAB4DC22DB6`
- formal parent deck: `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`
- source manifest: `90A512D5C9AE5EAD8DF92F370C32716959EC0929F9465451E7BB0926DBEB5A68`
- stopped search-guard report: `4CE04C09BCEA147DF80F90620BDB2CE91332D7154B9D883835C59E8F38ECAC9D`

The stopped search-specific census found four raw search replacements in three
causal turns/replays. All four were the same broader defect: a unique exact
Metal Defender attack immediately won the game, while the parent selected a
Pokémon-search Item. Search-card identity is not the correct activation
property.

The parent protects a terminal when the parent already chose an attack or a
certified Boss line. Its PF Gear layer repairs a direct finish only when the
parent selected Gear. No accepted rule currently makes a unique immediate
terminal attack dominate every owner-free clear-MAIN parent family.

## Single hard rule

Capture the public observation and complete pre-owner vector, then call the
formal parent exactly once. Do not unwind or replay the parent's runtime state.

Return the exact parent for deck/result/reset states, forced selections,
non-clear-MAIN callbacks, any owner/watch/effect callback already live, any
owner newly armed by the parent, or an inherited exact terminal transaction.

Only owner-free clear MAIN is eligible:

- `context == MAIN`, `minCount == maxCount == 1`;
- no effect, context card, or looking zone;
- unresolved game and a complete unique public serial universe;
- at least two legal semantics unless the parent already emits the attack.

Enumerate every legal `ATTACK` option from the actual Active. Every distinct
semantic attack requires exact public access, exact Energy payment, and an
`EXACT` final public-combat-oracle certificate with exact source/target serials,
HP, damage pipeline, KO result, Prize yield, and admitted public effects.

Duplicate UI entries may collapse only when semantic attack, payment, and the
complete oracle certificate are identical. Any unsupported legal attack makes
terminal uniqueness unprovable and returns the parent.

A terminal witness is either:

- an exact KO with exact Prize yield at least the count of our remaining Prize
  cards; or
- an exact KO while the opponent Bench is exactly empty.

Prize identities are never read. Only the public count is used.

Emit the attack only when exactly one terminal semantic exists. It dominates
every nonterminal parent PLAY, EVOLVE, ATTACH, RETREAT, ABILITY, END, or ATTACK
regardless of setup/resource score. If the parent already emits the same attack,
record a semantic hold.

Return the parent on zero terminals, multiple terminal semantics, unsupported
or incomparable attacks, ambiguous binding, stale revalidation, or exception.
This rule owns no multi-callback transaction.

An identical retry still calls the parent once, then rebinds the same semantic
attack only after snapshot, option multiset, parent semantic, and pre/post owner
fingerprints agree. Changed game, seat, turn, action count, result, or snapshot
clears the retry identity.

No replay, opponent, deck, matchup, seed, or option-index predicate is allowed.
Public card and attack identifiers may validate metadata and bind current legal
semantics only.

## Precedence

1. Legality, mandatory selection, deck/result/reset, and malformed observations.
2. Any inherited or newly armed owner/watch/transaction, including Boss finish,
   H3, PFC, PCRD, cumulative arbitration, DPER callback ownership, and PF Gear.
3. Unique exact public terminal attack.
4. Exact formal-parent action.

## Frozen pre-edit outputs

Produce:

- `all_callback_rows.csv`
- `causal_first_differences.csv`
- copied `source_manifest.json`
- `summary.json`

Required row fields include:

`replay, replay_sha256, seat, step, turn, turn_action_count, snapshot_sha256, context, min_count, max_count, result, clear_main, forced, option_multiset, pre_owner_vector, post_owner_vector, parent_started_owner, parent_action, parent_semantic, parent_valid, parent_action_family, inherited_terminal_kind, attacker_serial, target_serial, remaining_prizes, opponent_bench_count, legal_attack_semantics, duplicate_attack_groups, attack_access_statuses, attack_payments, oracle_statuses, unsupported_reasons, attack_damage, attack_ko, attack_prize_yield, terminal_kind, terminal_semantic_count, contract_action, contract_semantic, contract_valid, predicted_difference, duplicate_retry, first_causal_difference, unreachable_after_terminal_override, classification, hidden_info_used, owner_collision, error`.

Normalize the parent family only for evidence:

`PLAY_POKEMON, PLAY_ITEM_SEARCH, PLAY_ITEM_OTHER, PLAY_SUPPORTER, PLAY_STADIUM, PLAY_TOOL, EVOLVE, ATTACH, RETREAT, ABILITY, END, ATTACK, OTHER_MAIN`.

Only the earliest predicted terminal replacement per `(replay_sha256, seat)` is
causal. Every later baseline callback is unreachable because the earlier
candidate attack wins; later rows must not inflate frequency.

## Immutable implement/stop gate

Require every item:

- exact 207 replays, 209 target seats, 25,880 parent calls, bound hashes, unique
  raw keys, and zero manifest mismatch;
- zero invalid parent/contract action, hidden-information use, owner collision,
  semantic-copy prediction, exception, stale nonidentical retry, or unclassified
  clear-MAIN row;
- reproduce the known residue exactly: four raw search rows, three earliest
  causal starts, three replays, both seats, Poké Pad 3, Ultra Ball 1, all Metal
  Defender;
- at least 24 earliest causal replacements across at least 16 replays;
- at least six causal replacements from each seat;
- at least three normalized parent-action families with at least three causal
  replacements each;
- at least twelve causal replacements outside `PLAY_ITEM_SEARCH`, spanning at
  least two non-search families;
- no single family above 75% of causal replacements;
- at least 24 parent-equal unique-terminal controls across 16 replays and both
  seats;
- root inspection labels every causal replacement `GOOD_CAUSAL`, and sampled
  inherited-owner, parent-terminal, multiple-terminal, and unsupported holds are
  correct.

Any failed gate is:

`STOP__PUBLIC_UNIQUE_TERMINAL_ATTACK_DOMINANCE_NOT_BROADLY_ACTIONABLE`

Thresholds must not be relaxed.

## Regression risks

Critical risks are a false KO or Prize certificate, hidden Prize use, incomplete
Memory Dive/access handling, unsupported spread or simultaneous-KO effects,
treating duplicate terminal attacks as unique, overriding a live/new owner,
double-counting baseline callbacks after the first terminal override, and
overlapping the existing Gear direct-finish veto. Parent-emitted terminal attacks
and Gear/Boss terminal transactions must remain semantic holds.

Only a passing census may authorize one isolated Sol-xhigh implementation worker.

