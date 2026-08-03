# v4 C2 次アタッカー距離シャドー fix4 不変仕様

## 目的

二値の `second_attacker_ready` を、フーディン系統の各盤面系統について、完成までの不足部品と必要行動を説明できる距離へ置き換える。

C2 は計測専用である。親方策が返した action の Python 値、型、要素順序を一切変更しない。距離計算に失敗した場合も親 action をそのまま返し、例外だけを trace へ記録する。

この距離は「相手の次の攻撃に耐えるか」を判定しない。生存性は C3 の公開打点、C4 の壁判定で別に評価する。

## 親版

C1 の採否確定後に、root が次のいずれかを execution amendment へ固定する。

- C1 が全採用条件を満たした場合:
  `alakazam_newdeck_v4_poffin_role_cardinality_fix3`
- C1 が不採用または到達不足の場合:
  `alakazam_newdeck_v3_exact_evolution_ko_fix2`

不採用候補の行動変更を C2 に混ぜない。

## 公開情報境界

使用してよい入力は次だけである。

- 現在の raw observation と、それを同一 callback から変換した parsed observation
- 自分の Active、Bench、Hand、Discard、公開 Lost Zone
- 自分の既知の60枚デッキ構成と、現在の山札枚数
- 現在の合法 options
- `appearThisTurn`、`energyAttached`、`retreated`、状態異常、残りサイド、ベンチ上限
- カードの静的 metadata

使用してはいけない入力:

- 相手名、submission ID、episode ID、seed
- 非公開の相手手札
- 自分または相手の山札順
- サイドにあるカードの推定位置
- 後続結果、勝敗、過去リプレイの action

カードが山札かサイドかを公開情報から一意に区別できない経路は `CERTIFIED` にしない。

## 出力

各フーディン系統と、必要な場合は再建用の仮想系統について次を出力する。

```text
(
  route_class,
  turn_delay,
  main_actions,
  forced_prompts,
  witness
)
```

`route_class` の順序:

```text
0 CERTIFIED
1 POSSIBLE
2 IMPOSSIBLE
3 UNKNOWN
```

同じ class 内では次の辞書式順序で小さい経路を優先する。

```text
turn_delay
main_actions
forced_prompts
canonical_witness_key
```

### route class

- `CERTIFIED`
  - 現在の公開盤面、自分の手札、正確な turn flags、エネルギー、静的 metadataだけで構成できる。
  - 山札・サイドから特定カードを引くことを前提にしない。
  - 次の相手ターンに、相手が手札干渉、呼び出し、KOなどの盤面変更をしないという条件は `interruption_exposure` として別記する。
- `POSSIBLE`
  - 必要なカードまたは手段を名前付きで列挙できるが、現在は利用できない。
  - 例: `NEEDS_KADABRA`, `NEEDS_ALAKAZAM`, `NEEDS_PSYCHIC_ENERGY`, `NEEDS_SEARCH_OR_DRAW`, `NEEDS_SAFE_SWITCH`.
- `IMPOSSIBLE`
  - 対応済みの経路テンプレートでは、2回先までの自分ターン内に完成しない。
  - すべての物理コピーが公開領域から失われているなど、公開情報で不可能を証明できる場合も含む。
- `UNKNOWN`
  - raw/parsed不一致、必須flag欠損、未知の状態異常、未知のエネルギー意味論、未知の攻撃コスト、曖昧な option、unsupported effect など。
  - `UNKNOWN` を `POSSIBLE` や `IMPOSSIBLE` へ丸めない。

## 距離の対象

### 盤面系統

Active と Bench の各スタックについて、最下段のケーシィserialを安定した `line_id` とする。

- ケーシィ `741`
- ユンゲラー `742`
- フーディン `743`

進化元のserialが欠損、重複、または順序不正なら、その系統は `UNKNOWN` とする。

### 再建用仮想系統

盤面に系統が0本、または既存系統を失った場合の比較が必要なときだけ `RECONSTRUCT` を出す。

- 手札に正確なケーシィがあり、現在または次の自分ターンに合法的にBenchへ出せるなら、その物理serialを使う。
- 山札検索や通常ドローが必要なら `POSSIBLE` とし、必要カード名を witness に残す。
- 山札にあると断定できないカードを `CERTIFIED` にしない。

