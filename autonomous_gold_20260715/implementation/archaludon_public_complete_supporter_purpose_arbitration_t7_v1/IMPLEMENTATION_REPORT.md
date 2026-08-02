# Task 7 implementation report

## Files and hashes

- Candidate `main.py`: `8364A91B1DAF48968D9D5C3BBA257D43546E27AB7076841A5400124048602E28`.
- Candidate `deck.csv`: `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`.
- Frozen parent `main.py`: `99EE7BF5E6E6D61D863EF1D131232F90DCE36A3CFDF032AF6E534DECA79B2756`.
- `run_focused_fixtures.py`: `1BF6C6C094CCAF253173449EF7E0EABEAB57955B3CE8209CFC9B754A298B364F`.
- `run_replay_shadow.py`: `DBB126BA83630E9CBFC34ED4020FF3A9D9AF274A3EB34B1029A0088978D70E64`.
- `verify_structure.py`: `6E012EB12FB01F6B9BDD14C07BA5784E5A0B9AA4954D581CC346B9B9448D669F`.

The candidate is a full copy of the frozen parent. `git diff --no-index --numstat`
reports `1148 0 main.py`; all other 11 package entries are byte-identical.

## Behavioral intent

The only new purpose is `FINISH_NOW_EXACT_BOSS`. On an owner-free MAIN
callback, Task 7 admits direct Boss or Pokégear only when a payable current
attack has an exact public post-gust certificate with `ko=True` and
`prize_yield >= own remaining Prizes`, while attacking the current Active is
not already terminal. It selects exact targets by
`(-prize_yield, -lethal_margin, target_semantic_fp, target_serial, attack_id)`
and binds the minimum physical Boss serial. Direct Boss has a stateful
Boss/target/attack transaction. Pokégear reuses the inherited PF Gear
transaction and binds Boss only in the reveal callback; Explorer and Lillie
are never generally valued by Task 7 and produce a legal empty reveal choice
when Boss is absent.

The Gear reveal certificate is committed only after the reveal action has
been emitted, using the emitted callback fingerprint and semantic roles.
Reveal rows are normalized and sorted as
`(card_id, serial, status, semantic_role)`, so raw option order cannot alter
the reveal hash or rejection ledger. A rebound of the identical Gear prompt
increments the Task 7 certificate's `duplicate_count` and refreshes its hash.

Lunatone card 675's exact Lunar Cycle metadata is locally classified as
`OWN_TURN_HAND_ENGINE_ONLY_NO_INCOMING_COMBAT_MODIFIER` only during a Task 7
combat-oracle call. Both global skill maps are restored in `finally`. A name,
text, HP, card ID, skill-count, or frozen text-hash mismatch fails closed.

## Verification

### Compile and import

Command:

```text
.\.venv-rl\Scripts\python.exe -B -c <compile the candidate main.py and three assigned verification scripts; import the candidate>
```

Outcome: exit 0, `compile_ok 4 import_callable True`, final rule
`PUBLIC_COMPLETE_SUPPORTER_PURPOSE_ARBITRATION_T7_V1`, purpose
`FINISH_NOW_EXACT_BOSS`.

### Focused fixtures

Command:

```text
.\.venv-rl\Scripts\python.exe -B autonomous_gold_20260715/implementation/archaludon_public_complete_supporter_purpose_arbitration_t7_v1/run_focused_fixtures.py
```

Outcome: exit 0, 94/94 passed. Output
`focused_fixture_results.json`, SHA-256
`6DDD98AD638E10E9639F5B4F558C81606472E0DB7C9B6448EDE73A9B0C1F9DCA`.

Coverage includes both seats; episode 89292594 Boss -> canonical target ->
Metal Defender; start and target retries; option reversal; HP 221, current
terminal, Boss-illegal, Supporter-used, insufficient-Prize and no-Bench
controls; all eight Boss/Explorer/Lillie reveal subsets in both seats; legal
miss clearing; duplicate Boss minimum-serial selection; complete Gear hit
lifecycle; hidden-opponent-hand invariance; existing-owner holds; and zero
owner collisions. Both seats also hold `looking` fixed while reversing only
the option rows: minimum Boss, selected route, emitted certificate hash,
callback fingerprint/roles, normalized rejection rows, and reveal hash all
remain identical. Rebinding each reversed prompt returns the same action,
increments `duplicate_count` to one, and leaves the two retry certificate
hashes identical. Direct conservation is `2 starts = 2 completes`, with zero
aborts/exceptions. PF Gear conservation holds with 24 fixture starts and no
live transaction.

Lunar Cycle fixtures prove identical `(220, True, 1)` damage/KO/Prize with and
without the Ability, exact global-map restoration, and UNKNOWN on a one-byte
text change. All four episode-89292594 Bench targets are exact after the scoped
classification; canonical target serial 3 remains selected.

