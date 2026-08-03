# v4 C4 壁価値 STRICT / PRESERVE_CHANCE シャドー fix6 不変仕様

## 目的

ノコッチ・ノココッチを、単なるベンチ要員や即時ドロー源ではなく、次の3価値で比較する。

```text
RUN_AWAY_ACCELERATION
CERTIFIED_REUSABLE_WALL
CERTIFIED_SACRIFICE_WALL
```

相手の攻撃準備ができている間、未完成のケーシィ系統をActiveへ出して倒され続ける事故を避ける。

同時に、壁を保持しすぎて手札補充を失う、相手に盤面形成・Boss到達の時間を与える、完成後も安全に解除できない事故を避ける。

C4は計測専用であり、全raw actionを親と完全一致させる。

## 一般化範囲

ミラー限定にしない。

相手名、archetype label、episode IDではなく、次だけで発火を判定する。

- 公開打点floor/cap
- 攻撃継続class
- ケーシィ系統の距離と重要度
- ノコッチ系統のHP、Prize、資源
- 公開された呼び出し・ベンチ狙撃経路
- 相手が攻撃しない場合の自分の確定進展
- 壁の安全な解除経路

相手の攻撃役が連続攻撃できないなら、同じ盤面でもSTRICTにならないことがある。

## 親版

C1〜C3の採否後、直前の最強採用版へshadow moduleを追加する。

- 不採用の行動変更を継承しない。
- C2距離はaction identity 100%の版だけを使う。
- C3打点解析は、unsupported action change 0かつraw完全性を通った版の解析部だけを使う。
- C3行動変更が不採用でも、検証済みの純粋damage/continuity analyzerはshadow部品として継承できる。

## 保護対象

各ケーシィ系統をC2で除外再計算する。

### UNIQUE

場に存在する有効なケーシィ系統がその1本だけ。

山札・手札からの再建が `POSSIBLE` でも、現在の1本は `UNIQUE` のまま。

### IMPORTANT

その系統を失うと、次のいずれかが起きる。

- best primary distanceのturn delayが1以上悪化
- `CERTIFIED -> POSSIBLE/IMPOSSIBLE/UNKNOWN`
- 唯一のEnergy付き系統を失う
- 最も進化した系統を失う
- 次の相手攻撃後に攻撃役が0本になる

### REDUNDANT

上記に該当しない。

### UNKNOWN_IMPORTANCE

除外再計算がfail-closedになった状態。安全でないとも安全とも決めず、行動変更には使用しない。

## threat class

### STRICT threat

すべて必要。

- 相手の対応済み攻撃役が `REPEATABLE_READY`
- `damage_floor >= protected_line_hp`
- その攻撃が保護対象へ到達する
- 現在公開中の確定gust・bench snipeで壁を無視できない
- formula、Energy、modifier、弱点・抵抗がすべてSUPPORTED

相手が `RECHARGE_REQUIRED` の場合、通常はSTRICTにしない。買った1ターンを使わずとも相手自身が再準備を要するため、ケーシィを1体犠牲にする方がPrize・tempo上よい場合がある。

### CHANCE threat

次のいずれか。

- KOがdamage capだけで成立
- continuityがRECHARGE_REQUIREDまたはUNKNOWN
- 打点補助がpossibleで未commit
- gust / bench snipeの可能性が残る
- 攻撃役の起動にhidden inputが必要

## 壁候補

### reusable wall

主にノココッチ `66`。

必要条件:

- exact legal promotionまたは現在Active
- wall HPがdamage capを上回る
-相手の公開確定効果で能力を止められない
- 後に `にげあしドロー` を使用できる
- 山札3枚以上を必要とする既存条件を満たす
- 解除後の昇格先が安全
- 最終Prizeを相手へ渡さない

### sacrifice wall

主にノコッチ `305`。

必要条件:

- exact legal promotionまたは現在Active
- 1-Prize
- attached Energy、Tool、進化札の損失を正確に計算
- 買った1自分ターンで保護対象がCERTIFIED-readyになる
- 相手が攻撃しなくても自分の進展がある
- `いれかわる` を使う場合の交代先が安全
- 最終Prizeを相手へ渡さない

