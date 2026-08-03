# First cumulative Archaludon integration selection

Date: 2026-07-30 JST  
Decision type: read-only pre-implementation strategy selection

## Authority and verified facts

- Controlling cumulative policy:
  `autonomous_gold_20260715/strategy/archaludon_hierarchical_rules_20260729/CUMULATIVE_RULE_INTEGRATION_POLICY_20260730.md`,
  SHA-256
  `F8E81D3872C809477068E7C9B476302BE20C14001127EA308C4C80B4CB95BB66`.
- Formal comparison and rollback source:
  `analysis_outputs/reference_agents/historical_silver_archaludon_54495224/main.py`,
  SHA-256
  `F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E`.
- Exact deck:
  `analysis_outputs/reference_agents/historical_silver_archaludon_54495224/deck.csv`,
  SHA-256
  `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`.
- Current coverage matrix:
  `autonomous_gold_20260715/strategy/archaludon_hierarchical_rules_20260729/HIERARCHY_COVERAGE_MATRIX.md`,
  SHA-256
  `AF11CA8EDBAC1538E4F241D61C77F07C9BA7739833ACAC664625E9C484F0F1A1`.
- Search-aware contract:
  `autonomous_gold_20260715/strategy/archaludon_hierarchical_rules_20260729/next_rule_after_hero_maturity_20260730/STRATEGY_SELECTION.md`,
  SHA-256
  `DE30DBA76E39DC0F6FF922E24727A3A9013C266DCEAC5CC306E6581CE601FDB0`.
- Search-aware pre-edit result:
  `autonomous_gold_20260715/root_verification/archaludon_search_aware_active_terminal_88827776_20260730/pre_edit_engine_counterfactual.json`,
  SHA-256
  `0EFAB0FECAB5FFAEFE904322C79ACD762A5069E08AE6671D0FEC34E91BB03CF4`.
  Root verified eight terminal transactions and 80 callbacks across both
  logical seats, public-only `P(hit)=164/165`, two search-miss fallbacks, five
  fail-closed branches, exact 220 damage for three Prizes, and zero faults.

## One selected hypothesis and decision

Select exactly one coherent integration hypothesis:

`CUMULATIVE_PUBLIC_HIERARCHY_AFTER_SEARCH_AWARE_V1`

> A fresh exact-historical-Silver child carrying every completed,
> destructive-safe Archaludon rule can improve coverage of finishing,
> forced defense, Prize conversion, attack continuity, survival, and setup
> without broad policy drift if every rule proposes from the same immutable
> public snapshot, only one explicit precedence winner may mutate state, one
> transaction owns all irreversible continuation, and every unknown
> interaction falls back to exact historical-Silver.

The first cumulative experimental set is the **broader verified set**, not
new-plus-Hero only:

1. `H2_CERTIFIED_LAST_PRIZE_STRETCHER_METAL_BOSS`
2. `SEARCH_AWARE_ACTIVE_TERMINAL_BEFORE_NONTERMINAL_BOSS_V1`, conditional
3. `H1_CERTIFIED_ENDGAME_ALAKAZAM_BOSS`
4. `H5_V2_PUBLIC_LETHAL_ACTIVE_NO_READY_SUCCESSOR`
5. `H4_V3_EXACT_INHERITED_ATTACK_LOCKED_UNIQUE_HIGHER_PRIZE_BOSS_KO`
6. `H6_UNIQUE_ACTIVE_METAL_DEFENDER_CONTINUITY_RESERVATION` v2
7. `HERO_CAPE_CURRENT_PAYABLE_SAME_ATTACK_SURVIVAL`
8. `H3_CERTIFIED_LONE_CINDERACE_ULTRA_BALL_TURBO_FLARE_LINE_FORMATION` v2

Search-aware inclusion is conditional on a frozen isolated candidate hash,
all contract gates, raw fixed evaluation, Root recomputation, and a final
rule-level safety judgment. Its currently changing implementation path is
`autonomous_gold_20260715/candidates/archaludon_search_aware_active_terminal_before_nonterminal_boss_v1/main.py`;
there is deliberately **no accepted source hash yet**. If isolated
verification fails, this exact cumulative candidate is aborted rather than
silently omitting or repairing the rule.

This decision does not call neutral or no-trigger evidence strength. It uses
that evidence only to identify rules whose observed implementation surface is
safe enough to enter destructive interaction testing. The new cumulative
policy supersedes old no-stacking practicality restrictions; it does not
promote any sibling, authorize reuse of an identical archive, or rehabilitate
a rejected version.

