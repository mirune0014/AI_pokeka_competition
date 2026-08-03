# 次候補戦略選定: Purpose-Bound Night Stretcher Recovery-to-Attack Transaction v1

## 判定

選ぶ仮説は一つだけである。

> Night Stretcher を使う前に、公開された discard・自分の hand/board・相手の公開 board から、回収対象とその後の具体的な合法 action 列を一つに束縛する。回収が `(a)` 今ターンの攻撃完成、`(b)` 確定進化から今ターンの攻撃、`(c)` 現在攻撃を維持した次アタッカー形成、`(d)` 最終 Prize または公開上の確定 loss 回避、のいずれかを作り、回収しない案・全ての別回収対象・Basic Metal 回収を hard hierarchy で厳密に上回る時だけ、その transaction を完遂する。それ以外は formal parent へ戻す。

候補名は `archaludon_purpose_bound_night_stretcher_recovery_to_attack_v1` とする。これは四つの独立 rule ではなく、「回収札は回収後の攻撃目的まで証明してから使う」という一つの一般原則を、目的ラベルで監査可能にしたものである。

実装元は次の formal parent 一つだけとする。

- `autonomous_gold_20260715/candidates/archaludon_purpose_first_pokegear_boss_transaction_v1/main.py`
- SHA-256: `558EE5DB29E001428B0D59813613FABEE8E15B96E422746C104BDFAB4DC22DB6`
- deck SHA-256: `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`

E19、失敗した BD7 Metal-allocation candidate、その他 dormant component を積まない。source/deck はこの選定作業では編集しない。

## 使用した root-verified facts

- 先行 Metal-allocation は `RARE_NARROW_FAIL`。root report SHA は `ABEC5E637490EEFE62BCCB866F69DD3FE1342E0336CE3F041C94BB0AC5D31415`、raw inventory SHA は `873FE2F3DBC48C06B0D2878B6D736C21C82BFA45862BAB561E9096ACB045C563`、summary SHA は `CFF1AD2E1C15DB805D7F0B47CE69A7AFC372BDC79E4A9A8C04A3173ABFD9A5C7`。744 通常 Metal attach に対して strict start/difference はともに 0 だった。条件を後付けで緩めず棄却する。
- 訂正済み root callback census SHA `6906AF3CCD0CD50F7B0435FE281D9E1594DD3435A4E9C5C781691DE525D72163` は、固定 207 replay / 209 target-seat corpus に Night Stretcher effect callback が 186 件、123 replay、両 seat と確認した。Kaggle replay action は一行前 observation への応答として次行 action と結合されている。既存 PLAY 集計では 168 unique turn である。
- 正しい historical target は Duraludon 93、Archaludon ex 53、Basic Metal 34、non-ex Archaludon 4、Cinderace 2。全186 callbackは `minCount=maxCount=1`、valid selection 186/186、empty 0である。option 数は1～20で1択は6件だけ、180件は複数候補である。これは正解ラベルではなく、Duraludon系へ偏りながらも五種類を含む自然な対象 arbitration が頻発し、card-ID固定優先では足りないことを示す。
- formal parent は Night Stretcher の item 使用を urgent 条件後の generic `20000`、回収対象を matchup/card-ID 固定 score で処理する。一方、正確な card text、serial binding、energy payment、evolution/energy projection、combat oracle、threat graph、resource ledger、role rebind は既に利用できる。
- parent 内の H2 は「最終 1 Prizeで Stretcher→Metal→Active attach→Boss→Metal Defender」の既存 transaction を所有する。新 rule は H2 の一般化代替ではあるが、runtime でその owner と重複してはならず、H2 発火時は完全に parent を返す。
- root 監査 `88017509` には、Duraludon 固定優先でなく discarded Metal を回収すれば同ターン最終 Prize に結べた certified missed lethal がある。ただし一 replay 固有分岐にはしない。

## gameplay 全体での理由

