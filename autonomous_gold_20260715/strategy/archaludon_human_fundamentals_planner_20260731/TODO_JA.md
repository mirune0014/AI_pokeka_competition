# Archaludon 基本プレイ再構築 TODO

## 目的

銀圏に到達した Archaludon の完成済み判断を壊さず、強い人間なら通常行わない
基本的な悪手を、公開情報だけを使う決定的な条件分岐で除去する。

「意味を表す関数やタグがある」だけでは完了としない。
実際に Kaggle が呼ぶ最後の `agent` が、その判断を最終行動として返し、
複数 callback からなるカード効果を最後まで正しく完走した場合だけ完了とする。

カードごとの使用目的・温存条件・ハード分岐は
`PLAYER_FUNDAMENTALS_ACCEPTANCE_MATRIX_JA.md` を受入仕様とする。
現行候補が未対応の相手特性・道具・攻撃効果は
`ROOT_PUBLIC_EFFECT_COVERAGE_GAPS.md` を実装台帳とする。
最初に追加する決定的な効果の数式と受入条件は
`EFFECT_REGISTRY_PHASE1.md` を仕様とする。
公開状態、効果レジストリ、行動後資源台帳、完全ターンプラン、
辞書順条件分岐、telemetry の構造は
`IMPLEMENTATION_ARCHITECTURE_JA.md` を実装仕様とする。
旧固定点の各到達経路と置換担当は
`SCORE_FALLBACK_REPLACEMENT_MAP.md` を台帳とする。
正しい提出席だけの自然なカード使用頻度は
`ROOT_TARGET_SEAT_ACTION_FREQUENCY.md` を実装順の参考にする。

## 現在の判定

記号は `[x]` が最終行動まで確認済み、`[-]` が意味解析または一部経路まで、
`[ ]` が未実装を表す。

- [x] TODO と受入条件を作成した。
- [x] 全面置換型の human-fundamentals planner v1 を実装した。
- [x] compile/import、60枚、ACE SPEC 1枚、決定性、両席 engine smoke を確認した。
- [x] 固定 seed・両席で親と比較した。
- [x] v1 を提出禁止と判定した。
- [x] 銀圏系の親判断を保持する修正版 v2 を実装した。
- [x] PCRD v2 修正版が対象の基本プレイを実際の engine callback で完走することを確認した。
- [x] v2 は固定 seed・両席の一次ゲートで破壊的な絶対性能低下がないことを確認した。
- [ ] 提出可能な archive を作る。

v1 の固定比較は親 `8/16`、候補 `1/16` だった。
これは「人間原則が弱い」という証拠ではなく、完成済みの初期処理とターン手順まで
全面置換し、次の基礎動作を壊したことが主因である。

- 有効な初期手札でマリガンを選んだ。
- 相手のマリガンに対する追加ドローを 2 枚ではなく 0 枚にした。
- Explorer、Poké Pad、ベンチ形成より先にエネルギーを付け、そのまま攻撃して
  セットアップ機会を失った。
- Explorer で鋼エネルギーを捨て札へ送り、Archaludon ex の Assemble Alloy で
  回収して即攻撃する連続手順を分断した。

### v2 一次ゲートの到達点

v2 は全面置換をやめ、完成済み親を必ず候補として残す。
新しい行動は、公開情報だけで現在の攻撃・Prize・返しを悪化させず、
盤面形成、攻撃継続、Prize 経路、生存のいずれかを厳密に改善する
完全な transaction を証明できる場合だけ親を置換する。

- 固定比較は親 `8/16`、v2 `8/16`、改善 `0`、悪化 `0`、同結果 `16`。
- Historical Silver は双方 `3/8`、Alakazam は双方 `5/8`。
- 48 回の実行はすべて正常終了し、action error と max-step は 0。
- 全8件の最初の行動差を点検した。6件は初期盤面に Duraludon を1体だけ置く変更、
  2件は同じIDの Duraludon の物理コピー差で、悪手・未分類は 0。
