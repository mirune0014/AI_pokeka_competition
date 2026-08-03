# v4 盤面形成・生存・ノココッチ壁パイプライン不変契約

## 目的

本契約は、次の五項目を一度に混ぜず、段階候補として実装・計測・評価するための不変境界である。

1. なかよしポフィンの使用判断と選択枚数
2. `next_attacker_action_distance`
3. 公開根拠に基づく最大打点とベンチ0回避
4. `STRICT_CERTIFIED_WALL`／`PRESERVE_CHANCE_WALL`のシャドー計測
5. シャドーログに基づく、一般化された壁ルールの行動変更

完成版を先に作ってから都合のよい結果だけを説明しない。
各段階で、対象仮説、変更可能な行動、非発火時の親版一致、到達数、対戦強度、事故条件を個別に検証する。

## 凍結した基準

- 基準版:
  `alakazam_staged_20260729/versions/alakazam_newdeck_v3_exact_evolution_ko_fix2`
- policy closure、33 files:
  `DC90205DE06AE3E2E41ADC661577096BB02EE5B42AB9F4366FC1A01154745B47`
- planner:
  `255FD9E1303E8E6DFB286952023A7F086CD233B4E5D5030EDBE06313A40697B7`
- deck:
  `F598F5E578D0440C96DC0492EAECF2E19739B7A23225BE57114A724EF7D0FB94`
- deck構成:
  ケーシィ4、ユンゲラー4、フーディン4、ノコッチ3、ノココッチ2、なかよしポフィン4
- checked engine:
  `analysis_outputs/cynthia_v9_vs_v11_poffin_role_selection_20260713/seeded_engine`
- engine tree:
  `466638706BD5C6915E25D1B3CB9E3D966390FBC263F4ED3153108E29C0194FFF`
- Python:
  `.venv-rl/Scripts/python.exe`

固定リプレイ:

- episode `88844273`:
  `C:/Users/amuam/Downloads/88844273.json`
- SHA-256:
  `9E749F259D90655BE4C17F1795C15D277132C02E0167310394216609B90A7EBF`
- 既存公開fixture:
  `alakazam_staged_20260729/fixtures/episode_88844273_public_observations`
- episode `88843743`:
  `C:/Users/amuam/Downloads/88843743.json`
- SHA-256:
  `B0B8752CA10D9319C667A5482323BF8A780A3038FFDD50AF7DCF588EDA882948`

`88843743`では、自分のノココッチが山札へ戻った後、バトル場はユンゲラー、ベンチは0体になった。
手札にはシェイミが存在したが展開せず、相手のソルロックの70打点に、闘ポケモンの打点を30上げる`Premium Power Pro`（card ID `1141`）が加わり、100打点でユンゲラーが倒され、盤面が全滅した。

## 段階候補

| 段階 | 候補名 | 仮説 | 行動変更 |
|---|---|---|---|
| B0 | `v3_exact_evolution_ko_fix2` | 絶対強度の基準 | なし |
| C1 | `v4_poffin_role_cardinality_fix3` | ポフィンはベンチ最大充填ではなく、攻撃役とドロー役の不足を埋める | あり |
| C2 | `v4_next_attacker_distance_shadow_fix4` | 二値準備率より、証明経路を持つ辞書式距離の方が次攻撃役を正しく表す | なし |
| C3 | `v4_public_survival_bench0_fix5` | 公開根拠別の生存包絡で、低コストなベンチ0敗北を避けられる | ベンチ0回避だけ |
| C4 | `v4_wall_shadow_fix6` | 確定壁と可能性保存壁を分ければ、一般化可能な壁価値を観測できる | なし |
| C5 | `v4_strict_wall_action_fix7` | 実測済みの厳格壁だけなら安全に行動を変えられる | あり |

前段階が棄却された場合、その変更を次段階へ継承しない。
次段階の親版は、直前までに採用された最強版とし、親identityを実装前の追補へ記録する。

## 共通優先順位

次を辞書式に扱う。

