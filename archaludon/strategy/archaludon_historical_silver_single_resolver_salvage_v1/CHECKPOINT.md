# CHECKPOINT

Updated: 2026-08-03 JST

## Invariants

- Silver scorer unchanged.
- One final agent, one resolver, one active transaction.
- One rule at a time.
- UNKNOWN returns Historical-Silver.
- Failed rules are removed, not patched by another rule.
- Existing artifacts remain read-only.

## Completed final candidate

- Candidate: `autonomous_gold_20260715/final/archaludon_historical_silver_single_resolver_salvage_v1`.
- Accepted rules: 1, 4, and 5.
- `main.py`: `D966E455E5110F9D5616195AEAAC8663E6A92F310DAFC4B7F79E4D37149A9C62`.
- Historical-Silver parent: `F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E`.
- `deck.csv`: `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`.

## Accepted rules

- Rule 1, exactly-one Duraludon setup: fixed160 `100=100`, natural starts 28,
  faults 0.
- Rule 4, exact materialization before parent Lillie: fixed160 `100=100`, two
  intended natural differences, faults 0.
- Rule 5, exact current win / unique higher-Prize Boss: fixed160 `100=100`, two
  intended direct-win differences, faults 0. Boss route was dormant and was
  not widened.

## Failed or deferred rules

- Rule 2 continuity: `DEFER-DORMANT`; no natural fire, not integrated.
- Rule 3 Ultra Ball: `REJECT`; fixed160 `100 -> 99`, one regression.
- Rule 6 Poké Pad: `REJECT`; one start but no naturally completed route.
- Rule 7 Turbo Flare concentration: `REJECT`; fixed160 `100 -> 98`, G/R/T
  `3/5/152`, seat 1 `-3`; fixed760 forbidden.
- Rule 8 same-Active attack dominance: `DEFER-DORMANT`; shadow plus fixed160
  produced zero starts and zero differences. Fixed160 was `100=100`, G/R/T
  `0/0/160`, with all 160 traces byte-identical.
- Rule 9 Pokégear/Supporter complete plan: `DEFER-DORMANT`; fixed160 was
  `100=100`, G/R/T `0/0/160`, but no complete natural Gear-to-Boss terminal
  transaction was proven.
- Rule 10 proactive FML exact exchange: `DEFER-DORMANT`; shadow 30,977
  callbacks plus fixed160 produced zero starts and completions. Fixed160 was
  `100=100`, G/R/T `0/0/160`, with all 160 traces byte-identical.

## Final fixed760

- Historical-Silver `478/760`、candidate `480/760`。
- G/R/T `4/2/754`、mirror `100=100`、seat 0 `+2`、seat 1 `0`。
- Worst opponent delta `-1`。
- Fault、invalid action、exception、max-step、duplicate mismatchはすべて0。
- 145 first differencesをRule 1 `128`、Rule 4 `14`、Rule 5 `3`へ全分類。
- Base non-destruction gate: **PASS**。
- Strengthened gate: **FAIL** (`480 < 486`)。
- Sol-Ultra final judgment: **ACCEPT as non-destructive rebaseline**。

## Completion

要件定義v1の実装と所定検証は完了。追加規則、追加検証、Kaggle提出、デッキ変更、
Alakazam移植は行わない。将来の強化は別versionで開始する。

Rule 1後にSilverのUltra Ball検索が重複Duraludonを選ぶ相互作用を1 regressionで
確認した。現在候補への補修は行わず、独立した将来仮説としてのみ扱う。
