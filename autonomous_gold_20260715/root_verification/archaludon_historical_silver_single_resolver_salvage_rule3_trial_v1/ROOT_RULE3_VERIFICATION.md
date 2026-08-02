# Rule 3 実装・shadow root確認

## Frozen identity

- 受理Rule 1親: `153D8461FB66927DB9731CBE614B71FF5398B8EAE8980AE0BB4D46ADD0E8792A`
- Rule 3 trial `main.py`: `3F05F353B868307E91A38FA62ED460D4BFB9A82B85400E2D98B3DBB5CE67A0FC`
- Rule 3 helper: `2015A4E589D2AE428A151AF50520C160CED7E1B1926D5599A2B35EB0CC6CEA61`
- 内蔵Historical-Silver親: `F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E`
- デッキ: `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`
- 実装報告: `B271B65A0751B908481D6B2899A971D8845512CFFE1EE77F4DA9C8C3132A2540`

## Structure and focused verification

- 追加規則は`SILVER_DECLARED_ULTRA_BALL_TWO_ROUTE_TRANSACTION_V1`だけ。
- Rule 2 trialは含まない。
- final `agent` 1、resolver 1、親呼出し1 callbackにつき1回、transaction owner最大1。
- `main.py`の親との差はRule 3 helper登録に限定され、Silver scorer/chooserは変更なし。
- rootがfocused runnerを再実行し80/80 PASS。
- compile/import PASS、合法60枚、ACE SPEC 1枚。
- workerの両席engine smokeは73/164 step、action error 0、max-step 0。

## Replay shadow

- 凍結episode `89280661`、58 callback。
- 親候補との差分0、invalid 0。
- このshadowでRule 3自然発火0。

条件は広げない。固定160戦で自然発火・完結を確認し、shadowと固定160戦の合計発火0なら実装記録だけ残して不統合とする。

## Root decision

固定160戦の実行を許可する。追加の広範検証は許可しない。
