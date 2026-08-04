# Mega Lucario 監査修正の最終報告

- 報告日：2026-08-05
- 修正branch：`codex/megalucario-audit-repair-20260805`
- 最終判定：`REJECT_REQUIREMENTS_NOT_MET`
- Kaggle提出：未実施

## 判定の根拠

監査契約で指定された修正、focused fixture、固定対戦、自己完結パッケージ生成を完了した。

しかし、未調整fixed760では親方策58勝に対してcandidateは46勝であり、paired gain、regression、tieは`0/12/748`だった。

net paired gainは`-12`であり、採用条件の`+5以上`を満たさない。

さらに、Aura JabのEnergy付与transactionで`UNEXPECTED_CONTEXT_REF`が3戦発生し、runtime faultとtransaction faultが記録された。

したがって、この実装を完成版、強化版、提出候補とは扱わない。

## 入力と実装の同一性

| 対象 | SHA-256またはcommit |
|---|---|
| 元要件書 | `47cb7fe3d426a14281699e6882f37ea24ce5979a11f1c2a15cf5bc7edaf5e0d7` |
| 監査報告 | `2a50ab0d0be3e5492cceeee084880e49f68ccda0aa8af1a3f371f3e2e8d2704f` |
| 添付修正契約 | `6793ae2a4427b7eb18de2926b397630d25ad7174fa96ed25efb8542bc0434f68` |
| 監査報告が示す実装commit | `8c8f43b1478d0d64239ed5190f50a04409dd6f61` |
| 修正作業の親commit | `4cfdffae54561c9b6b054f4a9d461536ef573385` |
| 親runtime tree | `19f6dc9c9beb218228519ae20549966b72888aa5abe538676ea1e3f2ed6d9d35` |
| 修正後runtime commit | `75b6c7c91e1178f9450739803e477d3df4eb71aa` |
| 修正後runtime tree | `bdef06a10dc5cc8199d4893d9a0193ee6164c672adcefa1186d4fee120525dc3` |
| 評価manifestを含むHEAD | `d2f251119b3980b77598184de0412cec06353332` |
| 親archive | `398f9331addfab1f9fb5cb12e6e523522cfdd3bcc466b28b56a9147e92822d1c` |
| candidate archive | `163a50567237ce7b3fe1a190e9f81b7f5f0bc456810312953e15212bfc94dfe2` |

修正前の状態は`MEGA_LUCARIO_RULE_AGENT_FOUNDATION_AND_UNVALIDATED_POLICY_V1`として扱った。

fixed760を確認した後は、戦術条件もtransaction条件も変更していない。

## 要件と変更箇所

| Gate | 実装内容 | 主な変更箇所 | 結果 |
|---|---|---|---|
| Gate 0 | Wally、Cape、Gust、terminal receipt、Telemetryの5反例を親commitで再現 | `reports/GATE0_REPRODUCTION_REPORT.md` | 合格 |
| A1 | 固定damage閾値を廃止し、公開attackから回復前後の生存差とproductive attack維持を再計算 | `attack_outcomes.py`、`public_effects.py`、`routes.py` | focused fixture合格 |
| A2 | Cape前後の生存差、Tool有効性、Prizeまたは次attack維持、Bench spreadを再計算 | `attack_outcomes.py`、`routes.py` | focused fixture合格 |
| A3 | ActiveとBenchをexact Prize、KO、公開資源損失、engine denial、threat removalで辞書式比較 | `attack_outcomes.py`、`public_effects.py`、`routes.py`、`resolver.py` | focused fixture合格 |
| A4 | Wally、Cape、Gustのroute固有proof schemaを追加し、Observation、合法option、ledger、AttackOutcomeから再検証 | `certificates.py`、`resolver.py`、`routes.py` | adversarial fixture合格 |
| B1 | transaction typeごとのterminal receiptを定義し、receiptなしのturn跨ぎをfault化 | `state_view.py`、`transactions.py` | fixture合格 |
| B2 | 検証Telemetry、fault latch、例外containment、owner残存、unsupported MAINをrunnerへ露出 | `main.py`、`telemetry.py`、`run_local_battle.py` | fixture合格 |
| C | 公式cgをhash固定で無改変同梱し、clean unpackと外部cgなしの実行を検証 | `build_mega_lucario_package.py` | 合格 |
| D | action traceとvalidation traceを保存するpaired runner、事前固定schedule、重複controlを追加 | `run_seeded_paired_suite.py`、評価manifest | D1とD2合格、D3とD4不合格 |

