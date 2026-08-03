# Root verification: general visible-counterattack ready rotation v1

Date: 2026-07-31 JST

Decision: `SAFE_TO_PACKAGE_FOR_USER_LIVE_PROBE`

No Kaggle submission was performed.

## Frozen identity

- Candidate:
  `autonomous_gold_20260715/candidates/archaludon_general_visible_counterattack_ready_rotation_v1`
- Candidate `main.py` SHA-256:
  `AC70708082882C7BA01CFBF81D29F534B95166DFF6BAD11E1EF1FA001A5F79D2`
- Direct parent `main.py` SHA-256:
  `E7F8B3A6E84BD129BBDF5C49C524446BF3DFBE9C95C16F069F435CA104DCF65C`
- Deck SHA-256:
  `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`
- Clean archive SHA-256:
  `B2992E4A5F97A14127F6E75D4D3F3F528725E34ABC9854F06592B82D8EA24C95`
- Clean archive size:
  `2,072,276` bytes

Only `main.py` differs from the direct parent after excluding the parent's
pre-existing cache files. The candidate has exactly 12 runtime files and zero
cache files.

## Implemented rule

The narrow Mega Starmie-only rotation was replaced by
`GENERAL_VISIBLE_COUNTERATTACK_READY_ROTATION_V1`.

Before the exact parent-selected attack, the rule may perform:

`RETREAT -> unique ready backup -> same attack`

It starts only when:

1. the parent-selected attack is not an immediate game-winning attack;
2. exactly one legal retreat and exactly one ready Bench replacement exist;
3. the replacement preserves the same attack ID, target, deterministic damage,
   deterministic effect, KO result, and immediate Prize conversion;
4. at least one currently visible payable opponent reply KOs the current
   Active;
5. the replacement survives every supported visible payable reply; and
6. fixed Bench damage or damage-counter effects cannot KO the rotated-out
   Pokemon.

The reply set includes:

- attacks from a surviving opposing Active;
- attacks from ready opposing Bench Pokemon after a publicly legal retreat;
- attacks from every opposing Bench promotion candidate after a KO;
- public next-turn self-attack locks, bound to both attack ID and attacker
  serial;
- previous-Evolution attacks made available by a visible Memory Dive-type
  ability; and
- deterministic fixed Bench damage and damage counters.

Only an actually payable unsupported material reply fails closed. The rule does
not use opponent IDs, replay IDs, matchup names, HP ratios, Prize leads, or
source-state signatures.

## Demonstrated broad firing and evidence-led narrowing

The initial broad implementation naturally started 15 times in the 89-replay
population. Inspection found three proof errors or unnecessary starts, and only
those demonstrated causes were repaired:

- `88929453 / step 87`: Memory Dive exposes a post-attack inherited Raging
  Hammer for 300, which also KOs the proposed backup.
- `88935472 / step 106`: after Metal Defender leaves the opposing Active at
  100 HP, Memory Dive exposes inherited Raging Hammer for 380, which also KOs
  the 290-HP backup.
- `89001625 / step 117`: Mega Brave is publicly locked from the preceding use;
  the remaining Aura Jab deals only 100 to the 220-HP current Active, so no
  rotation is needed.

The corrected rule still naturally starts 12 times. In particular,
`88924284 / step 123` continues to start because the locked opposing Active can
publicly retreat to a ready Bench Mega Lucario that can use Mega Brave. This
confirms that the lock repair did not erase the real Bench-threat route.

## Root-recomputed verification

Root reran the focused test with Python 3.11:

- positives: `10/10`;
- complete deterministic callback transactions: `10/10`;
- proof-repair cases: `14/14`;
- negatives: `14/14`;
- overall: PASS.

Root independently reran the final-source shadow:

- episodes: `89`;
- callbacks: `4,864`;
- natural starts: `12`;
- candidate-parent action differences: `11`;
- first differences: `10`;
- unresolved harm inspections: `0`;
- action errors: `0`;
- exceptions: `0`;
- telemetry errors: `0`;
- emergencies: `0`.

The 15 shadow rollbacks are expected: after recording the candidate's
counterfactual retreat, the historical replay continues along the recorded
parent attack branch. They are not failed candidate transactions.

## Package verification

The archive was extracted into a fresh directory:

- exact runtime files: `12`;
- candidate/extracted hash mismatches: `0`;
- cache entries: `0`;
- loader-last callable: `agent`;
- loader identity: PASS;
- deck request: `60`;
- legal deck rows: `60`;
- Hero's Cape / ACE SPEC count: `1`.

The exact archive contents were then run through one full local engine game in
each seat against historical-Silver Archaludon:

- candidate seat 0, seed `731045701`: exit `0`, 160 steps, action errors `0`,
  max-step hit `false`;
- candidate seat 1, seed `731045702`: exit `0`, 84 steps, action errors `0`,
  max-step hit `false`.

Both smoke games were losses. This gate is intentionally destructive-safety
only; the result does not block the user-requested exploratory live probe.
