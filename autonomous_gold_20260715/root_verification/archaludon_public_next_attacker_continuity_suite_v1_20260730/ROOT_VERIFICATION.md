# Archaludon public next-attacker continuity suite v1

## Decision

`PASS_FOR_PRACTICAL_LIVE_PROBE`

This is a destructive-safety judgment, not a local win-rate claim.

## Parent and candidate

- Direct live parent:
  `autonomous_gold_20260715/candidates/archaludon_cumulative_public_one_turn_target_dominance_v1`
- Parent source SHA-256:
  `6504E0E3EA69D59EAB5F9A73E306D70695A0E76ECA8D347C97F1EB43AEE31B7A`
- Candidate:
  `autonomous_gold_20260715/candidates/archaludon_public_next_attacker_continuity_suite_v1`
- Candidate source SHA-256:
  `E7F8B3A6E84BD129BBDF5C49C524446BF3DFBE9C95C16F069F435CA104DCF65C`
- Deck SHA-256:
  `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`

Only `main.py` changes. The deck, requirements and nine `cg/` runtime files
are byte-identical to the direct parent.

## Root replay and regression verification

The preceding live submission had 54 public games, 32 wins and 22 losses.
Root replayed all 3,093 correct-seat callbacks before implementation.

The prior target-dominance overlay had:

- zero action differences from its direct parent;
- zero proposal or transaction-owner events;
- zero invalid actions and exceptions.

It caused no observed regression and remains installed.

Root reran the final candidate's short destructive gate and full-54 shadow.
Both commands exited zero and reported `PASS`.

### Exact intended live differences

| Episode | Step | Mechanism |
|---|---:|---|
| 88917360 | 12 | Cape before Lillie |
| 88917846 | 18 | Cape before Turbo Flare |
| 88917846 | 46 | Metal attachment and Turbo before retreat |
| 88923881 | 31 | Ready non-ex evolution through ex immunity |
| 88932139 | 131 | Healthy ready pre-attack rotation |
| 88947304 | 52 | Preserve one-prize Active and evolve Bench |

Final full shadow:

- episodes: 54;
- callbacks: 3,093;
- candidate-parent differences: exactly 6;
- untraceable differences: 0;
- invalid actions: 0;
- exceptions: 0;
- telemetry errors: 0;
- prior target-dominance eligible events: 0.

### Short gate

- source-shaped positives: 6/6 in the recorded and logical opposite seat;
- counterfactual transaction completions: 5 multi-step routes plus one atomic
  immunity conversion;
- close negatives: 24/24;
- existing-rule collisions: 45/45;
- duplicate callbacks: 6/6;
- reversed option order: 6/6;
- turn, seat and result resets: 3/3.

## Package verification

- Archive:
  `autonomous_gold_20260715/packages/archaludon_public_next_attacker_continuity_suite_v1_clean_20260730_2311/submission_archaludon_public_next_attacker_continuity_suite_v1_20260730.tar.gz`
- Archive SHA-256:
  `B79A148B0221890AE10F73F4B94B74FA92391C9F59D7D33E6FC8DF5237777EB7`

Root extracted the archive and independently checked:

- exactly 12 regular files;
- every extracted file byte-identical to the frozen candidate;
- extracted source SHA equal to
  `E7F8B3A6E84BD129BBDF5C49C524446BF3DFBE9C95C16F069F435CA104DCF65C`;
- legal 60-card deck;
- exactly one Hero's Cape / ACE SPEC;
- compile and import pass;
- one top-level `agent` definition;
- `agent` is the namespace insertion-order last callable;
- no cache or bytecode entries in the candidate or archive.

## Limitation and live interpretation

The full replay shadow necessarily returns to recorded parent states after the
first changed action. The complete alternative transactions are verified with
source-shaped counterfactual callbacks rather than full branched engine games.
The user explicitly requested a practical live probe once destructive defects
were excluded, so broad local win-rate evaluation is not required here.

After submission, causality must be judged only when one of the six rule IDs
actually proposes or owns a transaction. Unrelated losses should be logged
separately and must not be used to stack an unconnected repair onto this suite.