後攻初手のActive attack completionは、D3で公式catalog SHAの古い固定値により発火不能だった。

修正は公式catalog SHAへの置換とfail-closed fixtureの追加だけに限定し、D3を同じsemantic keyで再実行した。

## 変更ファイル

productionとrunnerの変更は次のとおりである。

- `mega_lucario_rule_agent/attack_outcomes.py`
- `mega_lucario_rule_agent/certificates.py`
- `mega_lucario_rule_agent/main.py`
- `mega_lucario_rule_agent/public_effects.py`
- `mega_lucario_rule_agent/resolver.py`
- `mega_lucario_rule_agent/routes.py`
- `mega_lucario_rule_agent/state_view.py`
- `mega_lucario_rule_agent/telemetry.py`
- `mega_lucario_rule_agent/transactions.py`
- `infrastructure/tools/build_mega_lucario_package.py`
- `infrastructure/tools/run_local_battle.py`
- `infrastructure/tools/run_seeded_paired_suite.py`

追加または変更したテストは次のとおりである。

- `tests/test_active_attack_completion_production_catalog.py`
- `tests/test_cape_public_survival.py`
- `tests/test_gate_a4_certificates.py`
- `tests/test_package_builder.py`
- `tests/test_poke_pad_core_search.py`
- `tests/test_requirement_routes.py`
- `tests/test_resolver.py`
- `tests/test_state_view.py`
- `tests/test_transaction_terminal_receipts.py`
- `tests/test_transactions.py`
- `tests/test_validation_hooks.py`
- `tests/test_wally_public_survival.py`
- `research/rl_ptcg/tests/test_run_local_battle_trace.py`
- `research/rl_ptcg/tests/test_run_seeded_paired_suite.py`

開始checkpoint、Gate 0証拠、評価schedule、追補manifestも追加した。

## fixtureと全テスト

追加fixtureは、Wallyの低damage生存差と高damage無価値、Cape前後の生存差とJamming、EnergyまたはTool付きGust、Active優位時のGust抑止、option順序不変性、false factsを持つcertificate、receiptなしturn跨ぎ、検証Telemetryの各正例と負例を含む。

transaction fixtureは、全owner typeの明示terminal receipt、許可された自動完了、missing callback、不可逆faultを扱う。

全テストの最終結果は次のとおりである。

| 項目 | 結果 |
|---|---:|
| passed | 530 |
| failed | 0 |
| skipped | 0 |
| Python | 3.11.6 |
| pytest | 8.4.2 |
| test file | 26 |
| test tree SHA-256 | `1288fc4a9d3bce04e1fe94856c485d73445f777624acaa73825bfb3a7498d006` |
| test schedule SHA-256 | `2a1c26c799065a5bad7447d651d1f146ec3a22746cf0de2dd95a78a3fa8e54eb` |

test tree SHA-256は、commit `75b6c7c`の`tests/*.py`について、`mega_lucario_rule_agent`相対path、bytes、file SHA-256をcompact sorted JSONへ変換した値である。

test schedule SHA-256は、candidate commit、実行command、Python version、test tree SHA-256をcompact sorted JSONへ変換した値である。

## deterministic smoke

最初のD2呼び出しはagent directoryをdeck pathとして渡したため、8 processが対戦開始前にexit 1となり、summaryは0 byteだった。

この呼び出しは証拠から除外せず、`d2_catalogfix_v1`として保存した。

引数だけを正した`d2_catalogfix_v1_retry1`を正式なD2として扱う。

| 項目 | 結果 |
|---|---:|
| opponents × seeds × seats | 2 × 2 × 2 |
| 1回あたりの対戦 | 8 |
| repeat | 2 |
| 合計 | 16 |
| action trace hash一致 | 8/8 |
| validation trace hash一致 | 8/8 |
| 勝敗と終了step一致 | 8/8 |
| action error | 0 |
| max-step | 0 |
| runtime fault | 0 |
| transaction fault | 0 |
| exception containment | 0 |
| unsupported stable MAIN | 0 |
| owner残存 | 0 |