- setup/board formation: 無目的に Pokémon を回収せず、Bench slot、進化元、`appearThisTurn`、既存同役割枚数まで確認する。
- attacker/backup: 現在の payable attack を最優先し、回収 Pokémon/Metal が実際に ready backup を作る場合だけ continuity と数える。
- Energy/hand/deck: Basic Metal を単なる fallback にせず全 Pokémon target と同列比較する。同じ役割が hand/board に既にある時、将来唯一の Stretcher を消費する案は劣後する。hidden deck top や future draw は価値 0 と置かず UNKNOWN とする。
- attack/prize/finishing: 同ターン exact win、確定 loss 回避、現在 KO/Prize、現在 attack 維持、backup の順に評価し、現在 Prize を捨てて盤面だけ作る案を許さない。
- disruption: opponent の公開 threat/effect で回収後の backup が確実に失われる、hand に戻しただけでは使えない、または reply が decision-relevant なのに UNKNOWN なら parent に戻す。
- regression risk: 新 rule は Stretcher とその直接後続 callback だけを所有し、Lillie、Explorer、Pad、Gear、一般 item planner を広げない。

## implementation-ready behavioral contract

### 1. 起動境界と parent mode

新 suffix wrapper は formal parent を callback ごとに厳密に一回だけ呼び、その action を先に保存する。

起動には、game 継続中、正しい seat/turn、complete serial universe、Night Stretcher text/static hash 一致、clear MAIN、`minCount=maxCount=1`、effect/contextCard/looking なし、かつ legal Stretcher PLAY option が必要である。既存 owner/watch、特に H2、PCRD、DPER、CUM、PF Gear transaction/veto が parent call の前後どちらかで生きていれば、状態を一切変更せず parent action を返す。

二つの mode だけを許す。

1. `PARENT_ALREADY_STRETCHER`: parent 自身が exact Stretcher serial の PLAY を選んだ。新 rule は「使う」という親判断を再主張せず、全 recovery target と後続目的を比較して一意な target/route を所有できる。NO_USE が exact に構築できれば比較するが、NO_USE が UNKNOWN でもそれを 0 と扱わず、使用判断は parent に残したまま target arbitration だけを行える。
2. `OVERRIDE_TO_STRETCHER`: parent が別 action を選んだ。parent action と NO_USE route が完全に exact で、Stretcher route が `(a)`、`(b)`、または `(d)` の上位 hard layerを厳密改善する時だけ Stretcher へ変更する。backup-only `(c)` で parent の非-Stretcher actionを覆してはならない。

parent が Stretcher を選んだが certified purpose が無い場合、unique exact NO_USE action が明確に支配する時だけその actionへ veto して Stretcher を保存する。それも証明できなければ parent を返す。END や任意の低 score action を安全策として捏造しない。

### 2. 回収候補と plan generation

Stretcher を返す前に、公開 discard の全 Pokémon と全 Basic Energy を card text/CARD_DB と serial で列挙し、callback で提示されるはずの semantic target set を保存する。Basic Metal は固定 fallback でなく通常の recovery plan 一つである。同 ID の物理 copy は別 serial のまま projection し、全 outcome/ledger が完全一致する時だけ同義 role として collapse し lowest serial を tie-break に使う。

各 target について、完全な action queue と postcondition を事前生成する。

- `(a) ATTACK_NOW`: 主に Basic Energy 回収→未使用の通常 attach→現在 Active の exact payable attack→attack。回収無しではその攻撃が払えないことを確認する。
- `(b) EVOLVE_ATTACK_NOW`: 回収 Pokémon→公開 board の合法な一意の進化元へ evolve→必要なら公開 discard だけを使う Assemble Alloy callback と allocation→exact payable attack。`appearThisTurn`、evolution relation、Ability text、全 Energy serial/target を事前に確定する。
- `(c) BACKUP_CONTINUITY`: 回収 Basic Pokémon の Bench play、回収 evolution の既存 Bench 進化、または回収 Metal の backup attach により、現在 attack/KO/Prize を維持した上で、worst exact public reply 後も `READY_NOW` または手札に現存する一枚だけで payable な `KNOWN_PUBLIC_RESOURCE` backup を作る。future draw/search を数えない。
- `(d) TERMINAL_OR_LOSS_AVOIDANCE`: 同ターン最終 Prize、または threat graph 上の確定次ターン loss を、公開 route によって消す。既存 H2 owner が成立する局面は H2 control として parent に渡し、新 rule は所有しない。