### 主距離と補助距離

各系統に次を出す。

- `primary_distance`
  - フーディンが `Powerful Hand` を合法的に使用できる状態まで。
- `fallback_attack_distance`
  - ユンゲラーの対応済みダメージ技を含む、合法的な有打点攻撃まで。

壁の重要度判定に使う正規値 `next_attacker_action_distance` は `primary_distance` とする。ケーシィの交代技だけを「次アタッカー完成」と扱わない。

## 行動数

`main_actions` に数えるもの:

- Basic をBenchへ出す
- 進化する
- 手札からエネルギーを付ける
- 逃げる
- 入れ替えカード・技・特性を開始する
- `にげあしドロー` を開始する

技を実際に宣言する最後の `ATTACK` 自体は、「攻撃可能状態まで」の距離には含めない。

`forced_prompts` に数えるもの:

- 進化先、付け先、交代先などの子prompt
- `にげあしドロー` 後の昇格prompt
- KO後の強制昇格prompt

同じ engine action が MAIN と子prompt の2 callbackを使う場合、`main_actions=1, forced_prompts=1` とする。

## 対応する確定経路テンプレート

初版で `CERTIFIED` にできるのは次だけとする。

1. `ACTIVE_ALAKAZAM_READY`
   - Activeフーディンが対応済み状態異常でなく、Powerful Handの正確なコストを満たす。
   - `(CERTIFIED, 0, 0, 0, ...)`
2. `BENCH_ALAKAZAM_READY_AFTER_EXACT_PROMOTION`
   - Benchフーディンが攻撃コストを満たし、現在のpromptに一意な昇格optionがある。
3. `BENCH_ALAKAZAM_READY_AFTER_RUN_AWAY`
   - Activeノココッチ、正確な `にげあしドロー` option、山札3枚以上、昇格先が一意、後続攻撃が確定。
4. `BENCH_ALAKAZAM_READY_AFTER_RETREAT_OR_SWITCH`
   - 逃げコスト、支払うエネルギー、状態異常、`retreated` flag、交代先を正確に証明できる。
5. `EVOLVE_AND_OR_ATTACH_THIS_TURN`
   - 手札の物理カード、`appearThisTurn=False`、未使用の手張り、正確な付け先optionだけを使う。
6. `ONE_TURN_MATURATION`
   - 現在の手札だけで、次の自分ターンに1回の進化または手張りを行えば完成する。
7. `TWO_TURN_MATURATION`
   - 現在の手札だけで、進化の一ターン一回制約を守って2回先の自分ターンまでに完成する。
8. `PLAY_ABRA_FROM_HAND_AND_MATURE`
   - 空きBench、手札のケーシィ、後続進化札、エネルギーをすべて物理serialで証明する。

検索、ドロー、コイントス、未知のコピー技、相手依存の効果を含む経路は、初版では `CERTIFIED` にしない。

## 時間制約

- 新しく出したケーシィは同じターンに進化できない。
- 今ターン進化したユンゲラーは同じターンにフーディンへ進化できない。
- `appearThisTurn=True` の系統は次の自分ターンまで進化を待つ。
- 手張りは各自分ターン1回だけで、`current.energyAttached=True` なら今ターンの追加手張りを禁止する。
- `retreated=True` なら、別の正確な入れ替え手段がない限り今ターンの逃げを禁止する。
- 麻痺・ねむりなど、逃げ・攻撃を阻害する状態は engine metadata と現在flagの両方が正確な場合だけ計算する。
- エネルギーを捨てる逃げ、攻撃コスト、特殊エネルギーの複数個分換算は既存の厳密helperでのみ計算する。

## 相手ターンをまたぐ経路

`turn_delay > 0` の `CERTIFIED` は、カード不足という意味では確定だが、相手の妨害に対する生存保証ではない。必ず次を併記する。

```text
interruption_exposure:
  NONE_CURRENT_TURN
  ONE_OPPONENT_TURN
  TWO_OPPONENT_TURNS
```

