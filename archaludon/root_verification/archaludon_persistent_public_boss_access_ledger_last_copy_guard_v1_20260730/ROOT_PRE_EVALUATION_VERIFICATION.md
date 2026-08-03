# Root pre-evaluation verification

Date: 2026-07-30 JST

Decision:
`PASS_FOR_IMMUTABLE_FIXED760_EXECUTION_ONLY`

This decision authorizes deterministic local evaluation. It does not authorize
packaging, Kaggle submission, formal-parent promotion, or cumulative
integration.

## Frozen identities

- exact historical-Silver parent `main.py`:
  `F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E`
- candidate `main.py`:
  `AACAC0B2E47C495A971A6CFCA91A393DBAC4A567291F849DB7912E9F26E9D3A3`
- parent and candidate `deck.csv`:
  `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`
- strategy selection:
  `D47611B40E937787BCD16DFCD0A86C317D712CC86958E7D1D7FCF0E15F6A2446`
- implementation report:
  `0FF9CCB058F5C7B15921B36E1389FE0F48571ABF0BC3B59847CA2E162D4E5FF0`
- implementation hash manifest:
  `BB514F878632F6E4763F4B02DA1661D7582E289D5365604A476E63C5CC6A7A3D`

The two runtime trees contain the same 12 relative files. Only `main.py`
differs; the other 11 files are byte-identical. The candidate tree contains
zero cache artifacts. A runtime search found no episode IDs, source-row IDs,
or replay-specific literals.

## Independent structural verification

Root independently compiled and imported the final frozen candidate with
Python 3.11 and bytecode writes disabled.

- compile/import: pass
- top-level `agent` definitions: exactly one, at line 2476
- last inserted callable: `agent`
- deck request: byte-order-equivalent to the extracted `deck.csv`
- deck count: 60
- ACE SPEC count: one Hero's Cape `1159`
- maximum non-Basic-Energy copy count: four
- cache artifacts after verification: zero

## Independent focused-evidence recomputation

The final focused JSON is bound to the final candidate hash. Root recomputed:

- 18/18 hard negatives return the exact parent action;
- invalid actions/errors: `0/0`;
- both logical seats cover search selection into hand, unselected reveal to
  unknown, discard, lost zone, return to hand, ordinary-turn persistence,
  Prize-to-hand confirmation, Unfair Stamp invalidation, result/new-game
  reset, and seat/first-player reset;
- the positive semantic change is exactly
  `[Boss 1182#39, Metal 8#57]` to
  `[non-ex Archaludon 840#31, Metal 8#57]`;
- an identical retry returns the cached action without advancing ledger state;
- option mutation and a mismatched post-emission observation fail closed to
  exact historical-Silver.

Focused JSON SHA-256:
`143C04BAE184AA18EA67656E37A9C36DE86C47AE11DAA26DE9FA82E1CB2A5AD2`.

## Independent engine-evidence recomputation

Candidate engine JSON SHA-256:
`1602932207B2BC6C0E35925C57A6039B2A36FB71C4C1B880F2CC17E838A62CC5`.

Root recomputed 16 unique branch keys over eight configurations:

- logical seats: `0` and `1`;
- option modes: identity, reverse, and duplicate-equivalent;
- serial offsets: `0` and `1000`;
- two branches per configuration: exact parent and candidate.

All eight paired comparisons prove:

- only the alternate preserves Boss;
- only the alternate substitutes non-ex Archaludon;
- the same Metal is discarded;
- the same Duraludon search and Bench action occur;
- the same Metal Defender `253`, target, damage, Prize result, and functional
  pre-attack state occur.

All 16 branches have zero invalid actions, exceptions, stale state,
max-step hits, and nondeterminism.

## Independent union-shadow recomputation

Union-shadow summary SHA-256:
`68210F16E6E18957E8E9F31F67B1EBF4ADA03F713BE64F057DD2B080256D0107`.

Root independently read the raw per-file rows and source manifest:

- source files: 261;
- unique `(population, episode, seat)` keys: 261;
- callbacks: 14,464;
- action differences: exactly one;
- difference and first-difference row sets: equal;
- missing source files: zero;
- byte-size mismatches: zero;
- SHA-256 mismatches across all 261 source replays: zero;
- action errors, exceptions, guard exceptions, emergency fallbacks,
  max-step hits, and external differences: all zero.

The sole difference is the certified source callback
`88819392:120`, seat 0. This replay reference exists only in the evidence CSV;
it is not present in runtime source.

## Frozen-rule and negative controls

- frozen-rule controls JSON:
  `A94FB33A21296BE3B1069932D9E24DE72C77A90CACCB1FDD35459F41C4B4A7C6`
- recorded positives: 27 spanning all eight cumulative rules
- ordered both-seat collision cases: 112
- new rule placement: below all eight frozen rules
- unknown/equal-rank collision: exact-parent fail closed
- episode `88775564` negative: 22 callbacks, zero differences, zero action
  errors; JSON SHA-256
  `EA81F76DE48048F1214956FBE5CC26B83DC3064F8A2D0F294899257879927D8E`

These are integration-contract controls, not evidence that the isolated
candidate already contains the eight-rule cumulative resolver.

## Immutable fixed-760 gate

Run the exact previously checked fixed-760 schedule:

- historical-Silver anchor: 100 games in each candidate seat, 200 rows;
- adjacent population: seven opponents, 40 games per seat per opponent,
  560 rows;
- exact total: 760 unique `(panel, opponent, seat, seed)` keys;
- max steps: 1000;
- baseline and candidate use identical seeds and both seats;
- preserve duplicate controls and full raw traces.

Require:

- zero execution faults, action errors, exceptions, missing starts, and
  max-step hits;
- exact schedule equality and duplicate-control equality;
- no regression in the 200-row historical anchor, 560-row adjacent panel,
  either 380-row seat total, or any panel/opponent/seat bucket;
- every outcome or trace difference inspected;
- a neutral schedule permits later cumulative integration of this valid
  dormant component, not formal-parent promotion.

