# 次候補戦略選定: Public Attack-Readiness Metal Allocation v1

## 結論

選ぶ仮説は一つだけである。

> 親が MAIN で Basic Metal の通常手貼りを既に選んだ場合に限り、親対象への貼付が公開済み攻撃の readiness を何も改善せず、同じ Energy を別の一意な対象へ貼る案だけが現在攻撃または次アタッカーの readiness を厳密に改善すると公開情報から証明できるなら、貼付対象だけを差し替える。

候補名は `archaludon_public_attack_readiness_metal_allocation_v1` とする。Explorer deadline finalizer は dormant component のまま積まず、以下へ直接実装する。

- formal parent: `autonomous_gold_20260715/candidates/archaludon_purpose_first_pokegear_boss_transaction_v1/main.py`
- SHA-256: `558EE5DB29E001428B0D59813613FABEE8E15B96E422746C104BDFAB4DC22DB6`
- 先行最終判定: `DB874FB5FA7C0329E793EB93148F8A36A2BBC34C29818746FBDB6B6708D18CFD`

これはカード ID 別の点数表ではなく、「現在攻撃を先に成立させ、その後は無駄貼りを避けて次アタッカーを作る」という一つの一般原則である。親の Energy カード選択、手貼りを行う判断、残りの手順には介入しない。

## 検証済み事実と選定理由

- 現親の `attach_target_score` は Energy 枚数、カード ID、Active/Bench、HP、matchup の固定点で対象を選ぶ。攻撃コストや次アタッカー化を直接比較していない。
- 現親には `_pcrd_attack_payment`、`_pcrd_missing_energy_count`、`_pcrd_add_energy_projection`、公開 combat oracle、threat graph、resource ledger、semantic role/rebind が既にある。新しい damage model は不要である。
- acceptance matrix は「今払える攻撃を END しない」「既に攻撃可能な Active へ過剰貼りせず次アタッカーへ回す」「ただし Raging Hammer 等を解禁する Active 貼りは守る」を要求する。
- 207 replay / 209 target-seat の既存集計では Duraludon play 523 unique turns、Explorer 387、Pad 310、Gear 305、Lillie 256、Stretcher 168、Boss 87 である。ただし通常手貼り回数は未集計なので、頻度を推測してはならない。
- setup、盤面形成、現在アタッカー、backup、Energy/hand、攻撃継続、prize exchange、finishing、公開 disruption を同じ hard hierarchy で守れる。親の選んだ同じ一枚を移すだけなので hand/deck 消費は同一である。

期待する勝因は、Ready Active への無意味な 4 枚目等を、公開攻撃コストが一段進む一意の backup へ移し、Active が倒された次ターンの無攻撃を減らすことである。現在攻撃・現在 prize を犠牲にする改善は認めない。

## 実装契約

### 起動境界

1. 新 wrapper は formal parent を各 callback で厳密に一回だけ呼ぶ。
2. `obs.select` が clear MAIN、`minCount=maxCount=1`、effect/contextCard/looking がなく、全 serial と静的 metadata が完全な時だけ判定する。
3. 親 action が一つの `ATTACH` option で、card が同一 serial の Basic Metal、`energyAttached == False` の時だけ起動する。
4. `_pfgear_transaction`、`_pfgear_veto_watch`、`_pfgear_inherited_owner_active()`、または既存 owner/watch が生きていれば親をそのまま返す。Assemble Alloy、Turbo Flare、Ability、Trainer、Tool、Special Energy、retreat、attack option は対象外である。
5. 同じ Metal serial を同じ公開 Pokémon serial へ貼る option が一意に bind できない、対象集合が不完全、状態が UNKNOWN なら親を返す。

### readiness 証明と hard hierarchy

各 legal target へ同じ Metal を `_pcrd_add_energy_projection` し、現在カードに印刷された攻撃と、手札に公開され一意に適用できる同系統の一段 evolution の印刷攻撃だけを調べる。支払判定は `_pcrd_attack_payment` / `_pcrd_missing_energy_count`、damage・KO・prize・防御効果は既存 public combat oracle を唯一の authority とする。coin、山札順、相手手札、未知 effect、未対応 special-energy 解釈を仮定しない。

比較順は次の hard condition とし、巨大 score や重み付き和を作らない。

1. 現在 Active に exact payable attack が無い場合、貼付後に exact payable current attack を作る一意の対象だけを許す。親対象がそれを作るなら必ず親を維持する。
2. 現在の exact win、現在 KO/prize、最良の payable current attack、公開 worst reply 後の terminal-loss avoidance と Active survival を悪化させない。
3. 親対象の貼付が、どの supported printed attack についても `unpayable -> payable` を作らず、最小不足 Basic Metal 数も減らさないことを要求する。Raging Hammer を含む別の意味ある攻撃を解禁・接近させる親貼りは維持する。
4. 別対象だけが `unpayable -> payable`、または exact minimum remaining Basic-Metal attachments を一つ減らす。さらに READY_NOW / KNOWN_PUBLIC_RESOURCE の worst public reply 後もその対象が in play であることを要求する。
5. 候補の current/next attack continuity、prize liability、post-action/post-reply resource ledger が親案以上で、strict improvement が readiness に存在することを要求する。
6. strict candidate が一つだけなら、その同じ Metal serial・別 target serial の option へ差し替える。tie、複数候補、Pareto trade-off、UNKNOWN、INCOMPARABLE は厳密に親へ fail-close する。

