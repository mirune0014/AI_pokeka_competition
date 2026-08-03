# 公開効果レジストリ第2段階 実装マップ

## 目的

相手の公開された特性、攻撃効果、特殊エネルギー、グッズを無視したまま
KO、被KO、攻撃継続、資源差を判定しない。

カード名を whitelist へ追加するだけでは完了としない。
最終 `agent` が実際の callback を所有し、効果解決後の盤面を次の行動判断へ渡したときだけ `[x]` とする。

## 共通条件

- ID、entry、正規化テキスト hash を三点一致させる。
- 選択肢で公開されたカードだけを使う。
- 山札全体の内部配列や相手の非公開手札を使わない。
- 物理 serial、対象、枚数、owner、seat、turn を保存する。
- duplicate callback は同じ意味行動を返す。
- 対応外の効果が戦闘結果へ関係するなら親へ戻る。
- ダメージだけでなく、Energy、手札、山札、Bench、進化、次攻撃可能性を更新する。

## Batch A: 戦闘結果を直接変える決定的効果

### Repelling Veil

- binding: card `414`, skill entry `0`
- text hash:
  `ACDDBD907D301140B9C6332FBDDED801E5DA4C57425AC7F9BEA8AD6FA74361B7`
- 専用 callback はない公開 passive。
- Team Rocket's Basic Pokémon が受ける相手攻撃の効果を防ぐ。
- 通常の attack damage は防がない。

更新対象:

- attack-effect による damage counter placement。
- Energy discard、switch、その他の対象効果。
- `target_attack_effects_prevented`。
- Bench component、KO、Prize、残りHP。

正負 fixture:

- Team Rocket's Basic への攻撃効果は無効。
- 通常ダメージは通る。
- Team Rocket's でないポケモンには適用しない。

### Shadow Bullet の最終対象

- attack `648/937`
- `DAMAGE` callback、相手Benchを一体、`min=max=1`。
- 保存した唯一の対象へ30ダメージを与え、HP、KO、Prizeを更新する。
- Flower Curtain などのBench保護を同じ計算へ通す。

### Trading Places / Teleportation Attack

- `SWITCH` callback、Bench一体、`min=max=1`。
- 攻撃後のActiveとBenchを交換する。
- Benchがない場合は攻撃自体を違法にせず、任意switchだけを省略する。

## Batch B: Energy と攻撃可能性を変える決定的効果

### Telepath Psychic Energy

- card `19`, skill entry `0`
- text hash:
  `E41D5D0EB0E239D2675A7DE4597E7CEB90513F56E507A2730F3E30329FB4E1D5`
- attach 後、`TO_BENCH/CARD`、`0..2`。
- engine が公開した Basic Psychic だけを対象にする。

更新対象:

- 手札からEnergy一枚を減らす。
- 装着先のEnergyを増やす。
- 選択したBasicを山札からBenchへ移す。
- Bench枠、山札枚数、次アタッカー、進化可能ラインを再計算する。

### Enriching Energy

- card `13`, skill entry `0`
- text hash:
  `907FD824677844EBDF2A11ADCD9B0F976BEA8F83D7BE509CE396B5E693C52838`
- attach後の4枚ドローは自動。
- ドロー前に未知カードIDを推定しない。

更新対象:

- Energy装着。
- `draw_count=min(4, deckCount)`。
- 手札枚数と山札枚数。

### Enhanced Hammer

- card `1081`, skill entry `0`
- text hash:
  `227B26FA449AFBD07A738916A8D36D746D2AE810E3CEFEA0F1241C0717208D4A`
- `DISCARD_ENERGY`、相手の特殊Energy一枚、`min=max=1`。

更新対象:

- グッズを手札から捨て札へ移す。
- 対象ポケモンから物理Energyを一枚外す。
- 相手の捨て札へ移す。
- 相手の攻撃支払い、逃げ、次攻撃可能性を再計算する。

### Punk Up / Aura Jab