「ノコッチを出したが控えを作れない」状態は壁として認定しない。ただし、今ここで唯一のケーシィ系統を守らなければ、再建が `POSSIBLE/IMPOSSIBLE` へ悪化する場合は、現在手札に全完成部品がなくても保護価値を残す。

## 相手が攻撃しない場合

「相手が1ターン無駄にするかもしれない」は進展証明にならない。

壁をActiveにしたままでも、次のいずれかが確定していることを要求する。

- ケーシィ系統を進化できる
- 必要Energyを付けられる
- 既知Handの検索・ドローを使い、必要部品を確定取得できる
- protected lineのdistanceが1段階以上改善する
- 壁を安全に解除できる

相手が攻撃せず盤面形成を続けるとき、壁保持turnごとに
`gust_exposure_turns` を増やす。

必要な進展が起きない追加turnはSTRICTを失効させる。

## 安全な解除

ノココッチの `にげあしドロー` やノコッチの `いれかわる` で解除する場合、昇格・交代先について次のいずれかを要求する。

1. 同じ自分ターンに確定terminal winまたは確定current threat KOを取る。
2. 攻撃後も相手damage floorを耐える。
3. 攻撃後に別のCERTIFIED-ready backupが残り、Prize交換が悪化しない。
4. 別のcertified wallへ交代する。

単に「フーディンが完成した」だけでは、安全解除としない。完成フーディンで相手を倒せず、次ターンに同じready攻撃役から倒されるなら、解除は危険である。

相手がすでに攻撃準備済みなのに、未完成ケーシィ・ユンゲラーへ `いれかわる` で交代する経路は拒否する。

## 3価値の比較

### RUN_AWAY_ACCELERATION

ノココッチを山札へ戻し3枚引く価値。

確定価値にできるのは:

- 既存Hand/Benchだけで同ターンattackへ変換
- safe promotionが一意
- 山札3枚以上

未知の3枚の中身による改善は確率的価値としてtraceするだけで、STRICTな証明にしない。

手札が3枚増えると、将来Powerful Handは最大+60され得るが、未知ドローなので確定KO証明には使わない。

### CERTIFIED_REUSABLE_WALL

ノココッチがdamage capを耐え、買ったturnで盤面が確定進展し、後で安全にRun Awayできる価値。

比較項目:

```text
survival_margin
protected_distance_gain
safe_release_distance
lost_immediate_draw3
gust_exposure_turns
resource_cost
```

### CERTIFIED_SACRIFICE_WALL

ノコッチ1-Prizeを失う代わりに、唯一・重要なケーシィ系統を確定readyにする価値。

比較項目:

```text
prize_value
evolution_cards
attached_energy
attached_tools
lost_future_dudunsparce
lost_draw3_value
protected_distance_gain
```

## arbitration shadow

次の順序で提案する。

1. `CURRENT_TERMINAL_ATTACK`
2. `CURRENT_CERTIFIED_THREAT_KO`
3. `RUN_AWAY_ACCELERATION`
   - 同ターンattack変換
   - safe exact promotion
   - deck count 3以上
4. `CERTIFIED_REUSABLE_WALL`
5. `CERTIFIED_SACRIFICE_WALL`
6. `PARENT_ACTION`

reusable wall同士:

```text
survival_margin desc
protected_distance_gain desc
safe_release_distance asc
resource_cost asc
canonical_option_key
```

sacrifice wall同士:

```text
prize_value
evolution_cards
attached_energy
attached_tools
lost_future_dudunsparce
lost_draw3_value
canonical_option_key
```

## STRICT_CERTIFIED_WALL

次をすべて満たす。

- STRICT threat
- protected lineがUNIQUEまたはIMPORTANT
- wall候補がexact legal
- 公開確定bypassなし
- 相手が攻撃しても、しなくても自分の確定進展がある
- reusableならdamage capを耐える
- sacrificeなら買ったturnでprotected lineがCERTIFIED-ready
- safe releaseを証明
- 相手の最終Prizeにならない
- reconstructionがIMPOSSIBLEで保護対象が存在しない単なる延命でない
- unsupported input 0

