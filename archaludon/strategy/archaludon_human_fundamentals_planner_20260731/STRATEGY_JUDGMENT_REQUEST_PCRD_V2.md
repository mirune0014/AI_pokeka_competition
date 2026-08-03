# Strategy judgment request: PCRD v2

## Decision question

Select exactly one next rule hypothesis after rejecting
`PUBLIC_COMBAT_RETURN_DOMINANCE_V1`.

The preferred candidate is a repaired PCRD v2 with:

- post-action, post-public-reply location-aware resource accounting;
- a lexicographic hard-condition hierarchy;
- retention of proven Coated Attack current-KO and Basic-prevention lines;
- rejection of same-Prize, same-survival, nonlethal-chip-only evolution into
  the same certain return KO.

Decide whether this is the strongest coherent next move. If yes, freeze exact
positive, negative, fail-closed, and transaction requirements for one
Sol-xhigh implementation worker. If no, select one alternative from
`NEXT_HYPOTHESIS_OPTIONS.md` and explain why it should precede the known defect.

## Immutable sources

- V2:
  `candidates/archaludon_parent_first_complete_turn_fundamentals_v2/main.py`
  SHA `5A6B82E159CD7EC297AFD2B520580F97DDB01B7D500683F053B4C7096192CA0C`
- rejected PCRD v1:
  `candidates/archaludon_public_combat_return_dominance_v1/main.py`
  SHA `DCF7A4AB477CEA3743E7053DCABD0B1FBFDA20B13E84D256995A3557209400F1`
- deck:
  SHA `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`

## Root-verified evidence

- fixed760 root recomputation:
  `evaluations/archaludon_public_combat_return_dominance_v1/ROOT_FIXED760_RECOMPUTATION.md`
  SHA `3C0233B9CA83402DB1FFE85875F736768CDBC4B46768DE644AADAFE8715A74B5`
- Historical qualitative audit:
  `.../qualitative_historical_diff_audit/AUDIT.md`
  SHA `5A20550D7634404128D7AE8995ADFCA58434515B2810617E5912F5476BFB2C28`
- adjacent five addendum:
  `.../qualitative_historical_diff_audit/ADJACENT_FIVE_ADDENDUM.md`
  SHA `C1A4F32B636C3B26938C133E37EAFE297347FCBE020BB560A4963524DB765994`
- implementation verification:
  `implementation/archaludon_public_combat_return_dominance_v1/VERIFICATION.md`
  SHA `B5F729B40CED3CD70126C767C3A1B41140A540DF2D5D1D3A32DF2F1BCA207711`

Root row recomputation:

- 760 unique pairs;
- V2 474 wins, PCRD 474 wins;
- one gain, one regression, 758 same outcomes;
- 48 manifests, all exit zero;
- 2,280 summary rows;
- zero action errors, max-step hits, not-started games, and duplicate mismatch;
- 16 byte-different trace pairs.

Qualitative classification of the 16 first differences:

- sound: Historical 71 and 89, adjacent arch-peak seat0 game19;
- defensible: Historical seat1 game2;
- unsound: the remaining 12.

## Required dependency order

The broader human-fundamentals program remains:

1. trustworthy shared combat/return and resource ledger;
2. deterministic public effect coverage;
3. Trainer-purpose and whole-turn transaction replacement;
4. Prize race, harmful KO, Bench threat, and comeback modes;
5. setup, first/second choice, and Turbo Flare opening.

The next rule must not attempt to complete all five groups at once.
It must leave exact interfaces for the next group and preserve the V2 fallback.
