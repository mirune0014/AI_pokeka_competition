# フーディン新デッキ v0 移植設計

## 結論

`alakazam_newdeck_v0_port`は、submission `54906455`の凍結方策を、今回選定した60枚へ機械的に移植した版である。

この段階では新しいセットアップ、エネルギー、攻撃、対面、継続攻撃の戦術を追加しない。

目的は、9枠の変更を方策へ認識させたうえで、旧方策の判断を比較可能な基準として残すことである。

## 入出力

| 項目 | 固定値 |
| --- | --- |
| 基準方策 | `alakazam_800_frozen` |
| 出力方策 | `alakazam_newdeck_v0_port` |
| 旧normalized deck hash | `f2e179fb82cb91504ccd207d707ca5e7be8afc7228df26a7b287c6205064507c` |
| 新normalized deck hash | `4414e8995e50c7a00d4b6aa7d9229f63c1dff5261643ec7cd86c4e329113ed69` |
| 新raw `deck.csv` SHA-256 | `F598F5E578D0440C96DC0492EAECF2E19739B7A23225BE57114A724EF7D0FB94` |
| 方策closure SHA-256 | `D9ADBC03054AB1D2FFD1E1955D734DB1D14DA74C9D1088249A271F98EBCECD46` |

旧版と新版はカード多重集合で51枠が共通し、9枠が異なる。

完全な差分は`reports/alakazam_deck_diff_51_of_60.md`に固定した。

## 変更した処理

`_cumulative_parent.py`のデッキ枚数定数を、新しい60枚へ更新した。

新規カードIDとして、Lana's Aid `1184`、Xerosic's Machinations `1197`、Nighttime Mine `1266`を登録した。

この3種類は`V0_GENERIC_HOLD`へ明示的に登録した。

任意のMAIN `PLAY`ではスコア`-1`、理由`V0_GENERIC_HOLD`として保持し、旧方策の未知Trainer既定値`10000`へ流入させない。

強制`DISCARD`でこの3種類が合法な`CARD`候補として提示された場合だけ、スコア`1`、理由`V0_GENERIC_FORCED_DISCARD`を付ける。

それ以外のprompt、カード、順位付け、transaction、fallbackは凍結方策を継承する。

削除カードのIDと公開情報上の意味は残した。

そのため、相手がGenesect、Psyduck、Lucky Helmet、Handheld Fan、Battle Cageを提示しても、既知カードとして扱える。

一方、新デッキ自身から削除カードを使う経路は、枚数0のため到達不能である。

## 観測用sidecar

`main.agent`は、継承方策が行動を返した後に`LAST_V0_PORT_TRACE`を更新する。

sidecarは、選択行動、合法な追加カードのMAIN候補、強制discardで選ばれた追加カード、理由タグを記録する。

sidecarはスコアリング、transaction、選択結果から一度も参照されない。

継承方策が返したaction objectを、そのまま呼び出し元へ返す。

したがって、sidecar自体は方策変更ではなく、同値性と追加カード処理を監査するための観測器である。

## 意図的に実装しないこと

Lana's Aid、Xerosic's Machinations、Nighttime Mineを任意に使用する戦術は、v0には実装しない。

4枚目のAlakazam、4枚目のEnhanced Hammer、3枚目のBoss's Ordersを特別扱いする規則も追加しない。

継続攻撃、次アタッカー復旧、Hand Power手札床、対面別優先度は、v1以降の独立仮説として扱う。

この制限により、比較Aは「デッキを移植するために必要な処理」と「新戦術」を混同しない。

## 変更ファイル

| ファイル | 変更内容 | SHA-256 |
| --- | --- | --- |
| `_cumulative_parent.py` | 枚数定数、追加3カードのhold、強制discard処理 | `71D884F3545372B246AB7B7F76B9209A49C3544D3DB93496B4D3D6A1880DEFC1` |
| `main.py` | 動作非干渉のv0 sidecar | `6FD9519ED9805901F6E14C0F9D56B13E462E92A72DBE73BF878E21EB1D330ACD` |
| `runtime/main.py` | sidecarの動的公開 | `62FDCAC6A831F0F26EE85C6D64E5C6E4924BF55AD149E2A94C673F1F2BF0E629` |
| `test_v0_port.py` | deck、理由、委譲同一性、runtimeの検査 | `58F723FB15C234EE27B12A677F44DC2106D5391D199123231870AC278E1C2210` |

上記以外の共有Pythonファイルは、凍結版とbyte単位で同一である。

## 静的・構造検証

全32 Python sourceのcompileは成功した。

`test_v0_port.py`の7 testはすべて成功した。

testは、60枚と正確な枚数、normalized hash、ACE SPEC 1枚、新規3カードのmetadata、holdとforced-discard理由、委譲actionのobject同一性、sidecar、runtime deck一致、無関係な共有sourceのbyte一致を検証する。

Historical-Silverを相手に、同一seed `2026101741`の両seat smokeを実行した。

両試合ともexit code `0`、action error `0`、max-step hit `0`で完了した。

smokeの勝敗は構造検証であり、強度の採否根拠には使わない。

## 比較Aのゲート

v0からv1へ進むには、次をすべて満たす必要がある。

- invalid action、未捕捉exception、timeout、max-step hitが0である。

- 追加3カードが未知カード既定処理へ流入せず、holdまたはforced-discardとして明示的に処理される。

- 保存済みreplayの共有51枠比較で、凍結版とv0の選択actionに意図しない差がない。

- 同一opponent、seed、seatで比較Aの全scheduleが欠落なく完了する。

勝率差だけでは、この移植ゲートの合否を決めない。

新デッキは9枠が異なるため、実対戦の盤面推移まで凍結版と一致することは要求しない。

## 既知の制約

新規3カードを任意に使わないため、v0は新デッキの戦術的上限を表さない。

強制discardは、未対応カードを既存のscore 0候補より先に捨てる合法で決定的な処理であり、最適discardの主張ではない。

`LAST_V0_PORT_TRACE`は最後のcallbackだけを保持する可変観測値であり、transaction stateではない。

ローカル評価は実装済みproxy agentにも依存するため、Kaggle leaderboardの勝率推定としては扱わない。