- v1 が壊した seed `2026073117` の Explorer 先行局面は、両相手とも親と同じ
  Explorer → Poké Pad → Duraludon形成 → 手貼り → 攻撃へ戻った。

これは「基本プレイ全体の完成」ではない。
親を壊さずに条件分岐を追加できる安全な土台が一次ゲートを通った、という判定である。
以下では、v2 で実装・確認済みの狭い項目だけ `[x]` とし、
カード効果、共通ダメージ計算、相手特性、Prize race など未完成の項目は残す。

### 共通戦闘・返し計算候補の進捗

`archaludon_public_combat_return_dominance_v1` では、次を候補実装した。
ただし、これはまだ採用済みを意味しない。

- 自分と相手で共通のダメージ計算器を使う。
- Weakness、Resistance、Full Metal Lab、Hero's Cape、Jumbo Ice Cream、
  Hammer In、Raging Hammer、Metal Defender、Coated Attack、
  Turbo Flare、現在の Powerful Hand を扱う。
- Sturdy、Run Away Draw、Prize値、KO後の昇格、逃げ0を含む逃げ可否、
  手貼り1枚までの公開された返しを扱う。
- 非ex、ex、未進化の完全な攻撃プランを比較し、非ex一律減点を上書きする。
- 未対応の公開効果が戦闘結果に関係する場合は、推測で0扱いせずv2へ戻る。

focused test `17/17`、継承test `16/16`、両席の対象transaction `2/2`、
固定safety16は親 `8/16`・候補 `8/16`、invalid・例外・duplicate不一致は0。

一方、Historical-Silver 200戦では候補が行動を変えた11戦のうち、
勝敗改善1件と悪化1件を確認した。

- 改善: 非ex進化後の Coated Attack がBasicの返しを防ぎ、
  相手にBossを要求して敗戦を勝利へ変えた。
- 悪化: 返しに確実に倒されるActiveへ非ex進化札を投入し、
  同じPrize・同じ生存のままchipだけ増やした。

原因は、計画後に消費した進化札を資源台帳から減らさず、
手札に温存した進化札と倒されるActiveへ投入した進化札を同価値にしたことにある。
したがって、共通戦闘候補はこのまま採用しない。
次版では、行動後の資源台帳と次の辞書順条件分岐を必須にする。

1. 確定勝利。
2. 確定敗北回避。
3. Prize取得・生存・攻撃継続を変える進化。
4. 上記を変えないchipだけの進化を禁止。
5. 最後にだけ残存資源を比較。

固定760戦の最終再計算でも親 `474/760`、候補 `474/760`、
改善1、悪化1、同結果758だった。16戦で行動が変わり、
完遂した evolve→Coated Attack は17回・3相手に留まった。
独立数値監査は promotion gate を `FAIL` と判定した。
したがって v1 は archive / Kaggle 提出禁止、修正版 v2 の実装素材にのみ使う。
最終戦略判断 `PCRD_V2_FINAL_JUDGMENT.md`
（SHA `3A078C3F799308CF01B75E20237A1841F3A3AE4EE743914F6A12D33EFA493634`）
は、v2 を「行動後・公開返し後の場所別資源台帳＋ハード辞書順選択器」
として単一候補実装する方針を選択した。

### PCRD v2 修正版の到達点

`archaludon_post_reply_resource_lexicographic_v2` を実装し、Root が独立再検証した。

- 候補 `main.py` SHA:
  `4B9851F54A49DE19614F4E9AACBB430539A2DB8CCCEA3EC57108FF21DDB34ED8`
- 親の先頭 `668,927` bytes と non-main 11 files は byte-identical。
- unit test は `38/38 PASS`。
- 既知16局面は、正例 `3/3`、境界 `1/1` は明示的に親へ戻り、
  負例 `12/12` は親と同じ意味行動になった。
- 両席の実 engine transaction は開始・完了 `2/2`、
  invalid・例外・stale は0、duplicate再試行は同じ意味行動だった。
- 進化札、進化元、付属Energy、Toolを、返しの確定KO後も手札資源と同価値にする
  欠陥を除去した。
