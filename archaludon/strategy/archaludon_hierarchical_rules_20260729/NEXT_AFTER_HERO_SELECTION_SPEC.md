# Immutable selection specification — successor after Hero's Cape

This is a read-only strategy-selection task. It does not authorize
implementation, packaging, or a Kaggle write.

## Formal parent and invariants

- exact historical-Silver policy:
  `analysis_outputs/reference_agents/historical_silver_archaludon_54495224/main.py`
- policy SHA-256:
  `F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E`
- deck SHA-256:
  `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`

Every future candidate remains a direct sibling from that parent. Do not
stack H1-H7, H6, Hero's Cape, or another candidate.

## Current ordered work

H6 v2 is live and must close first. Hero's Cape is already selected as the
next isolated implementation:

- contract:
  `STRATEGY_SELECTION_HERO_CAPE_CURRENT_PAYABLE_SURVIVAL.md`
- contract SHA-256:
  `ADE5F064CCDD62D9436AD5837EC138276ED347335A380DAE7A9CD1B3C38ACABB`

This task selects only the one successor to consider after Hero's Cape
finishes. It must not displace or modify the Hero's Cape contract.

## Root-verified candidate evidence

### A. Bench-damage future value

- root verification:
  `ROOT_BENCH_DAMAGE_AUDIT_VERIFICATION.md`
- SHA-256:
  `4D8AC5B31817B4857A8520A5D862FFBCC5CCD6029ACD9188A0D4E0AD84F0A1AB`
- qualitative audit:
  `BENCH_DAMAGE_FUTURE_VALUE_AUDIT.md`
- SHA-256:
  `74C135E9F005F9BADC8C94933FF069F4F23B584183683D7AB0B2811F04F83A9C`
- replay:
  `autonomous_gold_20260715/evidence/live_54927163_refresh_20260729_0344/episode_88247531_replay.json`
- replay SHA-256:
  `26D1D7054A5C67ED89261B4CA391445A3EA46C5FC8D4AE314E63A577CFC7434E`

Root verified one direct policy failure at step 115: the same Archaludon ex
could evolve either healthy Active Duraludon or a 10/130, three-Metal Bench
Duraludon. Parent chose Active. Evolving the invested Bench retains 120 damage
but raises max HP to 300, producing 180 current HP and crossing the payable
30 Bench-damage survival boundary. The full public 30-plus-30 package leaves
120 HP. Root did not prove a match win or the later Alloy continuation.

### B. One-to-two-turn threat window

- deferred Root memo:
  `DEFERRED_LOSS_MEMO_88776108_DRAGAPULT_THREAT_WINDOW.md`
- SHA-256:
  `69FEFF27731179ACB809BA9B9605C7B44847819FC05382D6F0CDDD1E554F09FB`
- replay SHA-256:
  `4A3DBF7BC27EA49B84236BE96497E1FDAD5381C92171C357C3A36294ED8EDB87`

Root verified a possible defensive-evolution source: two-Metal Active
Duraludon, legal Archaludon ex, publicly mature Dragapult line plus Duskull,
two backups, and a non-Prize Hammer In. Parent attacked. The next turn used
Cursed Blast 130 to force promotion and Phantom Dive 170 to take another KO.
This is a narrower and more opponent-card-specific source. It does not prove
the opponent evolution/ability access from the prior callback.

### C. Coverage constraints

- coverage matrix:
  `HIERARCHY_COVERAGE_MATRIX.md`
- SHA-256:
  `988FB47D2048886C2DF983AB950289E475AD8C3EF12F1DD218ABD63B83B9627E`

Bench future value, opponent one-to-two-turn completion, persistent known-hand
ledger, general card-count access, explicit modes, broader winning outs, and
generic turn-plan commitment remain incomplete.

## Decision question

Select exactly one coherent successor hypothesis after Hero's Cape, or return
`NO_SAFE_SELECTION` if neither source supports a bounded deterministic rule.

Judge:

1. public-state sufficiency and hidden-information risk;
2. whether the first changed callback is mechanically addressable;
3. exact terminal/Prize/setup/forced-defense precedence;
4. current and backup attack continuity;
5. resource and Prize liability;
6. both-seat exact-engine reconstructability;
7. falsifying negatives and fail-closed unknowns;
8. value toward the full user-requested hierarchy rather than only one replay.

If selecting, specify one rule name, exact trigger, one changed semantic
action, precedence, transaction/rollback needs, mandatory positives and
negatives, shadow telemetry, fixed-evaluation floors, and adoption versus
experiment-only thresholds. Do not broaden the rule to cover both A and B.