Taken as one deck plan, the set is coherent:

- H3 v2 supplies conservative board formation and backup Energy; H6 v2
  protects an exact attack-completing Metal; Hero protects one exact
  current-payable attack line.
- H5 v2 removes a paid lethal Active only with no ready successor; H1 removes
  a unique ready terminal Bench threat; H4 v3 converts only the exact
  inherited attack into a higher-Prize KO.
- H2 takes a deterministic last Prize; search-aware tries the current
  three-Prize Active before a nonterminal Boss diversion.
- Boss, ACE SPEC, Metal, hand, deck, and setup costs remain local to their
  full certificates. Parent disruption and ordinary sequencing remain
  unchanged outside the certified union.

## Included component ledger

### H2 — included; live-dormant

- Source:
  `autonomous_gold_20260715/candidates/archaludon_certified_last_prize_stretcher_metal_boss_transaction_v1/main.py`,
  SHA-256
  `F45E0EB55D8DD7CC48ADD02EE342F2B0721CB0D9F88C1B97C1793A755C52B76F`.
- Final safety evidence:
  `autonomous_gold_20260715/evaluations/archaludon_certified_last_prize_stretcher_metal_boss_transaction_v1/numerical_audit/AUDIT_REPORT.md`,
  SHA-256
  `0FEB92D6747EA116C7FFCC758D12568DC4945C02F9B47DE2CE13AB589788C0D2`;
  Root recomputation SHA
  `168DCBA718A0FBDC5C0331E4C6AF73007BDB3D348077F5E797186979FC2F70F0`.
- Evidence: exact six-stage terminal engine transaction, full shadow with
  zero trigger-external differences, parent=candidate `478/760`, zero
  regressions/faults. The mature 41-game live record was `23-17-1` at
  `769.8074705053797`, with no live H2 difference.
- Reason: the only completed guaranteed response-free terminal sibling. It
  outranks the probabilistic search attempt. It is dormant as causal live
  evidence, not rejected.

### Search-aware — conditionally included; primary new component

- Contract and pre-edit evidence are the two authoritative paths/hashes above.
- Accepted source path:
  `autonomous_gold_20260715/candidates/archaludon_search_aware_active_terminal_before_nonterminal_boss_v1/main.py`.
  Accepted source hash: `PENDING_ISOLATED_FINAL`; any build lacking a frozen
  final hash is invalid.
- Reason: it unifies finishing, search-aware evolution, attacker formation,
  Alloy payment, Prize arbitration, and same-turn commitment without an
  opponent-response interval. It is not dormant; it is the intended primary
  action-changing mechanism.

### H1 — included; live-dormant

- Source:
  `autonomous_gold_20260715/candidates/archaludon_certified_endgame_alakazam_boss_transaction_v1/main.py`,
  SHA-256
  `CC7C2C53EC49BF4C690D6CD686DFB8BBA0041F1EA8F174C8B91135FBBA33DC49`.
- Final safety evidence:
  `autonomous_gold_20260715/strategy/archaludon_hierarchical_rules_20260729/FINAL_RULE_JUDGMENT.md`,
  SHA-256
  `86DAB82DC4293384926BF32C12AE52DA83E852F1AF6400CE35F9ABE76A80487B`;
  mature Root review SHA
  `86D567092821D9E2664AC7151EF348A1460BC798412B1C8C5F24870E67B47071`.
- Evidence: one intended difference in 10,319 callbacks, exact
  Boss-to-Alakazam-to-Metal-Defender engine completion, `478/760`, zero
  regressions/faults. All 46 live games were parent-identical.
- Reason: narrow public forced-loss defense not duplicated by a terminal or
  generic higher-Prize rule. It is live-dormant and supplies no strength
  credit.

### H5 v2 — included; live-dormant

- Source:
  `autonomous_gold_20260715/candidates/archaludon_public_lethal_active_no_ready_successor_nonex_120_ko_v2/main.py`,
  SHA-256
  `E493C692198FE3699269F3CAFECD3010815DDE5EA2B3002321DDE109F9566798`.
