# v4 C3 公開生存範囲・ベンチ0回避 fix5 不変仕様

## 目的

公開情報から、相手が必ず出せる打点と、公開根拠付きで出し得る上限を分けて計算する。

そのうえで、こちらのBenchが0体のままActiveを倒されて盤面全滅する局面だけ、現在の確定利益を壊さない低コストBasic展開を先に行う。

相手が補助カードを持っていると常に仮定しない。逆に、同じ試合ですでに公開され、同型公開デッキでも複数採用が確認されている補助を完全に無視しない。

## 親版

C1とC2の採否後に、rootがexecution amendmentへ固定する。

- C1が採用なら、C1を含むC2 shadow版
- C1が不採用なら、B0を親とするC2 shadow版

不採用の行動変更を継承しない。C2はraw action identityが100%のときだけ継承する。

## 変更範囲

C3で行動を変えてよいのは、通常MAINにおける次の1種類だけである。

```text
Bench 0の盤面で、親がBasicを出さずにATTACKまたはENDへ進む直前、
低コストBasicを1体だけ先に出す。
```

初版では次を変更しない。

- サポート、検索、ドローを親が先に使う判断
- forced Active promotion
- Activeノココッチの `にげあしドロー` 使用・抑制
- ノコッチの `いれかわる` 交代先
- wallの選択

したがってepisode `88843743` では、step24のHildaは保持し、Hilda後のstep27でShayminを先に出す候補とする。step22のRun Away自体はC3では変更しない。

Run Away、forced promotion、Switch Outの行動変更は、C4のshadow到達を経たC5だけで扱う。

## 公開情報境界

使用してよい:

- 現callbackのraw/parsed observation
- 両者のActive、Bench、公開Discard、Lost Zone、Stadium、公開Tool、公開Energy
- 自分のHand
- 現在の合法options
- match開始後に自分で観測した相手公開カードの `(card_id, serial, first_seen_turn)`
- 静的card/attack metadata
- rootが凍結した公開デッキ根拠

使用禁止:

- 相手名、submission ID、episode ID、seed
- 相手の非公開Hand、Deck、Prize
- 山札順
- 後続action、実勝敗、結果label
- リプレイから得た非公開情報

## damage envelope

各公開攻撃役について次を出力する。

```text
damage_floor
damage_cap
damage_formula
modifier_provenance[]
activation_class
hidden_requirements[]
continuity
stochastic_effects[]
unsupported_reasons[]
```

### damage floor

現在公開され、すでに支払われ、現在の攻撃に確定している資源だけで出せる打点。

- 現在のEnergyで支払える技だけ。
- 弱点、抵抗、Tool、Stadium、攻撃本文を対応済みの順序で適用する。
- 使用済みの打点補助は、当該ターン・当該攻撃へ適用中であることをraw logと公開zone deltaの両方から証明する。
- coin、未知の手札、次の手張り、未知の入れ替え札を含めない。

### damage cap

次の相手ターンに成立し得る、対応済み公開経路の上限。

必ず次を併記する。

- Activeのままか、Benchから起動するか
- 必要な通常手張り数
- 必要な進化数
- 必要な交代・逃げ・入れ替え
- hidden inputの有無
- modifierの公開根拠

capは「相手がそのカードを持っている確率」ではなく、公開根拠のある対応済み上限である。capだけで発火する行動には、後述の低コスト条件を追加する。

### activation class

```text
ACTIVE_READY
ACTIVE_ONE_ATTACHMENT_POSSIBLE
BENCH_READY_EXACT_SWITCH
BENCH_ONE_ATTACHMENT_AND_SWITCH_POSSIBLE
NO_SUPPORTED_ACTIVATION
UNKNOWN
```

Bench攻撃役をcapへ入れる場合、必要な未確定Energy・進化・交代を `hidden_requirements` に残す。これをfloorへ入れない。

## continuity

```text
REPEATABLE_READY
RECHARGE_REQUIRED
NO_READY_ATTACK
UNKNOWN
```

- `REPEATABLE_READY`
  - 現在の公開資源のまま、技の使用制限やEnergy discardなしで次の相手ターンも同等攻撃を繰り返せる。
- `RECHARGE_REQUIRED`
  - Energy discard、次ターン使用不可、Active交代など、1個以上の再準備が必要。
