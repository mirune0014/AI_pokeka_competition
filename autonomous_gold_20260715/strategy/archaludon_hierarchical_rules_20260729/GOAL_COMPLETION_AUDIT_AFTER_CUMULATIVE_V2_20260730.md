# Archaludon cumulative hierarchy completion audit

Audit time: 2026-07-30 05:35 JST.

Conclusion: `INCOMPLETE__KEEP_GOAL_ACTIVE`.

This audit supersedes only the implementation-status conclusions in
`GOAL_COMPLETION_AUDIT_20260729_1826.md`. It does not supersede any frozen
candidate contract, rejection, safety judgment, or Kaggle submission record.

## Controlling artifacts

- Exact historical-Silver formal parent:
  `analysis_outputs/reference_agents/historical_silver_archaludon_54495224/main.py`,
  SHA-256
  `F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E`.
- Exact deck SHA-256:
  `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`.
- Current cumulative candidate:
  `candidates/archaludon_cumulative_public_hierarchy_megabrave_lock_veto_v2/main.py`,
  SHA-256
  `DEE5092B6785DF7A63752C7AAE497051D08DCC62F7723CD9786225A0C5A99DE8`.
- Current clean package SHA-256:
  `8C921DCCFE6F597F49D60B45799EB97FA4DE573EA7B8FF4C930A91C22FEA9F88`.
- Root numerical recomputation:
  `root_verification/archaludon_cumulative_public_hierarchy_megabrave_lock_veto_v2_20260730/ROOT_NUMERICAL_RECOMPUTATION.md`,
  SHA-256
  `10A9570AB109869B68016D4F6BB0F150F35F316812F4C49F2C3E7959CC3F2C87`.
- Final practical-live judgment:
  `strategy/archaludon_hierarchical_rules_20260729/cumulative_megabrave_lock_v2_final_judgment_20260730/FINAL_PRACTICAL_LIVE_JUDGMENT.md`,
  SHA-256
  `92C0C104F8FC442C3C87E7B96B04DCC7FACB728C8B332C939865213A2911A553`.

## Global destructive-safety status

The cumulative v2 candidate integrates eight independently frozen components
directly over exact historical-Silver:

1. H2 last-Prize Stretcher/Metal/Boss terminal transaction;
2. search-aware Active-terminal conversion;
3. H1 visible ready terminal-threat removal;
4. H5 v2 lethal-Active/no-ready-successor conversion;
5. H4 v3 exact-inherited-attack higher-Prize Boss conversion, with the
   Mega Brave self-lock-release veto;
6. H6 v2 attack-completing Energy reservation;
7. Hero's Cape current-payable same-attack survival;
8. H3 v2 Cinderace/Duraludon line formation with count-only access.

The resolver has one active transaction owner, deterministic total
precedence, fail-closed exact-parent fallback, and per-rule proposal,
suppression, ownership, rollback, and final-action telemetry.

Root verified all 28 unordered clear-state pairs, both ownership directions,
both seats, the all-eligible family, duplicate/reset behavior, and the union
replay shadow. The union shadow covered 261 replays and 14,464 callbacks,
with 115,712 isolated comparisons and zero faults. Fixed-760 was
parent=candidate `478/760`, historical `100/200`, adjacent `378/560`, seat 0
`243/380`, seat 1 `235/380`, with zero gains, zero regressions, and exactly
three intended outcome-neutral trace changes.

The old cumulative v1 source
`BE8C67E387CE4F36344A4B0DE610CAB9976BB07EE49200997D35CCC6C5DBF18A`
is permanently rejected for live use. Its H4 rule released a public Mega
Brave self-lock and exposed a three-Energy two-Prize Archaludon to a KO. The
v2 veto repairs that exact collision and preserves the parent action at the
reproducer.

This evidence proves destructive local safety for the eight-rule cumulative
candidate. It does not prove broad strength or completion of every requested
decision mechanism.

## Requirement-by-requirement status

