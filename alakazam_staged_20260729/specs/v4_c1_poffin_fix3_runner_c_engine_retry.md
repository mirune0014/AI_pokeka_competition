# v4 C1 ポフィン fix3 Runner C engine path retry

Runner Cの最初のpanelは、固定仕様にあるengine pathではなく、存在しない
`alakazam_staged_20260729/seeded_engine` を渡したため、最初のbaseline subprocessがexit 1となった。

対象:

```text
202608520_direct_frozen/attempt_1
```

検証結果:

- `report.valid=false`
- paired rows: 0
- battle summary rows: 0
- failing subprocess: first baseline A
- candidate process: 未開始

このinvalid attemptを保持し、first-valid resultに数えない。

retryは `attempt_2` へ、次の固定engine pathをliteralで渡す。

```text
analysis_outputs/cynthia_v9_vs_v11_poffin_role_selection_20260713/seeded_engine
```

他のRunner C割当10panelは予定どおり `attempt_1` とする。方策、opponent、seed、games、seat、max stepsは変更しない。
