# フーディン準備・壁価値の統合設計

日付: 2026-07-30

## 目的

この設計は、フーディンの打点だけを最大化するのではなく、次の価値を同時に
比較するためのものである。

```text
現在の攻撃価値
次アタッカーの準備価値
ベンチ0による即敗北の回避価値
ノコッチ／ノココッチの壁価値
にげあしドローによる手札・打点加速価値
相手へ与えるPrize・盤面形成・Boss到達時間
```

ミラーや特定episodeへ固定せず、公開盤面、合法手、物理card serial、
SUPPORTEDなカード本文だけで判定する。

## 1. ポフィン判断と選択枚数

「ポフィンを使うか」と「何体選ぶか」を別の判断にする。

使用判断では、現在の手札枚数だけでなく次を比較する。

- ベンチ0回避
- UNIQUEなケーシィ系統の確保
- 2本目のケーシィ系統による攻撃継続
- ノコッチからノココッチへ進化するdraw engine
- ベンチ枠を使うことによるPowerful Handの手札減少
- 既に十分な盤面があるときの過剰展開

選択枚数は検索上限まで自動的に選ばない。

```text
0: 使用しない
1: 必須の1体だけ
2以上: 独立した役割が各対象にある場合だけ
```

同じ役割の3体目のノコッチ、育成経路のないケーシィ、ベンチ枠を塞ぐだけの
Basicは拒否する。

ただし、この候補は単独比較で数値ゲートを満たさなかった場合、後続へ行動を
継承しない。設計上有望であることと、現在の実装を採用することを分ける。

## 2. 次アタッカー距離

従来の `second_attacker_ready` という真偽値を、段階的な距離へ置き換える。

```text
0: 現在攻撃可能
1: 手張り、進化、入れ替え等の確定1段階で攻撃可能
2: 確定2段階で攻撃可能
3以上: さらに準備が必要
POSSIBLE: 公開情報上は経路があるが、引くカード等が未確定
IMPOSSIBLE: 公開情報から有効経路がない
UNKNOWN: カード本文・選択肢・状態を安全に解釈できない
```

距離は各ケーシィ系統を物理serialで追跡し、対象lineを除外して再計算する。

- 有効lineが1本なら、山札からの再建がPOSSIBLEでも `UNIQUE`
- 失うと最良距離が1turn以上悪化するなら `IMPORTANT`
- 唯一のEnergy付きline、最も進化したline、次の攻撃役0本化もIMPORTANT
- 除外再計算が失敗した場合は `UNKNOWN_IMPORTANCE`

UNKNOWNを安全認定へ変換しない。

## 3. 公開最大打点

相手の現在Activeについて、次を分離して計算する。

```text
damage_floor
evidenced_policy_cap
final_safety_cap
continuity
```

### floor

現在公開され、支払い済みまたは確定支払い可能な技・modifierだけから得る最低
打点。

### evidenced policy cap

公開済みカード、同一試合で確認された補助、対象デッキで高頻度に採用されると
いう事前裏付けを分けて記録する。単に「入ることがある」だけでは確定所持に
しない。

### final safety cap

技本体、Energy、弱点・抵抗、Tool、Stadium、公開modifier、物理的に残る
Power Proの枚数を合成した上限。

Power Proは1枚だけと仮定せず、物理4枚から公開済み・使用済み・捨て札・
現在使用可能なserialを差し引く。同一turnのstackを反映する。

### continuity

```text
REPEATABLE_READY
RECHARGE_REQUIRED
NO_READY_ATTACK
UNKNOWN
```

最大打点が高くても、次の攻撃に再準備が必要なら、壁の価値とケーシィを
犠牲にする価値は変わる。

## 4. ベンチ0回避

ベンチ0でActiveが倒されれば敗北する局面では、Powerful Handの打点を20
下げてもShaymin等を出す価値がある。

ただし、常にBasicを出す規則にはしない。

優先するのは次を満たす低費用Basicである。

- 合法に場へ出せる
- 現在の確定terminal attackやcurrent threat KOを失わない
- 追加することで明確にboard-outを回避する
- 失う手札1枚、打点20、ベンチ枠、Prize価値が許容できる
- 親の攻撃またはEND直前に限定できる

公開情報からのfinal safety capでもActiveが倒されず、育成・検索・壁・
次アタッカー等の別の合理的理由もない場合は、ベンチへ出すことを強制しない。

この行動変更は、実ログで発火せず数値差もない場合、解析器だけを残し行動gate
は採用しない。

## 5. ノコッチ／ノココッチの3価値

各判断点で次の4候補を作る。

```text
RUN_AWAY_ACCELERATION
CERTIFIED_REUSABLE_WALL
CERTIFIED_SACRIFICE_WALL
NO_WALL_OR_UNKNOWN
```

### RUN_AWAY_ACCELERATION

