# Rule 4 実装・shadow root確認

## Frozen identity

- 受理Rule 1親: `153D8461FB66927DB9731CBE614B71FF5398B8EAE8980AE0BB4D46ADD0E8792A`
- Rule 4 trial `main.py`: `F6B6266D870D3F134544A91616C27673620557D149C0496CC2034E7674F010D9`
- 内蔵Historical-Silver親: `F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E`
- deck: `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`
- strategy selection: `136526EB9D2435A7E5822D3A6EE106078267365EDFB5801DCDE15A7737F7A269`
- implementation report: `0F5DDDAC225AC16CC439FD096A01D8C34FA19150839A423316EE39A58EF9B967`

## Structure and focused verification

- 追加規則は`PARENT_LILLIE_EXACT_CURRENT_MATERIALIZATION_V1`だけ。
- Rule 2とRule 3を含まない。
- final `agent` 1、resolver 1、親呼出し1 callbackにつき1回、transaction owner最大1。
- proposalは`rule_id/action/category/purpose/exact_proof/transaction`の6項目。
- Silver scorer/chooserは変更なし。候補の非`main.py`ファイルはRule 1親とbyte-identical。
- rootがfocused suiteを再実行し22/22 PASS。
- compile/import、合法60枚、ACE SPEC 1枚、cache-freeを確認。
- 両席engine smokeは53/105 step、action error 0、max-step 0。

## Replay shadow

- 77 readable replay、4,262 callback、invalid/exception 0。
- 自然発火・action differenceは2件。
- 2件とも親actionは一意なLillie PLAYで、分類は`BENCH_EVOLUTION_BEFORE_LILLIE`。

### episode 89279065 / seat 1 / step 41

- 親: Lillie serial 108。
- 候補: 3枚のBasic Metalを持つ旧ターンのbench Duraludon serial 66へ、Archaludon ex serial 68を進化。
- 支払い可能な印刷済み攻撃はMetal Defender。相手残りPrize 6。
- 公開情報上、Lillieで進化札を山札へ戻す前に確定展開する意図どおりの差分。

### episode 89283885 / seat 1 / step 34

- 親: Lillie serial 107。
- 候補: 3枚のBasic Metalを持つ旧ターンのbench Duraludon serial 64へ、非ex Archaludon serial 91を進化。
- 支払い可能な印刷済み攻撃はCoated Attack。相手残りPrize 6。
- 既知の敗戦監査で確認した「進化せずLillieを使い、直後に進化札を失った」境界と一致する。

いずれもshadowはfirst difference後の反実仮想を継続できないため、transaction receiptはfocused fixtureで確認済み。固定160では自然開始と完結を別に数える。

## Root decision

実装・shadow gateはPASS。固定160戦の実行を許可する。追加検証は行わず、凍結scheduleだけを使う。
