# v2 fix5 一意なベンチフーディンへの手張り後KO契約

## 状態

この文書は、比較Bの独立数値監査とSol-Ultra戦略判定を通過した後に固定する、v2の単一変更契約である。

規則名は`V2_H1_UNIQUE_BENCH_ALAKAZAM_ATTACH_THEN_KO`とする。

この契約は実験開始を許可するが、v2の採用を意味しない。

既存の`alakazam_newdeck_v2_continuity`と`v2_certified_h1_continuity_contract.md`は失敗済みの`SUPERSEDED_NO_GO`証跡である。

旧v2のplanner、model、transaction、fixtureをimport、copy、部分移植してはならない。

## 凍結入力

- repository commit at branch start:
  `54f09edb2b3f6dd2def7c2c49efde16dfeda97c9`
- branch:
  `codex/alakazam-staged-development`
- v1 source:
  `alakazam_staged_20260729/versions/alakazam_newdeck_v1_package_runtime_certified_fix5`
- v1 policy closure SHA-256:
  `5FFA8776CA95E16C7030C55B5682DE42BA21C06964C790A3D6312B60FBAA5009`
- v1 planner SHA-256:
  `80A9B0F88A04591D4174B21AFCC5C9019A4EFCEC02E8F9C2D1576DCFC0FC044B`
- raw deck SHA-256:
  `F598F5E578D0440C96DC0492EAECF2E19739B7A23225BE57114A724EF7D0FB94`
- normalized deck hash:
  `4414e8995e50c7a00d4b6aa7d9229f63c1dff5261643ec7cd86c4e329113ed69`
- comparison B immutable spec SHA-256:
  `43632474EFD532E6632A5C0C6AC45D5D958BB15FAE840EAF77A2D718BDB1733D`
- comparison B paired rows SHA-256:
  `40CC9DBD57DF0826EA645FFB860BA976AD9B30E91209B337F1117073DBDCDE57`
- comparison B combined manifest SHA-256:
  `BE908376D654A36AFD1193C8D66D2ABA340658202E03C9B103845EF3CCAD14A5`
- comparison B root recomputation SHA-256:
  `C921E31583622CCFF39DF36549037779AD4EC1ACD9A57B3F194A592EA86A87A3`
- comparison B first-divergence CSV SHA-256:
  `127DD17D468DE5215496A41F68D27729A69DACA321C4393D1D5540A270CDA053`
- formal v1 suite manifest SHA-256:
  `0785538138716F87723AD0A025E375E5408F0DED5112F4309B6BD7468F9B6847`
- formal v1 game metrics SHA-256:
  `A95FA44026DA8A7B4FF5D30536F3F4980CEC7BF17BED18F6DD926A92578394F4`
- formal v1 checked join SHA-256:
  `7D406323FD8F9861EF35C95FAE10A81910CB6CFF949B410401966F7E57055883`

比較Bはv0の428/700勝からv1の451/700勝へ23勝増えた。

対応付きgain/lossは35/12で、両側exact sign testは`p=0.0010885382064742544`だった。

独立監査では、700キーの一意性、schedule一致、baseline duplicate一致、formal join一致、安全異常0を再確認した。

比較Bはv2実験へ進む条件付きPASSであり、v1またはv2の最終採用判定ではない。

## 単一仮説

現在ActiveのAlakazamが非終局のPowerful Hand KOを確定している局面に限り、既存Benchの一意なAlakazamへ1枚の超エネルギーを手張りする。

手張り後も現在KOに必要な手札床を維持し、同じターンに同じActiveから同じ対象をPowerful Handで倒す。

この一手によって、現在攻撃者が倒された後に攻撃可能な2体目のAlakazamを用意する。

v2はAbraの展開、進化、回収、retreat、promotion、対面別分岐、複数ターン復旧を新規実装しない。

ID19のoptional searchでは必ず空選択し、追加のAbraを探索しない。

