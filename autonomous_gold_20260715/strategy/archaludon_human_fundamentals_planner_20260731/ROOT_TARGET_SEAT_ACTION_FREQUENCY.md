# Root-verified target-seat action frequency

## 対象

`live/55070349/refresh_20260729_1241/shadow_corpus_196_prior_plus_11_new`

- replay:
  `207`
- `TeamNames == "rurumi"` の対象席:
  `209`
- seat 0:
  `108`
- seat 1:
  `101`

self-play で両方が `rurumi` の場合だけ両席を数えた。
相手席へ候補を仮適用した回数は含めない。

## 集計方法

Kaggle replay の `action` は、同じ行ではなく1行前の `observation` への応答である。
このため、同じ行の action と hand index を結び付ける集計は使用しない。

カード使用は、対象席の observation に現れる log のうち、

- log type:
  `10`
- `playerIndex`:
  対象席
- `cardId`:
  対象カード

を使った。

同じ `(replay, seat, turn, cardId, physical serial)` は重複排除した。
Supporter の Explorer、Lillie、Boss は、unique turn と physical serial が一致する。

## 自然な使用回数

| card | ID | physical PLAY logs | unique turns |
|---|---:|---:|---:|
| Duraludon | 169 | 700 | 523 |
| Explorer's Guidance | 1185 | 387 | 387 |
| Poké Pad | 1152 | 372 | 310 |
| Pokégear 3.0 | 1122 | 365 | 305 |
| Lillie's Determination | 1227 | 256 | 256 |
| Ultra Ball | 1121 | 229 | 223 |
| Night Stretcher | 1097 | 186 | 168 |
| Full Metal Lab | 1244 | 172 | 172 |
| Jumbo Ice Cream | 1147 | 92 | 82 |
| Boss's Orders | 1182 | 87 | 87 |

Pokémonの進化、Toolの装着、手貼り、Ability、Attack は、
log type と callback が異なるため、この表の `PLAY` 集計へ混ぜない。

## 実装順への意味

頻度だけで強さを決めない。
ただし、自然発火0件の狭いルールより、基本プレイを直す順序の根拠には使う。

現在の順序:

1. Explorer から Alloy と攻撃までの完全 transaction。
2. Pad / Gear / Ultra / Stretcher の目的別使用と callback 完遂。
3. Lillie の使用前後で確定攻撃、Boss、回収経路を比較する。
4. Stadium、Ice Cream、Boss の対称的な戦闘・Prize 条件。

各候補では、単なるカード使用回数ではなく、
候補 certificate の開始、完遂、rollback、最初の行動差を別に数える。
