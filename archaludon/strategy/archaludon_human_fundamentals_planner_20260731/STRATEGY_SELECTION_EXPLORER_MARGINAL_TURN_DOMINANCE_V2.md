# Frozen strategy: EXPLORER_ALLOY_MARGINAL_TURN_DOMINANCE_V2

## 単一仮説

Explorer's Guidance の公開六枚から二枚を選ぶとき、完成可能な
`keep 2 -> discard 4 -> Archaludon ex 進化 -> Assemble Alloy ->
必要なら手貼り -> 攻撃`
の全経路を列挙し、ターン目的の限界改善だけをハードな辞書順で比較する。

「経路が最後まで動く」だけでは採用しない。
親の二枚組を既定値とし、新しい二枚組が公開情報だけで親を厳密に支配するときだけ置換する。

ルール名は `EXPLORER_ALLOY_MARGINAL_TURN_DOMINANCE_V2` とする。

## 親と実装基盤

直接の行動親は次に固定する。

- `candidates/archaludon_purpose_first_pokegear_boss_transaction_v1/main.py`
- SHA-256:
  `558EE5DB29E001428B0D59813613FABEE8E15B96E422746C104BDFAB4DC22DB6`

`archaludon_explorer_alloy_attack_continuity_v1` は callback transaction の機械的な実装基盤としてだけ使ってよい。
同候補の SHA-256 は
`749862FFD92C4A917E37E832B4ABF6D600CFF6B8B12A0CDE18A45185CFFF1C47`
である。

v1 を行動親として包み、その誤った選択を後から部分的に veto してはならない。
最終 agent は直接の親を callback ごとにちょうど一回呼び、v2 が厳密に証明した行動だけを置換する。

## ハードな辞書順

候補経路は次の層を上から順に比較する。
固定点や加点スコアへ変換しない。

1. 合法性、エンジン強制、確定済み結果、開始済み transaction。
2. 今ターンの確定勝利。
3. 公開情報だけで証明できる確定敗北の回避。
4. 今ターンに取る即時 Prize 数。
5. 攻撃解決後の現在攻撃結果。
6. 最初の異なる攻撃可能な控えを一体作ること。
7. 公開された具体的用途を持つ資源の保存。
8. 完全に意味が同じなら親の二枚組。
9. カード ID と役割が同じ物理コピー間だけ serial 昇順。

上位層が異なるなら、下位層を理由に逆転させない。
上位層が同じで下位層が比較不能なら、親の二枚組へ戻る。

## 即時 Prize

終端勝利だけでなく、通常の即時 Prize を独立したハード層にする。

- `P1` は `P0` より上。
- `P2` は `P1` より上。
- 今ターンの Prize が同じ場合だけ、攻撃後のダメージ、継続効果、控え、資源へ進む。

`episode_87658443_replay.json`、seat `1`、turn `4` では、Bench 育成と
Hammer In `30/P0` を維持する経路より、Active を進化して
Metal Defender `190/P1` を取る経路を選ぶ。

## 現在攻撃の実効結果

printed damage ではなく、公開効果レジストリを通した attack certificate を比較する。

最低限、次を一つの結果として扱う。

- KO と Prize。
- 実効ダメージと残り HP。
- Weakness、Resistance、Full Metal Lab。
- 攻撃無効、ダメージ無効、Sturdy。
- 自傷、反射、攻撃後の energy discard。
- Metal Defender の弱点消去。
- Turbo Flare の解決可能な加速。
- Coated Attack の保護。
- 相手 Active が任意に手札へ戻る公開効果。

Active を進化させる候補が、現在の合法攻撃より Prize、KO、実効ダメージ、
または確定した攻撃後効果を悪化させる場合は置換しない。

`episode_87738210_replay.json`、seat `1`、turn `8` では、
Mysterious Rock Inn により Metal Defender が `0` になるため、
Hammer In `30` を失う Active 進化経路を veto する。

効果が未登録、テキスト不一致、または比較不能なら親へ戻る。

## 控えの限界価値

控えの価値は、攻撃可能な異なる次アタッカーが `0 -> 1` になる場合だけ正にする。

攻撃可能とは、公開盤面だけで次をすべて証明できることをいう。

- Active と異なる物理 serial。
- 進化 lineage と進化可否が正しい。
- 保存した chosen backup attack のエネルギー支払いが完了している。
- Active が倒れた後、通常の昇格で Active になれる。
- 公開効果により攻撃が不可能にならない。

すでに異なる攻撃可能な控えが一体以上いる場合、二体目以降の追加 ready attacker は
この層では価値を増やさない。
上位層を改善せず、保護資源を失う追加育成は行わない。

`episode_88242194_replay.json`、seat `1`、turn `4` では、三エネルギー付き
Archaludon ex の控えがすでにいる。
別の Duraludon をさらに進化させるために Boss、Explorer、Lillie を捨てる経路を veto する。

## 公開資源の役割支配

カード枚数、固定点、serial の大小ではなく、そのターンと公開された次ターンに接続できる具体的役割を記録する。

少なくとも次の役割を区別する。

1. この経路で必要な Archaludon ex。
2. 手貼りに必要な Basic Metal Energy。
3. Assemble Alloy の燃料として捨てる Basic Metal Energy。
4. 公開された確定 Prize を取る Boss。
5. Night Stretcher の合法な回収対象と、回収後の具体的経路。
6. Lillie による無条件の次ターン手札改善。
7. Explorer による次ターンの手札選択と鋼 discard。
8. Ultra Ball、Poké Pad、Pokégear の合法な検索対象と、検索後の具体的経路。
9. Cinderace や Duraludon の、公開盤面から到達可能な進化または攻撃経路。
10. Hero's Cape、Jumbo Ice Cream、Full Metal Lab の、被 KO ターンまたは
    Prize race を実際に変える公開効果。