- 同じPrize・同じ生存・同じ後続のまま非致死chipだけ増やす進化をハード拒否した。
- 現在Prizeを取る、Basicの返しを防ぐ、確定後続を作る進化は保持した。

Root verification:
`implementation/archaludon_post_reply_resource_lexicographic_v2/ROOT_VERIFICATION.md`

これは次の effect registry と Trainer transaction を積むための安全な開発親であり、
単独の正式な強度採用や Kaggle 提出候補とはまだ判定しない。

### 決定的公開効果レジストリ第1段階

`archaludon_deterministic_public_effect_registry_phase1_v1` を、
PCRD v2 を一度だけ呼ぶ suffix として実装し、Root が独立再検証した。

- 候補 `main.py` SHA:
  `02F37B3F0EC684018647E59C74FCA0EA22120500D5D496BCA4C4322806FFA9B3`
- 直接親の先頭 `829,528` bytes と non-main 11 files は byte-identical。
- レジストリは34効果・37 bindingで、ID・entry ID・本文hashを全件確認した。
- focused test `32/32`、継承test `38/38` が通った。
- frozen16 は正例3、境界1、負例12で、両seatを含む。
- 既存 Assemble Alloy transaction の実engine確認は両seat `2/2` 完了し、
  invalid・例外・staleは0だった。
- Shadow Bulletの単一Bench対象、Flower Curtain、Adrena-Brainの任意供給元と対象、
  Battle Cage、Spiky Energy、Mist/Rock、Premium Power Pro重複使用、
  Run Away Drawの残り枚数ドローなどを共通計算へ入れた。
- 相手の非公開手札のカードIDから未来の経路を作らない。
- Adrena-Brainで処理できない割当が残る場合と、非終端のActive KO後に必要な
  強制昇格・続行を証明できない場合は、返し全体を未確定として親へ戻す。

ただし、34効果すべての使用判断が完成したわけではない。

- 20効果は戦闘・返し計算へ直接到達する。
- Assemble AlloyとTurbo Flareは既存transactionが行動を所有する。
- 9効果は可視callbackの観測までで、新しい行動を選ばない。
- Shadow Bullet、Trading Places、Teleportation Attackは意味経路までで、
  最終対象callbackは親が選ぶ。

Root verification:
`implementation/archaludon_deterministic_public_effect_registry_phase1_v1/ROOT_VERIFICATION.md`

したがって、この段階は安全な開発親として受け入れるが、
基本プレイ完成またはKaggle提出可能とは判定しない。

## P0: engine とセットアップ

- [x] 有効な初期手札では必ず `NO MULLIGAN` を選ぶ。
- [ ] マリガンが必要な手札だけを引き直す。
- [x] 相手のマリガンによる任意追加ドローは、山札切れなどの明確な害がない限り
  最大枚数を選ぶ。
- [ ] Turbo Flare を初動にする手札では後攻を選ぶ。
- [ ] Explosiveness が成立する Cinderace を Active に置く。
- [x] Duraludon を Turbo Flare の加速先、次アタッカー、donk 防止として
  Bench に置く。
- [x] SETUP、強制選択、進化先、検索先、捨て札、エネルギー配分など、
  非 MAIN callback は既知のカード効果または完成済み親処理を使う。
- [ ] 未知 callback の fallback は合法かつ決定的にするが、既知 callback を
  「最小値」「NO」で一括処理しない。

## P1: 一ターンを行動単位ではなく連続手順として扱う

- [ ] ターン開始時に「このターンの攻撃」「必要エネルギー」「必要進化」
  「必要な捨て札」「次アタッカー」を先に決める。
- [ ] 同じ攻撃を維持できるなら、情報を増やす Explorer / Pokégear / Poké Pad を
  不可逆な進化・手貼り・攻撃より先に使う。
- [ ] 手札保護や確定攻撃維持のため先に手貼りすべき場合だけ、ドローより先に付ける。
- [-] Explorer で鋼を捨てる → ex 進化 → Assemble Alloy →
  足りない分を手貼り → 攻撃、を一つの transaction として扱う。