ノココッチ66を山札へ戻し、`min(3, deck_count)`枚引く価値。

確定してよいのは、引く枚数と、手札枚数によるPowerful Handの
`20 * draw_count`だけである。カードidentityを必要とする進化、Energy、
検索、switchはPOSSIBLEに留める。

Run Awayを壁より上に置けるのは次をexactに証明できる場合に限る。

1. terminal win
2. 現在の反復可能な脅威への確定KO
3. backupを含む安全なPrize交換

単に攻撃できる、非KO damageを与えられる、手札が増える、だけでは壁を解除
しない。

### CERTIFIED_REUSABLE_WALL

主にノココッチ66。

- `remaining_hp > final_safety_cap`
- Run Away能力が公開metadataで一致
- 攻撃された場合も拒否された場合も準備が確実に進む
- 後で安全にRun Awayできる
- 解除後の昇格先と返しの攻撃まで安全
- 相手の最終Prizeにならない

等値はKOなので拒否する。

### CERTIFIED_SACRIFICE_WALL

主にノコッチ305。

- 1-Prize bodyとして正確に評価
- Energy、Tool、進化札、将来のノココッチ価値を損失へ含める
- 買った1自分turnでprotected lineがCERTIFIED-readyになる
- 相手が攻撃を拒否してもcurrent handから確定進展する
- `いれかわる`後の交代先が安全
- 相手の最終Prizeにならない

「ノコッチを出したが控えを作れない」状態は認定しない。ただし、今唯一の
ケーシィ系統を守らなければ再建可能性が悪化する場合、その現在lineの保護価値
は残す。

## 6. STRICTとPRESERVE_CHANCE

### STRICT_CERTIFIED_WALL

すべて必要。

- protected lineがUNIQUEまたはIMPORTANT
- 露出側でSUPPORTEDなREPEATABLE_READY floor KO
- wall optionがexact legal
- 現在公開されarmedなgust / bench snipeなし
- 攻撃時・拒否時の両方でCERTIFIED progress
- 解除後の攻撃と相手continuityまで含むsafe release
- final Prize donationでない
- terminal/current threat KOを失わない
- unsupported input 0

### PRESERVE_CHANCE_WALL

次のいずれかが残る場合。

```text
CAP_ONLY
RECHARGE_REQUIRED
CONTINUITY_UNKNOWN
REVEALED_POSSIBLE_BYPASS
PROGRESS_POSSIBLE_ONLY
RELEASE_POSSIBLE_ONLY
IMPORTANCE_UNKNOWN
SAFETY_CAP_UNKNOWN
```

PRESERVE_CHANCEは「保護価値がない」ではない。しかし、初版の行動変更根拠
には使わず、ログへ残す。

## 7. 相手が攻撃しない事故

壁を出すだけで1turnを買ったとは数えない。

相手が攻撃を拒否しても、現在の手札・盤面で次のいずれかが確定することを
要求する。

- 進化
- 手張り
- 既知検索による確定取得
- distanceの厳密な改善
- 安全な自己解除

壁へ入った時点で期限を固定する。

```text
hold_deadline = hold_entry_turn + initial_certified_turn_delay
```

期限を後から延長しない。各自分turnで距離が厳密に改善しなければSTRICTを
失効させる。完成後も壁を保持し続け、Bossを引く時間を与えない。

## 8. 安全な解除

Run AwayまたはTrading Placesで壁を解除する場合、次のいずれかを必要とする。

1. 同じturnにterminal winまたはcurrent threat KO
2. 攻撃後も相手floorを耐える
3. 別のCERTIFIED-ready backupが残りPrize交換が悪化しない
4. 別のcertified wallへ交代する

「フーディンが完成した」だけでは不足する。相手を倒せず、返しに同じready
攻撃役から倒されるなら解除しない。

## 9. シャドー計測と行動変更

C4は次の3作用点を測るが、全callbackで親actionと同一objectを返す。

```text
A_FORCED_PROMOTION
B_ACTIVE_DUDUNSPARCE_RUN_AWAY
C_DUNSPARCE_TRADING_PLACES_CHILD
```

EXPOSE_STATEとWALL_STATEを別々に投影し、脅威、HP、backup、bypass、拒否時
進展、解除後状態を現在stateから流用しない。

C4の到達条件を満たした後、C5ではA/B/Cのうち一つだけを選べる。

- 同じ機構が2つ以上の非mirror bucketで観測
- 各bucketでcompleteなnatural parent agreementが2件以上
- refusal、gust、safe releaseに重大な反例なし
- root検証済みstateをfixture化

条件不足ならC5はno-opとする。PRESERVE_CHANCEの件数だけで行動を変えない。

行動変更候補は固定700局の絶対強度、両seat、Historical Silver、隣接対面、
対面別floor、paired lower bound、transaction完全性を通過した場合だけ最終
提出候補へ含める。