1. 今ターンの確定勝利
2. 今ターンの確定KOと正しいサイド交換
3. 今ターンの攻撃へ変換できる安全な`にげあしドロー`
4. 次攻撃役の確定準備
5. 重要または唯一のケーシィ系統の保存
6. 再利用可能なノココッチ壁
7. 攻撃役を確定準備に変える1賞札の犠牲壁
8. 手札補充、盤面形成、その他の親版行動

隠し手札に補助カードやボスが必ずあるとも、絶対にないとも仮定しない。
公開根拠の強さと、対処によって失う価値を分けて比較する。

## C1: なかよしポフィン

### MAINの使用判断

親版が厳密に同定されたなかよしポフィンを既に選んだ場合だけ所有する。
確定KO、終局、進行中transaction、強制prompt、薄い山札の親版拒否を上書きしない。

検索後に有益な対象が0件、合法選択可能数が0件、または山札・ベンチ安全条件を満たさない場合は、ポフィンを使わない親版合法行動へ再順位付けする。
任意0枚の検索をするためだけにポフィンを消費しない。

### 選択枚数

正確なポフィン`TO_BENCH` promptで次を定義する。

- `A`: 場のケーシィ／ユンゲラー／フーディン系統数
- `N`: 場のノコッチ／ノココッチ系統数
- `F`: 空きベンチ数
- 通常上限:
  `min(2, max(0, F - 1))`

原則として将来用のベンチを1枠残す。
ただし`A == 0`で、最後の1枠へケーシィを置く場合だけ例外を認める。

各選択後の投影値を再計算し、次の順で最大2枚を選ぶ。

1. `A < 1`ならケーシィ
2. `N < 1`ならノコッチ
3. `A < 2`ならケーシィ
4. `N < 2`ならノコッチ

投影`N >= 2`でノコッチを追加しない。
「最大2枚選べる」を「必ず2枚選ぶ」と解釈しない。
有益対象がなければ、promptが任意なら0枚、1件なら1枚、独立した役割不足が2件なら2枚を選ぶ。

シェイミは通常のポフィン対象外だが、手札から出す判断では、ベンチ保護と盤面全滅回避を独立価値として扱う。

## C2: `next_attacker_action_distance`

ケーシィ系統の各候補に、次を出力する。

```text
(route_class, turn_delay, main_actions, forced_prompts, witness)
```

`route_class`:

- `CERTIFIED`: 現在の公開状態、自分の手札、厳密な合法option、ターンフラグ、エネルギーだけで決定的に実行できる
- `POSSIBLE`: 名前を特定した検索、ドロー、トップドローなど、未確定の入力を1個以上必要とする
- `IMPOSSIBLE`: 対応している経路では2回の自分ターン以内に攻撃役を作れない
- `UNKNOWN`: 未対応効果、壊れたmetadata、曖昧なoptionなどで評価不能

距離は`turn_delay → main_actions → forced_prompts → canonical witness`の辞書式とする。

- 今攻撃できるバトル場のフーディンは`(CERTIFIED, 0, 0, 0, ...)`
- ベンチの攻撃役を出すための逃げる／入れ替え、進化、手張り、ベンチ配置、にげあしドローは行動数へ含める
- 強制昇格やYES/NO等の子promptは`forced_prompts`へ分離する
- `appearThisTurn`、既に手張りしたか、状態異常、攻撃コスト、逃げエネ、捨てるエネルギー、進化の時間制約を必須入力にする
- 山札・賞札・相手手札の非公開内容を確定経路に使わない

場のケーシィ系統が1本だけなら、再建が`POSSIBLE`でも`UNIQUE`のままである。
「ベンチに既に完成経路がない」ことだけを理由に保存価値を0にしない。

C2は計測専用であり、すべての返却actionを親版と完全一致させる。

## C3: 公開打点・攻撃継続性・ベンチ0

### 打点の三層

各公開攻撃役について次を記録する。

- `damage_floor`: 現在公開され、既に成立・確約している資源だけで確実に出せる打点
- `damage_cap`: 公開根拠から支持できる次攻撃の上限
- `modifier_provenance`: 補正ごとの根拠

補正根拠:

