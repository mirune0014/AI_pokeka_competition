# v2 `V2_CERTIFIED_H1_CONTINUITY` 固定契約

## 状態

この文書は、`alakazam_newdeck_v2_continuity`の実装前に固定した単一変更仮説である。

v2の実装、単体試験、比較Cは、この契約から変更しない。

この文書はv2の採用を意味しない。

## 入力証拠

- v1 policy closure: `856D8D200BF23F2368C4014351652D49DD89B9DFDEF7C87EF5B5BB39411E5F48`
- 共有raw deck SHA-256: `F598F5E578D0440C96DC0492EAECF2E19739B7A23225BE57114A724EF7D0FB94`
- 共有normalized deck hash: `4414e8995e50c7a00d4b6aa7d9229f63c1dff5261643ec7cd86c4e329113ed69`
- 比較B paired rows SHA-256: `2851E7A87399E0D8EC7ADB3AAC7520C4FAB2BAA83EF7BF7807D6F25A26B3F914`
- v1 game metrics SHA-256: `A88DC83381C42843ED73B16EEFCC7BAB6C54A9C937D9FA81045D9E7AA7EE50D0`
- v1 aggregates SHA-256: `7FF0951D4A79BED75F1427D12ADC8521FE188726810079E9B65D14ABB9637E9E`
- 比較B first-divergence SHA-256: `61F863219364991C2F3E3F432AF8D2857EBCD08798874555DC465D9AB0A182BF`

比較Bはv0の428/700からv1の449/700へ増えた。

比較Bはv1の最終採用ではなく、v2実験へ進む条件付きPASSである。

## 単一仮説

`V2_CERTIFIED_H1_CONTINUITY`

> 非終局の現在Powerful Hand KOを同じターン内で維持しながら、現在攻撃者を除外した次攻撃者を公開情報で予約する。
>
> 現在攻撃者が実際にKOされた後は、同じ証明器で公開情報から確定する最短の同一ターン復旧経路だけを完遂する。

`PREATTACK`と`POST_KO`は別ルールではなく、同じH0/H1不変条件の2 stageである。

## 所有順位

1. raw observationとparsed observationの不一致、optionまたはserialの曖昧性ではv1へ戻す。
2. 親transaction、進行中v1 transaction、親またはv1のduplicate ownerを優先する。
3. 進行中のv2 transactionを処理する。
4. 終局KO、board-out、`V1_BOSS_TERMINAL_PRIZE_KO`を即時実行する。
5. `V1_XEROSIC_H_MINUS_1_CURRENT_KO`のplay、child、verify prefixをv1と同一にする。
6. 非終局H0、またはunsafeなActiveへのAlakazam進化だけを仲裁する。
7. 証明不能ならmutable stateを復元し、v1 action、Reason Code、transaction、fallbackを保存する。

非終局H0を遅らせられるのは同じターン内だけである。

v2 transactionの末尾は、凍結した同じH0 attackでなければならない。

v2はBoss、Xerosic、Enhanced Hammer、Nighttime Mineを新規利用しない。

## H0

H0は、現在ActiveのAlakazamがPowerful Handで現在の相手Activeを倒す、公開情報上の確定経路である。

必要手札枚数は次で求める。

```text
Hreq = ceil(remaining_HP / 20)
```

各substep後の保証手札枚数`Hfinal`が`Hreq`を下回る経路を禁止する。

target、target serial、attack、Hreq、現在攻撃者serialをtransaction開始時に凍結する。

target、公開HP、保護serial、legal attackが変化した場合はabortする。

## H1

H1はH0攻撃者、その進化stack、その付帯Energyを除外する。

H1 readinessは次のいずれかである。

1. 超エネルギーが付いたAlakazam
2. Alakazamと予約済みの超エネルギー
3. Kadabra、予約済みAlakazam、予約済み超エネルギー
4. 今ターン進化可能なAbra、ふしぎなアメ、予約済みAlakazam、予約済み超エネルギー

同じ物理serialをH0、H1、recoveryへ二重計上しない。

Enriching Energy `13`はPsychic readinessへ数えない。

## `PREATTACK`

同じターン内で、次を各最大1回だけ許可する。

- 手札のAbraをベンチへ置く。
- 既存ベンチのAbraまたはKadabraを通常進化する。
- 既存ベンチのAbraをふしぎなアメでAlakazamへ進化する。
- H1系統へ基本超エネルギー`5`またはTelepath Psychic Energy`19`を付ける。
- Telepath Psychic Energyの検索で、deck下限がAbraを保証する場合に限り1体を出す。
- 凍結したH0へ戻り、同じターンにPowerful Handを使う。

選択するsubstepは、H0を維持し、H1 readinessを厳密に上げるものだけとする。

H1が既にreadyなら追加消費をしない。

## unsafe Active Alakazam進化

次をすべて満たす`V1_ALAKAZAM_EXACT_EVOLUTION_RECOVERY`をunsafeとする。

- 非終局である。
- 現時点でH1 certificateがない。
- H0を維持したままH1 readinessを厳密に上げる合法prepが存在する。

unsafeな即時進化は`V2_UNSAFE_ACTIVE_743_BLOCKED`として遮断する。

ベンチが空で合法なBasic展開がある状態と、既存ベンチAbra/Kadabraに合法な進化または超エネルギー装着がある状態を必須fixtureにする。

