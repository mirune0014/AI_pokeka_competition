# v3 サイコドロー任意化 fix1 実行環境追補

## 追補理由

`v3_psychic_draw_optional_fix1_immutable_spec.md` に固定した Python と engine は正しいが、最初の独立再実行では engine directory を `PYTHONPATH` へ渡さなかった。

このため、候補テストの import 時に次の機械的失敗が発生した。

- attempt:
  `alakazam_staged_20260729/evaluations/v3_psychic_draw_optional_fix1/runner_recheck`
- command:
  `.venv-rl/Scripts/python.exe -B -m unittest -v test_v3_psychic_draw_optional_fix1.py`
- exit code:
  `1`
- first error:
  `ModuleNotFoundError: No module named 'cg'`

この失敗は削除、上書き、成功扱い、または候補不合格扱いをしない。raw stdout、stderr、manifest を保存する。

## 固定する修正

全ての Python テストコマンドに、次の環境変数を明示する。

```text
PYTHONPATH=C:/Users/amuam/project/AI_pokeka_competition/analysis_outputs/cynthia_v9_vs_v11_poffin_role_selection_20260713/seeded_engine
```

既存の `PYTHONPATH` がある場合は、上記 engine directory を先頭へ追加する。

修正後の出力先は次とする。

```text
alakazam_staged_20260729/evaluations/v3_psychic_draw_optional_fix1/runner_recheck_attempt_2
```

テスト対象、Python executable、cwd、引数、候補、fixture、および合格条件は不変である。

## 最終静的監査後の再実行

attempt 2 の後、静的監査で次の二点を検出し、候補だけを狭く強化した。

1. サイコドローを `NO` にした遷移で、同じ手札集合の並べ替えを不変として受理しない。`NO` では手札 serial 列の完全一致を要求する。
2. Psychic-readiness reservation などの継承 transaction が能力 prompt を通過中でも、厳密な危険サイコドローなら外側で `NO` にできるようにする。継承 transaction と親の可変状態は保持する。

最終候補 identity は次のとおり。

- policy closure file count:
  `33`
- policy closure SHA-256:
  `7124EA621B02E58D9143149A33EAA79DB44E1AEF6D206560D17BA7146DF7D590`
- `planner_deck_adaptation_v1.py` SHA-256:
  `4C6F246A256A7C6B327ECFCB81E507E0E1D9E62D8B99D28FAF444BF3AAEA1929`

したがって attempt 2 は中間候補の証拠として保存し、最終合格判定には使用しない。

最終再実行先は次とする。

```text
alakazam_staged_20260729/evaluations/v3_psychic_draw_optional_fix1/runner_recheck_attempt_3
```

attempt 3 は追補済み `PYTHONPATH` を使用し、focused suite の期待件数を `9`、full candidate suite の期待件数を `155` とする。fixture suite は引き続き `3` 件である。

## Fixture 表示名の訂正

attempt 3 後の replay 原本照合で、step `67` と step `148` の旧ファイル名／`semantic_label` に Poffin と記載されていたが、当該公開観測の意味を正確に表していないことを確認した。

観測本体、`observation_sha256`、source step、次 step action、候補実装は変更せず、次の表示名だけを訂正した。

- step `67`:
  `first_alakazam_ko_forced_promotion`
- step `148`:
  `energized_kadabra_with_alakazam_in_hand_main`

この訂正後の fixture suite だけを、次の新規出力先で再実行する。

```text
alakazam_staged_20260729/evaluations/v3_psychic_draw_optional_fix1/fixture_recheck_attempt_4
```

期待件数は `3`、四局面の期待 action は引き続き `[0]`、`[0]`、`[4]`、`[7]` である。候補 closure は変化しない。
