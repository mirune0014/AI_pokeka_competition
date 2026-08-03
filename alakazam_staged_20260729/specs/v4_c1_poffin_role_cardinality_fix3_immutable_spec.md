# v4 C1 ポフィン役割・選択枚数 fix3 不変仕様

## 親契約

- umbrella:
  `alakazam_staged_20260729/specs/v4_setup_survival_wall_pipeline_immutable_contract.md`
- umbrella SHA-256:
  `B0657D0118847F2DDF7680E6D75AE28F2DF6CF42EE338B6355ADDC731F454783`

本候補では、なかよしポフィンの使用判断と0/1/2枚選択だけを変更する。
`next_attacker_action_distance`、公開打点、ベンチ0、壁判定は実装しない。

## 親identity

- source:
  `alakazam_staged_20260729/versions/alakazam_newdeck_v3_exact_evolution_ko_fix2`
- policy closure、33 files:
  `DC90205DE06AE3E2E41ADC661577096BB02EE5B42AB9F4366FC1A01154745B47`
- planner:
  `255FD9E1303E8E6DFB286952023A7F086CD233B4E5D5030EDBE06313A40697B7`
- deck:
  `F598F5E578D0440C96DC0492EAECF2E19739B7A23225BE57114A724EF7D0FB94`

## 出力

- candidate:
  `alakazam_staged_20260729/versions/alakazam_newdeck_v4_poffin_role_cardinality_fix3`
- focused test:
  `test_v4_poffin_role_cardinality_fix3.py`
- evaluation root:
  `alakazam_staged_20260729/evaluations/v4_poffin_role_cardinality_fix3`
- implementation receipt:
  `alakazam_staged_20260729/specs/v4_c1_poffin_role_cardinality_fix3_implementation_receipt.md`

親directory、既存fixture、共有toolを変更しない。
候補directory内のproduction sourceと新規focused testだけを所有する。

## 仮説

ポフィンは、ベンチを最大枚数で埋めるためではなく、フーディン攻撃系統とノココッチ補助系統の不足を埋めるために使う。

## MAIN判断

親版が、厳密に解決できるなかよしポフィン`1086`のPLAYを既に選択した場合だけ対象にする。

次を満たす場合、親版の通常順位付けの中でポフィンを拒否し、残る合法optionを同じ親版score／tie-breakで再順位付けする。

- 合法な空きベンチが0
- 通常上限`min(2, max(0, F - 1))`が0で、かつ`A == 0`のケーシィ例外も成立しない
- `A >= 2`かつ`N >= 2`

`A`は場のケーシィ／ユンゲラー／フーディン系統数、`N`は場のノコッチ／ノココッチ系統数、`F`は空きベンチ数である。

需要と容量が1以上なら、親版のポフィン優先順位を変更しない。
山札安全、現在KO、終局、既存transaction、親版のより厳しい拒否を緩めない。
ポフィンを任意0枚検索するためだけに消費しない。

## `TO_BENCH`選択

次をすべて満たすpromptだけを所有する。

- effectまたはcontext cardが一意にポフィン`1086`
- contextが`TO_BENCH`
- optional、`minCount == 0`
- `maxCount`が1または2
- raw／parsed一致
- option censusが一意
- 各optionを自分のdeck由来のcard ID、serialへ一意に解決できる

通常選択可能数:

```text
capacity = min(maxCount, 2, max(0, F - 1))
```

ただし、`A == 0`で、最後の空き1枠へケーシィを置ける場合だけ、capacityを1まで広げる。

各選択後の投影値を更新し、次を順番に1回ずつ満たす。

1. `A < 1`: ケーシィ
2. `N < 1`: ノコッチ
3. `A < 2`: ケーシィ
4. `N < 2`: ノコッチ

同じphysical card、同じserial、同じoptionを二度選ばない。
投影`N >= 2`でノコッチを追加しない。

該当0件なら`[]`、1件なら1 index、2件なら2 indexを返す。
`maxCount == 2`だけを理由に2件返さない。

同じ役割を満たすphysical cardが複数ある場合は、card ID、serial、stable semantic option keyの順で決定し、option表示順へ依存しない。

## 優先順位・所有権

- v1/v3 transactionが所有中なら発火しない
- 継承planner transactionが所有中なら発火しない
- Hilda→Enriching→緊急reserve transactionの既存1枚選択を変更しない
- current terminal KO、Boss terminal、進化後確定KOを変更しない
- duplicate callbackでは同じsemantic selectionへrebindする
- stale child、effect不一致、盤面変化、対象欠損では新規所有を解除し、親版へ安全に委譲する
- 不可逆なポフィンPLAY後に子promptを所有した場合、任意0枚が合法なら、曖昧時は`[]`を返してtransactionを完了する

## 必須trace

親版の`LAST_V1_PACKAGE_TRACE`または候補固有traceへ次をJSON-safeで追加する。

- rule:
  `V4_POFFIN_ROLE_CARDINALITY`
- parent action
- applied action
- `A`, `N`, `F`
- normal capacity、Abra final-slot exception
- role deficits before／after
- resolved candidate card ID／serial／semantic key
- selected cardinality
- `MAIN_PRESERVE_PARENT_POFFIN`
- `MAIN_VETO_ZERO_DEMAND`
- `CHILD_SELECT_0`
- `CHILD_SELECT_1`
- `CHILD_SELECT_2`
- fail-closed reason

非発火時の既存trace fieldsを消さない。

## focused fixture

少なくとも次を含む。

1. `A=0,N=0,F>=3`: ケーシィ＋ノコッチの2枚
2. `A=1,N=0,F>=2`: ノコッチ1枚
3. `A=0,N=1,F=1`: 最終枠ケーシィ1枚
4. `A=1,N=1,F=1`: 0枚
5. `A>=2,N>=2`: 0枚
6. `N=2`: 3体目ノコッチを拒否
7. 第二対象が存在しない: 1枚
8. `maxCount=1`: 1枚上限
9. option並べ替えでも同じserial集合
10. semantic duplicate／欠損serial／effect不一致／required minで親委譲
11. MAIN需要0でポフィン以外へ親score再順位付け
12. MAIN需要ありで親ポフィンactionを保存
13. 両owner鏡映
14. duplicate callback／stale child
15. 既存Hilda emergency reserveとv1/v3 transaction優先

## 回帰

- `88844273`の4 fixtureは親版と同じactionを維持する
- サイコドロー任意化と進化後確定KOの全重点テストを維持する
- candidate full suite成功
- parent full suite成功
- changed production/test source compile成功
- `deck.csv` 60枚、SHA不変

## 機構到達gate

固定7対面scheduleで次を必要とする。

- exact Poffin child context 30件以上
- 両seat
- 3 opponents以上、うち非ミラー2以上
- 提案0/1/2枚を各5件以上
- 親から変更またはMAIN拒否10件以上
- action error、transaction fault、stale abort 0

不足は`INSUFFICIENT_EVIDENCE`であり、採用ではない。

## 対戦採用gate

B0のroot検証済み`ABS_FLOOR`を候補結果より先に凍結する。
umbrella契約の全採用gateを使う。

機構到達、overall、Historical Silver、他6対面、seat、seed block、paired lower bound、schedule完全性の一つでも失敗したら、本変更を次段階へ継承しない。

本段階ではKaggle packageを作成しない。