- Final safety evidence:
  `autonomous_gold_20260715/evaluations/archaludon_public_lethal_active_no_ready_successor_nonex_120_ko_v2/FINAL_JUDGMENT.md`,
  SHA-256
  `75824A0C559D1C339D2862D7B80CD120EE9FEC0A55FD88A328A642F62CB59639`;
  mature Root review SHA
  `044FC4C0E4B80385CA9F7DABB113C8A88A6BC9B0420D04D0446B878D8461C23A`.
- Evidence: 60/60 focused checks, both-seat exact-engine completion, one
  intended difference in 11,473 callbacks, `478/760`, zero regression/fault.
  Forty-seven public games remained parent-identical.
- Reason: v2 contains the causal urgency/no-ready-successor separator missing
  from rejected v1. It is live-dormant and earns no strength credit.

### H4 v3 — included; locally exercised, no live probe

- Source:
  `autonomous_gold_20260715/candidates/archaludon_exact_inherited_attack_locked_unique_higher_prize_boss_ko_v3/main.py`,
  SHA-256
  `36A7D19EEBB781C0406D2A99571B728DE841FBEAC7BC15C0AAF869BD0367DD45`.
- Final safety evidence:
  `autonomous_gold_20260715/evaluations/archaludon_exact_inherited_attack_locked_unique_higher_prize_boss_ko_v3/FINAL_JUDGMENT.md`,
  SHA-256
  `83E4B982968C538533A7034EDFF94D03FFE90DB8A693B9441CE84C86E37D4A75`.
- Evidence: 20/20 focused checks, six both-seat engine transactions, exact
  inherited/stored/executed attack identity, zero external shadow
  differences, and parent=candidate `478/760`. Three traces perform the
  intended same-attack Prize conversion; all were already parent wins.
- Reason: contract-correct Prize arbitration after setup and exact attack
  choice are fixed. It is not live-proven and has no strength gain, but it is
  not dormant in local trace coverage.

### H6 v2 — included; causally dormant but transaction-exercised

- Source:
  `autonomous_gold_20260715/candidates/archaludon_attack_completing_energy_reservation_v2/main.py`,
  SHA-256
  `C2B2E6E2A3170A1E90853CD0128075EA023831C17F2B7263744E371FC826E530`.
- Final safety evidence:
  `autonomous_gold_20260715/evaluations/archaludon_attack_completing_energy_reservation_v2/FINAL_JUDGMENT.md`,
  SHA-256
  `347483F6AEC0A280E2B26D79362B139D986C4B8EE7930F8A331FE41514993539`;
  mature Root review SHA
  `8C0604E8491D598C1B1471EB90CC36343FD873D296B3DB12BF4A71A364B08CE9`.
- Evidence: v1 defect closed; focused/rollback/reset/both-seat engine gates
  passed; fixed-760 had byte-identical traces and zero faults. In 40 mature
  live games H6 safely failed closed once and completed once, but all 2,273
  actions were parent-identical.
- Reason: exact attack-completion resource protection fills a hierarchy row.
  It is transaction-exercised but causally dormant and supplies no strength
  credit.

### Hero — included; explicitly dormant

- Source:
  `autonomous_gold_20260715/candidates/archaludon_hero_cape_current_payable_survival_score_v1/main.py`,
  SHA-256
  `0EDE7D1B58AC31F6E3C4F10093D79940F08F058B7F63148CC48A884B25D4972B`.
- Final safety evidence:
  `autonomous_gold_20260715/strategy/archaludon_hierarchical_rules_20260729/hero_cape_final_judgment_20260729/FINAL_RULE_JUDGMENT.md`,
  SHA-256
  `944C82FC8FD2120EE8DAE2E7DCBAD1FD4C99907503AB128ECE5B8F3DA7D3872C`;
  mature Root review SHA
  `F63A30BF0DA60D90CDD3A6D5DE452E7EF9B2FC13E919BA03AF689F17520C8495`.
- Evidence: focused source/negative groups, six transaction groups, all
  three exact-engine branches, one intended difference in 11,967 callbacks,
  fixed `478/760`, and zero faults. Forty-one public games/2,332 callbacks
  produced zero starts or differences.
- Reason: the user explicitly permits this frozen survival component to
  remain dormant until it fires. No activation is neither positive nor
  negative strength evidence.

### H3 v2 — included; live-dormant

- Source:
  `autonomous_gold_20260715/candidates/archaludon_certified_lone_cinderace_ultra_ball_turbo_flare_line_formation_explorer_veto_v2/main.py`,
  SHA-256
  `9D5A2A87770FE4CC2F77599E0FDF044ECC61C3F20BA335A02E1E2650BE5036B0`.