一 plan が複数 purpose を満たす時は、比較で最初に strict improvement を生んだ hard layerを唯一の telemetry label とする。card/opponent/replay/seed/seat の ID 例外は禁止する。

### 3. NO_USE、別 target、Metal の比較

NO_USE には、Stretcher を手札に保持したまま現在存在する exact attack、手札 Metal の attach、手札 evolution、parent の bounded action route を含める。parent action が Trainer/search/draw 等で outcome を公開証明できない時は、`OVERRIDE_TO_STRETCHER` を禁止する。

effect callback は root-verified で全186件 `minCount=maxCount=1` である。Stretcher PLAY 後は必ず一枚を選ぶ mandatory selection とし、空選択、decline、未選択 plan を生成しない。Stretcher を使わない比較は PLAY 前の NO_USE だけで行う。

Basic Metal の比較規則は明示する。

- Metal が現在の exact attack/最終 Prize を完成するなら、同ターン攻撃を作らない Pokémon 回収より上位。
- 現在 attack が既に payable で、Pokémon 回収だけが exact surviving backup を作るなら、未使用 Metal 回収より Pokémon plan が上位になり得る。
- Metal と Pokémon が同じ gameplay fields を作るなら、resource ledger と Stretcher 保存を比較し、それも同値なら NO_USE、次に parent。カード種別の固定順位で決めない。

### 4. hard hierarchy

重み付き score や巨大定数を追加しない。各 plan は次の順で lexicographic/Pareto 比較する。

1. legality、owner、exact metadata、支払可能性。
2. `CURRENT_EXACT_WIN`。
3. `CERTAIN_TERMINAL_LOSS_AVOIDANCE`、または全案が losing の時の exact turns-to-loss。
4. `CURRENT_ATTACK_PAYABLE`、`CURRENT_PRIZE`、`CURRENT_KO`。
5. current attacker survival、attack continuity、exact ready backup、next-Prize timing。
6. own/opponent Prize liability と worst exact public reply。
7. post-action/post-reply hand・board・discard・Energy resource ledger。
8. gameplay fields が同値なら Stretcher を使わない案。

上位 layer が悪化する下位改善は却下する。同一 layer 内の trade-off、複数 nondominated targets、decision-relevant UNKNOWN/INCOMPARABLE は parent。hidden opponent hand、future topdeck、coin、未対応 effect は 0 としない。terminal attack で game が終わり reply が存在しない場合だけ、不要な reply proof を要求しない。

### 5. transaction と callback ownership

保存 state は少なくとも次を含む。

`(source snapshot/hash, seat, turn, action-count, purpose, Stretcher role, recovery target role, expected target set, ordered semantic steps, current attack/prize certificate, backup certificate, public reply certificate, comparison layers, parent role, NO_USE proof)`。

基本 stage は以下である。

1. `ARMED`: 保存した Stretcher role を play。
2. `AWAIT_EFFECT`: PLAY log または hand→discard と、effect id/serial を確認。
3. `RECOVERY_SELECT`: option target set を保存集合と照合し、保存 target role を選択。
4. `RECOVERY_POST`: その serial だけが discard→hand へ移ったことを確認。
5. `ROUTE_STEP[n]`: play/evolve/Ability selection/attach/Boss target/attack の各 semantic roleを一手ずつ実行し、それぞれの公開 postcondition 後だけ進む。
6. `DONE`: attack log、terminal result、または certified backup と現在 attack の完了を確認して clear。