- [ ] Cinderace → Turbo Flare → 複数 Duraludon への必要量配分を
  一つの transaction として扱う。
- [ ] 攻撃でターンを終了する前に、現在の攻撃を壊さず次アタッカーを作れる
  行動を完了する。
- [ ] ただし「使えるグッズを全部使う」のではなく、各カードに
  現攻撃成立、盤面形成、回収、勝利短縮、生存のいずれかの目的を要求する。
- [ ] 目的がなく山札と手札を消費するだけのカードは温存する。

### 次期実装順序: 後続アタッカー形成から上位戦術まで

Episode 89347400 の Bench 0 敗戦を受け、従来の Task 4〜8 より前に、すべての検索カードが共有する「攻撃前の後続アタッカー形成・Bench 0 継続ゲート」を挿入する。従来の Task 4〜8 は Task 5〜9 に繰り下げる。

| Task | 実装項目 | 所有する目的 |
| --- | --- | --- |
| 4 | 攻撃前の後続アタッカー形成・Bench 0 継続ゲート | 非終局攻撃が、同じターンに両立する Basic の検索・配置・次アタッカー育成を上書きしないようにする。目的は単なる盤面切れ防止ではなく、返しの後も攻撃できる実行可能な後続を作ること。 |
| 5 | Poké Pad の検索計画 | 検索開始、検索対象、Bench 容量、配置、次のエネルギー・進化・攻撃までを一つの目的で所有する。 |
| 6 | Ultra Ball の捨て札・検索計画 | 捨て札2枚、検索対象、配置後の役割、Turbo Flare との接続を一つの transaction にする。 |
| 7 | Pokégear と Supporter の選択 | Boss、Explorer、Lillie の使用目的と、そのターンに実行できる経路を確定してから使う。 |
| 8 | Lillie の使用・温存 | 手札枚数ではなく、使用で失う確定経路と、使用後に得る盤面改善を比較する。 |
| 9 | 有害 KO 回避・Boss 対象・逆転分岐 | 現在の攻撃、Prize 交換、返しの致死、逆転確率と交差するため、最後に上位戦術として統合する。 |

#### Task 4: 攻撃前の後続アタッカー形成・Bench 0 継続ゲート

- [x] 共通ゲートはカード効果を重複実装せず、後続形成の目的を Task 5 と Task 6 の各 transaction に渡す。
- [x] 行動優先順位を次の順で固定する。
  1. このターンの勝利・最終 Prize の確定
  2. 検索、Basic 配置、進化による次ターンの盤面切れ回避
  3. 非終局攻撃と同じターンに両立する、実行可能な次アタッカー形成
  4. 非終局攻撃
- [x] Bench 0、または相手の返しを受けた後の実行可能な後続が0体のとき、`SECURED_ATTACK_NOW` が親の盤面形成行動（Poké Pad、Ultra Ball、公開捨て札の Basic を対象にした Night Stretcher）を上書きしない。
- [x] `card_or_target_binding_unknown` は攻撃へ倒す理由にせず、親またはカード固有 transaction を維持する理由として扱う。
- [ ] Cinderace の基本経路を `SEARCH_BASIC -> BENCH_BASIC -> TURBO_FLARE -> ENERGY_TO_EXECUTABLE_SUCCESSOR -> NEXT_ATTACKER_READY` として所有する。
- [ ] 検索が不発なら、その同じターンに Turbo Flare へ戻る。
- [ ] 検索が成功したら、対象の serial と必要エネルギー差分を Turbo Flare のエネルギー配分へ渡す。
- [ ] Basic と Energy は、次の攻撃までの差分を安全に縮められるなら盤面へ変換する。特に Xerosic 前は、目的のある資源を手札に抱えない。
- [ ] ただし、最終 Prize、明確な最終 Prize 用 Boss の標的化、確定 Bench ダメージ、最後の Bench 枠、返しに確実に倒される育成先では温存または別経路を選ぶ。

