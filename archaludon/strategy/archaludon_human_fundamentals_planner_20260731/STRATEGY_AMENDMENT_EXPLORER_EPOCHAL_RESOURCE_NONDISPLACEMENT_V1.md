# Controlling amendment: EXPLORER_EPOCHAL_RESOURCE_NONDISPLACEMENT_V1

## 判定

`archaludon_explorer_alloy_marginal_turn_dominance_v2`
（SHA-256: `ED4DFBE95FC9A5D6AD3AFED111155D7279A4694A0E93ABD1283F5D009611660E`）には、時間軸を無視した資源置換と、親の合法なグッズ使用を飛ばす継続が残っている。

この amendment は、Explorer v2 の即時Prize、実効攻撃、最初の控え、ATTACK_DEPTH の hard tier を保持したまま、資源比較と same-parent-pair 継続だけを上書きする。

単一仮説名は `EXPLORER_EPOCHAL_RESOURCE_NONDISPLACEMENT_V1` とする。

## 資源役割の時間軸

すべての資源役割に次の epoch を付ける。

1. `ROUTE_NOW`
   - このターンの保存済み攻撃に不可欠な進化、Alloy、エネルギー、手張り、攻撃役。
2. `NOW`
   - Explorer 解決後、このターン中に合法に使える Trainer、特性、設置、回収、検索。
3. `NEXT_TURN`
   - Supporter 権や進化制限などにより、このターンは使えず、次ターン以降にだけ使える役割。

`NEXT_TURN` は、親が持つ `NOW` を支配できない。異なる role family も比較不能とする。

候補が資源役割で親を厳密支配できるのは、次をすべて満たす場合だけである。

- 現在ターンの戦闘結果が同じ。
- 親の各 protected role を、同じ role family、同じ公開目的、同じかそれ以前の epoch で保存する。
- 候補だけが追加の生きた役割を持つ。
- 他の資源、Bench 容量、即時Prize露出、攻撃深度を悪化させない。

カード名、枚数、固定 serial だけでこの判定を代用しない。

## 親が選んだ現在合法な Trainer の保護

普通の `MAIN` で direct parent が現在合法な Trainer PLAY を選び、その公開された正の目的が親処理から確認できる場合、次の役割として保護する。

`NOW_PARENT_TRAINER_OPPORTUNITY(card_id, action_semantics)`

山札内の exact target を確定する必要はない。ただし、対象の非公開性だけを理由に「その Trainer は無価値」と判定してはならない。

## same-parent-pair の継続権

親と同じ二枚組を選んだことは、その後の行動を最後まで強制する権限ではない。

各 callback で direct parent を一度呼び、親の現在行動と候補の次行動を比較する。次をすべて満たす場合、Explorer transaction を clear し、genuine parent action へ handoff する。

- 候補の攻撃が終端勝利ではない。
- 親に対する確定敗北回避の厳密改善ではない。
- 親または現在攻撃に対する即時Prizeの厳密増加ではない。
- 候補は同じ攻撃を、親行動後も壊さず継続できる。
- 親が現在合法な positive-purpose Trainer を選んでいる。

単に `immediate_prize_yield > 0` であるだけでは、親 Trainer を飛ばす理由にならない。親または現在攻撃に対する strict hard delta が必要である。

handoff 後を rollback と呼ばず、`NOW_PARENT_TRAINER_HANDOFF` として記録する。

## 必須fixture

### `88479736`, seat 1, turn 5

- 親: Poke Pad `79` を今使う。
- 旧候補: Metal Energy `112` を手張りして攻撃。
- どちらも同じ `P1` KO を継続できる。
- 期待: `PARENT_FALLBACK:now_parent_trainer_nondisplacement`。
- Poke Pad を飛ばさない。

### `88681773`, seat 0, turn 4

- 親: Archaludon ex `9` + Poke Pad `16`。
- 旧候補: Archaludon ex `9` + Explorer `42`。
- Pad は `NOW`、Explorer は Supporter 使用済みのため `NEXT_TURN`。
- 期待: reveal で親へ fallback。

### `87663229`, seat 0, turn 8

- 親: Archaludon ex `7` + Boss `41`。
- 旧候補: Archaludon ex `7` + Lillie `47`。
- 同じ `P0/190`。Boss と Lillie は異なる `NEXT_TURN` role family。
- 期待: resource-role incomparable で親へ fallback。

### `88356203`, seat 0, turn 6

- 親: Poke Pad `16` + Lillie `49`。
- 旧候補: Boss `39` + Lillie `49`。
- 同じ `P0/220`、同じ追加 attack depth。
- Pad は `NOW`、Boss は Supporter 使用済みで `NEXT_TURN`。
- 期待: reveal で親へ fallback。

## 保持する正例

次の四件は、親または現在攻撃より即時Prizeを厳密に増やしたため保持する。

- `87658443`
- `87673473`
- `87773965`
- `88147935`

`87738210` の Mysterious Rock Inn `30 -> 0` veto も保持する。

`87877210` の Night Stretcher 置換は、epoch と同一 role-family 支配を再証明できる場合だけ保持する。

## telemetry

少なくとも次を追加する。

- `route_now_roles_seen`
- `now_roles_seen`
- `next_turn_roles_seen`
- `epoch_regression_veto`
- `role_family_incomparable_fallback`
- `now_parent_trainer_opportunity_seen`
- `now_parent_trainer_handoffs`
- `strict_hard_delta_overrides_parent_trainer`

## gate

- 上記四fixtureと seat-mirrored synthetic。
- 旧 BAD_ATTACK 四件の即時Prize修正を維持。
- Inn `30 -> 0` veto を維持。
- 全207 replay、209対象席、387 Explorer PLAY の shadow。
- 変更位置を全件再精査。
- 現在合法 Trainer の不当な飛ばし、epoch逆転、role-family誤支配、即時Prize低下、実効攻撃低下をすべて `0` にする。
- invalid、exception、stale、owner collision をすべて `0` にする。
- 両席の実engineで handoff と strict hard delta override を完走させる。
