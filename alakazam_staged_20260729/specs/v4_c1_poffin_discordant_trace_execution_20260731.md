# v4 C1 ポフィン勝敗反転局面・固定再実行仕様

日付: 2026-07-31

## 目的

ポフィン候補 C1 と親版の勝敗が異なった試合について、同一 seed・同一
seat・同一対面を再実行し、最初の方策差とその後の盤面推移を保存する。

この再実行は既存 700 組の勝率評価を置き換えない。
既存結果と再実行結果が一致しない試合は、解釈対象から除外する。

## 固定入力

元 paired CSV:

`alakazam_staged_20260729/evaluations/v4_c1_poffin_fix3_combined_attempt2/combined_paired_results.csv`

SHA-256:

`BAFA80721A1095E3033B8AA82D344936A5438243EB98698838175B4EFCAF6394`

そこから opponent の完全一致だけで機械抽出した 100 行の schedule:

| opponent | schedule | rows | discordant | SHA-256 |
|---|---|---:|---:|---|
| marnie | `analysis_outputs/v4_poffin_bench0_causal_analysis_20260731/rerun_specs/marnie.csv` | 100 | 19 | `897BECDAA323F9FC841DEEFF99648FA2C46C8370E9E5D06E3C31D25FE502D6BB` |
| cynthia | `analysis_outputs/v4_poffin_bench0_causal_analysis_20260731/rerun_specs/cynthia.csv` | 100 | 24 | `0B36883863D5AC86C51D0A4C4BD18A928249EE6584A75CE4E6D7E768EDED1401` |
| rocket_mewtwo_spidops_proxy | `analysis_outputs/v4_poffin_bench0_causal_analysis_20260731/rerun_specs/rocket_mewtwo_spidops_proxy.csv` | 100 | 28 | `B459D703018BFDD402218DB581E53F6A5C9B72BBD1FCBF638902E26219962460` |
| historical_silver | `analysis_outputs/v4_poffin_bench0_causal_analysis_20260731/rerun_specs/historical_silver.csv` | 100 | 14 | `A28A83C44FC7A800D99166A7EC7F59364492BD058C0226C901F5C5ADA0E0A439` |

合計 85 discordant pairs、170 one-game runs である。

## 固定方策と実行系

Engine:

`analysis_outputs/cynthia_v9_vs_v11_poffin_role_selection_20260713/seeded_engine`

tree SHA-256:

`466638706BD5C6915E25D1B3CB9E3D966390FBC263F4ED3153108E29C0194FFF`

Baseline adapter:

`alakazam_staged_20260729/eval_adapters/alakazam_newdeck_v3_exact_evolution_ko_fix2`

Candidate adapter:

`alakazam_staged_20260729/eval_adapters/alakazam_newdeck_v4_poffin_role_cardinality_fix3`

両 adapter の `main.py` SHA-256:

`426F1BBB71583A691CBF39A07FA8A042CB0AB0600EB43F22F9E4DBD247E5AAEC`

Baseline closure:

`DC90205DE06AE3E2E41ADC661577096BB02EE5B42AB9F4366FC1A01154745B47`

Candidate closure:

`DE7FCD20A1B3362E845B8573DC6178E32B13F250EA8AC8619B7BA0AA704D271D`

Trace runner:

`tools/trace_paired_outcome_divergences.py`

SHA-256:

`0719502B38E84F56563C8B6461B12948D021BAA9CB7680B5E8B39088A6A98CA2`

Battle runner:

`tools/run_local_battle.py`

SHA-256:

`E1ABA0151CDAEE425B858511AA760CE5C5647D555DDEFBD69D7319C29C5B773B`

Python:

`.venv-rl/Scripts/python.exe`

## 対面

```text
marnie
  meta_agents/marnie_sota_live_85033057_simple

cynthia
  meta_agents/cynthia_garchomp_nasuo445_v80_legal_complete_role_cycle

rocket_mewtwo_spidops_proxy
  meta_agents/rocket_mewtwo_spidops_kashiwashira_20260703_simple

historical_silver
  analysis_outputs/reference_agents/historical_silver_archaludon_54495224
```

## 実行条件

- schedule CSV の `baseline_win != candidate_win` の行だけを実行する。
- `seat` と `seed` は各行をそのまま使う。
- `--max-steps 1000`
- `--engine-seed`
- `--trace-scores`
- `--trace-score-limit 30`
- `--trace-options`
- baseline と candidate は必ず別 process で実行する。
- 既存出力を上書きしない。

出力先:

```text
analysis_outputs/v4_poffin_bench0_causal_analysis_20260731/discordant_traces/
  marnie/
  cynthia/
  rocket_mewtwo_spidops_proxy/
  historical_silver/
```

## 完全性条件

- 4 command が exit 0。
- manifest は合計 170 行。
- 各 `(opponent, seat, seed, role)` は一意。
- summary は合計 170 行で、action error 0、max-step 0。
- 各 summary の policy-side win を schedule の `expected_win` と照合する。
- 既存 paired 結果と不一致の pair は明示し、局面診断から除外する。
- trace は 170 個すべて非空。
- 対面 path、agent path、deck path、engine pathを manifest に保持する。

数値解釈や採否判断は実行担当が行わない。