- `PUBLIC_COMMITTED`: 場、使用済み効果、付属カード等により既に確定
- `REVEALED_POSSIBLE`: 同じ対戦で公開された採用カードに、残存可能性がある
- `ARCHETYPE_COMMON_POSSIBLE`: 公開されたポケモン群から同系統構築を同定でき、その系統で高頻度な補助である
- `UNSUPPORTED`: 未対応または曖昧

`Premium Power Pro`の+30は、既に使用され当該攻撃へ確定している場合だけ`damage_floor`へ入れる。
同対戦で確認済み、または公開された闘ポケモン群から支持される場合は、根拠を付けて`damage_cap`へ入れる。
相手名、episode ID、seed、非公開手札、非公開山札順から推定しない。

コイン、麻痺等は確定値にせず、確率効果として別記録する。
未対応の動的打点、コピー攻撃、場効果、道具、エネルギー、弱点抵抗の解決が一つでも必要なら、厳格判定は`UNKNOWN`へ倒す。

### 攻撃継続性

- `REPEATABLE_READY`: 現在の公開資源だけで次の相手ターンも同等攻撃を継続できる
- `RECHARGE_REQUIRED`: エネルギートラッシュ、連続使用不可等により再準備が必要
- `NO_READY_ATTACK`: 公開情報上、次の攻撃役がない
- `UNKNOWN`: 条件を確定できない

### ベンチ0回避

ベンチ0でバトル場が倒れると盤面全滅する局面だけを対象にする。
合法な手札のたねポケモンを出すか、ポフィンで置く経路がある場合、次を比較する。

- ベンチへ出して失うハンドパワー20
- 今ターンの確定KO、取得サイド、終局を失うか
- 最後のベンチ枠を消費するか
- 出すポケモンの将来価値
- `damage_floor`での盤面全滅
- `damage_cap`だけでの盤面全滅と、その根拠

`damage_floor`で盤面全滅する場合は、今ターンの確定勝利を失わない限り回避を優先する。
`REVEALED_POSSIBLE`／`ARCHETYPE_COMMON_POSSIBLE`だけで倒れる場合は、シェイミを出す、不要なたねを1体出す等の低コスト回避だけを許す。
その対処で確定KOや大きなサイド交換を失う場合は、補助カードを必ず持つとは仮定せず親版を維持する。

シェイミは、打点が20下がっても盤面全滅を避ける価値が上回る局面を明示的に正例とする。
相手の支持打点でも倒されず、控え育成等の独立した合理性もない局面では、安全だけを理由に無条件展開しない。

## C4: 壁シャドー

### ケーシィ系統の重要度

- `UNIQUE`: 場の生存ケーシィ系統がその1本だけ
- `IMPORTANT`: 失うと確定距離が1ターン以上悪化、`CERTIFIED`から`POSSIBLE/IMPOSSIBLE`へ悪化、または唯一の成熟・エネルギー付き系統を失う
- `REDUNDANT`: どちらにも該当しない

### 壁分類

`STRICT_CERTIFIED_WALL`:

- 相手は`REPEATABLE_READY`
- `damage_floor`で、保護対象を倒せる
- 保護対象は`UNIQUE`または`IMPORTANT`
- 今使える公開済みボス、ベンチ狙撃等の確定迂回路がない
- 相手が壁を殴らなくても、自分側に成熟、既知の進化・手張り、または確定した壁解除による進展がある
- 壁が相手の最後のサイドにならない
- 盾を使っても再建`IMPOSSIBLE`の単なる延命ではない

`PRESERVE_CHANCE_WALL`:

- KOが`damage_cap`だけで成立する
- 攻撃継続性が不確定
- 補助カード、検索、ドロー等の未確定経路を必要とする
- 迂回路の可能性が残る

後者は重要な仮説だが、C4では行動を変えない。

### ノココッチの三価値

同じ尺度で次を比較する。

1. `RUN_AWAY_ACCELERATION`: 今3枚引くことで、そのターンの確定攻撃・KO、または次攻撃役距離の改善へ変換できる
2. `CERTIFIED_REUSABLE_WALL`: `damage_cap`を耐え、後で安全に`にげあしドロー`できる
3. `CERTIFIED_SACRIFICE_WALL`: 1賞札を渡すが、買った1ターンで保護対象が確定準備になる

優先順位:

1. 今ターンの確定攻撃
2. 同ターン攻撃へ変換する安全な`にげあしドロー`
3. 生存余裕と後続解除を証明した再利用壁
4. 買ったターンで攻撃役が確定完成する1賞札犠牲壁
5. 親版

再利用壁は、生存余裕が大きく、失うエネルギー・道具等が少ないものを選ぶ。
犠牲壁は、賞札価値、進化枚数、付属エネルギー、道具、失う3枚ドロー価値、canonical option keyの順で比較する。

盾を維持して増える相手ターン数を`gust_exposure_turns`として記録する。
隠しボスを決めつけない一方、現在合法な公開迂回路は厳格壁を拒否する。

### 相手が攻撃しない事故

「相手が攻撃しなければ1ターン得をする」は進展証明にしない。
相手が盤面形成を続けた場合でも、次のいずれかを確定する。

- ケーシィ系統の成熟
- 既知手札による次ターンの進化・手張り
- 安全な逃げる／入れ替え
- 安全な`にげあしドロー`と昇格先

完成前にノココッチを山札へ戻し、未完成のケーシィ系統を前へ出す判定は拒否する。

## C5: 行動変更

C4の自然ログで到達条件を満たした`STRICT_CERTIFIED_WALL`だけを行動変更へ昇格する。
`PRESERVE_CHANCE_WALL`は観測専用のまま残す。

許可する行動点:

- KO後等の強制昇格で、ノコッチ系統を壁として選ぶ
- バトル場のノココッチの`にげあしドロー`を抑制する
- ノコッチの攻撃後入れ替えで、危険な未完成ケーシィ系統を前へ出す選択を拒否する

拒否後は、残る合法optionへ親版の順位付けを再適用する。
機械的に`END`を返さない。
各子promptで証明を再計算し、曖昧化したら親版へ戻す。

フーディンミラー、相手名、特定episodeに限定しない。
相手の公開攻撃継続性、打点、保護対象、解除経路から判断する。

## 共通fail-closed

次のいずれかで新規ルールは発火せず、親版actionへ委譲する。

- raw observationとparsed observationの不一致
- option censusの不安定、semantic duplicate
- Pokémon serial欠損・重複
- 未対応の攻撃、効果、道具、エネルギー、スタジアム、状態
- turn flag、benchMax、deckCount、prize枚数の欠損
- 曖昧な強制昇格
- 非一意な対象
- 親版またはv1/v3 transactionが所有中
- 対戦相手名、seed、episode ID、過去行動ラベル、隠し手札を必要とする条件

## 必須trace

各判断へ次を保存する。

- trace schema/rule version
- 親版・候補版closure
- 決定的な`decision_id`
- opponent、seat、seed、turn、contextは監査用だけに保存し、方策条件には使わない
- 親action、提案action、適用actionのsemantic key
- ポフィンの`A/N/F`、役割不足、候補、合法上限、選択枚数
- 各ケーシィ系統の距離、class、witness、重要度、再建class
- 相手の継続性、`damage_floor`、`damage_cap`、補正根拠、確率効果
- 壁HP、サイド・進化・エネルギー・道具コスト、生存、再利用性
- ボス／狙撃迂回、相手拒否時の進展証明、`gust_exposure_turns`
- 拒否理由、仲裁理由

結果行は`decision_id`へ結合し、次を区別する。

- `PARENT_AGREEMENT`
- `CANDIDATE_APPLIED`
- `COUNTERFACTUAL_UNOBSERVED`

壁が殴られた、生存、KO、ボス／狙撃で迂回、相手が攻撃しなかった、にげあしドロー、安全昇格、攻撃役完成・攻撃、サイド差、終局、打切りを追跡する。
シャドーで選ばれなかった反実仮想の結果を、実際に壁を使った結果として数えない。

## 到達条件

- C1:
  ポフィンcontext 30件以上、両seat、3 opponents以上かつ非ミラー2以上。
  提案0/1/2枚を各5件以上、変更・拒否10件以上。
- C2:
  unique state 50件以上、両seat、3 opponents以上かつ非ミラー2以上。
  各route classを5件以上。
  action一致100%、metric exception 0。