安全なprepを証明できない場合、推測でENDを選ばずv1へ戻す。

終局、既にH1-ready、またはH0を維持するprepがない場合はv1を変更しない。

## `POST_KO`

凍結したH0 attacker serialが公開状態でKOされ、その後の最初の自分のMAINに入った場合だけ評価する。

次の固定探索だけを許可する。

- Night Stretcher、Lana's Aid、Hildaのうち最大1枚
- `Kadabra → Alakazam`
- 合法な`Abra + Rare Candy → Alakazam`
- 超エネルギー装着を最大1回
- 必要な一意のretreat、payment、promotion
- deck clockを維持するAlakazam AbilityのYES/NO
- 最終actionとしてPowerful Hand

Powerful HandのKO経路がある場合は、非KO経路を選ばない。

Dawn、Poffin、Poké Pad、Sacred Ash、AbraのTeleportation Attackは使わない。

対面名、seed、保存replayの実actionは参照しない。

カード効果、prompt、serialを一意に再束縛できない場合は発火しない。

## 手札差分

公開効果の保証差分は次で固定する。

| action | 保証差分 |
|---|---:|
| Abraを置く | -1 |
| 基本超またはTelepathを付ける | -1 |
| Night Stretcher | 0 |
| Lanaでk枚回収 | k - 1 |
| Hilda | +1 |
| Kadabra進化と2枚ドロー | +1 |
| Alakazam進化と3枚ドロー | +2 |
| Rare Candy、Alakazam、3枚ドロー | +1 |

各段階で`Hfinal >= Hreq`を維持する。

## 資源区間

対象総数は次で固定する。

| card | ID | N |
|---|---:|---:|
| Abra | 741 | 4 |
| Kadabra | 742 | 4 |
| Alakazam | 743 | 4 |
| Rare Candy | deck.csvの該当ID | 3 |
| Basic Psychic Energy | 5 | 2 |
| Telepath Psychic Energy | 19 | 4 |

公開済み枚数`V`、deck枚数`D`、prize枚数`P`、`U=N-V`に対し、次の区間を使う。

```text
deck_lb  = max(0, U - P)
deck_ub  = min(U, D)
prize_lb = max(0, U - D)
prize_ub = min(U, P)
```

実際の山札順、prize内容、将来ドローは参照しない。

Hilda依存経路はAlakazamと必要な超エネルギーのdeck下限を個別に証明する。

異なるカード群のlower boundを、同じ物理枠として二重加算しない。

非終局のdrawまたはsearch後は`deckCount > own_prizes_remaining`を維持する。

相手ターン後はcertificateを再計算し、相手の妨害を予測しない。

## Reason Code

- `V2_H1_PREP_ABRA`
- `V2_H1_PREP_EVOLVE`
- `V2_H1_PREP_PSYCHIC`
- `V2_H1_RECOVER_STRETCHER`
- `V2_H1_RECOVER_LANA`
- `V2_H1_RECOVER_HILDA`
- `V2_H1_PROMOTE_OR_RETREAT`
- `V2_H1_POWERFUL_HAND`
- `V2_TERMINAL_KO_PRECEDENCE`
- `V2_DEFER_V1_XEROSIC`
- `V2_H0_FLOOR_BLOCK`
- `V2_H1_RESOURCE_INTERVAL_UNPROVEN`
- `V2_H1_DECK_CLOCK_BLOCK`
- `V2_UNSAFE_ACTIVE_743_BLOCKED`
- `V2_ABORT_PUBLIC_MUTATION`
- `V2_BASELINE_FALLBACK`

`LAST_V2_CONTINUITY_TRACE`へstage、selected action、H0/H1 serial、Hreq、Hfinal、resource interval、transaction結果を残す。

不可逆action後のabortは合法fallbackであっても評価faultとする。

## 必須単体試験

- H-floor丁度ではprep禁止し、`Hreq + 1`ではprep後も同じH0を実行する。
- 終局KOと終局Bossはv1と同一にする。
- Xerosicのplay、child、verify prefixをv1と同一にする。
- 4件のunsafe Alakazam進化形状で即時進化を遮断し、H0とH1-readyを維持する。
- 公開情報で復旧可能なpost-KO形状と、構造的に復旧不能な形状を分ける。
- ready Alakazam、Kadabra経路、Rare Candy経路、各超エネルギーの有無を検証する。
- Stretcher、Lana、Hildaの正例と負例を検証する。
- Hildaのdeck lower bound境界を検証する。
- option順序変更、serial重複、raw不一致、duplicate callbackを検証する。
- 非発火時にv1 action、trace、親mutable stateを保存する。
- changed fixtureを3回反復し、actionとtraceを一致させる。

## 比較Cへ進む前のhard gate

- v0/v1の33件とv2追加試験がすべて成功する。
- compile errorがない。
- deck.csvがv1とbyte-identicalである。
- v1 source treeを変更していない。
- v2非発火fixtureでv1 action、Reason Code、transaction、fallbackが一致する。
- v2発火fixtureでH0 floor違反、invalid action、不可逆abortが0である。

比較Cのschedule、path、engine、opponents、seat、seed、hash、schemaは、候補closure確定後に別specへ固定する。