| Requested mechanism | Current cumulative coverage | Judgment | Missing proof or implementation |
|---|---|---|---|
| Exact-win hard gate | H2 and search-aware terminal transactions are integrated above the parent. | Implemented for two certified route families; broader coverage partial. | Live activation and additional public terminal-out families. |
| Exact-loss / forced-defense hard gate | H1 removes one unique visible ready terminal threat. | Narrow implementation complete; scope partial. | Unfinished threats that can become ready within one or two turns. |
| Prize-route arbitration | H2, H1, H5 v2, H4 v3, exact-parent terminal priority, and one-owner precedence are integrated. | Implemented for frozen route families. | Mode-sensitive multi-turn Prize-lane comparison outside the frozen families. |
| Harmful-KO avoidance | H1 and H5 v2 cover two certified cases where target choice or immediate KO urgency changes survival. | Partial. | A general public certificate for deliberately declining an available KO when the resulting Prize exchange or board unlock is losing. |
| Non-KO attack and Active constraint | Hero's Cape survival and the repaired Mega Brave self-lock veto preserve two concrete constraint/survival cases. | Implemented for the frozen cases. | Additional Active-lock attacks and escape-cost/control states. |
| Bench damage and future-board value | Historical-Silver has ordinary attack scores, but no cumulative component projects evolution, healing, future HP thresholds, or future attacker readiness for Bench damage. | Not implemented. | One bounded public-state future-value rule with exact changed-position tests. |
| Visible ready and one-to-two-turn unfinished threats | H1 sees an already-ready Alakazam; H3 reasons about our own line formation. | Requested opponent scope not implemented. | Public evolution/attachment/attack completion envelope, strict unknown handling, and both-seat fixtures. |
| Known hand and deterministic access | Search-aware keeps a same-turn public access ledger for its certified route. | Narrow same-turn implementation only. | Persistent public search/reveal/return/known-discard ledger with lifetime and reset semantics across turns. |
| Card-count/effect-only probabilistic access | Search-aware uses its frozen `0.99` threshold; H3 separately uses `0.999` hypergeometric access and a public Metal lower bound. | Two narrow primitives implemented. | Audited reusable access registry for additional card/effect families; hidden Prize contents must remain unknown. |
| Winning / normal / comeback modes | No explicit mode state or mode-specific thresholds exist in the cumulative resolver. | Not implemented. | Public Prize/board/readiness classifier, transition hysteresis, separate admissibility thresholds, and comeback-out valuation. |
| Winning outs and forced conversion | H2 and search-aware reserve and complete two exact terminal routes. | Partial. | Multiple competing same-turn outs and nonterminal comeback outs without preempting parent setup. |
| Turn-plan commitment | Every integrated multi-step component has its own snapshot, owner, stages, rollback, duplicate, and reset handling. | Mechanism infrastructure implemented; objective coverage partial. | A shared mode/plan layer capable of reserving a multi-turn objective across rule families without transferring irreversible state. |

## Completion blockers

The Goal cannot be marked complete while these four primary gaps remain:

1. no future-value component for Bench damage or choosing Active versus Bench;
2. no opponent one-to-two-turn unfinished-threat completion envelope;
3. no persistent public known-card/deterministic-access ledger across turns;
4. no explicit winning/normal/comeback mode with separate admissibility and
   winning-out thresholds.

The harmful-KO and winning-out rows also remain broader than the two narrow
families currently implemented.

## Next implementation order

The next rule must be selected from Root-verified public evidence, not from a
replay result label. Preferred dependency order:

1. public known-card and deterministic-access ledger, because future threat,
   Bench value, and mode decisions need a reliable information boundary;
2. one-to-two-turn public threat completion envelope;
3. winning/normal/comeback mode classifier and transition contract;
4. harmful-KO / Active-versus-Bench future-value arbitration using only the
   certified ledger, threat envelope, and mode state.

Each new mechanism remains an isolated direct-parent implementation during
development. After its destructive gate passes, it may be accumulated into a
new traced hierarchy candidate. A dormant, valid rule remains available until
it fires; no-trigger evidence alone is not a reason to delete it.

## Immediate live step

The repaired eight-rule cumulative v2 is authorized for one exploratory live
probe but has not yet been submitted. At the 2026-07-30 05:27 JST
authenticated refresh, the current UTC-day quota was exhausted. Root must
refresh submissions, quota, exact episode IDs, and all source/package hashes
after the expected 09:00 JST reset before any Kaggle write.

The live probe is diagnostic. Weak score alone is not an implementation
defect. Immediate rollback conditions are an invalid action, stale or dual
transaction owner, telemetry attribution failure, Mega Brave self-lock
release, or a rule/collision-owned causal regression.
