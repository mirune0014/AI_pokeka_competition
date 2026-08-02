# Task 7: PUBLIC_COMPLETE_SUPPORTER_PURPOSE_ARBITRATION_T7_V1

## Frozen parent

- Parent: `archaludon_public_ultra_ball_declared_complete_route_transaction_v1`
- Parent `main.py` SHA-256: `99EE7BF5E6E6D61D863EF1D131232F90DCE36A3CFDF032AF6E534DECA79B2756`
- Deck SHA-256: `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`
- Root evidence: `ROOT_VERIFIED_EVIDENCE.md`

## Selected hypothesis

公開情報だけで同一ターンの最終 Prize 取得まで証明できる場合、手札または
Pokégear 公開中の Boss's Orders を Explorer's Guidance / Lillie's
Determination より優先する。完全経路を証明できない Supporter は Task 7 が
所有しない。

Task 7 の新規 purpose は `FINISH_NOW_EXACT_BOSS` 一つだけとする。一般的な
Lillie の使用・温存は Task 8、非終端の有害 KO・Boss 対象・逆転分岐は Task 9
の責務であり、ここでは先取りしない。

## Hard priority

1. deck/setup/result/mandatory callback;
2. Task 4–6、CUM/PCRD/DPER、既存 PF、Turbo を含む既存 owner の継続;
3. 現在 Active への公開情報上の exact terminal attack;
4. Task 7 `FINISH_NOW_EXACT_BOSS`;
5. exact cumulative parent.

最終 callable の後へ append-only wrapper を置き、親を callback ごとに一度だけ
呼ぶ。既存 owner が動作中、または親呼出中に別 owner が arm した場合は Task 7
は所有しない。

## Direct Boss certificate

通常 MAIN、Supporter 未使用、owner-free、Boss が合法、公開 serial/state が
完全な場合に限る。

- 現在 Active に合法かつ支払済みの attack がある。
- 公開 Bench target を gust 後 Active として投影する。
- 既存 `_pfgear_attack_certificate` と同じ oracle を使い、相手手札は常に
  `target_public_hand=()` とする。
- `ko=True` かつ `prize_yield >= own_remaining_prizes`。
- Boss 後にも同じ attacker/attack/payment/certificate が成立する。
- 現在 Active への attack だけで既に terminal なら Boss は使わない。

複数 attack は semantic duplicate を畳み、公開 resource/prize の全項目で一つが
componentwise dominant な場合だけ採用する。比較不能なら非所有。複数 terminal
target は次の option-index 非依存キーで決定する。

`(-prize_yield, -lethal_margin, target_semantic_fp, target_serial, attack_id)`

Boss の物理 copy は最小正 serial とする。

## Pokégear

新しい Gear owner は作らず、既存 `PF_GEAR_BOSS_TX_V1` の transaction/lifecycle
を再利用または厳密に委譲する。certificate に汎用
`declared_supporter_routes` を追加し、Task 7 の route は
`supporter_id=BOSS / purpose=FINISH_NOW_EXACT_BOSS` だけとする。

開始条件:

- 手札に direct terminal Boss がない。
- current terminal attack がない。
- Gear 使用前に完全 route が一つ以上ある。
- Supporter serial は公開前なので `None`。
- 既存 exact MAIN/metadata/serial/status/deck/owner gate をすべて満たす。

公開時は `current.looking` と option の物理対応を検証し、事前宣言 route と
card id が一致するものだけを候補にする。

- `{B}`, `{B,E}`, `{B,L}`, `{B,E,L}` は canonical Boss。
- `{}`, `{E}`, `{L}`, `{E,L}` は合法な空選択 `[]`。
- Explorer/Lillie を Boss の代用品にしない。
- 複数 Boss は最小 serial。Supporter serial は公開 callback で初めて bind。
- 完全 purpose のない開始局面では owner を持たず親完全一致。

## Lifecycle, retry, rollback

Direct:

`BOSS_PLAY_EMITTED -> BOSS_TARGET_EMITTED -> ATTACK_EMITTED -> COMPLETE`

Gear:

`GEAR_PLAY_EMITTED -> GEAR_HIT_EMITTED | MISS_EMPTY_EMITTED -> BOSS_PLAY_EMITTED -> TARGET_EMITTED -> ATTACK_EMITTED`

各遷移で seat/turn/actionCount、flags、hand/deck/discard multiset、board、
effect/serial、metadata hash を再検証する。

- 同一 callback retry は semantic role を再 bind し、stage/counter を進めない。
- 不可逆 action 前の stale は clear して親へ戻す。
- Boss/Gear emission 後の stale は合法な親 actionへ fail-closeし、
  `irreversible_abort` を記録して安全境界で clear する。
- Gear miss は必ず `[]`、次の MAIN で ledger を確認して clear。別 Supporterを
  選ばず owner を残さない。
- 保存則は `starts = completes + misses + aborts + live`。

## Reusable certificate schema

最低限、次を保存する。

- schema/rule/purpose/priority/source kind;
- seat/game epoch/turn/action count/stage;
- supporter id/serial（Gear前はserial `None`）、gear serial;
- attacker serial/attack id/payment;
- target serial/semantic fingerprint;
- remaining prizes/prize yield/lethal margin/terminal proof;
- complete route steps/public-input hash;
- pre/post attack certificate/resource delta/attack continuity;
- hand/deck/discard/board/option/metadata hashes;
- revealed Supporter multiset/eligible declared routes/selected route;
- per-Supporter rejection, tie-break key;
- callback fingerprint/roles/duplicate count;
- owner before/after/irreversible/rollback/completion reason.

Task 8/9 は同じ route schema に purpose を追加できるが、別 owner を同時に積まない。

## Required practical safety gates

- Episode `89292594` step 120 を両 seat・option permutation で
  Boss -> canonical target -> Metal Defender と完走。
- target を HP 221 にした負例は親完全一致、ownerなし。
- current terminal attack、Boss illegal、Supporter使用済み、Prize不足、Benchなし、
  oracle UNKNOWN は親完全一致。
- Gear の全8 Boss/Explorer/Lillie subset、duplicates、looking/option reorder、retry、
  miss後clear。
- 相手 hidden-hand identityだけを変えて action/certificate 不変。
- 既存 owner中は親完全一致。
- exact parent/deck hash、`main.py`以外不変、compile/import/final callable、
  legal60/ACE1/cache-free。
- current + historical shadow の全first differenceが宣言範囲内。
- extracted both-seat smokeでaction error 0、max-step 0、owner collision 0、保存則成立。

負例発火、Explorer/Lillieの未宣言選択、option permutation非決定、hidden-hand依存、
stale owner、説明不能なshadow差分が一件でもあれば reject する。これは実装安全性
の契約であり、強度改善の証明ではない。
