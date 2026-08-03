# v4 C5 一般化STRICT壁 行動変更 fix7 決定契約

## 前提

C5はC4のshadow logを取得・監査する前に実装しない。

C4:

- spec:
  `alakazam_staged_20260729/specs/v4_c4_wall_shadow_fix6_immutable_spec.md`
- C4 spec SHA-256:
  `F6BFEA318FC245543BDB8043D4FF0E8D60CD9A476403FA3E52993EF35CB2859B`

Sol-Ultra strategy judgeが、C4のroot検証済みraw rowsから行動変更可能なSTRICT部分集合を選ぶ。

`PRESERVE_CHANCE_WALL` は件数や見かけの成功率にかかわらずshadowのまま残す。

## 一般化条件

実装条件に使ってよい:

- threatのdamage floor/cap
- continuity
- protected lineのUNIQUE/IMPORTANT
- next-attacker distance
- wall HP、Prize、Energy、Tool、進化札
- public bypass
- refusal progress
- safe release
- turn flagsとlegal options

使用禁止:

- 相手名
- matchup名
- episode ID
- seed
- replay action label
- hidden Hand/Deck/Prize

ミラーだけ、特定のSolrockだけ、特定episodeだけに発火する固定分岐を作らない。

## 許可する行動点

Sol-UltraがC4 evidenceから有効と判断したものだけを個別にenableする。

### A. forced promotion

KO後または自己除去後の `TO_ACTIVE` で、親が未完成のUNIQUE/IMPORTANTケーシィ系統を選ぶ一方、STRICTな壁optionが存在するとき、壁を選ぶ。

必要:

- promotion promptがexact
- protected lineへのfloor KOがrepeatable
- wallにより確定進展
- safe release
- final Prize donationでない

### B. Active Dudunsparce Run Away抑制

親が `にげあしドロー` を選ぶが、次をすべて満たすとき、そのoptionを除外して親順位を再適用する。

- ActiveノココッチがSTRICT reusable wall
- Run Away後の昇格先がunsafe
- Run Awayが同ターンterminal/current threat KOへ変換しない
- wall保持中にprotected lineが確定進展する
- 壁を保持する追加turnが必要最小限

未知のdraw3を理由にSTRICTを解除しない。ただし、既存Hand/Benchで同ターンattack変換が確定するRun Awayは壁より優先する。

### C. Dunsparce Trading Places交代先veto

ノコッチの `いれかわる` 後のSwitch childで、親が未完成UNIQUE/IMPORTANT lineをready threatの前へ出すとき、その交代先だけを除外して親順位を再適用する。

必要:

- attackとchildのtransactionを物理serialで追跡
- 残る合法optionが1個以上
- strict wallまたはsafe attackerへの交代先が存在
- switch後のattack exposureを再計算

## veto後の原則

- action indexを固定しない。
- semantic option keyで除外・再bindする。
- 親delegate stateを変更前snapshotへ戻す。
- 残存optionsで通常親rankingを再実行する。
- parent ownerが新規成立したら、そのtransactionを保持する。
- duplicate callbackを同じsemantic actionへrebindする。
- callbackごとにSTRICT証明を再計算する。
- rerankを証明できなければ親actionを保持する。
- arbitrary ENDへ置換しない。

## hold duration

壁を保持するのは、protected distanceを改善する必要最小turnだけ。

各自分turnで次を再計算する。

```text
distance_before
distance_after
remaining_progress_steps
gust_exposure_turns
safe_release_now
```

次でholdを終了する。

- terminal/current threat KOへ変換できる
- protected attackerがreadyかつsafe release可能
- backup readyによりPrize交換が成立
- wallのcap survivalが失われた
- public bypassが成立した
- refusal progressが停止した
- final Prize条件が変わった

完成後も惰性で壁を保持し、相手がBossを引くturnを増やさない。

## draw3との比較

Run Awayを抑制するたび、次をtraceする。

```text
lost_immediate_draw_count = min(3, deck_count)
lost_possible_powerful_hand = 20 * lost_immediate_draw_count
same_turn_attack_conversion
protected_distance_gain
wall_survival_margin
hold_turns
```

`lost_possible_powerful_hand` は機会費用であり、未知のdraw内容を確定利益にしない。

壁保持による保護が確定でなくなったら、draw3を抑制しない。

## 事故防止

次では発火禁止。

- 壁だけ残り、live lineがなくrebuild IMPOSSIBLE
- 相手が攻撃しなくても自分が進展しない
- safe releaseがない
- 相手のfinal Prizeになる
- public gust / snipeで保護不能
- continuityがRECHARGE_REQUIRED / NO_READY_ATTACK / UNKNOWN
- cap-only threat
- current terminal attackまたはcurrent threat KOを失う
- exact parent owner / v1/v3/C1/C3 transaction中
- malformed/unsupported state

## trace

```text
rule_version = V4_STRICT_WALL_ACTION_FIX7
decision_id
enabled_action_point
strict_certificate
parent_action
excluded_semantic_keys
reranked_parent_action
applied_action
transaction_stage
hold_turn
distance_delta
safe_release
outcome_linkage
```

outcome:

```text
PARENT_AGREEMENT
CANDIDATE_APPLIED
COUNTERFACTUAL_UNOBSERVED
```

## 固定fixture

各enable action pointについて、C4で実在したroot検証済みstateを最低2件fixture化する。

さらに:

1. mirror / nonmirror同型条件で同じ判断
2. opponent名だけ変更して同じ判断
3. continuityをRECHARGE_REQUIREDへ変えると非発火
4. protected lineをREDUNDANTへ変えると非発火
5. wallがfinal Prizeなら非発火
6. public gust追加で非発火
7. refusal progress削除で非発火
8. safe release削除で非発火
9. Run Awayがcurrent threat KOへ変換するなら保持
10. ready後の余分なholdをしない
11. duplicate / reordered option / owner transaction
12. rerank uncertifiedなら親保持
13. `88844273` 4局面
14. `88843743` Run Away前後

## 機構到達条件

- action-changing STRICT completion 8件以上
- 両seat
- 2 nonmirror opponent buckets以上
- enableした各action pointで2 completed outcomes以上
- protected line readyまたは攻撃までのtrace完了
- opponent refusalを含むoutcome 2件以上
- gust exposureを含むoutcome 2件以上
- transaction fault、stale abort、unsupported change 0

到達不足は `INSUFFICIENT_EVIDENCE`。

## 数値採用条件

固定700局で全共通gateを満たす。

- wins `>= ABS_FLOOR`
- overall paired delta正
- Historical Silver `>= +3/100`
- Silver両seat非負
- Silver seed block 5個中2個以上正
- adjacent 6 opponents合計 `>= -2/600`
- 各opponent `>= -2/100`
- 各opponent-seat `>= -2/50`
- one-sided 95% paired lower bound:
  - overall / adjacent `>= -1pp`
  - Silver `>= -3pp`
- 機構到達条件
- raw完全性

## rollback

A/B/Cを個別feature flagとして実装・評価する。

問題が出たaction pointだけを外せるようにし、C4 shadow traceと他の採用済み段階を壊さない。

最終提出候補へ含めるのは、Sol-Ultraの事後判定とrootのraw再検証を両方通ったaction pointだけである。