## 変更境界

変更を許可するのは、v1 sourceを複製した隔離destination内の次だけとする。

- 外側entry pointの`main.py`
- 新規の独立v2 planner
- 新規のv2 tests

`planner_deck_adaptation_v1.py`を含むfix5 v1 core、`deck.csv`、`runtime/main.py`、既存v1 testsを変更してはならない。

v2の非発火時は、v1が返した同じaction objectをそのまま返す。

v1 trace、v1 transaction、v1 duplicate cache、core transaction、core duplicate cache、duplicate order、trace log、latest trace、parent mutable stateを変更してはならない。

## 所有順位

進行中のv2 transactionがないcallbackでは、wrapperはfix5 v1を正確に1回だけ呼ぶ。

次のいずれかがcall前またはcall後に成立する場合、v2は完全にdeferする。

- v1の`selected_rule`が非null
- v1 transactionがactive
- integrated transactionがactive
- parent ownerがactive
- inheritedまたはv1 duplicate ownerがactive
- v1 traceにterminal、fault、removed-card filter、irreversible abortが記録される
- Boss、Xerosic、Hammer、Lana、Alakazam、Nighttime Mineのstart、child、verifyが所有する

進行中のv2 transactionは、attach child、attach verify、attack dispatch、attack resolution verifyだけを所有する。

v2 transaction中に新しいv1 ownerが現れた場合は、不可逆faultとして記録してfail closedする。

## 発火条件

次の条件をすべて満たす場合だけ発火する。

1. raw observationとparsed observationが完全に一致する。
2. `MAIN`の完全なpublic envelopeである。
3. option censusとstable option keyが完全で一意である。
4. v1が返したaction objectが、一意なPowerful Hand `1072`である。
5. Activeは公開情報が完全なready Alakazam `743`である。
6. 自分のasleep、paralyzed、confusedはすべてfalseである。
7. 相手ActiveへのPowerful Hand効果が公開情報上完全にclearである。
8. 現在のPowerful Handが相手Activeを正確にKOする。
9. このKOは終局ではない。
10. 相手Benchが存在する。
11. `Hreq = ceil(opponent_active_hp / 20)`とする。
12. 自分の公開手札が完全で、`handCount - 1 >= Hreq`である。
13. 今ターンのEnergy attachが未使用である。
14. BenchのAlakazam `743`が正確に1体である。
15. そのBench AlakazamのPowerful Hand cost不足が正確にPsychic 1個だけである。
16. Basic Psychic Energy `5`またはTelepath Psychic Energy `19`を1枚だけ仮想装着すると不足が0になる。
17. 対象Alakazam、source Energy、ATTACH optionを結ぶ適格routeが正確に1件である。
18. source Energyの`id`、`serial`、`owner`が完全で一意である。
19. target Alakazamのtop、進化stack、Energy、Toolのserialが完全で一意である。
20. ATTACH optionのtype、area、hand index、inPlayArea、inPlayIndex、stable keyが完全一致する。

複数の適格Energy、複数の適格option、複数のBench Alakazam、owner曖昧、serial重複、metadata不明では発火しない。

ID5はBasic Psychic Energyとしてのmetadataが完全一致しなければならない。

ID19はTelepath Psychic Energyとして、name、card type、energy type、skill name、skill textが完全一致しなければならない。

## transaction

transaction開始時に次を凍結する。

- owner
- turn
- start public state
- v1 attack action objectとstable key
- Active Alakazamのid、serial、完全fingerprint
- targetのid、serial、HP、完全fingerprint
- `Hreq`
- start hand count
- source Energyのid、serial、owner、完全card row
- target Bench index
- target Alakazamの完全fingerprint
- ATTACH optionのstable key
- protected serial集合

発火時は、v1 call前に保存したparent、core、v1 mutable stateへ復元してからv2 transactionを開始する。

### Basic Psychic Energy

