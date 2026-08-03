# v4 C3 fix5 最終 strategy judgment

日付: 2026-07-30  
役割: read-only rule-policy judge

## 最終決定

1. **C3 bench-0 action gate は REJECT。**
2. **`planner_public_damage_continuity.py` は C4 shadow の観測専用部品に限り継承可。**
3. **C4 の executable action parent は、採用済み C2 closure
   `29084BC13CB74236ABE557B57A9E633A8F9E88FA83FF22D131C835293E987157`
   に固定してよい。**

C3 の Basic 展開行動は採用しない。C4 は C3 candidate closure
`5C1BAD6C505358BFF7550A89F167D3DE19B0D2540C6C54ED85324F961A37E134`
を action parent にせず、公開 damage/continuity 解析だけを C2 上の shadow
計測として残す。

## 検証済み事実

数値は root paired/metric audit と独立数値監査からのみ採用し、新しい集計は
行っていない。

- 支配仕様:
  - immutable spec:
    `1585C9FC7BEB326E2F496AC8B35D99E5B75A976F0F69C7A8B7492671E7B73B5F`
  - formal spec:
    `B0E7ED5FE726BFB55E20A535BCD0D58E7BCA550D8C5F7A9D56635015DACCFA4A`
  - final collector amendment:
    `6618E5C8AAC1AF3D51E1AD562F2FB5CCBA94CDEBD01E31178A68D3F0C9A3B991`
  - path/retry amendment:
    `7614294084EC942EAD38BC72E5AC4037983F81B63F12290AF61B641DA8C52428`
- Root evidence:
  - paired audit:
    `99D376DD46257B5A5A2BC15A1F9220EA6AE57FB0BAC7BA838D330A82015A1812`
  - metric audit:
    `3F0AC1FB99E8A8E813CD611EB782F574039D7C3BC461B9B527DD2C46CA0F5F89`
- Production components:
  - pure analyzer:
    `AD14F84C80FC92B95ACB7C585D492910BD46883528CE2F99158AF046EDDAE201`
  - C3 action wrapper:
    `C9E86FFDBD054476E562313808DD08E35E05176F30BE083E1862A370229E3AEC`

Paired evidence:

- baseline/candidate 各700 unique schedule rows。missing、unexpected、duplicate は0。
- baseline と candidate はともに `452/700` wins (`64.57%`)。
- gain/loss/tie は `0/0/700`、overall delta は `0/700`。
- Historical Silver は双方 `56/100`、delta `0/100`、両 seat delta
  `0/50, 0/50`、positive seed block `0/5`。
- adjacent six は双方 `396/600`、delta `0/600`。全 opponent と全
  opponent-seat cell の delta も0。
- absolute floor と lower-bound safety は通過したが、overall positive、
  Silver `>=+3/100`、Silver positive block `>=2/5` は失敗。
- Rocket proxy は `38/100`、seat 1 は `17/50`。20-game blocks は
  `6,5,12,9,6` wins で、反復する弱い absolute floor を改善していない。

Mechanism/integrity evidence:

- accepted metric evidence は `90/90` blocks、`900/900` games。
- `CALL_START/CALL_END` は `55,514/55,514`。
- action error、max-step、nonzero exit、timeout、duplicate/unmatched callback、
  unsupported action change、transaction fault、metric/wrapper exception、
  structural invalid はすべて0。
- 全 callback が `NO_ACTION`。許可された
  `FLOOR_BOARDOUT_AVOIDANCE` と `CAP_LOW_COST_BOARDOUT_AVOIDANCE` は0。
- supported threat/action state は0、supported origin 内の
  promotion/removal context は0、continuity reach は0/4、seat/opponent reach
  も0。mechanism reach は `INSUFFICIENT_EVIDENCE`。
- analyzer の固定静的証拠は focused tests `14/14`、candidate regression
  `254/254`、`py_compile` exit 0。

## 仮説と REJECT 理由

評価した単一仮説は、Bench 0 で公開 floor/cap による盤面全滅 threat があり、
現在の攻撃、確定 KO、Prize 交換、最終 Prize を壊さない場合だけ独立価値のある
低コスト Basic を先に出せば、主力 anchor を改善し adjacent population を
悪化させず attack continuity を延ばせる、というものだった。

公開情報・デッキ理論に基づく仮説自体は妥当だが、実装済み action rule は支持
されなかった。

- **実用強度 / primary anchor:** `452/700` は absolute floor ちょうど。
  Silver は `0/100` 改善、positive block `0/5` で主 anchor を動かしていない。
- **両 seat / adjacent safety:** 全差分0で観測回帰はない。しかし action が
  一度も発火していないため、発火時の safety の証明ではない。
- **setup / board formation / backup readiness:** 意図した Basic 展開が0回で、
  盤面形成や次アタッカー距離の改善を観測していない。
