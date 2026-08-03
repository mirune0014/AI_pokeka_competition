# v3 進化後確定KO優先 fix2 不変仕様

## 目的

ユーザーと合意した実装順序の第3項だけを、サイコドロー任意化 fix1 の上へ追加する。

対象は、自分のバトル場に攻撃可能なユンゲラーがいて、手札のフーディンへ進化し、サイコドローの YES/NO 選択まで含めると、そのターンの「ハンドパワー」で相手バトルポケモンを確定KOできる局面である。

ポフィン、ノコッチの盾、次アタッカー距離、公開最大打点、ベンチ0回避は変更しない。

## 凍結入力

- 親実装:
  `alakazam_staged_20260729/versions/alakazam_newdeck_v3_psychic_draw_optional_fix1`
- 親 source closure SHA-256:
  `7124EA621B02E58D9143149A33EAA79DB44E1AEF6D206560D17BA7146DF7D590`
- 親 planner SHA-256:
  `4C6F246A256A7C6B327ECFCB81E507E0E1D9E62D8B99D28FAF444BF3AAEA1929`
- deck SHA-256:
  `F598F5E578D0440C96DC0492EAECF2E19739B7A23225BE57114A724EF7D0FB94`
- replay:
  `C:/Users/amuam/Downloads/88844273.json`
- replay SHA-256:
  `9E749F259D90655BE4C17F1795C15D277132C02E0167310394216609B90A7EBF`
- 対象 agent index:
  `1`
- checked engine:
  `analysis_outputs/cynthia_v9_vs_v11_poffin_role_selection_20260713/seeded_engine`
- engine tree SHA-256:
  `466638706BD5C6915E25D1B3CB9E3D966390FBC263F4ED3153108E29C0194FFF`
- Python:
  `C:/Users/amuam/project/AI_pokeka_competition/.venv-rl/Scripts/python.exe`

親実装と既存fixtureは一切変更しない。

## 出力

- 候補:
  `alakazam_staged_20260729/versions/alakazam_newdeck_v3_exact_evolution_ko_fix2`
- 新規候補テスト:
  候補ディレクトリ内
- 検証証拠:
  `alakazam_staged_20260729/evaluations/v3_exact_evolution_ko_fix2`
- 実装記録:
  `alakazam_staged_20260729/specs/v3_exact_evolution_ko_fix2_implementation_receipt.md`

## 対象局面と期待行動

episode `88844273` の公開観測fixtureを使用する。

| source step | 意味 | 親 action | 候補 action |
|---:|---|---|---|
| 67 | 最初のフーディンKO後の強制昇格 | `[0]` | `[0]` |
| 98 | ユンゲラーを含む後続選択の強制昇格 | `[0]` | `[0]` |
| 121 | 後半の強制昇格 | `[4]` | `[4]` |
| 148 | エネルギー付きユンゲラーと手札フーディンがある MAIN | `[7]` | `[0]` |

step 148 の公開事実は次のとおりである。

- 自分のバトル場は、今ターン出たポケモンではないユンゲラー `742/67`。
- 進化元にケーシィがあり、ツールはなく、超エネルギー1個を持つ。
- 手札 index 0 はフーディン `743/73`。
- 自分の手札枚数は12枚、山札は7枚。
- 相手バトル場 `140/12` の現在HPは180、最大HPは210。
- option 0 はフーディンへの対象進化である。
- options 7/8 は、別serialのノコッチを別serialのノココッチへ進化させる無関係な候補である。

候補は option 0 を選び、その後のサイコドローで YES を選ぶ。進化で手札11枚、3枚引いて14枚、ハンドパワー280ダメージ相当で相手の現在HP180をKOする。

## 新規ルール

新しい識別可能なルール名を追加する。

`V3_ALAKAZAM_EXACT_EVOLUTION_KO_PRIORITY`

既存のルール名、既存の通常進化候補生成器、親方策の意味を変更しない。新規ルールは、既存の active-Alakazam 候補が成立しなかった場合に限り、同じ優先順位位置で評価する。

## 進化候補の一意性

MAIN のすべての EVOLVE option を公開状態から厳密に解決する。未知、欠損、範囲外、または安定したoption keyを作れない EVOLVE optionが一つでもあれば発火しない。

対象候補とは、次をすべて満たす EVOLVE optionである。

- source は自分の手札のフーディン。
- target は自分の唯一のバトル場 slot 0 のユンゲラー。
- source/target の card ID、serial、owner、area、index を一意に解決できる。

対象候補はちょうど一つでなければならない。同じフーディンserialまたは同じユンゲラーserialを共有する別のEVOLVE optionがあれば発火しない。

sourceとtargetの両serialが対象候補と異なり、公開状態から完全に解決できる無関係な進化候補は許可する。これにより、step 148 のノココッチ進化 options 7/8 は対象進化の一意性を壊さない。

## 発火前の必須証明

親実装が既に要求する active-Kadabra 進化KOの証明を緩めない。