- Final safety evidence:
  `autonomous_gold_20260715/evaluations/archaludon_certified_lone_cinderace_ultra_ball_turbo_flare_line_formation_explorer_veto_v2/FINAL_JUDGMENT.md`,
  SHA-256
  `B72051DD59A1E6C25794F6899DF735B39D79B6C128601FE09BCCC26B581F55FD`;
  mature Root review SHA
  `E936A478D106AF315ACA890302E0D6BED76A773D6DF4E329B9E14F04A5772B4A`.
- Evidence: Explorer veto repaired v1, six both-seat exact-engine
  transactions, one intended shadow difference, `478/760`, and zero
  regression/fault. All 33 live games were parent-identical.
- Reason: it is the only completed setup/backup and count-only access rule.
  It receives the lowest rule precedence and is live-dormant.

## Excluded mechanisms

| Mechanism | Exact source path and SHA-256 | Controlling evidence | Reason |
|---|---|---|---|
| H3 v1 | `autonomous_gold_20260715/candidates/archaludon_certified_lone_cinderace_ultra_ball_turbo_flare_line_formation_v1/main.py`; `97E3719088895B3B0FA80B3CD061C2DA23D8A3C9F03E27DC62BFEEF340BCC41F` | `autonomous_gold_20260715/evaluations/archaludon_certified_lone_cinderace_ultra_ball_turbo_flare_line_formation_v1/FINAL_JUDGMENT.md`; `5B61FC2E207F297CD715CD347B71D7E44AAF8D31F59EB6DDB5AA65CDD88B2DE3` | Rejected: preempted legal Explorer and paid avoidable Boss/heal discard costs. Superseded only by included v2. |
| H4 v1 | `autonomous_gold_20260715/candidates/archaludon_certified_unique_higher_prize_boss_ko_v1/main.py`; `4552FE569E146A9FA3F540BB962BD801233D944D52A032077778DD6454E51E5C` | Root trace audit `autonomous_gold_20260715/evaluations/archaludon_certified_unique_higher_prize_boss_ko_v1/ROOT_CHANGED_TRACE_AUDIT.md`; `B7C46084407F8104374AF0F4A19D3894354E9D6AD5A132C7F1DD453A0EE520FC` | Permanently rejected: preempted healing/setup/backup, `478 -> 475`, one gain and four causal regressions. |
| H4 v2 | `autonomous_gold_20260715/candidates/archaludon_parent_attack_admissible_unique_higher_prize_boss_ko_v2/main.py`; `29811BBFD174898B34FB551663DF0E8A3282C6C8675CEEDC5E97D631A1CE3041` | `autonomous_gold_20260715/evaluations/archaludon_parent_attack_admissible_unique_higher_prize_boss_ko_v2/FINAL_JUDGMENT.md`; `30D4BD83F00FF6A263A62D6BA6246FE7D1199085C882990F3AA3A3B884C99B08` | Rejected despite outcome neutrality: changed inherited Raging Hammer `224` into Hammer In `223` and spent Boss without the frozen same-attack certificate. |
| H5 v1 | `autonomous_gold_20260715/candidates/archaludon_inherited_attack_nonex_120_ko_v1/main.py`; `2E384C04B3725337C29207689B08A3C5E5A2A55C01BF9645A518B34573A20196` | `autonomous_gold_20260715/evaluations/archaludon_inherited_attack_nonex_120_ko_v1/FINAL_JUDGMENT.md`; `FA94FAD12C6409D466F270CB72E8595FEB80A088B121E53FBAE0202C524BF16A` | Immutable rejected control: `478 -> 477`; omitted lethal-Active urgency/no-ready-successor distinction. |
| H6 v1 | `autonomous_gold_20260715/candidates/archaludon_attack_completing_energy_reservation_v1/main.py`; `AC798FD2B757D94DDC21EFF07FE53EF4AFB9C139F98EA47DA0A9285ABC5FABB5` | `autonomous_gold_20260715/evaluations/archaludon_attack_completing_energy_reservation_v1/ROOT_DEFECT_VERIFICATION.md`; `AECD7A27F640D7C93B67BEF747E0BEAAF027174F8BB4E3E1BE5A1A9704BF77D6` | Permanently rejected certificate breach: did not invalidate a reservation when a second visible Metal appeared before attachment. Neutral fixed output did not make it safe. |
| H7-A | No candidate source exists; source hash `NONE`. Selection only: `autonomous_gold_20260715/strategy/archaludon_hierarchical_rules_20260729/STRATEGY_SELECTION_H7A_SOLE_READY_SUCCESSOR_CONTINUITY.md`; `D5B900A869078E76D71A4FB3ABF214D40C7A3AC341576F44E03EF1CBADA3C62F` | No completed implementation, isolated raw evaluation, or final safety judgment | Deferred, not rejected as theory. It can sacrifice a positive current attack for a successor whose current damage is zero and does not control later promotion. H7-B has no frozen contract or source and is also excluded. |

