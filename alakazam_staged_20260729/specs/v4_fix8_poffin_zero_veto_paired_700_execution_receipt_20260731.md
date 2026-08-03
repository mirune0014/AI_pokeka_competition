# v4 Fix8 ポフィン0需要拒否・700組比較 実行記録

実行日: 2026-07-31

## 固定入力

- 比較仕様:
  `alakazam_staged_20260729/specs/v4_fix8_poffin_zero_veto_paired_700_20260731.json`
- 比較仕様 SHA-256:
  `59B50A77A8D2B4852D9ADFD8F42D3121F56E8D2AC74E15EDDF0F52AE1E52ABA8`
- 自然到達監査:
  `analysis_outputs/v4_poffin_bench0_causal_analysis_20260731/numeric/fix8_reach_screen_ultra_audit.json`
- 自然到達監査 SHA-256:
  `A0B8BEC9BA16270F27B940E2E9A99164F9AB560414092FDCCA54D1C3B283530B`
- 自然到達判定:
  `INTEGRITY_PASS_AND_NATURAL_REACH_PASS`

## 実行

比較仕様の `runner_partition.a`、`runner_partition.b`、
`runner_partition.c` を、checked
`tools/run_seeded_paired_suite.py` で実行した。

全35パネルの正規出力は次にある。

```text
alakazam_staged_20260729/evaluations/
  v4_fix8_poffin_zero_veto_unused_seed_700_20260731/
    panels/<seed_base>_<opponent>/attempt_1/
```

各パネルは次を生成した。

- `paired_results.csv`: データ20行
- `manifest.jsonl`: 6行
- `cell_summary.csv`: データ2行
- `report.json`: `valid=true`

rootによる結合前の機械再確認値は次のとおり。

- panel: 35
- paired row: 700
- manifest row: 210
- raw summary row: 2,100
- action error: 0
- max-step hit: 0
- unstarted: 0
- invalid result: 0
- duplicate baseline mismatch: 0
- missingまたはinvalid panel: 0

## 実行上の訂正記録

partition Cの初回起動は、`--opponent`へ`NAME=PATH`ではなく
`PATH`だけを渡したため、argparseがexit code 2で拒否した。

この時点では対戦は0件で、panel出力も生成されていなかった。

引数を仕様どおりの`NAME=PATH`へ訂正し、全11パネルを
`attempt_1`として実行した。

partition C担当の最終proseには`manifest rows 5`という記述が
1か所あったが、同じ報告内ではJSONL 6行とも記されていた。

rootが全35個の実ファイルを直接再計数した結果は、各パネル6行、
合計210行である。

この不一致はrawへ合わせて黙って置換せず、転記上のoff-by-oneとして
ここに記録する。

## 結合前のソース再確認

- C2 baseline adapter `main.py`:
  `EAF8763BAE815637DE07C73D039BD1EF54BD8F04B17F6D74C97E73FAE7C7B4C5`
- Fix8 candidate adapter `main.py`:
  `094DC137BAF552CB1BCB89A528128579CAB80BB5195980C073F5F978F9A46645`
- checked paired runner:
  `5EC25C98F2777FF61DE2DBD0A03A08519A7FEA4B2B4C510B5B8895BC2000E000`

すべて固定仕様と一致した。
