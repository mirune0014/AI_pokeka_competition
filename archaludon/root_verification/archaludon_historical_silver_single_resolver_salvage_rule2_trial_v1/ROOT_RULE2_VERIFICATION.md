# Rule 2 実装・shadow root確認

## Frozen identity

- 受理Rule 1親 `main.py`: `153D8461FB66927DB9731CBE614B71FF5398B8EAE8980AE0BB4D46ADD0E8792A`
- Rule 2 trial `main.py`: `D2BC5FCC82A5A507B7C5CC9FEDAAC4ED6EA0BE1622EBE99EFC74B6E6A926FC62`
- 内蔵Historical-Silver親: `F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E`
- デッキ: `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`

## Structure and focused verification

- 追加規則は`EXACT_LONE_ACTIVE_REPLY_KO_CONTINUITY_V1`だけ。
- final `agent` 1、resolver 1、親呼出し1 callbackにつき1回、transaction owner最大1。
- Historical-Silver scorer/chooserとデッキは変更なし。
- focused fixtureをroot再実行し、9/9 PASS。
- compile/import PASS、合法60枚、ACE SPEC 1枚。
- workerの両席engine smokeは108/42 step、action error 0、max-step 0。

## Replay shadow

rootが77個の比較JSONを再集計した。

- callbacks: 4,262
- parent/candidate differences: 0
- 読み取り不能な比較JSON: 0

このshadowは非破壊性を支持するが、Rule 2の自然発火は0である。要件に従い、条件は広げない。固定160戦で一度でも自然発火するかを確認し、shadowと固定160戦を合わせても0なら実装記録だけ残して不採用とする。

## Root decision

固定160戦の実行を許可する。追加の広範検証は許可しない。