- C3:
  対応済みthreat state 30件以上、昇格／盤面除去context 10件以上。
  継続性4分類をすべて観測。
  未対応状態によるaction変更0。
- C4:
  strict 24件以上、chance 40件以上、両seat、3 opponents以上かつ非ミラー2以上。
  strictが2 opponent bucket以上で反復。
  自然な親版一致12件以上、結果追跡が完了した壁8件以上。
- C5:
  行動変更したstrict機序完了8件以上、両seat、非ミラー2 bucket以上。

不足は合格ではなく`INSUFFICIENT_EVIDENCE`とする。
追加seedが必要なら、結果を見る前に未使用seed範囲を別追補へ凍結する。

## 固定評価schedule

7 opponents、両seat、50 seeds、各cell 10 games、各版700 games、`max_steps=1000`。

seed bases:

- `202608500`
- `202608510`
- `202608520`
- `202608530`
- `202608540`

opponents:

- `marnie`
- `cynthia`
- `alakazam_mirror`
- `rocket_mewtwo_spidops_proxy`
- `kangaskhan_crustle`
- `historical_silver`
- `direct_frozen`

既存の正規manifest:

`alakazam_staged_20260729/metrics/formal_frozen_7opp_50seed/suite_manifest.json`

B0を候補結果より先に実行し、rootが700行、schedule、勝敗列、exit、action error、max-stepを再計算する。
その勝数を最初の`ABS_FLOOR`とする。
採用後は、採用済み最強版の勝数まで`ABS_FLOOR`を引き上げる。

## 採用gate

シャドー候補は全raw actionが親版と完全一致しなければ棄却する。

行動変更候補は次をすべて満たす。

- 候補総勝数`>= ABS_FLOOR`
- overall paired deltaが正
- Historical Silverで`+3/100`以上
- Historical Silverの両seatが非負
- Historical Silverの20-game seed block 5個中2個以上が正
- 他6 opponents合計で`-2/600`以上
- 各opponentで`-2/100`以上
- 各opponent-seatで`-2/50`以上
- one-sided 95% paired lower boundがoverall／adjacentで`-1pp`以上
- Historical Silverで同lower boundが`-3pp`以上
- 必須機序到達と、意図した後続結果が成立
- `(opponent, seat, seed)`が各版700 unique、schedule完全一致
- action error、max-step、duplicate control差、非zero exit、欠損結果、raw/parsed不一致が0

小さなoverall改善だけで、seat、対面、機序、完全性の失敗を上書きしない。

## fixture・回帰

必須fixture:

- `88844273`の既存4局面
- `88843743`の、にげあしドロー後の強制昇格と、ベンチ0・手札シェイミのMAIN
- ポフィン0/1/2枚、空き枠0/1/2以上、対象不足、3体目ノコッチ拒否
- ready Active、進化1行動、手張り1行動、入れ替え1行動、2行動、3以上、`POSSIBLE/IMPOSSIBLE/UNKNOWN`
- 70、100、130等の打点境界、`Premium Power Pro`未確認／確認済み／当ターン確定
- 確定KOを壊すベンチ配置の拒否、シェイミによる低コスト盤面全滅回避
- 再利用壁、犠牲壁、相手拒否、ボス迂回、ベンチ狙撃、再充填必要、連続使用不可、状態異常
- duplicate callback、option並べ替え、owner鏡映、stale state、rollback

各候補で、focused、候補full、親full、changed-source compileを実行する。
最終版でKaggle-style last-callable、`select=None`の60枚deck callback、archive再展開hash、BOMなし、top-level Python compileを確認する。

## 提出条件

最終的な提出用archiveは、最後に採用された候補だけから作る。
棄却候補、未評価候補、シャドー到達不足を行動変更へ昇格した候補は提出用にしない。

提出物に含める:

- `.tar.gz`
- package manifest
- source closureと全member SHA-256
- deck 60枚検証
- Kaggle-style entrypoint／deck callback検証
- 最終回帰結果
- 固定scheduleのpaired評価とroot再計算
- シャドー／壁機序監査

本契約は実装・ローカル評価・パッケージ化を許可する。
Kaggleへの外部提出は、この依頼の範囲に含めない。
