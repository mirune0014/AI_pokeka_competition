# Frozen strategy: EXPLORER_ALLOY_ATTACK_CONTINUITY_V1

## 選定

次の単一仮説は、
`EXPLORER_ALLOY_ATTACK_CONTINUITY_V1` とする。

Explorer's Guidance の使用、公開6枚からの2枚選択、鋼エネルギーの捨て札化、
Archaludon ex への進化、Assemble Alloy の配分、必要な手貼り、
そのターンの攻撃を、一つの決定的 transaction として扱う。

複数の無関係な Trainer ルールを同時に追加しない。
Explorer から攻撃継続までの一つの因果系列だけを所有する。

## 直接の親

- 親:
  `candidates/archaludon_purpose_first_pokegear_boss_transaction_v1/main.py`
- 親 SHA-256:
  `558EE5DB29E001428B0D59813613FABEE8E15B96E422746C104BDFAB4DC22DB6`

親全体を byte-identical prefix として一度だけ含める。
最終 `agent` は callback ごとにこの親をちょうど1回呼ぶ。

## 頻度の根拠

対象 corpus は次で固定する。

`live/55070349/refresh_20260729_1241/shadow_corpus_196_prior_plus_11_new`

- ファイル:
  `207`
- `TeamNames == "rurumi"` の対象席:
  `209`
- seat 0:
  `108`
- seat 1:
  `101`
- 対象席の type `10`、cardId `1185`、playerIndex が対象席と一致する
  Explorer PLAY ログ:
  `387`
- unique `(replay, seat, turn)`:
  `387`
- unique `(replay, seat, physical serial)`:
  `387`

Kaggle replay では、行 `r` の action は行 `r-1` の observation への応答である。
同じ行の action と observation を結び付けた `121` という値は誤りであり、
使用しない。

この `387` は自然な使用頻度であり、候補の発火回数や強度ではない。
実装後に、正しい対象席だけで候補 certificate の自然発火を別に集計する。

## 人間プレイヤーとしての目的

Explorer を「使える Supporter」だから使うのではない。
使用後に次のどれを成立させるかを固定する。

1. `MAKE_ACTIVE_ATTACK`
   - Active Duraludon を Archaludon ex に進化する。
   - Explorer で鋼を捨てる。
   - Assemble Alloy と必要な手貼りで、選んだ攻撃をこのターンに使う。
2. `READY_BACKUP_KEEP_CURRENT_ATTACK`
   - 現在の Active の確定攻撃を維持する。
   - Bench Duraludon を Archaludon ex に進化する。
   - 捨てた鋼を次アタッカーへ付ける。
   - 最後は元から選んだ現在の攻撃を行う。
3. `RESTORE_ATTACK_CONTINUITY`
   - 現在の攻撃が不足している。
   - Explorer、進化、Alloy、必要な手貼りの公開された組合せで、
     このターンの合法攻撃を新しく成立させる。

Explorer 使用前の top 6 は未知である。
親が Explorer を使ったことだけを、top 6 の中身を知っていた証拠にしない。
transaction は親が Explorer PLAY を選んだ時点で監視を開始し、
公開後に上記目的が証明できた場合だけ行動を置換する。
公開後に証明できなければ、その callback の合法な親行動へ戻り、
新しい強制継続は開始しない。

## ハードな優先順位

次をスコアにしない。

1. エンジン強制、合法性、結果確定。
2. 現在の確定勝利。
3. 現在の確定敗北を回避する既存取引。
4. 既に開始済みの親 transaction。
5. 開始済みの本 transaction。
6. 新しい Explorer 監視。
7. 親の行動。

現在の確定勝利や既存の敗北回避より Explorer を優先しない。
scalar score、固定加点、カードIDだけの順位は使わない。

## 開始条件

普通の MAIN callback で、親が物理的に一意な Explorer's Guidance を
PLAY するときに、監視 transaction を開始する。

必要条件:

- current result は未確定。
- 自分の手番。
- Supporter は未使用。
- Explorer の card ID、物理 serial、公開テキストが完全一致。
- 選択肢中の該当 Explorer PLAY は一意。
- 現在の Active、Bench、手札、捨て札、残り Prize、deckCount、
  energyAttached、stadium、turn、seat を snapshot に保存できる。
- 親または他の final-layer transaction の owner がいない。
- 親が既に確定勝利、確定敗北回避、強制 action を返していない。

