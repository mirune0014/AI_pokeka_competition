# Root verification — return relevance census v1

## 結論

`RELEVANCE_BOUND_PUBLIC_RETURN_COMPLETENESS_V1` は実装しない。

固定判定は
`STOP__RETURN_UNKNOWN_NOT_ONE_ACTIONABLE_BOUNDED_CAUSE` とする。
親は
`archaludon_purpose_first_pokegear_boss_transaction_v1`
のまま維持する。

公開経路に関係しない攻撃解析失敗だけを空経路として扱う shadow は、
到達可能な攻撃経路を消さずに一部の `RETURN_UNKNOWN` を解消できた。
しかし、独立75ターン中で完全比較可能になったのは5ターンだけであり、
hardなプラン順位差も、返す最初の合法手の差も0件だった。
内部の不確定値を減らすだけで、プレイ改善にはつながらない。

## 凍結入力

- strategy contract:
  `B4ED651CD03D033FCCEDDA481A2D8636C41F328E7C3A8814C2844BF5AE710731`
- census runner:
  `E6F65CFE8DCC247988EE86A56DBB60C2102973F3E4C6345579ECB38F7ACBEFC0`
- exact parent `main.py`:
  `558EE5DB29E001428B0D59813613FABEE8E15B96E422746C104BDFAB4DC22DB6`
- source manifest:
  `90A512D5C9AE5EAD8DF92F370C32716959EC0929F9465451E7BB0926DBEB5A68`
- execution specification:
  `7CCE3CCDD7683D7AC7726F509C252066876CFB17AF35D7F4F10A6E3C9F613BCB`

## 実行結果

凍結runnerを一度だけ実行し、exit code 0で完了した。
実行時間は約731秒だった。

- `cause_rows.csv`:
  819 data rows、SHA-256
  `78C16DDBFE1BA27BB9701781CDFFF011719ECA8BBFC0CD4EB397453AB30ED2DA`
- `shadow_plan_rows.csv`:
  254 data rows、SHA-256
  `72C30B7D76BB8D5E2032208575007F5B26701A5D47C63378F6FA47E7F4585ADA`
- `summary.json`:
  SHA-256
  `6AB7D5EC7D02E4C490A71B7A4FABF01F2753FE1F9A0A0BDD5694DF5AC0195999`
- independent Sol-Ultra numerical audit:
  SHA-256
  `E5DCD079F492E1A7A6E2340B63CDD8116C10F1B55CFADBE2CB096E0590D86D7A`

## Root再計算

### 完全性

- manifest: 207 replays、209 target seats。
- selectable parent callbacks: 25,880。
- unique raw callback keys: 25,880。
- frozen target callbacks: 225。
- attack alternatives: 254。
- cause keys: 819/819 unique。
- shadow keys: 254/254 unique。
- manifest mismatch、duplicate raw key、persisted target action error: 0。
- persisted parent actions: 254/254 valid。

### 独立ターン単位の固定gate

独立callbackは `pre_call_owners == {}` とし、
同一 `(replay, seat, turn)` の最小stepだけをそのターンの証拠とした。

| gate | Root再計算 | 必要値 | 判定 |
|---|---:|---:|---|
| independent target turns | 75、両席、48 replays | 参照値 | - |
| bounded `EXACT_LOCAL_NO_ROUTE` | 37 turns、両席、30 replays | 40 / 両席 / 15 | FAIL |
| boundedかつ単一event provenanceあり | 33 turns、両席、28 replays | 同上 | FAIL |
| fully exact shadow | 5 turns、両席、5 replays | 24 / 両席 / 12 | FAIL |
| hard ranking difference | 0 | 12 / 両席 / 8 | FAIL |
| predicted legal first-action difference | 0 | 8 / 両席 / 6 | FAIL |
| qualifying hard-layer classes | 0 | 2 classes各3件 | FAIL |

runner summaryの39ターンは、同一ターン中の後続callbackも合算した値である。
固定契約の「earliest-independent turn」では37ターンになる。

### blocker provenanceの不一致

819 blocker rowsの内訳は次のとおりだった。

- exactly one matched route event: 469。
- multiple matched route events: 263。
- no matched route event: 87。

`summary.json` は、行数一致と許可済みenumだけで
`blocker_assignment: true` としている。
しかし350/819行では単一のroute eventへ対応しておらず、
現在の支払Energy割当もCSVに保存されていない。
したがって「全blockerを一度ずつ、完全なmetadata provenanceで割り当てる」
という固定gateはRoot判定ではFAILである。
この不一致は修正せず記録し、runner aggregateを採用根拠にしない。

### 安全性と因果性

shadowが抑制したroute-eventは272件だった。

- `analysis.relevant` が非空の抑制: 0。
- 非exact解析の抑制: 0。
- unsafe local scopeの抑制: 0。
- 元routeが `None` 以外だった抑制: 0。
- suppression eligibility不一致: 0。
- hidden Energyを「所持している」と仮定した経路: 0。

13/254 attack alternatives、5/75 independent turnsでは、
返しのPrize、生存、攻撃継続、ready backupに関する未確定値がexactになった。
それでも現在のKO/Prizeは変わらず、hard hierarchyも最初の行動も変わらなかった。
よって安全な局所整理ではあるが、勝敗を変える改善とは評価できない。

## 決定

- candidate sourceを作らない。
- package、local battle schedule、Kaggle提出へ進めない。
- gateを緩和しない。
- この失敗結果を次の仮説選定の入力とする。