C4では行動を変えない。

## PRESERVE_CHANCE_WALL

保護価値はあるが、STRICTのどれかが未確定。

例:

- KOがcapのみ
- continuityがRECHARGE_REQUIRED / UNKNOWN
- possible gust
- safe releaseがPOSSIBLE
- protected reconstructionがPOSSIBLE
- wallがfloorは耐えるがcapを耐えない
- opponent refusal時の進展が検索・ドロー待ち

C4でもC5でも、初版では行動を変えない。

## bypass

```text
NO_PUBLIC_BYPASS
CERTIFIED_GUST
CERTIFIED_BENCH_SNIPE
REVEALED_POSSIBLE_GUST
HIDDEN_UNKNOWN
```

隠れたBossを「必ずある」「絶対ない」のどちらにも置かない。

現在すでに合法・公開・armedなgustまたはbench snipeだけがSTRICTを拒否する。

同試合でBossが公開されたが現在の所持を証明できない場合は、`REVEALED_POSSIBLE_GUST` としてchance riskと `gust_exposure_turns` を記録する。

## outcome tracking

各shadow decisionへ安定した `decision_id` を付ける。

```text
PARENT_AGREEMENT
CANDIDATE_APPLIED
COUNTERFACTUAL_UNOBSERVED
```

C4で観測結果として使えるのは `PARENT_AGREEMENT` だけ。

追跡:

- wallがActiveになった
- wallが攻撃された
- wallがsurvive / KO
- 相手が攻撃を拒否
- gust / snipe bypass
- protected lineが進化・手張り
- distanceが改善
- Run Away / Trading Placesで解除
- 解除先
- protected attackerがattack
- Prize delta
- game end / truncation

shadowで親が壁を選ばなかった反実仮想を「壁が有効だった」と数えない。

## trace

最低限:

```text
schema_version
rule_version = V4_WALL_SHADOW_FIX6
decision_id
parent_action
proposed_action
applied_action
action_identity
protected_line
importance
distance_before
distance_without_line
threat
damage_floor
damage_cap
continuity
wall_candidates[]
run_away_value
reusable_wall_value
sacrifice_wall_value
bypass
refusal_progress
safe_release
gust_exposure_turns
wall_class
arbitration_reason
outcome_status
```

## 必須fixture

1. mirrorの完成Alakazam対未完成Abra line、Dudunsparce reusable wall
2. 非mirrorのrepeatable attackerで同じSTRICT
3. recharge-required attackerではSTRICTを拒否
4. unique Abraだけを守るsacrifice Dunsparce
5. rebuildがPOSSIBLEでも現在lineをUNIQUE維持
6. live lineなし＋rebuild IMPOSSIBLEの単なる延命拒否
7. opponent refusalでも進化・手張りが進む
8. opponent refusalで何も進まず拒否
9. Run Awayでcurrent threat KOへ変換
10. Run Away後の昇格先が倒されるため拒否
11. Trading Places後の未完成line露出を拒否
12. public certified gustでSTRICT拒否
13. revealed possible Bossはchance riskだけ
14. opponent final Prizeになる壁を拒否
15. wallとdraw3の比較
16. duplicate / reordered options / stale outcome
17. episode `88844273` 固定局面
18. episode `88843743` Run Away前後

## 到達条件

- STRICT 24 unique states以上
- PRESERVE_CHANCE 40 unique states以上
- 両seat
- 3 opponents以上、非mirror2以上
- STRICTが2 opponent buckets以上で反復
- natural parent agreement 12件以上
- trace-complete observed wall outcome 8件以上
- action identity 100%
- metric exception 0

不足は `INSUFFICIENT_EVIDENCE`。

## C5へ渡す条件

C5はC4 raw logをSol-Ultraが読み、次を満たすSTRICT部分集合だけを選ぶ。

- 少なくとも2非mirror bucketで同じ機構
- natural observed outcomeが意図と一致
- opponent refusal、gust exposure、safe releaseの重大な未解決例がない
- reusable / sacrifice / Run Awayのどれを変更対象にするかを個別に固定

C4のPRESERVE_CHANCE件数を理由に行動変更しない。
