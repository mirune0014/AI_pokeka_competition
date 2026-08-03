# v4 C1 ポフィン fix3 静的レビュー修正契約

## 対象

- 親仕様:
  `alakazam_staged_20260729/specs/v4_c1_poffin_role_cardinality_fix3_immutable_spec.md`
- 実装候補:
  `alakazam_staged_20260729/versions/alakazam_newdeck_v4_poffin_role_cardinality_fix3`
- 修正対象:
  候補directory内の`planner_deck_adaptation_v1.py`と
  `test_v4_poffin_role_cardinality_fix3.py`だけ

本修正はC1の仮説、役割順、0/1/2枚上限、親identity、評価scheduleを
変更しない。正式な候補評価を開始する前の所有権・監査修正である。

## 修正1: 完了callbackを全仲裁へ戻す

`await_v4_poffin_complete`または
`await_v4_poffin_main_complete`で、同一子promptのduplicateではない
新しいcallbackを受けた場合、C1 transactionを解除した後、そのcallbackを
通常のv1/v3/C1/親仲裁へ一度だけ戻す。

そのcallbackで取得した親actionを直返ししてはならない。特に次を維持する。

- サイコドロー任意化
- 進化後確定KO
- current／terminal KO
- Boss、Mine、Lana、Hammer、Xerosic
- 継承planner transaction

再仲裁は同じraw observationを使い、親方策を二重実行しない。

## 修正2: 公開情報上の対象枯渇をMAINで拒否する

正確な60枚deck countと、自分の公開領域にあるphysical cardを用いて、
ケーシィ`741`とノコッチ`305`の未確認枚数を別々に計算する。

公開領域には少なくとも次を含む。

- hand
- discard
- Active／Benchのtop card
- Active／BenchのpreEvolution

serial重複、owner不一致、未知領域、deck count不整合ではこの追加証明を
使わず、既存のfail-closed方針へ戻す。

必要な役割に対応する両basicが公開情報上すべて枯渇している場合、
親がポフィンを選んでもMAINで拒否して親の残存optionを再順位付けする。

`A == 0, F == 1`の最終枠例外は、未確認ケーシィが1枚以上ある場合だけ
「候補があり得る」と扱う。

未確認cardがPrizeにあるかDeckにあるかは非公開である。そのため、
未確認枚数が正ならポフィンを保存してよい。子promptで対象0件だった場合は
不可逆なPLAY後の合法な`[]`を返し、
`HIDDEN_ZONE_TARGET_WHIFF`をtraceへ残す。非公開Prizeを推測しない。

## 修正3: filtered rerankのduplicate所有権

ポフィンを除いた親再順位付けがHilda等の継承transactionを新規成立させた
場合でも、元の未filter callbackについて、選んだsemantic actionを
duplicate cacheへ記録する。

元callbackが再送された場合は、同じphysical／semantic optionへrebindし、
親transactionを二重実行、誤解除、別optionへ変更しない。

## 修正4: rerank不成立時のfail-closed表現

filtered observation、親action、semantic rebindのいずれかを証明できない
場合は、任意のENDや別optionを作らず、元の認証済み親actionを保存する。

この場合は「拒否成功」と記録せず、次を明示する。

- classification:
  `MAIN_RERANK_UNCERTIFIED_PARENT_PRESERVED`
- fail reason:
  `PARENT_RERANK_NOT_CERTIFIED`

正式評価ではこの分類をtransaction faultとして数え、0件を要求する。

## 修正5: traceの時間軸を壊さない

ポフィンMAIN／子promptの`parent_action`と`applied_action`を、後続の別callback
のactionで上書きしない。

後続callbackの情報が必要なら、別fieldへ保存する。

- `completion_parent_action`
- `completion_applied_action`
- `completion_selected_rule`

`CHILD_SELECT_0/1/2`、selected cardinality、selected serial、A/N/Fは、
当該ポフィン判断時の値を維持する。

## 追加focused fixture

少なくとも次を追加する。

1. Poffin子選択完了直後の新規MAINで、進化後確定KOが通常どおり発火する。
2. Poffin子選択完了直後の新規promptで、サイコドロー任意化が維持される。
3. MAIN veto bookkeeping完了直後も、通常仲裁を飛ばさない。
4. ケーシィ／ノコッチが公開領域ですべて枯渇している場合、MAINでPoffinを
   拒否する。
5. 未確認cardが残るが子optionが0件の場合、合法な`[]`と
   `HIDDEN_ZONE_TARGET_WHIFF`を返す。
6. rerankがHildaまたは継承planner ownerを新規成立させた後、元callbackの
   duplicateが同じsemantic actionへrebindする。
7. rerank証明失敗時は元親actionを保存し、拒否成功と記録しない。
8. 完了callback後も元のPoffin action／cardinality／serial traceが不変である。

修正後にfocused、候補full、凍結親full、changed-source compileを再実行し、
親closureとdeck SHAの不変を確認する。正式simulationはその後に開始する。
