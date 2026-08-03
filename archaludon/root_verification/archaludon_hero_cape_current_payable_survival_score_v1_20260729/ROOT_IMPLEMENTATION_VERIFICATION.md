# Root implementation verification

Candidate:
`archaludon_hero_cape_current_payable_survival_score_v1`

Root-verified at 2026-07-29 21:29 JST.

Decision:
`PASS_IMPLEMENTATION_AND_FIXED_EVALUATION_GATE__NO_PACKAGE_OR_LIVE_AUTHORITY`

## Frozen identity

- formal parent `main.py` SHA-256:
  `F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E`
- candidate `main.py` SHA-256:
  `0EDE7D1B58AC31F6E3C4F10093D79940F08F058B7F63148CC48A884B25D4972B`
- parent/candidate deck SHA-256:
  `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`
- frozen strategy SHA-256:
  `ADE5F064CCDD62D9436AD5837EC138276ED347335A380DAE7A9CD1B3C38ACABB`
- implementation report SHA-256:
  `E466AB541744710EC8BAEC869B7600518432BCFBA0D45FBC48470D806B05AF7E`

The candidate is a direct exact-historical-Silver sibling. It does not contain
H5, H6, H7-A, or another candidate overlay.

## Root source review

Root inspected the full candidate-only block and the parent diff. The runtime
diff is only `main.py`; the candidate adds 701 lines and replaces eight lines
that formerly implemented the parent chooser/agent wrapper. The replacement
parent-scoring loop preserves the exact historical sort, tie, minimum-count,
and negative-score behavior and calls the unchanged `score_option`.

The added rule is only:
`HERO_CAPE_CURRENT_PAYABLE_SAME_ATTACK_SURVIVAL`.

It requires:

- ongoing strict one-choice `MAIN`;
- only `ATTACH`, `ATTACK`, and `END` legal option types;
- an untied exact parent winner of Raging Hammer `224`;
- exactly one semantic Cape-to-current-Active-Duraludon binding;
- positive non-KO Raging Hammer damage and no legal KO attack;
- complete unique public serials and supported public Energy units;
- an audited exact attack registry for `223`, `224`, `982`, and `983`;
- at least one current-payable E0 attack lethal before Cape;
- every E0 attack strictly nonlethal after `+100 HP`;
- fail-closed handling for any Tool, Stadium, status, skill/modifier,
  Weakness/Resistance, unsupported attack/Energy, changed option, or changed
  state.

The certified Cape score is exactly
`max(parent Cape score, inherited attack score + 1)`. At source
`88643491:77`, the parent Cape score is 8,000, Raging Hammer is 25,000, and
the candidate Cape score is 25,001. The candidate records
`E1_CAPE_LETHAL`; one hypothetical Basic Fighting makes Mega Brave 270
payable and lethal. This telemetry is not used as a safety claim.

The transaction snapshots the public material state, semantic option
multiset, attacker, target, Cape serial, stored attack, E0/E1 envelopes, and
game identity. It supports semantic duplicate/option rebinding and exact
retries, confirms only a Cape-only public transition, recomputes the parent,
then emits the same Raging Hammer. Mutation or inconsistency clears and
delegates.

## Root reruns

Root reran all checked implementation tools against the frozen source.

### Focused and exact-engine

Command:
`py -3.11 -B test_candidate.py`

Result: exit `0`.

- source positive and source negative: pass;
- transaction-control groups: `6/6`;
- fail-closed negative groups: `19/19`;
- no Cape plus Aura Jab: Duraludon KO;
- Cape plus same Raging Hammer plus Aura Jab: Duraludon survives at
  `100/230`;
- Cape plus one Basic Fighting plus Mega Brave: Duraludon KO.

Focused result SHA-256:
`F73C961CDE5B1ACA6A20E5E350632A74B2DE3FA0983A4FD995F9015FD00E4E77`.

### Correct-seat shadow

Command:
`py -3.11 -B run_shadow.py`

Result: exit `0`.

- replay files: `217`;
- correct seats: 113 seat 0 / 104 seat 1;
- actionable callbacks: `11,967`;
- semantic differences: `1`;
- classified source differences: `1`;
- certificate-external differences: `0`;
- action errors / exceptions / max-step hits: `0 / 0 / 0`;
- frozen sibling/control callbacks: `61`, all parent-equal;
- stale transactions: `0`.

The only first difference is `88643491:77`, parent Raging Hammer to candidate
Hero's Cape, labeled
`HERO_CAPE_THEN_STORED_RAGING_HAMMER` and `E1_CAPE_LETHAL`.
The historical replay follows the parent branch, so the later candidate
transaction safely clears and delegates; the complete Cape continuation is
proved by the focused exact-engine branch instead.

Shadow summary SHA-256:
`5C99B44A660BC179DD743EC3EE7E7BD5CF8B21DD01B8DDC97E03C413E8028708`.

Shadow difference SHA-256:
`5432EAC6DB562E9C57FB40DBBCDECB24E5C4EA69EDE3865C40E6BC724BFF8E1D`.

Shadow manifest SHA-256:
`2BB9D462D1C6FD5BF49CEB34A9EA49F4C658A91DFF2330757AD510A5C62ABABD`.

### Structure

Command:
`py -3.11 -B validate_candidate.py`

Result: exit `0`.

- runtime files: `12`;
- changed runtime files: only `main.py`;
- unchanged runtime files: `11`, parent byte-identical;
- deck cards: `60`;
- deck request smoke: pass;
- candidate and implementation caches after Root cleanup: `0`;
- archive/package: none.

Structural result SHA-256:
`604968606A5C4A86D4127F4C4B8B0ED314F364624C2861D463FE88CB5829A564`.

Root separately compiled the candidate. That command generated a local
`__pycache__`; Root verified its absolute path was inside the isolated
candidate and removed only that cache. Candidate source/deck hashes remained
unchanged.

## Gate

The implementation is contract-correct, deterministic, legal, isolated, and
safe enough to enter the fixed identical-seed/both-seat evaluation.

This report does not authorize packaging, formal-parent promotion, or a
Kaggle write. Absolute strength, adjacent floors, seat effects, changed
positions, and the source tradeoff remain for fixed evaluation and final
Sol-Ultra judgment.
