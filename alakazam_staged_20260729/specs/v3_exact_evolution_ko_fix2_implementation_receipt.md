# v3 進化後確定KO優先 fix2 実装記録

## 結果

合意した実装順序の第3項「進化後の確定KOを優先」を、サイコドロー任意化 fix1 の上へ独立ルールとして実装した。

新しいルールは次である。

`V3_ALAKAZAM_EXACT_EVOLUTION_KO_PRIORITY`

episode `88844273` の step 148 では、親版の `[7]` から、手札のフーディンをバトル場のユンゲラーへ進化させる `[0]` に変わる。

実際にchecked engineで確認した連鎖は次のとおりである。

1. フーディンへ進化 `[0]`
2. サイコドロー `YES [0]`
3. 手札14枚、山札4枚
4. ハンドパワー `[13]`
5. 280ダメージカウンタ相当で現在HP180の相手をKO
6. 2枚サイド取得 `[0, 1]`

## 成果物

- 候補:
  `alakazam_staged_20260729/versions/alakazam_newdeck_v3_exact_evolution_ko_fix2`
- production変更:
  `planner_deck_adaptation_v1.py`
- 新規重点テスト:
  `test_v3_exact_evolution_ko_fix2.py`
- 不変仕様:
  `specs/v3_exact_evolution_ko_fix2_immutable_spec.md`
- 実行仕様:
  `specs/v3_exact_evolution_ko_fix2_execution_spec.md`
- 実行追補:
  `specs/v3_exact_evolution_ko_fix2_execution_amendment.md`
- 最終raw evidence:
  `evaluations/v3_exact_evolution_ko_fix2/runner_recheck_attempt_3`

## 実装内容

- 既存の`_evolve_rows`と既存active-Alakazam候補は変更せず、先に評価する。
- 新規候補はMAINの全EVOLVE optionを公開状態から厳密に解決する。
- `手札フーディン → 自分のバトル場slot 0のユンゲラー`だけを対象候補として数え、ちょうど1件を要求する。
- sourceまたはtarget serialを共有する別候補、semantic duplicate、malformed optionは拒否する。
- sourceとtargetがともに異なる完全解決済みのノココッチ進化などは許可する。
- 進化前に、成熟状態、ケーシィ進化系統、ツール、超エネルギー支払い、状態異常、公開効果、標的、サイド価値、相手ベンチを証明する。
- `D >= 4`はサイコドローYES、予測手札`H+2`、山札`D-3`。
- `D = 1..3`はNO、予測手札`H-1`、山札`D`のまま。YESを仮定した打点では発火しない。
- `D = 0`は、NO後打点でKOでき、取得サイドだけで勝利する場合に限る。
- 発火後は、予定したYES/NOと実際の選択、手札・山札delta、進化後fingerprint、攻撃、ダメージログ、対象stackのdiscard、サイドpromptを厳密に照合する。
- 現在の確定KO、終局Boss、Mine、既存active進化等の優先順位は維持する。

## 最終identity

- 親 policy closure、33 files:
  `7124EA621B02E58D9143149A33EAA79DB44E1AEF6D206560D17BA7146DF7D590`
- 親 planner:
  `4C6F246A256A7C6B327ECFCB81E507E0E1D9E62D8B99D28FAF444BF3AAEA1929`
- 候補 policy closure、33 files:
  `DC90205DE06AE3E2E41ADC661577096BB02EE5B42AB9F4366FC1A01154745B47`
- 候補 planner:
  `255FD9E1303E8E6DFB286952023A7F086CD233B4E5D5030EDBE06313A40697B7`
- focused test:
  `A8ABFF15D89658FF340484369BEBAD07BDB8D86D9481D1BE78D8383D5A5EAB7F`
- deck:
  `F598F5E578D0440C96DC0492EAECF2E19739B7A23225BE57114A724EF7D0FB94`
- replay:
  `9E749F259D90655BE4C17F1795C15D277132C02E0167310394216609B90A7EBF`
- immutable spec:
  `64B0E5459816954E81CC55853BABE68FD2D23C6413AB6D01D64F88E6EBFF47E9`
- final execution manifest:
  `6F6904C133D9E01C779EF3DAEC5946F30CC558E9215CDF384FC642EB00803B38`

親と候補の非pyc差分は、production plannerの変更と新規focused testだけである。`deck.csv`、`_cumulative_parent.py`、`main.py`、`runtime/main.py`は不変である。

## 検証

- focused candidate:
  `11/11 OK`
- candidate full:
  `166/166 OK`
- parent full:
  `155/155 OK`
- changed-source compile:
  `2/2 OK`
- root独立確認:
  - step 148の親 actionは`[7]`
  - step 148の候補 actionは`[0]`
  - ruleは`V3_ALAKAZAM_EXACT_EVOLUTION_KO_PRIORITY`
  - planned branchはYES、手札14、山札4、取得サイド2
  - checked-engine通常連鎖とD0終局連鎖の2件は`2/2 OK`

fixed fixtureの候補action:

| step | 親 | 候補 |
|---:|---:|---:|
| 67 | `[0]` | `[0]` |
| 98 | `[0]` | `[0]` |
| 121 | `[4]` | `[4]` |
| 148 | `[7]` | `[0]` |

重点テストは、山札`4/3/2/1/0`、同値KOと1不足、YES仮定だけならKOになる低山札、候補0/2件、duplicate、shared serial、malformed option、option並べ替え、owner鏡映、進化系統、成熟、ツール、エネルギー、状態、公開効果、サイド価値、相手ベンチ、現在KO、Boss、Mine、duplicate callbackを含む。

## runnerの機械的失敗

- attempt 1:
  PowerShell wrapperがPython起動前に失敗。空のstdout/stderrだけを保存した。
- attempt 2:
  redirect先を相対パスとして解釈し、Python起動前に`DirectoryNotFoundException`。誤作成された空directory treeは、ファイル0件かつ候補配下であることを確認して削除した。
- attempt 3:
  解決済み絶対パスと`ProcessStartInfo`を使用し、全テストとcompileがexit code 0。

attempt 1/2を成功証拠には使っていない。

## 残る範囲

公開効果の判定は意図的にfail-closedである。未認識の場の特性、付属カード効果、使用履歴を公開情報から確定できないLegacy Energy等がある場合、このルールは発火しない。

D0終局連鎖はchecked-engine由来の公開transaction状態を使った固定検証であり、自然対戦での到達例はまだ観測していない。

今回の完了範囲は実装と機構・回帰検証である。対戦パネルによる勝率評価、最終採用、Kaggle提出は実施していない。