- exact MAIN envelope と公開snapshot。
- 成熟したバトル場のユンゲラー、完全なケーシィ進化系統、各serialの一意性。
- ユンゲラーにツールがない。
- 公開されたエネルギー単位で超エネルギーの攻撃コストを支払える。
- フーディン、サイコドロー、ハンドパワーのcard/skill metadataが既知かつ一致する。
- フーディンはテラスタルではない。
- 攻撃不能状態、攻撃アクセス、コスト、ダメカン配置妨害、KO防止、相手の味方を含む公開特性・公開効果を厳密に確認する。
- 相手バトルポケモン、付属カード、現在HP、サイド価値を公開情報から一意に解決する。
- 相手を倒した場合の取得サイド `P` は1以上であり、エネルギー・ツール等の公開サイド補正も確定している。
- 対戦相手のベンチが1体以上いる。ベンチ0によるゲーム終了は、この候補の終局証明には使わない。
- opponent ID、episode ID、replay stepによる特例を作らない。

いずれかの情報が未知、曖昧、または不整合なら、親方策へ完全にフォールバックする。

## サイコドロー分岐と確定打点

進化前の手札枚数を `H`、山札枚数を `D` とする。

- `D >= 4`
  - サイコドローは `YES`。
  - 進化後かつ能力解決後の手札は `H + 2`。
  - 山札は `D - 3`。
  - ハンドパワーは `20 * (H + 2)`。
- `1 <= D <= 3`
  - サイコドローは `NO`。
  - 進化後の手札は `H - 1`。
  - 山札は `D` のまま。
  - ハンドパワーは `20 * (H - 1)`。
  - `YES`を仮定した打点ではなく、必ずこのNO後打点でKOを証明する。
- `D == 0`
  - サイコドローは `NO`。
  - NO後打点でKOでき、かつ `P >= 自分の残りサイド枚数` の公開サイド終局である場合だけ許可する。
  - それ以外は発火しない。

予測打点が相手の現在HPと同値ならKO、1不足なら非発火とする。

## 優先順位

既存の所有中transaction、duplicate callback処理、removed-card gate、サイコドローprompt所有を最優先で維持する。

- 親が現在のバトルポケモンで確定終局KOを選ぶ場合、その行動を変えない。
- 親が現在のバトルポケモンで非終局KOを選ぶ場合に許可されている既存の例外だけを維持する。
- 現在KOがない分岐の `終局ボス → マイン → active進化 → 妨害` の順序を維持する。
- 新規ルールは既存active進化候補と同じ場所に置き、既存候補を先に評価する。
- ボス、マイン、ready-bench、ゼイユ、ラナ、ハンマー等の既存発火条件を変更しない。

## transaction検証

新規ルールは、既存active進化transactionと同等以上の厳密さで次を検証する。

1. フーディン進化による手札・バトル場・進化系統の正確なdeltaとserial rebound。
2. exact ACTIVATE prompt、フーディンのcontext card、YES/NO optionの意味。
3. 予定したYES/NOに対応する正確な手札・山札delta。
4. 同じ攻撃役と標的、無関係な盤面の不変性、ハンドパワーoptionの一意性。
5. prompt解決後の実手札枚数で再計算した確定KO。
6. exact ATTACK log、`20 * post_hand` のダメージカウンタ変化、対象stack全体のdiscard移動。
7. exact取得サイドpromptとサイド価値、KO解決を確認してからtransactionを完了する。

途中で予測と異なる状態へ進んだ場合は、既存のfail-closed規則を使う。不可逆な行動後に別ルールへ安易に切り替えない。

## 必須テスト

### replay fixture

- step 148: 親 `[7]`、候補 `[0]`。
- step 67/98/121: 親と候補が完全一致。
- option順を入れ替えても、同じsource/target serialの進化を選ぶ。
- player/ownerを鏡映した局面でも、同じ意味の進化を選ぶ。

### 境界・非発火

- `D=4`: YES後の予測打点で境界KO。
- `D=3/2/1`: NO後の予測打点で境界KO。
- `D=3`: YESを仮定すればKOだがNO後は届かない局面で非発火。
- `D=0`: 公開サイド終局なら発火、非終局なら非発火。
- 予測打点よりHPが1高い場合は非発火。
- 対象進化が0件または2件、semantic duplicate、source/target serial共有で非発火。
- malformedな無関係EVOLVE optionが一つでもあれば非発火。
- 未成熟、誤った進化系統、ツール付き、超エネルギー不足、未知の状態・効果・サイド価値で非発火。
- 相手ベンチ0で非発火。
- option keyを安定して解決できない場合は非発火。
- 現在の確定KOおよび既存Boss/Mine優先fixtureは親と一致。

### checked engine

episode step 148 の公開観測を最初のpolicy callbackへ渡し、hidden stateはengine初期化だけに使う。以後policyへ渡す観測では、両者のサイド中身を枚数だけ残して `None` へmaskし、相手手札・探索中情報等の非公開情報を渡さない。

期待連鎖は次のとおりである。

1. MAINでoption 0のフーディン進化。
2. ACTIVATEでサイコドローYES。
3. 手札14、山札4のMAINでハンドパワー。
4. 280ダメージカウンタ相当で現在HP180の相手をKO。
5. exact 2枚サイド取得promptを確認。
6. duplicate callbackでも同一行動を返し、fault/abortを出さずtransactionを完了。

### 回帰

- 候補ディレクトリの全unittestが成功する。
- 変更したPython sourceがcompileできる。
- action error、transaction fault、irreversible abortが0。
- 親のsource closure、planner、deck、fixture hashが不変。

## 合格条件

必須テストがすべて成功し、step 148だけが意図した進化優先へ変わり、他の固定3局面と既存回帰が不変であること。

この作業はルールの実装・機構検証であり、勝率改善、最終採用、Kaggle提出を意味しない。対戦パネルによる採用評価は別工程とする。
