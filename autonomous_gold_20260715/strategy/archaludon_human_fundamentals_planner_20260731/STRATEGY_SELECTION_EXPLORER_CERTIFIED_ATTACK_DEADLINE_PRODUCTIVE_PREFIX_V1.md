# Strategy selection: EXPLORER_CERTIFIED_ATTACK_DEADLINE_PRODUCTIVE_PREFIX_V1

## 判定

`archaludon_explorer_epochal_resource_nondisplacement_v1`
（source SHA-256: `5E19FA44A1CB55C0747A04F2E95E01A9C6A4CD4E80723B1C120A97EA57DB1906`）は reject とする。
七つの自然な変更に `GOOD_CAUSAL` がなく、五件で親の安全な前処理または資源温存を失った。

根拠:

- `implementation/archaludon_explorer_epochal_resource_nondisplacement_v1/ROOT_QUALITATIVE_AUDIT_JA.md`
- SHA-256:
  `DA71A9E6406197FD0DBCA34646CC4BDECE034A056DA1E4DA0847AF5CDF886D7B`

5E19候補をbehavioral parentとして積み重ねてはならない。
新候補のdirect behavioral parentは必ず次とする。

- `candidates/archaludon_purpose_first_pokegear_boss_transaction_v1/main.py`
- SHA-256:
  `558EE5DB29E001428B0D59813613FABEE8E15B96E422746C104BDFAB4DC22DB6`

5E19のコードは機械的templateとしてだけ参照できる。

## 唯一の仮説

`EXPLORER_CERTIFIED_ATTACK_DEADLINE_PRODUCTIVE_PREFIX_V1`

Explorerのrevealと保持資源を変更しない。
親が現在すでに作ったunique exact attackを「今ターン中に必ず実行するdeadline」として保存する。
この攻撃を壊さないことを公開情報だけで証明できるproductive MAIN actionを一つずつ親に許可する。

各actionと全callback解決後に攻撃を再証明する。
親がATTACK、END、unsafe/unknown actionを提案したとき、またはproductive prefixが上限へ達したとき、保存attackを実行する。

終端勝利だけは直ちに攻撃する。

## hard precedence

1. result、attack完了log、既存親transaction。
2. unique exact terminal-winning attack。前処理を許可せず直ちに実行する。
3. 保存deadlineのattacker、target、attack、payment、combat/Prize floorを再証明する。
4. exact-safe productive parent actionを一つ許可する。
5. 親がATTACK、END、別attack、unsafe/unknown action、またはprefix上限を提案したら保存attackを強制する。
6. 保存attackをactual stateで再bindできない場合だけ、wrapper stateを消してgenuine parentへ戻る。実盤面を過去snapshotへ戻してはならない。

非終端deadlineの不変条件:

- 同じgame epoch、seat、turn。
- 同じActive attacker serial。
- 同じopposing Active target serial。
- 同じattack IDが一意に合法。
- 保存paymentが維持される。
- exact combatのPrize、KO、damage、persistent effectsが悪化しない。
- attackを既に消費していない。
- opponent Active、attacker、必要Energyを変更しない。

## productive action

effect registryとcallback graphが完全で、全mandatory branchに安全な完了経路がある場合だけ許可する。

- Poke Pad、Ultra Ball、Pokégear、Night Stretcher、Jumbo Ice Cream。
- 空きBenchへのBasic Pokémon PLAY。unsupported on-play effectがなく、Activeを変えない場合。
- manual Energy attach。保存paymentを消費せず、backup readinessまたは公開された攻撃準備を改善する場合。
- exact Hero's Cape attach。
- exact healing。HPを増やし、保存attackを悪化させない場合。
- exact Stadium。置換後も保存combatが非悪化で、公開された防御価値がある場合。

retreat、switch/gust、保存attackerのevolve、別attack、END、unsupported effect、意味のない反復、target/payment/Prize floorを変えるactionは禁止する。

hidden search targetを事前に読まない。
Ultra Ball等は公開handからsafe cost completionの存在を証明する。
callbackで親選択が安全ならそのまま返し、unsafeなら保存済みsafe semantic choiceへ差し替える。
optional cancelがある場合はcancelできる。
mandatory safe completionがないactionは開始しない。

productive MAIN actionは物理card/action fingerprintごとに一度、最大六回までとする。
一つのactionが完全解決し、attack再証明が終わるまで次を許可しない。

## state machine

`IDLE -> DEADLINE_READY -> PARENT_SUBTX_ACTIVE/AWAIT_POSTCONDITION -> DEADLINE_READY -> ATTACK_EMITTED -> COMPLETE`