Basic Energy attach後の次MAINで、次をすべて検証する。

- turnは不変
- action countは正確に1増加
- `energyAttached`はfalseからtrue
- hand countは正確に1減少
- own handから凍結Energy rowだけが消える
- 同じEnergy rowが凍結Bench Alakazamへ正確に1枚増える
- Active、target、他のBench、prize、discard、deck count、stadium、statusは許容差分以外不変
- attach logのplayer、Energy id、serial、target id、target serialが完全一致
- 手張り後も`handCount >= Hreq`
- Bench AlakazamのPowerful Hand cost不足が0

### Telepath Psychic Energy

Telepath attach直後のchildは、完全なoptional `TO_BENCH` envelopeでなければならない。

`minCount`は0でなければならない。

effectまたはcontext cardは凍結したTelepath rowと完全一致しなければならない。

option census、deck、area、player、card serialを検証した後、必ず空action `[]`を返す。

Abraを探索してはならない。

その後のMAINで、Basic Energyと同じattach deltaに加えて、deck countが変化していないことを検証する。

## attack完遂

attachを検証した同一turnのMAINで、wrapperはfix5 v1を正確に1回だけ呼ぶ。

v1自身が、同じActive Alakazamから同じPowerful Hand `1072`を一意に選ぶ場合だけ、その同じaction objectを返す。

別のv1 rule、transaction、owner、target mutation、手札床違反、Powerful Hand不成立が現れた場合はfault-abortとする。

attack返却前に、fix5の`_arm_attack_resolution`と同等以上の完全なpublic proofを保存する。

次callbackで、fix5の`_exact_attack_resolution`を用いて次を完全検証する。

- 同じattacker serial
- 同じtarget serial
- 期待damage-counter log
- target top、進化stack、Energy、Toolの正確なdiscard移動
- 正確なprize prompt
- action count、turn、status、hand、boardの許容差分

attack resolutionを検証した後だけtransactionをcompleteとする。

complete callbackの選択は、v2をresetした後にfix5 v1へ1回だけ委譲する。

## trace

`LAST_V2_CONTINUITY_TRACE`へ最低限、次を記録する。

- public snapshot hash
- context
- selected action
- selected rule
- stage
- reason tags
- transaction outcome
- transaction abort reason
- irreversible abort fault
- H0 attacker serial
- H1 Alakazam serial
- Energy idとserial
- target serial
- `Hreq`
- start handとfinal hand
- attach verified
- attack dispatched
- KO resolved

Reason Codeは次に固定する。

- `V2_H1_UNIQUE_BENCH_ALAKAZAM_ATTACH_THEN_KO`
- `V2_H1_ATTACH_BASIC_PSYCHIC`
- `V2_H1_ATTACH_TELEPATH_PSYCHIC`
- `V2_H1_TELEPATH_EMPTY_CHILD`
- `V2_H1_ATTACH_VERIFIED`
- `V2_H1_POWERFUL_HAND_DISPATCHED`
- `V2_H1_KO_RESOLVED`
- `V2_H1_H_FLOOR_BLOCK`
- `V2_H1_NON_UNIQUE_ROUTE`
- `V2_H1_METADATA_UNPROVEN`
- `V2_H1_PUBLIC_MUTATION_ABORT`
- `V2_H1_IRREVERSIBLE_ABORT_FAULT`
- `V2_DEFER_V1_OWNER`
- `V2_BASELINE_FALLBACK`

## 必須試験

既存fix5の146 testsをbyte-identical source上で全件通す。

新規試験は最低限、次を含める。

