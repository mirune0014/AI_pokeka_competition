# Controlling amendment: Explorer ATTACK_DEPTH

この文書は
`STRATEGY_SELECTION_EXPLORER_MARGINAL_TURN_DOMINANCE_V2.md`
のうち、二体目以降の攻撃可能な控えの扱いと
`episode_88242194_replay.json` の必須 veto を上書きする。

## 証拠の更新

全 `44/44` certificate を再監査した結果、
`episode_88242194_replay.json`、seat `1`、turn `4` は
`BAD_RESOURCE` ではなく `GOOD_BUT_TIEBREAK` と確定した。

同じく次の追加 ready attacker 局面も `GOOD_BUT_TIEBREAK` であり、
追加控えを一律に無価値または悪手とは扱えない。

- `episode_87668611_replay.json`
- `episode_87670217_replay.json`
- `episode_87671854_replay.json`
- `episode_87858380_replay.json`
- `episode_88399550_replay.json`
- `episode_88725375_replay.json`

## 削除する条件

次の旧条件を削除する。

- 攻撃可能な異なる控えが一体いれば、二体目以降の価値は常にゼロ。
- `88242194` では追加控えを必ず veto する。

二体目の攻撃可能な控えは、状況により正の `ATTACK_DEPTH` 役割を持つ。

## 改訂した比較

上位五層は変更しない。

1. 今ターンの確定勝利。
2. 公開情報による確定敗北回避。
3. 今ターンの即時 Prize。
4. 全公開効果適用後の現在攻撃結果。
5. 最初の異なる ready successor が `0 -> 1` になること。

第六層では、次を一つの componentwise board/resource vector として比較する。

- 異なる ready attacker の深さ。
- 場に増える二 Prize ポケモンの露出。
- 保持する draw、Boss、回収、進化の具体的役割。
- 保持する Energy と、次の手貼り余地。
- Bench 容量。
- 対応済みの公開 reply envelope に対する生存・攻撃範囲。

候補が全成分で親以上であり、少なくとも一成分で厳密に上回る場合だけ、
`ATTACK_DEPTH` を理由に置換できる。

次は比較不能であり、親へ戻す。

- 控えの深さは増えるが、重要な資源を失う。
- 控えの深さは増えるが、二 Prize 露出も増える。
- reply envelope が不完全で、追加控えの支配を証明できない。
- 異なる生きた役割どうしの優劣が公開情報で決まらない。

親の追加控え行動を、「すでに一体いる」という理由だけで止めない。
attacker の頭数や物理 serial だけで決めない。

## `88242194` の期待動作

Cape `97` と Lillie `108` は親の二枚組として保持する。
既存 ready Archaludon ex `68` と、新しく ready になる Archaludon ex `67` は
`ATTACK_DEPTH` である。

この局面は悪手 fixture ではなく、正の tie-break control とする。
親が同じ選択または継続を返すなら、別経路が componentwise に厳密支配しない限り親を保つ。

## telemetry

旧 `redundant_backup_rejections` は使わず、次を分ける。

- `attack_depth_seen`
- `attack_depth_strict_nonworse`
- `attack_depth_incomparable_parent`
- `attack_depth_strictly_worse`

## 不合格集合

確定した `BAD_ATTACK 5` と `BAD_RESOURCE 11` は変更しない。
それらは即時 Prize、実効攻撃、または資源役割支配で修正する。
上記七件の `GOOD_BUT_TIEBREAK` を、不合格集合へ混ぜない。