No rejected source may be copied, packaged, used as a parent, or allowed to
enter the proposal registry.

## Implementation-ready arbitration contract

Build one fresh direct child of exact historical-Silver. Do not chain, nest,
or call any frozen candidate agent as a parent. Port only the frozen
component certificates and transactions. All ordinary parent behavior comes
from one exact historical-Silver chooser.

For each callback:

1. Canonicalize one immutable public snapshot and compute the exact parent
   semantic action exactly once.
2. Run every clear component as a pure evaluator returning
   `(eligible, rejection_reason, proposed_semantic_action,
   certificate_digest, state_intent)`. Evaluation may not mutate any
   transaction.
3. Apply the total precedence below. Commit state only for the winner.
   Suppressed components remain bit-for-bit clear.
4. Rebind the winning semantic action to current legal options. Ambiguous,
   missing, unsupported, or nonunique binding fails closed.
5. Emit at most one action. A returned action does not confirm a stage;
   only a novel public mutation/log does.

H3's `0.999` access threshold and search-aware's `0.99` threshold remain
separate named constants and separate ledgers. No opponent identity, episode,
row, seed, fixed serial, hidden card, or replay-future condition is allowed.

### Frozen total precedence

| Rank | Action owner |
|---:|---|
| 0 | Engine legality, mandatory callback, setup/deck request, result, reset, and deterministic emergency legality |
| 1 | Exact-parent already-legal direct terminal Attack or shorter guaranteed exact terminal Boss action |
| 2 | One already-confirmed, still-valid active transaction owner, subject to the collision rules below |
| 3 | H2 guaranteed last-Prize response-free transaction |
| 4 | Search-aware `P(hit) >= 0.99` Active-terminal attempt |
| 5 | H1 unique ready terminal-threat forced defense |
| 6 | H5 v2 paid-lethal-Active/no-ready-successor conversion |
| 7 | H4 v3 exact-inherited-attack higher-Prize conversion |
| 8 | H6 v2 attack-completing Energy reservation |
| 9 | Hero current-payable same-attack survival |
| 10 | H3 v2 line formation/setup |
| 11 | Exact historical-Silver action |

Equivalent semantic proposals still have one owner: the higher-ranked rule.
Different actions at an equal or unregistered rank fail closed to the parent.

### Pairwise and all-eligible clear-state matrix

Abbreviations: `T=H2`, `S=search-aware`, `D=H1`, `L=H5v2`, `P=H4v3`,
`E=H6v2`, `C=Hero`, `F=H3v2`. Each cell is the required winner when the row
and column both propose from a clear snapshot.

| Higher \ lower | S | D | L | P | E | C | F |
|---|---|---|---|---|---|---|---|
| T | T | T | T | T | T | T | T |
| S | — | S | S | S | S | S | S |
| D | — | — | D | D | D | D | D |
| L | — | — | — | L | L | L | L |
| P | — | — | — | — | P | P | P |
| E | — | — | — | — | — | E | E |
| C | — | — | — | — | — | — | C |

This enumerates all 28 pairs. Natural certificate mutual exclusion is not a
test waiver: inject pure proposals into the resolver to test every cell, and
separately prove the expected public-state exclusions. With all eight
eligible at a clear callback, `T` wins, seven rules are logged as suppressed,
and only T may arm. If rank 1 is present, exact parent wins over all eight.

### Transaction ownership and fail-closed behavior

- There is one global `active_transaction_owner`; each component has a
  separate namespaced state object, but at most one may be nonclear.
- Identical retries return the cached semantic action and do not call the
  parent again, advance state, or create a second owner.
- A rule eligible and suppressed on the arming snapshot remains clear. The
  valid owner may continue over that already-recorded suppressed proposal.
