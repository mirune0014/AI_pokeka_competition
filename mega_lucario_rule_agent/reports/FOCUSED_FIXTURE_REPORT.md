# 最小確認結果

## 対象

対象commitは `8c8f43b1478d0d64239ed5190f50a04409dd6f61` である。
runtime manifest SHA-256は `b629317a8acd2fd08f255918ba1351d3956575e1ef8e29dcf22a392a408fd422` である。

## 静的確認

| 確認 | 結果 |
|---|---|
| Gong・手貼り修正fixture | 13 passed |
| 全テスト | 446 passed |
| Ruff check | 成功 |
| Ruff format check | 変更不要 |
| flat import | 成功 |
| deck読込 | 60枚 |

## 今回追加した確認

- 先攻1ターン目、Active Solrock、LunatoneとRiolu系統なし、Gongと闘Energyあり、という停止局面でGongを使う。
- 検索候補は `Lunatone 675 > Riolu 677 > Fighting Energy 6` とする。
- Lunatone不在時はRiolu、両Pokémon不在時はEnergyを実際に取得する。
- full Bench、公開Riolu/Mega、手貼り済み、既に攻撃可能、Activeへの手貼りoptionなしでは狭いGong規則を出さない。
- LunatoneがBenchにいるSolrockの中盤手貼りを `DECK_RULE_V1` が拒否しない。
- LunatoneがいないSolrockには0 damageとなるため、中盤手貼りproposalを出さない。

## 代表局面

同一seed `314159265`、Mega Lucarioを先攻席、相手をhistorical Silver Archaludonとして1局だけ再実行した。
修正前は29手で盤面切れ、0 Prize取得だった。
修正後はGongからLunatoneを取得し、Lunar Cycle、Riolu配置、Riolu手貼りへ進んだ。
最終的に116手まで継続し、2 Prizeを取得したが敗戦した。
action errorは0、max-step到達はなしである。

これはルールが想定どおり発火したことの確認であり、勝率比較ではない。
