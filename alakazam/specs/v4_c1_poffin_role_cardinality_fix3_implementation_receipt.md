# v4 C1 Poffin role/cardinality fix3 implementation receipt

## Identity

- Immutable spec SHA-256:
  `F5301C098EC76C306CD1392078EEB78B6B1F14530C60103A662564714FA65883`
- Umbrella contract SHA-256:
  `B0657D0118847F2DDF7680E6D75AE28F2DF6CF42EE338B6355ADDC731F454783`
- Static-review amendment SHA-256:
  `592963EDE071F6B7DC023EA952F4A22D8D2E5FD45B5EDB51BA4DF43E5D8DEE11`
- Frozen parent:
  `alakazam_staged_20260729/versions/alakazam_newdeck_v3_exact_evolution_ko_fix2`
- Candidate:
  `alakazam_staged_20260729/versions/alakazam_newdeck_v4_poffin_role_cardinality_fix3`

## Changed files

- Production:
  `planner_deck_adaptation_v1.py`
  - SHA-256:
    `A23BF536227465661FD98087299D2672400E918DB9B168DFEB2B9C3CF60A4D9E`
  - bytes: `190855`
- Focused test:
  `test_v4_poffin_role_cardinality_fix3.py`
  - SHA-256:
    `FE9B93E73E9D0250A482DCBB66226C8F5E30883054849B8CBCEC212C07556874`
  - bytes: `28290`

The candidate differs from the frozen parent only in the changed production
planner and the new focused test. Cache directories and `.pyc` files are
absent.

## Behavioral intent

- Fire only after the inherited policy has selected one exactly resolved
  Buddy-Buddy Poffin (`1086`) PLAY action.
- Preserve that action when role demand and legal capacity remain.
- Veto zero-capacity or zero-demand Poffin and rerun the same inherited policy
  against the same MAIN callback with every Poffin PLAY option removed, then
  semantically rebind its winner to the original legal options.
- Own only exact optional Poffin `TO_BENCH` prompts and select deterministic
  physical cards in projected role order:
  Abra primary, Dunsparce primary, Abra backup, Dunsparce backup.
- Apply normal capacity
  `min(maxCount, 2, max(0, F - 1))`, with the single final-slot Abra exception.
- Return exactly zero, one, or two options as warranted; never add a third
  Dunsparce; rebind duplicate/reordered callbacks by semantic physical-card
  keys.
- Preserve active v1/v3 and inherited planner transactions, the
  Hilda -> Enriching -> emergency-reserve owner, terminal/current KO, Boss,
  and exact-evolution KO precedence.
- Emit JSON-safe `V4_POFFIN_ROLE_CARDINALITY` proof data under
  `LAST_V1_PACKAGE_TRACE["v4_poffin_role_cardinality"]` and
  `LAST_V4_POFFIN_TRACE`.
- On a genuinely new callback after C1 completion, release C1 and run the full
  v1/v3/C1/inherited arbitration once on that same callback.
- Certify public Abra/Dunsparce depletion against the exact 60-card partition,
  including hand, discard, field tops and components, public prizes, and owned
  stadium; owner, serial, or partition ambiguity preserves the parent action.
- Preserve hidden-zone uncertainty. If an inferred remaining target is absent
  from the irreversible child prompt, return legal `[]` with
  `HIDDEN_ZONE_TARGET_WHIFF`.
- Retain a semantic duplicate record for the original unfiltered callback even
  when filtered reranking establishes an inherited owner.
- Report uncertified reranking as
  `MAIN_RERANK_UNCERTIFIED_PARENT_PRESERVED` and preserve the original parent
  action. Completion actions are recorded in separate `completion_*` fields
  without overwriting the original Poffin decision axes.

## Verification

Commands used the checked engine:

```text
PYTHONPATH=C:\Users\amuam\project\AI_pokeka_competition\analysis_outputs\cynthia_v9_vs_v11_poffin_role_selection_20260713\seeded_engine
```

1. Focused suite:

```text
C:\Users\amuam\project\AI_pokeka_competition\.venv-rl\Scripts\python.exe -m unittest -v test_v4_poffin_role_cardinality_fix3.py
```

Result: `25/25 OK`, exit code `0`.

The focused total includes all eight static-review fixtures:
child-completion exact-evolution re-entry, child-completion Psychic Draw
re-entry, MAIN-bookkeeping completion re-entry, public role-basic depletion,
hidden-zone target whiff, rerank-owner duplicate rebinding, uncertified rerank
parent preservation, and original Poffin trace-axis preservation. It also
checks duplicate serial, wrong owner, and invalid 60-card partition
fail-closed behavior.

2. Candidate full suite:

```text
C:\Users\amuam\project\AI_pokeka_competition\.venv-rl\Scripts\python.exe -m unittest discover -v
```

Result: `191/191 OK`, exit code `0`.

3. Frozen-parent full suite, run from the parent directory:

```text
C:\Users\amuam\project\AI_pokeka_competition\.venv-rl\Scripts\python.exe -m unittest discover -v
```

Result: `166/166 OK`, exit code `0`.

4. Changed-source compile:

```text
C:\Users\amuam\project\AI_pokeka_competition\.venv-rl\Scripts\python.exe -m py_compile planner_deck_adaptation_v1.py test_v4_poffin_role_cardinality_fix3.py
```

Result: `2/2 OK`, exit code `0`. Generated cache artifacts were removed after
the compile check.

5. Deck:

- exact card rows: `60`
- SHA-256:
  `F598F5E578D0440C96DC0492EAECF2E19739B7A23225BE57114A724EF7D0FB94`
- unchanged from parent: `YES`

6. Episode `88844273` fixed public fixtures:

| step | parent/candidate action |
| ---: | :--- |
| 67 | `[0]` |
| 98 | `[0]` |
| 121 | `[4]` |
| 148 | `[0]` |

## Closure and parent invariance

Closure algorithm: top-level non-test Python, top-level `deck.csv`, and
`runtime/main.py`; relative paths sorted lexically; each row is
`path + NUL + uppercase file SHA-256 + NUL + byte size + LF`.

- Frozen parent policy closure, `33` files:
  `DC90205DE06AE3E2E41ADC661577096BB02EE5B42AB9F4366FC1A01154745B47`
- Frozen parent planner:
  `255FD9E1303E8E6DFB286952023A7F086CD233B4E5D5030EDBE06313A40697B7`
- Candidate policy closure, `33` files:
  `DE7FCD20A1B3362E845B8573DC6178E32B13F250EA8AC8619B7BA0AA704D271D`

The parent closure and planner match the immutable specification.

## Known tradeoffs and evaluator checks

- MAIN proves public exhaustion but never guesses a hidden prize location. At
  `A == 0, F == 1`, it preserves the parent Poffin only while at least one Abra
  remains outside public zones; the exact child safely returns `[]` with a
  whiff trace if that card is hidden outside the searchable deck.
- A certified zero-demand MAIN veto evaluates the inherited policy a second
  time on an option-filtered copy. Any failure to certify or semantically
  rebind that result preserves the original parent action and records
  `PARENT_RERANK_NOT_CERTIFIED`.
- Formal simulations and packaging were intentionally not run.

The evaluator must test at least 30 exact Poffin child contexts across both
seats and at least three opponents (including two non-mirrors), exercise all
0/1/2 cardinalities, cover at least 10 changed-or-preserved MAIN decisions,
and require zero action errors, transaction faults, and stale aborts.
