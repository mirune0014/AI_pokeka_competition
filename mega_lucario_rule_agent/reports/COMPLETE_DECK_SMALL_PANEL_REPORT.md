# 完成後の小規模パネル

## 目的

個別ルールごとの両席比較は行わず、主要ルール接続後に一度だけ自然対戦の重大停止を探した。
対象は修正前commit `45af7fcba6c5e1961a689bedc9977083902e4e53` である。

## 固定schedule

- 相手4種: historical Silver Archaludon、Archaludon peak、Alakazam Capbloo Gold、Marnie Kazuki Live
- 各相手について両席5 seed
- 合計40 paired rows
- action error 0、max-step到達0、重複key 0

| 相手 | 局数 | historical Silver勝 | Mega Lucario勝 |
|---|---:|---:|---:|
| historical Silver | 10 | 5 | 0 |
| Archaludon peak | 10 | 5 | 0 |
| Alakazam Capbloo Gold | 10 | 8 | 0 |
| Marnie Kazuki Live | 10 | 10 | 0 |
| 合計 | 40 | 28 | 0 |

## 発見と修正

代表seedでは、Active Solrock、Gong、闘Energyがあるのに先攻初手を終了していた。
原因は、欠けたLunatone単体だけで山札存在保証を要求したことだった。
さらに、Lunatone完成後の正しい中盤手貼りproposalがresolverのtier許可漏れで拒否されていた。

commit `8c8f43b` で次を修正した。

- Gongの保証を `{Lunatone, Riolu, Fighting Energy}` のunionで証明する。
- 実際の検索順を `Lunatone > Riolu > Energy` とする。
- Energyを保証用ダミーではなく実選択可能な最終fallbackとする。
- `DECK_RULE_V1` で `ROUTE_CRITICAL_MANUAL_ATTACH` を許可する。

## 修正後の扱い

ユーザー指示に従い、40局パネルは再実行していない。
同一seedの1局だけで、Gong、Lunatone、Lunar Cycle、Riolu、手貼り、攻撃への進行を確認した。
敗戦したため、競技強度の完成やKaggle提出妥当性は主張しない。