C4で壁価値を判定するときは、距離だけでなく、C3の打点・連続攻撃・公開呼び出し経路を同時に見る。

## UNIQUE / IMPORTANT のための差分

C2では行動を変えないが、各盤面系統について「その系統を除いた再計算」を行う。

- `UNIQUE`
  - 場に存在する有効なフーディン系統が1本だけ。
  - 再建が `POSSIBLE` でも、既存の1本は `UNIQUE` のまま。
- `IMPORTANT`
  - 除去後に best `primary_distance.turn_delay` が1以上悪化する。
  - `CERTIFIED` から `POSSIBLE/IMPOSSIBLE/UNKNOWN` へ悪化する。
  - 唯一のエネルギー付き系統または最も進化した系統を失う。
- `REDUNDANT`
  - 上記のどちらでもない。

`UNKNOWN` を「重要でない」と解釈しない。重要度を `UNKNOWN_IMPORTANCE` としてfail-closedに残す。

## シャドーtrace

`LAST_STAGED_POLICY_TRACE` に最低限次を保存する。

```text
schema_version
rule_version = V4_NEXT_ATTACKER_DISTANCE_SHADOW_FIX4
parent_closure_sha256
candidate_closure_sha256
raw_parent_action
applied_action
action_identity
observation_fingerprint
route_rows[]
best_primary_route
best_fallback_route
line_importance_rows[]
unsupported_reasons[]
metric_exception
```

各 `route_rows[]`:

```text
line_id
location
top_card_id
top_serial
stack_serials
energy_units
primary_distance
fallback_attack_distance
missing_requirements
interruption_exposure
witness_steps
```

`raw_parent_action` と `applied_action` は値・型・順序まで同一でなければならない。

## fail-closed

次のいずれかでは、その行または全体を `UNKNOWN` とする。

- raw/parsedのowner、serial、zone、card IDが不一致
- Activeが1体でない通常MAIN
- 同じserialが複数zoneにある
- 進化スタックが `741 -> 742 -> 743` の部分列でない
- card metadata欠損
- option semanticが一意でない
- turn/attachment/retreat/status flag欠損
- 対応外の特殊エネルギー、コスト変更、攻撃コピー、スタジアム、ポケモンのどうぐ
- ベンチ上限、山札枚数、サイド枚数の不正値
- 既存v1/v3/C1 transactionの途中で、将来経路を一意に再構成できない

計測例外は action 変更理由にしてはいけない。

## 必須fixture

少なくとも次を固定する。

1. Activeフーディン攻撃可能: `(CERTIFIED,0,0,0)`
2. Benchフーディン、強制昇格1prompt
3. Activeノココッチ、Run Away後に一意なフーディン昇格
4. ユンゲラー＋手札フーディン＋十分なエネルギー
5. ユンゲラー＋手札フーディン＋手札エネルギー、今ターン手張り未使用
6. 今ターン出たケーシィ＋手札ユンゲラー・フーディン
7. 手札ケーシィから2ターン再建
8. 必要進化札がなく `POSSIBLE`
9. 公開上すべての必要コピーを失い `IMPOSSIBLE`
10. malformed stack / unknown energy / unknown status の各 `UNKNOWN`
11. 同じ盤面で option順序だけを替えて同じsemantic distance
12. duplicate callbackで同じtraceと同じaction
13. v1/v3/C1 transaction中も親action identity
14. episode `88844273` の4固定局面
15. episode `88843743` のRun Away前後

全fixtureで親 action と候補 action の完全一致を検査する。

## 到達条件

- unique state 50件以上
- 両seat
- 3 opponent以上、うち非ミラー2以上
- `CERTIFIED/POSSIBLE/IMPOSSIBLE/UNKNOWN` を各5件以上
- action identity 100%
- metric exception 0
- duplicate decisionをunique stateとして水増ししない

不足は `INSUFFICIENT_EVIDENCE` とする。

## 検証順

1. focused fixture
2. 候補full regression
3. 親full regression
4. changed-source compile
5. 親とshadow候補の固定700局raw action identity
6. trace到達条件
7. rootによるraw再計算

C2は行動を変えないため、勝率差で採用を主張しない。raw actionが1件でも異なれば不採用とする。
