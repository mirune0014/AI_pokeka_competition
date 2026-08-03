# v4 C4 壁シャドー fix6 後発binding amendment

日付: 2026-07-30

## 優先順位

このamendmentは、次の後に確定したユーザー判断とstrategy judgmentを、
凍結C4仕様へ追加する。

```text
v4_c4_wall_shadow_fix6_immutable_spec.md
v4_c2_c5_strategy_judge_binding_amendment.md
v4_c3_power_pro_stacking_engine_amendment.md
```

矛盾する場合は、C2-C5 binding、Power Pro stacking amendment、この
amendmentの順に後発内容を適用する。

## C4の作用

C4はすべてのcallbackで親actionをPython object、値、要素順まで同一に返す。

```text
applied_action = exact parent action
```

`proposed_action`はshadow比較結果であり、行動変更ではない。

C4で `CANDIDATE_APPLIED` が1件でも出た場合はmetric faultとする。

## 状態機械

```text
CAPTURE
VALIDATE_PUBLIC_STATE
BUILD_COUNTERFACTUAL_PAIR
CLASSIFY_PROTECTED_LINE
CLASSIFY_EXPOSE_THREAT
ENUMERATE_FOUR_ALTERNATIVES
CERTIFY_STRICT_OR_CHANCE
PARETO_ARBITRATE
EMIT_SHADOW
RETURN_EXACT_PARENT_ACTION
```

失敗時:

```text
EMIT_REJECTION
RETURN_EXACT_PARENT_ACTION
```

## decision point

```text
A_FORCED_PROMOTION
B_ACTIVE_DUDUNSPARCE_RUN_AWAY
C_DUNSPARCE_TRADING_PLACES_CHILD
```

初版C4は三点を計測するが、いずれも変更しない。

## counterfactual pair

`EXPOSE_STATE` と `WALL_STATE` を別に投影する。

- EXPOSE:
  親の昇格、Run Away後昇格、Trading Places child後
- WALL:
  壁を選択または保持した後

次を現在stateから共用してはならない。

- threat reach
- protected line HP
- wall HP
- post-attack attacker survival
- backup readiness
- gust / snipe bypass
- refusal progress
- safe release

両投影のfingerprintを別々にtraceする。

## 4候補

```text
RUN_AWAY_ACCELERATION
CERTIFIED_REUSABLE_WALL
CERTIFIED_SACRIFICE_WALL
NO_WALL_OR_UNKNOWN
```

## Run Away

未知の3枚は匿名tokenとする。

- certified draw count:
  `min(3, deck_count)`
- Powerful Handの枚数由来damage delta:
  `20 * certified_draw_count`
- 引くcard identityを使う進化、検索、Energy、switch経路:
  `POSSIBLE`

Run Awayを壁より優先できるexact conversionは次だけ。

1. terminal win
2. current repeatable threat KO
3. backupを含む安全なPrize交換

単なる同turn attackまたは非KO damageでは壁より上に置かない。

## reusable wall

Run Away能力を持つのはノココッチ `66` だけとする。

必要:

```text
remaining_hp > final_safety_cap
```

`final_safety_cap`は、技本体、対応済み公開modifier、弱点・抵抗、Tool、
Stadium、Power Proの物理4枚stackを反映した最終打点である。

等値はKOとして拒否する。

## sacrifice wall

ノコッチ `305` を1-Prize bodyまたはTrading Placesの攻撃役として扱う。
Run Away能力を付与しない。

買った1自分turnでprotected lineが `CERTIFIED-ready` になること、
相手が攻撃を拒否してもcurrent-hand witnessで進展または安全解除できることを
STRICTの必要条件にする。

## protected line

rebuildが `POSSIBLE` でも、現在の有効lineが1本なら `UNIQUE` を維持する。

除外再計算で次のいずれかが起きるlineを `IMPORTANT` とする。

- best distanceが1 turn以上悪化
- `CERTIFIED`から低下
- 唯一のEnergy付きlineを失う
- 最も進化したlineを失う
- 次の相手攻撃後の攻撃役が0本

## STRICT

すべて必要。

- protected lineがUNIQUEまたはIMPORTANT
- EXPOSE側でSUPPORTEDなREPEATABLE_READY floor KO
- wall optionがexact legal
- 現在公開・armedなbypassなし
- 攻撃時・拒否時の両方でCERTIFIED progress
- post-release attackと相手continuityまで含むsafe release
- final Prize donationでない
- terminal/current threat KOを失わない
- unsupported input 0

## PRESERVE_CHANCE

次は必ずchanceへ落とし、C4でもC5初版でも行動変更へ使わない。

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

## Pareto arbitration

reusableをsacrificeより自動優先しない。

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

一意な優越がなければ:

```text
NO_CERTIFIED_DOMINANCE
```

## non-rolling deadline

entry時に固定する。

```text
hold_deadline = hold_entry_turn + initial_certified_turn_delay
```

後のcallbackで延長しない。

各held own-turnでdistanceが厳密に改善しなければ証明を失効させる。

## fixed-damage primitive

親版 `_cumulative_parent.py` の
`_bridge_retaliation_attack_damage` と同値のfail-closed primitiveを使ってよい。

用途:

- fixed printed damage
- exact Energy payment
- Weakness / Resistance
- ignore W/R本文

次はC4側で別に合成する。

- Active threat
- EXPOSE/WALL投影
- continuity
- Power Pro safety cap
- gust / snipe
- refusal / release / deadline

対応外・動的本文は `UNKNOWN` とする。

## identity

```text
pair_id =
  public state fingerprint
  + decision point
  + semantic action keys
  + protected serial
  + wall serial

decision_id =
  pair_id
  + game boundary fingerprint
  + turn
  + transaction stage
```

相手名、seed、episode IDはID材料にも判定材料にも使わない。

## 必須追加trace

```text
decision_point
pair_id
parent_post_fingerprint
candidate_post_fingerprint
expose_state_fingerprint
wall_state_fingerprint
certified_draw_count
certified_draw_damage_delta
premium_power_pro_multiplicity
evidenced_policy_cap
safety_cap
hold_entry_turn
hold_deadline
distance_progress_by_turn
candidate_rows[4]
rejection_codes[]
parser_source
outcome_events[]
```

## C5選択前提

C4の到達条件を満たすまでC5は `NO_OP / INSUFFICIENT_EVIDENCE` とする。

到達後も、A/B/Cを組み合わせず一つだけ選ぶ。選択点は、2つ以上の非mirror
bucketの各bucketでcompleteなnatural `PARENT_AGREEMENT`が2件以上あり、
refusal、gust、safe releaseに重大な反例がないものに限定する。