同一 snapshot の duplicate callback は stage を進めず、`_pcrd_action_roles/_pcrd_bind_roles` 相当で保存 role を現在 option orderへ再 bindして同じ actionを返す。option reorder、same-ID copies、両 seatで position番号を記憶しない。

transaction 中にも formal parent は一回呼ぶ。parent が新しい既存 owner を開始したら二重所有しない。parent action が保存 next role と一致していても新 transaction を clearして正式 ownerへ完全委譲し、一致しなければ rollback reasonを記録して clear-and-parentする。parent ownerを消去・改変してはならない。

Stretcher 消費前の mismatch は transaction を clearして parent。消費後は undo できないため、actual state を再読し、保存 roleが無い、target set違い、postcondition failure、seat/turn/result/context discontinuity、公開 certificate失効のいずれでも stale actionを返さず clear-and-parentする。mandatory callback では parent の合法 actionを返し、空 actionを捏造しない。game/seat/turnをまたぐ global stateを残さない。

## focused fixtures

最低限、全 fixture を seat 0/1、option permutation、同一 callback duplicate で反転する。

Positive:

1. 非terminalで discarded Metalだけが Active の一枚不足を埋め、同ターン exact attackを作る `(a)`。
2. discarded Archaludon exを回収し、既存 Duraludonを合法進化、公開 discard Metalを exact Alloy allocationし、同ターン attackする `(b)`。
3. 現在 attackを維持し、回収 DuraludonのBench playまたは回収 Metalのbackup attachだけが worst reply後のready backupを作る `(c)`。
4. H2と異なる recovery/evolution routeで最終 Prize、または確定lossを回避する `(d)`。
5. Duraludon固定scoreより Basic Metalが現在 attack/Prizeで上位、逆に現在 attack ready時は surviving Pokémon backupがMetalより上位。

Negative/control:

1. `88017509`型の既存 H2 ownerは新 rule 0 ownershipで、formal parent H2 action列と完全一致。
2. Metalが既にhand、同役割Pokémonがboard/handに存在、回収後に合法利用不能、backupがworst replyで確実に失われる、現在KO/Prizeを落とす: Stretcherを開始しない。
3. 二つの異種targetがPareto非比較、evolution/attack/effectがUNKNOWN、hidden search/drawまたはcoinが必要: parent。
4. recovery callback は `minCount=maxCount=1` で保存 target を厳密に一枚選ぶ。保存 role が無い、不一意、または callback cardinality が違う時は空 actionを返さず parent の mandatory selectionへrollback。
5. H2/PCRD/PF Gear owner live、duplicate/reorder、same-ID serial、effect target set差、Stretcher/target/evolution/Alloy/attach/attack各段のpostcondition failure、turn/seat/result reset: 一 owner、合法rollback、fault 0。

fresh engine の全四purposeを含む focused lifecycle は24ケース以上、両seat、二回実行byte-identical、parent call exactly once/callback、invalid action・exception・stale owner・max-step 0を要求する。

## 事前固定する shadow gate

まず root census artifactと同じ corpus/manifest/hashを固定し、186 effect callback、123 replay、両seat、168 unique PLAY turnを再現する。各 rowに replay/seat/turn、Stretcher serial、context/min/max、全option role、historical role、parent role/owner、candidate purpose/target/steps/comparison/rollbackを出す。historical actionは正解ラベルにしない。

fixed760へ進む最低条件は次の全てである。

- exact purpose-classified callback `>=24/186`、両seat、`>=12` replay。
- 完全な candidate transaction start `>=16`、両seat、`>=8` replay。
- actual first difference `>=10`、両seat、`>=6` replay。play/use、recovery target、または後続actionのどこが最初かを分ける。
- 自然startに少なくとも2 purpose classが各3件以上含まれ、Basic Metal recoveryとPokémon recoveryがともに存在する。H2-owned rowはこの数に入れない。
- 既存 H2 ownership overlap、unknown-as-zero、mandatory-selection fault、duplicate advance、stale role、parent-call fault、postcondition faultは全て0。
- rootが全 first differenceを監査し、変更が保存certificateの目的と一致し、同一target card-IDの挙動模倣でないことを確認する。trigger外actionは100% parent同一。