この段階では top 6 の内容を推定しない。

## 公開6枚の2枚選択

Explorer の公開カードが完全に観測でき、効果テキストと枚数制約が一致したら、
合法な2枚組をすべて列挙する。

各組合せについて、残り4枚が捨て札になることを正確に反映し、
次の公開経路を最後の攻撃まで投影する。

- 手札に残る Archaludon ex。
- Explorer 前から手札にある Archaludon ex。
- このターン進化可能な Active または Bench Duraludon。
- 捨て札に新しく入る Basic Metal Energy の物理 serial。
- Explorer 前から捨て札にある Basic Metal Energy。
- Assemble Alloy で付けられる最大2枚。
- 未使用なら手貼りできる手札の Basic Metal Energy 1枚。
- 現在の攻撃と、進化後に使える攻撃。
- 現在 Active の攻撃を壊さずに作れる次アタッカー。

組合せの辞書順は次とする。

1. このターンの確定勝利を成立・維持する。
2. このターンの合法攻撃を成立・維持する。
3. 現在の攻撃を変えず、次アタッカーを攻撃可能にする。
4. 必要な Archaludon ex を手札へ残す。
5. 必要数の鋼を捨て、Alloy の有効付与枚数を増やす。
6. 現在攻撃と次アタッカーに不要な資源を多く残す。
7. 完全同値なら、親が選んだ2枚組。
8. それも同値なら、物理 serial の昇順。

「鋼だから取る」または「鋼だから捨てる」と固定しない。
手貼りに必要な鋼は取る。
Alloy に必要な鋼は捨てる。
2枚取ることで攻撃経路を壊すなら、その組合せを選ばない。

どの組合せも上記3目的のどれも完遂できない場合、
親の2枚選択をそのまま返し、transaction を終了する。

## 保存する identity

少なくとも次を保存する。

- seat、turn、Explorer serial。
- reveal された各カードの ID と serial。
- 取る2枚と捨てる4枚。
- 目的。
- 進化対象 Duraludon serial。
- Archaludon ex serial。
- 付与する鋼 energy serial と対象 Pokémon serial。
- 手貼りする場合の energy serial と対象 serial。
- 最後の attacker serial と attack ID。
- Explorer 前の current attack certificate。
- Explorer 後の chosen attack certificate。
- 親 owner の開始前 snapshot。

同じIDの別カードを代用しない。

## callback stages

少なくとも次の段階を持つ。

1. `EXPLORER_PLAY_EMITTED`
2. `REVEAL_CHOICE_EMITTED`
3. `EXPLORER_RESOLVED`
4. `EX_EVOLVE_EMITTED`
5. `ALLOY_YES_EMITTED`
6. `ALLOY_ENERGY_SELECTION_EMITTED`
7. `ALLOY_TARGET_ALLOCATION_EMITTED`
8. `MANUAL_ATTACH_EMITTED` または `MANUAL_ATTACH_SKIPPED`
9. `ATTACK_EMITTED`
10. `COMPLETE`

エンジンが一つの callback で複数段階を解決する場合、
実際のログと current state で複数段階をまとめて確認してよい。
実装都合で契約を弱めてはならない。

## エネルギー配分

Assemble Alloy は最大2枚を任意の鋼ポケモンへ付ける。

配分のハード順:

1. このターンの chosen attack に不足する分を満たす。
2. 現在の chosen attack が既に払えるなら、次アタッカーの
   chosen backup attack に不足する分を満たす。
3. どちらの攻撃閾値も変わらない過剰付与を強制しない。

手貼りのハード順:

1. 手貼り1枚でこのターンの chosen attack が払えるなら現在 attacker。
2. 現在攻撃が既に払え、手貼り1枚で次アタッカーの攻撃可能ターンが
   1ターン縮むなら次アタッカー。
3. どちらでもなければ本 transaction は手貼りを強制しない。

## 進化と攻撃

- Active Duraludon を進化して攻撃を作る経路と、
  Bench Duraludon を進化して現在攻撃を維持する経路を両方扱う。
- `appearThisTurn` と進化元 lineage を正確に確認する。
- ex 進化で現在の合法攻撃が失われる場合は置換しない。
- Alloy 解決後と手貼り後に、chosen attack の支払いを毎回再証明する。
- 最後は保存した attacker serial と attack ID が一致する攻撃だけを選ぶ。
- 攻撃ログは、seat/turn stale 判定より先に確認する。
  攻撃とターン更新が同じ search step で起こるためである。

