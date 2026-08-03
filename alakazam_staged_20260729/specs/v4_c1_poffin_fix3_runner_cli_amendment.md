# v4 C1 ポフィン fix3 runner CLI 修正追補

## 理由

固定paired仕様のopponent一覧はnameとpathを別行で示していたが、checked runnerの `--opponent` 引数が要求するliteral形式を明記していなかった。

Runner AとRunner Bは、最初のpanelでpathだけを渡したため、checked runnerの引数検証でexit code 2となった。battle processは開始されず、raw対戦行は0件である。

この追補はCLI表記だけを修正する。方策、engine、opponent、seed、games、seat、max steps、採用条件は変更しない。

## checked runner literal

`--opponent` は必ず次の形式で渡す。

```text
--opponent NAME=PATH
```

固定literal:

```text
marnie=meta_agents/marnie_sota_live_85033057_simple
cynthia=meta_agents/cynthia_garchomp_nasuo445_v80_legal_complete_role_cycle
alakazam_mirror=meta_agents/alakazam_oselcoun_live_85035844_simple
rocket_mewtwo_spidops_proxy=meta_agents/rocket_mewtwo_spidops_kashiwashira_20260703_simple
kangaskhan_crustle=meta_agents/kangaskhan_crustle_mpgaming_v13_backupkang_two_growline
historical_silver=analysis_outputs/reference_agents/historical_silver_archaludon_54495224
direct_frozen=alakazam_staged_20260729/eval_adapters/alakazam_800_frozen
```

## 無効attempt

次の2 directoryは、CLI検証失敗の証跡として保持し、first-valid attemptに数えない。

```text
202608500_marnie/attempt_1
202608510_direct_frozen/attempt_1
```

両方ともbattle raw outputは0件である。

この2 panelだけ、修正literalを使って `attempt_2` へ実行する。他33 panelは予定どおり `attempt_1` を使う。

## 不変条件

- 失敗directoryを削除・上書きしない。
- exit 2のattemptを結果行へ混ぜない。
- combine時は各panelの最初の完全valid attemptだけを選ぶ。
- corrected command以外のscheduleを変更しない。
- checked runner以外のcustom runnerやcustom aggregateを作らない。