役割が同じ戦闘結果を保ったまま一方にだけ追加されるなら、その資源集合が厳密に優越する。
異なる生きた役割どうしは比較不能とし、親へ戻る。
公開盤面から到達できない setup-only カードは、生きた役割を持つカードを上回らない。

`episode_87658981_replay.json`、seat `1`、turn `5` では、
同じ Turbo Flare と Alloy 配分を成立させる
`Night Stretcher + Lillie`
を、
`Cinderace + Night Stretcher`
より優先する。
当該盤面の Cinderace は公開された到達可能用途がなく、Lillie には無条件の次ターン手札改善がある。

`unused_kept` の個数、card ID の固定点、または物理 serial でこの比較を代用しない。

## 親の既定値と厳密支配

親が選んだ二枚組についても、同じ公開 successor を可能な範囲で構築する。

- 親経路の攻撃まで完全投影できる場合、候補は上記辞書順で親を厳密に支配する必要がある。
- 親経路の一部しか投影できない場合、未確定部分を候補に有利に扱わない。
- 比較不能なら親を返す。
- 親二枚組と候補二枚組が意味同値なら親を返す。

「候補が合法だから」または「候補が攻撃できるから」は置換理由にならない。

## 必須 veto

次の場合は新しい reveal override を行わない。

- Active 進化後の実効攻撃結果が現在攻撃より悪い。
- 即時 Prize を失って控えだけを育てる。
- 異なる攻撃可能な控えがすでにいるのに、上位層を改善せず追加控えを育てる。
- 具体的用途のある資源を、用途のないカードまたは余分な控えのために失う。
- 公開効果、カードテキスト、対象、物理 identity、進化 lineage が未確定。
- 確定敗北回避を主張するのに公開 reply graph が不完全。
- 相手の非公開手札、山札上、Prize の ID を仮定する。
- supporter、turn、result、seat、owner、保存した serial が変化した。
- 親と候補の役割集合が比較不能。

## callback と fail-closed

v1 で確認済みの callback transaction、identity 保存、duplicate 再束縛、
攻撃ログ確認、親 owner 隔離、rollback を保持する。

ただし、v1 の certificate 選択結果をそのまま受け入れない。
reveal callback で v2 の辞書順と厳密支配を再計算し、その certificate だけを保存する。

どの段階でも certificate を再証明できなければ、その callback の genuine parent action へ戻り、
v2 transaction を終了する。

## telemetry

v1 の telemetry に加えて、少なくとも次を別々に数える。

- `terminal_win_dominance`
- `forced_loss_avoidance_dominance`
- `immediate_prize_dominance`
- `current_attack_effect_dominance`
- `first_ready_backup_gain`
- `redundant_backup_veto`
- `active_attack_degradation_veto`
- `resource_role_dominance`
- `resource_role_incomparable_fallback`
- `parent_not_strictly_dominated_fallback`
- `semantic_copy_tiebreak`

## focused negatives

最低限、次を両席または意味同値な両席 fixture で固定する。

1. `87658443`: P0 の控え育成より Active 進化 P1。
2. `87738210`: Hammer In `30` を Inn による Metal Defender `0` へ悪化させない。
3. `87658981`: 同一攻撃なら setup-only Cinderace より Lillie を残す。
4. `88242194`: ready backup がすでにいるとき三体目を資源損で作らない。
5. 現在 KO と進化後 KO が同じ場合、攻撃後防御と資源が比較不能なら親へ戻る。
6. 二枚組の生きた役割が異なり比較不能なら親へ戻る。
7. 未登録の相手効果が攻撃結果へ関与するなら親へ戻る。
8. 同 ID、同役割の物理コピーだけが違う場合だけ serial で決める。

## 自然履歴 gate

v1 と同じ `207` replay、`209` 対象席、`387` Explorer PLAY を使う。

- 上記四つの不合格例が期待どおり修正される。
- v2 が変更する全位置を人間プレイとして監査する。
- 即時 Prize 低下、実効攻撃低下、余分な ready backup、資源役割の逆支配:
  `0`
- invalid、exception、stale、owner collision:
  `0`
- certificate は両席で自然発火する。

発火件数を増やすために比較不能 fallback を弱めない。

## 実エンジン gate

Explorer PLAY から攻撃ログまで、fresh process、固定 seed、両席で確認する。

- Active を進化して即時 Prize を増やす経路。
- 現在攻撃を悪化させる Active 進化の veto。
- `0 -> 1` の ready backup 作成。
- 既存 ready backup があるときの追加育成 veto。
- 資源役割で厳密支配できる reveal 選択。
- 資源役割が比較不能なときの親 fallback。
- duplicate callback の意味同一。

invalid、exception、stale、owner collision は `0` とする。

## 採用範囲

この v2 が focused test、自然履歴、人間プレイ監査、実エンジン gate を通れば、
Explorer 一項目の安全な開発親候補にできる。

Trainer 全体、setup、Prize race、相手手札推定、全カード効果、Kaggle 強度が完成したとは扱わない。
幅広い基本プレイの TODO は未完了のまま残す。