Episode 89347400 を回帰アンカーにする。

- step 12 では、親の Explorer または検索準備を Turbo Flare が早取りした。
- step 19 では、親の Ultra Ball を Turbo Flare が上書きした。
- 完全な履歴では Duraludon が山札に3枚、Prize に1枚あり、Ultra Ball は実際に後続形成へ到達できた。
- Task 1〜3 は11個の canonical decision を変更しておらず、直接原因は継承された攻撃優先 wrapper だった。
- Task 4 の完了条件は、上書きを止め、後続形成目的をカード固有 transaction に渡すところまでとする。Episode 89347400 の経路全体は Task 4 と Task 6 の組み合わせで修復する。

Task 4 実装結果（2026-08-02）:

- `archaludon_public_pre_attack_executable_successor_bench_zero_continuity_gate_v1` として、攻撃優先 wrapper 内に stateless な veto-only gate を実装した。
- 最終 Prize の確定攻撃と既存 transaction owner を最優先し、それらがない場合だけ、Bench 0 または公開情報から実行可能な後続が0体と証明できる局面で親の盤面形成行動を維持する。
- 集中 fixture は33件すべて合格した。Episode 89347400 は11 decision 中 step 12 の Explorer と step 19 の Ultra Ball の2箇所だけが意図どおり親行動へ戻り、残り9箇所は不変だった。
- 歴史 replay 8件・389 decision の shadow では7箇所だけが同じ目的で変化し、最終攻撃、既存 owner、実行可能な後続がある局面は変更しなかった。両 seat の実エンジン smoke も action error 0 で終了した。
- Task 4 は「攻撃による上書きを止める」共通ゲートまでを所有する。検索対象、Ultra Ball の捨て札、検索後の配置、Turbo Flare への引き渡しは Task 5 と Task 6 で transaction として完成させる。

#### Task 5: Poké Pad の検索計画

- [x] Poké Pad を使う前に検索目的を宣言し、検索開始、公開された対象、手札への移動、配置、次のエネルギー・進化・攻撃までを一つの transaction owner で追跡する。
- [x] `DURALUDON_EXECUTABLE_SUCCESSOR` は Duraludon の物理コピーを公開時に決定論的に bind し、配置後は既存の Turbo Flare・エネルギー配分・攻撃継続計画へ引き渡す。
- [x] `NONEX_COATED_ATTACK_CONVERSION` は、公開情報だけで同じターンの非ex Archaludon進化から Coated Attack の正確なKOまで完走できる場合に限って検索する。
- [x] 宣言した対象が公開されなかった場合、無関係な Basic へ差し替えず、空選択が合法なら空選択して同じターンの確定攻撃へ戻る。
- [x] Cinderace 666 は Explosiveness がゲーム開始時だけの効果なので、途中配置用の検索対象にしない。
- [x] 最終Prize、既存 owner、terminal callback、重複・option順序、Bench容量喪失を fail-closed で扱い、二重 owner を作らない。

Task 5 実装結果（2026-08-02）:

- `archaludon_public_poke_pad_declared_executable_role_transaction_v1` として、従来の狭い Pad watch を目的宣言型 transaction に置き換えた。
- 集中 fixture は69件すべて合格し、Duraludon 後続形成と非ex Coated Attack 即時KOの全callback経路を両席で完走した。
- Episode 89347400、89285518、89282820 の合計145 decisionでは親との行動差が0で、記録済みの通常進行を変えていない。両席の実エンジン smoke も action error 0 で終了した。
- Task 5 は Poké Pad だけを所有する。Ultra Ball の捨て札2枚、検索対象、配置後の役割は Task 6 で別 transaction として実装する。

#### Task 6: Ultra Ball の捨て札・検索計画

