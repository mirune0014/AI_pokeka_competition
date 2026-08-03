# v4 C4 STRICT / PRESERVE_CHANCE 壁シャドー実装前判断

日付: 2026-07-30

## 判断

C4は行動を変えない一般化壁解析として実装する。

比較する候補は次の4つに固定する。

```text
RUN_AWAY_ACCELERATION
CERTIFIED_REUSABLE_WALL
CERTIFIED_SACRIFICE_WALL
NO_WALL_OR_UNKNOWN
```

相手名、対面名、episode ID、seedは判定条件に使わない。

C3の行動変更が不採用なら、C4の親は採用済みC2 FIX4B
`29084BC13CB74236ABE557B57A9E633A8F9E88FA83FF22D131C835293E987157`
とする。C3から継承してよいのは、行動gateを無効化したpureな
damage / continuity analyzerだけである。

C4 raw log取得前のC5判断は `NO_OP / INSUFFICIENT_EVIDENCE` とする。

## 状態機械

```text
CAPTURE
→ VALIDATE_PUBLIC_STATE
→ BUILD_COUNTERFACTUAL_PAIR
→ CLASSIFY_PROTECTED_LINE
→ CLASSIFY_EXPOSE_THREAT
→ ENUMERATE_FOUR_ALTERNATIVES
→ CERTIFY_STRICT_OR_CHANCE
→ PARETO_ARBITRATE
→ EMIT_SHADOW
→ RETURN_EXACT_PARENT_ACTION
```

失敗時は `EMIT_REJECTION → RETURN_EXACT_PARENT_ACTION` とする。

decision pointは次の3点をshadow分類する。

```text
A_FORCED_PROMOTION
B_ACTIVE_DUDUNSPARCE_RUN_AWAY
C_DUNSPARCE_TRADING_PLACES_CHILD
```

## 別投影

現在stateを両案へ流用しない。

- `EXPOSE_STATE`
  - 親の昇格、Run Away後の昇格、またはTrading Places child後
- `WALL_STATE`
  - 壁を選択または保持した後

脅威はEXPOSE側、壁の生存・公開bypass・攻撃拒否時の進展・解除後の状態は
WALL側で別々に計算する。

Run Awayの未知3枚は匿名tokenとして扱う。手札枚数 `+3` と
Powerful Handの `+60` は確定するが、カードidentityに依存する経路は
`POSSIBLE` のままにする。

## STRICT

すべて必要。

- liveなケーシィ系統が `UNIQUE` または `IMPORTANT`
- rebuildが `POSSIBLE` でも現在lineのUNIQUEを維持
- EXPOSE側でSUPPORTEDな `REPEATABLE_READY` 攻撃のfloorがlineをKO
- wall optionがexact legal
- 現在公開・armedなgust / snipe bypassなし
- 相手が攻撃しても拒否しても、current-handのCERTIFIED witnessで距離が進む
- safe releaseをpost-release attackと相手continuityまで含めて証明
- final Prize donationでない
- terminal win / current threat KOを失わない
- unsupported input 0

ノココッチ `66` だけをRun Away能力持ちとして扱う。

ノコッチ `305` は1-Prize bodyまたはTrading Placesの攻撃役として扱い、
Energy、Tool、将来ノココッチ価値、switch childを別に計算する。

reusable wallは次を必要とする。

```text
remaining_hp > final_safety_cap
```

等値はKOである。

sacrifice wallは、買った1自分turnでprotected lineが
`CERTIFIED-ready`になり、相手が攻撃しなくても安全な自己解除がある場合だけ
STRICTにする。

## PRESERVE_CHANCE

次は行動変更へ使わない。

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

隠れたBossの一般可能性だけでSTRICTを拒否しない。同試合で公開済みだが
現在所持を証明できないBossはCHANCEへ落とす。

## 比較

Run Awayを壁より優先できるのは、既存Hand / Benchと匿名draw countから
次のいずれかをexactに証明した場合だけとする。

1. terminal win
2. 現在のrepeatable threat KO
3. backupを含む安全なPrize交換

単なる攻撃可能や非KO damageでは不足する。

reusableとsacrificeは自動順位にせず、次をPareto比較する。

```text
protected readiness
attacker / backup continuity
own Prize loss
hold turns
gust exposure
Energy / Tool / evolution loss
lost draw3 / deck count
safe release
final-Prize outcome
```

一意な優越を証明できなければ `NO_CERTIFIED_DOMINANCE` とする。

## hold deadline

entry時に固定する。

```text
hold_deadline = hold_entry_turn + initial_certified_turn_delay
```

deadlineを後から延長しない。

各held own-turnでC2距離が厳密に改善しなければ証明を失効させる。

次でholdを終了する。

- readyかつsafe release
- current threat KO
- backup ready
- wallのcap survival喪失
- public bypass成立
- 拒否時進展停止
- final Prize条件変化
- deadline到達

## fixed damage parser

親の `_bridge_retaliation_attack_damage` は、固定printed damage、
Energy支払、Weakness / Resistanceのfail-closed primitiveとして再利用できる。

`_bridge_public_retaliation_analysis` 全体は、Active threat、
EXPOSE/WALL別投影、continuity、Power Pro、gust/snipe、
refusal/release/deadlineが不足するため、そのまま再利用しない。

traceへ `parser_source`、attack ID、SUPPORTED / rejection reasonを残す。

## C4到達条件

- STRICT 24 unique states以上
- PRESERVE_CHANCE 40 unique states以上
- 両seat
- 3 opponents以上、非mirror 2以上
- STRICTが2 opponent bucket以上
- natural parent agreement 12件以上
- trace-complete observed wall outcome 8件以上
- action identity 100%
- metric exception 0

不足は `INSUFFICIENT_EVIDENCE` とする。

## C5選択

C4の凍結到達条件を満たした後、A/B/Cのうち一つだけを選べる。

その作用点について、2つ以上の非mirror bucketの各bucketでcompleteな
`PARENT_AGREEMENT`を2件以上確認し、opponent refusal、gust exposure、
safe releaseに重大な反例がなく、root検証済みstateをfixture化できることを
必要とする。

複数作用点を同時に実装しない。優越が一意でなければC5はno-opとする。

## 後発binding

凍結C4本文と差がある場合、後発binding・Power Pro amendment・ユーザー判断を
次のように適用する。

- current state流用ではなくEXPOSE/WALL別投影
- `damage_cap`ではなく四枚stackを含む`final_safety_cap`
- Run Awayの単なる同turn attackより、terminal/threat-KO/safe exchangeを要求
- reusable自動優先ではなくsacrificeとの明示比較
- 手札枚数由来のPowerful Hand `+60`は確定、card identityは未知
- 通常の未知drawを拒否時の確定進展に使わない
- hold deadlineはnon-rolling
- C3不採用actionは継承せず、pure analyzerだけ継承