projection adapter の追加は許すが、既存 combat/effect 実装を複製しない。card/opponent ID に対する局所例外や replay ID、seed、seat 固有分岐は禁止する。

### callback 所有権

- 差し替え時だけ一手 watch を開始し、開始 snapshot、seat/turn/action-count、Energy role、target role、親 role、証明 fields を保存する。
- 同一 snapshot の duplicate/reordered callback は保存 role を `_pcrd_bind_roles` で一意に再 bind して同じ action を返す。bind 不能なら watch を破棄してその callback の親 actionへ戻る。
- engine が進んだ最初の callback で、Energy serial が手札から消え、選択 target serial に付き、他 target に付かず、`energyAttached` と action-count が整合することだけを観測確認して clear する。次 action を強制しない。
- seat/turn/result/select context の不連続、deck request、失敗 postcondition は clear-and-parent。両 seat 共通で global state の漏れを許さない。

## 必須 fixture

Positive:

1. Active は既に exact attack payable、親は readiness 不変の Active 貼り、Bench は Metal 一枚で exact attack payable: Bench へ変更。
2. Active は既に payable、親は readiness 不変の ready target、唯一の Bench だけが不足 2→1、worst public reply 後も残る: Bench へ変更。
3. Active が一枚不足、親は Bench を選ぶが Active 貼りだけが exact current attack/KO を解禁: Active へ変更。

Negative:

1. 親 Active 貼りが current attack、Raging Hammer、または別 supported attack を解禁/接近させる。自然 control `88443760` と `88681773` を含め親維持。
2. 親対象も readiness を改善する、候補が二体、候補が公開 reply で確実に失われる、prize/return/resource に trade-off がある: 親維持。
3. attack/effect/energy payment が UNKNOWN、coin/hidden draw が必要、Special Energy、Alloy/Turbo/Trainer callback、owner live: 親維持。
4. option reorder、same-ID 二体、duplicate callback、両 seat、turn/result discontinuity: semantic serial で同一結果、不能なら親。

fixture は positive/negative 各三件以上を seat 0/1 で反転し、fresh engine で二回実行して action/telemetry が byte-identical、action error と max-step が 0 でなければ実装失敗とする。

## falsifiable evaluation gates

### Shadow gate

先に 207 replay / 209 target-seat corpus の source manifest と hash を固定し、formal parent を全 callback で再生して通常 Basic Metal MAIN ATTACH の分母を数える。以下を全て満たさなければ rare/narrow として fixed 評価へ進めない。

- strict-eligible start が 20 unique `(replay, seat, turn)` 以上、両 seat に存在する。
- actual first difference が 12 以上、8 replay 以上、両 seat に存在する。
- 全 difference で同じ Energy serial、変更は target serial だけ、現在 attack/KO/prize と owner lifecycle は不変または hard hierarchy 上の改善。
- root が全 changed position を GOOD_CAUSAL と確認し、UNKNOWN-as-zero、stale role、postcondition failure が 0。

### Fixed gate

同じ engine・opponents・seats・seeds の exact paired 760 schedule（Silver 200、adjacent population 560）で formal parent と candidate を比較する。schedule/key 完全一致、760 unique rows、両 agent の exit/action error/max-step/duplicate が 0 を前提とし、次を全て要求する。

- overall `candidate_win - parent_win >= 16/760` かつ paired 95% CI lower bound `> 0`。
- primary historical-Silver `>= +8/200`、Silver の両 seat が非悪化。
- overall の両 seat がそれぞれ `>= +4/380`。
- adjacent total、各 opponent×seat cell、既存 Kangaskhan/Crustle floor が非悪化。
- 4 contiguous seed blocks のうち 3 以上が正、どの block も `< -1` でない。
- intended readiness mechanism の completed certificate が両 seat・4 opponent 以上に反復し、全 first difference と全 loss flip を root が replay で確認する。

一つでも満たさなければ reject。小さな paired delta、shadow 上だけの正しさ、単 seat 改善、Silver 横ばいだけでは採用しない。通過後も package/Kaggle 判断は root 専有である。

## 棄却した代替

- Phase2 A–D の個別効果: Repelling Veil、Hammer、search/recovery、Switch/Surfer、Jumbo 等は重要だが、Archaludon 自身の自然 action 頻度と勝敗寄与が未証明で、この一手より card-specific かつ callback 所有範囲が広い。
- Phase2 E Rapid-Fire Combo: variable/coin を exact hard rule として扱えず、現在の deterministic 方針では時期尚早。
- Lillie: 256 unique turns と頻出だが、draw 内容が hidden なので事前の strict benefit 証明ができず、UNKNOWN fail-close では変更が乏しい。
- Night Stretcher: 168 unique turns と頻出だが、回収後の exact attack path と複数 callback を所有する必要があり、先に readiness allocation 基盤を固める方が一般的。
- Boss/Pokégear: 現 formal parent の直接担当であり、重複 ownership と回帰リスクが高い。
- Explorer finalizer: terminal 12/12 は正しかったが fixed760 は 0G/0R/760 tie、Silver 100/200 不変で強度が無い。dormant のまま積まない。

## 次に必要な厳密証拠

実装前に必要なのは、通常 Basic Metal MAIN ATTACH の root-verified 分母、strict-eligible/changed position の replay・seat・turn・Energy serial・親/候補 target serial、および両案の readiness/attack/prize/reply/resource certificate である。これが shadow minimum に届かなければ、この仮説は一般的でも当該 agent では低頻度として棄却し、Night Stretcher の exact recovery-to-attack transaction を次の判別実験にする。