- [x] Ultra Ball を使う前に、検索目的、検索対象、捨て札2枚、配置または進化、Assemble Alloy、手貼り、現在の攻撃、Turbo Flareへの引き渡しまでを一つの transaction として確定する。
- [x] 手札の全ての異なる2枚組を比較し、重複札、Supporter、進化札、回収札、手札エネルギーの機会費用を固定カード点ではなく完成経路で比較する。Boss、進化、回収、Supporter、Stadium/Tool、手貼り・Turbo用エネルギー、次攻撃役に必要な物理カードまたは最低枚数は捨て札候補から除外する。
- [x] トラッシュに鋼エネルギーが2枚以上ある場合、手札エネルギーを「Alloyで戻せる有用なコスト」として優遇しない。
- [x] 攻撃役1エネ、トラッシュ1エネ、手札1エネでは、`Alloy 1枚＋手貼り1枚` と `手札エネを捨ててAlloy 2枚` の両経路を比較する。
- [x] 検索対象不在、重複callback、option順変更、所有権競合では代替対象を捏造せず、安全に親へ制御を返す。

Task 6 実装結果（2026-08-02）:

- `archaludon_public_ultra_ball_declared_complete_route_transaction_v1` として、従来のUltra Ball個別評価を目的宣言型の完全transactionへ置き換えた。
- 集中fixtureは210件すべて合格した。両席で5種類の検索目的、捨て札比較、Alloyと手貼りの配分、必要札の物理的保護、重複callback、空振り、所有権競合を確認した。
- Episode 89280661ではLillieとExplorerではなく重複Ultra Ball 2枚を捨てる。Episode 89291523では目的のないUltra Ballを使わず、ベンチのArchaludon exへ手貼りする。Episode 89347400の記録済み11判断は不変だった。
- 両席の実エンジンsmokeはaction error 0、手数上限到達なしで終了した。最初の最終監査で見つかったhard protection不足も修正し、再監査でTask 6のcommit/pushが承認された。これは破綻がないことの確認であり、勝率改善の主張ではない。

## P1: カード効果を理解した資源利用

- [x] Poké Pad は検索前に実行可能な役割を宣言し、検索対象、Bench容量、配置、後続育成または同ターンの攻撃までを一つの transaction として所有する。Task 5 の `PUBLIC_POKE_PAD_DECLARED_EXECUTABLE_ROLE_TRANSACTION_V1` で完了した。
- [x] Ultra Ball は検索対象と安全な捨て札2枚を使用前に確定し、検索、配置または進化、Alloy、手貼り、攻撃またはTurbo Flareへの引き渡しまでを Task 6 の `PUBLIC_ULTRA_BALL_DECLARED_COMPLETE_ROUTE_TRANSACTION_V1` が所有する。具体的な既存経路に必要な物理カードと最低枚数も捨て札から保護する。
- [-] Pokégear は必要な Supporter とその使用目的を決めてから使う。
- [-] Explorer は取得札、捨て札、Assemble Alloy、残り山札を一緒に評価する。
- [ ] Lillie は手札改善と山札回復を評価し、確定攻撃資源を戻す害も評価する。
- [ ] Night Stretcher は回収対象と回収後の具体的な攻撃経路を確定する。
- [ ] Jumbo Ice Cream は生存ターン増加と Raging Hammer 火力低下を比較する。
- [ ] Hero's Cape は被KO回数または Prize 経路が変わる対象に付ける。
- [ ] Full Metal Lab は自分と相手の鋼ポケモン双方のダメージを30軽減して再計算する。
- [ ] Boss は終端勝利、高Prize KO、準備済み脅威除去、確実な1ターン獲得に使う。

### Pokégear / Boss transaction 第1段階

`archaludon_purpose_first_pokegear_boss_transaction_v1` を実装し、
Root が独立再検証した。

- Pokégear を使う前に、`FINISH_NOW`、`AVOID_EXACT_LOSS`、
  `PRESERVE_ATTACK_CHAIN` のどれかを公開情報だけで固定する。
- Gear の hit / miss、Boss 取得、Boss 使用、対象選択、固定攻撃を
  callback をまたぐ一つの transaction として保存する。
- 親が無目的に Gear を選んでも、現在の攻撃が確定勝利なら
  Gear を veto して攻撃する。