- `NO_READY_ATTACK`
  - 対応済みの有打点攻撃を現在は使えない。
- `UNKNOWN`
  - formula、effect、cost、状態を厳密に評価できない。

相手が一度攻撃した後に連続攻撃できない場合、ケーシィ系統を壁で守る価値は下がり得る。C4はこのclassを距離と同時に使う。

## Premium Power Pro `1141`

### floor

`+30` をfloorへ入れるのは次がすべて成立するときだけ。

- 同じ相手ターンにcard `1141` の新しい物理serialが公開された。
- raw logがItemの使用を示す。
- HandからDiscardへの公開moveと一致する。
- 現在の攻撃がFighting Pokémonの技である。
- 効果がまだ当該ターン中である。

provenance:

```text
PUBLIC_COMMITTED
```

### cap

初版で `+30` を数値capへ入れるのは次がすべて成立するときだけ。

- 公開盤面・Discardに、Mega Lucario系統のfamily markerが3種類以上ある。
- markerには `676 Solrock` を含む。
- 同じ試合で `1141` の物理serialが少なくとも1枚、公開済みである。
- 凍結した2つ以上の公開完全一致60枚リストで `1141` が複数採用されている。
- すでに公開されたserialを、未使用の別copyとして二重計上しない。

provenance:

```text
REVEALED_AND_ARCHETYPE_COMMON_POSSIBLE
```

family markers:

```text
673 Makuhita
674 Hariyama
675 Lunatone
676 Solrock
677 Riolu
678 Mega Lucario ex
```

family markerだけで、`1141` が一度も見えていない試合のcapへ+30しない。その場合は
`ARCHETYPE_COMMON_UNCONFIRMED` としてtraceするだけにする。

### 凍結根拠

Source note:

- `docs/meta_deck_scouting_2026-07-03.md`
- SHA-256:
  `6E7BD8669CC2A13CE2190F32F89D11453649ECAEEDC5078498697A5C34D0E053`
- exact list:
  line 9437
- second public list summary:
  lines 11531–11534

Exact public deck A:

- `meta_agents/mega_lucario_aib4_live_84983544_simple/deck.csv`
- SHA-256:
  `2A541D7BF3D9E6B36037123F53F4DFEF6348223F79FD27095DAFC602A5357C19`
- rows:
  60
- `1141`:
  4 copies

Exact public deck B:

- `meta_agents/mega_lucario_fujiborozoukin_live_85033862_simple/deck.csv`
- SHA-256:
  `D6B1417B848C75991BCF1EA5FE96E65A2B8A56FEC27DCD95DDC51005A6C1E90E`
- rows:
  60
- `1141`:
  4 copies

この根拠はcapを許すだけで、所持確率やfloorを与えない。

## 初版の対応済みFighting formula

最低限、次の静的metadataと本文を正確に照合して対応する。

| Pokémon | attack | base | cost | special |
|---|---:|---:|---|---|
| Makuhita `673` | `976` | 10 | F | 通常 |
| Makuhita `673` | `977` | 30 | FF | 通常 |
| Hariyama `674` | `978` | 210 | FFF | 自傷70、相手打点は固定 |
| Lunatone `675` | `979` | 50 | FF | 通常 |
| Solrock `676` | `980` | 70 | F | BenchにLunatone必須、弱点・抵抗無視 |
| Riolu `677` | `981` | 30 | F | 次ターン同技使用不可 |
| Mega Lucario ex `678` | `982` | 130 | F | 打点固定 |
| Mega Lucario ex `678` | `983` | 270 | FF | 次ターン同技使用不可 |

metadataまたは本文が凍結値と一致しない場合は、そのformulaを `UNKNOWN` にする。

対応外の攻撃は、単純固定打点であることを厳密に証明できる場合だけ一般parserで扱う。動的打点、damage counter配置、コピー技、ベンチ狙撃、coin、条件付き倍率は個別対応がない限り `UNKNOWN`。

## match-lifetime公開ledger

相手公開カードを物理serialで一度だけ記録する。

```text
card_id
serial
first_seen_turn
first_seen_zone
last_seen_turn
last_seen_zone
committed_this_turn
```

ゲーム境界で必ずresetする。

reset proofは次の優先順:

1. Kaggle deck callback `select=None/current=None`
2. 前callbackがterminalで、次callbackが非terminal setup
3. turnが初期値へ戻り、action count、public serial集合、初期zone countの全条件が一致

