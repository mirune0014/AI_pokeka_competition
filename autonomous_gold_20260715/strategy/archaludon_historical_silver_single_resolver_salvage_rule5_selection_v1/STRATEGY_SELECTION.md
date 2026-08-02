# Rule 5 strategy selection

## Frozen parent

- Parent: `archaludon_historical_silver_single_resolver_salvage_rule4_trial_v1`
- `main.py`: `F6B6266D870D3F134544A91616C27673620557D149C0496CC2034E7674F010D9`
- deck: `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`
- Accepted rules: Rule 1 and Rule 4 only.

## Selected hypothesis

`PARENT_EXACT_ATTACK_WIN_OR_UNIQUE_HIGHER_PRIZE_BOSS_TRANSACTION_V1`

通常MAINで、公開情報上の一意な確定勝利attackを直ちに選ぶ。それがなければ、受理親が現在選んだ一つの対応attackをそのまま使い、現在Activeより厳密に多くのPrizeを取る一意なBench targetがある場合だけ、`Boss PLAY -> target -> 同一attack`を一transactionで実行する。

新しい汎用attack/Boss/threat scorerは作らない。

## Exact attack registry

対応attackは次だけ。

| Attacker | Attack | Exact immediate damage |
| --- | --- | --- |
| Duraludon `169` | Hammer In `223` | 30 |
| Duraludon `169` | Raging Hammer `224` | `80 + 10 × 公開damage counter` |
| Archaludon ex `190` | Metal Defender `253` | 220 |
| Archaludon `840` | Coated Attack `1212` | 120 |

名称、本文、印刷damage、Energy cost tupleを受理親の`_EXPECTED_ATTACKS`と完全照合する。Raging Hammerは`maxHp-hp`が既知・非負・10で割り切れる場合だけ。

即時damageは、登録damage、公開Weakness×2、公開Resistance-30、正確なFull Metal Lab `1244`によるMetal targetへの-30をこの順で扱う。Stadiumは空または正確なFull Metal Labのみ。Tool、Special Energy効果、Ability、Special Condition、永続防御、damage/Prize modifier、metadata不一致はUNKNOWNとして親へ戻る。

合法ATTACK optionを必須とし、Energy供給・進化・retreat・restriction解除は行わない。Turbo Flareその他のattackは対象外。

## Exact current win

- 現在Activeの合法な登録attackだけを比較する。
- `prize_take = min(exact printed Prize value, own remaining Prize)`、確定KOしなければ0。
- 親が選んだ登録attackが勝利ならその親actionをそのまま返す。
- それ以外は、現在ActiveをKOし、取得Prizeがown remaining Prizeに等しいdistinct attack IDがちょうど一つのときだけ上書きする。
- 複数terminal attack ID、未知効果、曖昧optionは親。

Prize valueはMega ex 3、その他ex 2、それ以外1。公開Prize変更効果があればUNKNOWN。

## Unique strictly-higher-Prize Boss conversion

- direct current winがない。
- 受理親actionが一意な対応ATTACK option。
- attacker fingerprintとそのattack IDを保存し、別attackへ変更しない。
- current Activeへの`current_take`を正確に計算する。
- Bench targetは同一attackで確定KOし、`target_take > current_take`の場合だけqualify。
- qualifying target serialがちょうど一つ。複数、同値、未知Prizeは親。
- terminal Boss targetは可。ただしcurrent Activeへのdirect winが常に優先。

## Precedence

1. deck/new-game/result resetと進行中Rule4/Rule5 transaction。
2. Rule1 setup。
3. Rule5 exact current win。
4. Rule4 Lillie materialization。
5. Rule5 unique higher-Prize Boss conversion。
6. 受理親action。

ownerが壊れた場合はclearしてそのcallbackの一度だけ計算済み親actionへ戻る。同callbackで別規則を再発火しない。

## Boss transaction

単一共有ownerを使用し、proposalは6項目だけ。

```text
EMPTY -> BOSS_EMITTED -> BOSS_CONFIRMED -> TARGET_CONFIRMED -> CLEAR
```

Snapshotはseat、turn、action count、Prize、supporter flag、Boss ref、attacker fingerprint、attack ID/metadata digest、元Activeとtargetのfingerprint/damage/Prize/take、Stadium、公開modifier、両board、semantic option signature。

- `BOSS_EMITTED`: 最低serialの合法Boss `1182`をPLAY。
- `BOSS_CONFIRMED`: Bossが手札を離れ、Supporter消費と公開log/discardが一致したときだけ、switch callbackで保存target serialを選ぶ。
- `TARGET_CONFIRMED`: 保存targetがActiveになった後、同じattackの合法性・damage・KO・Prize比較・fingerprintを再計算し、保存attack IDだけを選ぶ。
- matching attack log、result、turn/seat change、新game、mismatchでclear。

action返却だけでstageを進めない。同一prompt retryはsemantic roleを再bindし同じactionを返す。option順序反転はserial/attack IDで再bind。duplicate optionは最低position、Boss複数は最低serial。distinct qualifying targetが複数ならfail closed。

## Explicit exclusions

- search/Gear/Ultra/Pad/Turbo、Energy配分、進化、retreat、harmful-KO、comeback、hidden prediction。
- future Prize-race評価、一般脅威score、一般effect simulator。
- Rule2/Rule3の再導入。

## Focused fixtures

正例:

- 4 attackのunique terminal、親非attackからのunique terminal。
- Boss変換`0->1`,`0->2`,`1->2`,`1->3`。
- Weakness、Resistance、Full Metal Labと順序境界。
- 両席のBoss全transaction、option反転、retry、semantic duplicate。

負例:

- current attackで既に勝利、equal/lower Prize、non-KO、qualifying target複数。
- 親非attack、Rule4 Lillie materialization、別attackならKOするだけの局面。
- terminal attack複数、Supporter使用済み、Bossなし/違法、追加準備が必要。
- unsupported attack/modifier/Tool/Stadium/status/Prize effect。
- stale/interrupted transaction、target/damage/attack変更。
- 全Rule1/Rule4 focused fixtureを維持。

## Shadow and adoption gates

許可first differenceは次だけ。

- `DIRECT_EXACT_CURRENT_WIN`
- `BOSS_UNIQUE_STRICT_HIGHER_PRIZE_SAME_ATTACK`

Boss差分はparent/stored/executed attack ID一致、current_take、target_takeを記録する。その他は親同一。invalid/exception 0。

固定160は受理親`100/160`を再現し、schedule/duplicate一致、fault 0、gains >= regressions、各seat/opponent cell -3未満なし、全差分帰属可能、明確な有害first difference 0を要求する。shadow+fixed160自然発火0なら条件を広げず`DEFER-DORMANT`。