- 76テスト、既知16局面、両席の実エンジン lifecycle `2/2` は通過した。
- 過去207リプレイでは確定勝利 veto が2件自然発火し、
  どちらも Raging Hammer によるその場の勝利だった。
- 一方、目的付き Gear は自然発火0件、提出席での親 Gear 維持は289件だった。

したがって、この項目は部分完了 `[-]` とする。
確定勝利より Gear を優先する固定スコアは除去したが、
generic item `20000` と無目的 Gear を一般にはまだ除去していない。

Root verification:
`implementation/archaludon_purpose_first_pokegear_boss_transaction_v1/ROOT_VERIFICATION.md`

### Explorer / Assemble Alloy transaction

`archaludon_explorer_alloy_attack_continuity_v1` は、Explorer の使用から
二枚選択、進化、Assemble Alloy、手貼り、攻撃までを一つの transaction として
実エンジンで完走した。
しかし、人間プレイ監査で次の基本的な誤りが自然発火したため、不採用とした。

- 今すぐ取れる `1 Prize` より控え育成を優先した。
- 相手特性で実効ダメージが `30 -> 0` になる Active 進化を選んだ。
- 同じ攻撃経路で Lillie を捨て、公開用途のない Cinderace を残した。
- 攻撃可能な控えがすでにいるのに、重要な Trainer を捨てて三体目を育てた。

原因は、合法な攻撃経路の完成だけを見て、即時 Prize、現在攻撃の実効結果、
最初の控えの限界価値、カードの具体的用途を比較していなかったことである。

修正版 `EXPLORER_ALLOY_MARGINAL_TURN_DOMINANCE_V2` と、
資源の時間軸を加えた
`EXPLORER_EPOCHAL_RESOURCE_NONDISPLACEMENT_V1` を実装・全履歴監査した。
次を固定点ではなく、上から順に覆せないハード条件とした。

1. 確定勝利と確定敗北回避。
2. 今ターンの即時 Prize。
3. 全公開効果を適用した現在攻撃の結果。
4. 攻撃可能な控えが `0 -> 1` になること。
5. 公開された具体的用途を持つ資源の保存。

異なる生きた用途が比較不能なら親へ戻す。
物理 serial は、同じ ID と同じ用途のコピー間だけで使う。

ただし、epochal版も次の開発親として不採用とした。
validator、18テスト、両席engine、207 replay・209対象席・387 Explorer PLAYの
shadowはすべて通ったが、七つの自然な最初の差のうち五つが人間プレイとして不合格だった。

- 確定した今ターンのPrizeを「締切」ではなく「今すぐ攻撃する許可」と扱った。
- 親が手張り、Ultra Ball、Cape、Ice Creamを安全に済ませ、
  同じターンに同じKOを取れた局面でも先に攻撃した。
- 一局面では親が同じKOとBoss温存を両立したのに、候補はBossを捨てた。

次版では、確定攻撃をロックしたまま安全なMAIN行動を一つずつ通し、
各callback解決後に同じattacker、target、attack、Prizeを再証明する。
終端勝利だけは即時攻撃し、非終端では親がATTACK/ENDまたは
攻撃経路を壊す行動を提案した時点で保存攻撃を実行する。
Trainerだけでなく、Bench形成、手張り、Tool、回復を対象にする。

Frozen contract:
`strategy/archaludon_human_fundamentals_planner_20260731/STRATEGY_SELECTION_EXPLORER_MARGINAL_TURN_DOMINANCE_V2.md`

v1 failure report:
`implementation/archaludon_explorer_alloy_attack_continuity_v1/ROOT_QUALITATIVE_FAILURES_JA.md`

epochal版 failure report:
`implementation/archaludon_explorer_epochal_resource_nondisplacement_v1/ROOT_QUALITATIVE_AUDIT_JA.md`

## P1: 攻撃・進化・非exの基本判断