- If a different rule becomes newly eligible with a different action after
  any irreversible owner action, clear every component and delegate exact
  historical-Silver from the actual current state. Never transfer a
  half-completed transaction to the new rule.
- A newly eligible rule proposing the exact same semantic continuation may be
  logged and suppressed; the existing owner retains attribution.
- An exact-parent direct terminal action, forced callback, result/reset,
  invalid owner certificate, changed snapshot, unknown collision, stale
  stage, exception, ambiguous option binding, or untested interaction clears
  all rule state and returns the actual-state parent action if legal.
- After an irreversible card/effect, rollback is logical only. Never replay
  the initial parent action, undo a card, or import another rule's stored
  serial, target, attack, Energy, or probability ledger.

For every unordered pair, test both directions of active ownership in both
seats: competitor present-and-suppressed at arm, competitor newly appearing,
same-action collision, different-action collision, retry, rollback, turn
change, result, new game, and exception. The synthetic all-eligible fixture
must repeat the same cases.

## Required telemetry

Every callback, including parent-equal and reset callbacks, must emit:

- `snapshot_id`, `game_epoch`, `seat`, `turn`, `action_count`, and context;
- `exact_parent_action`;
- `eligible_rule_ids` in precedence order;
- `proposed_actions_by_rule`;
- for every rule: frozen source/contract hash, `eligible`,
  `rejection_reason`, `certificate_digest`, `precedence_rank`,
  `transaction_id`, `stage_before`, `stage_after`, `emitted`,
  `confirmed`, `duplicate_or_retry`, `suppressed_by`, and
  `rollback_reason`;
- `active_transaction_owner`, `winning_rule_id`, `suppressed_rule_ids`,
  `precedence_reason`, `final_action`, and `attribution_owner`;
- `duplicate_or_reset_state`, `invalid_or_emergency_fallback`, option-binding
  result, and state-clear result.

Telemetry must use semantic identities; option indices are supplemental only.
The Root must be able to attribute the first parent difference and every
later owned callback without rerunning an inference model.

## Falsifiable destructive and evaluation gates

### Conditional isolated search-aware gate

Before cumulative source work, search-aware must independently pass its
contract: focused positives/negatives, both-seat hit and matched miss
transactions, serial/option permutations, complete current shadow, immutable
both-seat fixed evaluation, exact schedule equality, no parent-win loss, no
panel/seat/cell regression, and zero start/action/exception/stale/max-step
faults. Root must freeze the final source hash and raw paths. Any failure
aborts this selection.

### Component and collision gates

- Reproduce every frozen component positive and full transaction in both
  logical seats from the cumulative implementation.
- Reproduce every frozen component negative/control, especially H3-v1,
  H4-v1/v2, H5-v1, and H6-v1 regression/defect states.
- Execute all 28 clear-state pair cells, both active-owner directions, and
  all-eligible cases with retries, option/serial permutations, rollback,
  reset, and exceptions. Expected winner/fallback and state ownership must
  be exact.
- Zero suppressed-state mutation, two-owner state, invalid action, exception,
  nondeterminism, stale transaction, action error, or max-step hit.

### Exact-parent and isolated-component shadows

Freeze one current union manifest containing every component source replay,
all frozen negatives, all search-aware source/miss fixtures, and all latest
public replays. For every callback:

1. independently loaded exact historical-Silver must equal the integrated
   runtime's cached `exact_parent_action`;
2. each integrated rule's proposal must equal its frozen isolated source on
   that rule's certificate and transaction callbacks;
3. absent a collision, integrated final action must equal the corresponding
   isolated component;
4. at a collision, the final action, owner, and suppression list must equal
   the matrix/transaction contract;
5. integrated-versus-parent differences must be only the
   precedence-resolved subset of isolated component differences; there may be
   no interaction-created external difference.

Require exact-parent equality outside all certificates and zero faults over
the complete shadow. A custom prose classification cannot waive a raw
difference.

### Immutable fixed evaluation

Use the checked historical-Silver 200-row mirror and seven-opponent 560-row
adjacent schedule with identical engine, seats, seeds, full traces, schema,
and `max_steps=1000`. Root must verify 760 unique
`(panel, opponent, seat, seed)` keys, exact schedule equality, duplicate
controls, exit codes, and win columns from raw rows. The physical paired CSV
must contain the `panel` column and the frozen
`panel,opponent,seat,seed,baseline_win,candidate_win,baseline_result,
candidate_result,baseline_steps,candidate_steps` schema; directory inference
is not sufficient for this new formal comparison.

