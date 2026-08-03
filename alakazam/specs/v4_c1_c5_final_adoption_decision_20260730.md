# フーディン v4 C1〜C5 最終採否記録

日付: 2026-07-30

## 結論

今回の提出対象は、採用済みC2を行動親とする
`alakazam_newdeck_v4_next_attacker_distance_shadow_fix4b`とする。

次の行動変更は提出版へ入れない。

- C1: ポフィンの使用判断・選択枚数変更
- C3: 公開最大打点に基づくベンチ0回避
- C5: ノコッチ／ノココッチの一般化壁行動

これらは未実装なのではない。個別候補を実装して固定評価した結果、採用条件を
満たさなかったため、設計・解析器・fixtureを残して行動変更だけを棄却した。

## 段階別の結果

| 段階 | 内容 | 固定評価 | 最終判断 |
|---|---|---:|---|
| C1 | ポフィンの使用判断と選択枚数を分離 | 親452勝、候補443勝。gain 68、loss 77、tie 555 | 行動変更を棄却 |
| C2 | 次アタッカー距離 | 700 callbackで親action同一。固定ルート解析のみ | 解析器を採用 |
| C3 | 公開最大打点・ベンチ0回避 | 親452勝、候補452勝。gain 0、loss 0、tie 700 | 行動変更を棄却、純粋解析をC4へ継承 |
| C4 | `STRICT`／`PRESERVE_CHANCE`シャドー | 900試合、55,514 callback、行動差0 | シャドーとして保持 |
| C5 | 一般化壁ルール | `STRICT=0`、自然一致0、完了結果0 | no-op |

## 実装した設計

### ポフィン

「使用するか」と「何体選ぶか」を別の判断にした。

使用価値には、ベンチ0回避、唯一のケーシィ系統の確保、2本目の攻撃系統、
ノコッチからノココッチへの進化、ベンチ1体によるPowerful Handの20点減少、
手札・検索資源の温存を含めた。

選択枚数は0・1・2を合法候補として比較し、同じ役割の3体目や育成経路のない
Basicを単にベンチへ並べない設計にした。ただし固定700局で9勝悪化したため、
提出行動には採用しない。

### 次アタッカー距離

従来の真偽値を、現在の公開情報から必要な確定部品・行動数へ分解した。

```text
0: 現在攻撃可能
1: 手張り、進化、入れ替えなど確定1行動
2: 確定2部品または2行動
3以上: さらに準備が必要
POSSIBLE: 公開経路はあるがドロー内容などが未確定
IMPOSSIBLE: 公開情報上の経路がない
UNKNOWN: 安全に解釈できない
```

対象系統を盤面から除いた場合も再計算し、その系統が
`UNIQUE`、`IMPORTANT`、`REDUNDANT`、`UNKNOWN_IMPORTANCE`のどれかを記録する。
Run Awayの3枚は手札枚数とPowerful Handの+60だけを確定値とし、未知の3枚を
進化札・検索札として扱わない。

### 公開最大打点とベンチ0回避

相手の現在Activeについて、最低保証打点と公開情報から物理的に可能な上限を
分離した。

Power Proteinは「ありそうだから常に+30」とはしない。同一試合の公開済み
カード、対象デッキでの裏付け、物理4枚上限、使用済み・捨て札・現在使用可能な
serialを区別する。隠れた相手手札は確定情報として使わない。

ベンチ0を回避する候補は、公開上限で現在Activeが倒され得て、追加Basicが
board-outを回避し、現在の確定KO・終局手を失わず、手札1枚と20打点の損失を
許容できる場合に限定した。安全でも、次アタッカー育成など別の合理的価値が
あればベンチ候補を残す設計である。

C3候補は固定700局で一度も勝敗を変えなかったため、行動変更は採用しない。

### ノコッチ／ノココッチの壁価値

ミラー専用にせず、相手の完成攻撃役、連続攻撃可否、こちらの保護対象、
解除後の安全性から判定する。

比較する役割は次の四つである。

```text
RUN_AWAY_ACCELERATION
CERTIFIED_REUSABLE_WALL
CERTIFIED_SACRIFICE_WALL
NO_WALL_OR_UNKNOWN
```

主な安全条件:

- 守るケーシィ系統が`UNIQUE`または`IMPORTANT`
- 相手が公開情報上の反復可能な攻撃で、その系統を確定KOできる
- 壁にしている間に進化・手張り・確定検索などの具体的進展がある
- 相手が攻撃を拒否しても期限内に距離が短くなる
- Run AwayまたはTrading Places後の昇格先が再び即KOされない
- 公開済みのBoss、ベンチ狙撃、最終Prize献上を確認する
- 相手が再充電を必要とするなら、ケーシィを捨てる方がよい可能性も残す
- 壁へ入った時点の期限を固定し、後から延長しない

ノココッチについては「壁として1ターンを買う価値」と「山札へ戻って3枚引く
価値」を同じ局面から別候補として比較する。3枚の中身による進化は推定せず、
確定するのは手札3枚とPowerful Handの60点増加だけである。

`PRESERVE_CHANCE`は保護価値がないという意味ではない。必要な証明の一部が
未確定という意味であり、初版では行動変更へ使わない。

## C4正式計測

### 固定ペア評価

- 7相手
- 5 seed base
- 両seat
- 各セル10試合
- 合計700行

結果:

```text
baseline wins = 452
candidate wins = 452
gain = 0
loss = 0
tie = 700
action errors = 0
max-step hits = 0
```