### Current and historical replay shadow

Command:

```text
.\.venv-rl\Scripts\python.exe -B autonomous_gold_20260715/implementation/archaludon_public_complete_supporter_purpose_arbitration_t7_v1/run_replay_shadow.py
```

Outcome: exit 0. Output `replay_shadow_results.json`, SHA-256
`8F485FC97927BC8CB91D2F0C6246400322239AA2B3ECFECD8D328F2DAD1F02D8`.
The script covered 45 readable current plus 207 historical replays: 252
replays and 13,829 decisions. There were ten semantic differences in nine
replays, and every difference was classified
`T7_EXACT_TERMINAL_BOSS`; unexpected differences were zero. There were 19
Task 7 activations, all direct-hand exact Boss routes.

Episode 89292594's first difference is parent Duraludon play -> Boss serial
101, target serial 3, Metal Defender 253. The other first-difference episodes
are current 89278577, 89288308 and 89290439, plus historical 87773965,
87858380, 88073289, 88252126 and 88293552. Historical 88482123 had Task 7
activation telemetry but no semantic difference.

One current source file, episode 89287701, is a pre-existing truncated
3,145,728-byte JSON and was not interpretable. The output records SHA-256
`601498052C7D2F96BCFB0972BBB65DBC7B76E76D41C19BACBD5EE06EB5837AAC`
and the exact JSON error rather than silently treating it as shadow evidence.

### Both-seat extracted engine smoke

Commands:

```text
.\.venv-rl\Scripts\python.exe -B tools/run_local_battle.py --engine-dir autonomous_gold_20260715/candidates/archaludon_public_complete_supporter_purpose_arbitration_t7_v1 --agent-a autonomous_gold_20260715/candidates/archaludon_public_complete_supporter_purpose_arbitration_t7_v1 --agent-b analysis_outputs/reference_agents/historical_silver_archaludon_54495224 --games 1 --max-steps 1000 --seed-base 2026080207 --no-trace --summary autonomous_gold_20260715/implementation/archaludon_public_complete_supporter_purpose_arbitration_t7_v1/engine_smoke_seat0.jsonl

.\.venv-rl\Scripts\python.exe -B tools/run_local_battle.py --engine-dir autonomous_gold_20260715/candidates/archaludon_public_complete_supporter_purpose_arbitration_t7_v1 --agent-a analysis_outputs/reference_agents/historical_silver_archaludon_54495224 --agent-b autonomous_gold_20260715/candidates/archaludon_public_complete_supporter_purpose_arbitration_t7_v1 --games 1 --max-steps 1000 --seed-base 2026080208 --no-trace --summary autonomous_gold_20260715/implementation/archaludon_public_complete_supporter_purpose_arbitration_t7_v1/engine_smoke_seat1.jsonl
```

Outcomes: exit 0; 33 and 111 steps; action errors 0/0; max-step hits false/false.
Raw output hashes are
`1C3BD34E14144CEE4D238B6B8FB11768C53A717EE3DFED165A7187E52122DBD3`
and `3DAE5F541BB1D296035C0F54D9B378A8266287646D85A33EF4EB4C0782F5F97F`.
An initial invocation using symbolic `candidate` agent labels failed before
game start because the runner interpreted them as a `candidate/deck.csv`
path. The two commands above use the exact candidate path and succeeded.

### Structure, legality and cache

Command:

```text
.\.venv-rl\Scripts\python.exe -B autonomous_gold_20260715/implementation/archaludon_public_complete_supporter_purpose_arbitration_t7_v1/verify_structure.py
```

Outcome: exit 0; final AST callable and imported callable are `agent`; package
entry count 12; only `main.py` differs; deck count 60; ACE SPEC count 1; no
cache entries. Output `structural_results.json`, SHA-256
`9B94727F8E0818CE0CC550F69DA6B3404D70DAFE75923A8B4D2E3326785743D8`.

## Known tradeoffs and evaluator checks

- Task 7 does not add general Explorer or Lillie valuation, nonterminal Boss
  target valuation, reversal logic, or harmful-KO avoidance.
- It refuses incomparable multi-attack terminal routes and any chosen target
  whose combat/payment metadata is not exact.
- Static shadow cannot execute the counterfactual suffix after a first changed
  action; both-seat direct and Gear callback completion is therefore covered
  by focused stateful fixtures and native-engine smoke.
- The evaluator should inspect the 94 fixture rows, especially both option-only
  reversal and duplicate-retry certificate rows; all ten classified shadow
  differences; the scoped Lunar Cycle map restoration; both smoke rows; and
  conservation/owner-collision fields.

No archive was created. No Git commit/push, Kaggle call, upload, Notebook,
Discussion, package publication, or Codex configuration change was performed.