D2の16-key SHA-256は`854799384647c3d261fb19aa4cc55b8919a67f9f08a170c3e097f826751f3e88`である。

## fixed160 discovery

D3は160個の`(panel, opponent, seat, seed)`を一度ずつ含み、parentとcandidateでscheduleは一致した。

engineはbaseline A、baseline B、candidateの480戦を実行し、duplicate controlの差は0だった。

| 指標 | parent | candidate |
|---|---:|---:|
| wins | 16 | 11 |
| losses | 144 | 149 |

paired gain、regression、tieは`0/5/155`であり、netは`-5`だった。

action error、max-step、runtime fault、transaction fault、invalid selected proofはすべて0だった。

監査対象routeのselected回数は、Active attack completion 3、Cape 1、Boss Gust 1、Hariyama Gust 1、Wally 0だった。

Active attack completionは3件ともglobal turn 2のActiveへEnergyを付け、証明した同turn attackを実行した。

この修正で旧candidateの1敗が1勝へ変わったが、parentも同じ対戦に勝っていたためpaired gainにはならなかった。

5件のregressionにおける最初の差は、Lillie 1件、Mega進化 1件、continuity attach 1件、即時fallback attack 2件だった。

D3 semantic key SHA-256は`ffcf1eddb04528798839df3bdc866628932b2e02d8377f3a189a7b80c780ec41`である。

## fixed760 confirmatory holdout

D4 scheduleはD3実行前に固定し、D3と重複しない760個のsemantic keyを使用した。

manifest SHA-256は`1b1667e27031bd1447a33921b3bdce57b8a51d32d43add444af33290a8c36ea0`、semantic key SHA-256は`af9f99a358e3c342cf485a85b9306bd7dbbbc349617b40c74607edad5015b1ad`である。

checked runnerがvalidation faultでprocessをfail-fastするため、同じ固定scheduleをhistorical 200戦、adjacent前半400戦、Kang 80戦、Cynthia 80戦の4区画で完走した。

全760 keyが一度ずつ存在し、baseline Aとbaseline Bのresult、step、action trace hashの差は0だった。

### 対戦結果

| panelまたはopponent | games | parent | candidate | 差 |
|---|---:|---:|---:|---:|
| historical panel | 200 | 2 | 2 | 0 |
| adjacent panel | 560 | 56 | 44 | -12 |
| Alakazam | 80 | 9 | 7 | -2 |
| Arch Peak | 80 | 5 | 5 | 0 |
| Arch Shumpei | 80 | 10 | 8 | -2 |
| Cynthia | 80 | 5 | 4 | -1 |
| Kang | 80 | 6 | 6 | 0 |
| Marnie | 80 | 11 | 8 | -3 |
| Mega mirror | 80 | 10 | 6 | -4 |
| 全体 | 760 | 58 | 46 | -12 |

paired gain、regression、tieは`0/12/748`だった。

絶対差は`-1.579`percentage point、親勝率に対する相対変化は`-20.7%`だった。

exact McNemarの両側p値は`0.00048828125`だった。

panelで層化したpaired seed-cluster bootstrapの95%区間は`[-2.632, -0.658]`percentage pointだった。

seat 0は`34→26`、seat 1は`24→20`であり、両席とも改善しなかった。

### routeとcertificate

| route | selected | 備考 |
|---|---:|---|
| Active attack completion | 48 | 48/48でActiveへ付与後に証明attackを同turn実行 |
| Boss Gust | 19 | 19/19でtransaction完了 |
| Wally | 0 | 自然対戦でselected証拠なし |
| Cape | 0 | validだが非選択が2件 |
| Hariyama Gust | 0 | 自然対戦でselected証拠なし |

Active attack completionの48件は1勝47敗だったが、この値はrouteの因果効果を表さない。

D4にはpaired gainがなく、12件のregressionの最初の差にActive attack completionはなかった。

### first difference

12件のregressionにおける最初の差は次の3群に分かれた。

- 資源または盤面順序6件：Ultra Ball、engine補完Bench 2件、board-out backup Bench、continuity attach、PPP breakpoint。
- SupporterまたはGustを攻撃前に選択した差3件：Lillie 1件、Boss Gust 2件。
- setupまたはattachより即時attackを選択した差3件：Aura Jab 2件、Corkscrew Punch 1件。