- `IDLE`: Explorerが同ターンに解決済み、ordinary MAIN、既存ownerなし、unique exact attackが現在合法ならlockする。
- `DEADLINE_READY`: 親actionを分類する。
- safe single-step: `AWAIT_POSTCONDITION`。
- safe multi-callback: `PARENT_SUBTX_ACTIVE`。
- MAINへ戻ったらexact postconditionとdeadlineを再証明する。
- attackを返したらexact attack logまで `ATTACK_EMITTED`。

親は各callbackで一度だけ呼ぶ。

safe actionが新しい親ownerを作った場合、exactly one owner、同じseat/turn/card/effect fingerprintのときだけ保持してsuspendする。
quarantineしてはならない。
effect callback中はwrapper独自のMAIN actionを出さず、親callbackをsafe envelope内で通す。

親のunsafe actionを保存attackで上書きするとき、未実行actionのため今回の親callが作ったownerだけを `owner_before` へ戻す。
既存ownerは消さない。
複数owner、owner identity変化、予期しないcontext、turn/seat変化はinvariant failureとする。

## snapshot・duplicate・fallback

各許可前に次を保存する。

- game epoch、seat、turn、turnActionCount。
- attacker、target、attack、payment、combat certificate。
- board、HP、Energy、hand/discard公開multiset、deck count、stadium。
- supporterPlayed、energyAttached。
- owner set/fingerprint。
- 許可action semanticsと期待postcondition envelope。

duplicate key:

`(game_epoch, seat, turn, context, effect/contextCard, option multiset, owner, last emitted semantic roles)`

duplicate callbackでは前回actionを現在optionsへsemantic rebindし、action count、subtransaction count、telemetryを二重加算しない。

fallbackはwrapper/owner metadataの清算とactual-state parent handoffだけを意味する。
実行済みcardやboardをsnapshot状態へ戻そうとしてはならない。

## 必須fixture

保持すべき親系列:

- `87658443`: revealは `ex67 + Boss100`。Bossを捨てず同じP1 KO。
- `87673473`: Duraludon5へMetal62 attach後、同じP1 KO。
- `87773965`: Duraludon4へMetal54 attach後、同じP1 KO。
- `88147935`: Ultra Ball83の全callback、Metal115+Cinderace71 discard、ex67取得後、同じP1 KO。
- `88660007`: Metal112 attach、Cape97 attachを順に許可し、同じP1 KO。
- `88679860`: terminal winのため前処理0で即attack。

変更禁止control:

- `88479736`、`88681773`、`87663229`、`88356203`、`87877210`: 親reveal/resource choiceを維持。
- `87738210`: Inn下で `30 -> 0` のattackを保存・強制しない。
- `88232035`: 同義physical-copy以外の意味差を作らない。

episode IDはfixture名にだけ使い、runtime policyへ含めない。

## telemetry

- `deadline_locks`
- `terminal_attacks_immediate`
- `safe_prefix_allowed_{trainer,basic,attach,tool,heal,stadium}`
- `parent_subtx_starts/callbacks/completes`
- `postcondition_reproof_pass/fail`
- `attack_reproof_pass/fail`
- `forced_attack_on_{attack,end,unsafe,unknown,cap}`
- `callback_safe_substitutions/cancels`
- `owner_suspensions/collisions`
- `duplicates`
- `invariant_breaches`
- `attacks_emitted/confirmed`
- `actual_state_fallbacks`
- `invalid_actions/exceptions/stale/max_step_hits`

保存則:

- `deadline_locks = attacks_confirmed + live_deadlines + actual_state_fallbacks`
- `parent_subtx_starts = parent_subtx_completes + live_parent_subtx + parent_subtx_failures`

## gate

- direct parent prefixとSHAがexact `558EE5...`。5E19をparent chainへ含めない。
- reveal pair changesとresource substitutionsは `0`。
- 四つのBAD_ATTACK_TIMING局面で親productive sequenceと最終P1 KOを完全保持する。
- terminal fixtureは前処理 `0` で即勝利する。
- 許可action後のsaved-attack lossは `0`。
- both seats、identity/reorder/duplicate、全許可action型、owner suspensionをfresh processで完走する。
- invalid、exception、stale、owner collision、max-step、nondeterminismをすべて `0` にする。
- 207 replay、209 target seats、387 Explorer rowsのshadowで既知fallbackとInn vetoを保持する。
- その後にだけ、historical-Silver primary anchorとadjacent complete-agent populationを同一seed・両席で評価する。
