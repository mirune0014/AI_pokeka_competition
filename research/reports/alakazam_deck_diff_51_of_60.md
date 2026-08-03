# フーディン2デッキの51/60差分

## 結論

既存submission `54906455`のデッキと今回選定したデッキは、同じ60枚ではない。

カード多重集合で51枠が共通し、9枠が入れ替わっている。

既存版のnormalized deck hashは`f2e179fb82cb91504ccd207d707ca5e7be8afc7228df26a7b287c6205064507c`である。

今回候補のnormalized deck hashは`4414e8995e50c7a00d4b6aa7d9229f63c1dff5261643ec7cd86c4e329113ed69`である。

normalized deck hashは、60個のcard IDを昇順に並べ、空白区切りと末尾改行でASCII化した値のSHA-256である。

## 既存版からなくなる9枠

| card ID | カード | 枚数差 |
| ---: | --- | ---: |
| 142 | Genesect | `1 → 0` |
| 858 | Psyduck | `1 → 0` |
| 1156 | Lucky Helmet | `1 → 0` |
| 1161 | Handheld Fan | `2 → 0` |
| 1264 | Battle Cage | `4 → 0` |

削除枚数の合計は9枚である。

## 今回候補で増える9枠

| card ID | カード | 枚数差 |
| ---: | --- | ---: |
| 743 | Alakazam | `3 → 4` |
| 1081 | Enhanced Hammer | `3 → 4` |
| 1182 | Boss’s Orders | `2 → 3` |
| 1184 | Lana’s Aid | `0 → 1` |
| 1197 | Xerosic’s Machinations | `0 → 3` |
| 1266 | Nighttime Mine | `0 → 2` |

増加枚数の合計は9枚である。

## 共有51枠

| card ID | カード | 共通枚数 |
| ---: | --- | ---: |
| 5 | Basic Psychic Energy | 2 |
| 13 | Enriching Energy | 1 |
| 19 | Telepath Psychic Energy | 4 |
| 66 | Dudunsparce | 2 |
| 140 | Fezandipiti ex | 1 |
| 305 | Dunsparce | 3 |
| 343 | Shaymin | 1 |
| 741 | Abra | 4 |
| 742 | Kadabra | 4 |
| 743 | Alakazam | 3 |
| 1079 | Rare Candy | 3 |
| 1081 | Enhanced Hammer | 3 |
| 1086 | Buddy-Buddy Poffin | 4 |
| 1097 | Night Stretcher | 1 |
| 1129 | Sacred Ash | 1 |
| 1152 | Poké Pad | 4 |
| 1182 | Boss’s Orders | 2 |
| 1225 | Hilda | 4 |
| 1231 | Dawn | 4 |

共有枚数の合計は51枚である。

## 方策へ影響する差

GenesectとPsyduckの削除は、初期Active、Basic Pokémon検索、Bench役割、retreat先、ACE SPEC関連の分岐を空にする。

Lucky HelmetとHandheld Fanの削除は、Tool装着、被弾応答、Hand Powerの将来手札見積り、resource reservationの分岐を空にする。

Battle Cageの削除は、Stadium設置、張り替え、Dragapult対策、v4の効果安全証明に関わる前提を変える。

4枚目のAlakazamは、回収後の残存枚数と2本目の進化経路を変える。

4枚目のEnhanced Hammerと3枚目のBoss’s Ordersは、妨害可能回数を増やす一方、使用時にHand Powerの打点を20ずつ下げる。

Lana’s Aid、Xerosic’s Machinations、Nighttime Mineは既存版に存在しないため、カードIDの登録、合法な選択prompt処理、使用または温存理由が必要になる。

したがって、比較Aは既存方策下での実運用上のデッキ差を測るが、厳密な純粋デッキ効果ではない。