これは186 callbackの約13%をpurpose分類、約5%を実差分に要求するため、前候補の0/744を後付け救済するものではなく、同時に一局面だけのH2再実装も通さない。threshold未達なら `RARE_NARROW_FAIL` としてfixedへ進めない。

## fixed760 adoption gate

formal parent対candidateを、同一engine・opponents・seats・seedsのexact paired 760 scheduleで比較する。historical-Silver 200をprimary anchor、adjacent population 560を安全性panelとする。

Integrity prerequisite:

- parent/candidate hash、deck hash、engine/schedule manifestを固定。
- unique `(panel, opponent, seat, seed)` key 760、schedule完全一致、duplicate 0。
- 両agentのexit/action error/exception/max-step/owner/postcondition faultが全て0。

Strength/safety gate:

- overall `candidate_win - parent_win >= 16/760`、かつpaired 95% CI lower bound `>0`。
- historical-Silver candidate `>=108/200` かつ parent比 `>=+8/200`。Silver両seat非悪化。
- overall両seatがそれぞれ `>=+4/380`。
- adjacent 560 totalはparent非悪化。各opponent totalの悪化は最大2 win、各opponent×seat cellの悪化も最大2 winまでとし、全悪化cellをroot replay auditする。
- Kangaskhanは少なくとも35%、Crustleは少なくとも32.5%を維持し、両bucketともparent win数を下回らない。
- 4 contiguous seed blocks中3以上がpositive、どのblockも `<-2` でない。
- completed Night Stretcher transaction `>=16`、両seat、4 opponent以上、2 purpose class以上。actual fixed first difference `>=10`で、観測mechanismが保存したrecovery-to-attack contractと一致する。
- 全 parent-win/candidate-loss、全 action sequence差、全 terminal/continuity certificateをrootが確認し、BAD_CAUSAL target choice、現在attack放棄、回収後未使用、H2競合が0。

小さなpaired deltaだけ、Silver横ばい、片seat改善、shadowのtarget正解だけではacceptしない。一つでも不成立ならrejectし、sourceは失敗記録として凍結する。package/Kaggle writeはroot専有である。

## 明示的に棄却する広げ方と回帰リスク

- `Cinderace > Metal > Archaludon` のようなhistorical target頻度/ID順はbehavior cloningであり禁止。
- Lillie後draw、Pad/Gear/Explorer search結果、future topdeck、opponent hidden hand、coinを回収価値へ混ぜない。
- generic item planner、全turn planner、一般Supporter順序、Alloy/Turbo全体最適化へ広げない。必要なAlloy callbackは保存route内だけで扱い、既存ownerが取れば委譲する。
- Stretcherを「hand-neutralだから先に使う」と扱わない。唯一の将来回収札の浪費、Bench枠消費、二Prize進化の露出、現attack遅延が主要回帰である。
- 既存H2を削除・置換・二重所有しない。E19/BD7をstackしない。

## 次に必要な exact evidence

実装前に訂正済み root census の row-level CSV/manifest/hashを固定し、次行 action 結合、186/186 valid、全 callback `minCount=maxCount=1`、empty 0、全option roleを再確認する。実装後は、186-row shadow trace、全purpose/target/NO_USE/Metal comparison fields、全first-difference starting observation、focused lifecycle raw、fixed760 raw rowsとreplaysが必要である。採否判断では、数値改善だけでなく、勝敗差が「目的を持つ回収→保存した具体的行動→攻撃または生存backup」という意図したmechanismで生じたことを独立に確認する。