### fault

faultは次の3戦で発生した。

- Mega mirror、seat 1、seed `1618164122`
- Kang、seat 1、seed `1618164119`
- Kang、seat 1、seed `1618164145`

3戦すべてで`TRANSACTION_RUN_FAULT`、`UNEXPECTED_CONTEXT_REF`、`IRREVERSIBLE_FAULT:UNEXPECTED_CONTEXT_REF`、`FAULT_BOUNDARY_REACHED`を記録した。

原因は、commit済みAura Jab付与transactionが`context_ref=None`を期待した一方、engineが選択済みEnergyを`contextCard`として返したことだった。

runtime fault latchとtransaction fault latchは各3件だった。

exception containment、unsupported MAIN、unfinished owner、owner at new game、telemetry異常は0だった。

### runner差異

2個のcandidate processはfaultによってexit 1になったが、各40戦のsummaryとtraceは完了していた。

paired CSVは該当80戦のcandidate result、step、trace関連欄を空欄にし、`candidate_win=0`を既定値として残した。

Mega mirror、seat 1、seed `1618164153`はsummary上candidate勝利だったため、CSVの既定値と1件だけ勝敗が食い違った。

本報告は指定された2個のsummary JSONLだけから80戦を復元し、path、seed、game、seat、file hashを照合した。

CSVを黙って修正せず、差異を証拠として残した。

## 自己完結パッケージ

パッケージはcommit `d2f2511`のdetached clean worktreeから生成した。

| 対象 | SHA-256 |
|---|---|
| 公式cg archive | `6fc2e64adac2a308b19b3b3791a307106b3c84621bd3b4f4dfb099838abbd907` |
| 公式cg tree | `4a8df9388d9bc6b6d3d29833d20f4361ebea9c364a3bf0da20e60897bfec1b54` |
| packaged runtime tree | `41dc89180d35400c00aa4615c30339d61eacbc782014278d8b60b57f8589fefc` |
| inner tar.gz | `e89daf23edcae148b423f37d9a483e3eed600686b5b10fe582f90b5cb3dd8eea` |
| package manifest | `ebbb7df341a8d2c911578f21342a39c8c0d4b205a2b87e43a62695f6e97bb4fb` |
| verification JSON | `63eb72836d2e69572d79650e9e1043cdf4e3f6aeab63d3ae8ed71c3627c97b6b` |
| outer ZIP | `cf49e0015e69b7eb0b4e237192d14be0f3e640fbdec2395949f29178906e2f9f` |

clean re-extract、任意cwd、ambient cgなし、root import、registry初期化、deck callback 60枚、公式cg allowlist、path安全性はすべて合格した。

公式cgはsemantic versionを公開しないため、選択binary `cg/cg.dll`のSHA-256 `9ea2b0a751029689bff3ddccb5f29a98edd46961dad264490ed121ef704fb500`をengine同一性として記録した。

## 未解決UNKNOWN

- Aura Jab付与transactionの正しい`context_ref`契約は、3件の実対戦faultを残している。
- Iron Defenderの持続状態はObservationに確実な形で保持されないため、Active attack completionはMetal対象をfail-closedで除外する。
- 相手由来のattack lock履歴は完全には再構成できない。
- 公式cgはsemantic versionを公開しないため、binary hash以上のversion表現はUNKNOWNである。
- WallyとHariyama GustはD4で発火せず、Capeもselectedされなかったため、自然対戦上の有効性は未確認である。

## 最終判定

**`REJECT_REQUIREMENTS_NOT_MET`**

focused fixtureとパッケージ検証の合格は、fixed760の強化条件とfault 0条件を代替しない。

Sol Ultraの独立数値監査と最終戦略判定も同じlabelを選択した。

次のcandidateでは、Aura Jabのcontext receiptをseed例外なしで修正し、12件のregression keyを診断した上で、新しいidentityと未使用holdoutを固定する必要がある。

再採用には、net paired gain `+5以上`、fault 0、action error 0、max-step 0、両席の安全性、主要対面floor、少なくとも1件の意図したrule起点のgainが必要である。
