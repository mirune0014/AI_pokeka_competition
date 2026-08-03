# HumanViewState スキーマ

## 原則

HumanViewStateは対戦ごとに固定したhuman_seatの視点で新規構築する、ライブ表示専用の許可リストDTOです。

スキーマバージョンは1です。

元状態から禁止フィールドを後で削る方式は採用しません。

## トップレベル

| フィールド | 意味 |
|---|---|
| schema_version | HumanViewスキーマの整数バージョンです。 |
| match_id | 対戦IDです。 |
| revision | 後方互換用の状態リビジョンです。 |
| state_revision | 受理済みbattle_selectごとに増える状態リビジョンです。 |
| step_id | 現在の受理済みステップIDです。 |
| phase | 許可済み状態機械値です。 |
| human_seat | 固定した人間座席です。 |
| acting_seat | 現在のcurrent.yourIndexです。 |
| turn_player | 先攻とターン番号から導いた現在ターンのプレイヤーです。 |
| can_act | 未終局かつ選択者が人間の場合だけtrueです。 |
| turn | エンジンのターン番号です。 |
| first_player | -1、0、1のいずれかです。 |
| result | -1、0、1、2のいずれかです。 |
| turn_flags | サポート、スタジアム、エネルギー、にげるの公開フラグです。 |
| stadium | 公開スタジアムまたはnullです。 |
| human | 人間プレイヤーの状態です。 |
| opponent | 相手の公開状態です。 |
| looking | ルール上、人間へ現在公開されている一時領域だけです。 |

## プレイヤー状態

両プレイヤーはseat、active、bench、bench_max、deck_count、discard、prize_count、hand_count、conditionsを持ちます。

人間プレイヤーだけがhandを持ち、相手状態にhandキーはありません。

両プレイヤーともdeckキーを持ちません。

サイドは枚数だけを持ち、内容を持ちません。

セットアップ中は相手のバトル場とベンチを空配列にし、枚数もカード実体も同時公開前に示しません。

## カードとポケモン

公開済みカードまたは人間所有と検証したカードはcard_id、state_token、fallback_nameを持ちます。

state_tokenは対戦秘密値、所有者、エンジンserialからHMAC生成し、生serialを渡しません。

同じカードが手札から盤面へ移動してもトークンを維持し、盤面ショートカットを現在の合法手DTOへ対応付けます。

ポケモンはhp、max_hp、appear_this_turn、energies、energy_cards、tools、pre_evolutionを追加で持ちます。

ダメージはUIでmax_hp - hpとして表示します。

## 公開ログ

公開ログは独立した許可リスト変換を通します。

相手のドローは枚数だけを残し、相手が引いたカードIDを残しません。

移動ログはゾーンだけを残し、カードIDとserialを残しません。

## 禁止情報

いずれの深さにもserial、deck、search_begin_input、selected、raw_observation、visualize_data、score、reason、ai_optionsを許可しません。

AI手札、山札順、サイド内容のカナリア値をHumanView、公開ログ、UTF-8 JSON IPCフレームから検出するテストを実行します。

同じカナリアが終局後用のFullReplayFrameには存在することも別テストで確認します。