ゲーム境界が曖昧ならledger全体を破棄し、cap modifierを `UNKNOWN` にする。別ゲームの公開cardを持ち越さない。

## bench-0 survival guard

### 共通発火条件

すべて必要。

- 通常MAIN
- 自分のActiveが正確に1体
- 自分のBenchが0体
- 親の最終actionがATTACKまたはEND
- 手札からBenchへ出す合法Basic optionが1個以上
- Activeが相手の `damage_floor` または根拠付き `damage_cap` でKOされ得る
- Basicを出した後も、現在の親attackを再評価できる
- terminal/current exact KO、最終Prize取得、確定勝利を壊さない
- 既存v1/v3/C1 transactionが進行中でない

### floor threat

`damage_floor >= active_hp` の場合、次を満たす最小コストBasicを先に出す。

- 親の確定最終Prizeを失わない。
- 親の確定current KOを非KOへ落とさない。
- attack legalityを失わない。
- 出したBasicが同時に確定ベンチ狙撃で倒され、盤面全滅を防げない状態でない。

### cap-only threat

`damage_floor < active_hp <= damage_cap` の場合は、さらに次をすべて要求する。

- modifier provenanceが `REVEALED_AND_ARCHETYPE_COMMON_POSSIBLE` または同等以上。
- Basic展開による現在attackのoutcome classが変わらない。
- 現在attackの確定KOを失わない。
- 現在のPrize交換を悪化させない。
- Basicに独立した盤面価値がある。
- 対処しない場合の盤面全滅を避けられる。

独立した盤面価値:

- Shaymin `343` の公開・静的に証明できるBench保護
- 唯一または重要な次アタッカーを作るケーシィ `741`
- 盤面にノコッチ系統が0本で、draw engineまたは将来wallを作るノコッチ `305`
- その他、凍結した個別根拠があるBasic

「Basicだから」という理由だけではcap-onlyで出さない。

## Basic候補の比較

候補ごとに次を計算する。

```text
survival_coverage
independent_board_value
next_attacker_distance_delta
current_attack_damage_delta
current_attack_outcome_before
current_attack_outcome_after
prize_liability
lost_hand_scaling_value
bench_snipe_exposure
canonical_option_key
```

優先順位:

1. 盤面全滅を実際に防ぐ。
2. 現在の確定勝利・最終Prize・確定KOを維持する。
3. 次アタッカー距離を改善する。
4. 公開ベンチ保護を持つ。
5. draw engine / future wallを作る。
6. Prize liabilityと失う資源が小さい。
7. canonical option key。

### Powerful Handとの比較

手札からBasicを1枚出すと、将来または現在のPowerful Handは通常20下がる。

- 現在Alakazamが攻撃する場合、出す前後の実打点とKO classを正確に再計算する。
- `KO -> non-KO`、`last-prize KO -> nonterminal` なら発火しない。
- 両方KO、または両方非KOならoutcome classは同じとしてtraceする。
- 現在Kadabraなど手札非依存技なら `current_attack_damage_delta=0`。

Shayminは「-20でも常に出す」ではない。盤面全滅回避が成立し、現在の確定利益を壊さないときに限り出す。

## 親actionとの仲裁

親がHilda、検索、ドローなどを選んだ場合は先に保持する。新しい公開Handを得た次callbackで再判定する。

guardがBasic PLAYへ変更した場合:

1. 親delegate stateを変更前snapshotへ戻す。
2. 物理card serialとsemantic option keyでBasic PLAYを選ぶ。
3. transactionを作り、duplicate callbackを同じsemantic actionへrebindする。
4. 次の新規MAINで、BasicがHandからBenchへ移ったことを検証する。
5. transactionを解除し、その同じcallbackをv1/v3/C1/親の全仲裁へ1回だけ戻す。

任意のENDへ置換しない。callbackごとに証明を再計算する。

## episode `88843743` 固定fixture

- replay:
  `C:/Users/amuam/Downloads/88843743.json`
- SHA-256:
  `B0B8752CA10D9319C667A5482323BF8A780A3038FFDD50AF7DCF588EDA882948`

保存するraw observations:

```text
steps[22][1].observation
steps[23][1].observation
steps[24][1].observation
steps[27][1].observation
```

親semantic:

```text
obs22 -> Active Dudunsparce Run Away Draw
obs23 -> Kadabra forced promotion
obs24 -> Hilda
obs27 -> Super Psy Bolt
```

C3 expected:

```text
obs22 -> parent Run Awayを保持、promotion riskをshadow記録
obs23 -> parent promotionを保持
obs24 -> parent Hildaを保持
obs27 -> PLAY Shaymin 343/serial81を候補として適用
```

obs27のShaymin PLAY後、同じSuper Psy Boltを再仲裁できることをtransaction fixtureで確認する。

根拠:

- Active Kadabraは80 HP、Bench 0。
- Super Psy Boltは手札非依存で、Shayminを出しても当該攻撃打点は変わらない。
- 将来Powerful Handの局所差は-20。
- 同じ試合で `1141` が公開済み。
- 公開family markerはMakuhita、Lunatone、Solrock。
- Solrock Cosmic Beam 70と+30の対応済みcapは100。
- 後続の実KOはfixtureの発火条件や成功labelには使わない。

counterfactual後続は `COUNTERFACTUAL_UNOBSERVED` とする。

## trace

最低限:

```text
schema_version
rule_version = V4_PUBLIC_SURVIVAL_BENCH0_FIX5
parent_closure_sha256
candidate_closure_sha256
raw_parent_action
proposed_action
applied_action
decision_id
damage_rows[]
modifier_ledger[]
active_hp
bench_count
basic_candidates[]
selected_basic
current_attack_before
current_attack_after
guard_class
guard_failure
transaction_stage
outcome_linkage
```

guard class:

```text
FLOOR_BOARDOUT_AVOIDANCE
CAP_LOW_COST_BOARDOUT_AVOIDANCE
SAFE_NO_ACTION
HIGH_COUNTERMEASURE_COST_NO_ACTION
UNSUPPORTED_NO_ACTION
```

## fail-closed

次では親actionを保持する。

- raw/parsed不一致
- serial/owner/zone重複
- attack metadata不一致
- 弱点・抵抗・damage effectがunsupported
- opponent public ledgerのgame境界が曖昧
- modifierの公開serialを一意に追跡できない
- family markerが不足
- Basic PLAY semanticが一意でない
- attack before/afterを再計算できない
- active/bench/hand/option/turn flag不正
- v1/v3/C1 transaction進行中
- exact terminal/current KOを判定不能

unsupported stateによるaction変更は0件でなければならない。

## 必須fixture

1. floorでActive KO、Bench 0、低コストBasicあり
2. cap-only、Shayminあり、現在attack outcome不変
3. cap-only、AlakazamのKOが-20で非KOになるため拒否
4. cap-only、Basicに独立価値がなく拒否
5. Activeがcapを耐えるためsurvival理由では出さない
6. exact terminal KOを保持
7. last-prize KOを保持
8. supporter/drawを先に保持し、次MAINで再判定
9. `1141` PUBLIC_COMMITTEDをfloorへ反映
10. `1141` 一度公開＋family commonをcapへ反映
11. family markerだけ、`1141`未公開なら数値capへ入れない
12. 別ゲームの公開ledgerを持ち越さない
13. duplicate callback / reordered options
14. Basic PLAY完了後に全仲裁へ再投入
15. unknown attack/effectは親保持
16. `88843743` の4局面

## 到達条件

- supported threat state 30件以上
- promotion/removal context 10件以上
- continuity 4classをすべて観測
- 両seat
- 3 opponents以上、非ミラー2以上
- `FLOOR_BOARDOUT_AVOIDANCE` と `CAP_LOW_COST_BOARDOUT_AVOIDANCE` の両方
- unsupported action change 0
- transaction fault、stale abort、metric exception 0

## 採用条件

C3は行動変更候補なので、固定700局で全共通gateを満たす。

- wins `>= ABS_FLOOR`
- overall paired deltaが正
- Historical Silver `>= +3/100`
- Silver両seat非負
- Silverの5 seed block中2個以上が正
- adjacent 6 opponents合計 `>= -2/600`
- 各opponent `>= -2/100`
- 各opponent-seat `>= -2/50`
- one-sided 95% paired lower boundの共通条件
- 到達条件と意図した機構結果
- raw完全性

満たさない場合はC3を不採用とし、C4のshadow解析は直前の最強採用版へ載せる。