- [ ] 払える有効な攻撃があるのに、理由なく END しない。
- [ ] 防御進化で被KOを回避し攻撃継続できるなら、理由なく未進化で残さない。
- [ ] Active が十分に攻撃可能なら、余剰エネルギーは次アタッカーへ付ける。
- [ ] Turbo Flare / Assemble Alloy で攻撃コストを超えて無駄に付けない。
- [x] 非ex Archaludon を一律減点しない。
- [x] 120で同じPrizeを取れる、Basicからの反撃をCoated Attackで防げる、
  一Prize壁でPrize raceを変えられる、exだけが無効化される、のいずれかなら
  非exを正式な候補にする。
- [ ] 220、Assemble Alloy、耐久、終端Prizeが必要なら ex を選ぶ。
- [ ] 進化しない方が Raging Hammer の即時攻撃を維持する場合も比較する。

## P1: ダメージ・特性・相手の返し

- [-] 自分と相手で同じダメージ計算器を使う。
  対応済み効果は共通器を通るが、全公開カード効果の網羅は未完了。
- [-] Weakness、Resistance、Full Metal Lab、Hero's Cape、
  Metal Defender、Coated Attack、Raging Hammer を正確に処理する。
- [-] 公開されているダメージ増減、攻撃無効、Sturdy、Prize増減を反映する。
  第1段階の登録効果は反映済みだが、未登録効果は親へ戻る。
- [-] 公開されているエネルギー加速、進化加速、交代、逃げる、回復、
  手札に戻る特性を相手の返しに反映する。
- [-] 現在攻撃可能、手貼り1枚で可能、進化1回で可能、既知特性で可能を分ける。
  現在攻撃・手貼り・一部の既知特性は分離済みで、検索・進化callbackは未完了。
- [x] 未対応テキストを0として確定生存・確定KOを証明しない。
- [x] Run Away などで回復しながら手札へ戻れる相手への非KOダメージを
  永続的な進捗として数えない。

## P1: Prize race と固定条件分岐

- [ ] 今ターンの確定勝利はハード分岐で取る。
- [ ] 次の相手ターンの確定敗北を回避できる手があるならハード分岐で回避する。
- [ ] KO後に準備済みベンチが最終Prizeを取る場合、KOしない、Boss、
  一Prize壁、準備済み脅威除去を比較する。
- [ ] 目の前のActiveよりBenchの進化エンジンや準備済み高Prize脅威を
  攻撃・Bossする方が勝利ターンを短縮する場合はそちらを選ぶ。
- [ ] 全て負け筋なら盤面点ではなく、敗北までのターン、
  相手に追加要求する資源、自分に残る逆転経路の順で選ぶ。

## 判定方式

- [ ] legality、engine context、確定勝利、確定敗北回避、
  継続中 transaction はハード条件分岐にする。
- [x] v2 が扱う明確な支配関係ではスコアを使わない。
- [x] v2 が追加する判断では、スコアを完全なターンプラン同士の
  最後の同点比較に限定する。
- [x] 完成済み親行動も一つの合法プランとして保持し、新プランが公開情報上
  明確に支配するときだけ置換する。
- [ ] 最終 `agent` から親・新規ルール・transaction のどれが選ばれたかを
  telemetry で追跡できるようにする。

## 必須検証

- [ ] マリガン、追加ドロー0～2、Active/Bench setup を実engineで確認する。
- [ ] Explorer → 鋼捨て → ex進化 → Alloy → 手貼り → 攻撃を実engineで確認する。
- [ ] Turbo Flare の両席配分と次ターン攻撃を実engineで確認する。
- [ ] Ultra Ball、Pad、Gear、Stretcher、Ice Cream、Cape、FML、Boss の
  正例・負例・callback完走を確認する。
- [x] v2 の対象 transaction は option順を変えても意味上同じ行動を選ぶ。
- [x] v2 一次ゲートで invalid action、例外、duplicate不一致、max-stepを0にする。
- [x] 同一seed・両席で銀圏系親と比較し、一次ゲートで破壊的な絶対性能低下がない。
- [x] v2 一次ゲートの全ての行動差について最初の差を確認する。
- [ ] 上記を満たすまで package / Kaggle 提出を行わない。