ルート独立監査:
`evaluations/v4_c4_wall_shadow_fix6_combined_attempt2/root_independent_paired_audit.json`

### シャドー到達計測

- 9相手
- 90 block
- 900試合
- 55,514 callback

改訂収集結果:

```text
integrity = PASS
STRICT unique states = 0
PRESERVE_CHANCE unique states = 246
natural parent agreements = 0
trace-complete outcomes = 0
candidate applied = 0
action identity faults = 0
metric exceptions = 0
overall = INSUFFICIENT_EVIDENCE
```

保護対象を一意に決められない983 callbackは、壁の有効性を示す証拠ではない。
このうちRun Awayの`PRESERVE_CHANCE`があっても到達数へ加えず、負の記録として
除外した。重複診断1014行は生ログに残し、衝突は0件だった。

ルート独立監査:
`metrics/formal_v4_c4_wall_shadow_fix6_union_audit_attempt2/root_independent_metric_audit.json`

### 独立数値監査

Sol-Ultraによる独立監査は、700行と900試合のraw sidecarを再走査し、
root集計と同じ値を再現した。

```text
status = PASS_WITH_INSUFFICIENT_EVIDENCE
paired delta = 0.000%
conservative paired 95% interval = -0.427% ～ +0.427%
```

監査中、事前に転送された2つのハッシュが古いことを検出した。rawを修復せず、
実ファイル、raw projection、root再計算が一致する値を監査記録へ明記した。
paired CSVの`50AC17...B851`は別artifactであり、変更されていない。

独立監査:

- `analysis_outputs/v4_c4_wall_shadow_fix6_formal_audit_20260730/AUDIT_REPORT.md`
- `analysis_outputs/v4_c4_wall_shadow_fix6_formal_audit_20260730/audit_results.json`

## 収集器の追補

元の凍結収集器は、保護対象なしの棄却ログにも`protected_line`辞書を要求して
いたため、初回集計を`FAIL`にした。元ファイルと失敗結果は変更せず保存した。

別バージョンの収集器は、全必須キー、raw binding、fingerprint、closure、
action identityを通常どおり検証した後、厳密な
`NO_LIVE_PROTECTED_LINE`形だけを証拠から減算する。

- A+C再検証: 705除外、重複診断732、残存fault 0
- 全900試合: 983除外、重複診断1014、残存fault 0

追補:
`specs/v4_c4_wall_shadow_fix6_collector_erratum_20260730.md`

## 提出対象

提出用アーカイブ:

`submissions/alakazam_newdeck_v4_c2_safe_final_20260730/submission_alakazam_newdeck_v4_c2_safe_final_20260730.tar.gz`

SHA-256:

`9F4DE9078E522501F99AEA97FC1D8319C3C81C93869EA1D2D5E2CEE2239B5E1A`

採用source closure:

`29084BC13CB74236ABE557B57A9E633A8F9E88FA83FF22D131C835293E987157`

このアーカイブは、未承認のC1・C3・C5行動を含まない。C4は行動同一だが、
Kaggle上で証拠ログを保存できない解析負荷を載せる合理性がないため、提出版は
C2を使用する。

検証:

- 60枚、deck hash
  `F598F5E578D0440C96DC0492EAECF2E19739B7A23225BE57114A724EF7D0FB94`
- C2回帰 192/192
- C4開発回帰 270/270
- Kaggle形式の最終callableと初期deck callbackを検証
- 展開済みアーカイブを両seatで実行し、action error 0、max-step hit 0

詳細:
`submissions/alakazam_newdeck_v4_c2_safe_final_20260730/submission_validation_20260730.md`

この作業ではKaggleへのアップロード・提出を行っていない。

## 最終戦略監査

独立した戦略監査も、次の採否を支持した。

- C1ポフィン行動は棄却
- C3ベンチ0回避行動は棄却し、pure analyzerだけを保持
- C4は開発用shadowとして保持
- C5一般化壁行動は`NO-OP`
- 提出版はC2 action path

C4の完全tieは行動同一性を証明するだけで、強化を証明しない。
特にRocket proxyは38/100、同seat 1は17/50であり、弱い絶対floorが残る。

危険な反例は、相手の攻撃拒否中に保護対象が進まないこと、再充電型相手への
不要な壁、Run Away後の昇格先の即KO、最終Prize献上、公開gust／snipe、
Energy・進化札・検索札・draw engineを壁のために失うこと、である。

最終戦略判断:
`reports/v4_c5_final_strategy_judgment_20260730.md`

## 次に壁行動を昇格させる条件

最低でも、凍結済み条件で次を満たす追加ログが必要である。

- `STRICT` 24 unique states
- 2以上の相手bucketで`STRICT`
- natural parent agreement 12件
- trace-complete observed outcome 8件
- 両seat、3相手以上、非mirror2相手以上
- 同一機構が非mirror 2 bucketで反復し、各bucketでcomplete agreement 2件以上
- refusal、Boss／狙撃、解除、後続未完成の重大反例0
- action、raw binding、fingerprint、closure、error、max-stepのfault 0

条件を満たした場合でも、Run Away、再利用壁、犠牲壁のうち一つだけを独立候補
として実装し、同一seed・両seatで再評価する。overallの正のdelta、
Historical Silverの改善、隣接対面の安全、bucket／cell floor、意図した機構で
勝敗が変わったことをすべて再確認してから採用する。