- Basic Psychicのfull chain正例
- Telepathのempty childを含むfull chain正例
- `H-1 == Hreq`の境界正例
- `H-1 < Hreq`の負例
- terminal KOの完全defer
- Boss、Xerosic、Hammer、Lana、Alakazam、Mineのstart、child、verify完全defer
- active v1 transaction、parent owner、duplicate ownerの完全defer
- Bench Alakazam 0体、2体以上の負例
- 既にreadyなBench Alakazamの負例
- 不足Energyが0、2以上、Psychic以外を含む負例
- 適格Energy 0枚、2枚以上の負例
- option 0件、2件以上、reordered、duplicate stable keyの負例
- card metadata、skill text、owner、serial、hand index、Bench index mutation
- attach後のhand、deck、discard、prize、active、target、他Bench mutation
- Telepath childのminCount、effect、contextCard、deck mutation
- attack log、damage、target movement、prize prompt mutation
- duplicate callbackの同一action再束縛
- 不可逆attach後の全abortがfaultとして記録されること
- 非発火時のaction object identity
- 非発火時のv1 trace、v1/core/parent全mutable stateの深い同一性
- 同じchanged fixtureを3回反復したactionとtraceの一致

## Comparison C前のhard gate

- fix5 v1 coreとdeckがbyte-identical
- 既存146 testsと新規testsがすべて成功
- compile error 0
- invalid action 0
- exception 0
- timeout 0
- max-step hit 0
- transaction start、attach verified、attack dispatched、KO resolvedが一対一
- pending transaction 0
- owner conflict 0
- active rule switch 0
- irreversible abort fault 0
- generic fallback 0
- first-legal fallback 0
- nonfire state difference 0

## Comparison C

Comparison Cは、v1 fix5対v2の独立holdoutとする。

- seed bases:
  `202608600, 202608610, 202608620, 202608630, 202608640`
- seeds:
  `202608600..202608649`
- opponents:
  7
- seats:
  `0, 1`
- games per cell:
  `10`
- paired rows:
  `700`
- manifest rows:
  `210`
- max steps:
  `1000`
- expected paired schedule SHA-256:
  `2D881C29FFD0E48A753499176594EA8406D22E5CDB10D6BA8BD3C481743EA9F4`
- expected manifest schedule SHA-256:
  `9E635C0DEDB8BC32C04B781F861AED179D26B3264E5F58A607636E76F260AEFB`

比較Bの`202608500..202608549`をComparison Cへpoolしてはならない。

全バージョン同一seed表のため、v2だけを`202608500..202608549`で別途実行する。

このaligned panelは比較Cのholdout結果へpoolしない。

## 発火分布gate

complete発火は20件以上必要とする。

complete発火は両seat、3 opponents以上、3 seed bases以上に分布しなければならない。

Historical-Silverで少なくとも1件のcomplete発火が必要である。

不足した場合は採用しない。

不足だけが理由で、他のhard gateがすべて成功している場合に限り、同じ規則を変更せず独立holdoutを追加できる。

## 採用条件

次をすべて満たす場合だけv2を採用する。

- v2は441/700勝以上
- v1 holdout比で10勝以上増加
- paired gainがlossを上回る
- 両側exact sign testが`p <= 0.10`
- Historical-Silverのdeltaが正
- Historical-Silverの両seatが非負
- 全体のseat 0とseat 1が各非負
- 他の各opponentのdeltaが-2勝以上
- gainが複数seed baseに分布
- 同じH1機序による反復lossがない
- 全complete発火でH-floor、現在KO、second-line readyが100%
- certified KO miss 0
- Telepathによるdeck消費0
- resource-floor violation 0
- common-opportunity paired post-KO continuityとsecond-line formationがともに非悪化
- common-opportunity paired post-KO continuityまたはsecond-line formationの少なくとも一方が改善
- attack-gap tailとbetweenが非悪化
- max consecutive attack turnsが非悪化
- realized opportunityから次攻撃への変換を複数bucketで確認

採用条件を一つでも満たさない場合はv2を棄却し、fix5 v1を最終候補とする。

小差だけ、Silver無発火、片seat依存、隣接population退行、安全fault、機序不一致は棄却理由とする。
