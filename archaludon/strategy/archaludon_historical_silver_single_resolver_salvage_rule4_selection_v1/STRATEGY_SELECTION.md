# Rule 4 strategy selection

## Frozen parent

- Parent: `archaludon_historical_silver_single_resolver_salvage_v1`
- Parent `main.py`: `153D8461FB66927DB9731CBE614B71FF5398B8EAE8980AE0BB4D46ADD0E8792A`
- Historical-Silver parent: `F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E`
- Deck: `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`

Rule 2とRule 3は親に含めない。

## Selected hypothesis

`PARENT_LILLIE_EXACT_CURRENT_MATERIALIZATION_V1`

1 callbackで一度だけ呼んだSilver親が、単一の物理Lillie `1227`をPLAYするときだけ、現在の公開盤面で完全に合法かつ一意に確定できる展開を一つ先に実行する。実行結果を物理serial・area・Energy枚数で確認した後ownerを解放し、次callbackの実盤面からSilverを一度だけ再計算する。

Lillieを温存する規則ではない。Lillieを使わないための`END`は生成しない。展開後にLillieを使う保証も持ち越さない。

## Entry gates

すべて必須。

1. 通常MAINでresult未確定、既存transaction ownerなし。
2. 親actionが、手札の一意なLillie serialに対する合法な`PLAY`。
3. Supporter未使用。
4. 現在のoption・hand・Active・Benchをserialで一意に結合できる。
5. 下記routeのうち、最上位で候補がちょうど一つ。
6. 不明metadata、同順位複数、effect判定不一致、owner衝突ではSilver。

## Certified routes

優先順位は記載順。上位routeが複数なら下位へ落とさずSilverへ戻る。

### 1. Duraludon Basic placement

- Benchに空きがある。
- 手札から合法にPLAYできるDuraludon `169`が全serial中ちょうど一つ。
- Benchに`169/190/840`が一体もいない。
- Activeを変更せず、Supporter権・手張り権・攻撃optionを消費しない。

選択したDuraludonをBenchへPLAYする。受領後、同serialがBenchにあることを確認してownerを解放する。

### 2. Ready benched Duraludon evolution

- BenchのDuraludon `169`で、今ターン出た個体ではなく、exact Basic Metalを3枚以上持つ個体が一体だけ。
- その個体への合法な進化optionが、全進化先・全serialを通して一つだけ。
- 進化先はArchaludon ex `190`または非ex Archaludon `840`。
- 進化後の印刷済み攻撃と必要Energy metadataを完全に読め、現在Energyで少なくとも一つ支払い可能。
- `190`へ進化する場合、相手残りPrizeは3枚以上。
- Active、現在の合法攻撃、Supporter権、手張り権を変更しない。

合法EVOLVEを実行する。受領後、同じ盤面slot・系列・進化serialを確認してownerを解放する。Assemble Alloyのeffect callbackは所有せず、そのcallbackのSilverへ渡す。

### 3. Active third Metal attachment

- Activeが`169/190/840`のいずれかで一意に結合できる。
- ActiveのEnergyがexact Basic Metalちょうど2枚で、未知Energyなし。
- 手張り未使用。
- 手札のBasic Metal `8`が一枚以上あり、合法ATTACH先としてActiveが存在する。
- 3枚で支払い可能になる印刷済み攻撃が一つ以上あり、攻撃cost metadataが完全一致。

最低serialの合法MetalをActiveへATTACHする。同serialがActiveに付いてexact Metal 3枚になったことを確認してownerを解放する。

### 4. Full Metal Lab placement

- Stadiumが空。
- 手札のFull Metal Labが合法PLAYで、複数なら最低serialを一意に束縛できる。
- 自分のActiveはMetal Pokémon。
- 相手のActiveとBenchの全公開Pokémonは、型metadataが既知でMetalではない。
- 自分の現在合法な攻撃option、Supporter権、手張り権を失わない。

最低serialのFull Metal LabをPLAYする。Stadiumへの物理配置を確認してownerを解放する。

## Transaction and fail-closed behavior

単一ownerの状態は次だけ。

```text
EMPTY -> MATERIALIZATION_EMITTED -> CLEAR
```

- 同一prompt retryではsemantic actionをserialから再bindし、stageを進めない。
- option順序が変わってもraw positionを保存せず、card ID・serial・action kind・target serialで再bindする。
- 発行後に期待した物理変化を確認できない、turn/seat/result/promptが変わる、またはownerが衝突した場合は状態を捏造しない。ownerをclearし、そのcallbackで一度だけ計算したSilver actionへ戻る。
- effect callback、mandatory callback、setup、attack後callbackはすべてSilver。

## Explicit exclusions

- `HOLD_LILLIE`、Lillie温存目的の`END`。
- Pokégear、Boss、Explorer、Ultra Ball、Poké Pad、Night Stretcher、Turbo Flare。
- attack選択、相手脅威評価、Prize race、隠れた札、将来draw、複数ターン探索。
- 汎用effect simulator、新しい総合スコア。
- Rule 2・Rule 3の再導入。

## Focused fixtures

- 両席で4 routeの正例と親Lillieへの復帰。
- 各routeの複数候補、未知metadata、違法option、今ターン出たDuraludon、ex進化Prize<3、既使用手張り、未知Energy、既存Stadium、相手Metalの負例。
- option順序反転、同一prompt再送、stale turn、owner衝突。
- Lillie以外の親action、Supporter使用済み、effect/mandatory/setup/attack後callbackは親同一。
- Rule 1 setup fixtureは全件維持。

## Shadow and adoption gates

first differenceは次だけに分類する。

- `DURALUDON_BEFORE_LILLIE`
- `BENCH_EVOLUTION_BEFORE_LILLIE`
- `THIRD_METAL_BEFORE_LILLIE`
- `FULL_METAL_LAB_BEFORE_LILLIE`

全差分で直前の親actionが一意なLillie PLAYでなければ不採用。materialization確認後の実盤面再評価がなく、ownerがLillieやENDを強制した場合も不採用。

固定160は凍結scheduleを使う。fault 0、明確な有害first difference 0、paired gains >= regressions、各席・各相手で親から3勝以上悪化なしを要求する。shadowとfixed160の合計自然発火0なら`DEFER-DORMANT`とし、条件を広げず最終候補へ統合しない。