## fail-closed と衝突

- hidden opponent hand のIDを使わない。
- 相手の未知の top deck や未公開 hand を仮定しない。
- カードテキスト、callback、対象、枚数、物理 identity が不明なら親へ戻る。
- Adrena-Brain の未対応変種など、公開効果レジストリが不完全なら親へ戻る。
- 親 owner が開始前から存在するなら本 transaction を開始しない。
- 本 transaction 中に親呼び出しが新しい owner を作った場合、
  開始前 snapshot と比較し、新しく作られた owner だけを隔離する。
  開始前からあった owner を消してはならない。
- 失敗時は本 transaction を消し、同じ pre-call observation から得た
  genuine unquarantined parent action を返す。
- duplicate callback は同じ意味行動を返し、counter を二重計上しない。
- unknown、exception、invalid action では親へ戻り、telemetry を残す。

## telemetry

少なくとも次を数える。

- observed Explorer PLAY。
- monitor starts。
- reveal callbacks。
- feasible combination count。
- purpose ごとの certificate starts。
- reveal override。
- ex evolve。
- Alloy YES。
- Alloy energy selection。
- Alloy target allocation。
- manual attach current / backup / skipped。
- attack。
- complete。
- reveal no-route fallback。
- parent owner collision。
- metadata rejection。
- hidden/unsupported rejection。
- duplicate。
- stale。
- invalid action。
- exception。
- rollback reason。

保存則:

`starts = completes + settled_fallbacks + live_transactions`

を満たす。

## focused tests

両席で最低限、次を確認する。

1. Active Duraludon、既存1鋼、reveal に ex と2鋼があり、
   鋼を捨てて ex を取り、進化、Alloy 2枚、攻撃まで完遂する。
2. 現在 Active は既に攻撃可能、Bench Duraludon があり、
   ex と鋼を使って backup を作り、最後は元の Active が攻撃する。
3. ex は既に手札にあり、reveal の鋼を捨てて同じ経路を完遂する。
4. Alloy 後に手貼り1枚だけで現在攻撃が成立する。
5. 現在攻撃は成立済みで、手貼りが backup の準備ターンだけを縮める。
6. 鋼を取る必要がある組合せと、鋼を捨てる必要がある組合せを各1件。
7. route がない reveal では親の2枚選択へ戻る。
8. eligible Duraludon がない。
9. ex が取得不能。
10. 進化したばかりなど、進化不能。
11. Supporter 使用済み。
12. terminal attack と exact-loss-avoidance が Explorer より優先される。
13. hidden opponent hand を変えても行動が変わらない。
14. 同ID複数枚、option reorder、duplicate callback。
15. 親 owner の開始前存在と、開始後の新規 owner collision。
16. attack log と turn advance が同時に起こる。

## 自然履歴 shadow

正しい対象席だけを使う。

- `TeamNames == "rurumi"` を対象とする。
- self-play で両方が `rurumi` のときだけ両席を対象とする。
- replay の action は1行前の observation への応答として扱う。
- Explorer 使用は type `10` の PLAY ログでも独立確認する。
- 全387使用について、親と候補の最初の差、目的、完遂/rollback、
  invalid、exception、owner collision を記録する。

positive certificate は、最低20 unique `(replay, seat, turn)`、
かつ両席で自然発火することを目標とする。
未達なら発火条件が狭すぎる可能性を明記し、
安全性だけで `[x]` にしない。

## 実エンジン gate

seed を固定し、fresh process で再現する。

- 両席。
- Active を作る経路と backup を作る経路を各1件以上。
- Explorer PLAY から攻撃ログまで最低4 transaction。
- duplicate を各経路で1回以上。
- 出力を2回実行し byte-identical。
- invalid action、exception、owner collision、stale:
  `0`

## 採用範囲

focused test、正しい対象席の自然 shadow、実エンジン gate を通れば、
次の開発親として採用できる。

この段階では broad win-rate 改善や Kaggle 提出を要求しない。
ただし、破綻、違法行動、親 transaction の破壊、自然発火0、
または attack 未完遂があれば採用しない。

この候補だけで Trainer 全体の基本プレイが完成したとは扱わない。
Explorer 項目だけを `[x]` または `[-]` に更新し、
他の Trainer、setup、Prize race は未完了のまま残す。
