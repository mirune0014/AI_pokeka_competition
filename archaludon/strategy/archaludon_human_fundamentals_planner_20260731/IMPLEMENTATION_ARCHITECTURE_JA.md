# 人間プレイ実装アーキテクチャ

## 1. 公開状態の正規化

各callbackで次をserial単位に正規化する。

- Active / Bench / hand / discard / deckCount / Prize枚数;
- HP、最大HP、進化元、付いているEnergy・Tool、状態異常;
- Stadium、ターン中のSupporter・手貼り・逃げ・Stadium使用済み状態;
- 公開された一時効果と攻撃使用禁止;
- 合法optionと、optionが表すカード・対象・攻撃。

名前やoption位置ではなく、card ID、serial、対象serial、効果text hashで
transactionを束縛する。

## 2. 効果レジストリ

カード効果は次の型へ変換する。

- `DAMAGE_MODIFIER`
- `MAX_HP_MODIFIER`
- `DAMAGE_PREVENTION`
- `ATTACK_EFFECT_PREVENTION`
- `DAMAGE_COUNTER_MOVE`
- `ENERGY_ACCELERATION`
- `EVOLUTION_ACCELERATION`
- `SWITCH_OR_RETREAT`
- `HEAL_OR_RETURN`
- `SEARCH_OR_RECOVERY`
- `ATTACK_LOCK`
- `PRIZE_MODIFIER`
- `VARIABLE_RANGE`

効果名をwhitelistするだけでは完了にしない。
各型は、戦闘計算、返し候補、資源台帳、transactionのいずれを更新するかを持つ。

## 3. 行動後資源台帳

同じカード枚数でも場所と生存性を区別する。

- `HAND_READY`
- `DECK_ACCESSIBLE`
- `DISCARD_RECOVERABLE_NOW`
- `DISCARD_NOT_RECOVERABLE_NOW`
- `IN_PLAY_PROTECTED`
- `IN_PLAY_EXPOSED`
- `IN_PLAY_CERTAINLY_LOST_ON_REPLY`
- `ATTACHED_AND_RECOVERABLE`
- `ATTACHED_AND_LOST`

計画の各action後、さらに公開された最善の返し後まで射影する。
現在観測の総数をそのまま「残存資源」に使わない。

## 4. 完全なターンプラン

一つのplanは次を持つ。

- 今ターンの最終攻撃と対象;
- その攻撃に必要な進化・Energy・Stadium;
- 先に使う検索・ドロー・回収と目的;
- 各カード効果の全callback;
- 攻撃後のPrize;
- 相手の公開された返し候補;
- 返し後のActive、次アタッカー、残存資源;
- 次の自分の攻撃までの確定手順。

単一のPLAYやEVOLVEだけを、後続攻撃と切り離して評価しない。

## 5. 辞書順の決定

次の層を上から順に比較し、上位層で差があれば下位層を見ない。

1. engine合法性・継続中transaction;
2. 今ターンの確定勝利;
3. 次ターンの確定敗北回避;
4. 今ターンのPrizeと相手の残りPrize;
5. 相手の確定返しを止める、Bossを要求する、攻撃を継続する;
6. 準備済み脅威除去と次アタッカー;
7. 正確な次のKOターン;
8. 行動後・返し後の資源台帳;
9. 山札切れ耐性と逆転アウト;
10. 完全に同等な場合だけ決定的なserial順。

固定点の加算で上位層と下位層を相殺しない。

## 6. 不確実性

- 公開情報だけで確定するものはexactとして扱う。
- 通常の手貼り1枚、公開済み検索、公開済み進化は別tierで具体的に扱う。
- コイントスと可変打点は最小・最大・期待範囲を保持する。
- 未知手札は、残り枚数と必要カード枚数からaccess tierを作る。
- 対戦履歴から相手の行動方策を学習・模倣しない。
- 戦闘に関係する未対応効果があれば確定判定を止め、完成済み親へ戻す。

## 7. 実行とtelemetry

最終agentは次のどれを返したかを記録できるようにする。

- `HARD_TERMINAL`
- `HARD_LOSS_AVOIDANCE`
- `PUBLIC_RETURN_CONTROL`
- `CARD_PURPOSE_TRANSACTION`
- `TURN_SEQUENCE_TRANSACTION`
- `RESOURCE_CONSERVATION`
- `PARENT_FALLBACK`
- `FAIL_CLOSED_UNKNOWN_EFFECT`

transactionごとに開始、各callback、完了、rollback理由を記録する。
同一callbackの再送では同じ意味上の行動を返す。

## 8. 完了判定

各ルール群は次を満たした場合だけ完了とする。

- 正例で発火する。
- 境界負例で発火しない。
- その後の全callbackと攻撃まで完走する。
- 両seatで同じ意味を持つ。
- option順や同一IDの物理コピー差に依存しない。
- invalid、例外、stale transaction、duplicate不一致がない。
- 実戦履歴で発火理由と勝敗への因果を分離して説明できる。