For destructive passage require:

- parent duplicate `478/760`, historical anchor `100/200`, adjacent
  `378/560`, seats `243/380` and `235/380`;
- cumulative at least those exact overall/panel/seat totals;
- no parent-win/cumulative-loss flip and no opponent/seat cell or inherited
  `28/80` Kangaskhan/Crustle-floor loss;
- zero starts missing, nonbinary results, action errors, exceptions,
  nondeterminism, stale state, and max-step hits;
- Root inspection of every trace difference with intended rule,
  transaction, and precedence agreement.

Equality is safety only. A tiny paired delta is not promotion evidence.

### Both-seat package and engine gate

The fresh cumulative package must retain the exact 60-card/one-ACE deck, the
expected 12 runtime members, parent-identical non-`main.py` files, one
loader-last/loader-only callable `agent`, deterministic deck request, clean
import, and zero cache/test/generated/traversal entries. Freeze extracted
member hashes and archive hash.

From the extracted package, run both seats for every component transaction,
every pair/all-eligible collision family, search hit/miss, duplicate/reset,
and deterministic battle smoke. Require exact semantic traces and zero
invalid actions, starts, action errors, exceptions, stale state, or max-step
hits.

## Practical live eligibility and later adoption

If every destructive gate passes, the cumulative candidate is eligible for
one practical **experimental** live probe under the controlling policy even
if fixed results are neutral. Root must issue a fresh final judgment, confirm
quota/status and a nonduplicate source/archive, and remains the only Kaggle
writer. Exact historical-Silver remains the formal parent and immediate
rollback.

Correct-seat shadow every genuinely new replay. Stop on a rule-owned or
collision-owned regression, certificate breach, attribution failure, package
or execution fault, stale/two-owner state, invalid action, exception, or
max-step hit. Parent-path losses remain unrelated memos. Absence of Hero or
another dormant activation is not removal evidence.

Formal-parent reconsideration requires a new Sol-Ultra judgment and at least:

- `486/760` overall and `104/200` primary anchor, adjacent at least
  `378/560`, no seat/cell/floor regression, and no parent-win loss;
- practical absolute strength, not a lone `+1` or other tiny paired delta;
- at least four completed search-aware transactions, at least two per seat
  and two public board configurations, plus two Root-verified
  parent-loss/candidate-win conversions covering both seats;
- repeated, certificate-valid behavior for every other rule that changes an
  action; dormant rules receive no strength credit;
- zero rule-owned/collision-owned regressions and zero action/max-step faults;
- trace proof that observed gains arise from the intended terminal,
  defense, Prize, continuity, survival, or setup mechanism rather than
  parent-identical variance.

## Regression risks and exact evidence needed next

Principal risks are integration refactoring changing an isolated certificate;
two state machines mutating on one callback; stale serial/option rebinding;
Boss, Cape, Metal, heal, or setup opportunity costs crossing transactions;
H3's and search-aware's probability ledgers being conflated; a low-priority
transaction hiding a newly available win; and telemetry attribution
disagreeing with the actual first difference.

The exact next evidence is:

1. frozen isolated search-aware source/deck/diff hashes, final judgment, raw
   focused/engine/shadow/fixed outputs, and Root recomputation;
2. fresh cumulative source/deck/direct-diff hashes and a component-import
   manifest binding every rule to the source hashes above;
3. raw 28-pair, both active-direction, and all-eligible resolver/engine
   outputs for both seats;
4. the union shadow manifest, exact-parent comparison, eight isolated
   proposal comparisons, integrated attribution rows, and difference hashes;
5. immutable fixed-760 raw rows/traces/exits and an independent numerical
   audit plus Root recomputation;
6. clean extracted-package inventory/hash and both-seat component/collision
   smoke;
7. only after a Root live authorization, per-callback cumulative telemetry
   and exact-parent counterfactuals for every live first difference.

H7-A may be added later only after a real direct-parent source exists, passes
its full both-seat transaction/negative/shadow/fixed gates with no regression,
and receives a fresh final safety judgment explicitly permitting cumulative
integration. H7-B or any deferred Boss/Bench/mode/known-access memo requires
its own single public-state hypothesis and isolated destructive verification;
memo quality or replay plausibility alone is insufficient.
