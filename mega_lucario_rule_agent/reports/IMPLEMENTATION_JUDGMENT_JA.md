# 実装判断

## 結論

要件書の主要なルール系統は、固定60枚の実行可能Agentとして接続した。
Setup、engine形成、Mega line、1 Prize line、検索、手貼り、進化、攻撃、Energy配置、Supporter、gust、回復、入れ替え、保護、fallbackまでが単一resolverで動く。

ただし、競技上の完成とは判断しない。
修正前の完成後パネルは0勝40敗で、初動停止を一つ修正した後も代表局は敗戦した。
現段階は「実装完成、強さの改善は未完」である。

## 上位チーム公開盤面分析との対応

285公開対戦の分析では、相手デッキ名より、開始順、自分Active、相手公開ActiveとHP、即時攻撃可能性、盤面欠損が行動差を説明した。
主要6群では、Solrockあり・Lunatone欠けからLunatoneを選ぶ観測が98/105、Lunatoneあり・Solrock欠けからSolrockが83/99、engine完成・Riolu系なしからRioluが80/94だった。
本実装はこの順序を固定対面ラベルではなく公開盤面ruleとして採用した。

攻撃ではAura JabとMega Braveが同時合法な477件で、Aura Jab 104件、Mega Brave 373件だった。
本実装は単純頻度を模倣せず、KO、Prize、連続使用制約、次attacker完成で選ぶ。
Wally、Boss、Hariyama、Switch、Aura Energy対象も同様に、replay actionを教師ラベルにせず公開結果のbreakpointへ変換した。

## 今回の判断

- ルール単位の広い比較をやめ、想定局面fixtureへ切り替えた判断は妥当である。
- 完成後の小パネルは、勝率測定より重大な初動停止を早期に見つける役割を果たした。
- 修正後は同一seed1局で発火と進行だけを確認したため、ユーザー指示の速度優先に沿っている。
- 現在のAgentをKaggleへ提出する根拠はまだない。
- 次の修正は、新しい実戦traceで最初に止まった公開局面を一つずつ直すのが費用対効果に優れる。

詳細な集計CSV、対面別統計、推定ルール、数値監査は同梱する `majkel1337_public_board_policy_bundle_20260804.zip` を参照する。
