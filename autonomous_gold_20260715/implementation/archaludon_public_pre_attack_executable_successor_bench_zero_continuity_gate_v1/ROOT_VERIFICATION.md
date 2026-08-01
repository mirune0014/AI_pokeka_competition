# Root verification: Task 4 successor-continuity gate

Date: 2026-08-02 JST

## Scope

Task 4 adds one stateless veto-only gate inside the inherited same-active pre-attack transaction. It does not choose search targets, Ultra Ball discard costs, recovery targets, Bench targets, Energy attachment targets, or Turbo Flare allocation. Its only job is to stop a non-terminal attack override from replacing a valid parent board-forming action when public information proves that no executable successor exists.

Precedence is unchanged:

1. unique exact terminal attack;
2. an existing transaction owner;
3. Task 4 continuity preservation;
4. inherited non-terminal attack preference.

## Frozen inputs

- Exact parent: `packages/archaludon_public_exact_same_active_attack_dominance_v1_clean_20260801_2352/extracted_frozen_verification`
- Parent `main.py` SHA-256: `914B8419ECAFB57D8F0CDC462E6035DB0EE6325044DFBCCE216F0FE759CE92DF`
- Candidate `main.py` SHA-256: `CAF2C696AE9F6102C1A4A8E67649C309104064CAABF9643865BE766D91BDE8DD`
- Candidate `deck.csv` SHA-256: `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`
- Strategy selection SHA-256: `4AF61D7E26B56F32B2614A230EFA619400ED4A1A03816A5C5A3BDE3D0E5D02B9`
- Focused fixture runner SHA-256: `FE284BAECE388B614B27EB86205DAE6305D966E15C8D571D16B263947DD0BB80`

The candidate preserves the parent's clean 12-file submission layout. The other 11 files are byte-identical to the exact parent package.

## Root checks

### Compile, import, loader, and deck legality

- Python 3.11 compile: PASS
- Import: PASS
- Last top-level callable selected by the Kaggle-style loader: `agent`
- Two repeated deck requests: deterministic and identical
- Deck total: 60 cards
- ACE SPEC count: one `Hero's Cape`
- Candidate and implementation trees: zero `__pycache__` directories and zero `.pyc` files

### Focused behavior

The root reran the immutable focused fixture runner: 33/33 PASS.

Positive coverage includes Bench 0 preservation and publicly proven no-successor preservation for direct Basic PLAY, Poké Pad, Ultra Ball, and Night Stretcher with a public discarded Basic. Negative coverage includes terminal attack, existing owner, ready backup, full Bench, empty deck search, missing recovery Basic, unknown proof, malformed state, ambiguous parent binding, unrelated binding failure, and non-MAIN callbacks. Both seats, option permutations, and duplicate calls are covered.

### Episode 89347400 regression anchor

The root reran the checked replay comparator against the exact parent for the correct seat.

- Canonical decisions: 11
- Candidate-parent differences: 2
- Unchanged decisions: 9
- Step 12: inherited immediate Turbo Flare override is vetoed; the parent Explorer action is preserved.
- Step 19: inherited immediate Turbo Flare override is vetoed; the parent Ultra Ball action is preserved.
- Neither difference is a terminal-attack position or an existing-owner position.

Task 4 intentionally does not simulate or own the later Explorer/Ultra Ball continuation. Those transactions remain Task 5 and Task 6 work.

### Targeted historical shadow

Eight representative historical replays produced 389 correct-seat decisions and seven candidate-parent differences. Every difference was inspected. All seven preserve a non-terminal board-forming/support action under Bench 0 or exact public no-successor proof. No exact terminal attack, active transaction owner, or publicly executable backup was displaced.

### Exact-engine smoke

The candidate was run against the historical-Silver Archaludon anchor in both orientations.

- Orientation 0, seed 804201: started, terminated, 101 steps, zero action errors, no max-step hit.
- Orientation 1, seed 804202: started, terminated, 139 steps, zero action errors, no max-step hit.

## Decision

Task 4 implementation gate: **PASS**.

This is an implementation and safety decision, not a claim of broad matchup improvement or Kaggle adoption. The candidate is ready to serve as the parent for Task 5 and Task 6, which must complete the card-specific search/discard/place/energy transactions that Task 4 now protects from premature attack overrides.