- **Energy / Hand / Deck management:** Hand 1枚、Powerful Hand の `-20`、
  Prize liability と生存価値の trade-off が実戦で発生していない。
- **attack continuity / prize exchange / finishing:** 親の確定利益は壊れて
  いないが、行動同一だったからである。展開後の連続攻撃や最終 Prize 保持は未証明。
- **disruption / promotion-removal:** supported origin の到達が0で、forced
  promotion、removal、transaction re-entry 周辺の action safety は未証明。
- **repeated buckets:** Silver の5 blockを一つも改善せず、Rocket の弱い block
  も保持した。小さな paired delta さえなく、観測効果は完全に0。

未発火の action gate を production に残すと、正式評価外の初回発火だけが実戦で
起きる out-of-distribution risk がある。integrity PASS は analyzer の限定継承を
支えるが、C3 action の採用理由にはならない。

## C4 shadow 限定継承の behavioral contract

1. C4 は C2 closure
   `29084BC13CB74236ABE557B57A9E633A8F9E88FA83FF22D131C835293E987157`
   から作る。C3 production directory/closure を親として複製しない。
2. C4 の `agent` は C2 action を先に得て、shadow の結果や例外にかかわらず、
   value、Python type、要素順序、返却 object identity を含めて変更せず返す。
3. `planner_public_survival_bench0.py` を import/call しない。
   `C3_TRANSACTION`、C3 duplicate cache、delegate rollback/re-entry、
   Basic rebind、C3 action publish 経路を継承しない。
4. analyzer の `proposed_action`、`applied_action`、`selected_basic`、
   `transaction_stage` を executable authority にしない。
   `rebind_semantic_action` を C4 action 選択へ使わない。
5. 継承利用は公開 damage floor/cap、Power Pro provenance、activation class、
   continuity、unsupported reasons、public-state fingerprint の shadow 出力に
   限る。`evaluate_survival_decision` を診断で呼ぶ場合も action-related fields
   は非権威化し、返却 action へ到達不能にする。
6. match ledger が必要なら C4 shadow が公開 serial だけを記録して所有する。
   game boundary 不明時は破棄して `UNKNOWN` にし、C3 wrapper の mutable state
   を action state として持ち込まない。
7. analyzer exception、raw/parsed 不一致、ledger ambiguity、unsupported formula
   は trace を fail-closed にするだけで、C2 action を保持する。
8. C4 trace は C2 parent closure、C4 candidate closure、analyzer component hash、
   raw/returned action identity、公開入力、解析出力を分離する。analyzer 内の
   C3 rule/closure field を C4 policy identity の代用にしない。
9. 相手名、submission/episode ID、seed、非公開 Hand/Deck/Prize、山札順、
   後続 action、実勝敗 label を入力へ加えない。

C4 shadow が C2 action を1件でも変更した場合、その実行は shadow evidence
として無効である。新しい action candidate として別仕様・closure・正式評価が
必要になる。

## 回帰リスクと不確実性

- analyzer integrity には肯定的証拠があるが、許可 action origin が0なので、
  C3 Basic 選択の正しさは未検証。
- cap-only threat の ledger reset、serial multiplicity、family marker、
  hidden requirement が action へ漏れると過剰防御になる。
- `0/700` は観測 schedule 上の効果ゼロを示すが、「発火時も安全」を示さない。
  最大の不確実性は効果量より mechanism non-reach である。
- C4 でも Silver、Rocket、両 seat、adjacent population、action error/max-step を
  分離して監査する必要がある。

## 次に必要な正確な証拠

C4 shadow 継承には次が必要。

1. C2 closure を parent とする新 closure receipt と、C3 wrapper/state 不在を
   示す file/diff manifest。
2. analyzer hash と C4 trace linkage。duplicate/reordered callback、game reset、
   analyzer exception、unsupported formula の静的 tests。
3. 凍結した両 seat・複数 opponent schedule の全 callback で C2 action identity
   100%、action error/max-step/transaction/wrapper/metric exception/
   structural invalid 0。
4. origin-linked public damage/continuity trace。未到達 class は推定で補わず
   `INSUFFICIENT_EVIDENCE` とする。

C3 action を再検討する場合は、結果を見る前に凍結した reach schedule で
supported origin `>=30`、その中の promotion/removal `>=10`、continuity 4 class、
両 seat、3 opponents以上・非mirror 2以上、floor/cap 両 guard をまず観測する。
その後、変更位置で setup、Hand/Energy cost、attack before/after、Prize/terminal
outcome、backup distance、transaction completion が意図どおりであることを確認し、
fresh paired evaluation で元仕様の全数値・integrity gateを同時に満たす必要がある。

それまでは、C3 action rule は不採用、C4 は C2 action parent 上の pure shadow
analysis に限定する。