- Punk Up:
  `ACTIVATE -> ATTACH_TO 0..5 -> ATTACH_FROM 1`
- Aura Jab:
  `ATTACH_TO 0..3 -> ATTACH_FROM 1`
- 選んだ各Energyのserialと付与先serialを最後まで保存する。
- 現在攻撃と次ターンの攻撃可能性を分けて更新する。

## Batch C: 公開検索・回収・進化

### Buddy-Buddy Poffin

- card `1086`
- `TO_BENCH/CARD`、`0..2`。
- engine が公開したHP70以下Basicだけを対象にする。

### Sacred Ash

- card `1129`
- `TO_DECK/CARD`、`1..5`。
- 選んだポケモンだけを捨て札から山札へ戻し、山札をシャッフルする。

### Lana's Aid

- card `1184`
- `TO_HAND/CARD`、`1..3`。
- 公開された非Rule Box PokémonまたはBasic Energyだけを回収する。

### Hilda / Dawn

- Hilda:
  Evolution `0..1`、次にEnergy `0..1`。
- Dawn:
  Basic、Stage 1、Stage 2を順に各 `0..1`。
- 各段階で公開された選択肢だけを使い、同じtransactionで対象の用途まで保存する。

### Champion's Call / Spikemuth Gym

- Cynthia's Pokémon または Marnie's Pokémon を `0..1` 検索する。
- 一ターン一回の使用済み状態を保存する。

### Fighting Gong / Energy Search / Dusk Ball

- Fighting Gong:
  Basic Fighting Energy または Basic Fighting Pokémon `0..1`。
- Energy Search:
  Basic Energy `0..1`。
- Dusk Ball:
  山札下七枚が `current.looking` に出た後、その公開領域だけから Pokémon `0..1`。
- Dusk Ball で内部の全山札配列を見てはならない。

### Rare Candy / Ascension / Forest of Vitality

- Rare Candy:
  公開されたBasicとStage 2の組を一つ進化。
- Ascension:
  `EVOLVES_TO 0..1`。
- Forest of Vitality:
  専用callbackを捏造せず、通常MAINの同ターンGrass進化を合法候補として扱う。

## Batch D: 回復・交代・ドロー

### Switch / Surfer

- `SWITCH/CARD`、一体。
- ActiveとBenchを交換する。
- Surferは解決後、手札が五枚になるまでの自動ドローを枚数で更新する。

### Wally's Compassion

- damaged Mega Evolution Pokémon ex 一体。
- 全回復し、付いているEnergyをすべて手札へ戻す。
- 自然callback donorが未確認なので、checked engineで形を確定するまで完成扱いにしない。

### Jumbo Ice Cream

- 専用callbackはなく、条件を満たすdamaged Activeへ自動解決する。
- `min(80, missing HP)` を回復する。
- 被KOターンとRaging Hammer打点を両方再計算する。

### Lunar Cycle / Run Errand

- Lunar Cycle:
  Basic Fighting Energy一枚を捨て、三枚ドロー。
- Run Errand:
  Active時に二枚ドロー、一ターン一回。
- 未知のドロー内容は枚数だけ更新する。

## Batch E: 変動効果

### Rapid-Fire Combo

- attack `756/1092`
- coin flipを偽の確定ダメージや期待値一個へ潰さない。
- 最低ダメージは200。
- `k`回連続表なら `200 + 50k`。
- checked engineで最大回数または停止条件を確認する。
- 確定KO、可能KO、KO確率を別フィールドにする。

この効果は決定的レジストリから分離し、確率分布または上下界を扱える段階で実装する。

## 実装順

1. Batch A。
2. Batch B。
3. Batch C。
4. Batch D。
5. Batch E。

各Batchはカード名の登録数ではなく、次で完了判定する。

- positive fixture。
- boundary negative fixture。
- option reorder。
- duplicate physical copies。
- duplicate callback。
- 両席の実engine lifecycle。
- 最終agentが期待する合法行動を返す。
- その効果がダメージ、Prize、攻撃可能性、資源台帳へ反映される。

