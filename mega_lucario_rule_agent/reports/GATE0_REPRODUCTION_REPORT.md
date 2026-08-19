# Gate 0 監査反例再現報告

- 対象branch: `codex/megalucario-audit-repair-20260805`
- 対象HEAD: `4cfdffae54561c9b6b054f4a9d461536ef573385`
- 監査対象implementation commit: `8c8f43b1478d0d64239ed5190f50a04409dd6f61`
- 監査報告SHA-256: `2a50ab0d0be3e5492cceeee084880e49f68ccda0aa8af1a3f371f3e2e8d2704f`
- 元要件書SHA-256: `47cb7fe3d426a14281699e6882f37ea24ce5979a11f1c2a15cf5bc7edaf5e0d7`
- 実行環境: Python 3.9.13
- 判定: **Gate 0 PASS（5反例すべて再現）**

この報告まで、productionの戦術・transaction・runtime codeは変更していない。

## A. Wally

相手Activeのregistry attackが0件、Active Mega Lucario exが180 damage、Fighting Energy
1枚付き、Aura JabとWallyが合法な状態を構築した。

- proposal: 1件
- selected rule: `R_WALLY_THREE_PRIZE_REBOOT_V1`
- tier: `SURVIVAL_CRITICAL_WALLY`
- certificate: `deck_rule_v1 / RESOURCE_IMPROVEMENT / valid=True`
- certificate digest: `b5ca3090eeef7a66208c08f231bd704874943112b9ddd8c6fbe21ec0c54d30b3`
- facts: `large_damage=True`, `three_prize_save=False`, `damage_healed=180`
- proposal rejection: なし
- first rejection reason: `null`

公開attackが存在せず生存差を計算できないにもかかわらず、固定180 damage条件だけで
proposalとvalid certificateが発行される監査指摘を再現した。

## B. Hero's Cape

Aと同じ相手Active attack 0件・Mega Lucario ex 180 damage状態で、Hero's Cape attachを
合法にした。

- proposal: 1件
- selected rule: `R_CAPE_EXPLICIT_PROTECTION_V1`
- tier: `CERTIFIED_SURVIVAL`
- certificate: `deck_rule_v1 / RESOURCE_IMPROVEMENT / valid=True`
- certificate digest: `b963bd95b9d2e78beac6e50274f2a7aa77c79923024129b77811b2bf857dccd5`
- facts: `purpose=THREE_PRIZE_MEGA`, `damage_before=180`
- proposal rejection: なし
- first rejection reason: `null`

Cape前後の生存差が存在しない状態でもvalid certificateが発行される監査指摘を再現した。

## C. Gust

相手Benchへ、次の公開状態を持つ非Mega Pokémon exを構築した。

- 残りHP: 100
- Prize価値: 2
- attached Energy: 1枚
- Aura Jabのexact damage: 130
- 現在Active: 300 HP・1 Prize
- Boss's Orders: 合法

結果:

- proposal: 0件
- certificate: なし
- first rejection reason: `TARGET_HAS_ATTACHED_ENERGY`
- production該当guard: `routes.py` の `or target.energy_refs`

proposal自体が作られないため、resolver rejectionもcertificateも存在しない。監査で指定された
100 HP・2 Prize・Energy付き・確定KO Bench targetを正確に再現した。

実行コマンド:

```text
python -m mega_lucario_rule_agent.reports.audit_gate0_exact_two_prize_gust
```

## D. transaction turn release

`two_step_plan()`のroot actionを開始した直後のcommit済みownerに対し、必須
`SELECT_EFFECT_TARGET` callbackを与えずturnを5から6へ進めた。

- status: `TURN_RELEASE`
- reasons: `TURN_OR_RESULT_CHANGED`
- owner remaining: `False`
- `run_fault_latched`: `False`
- first rejection reason: `TURN_OR_RESULT_CHANGED`

必須terminal receiptなしのturn changeがfaultではなく正常releaseになる監査指摘を再現した。
同じ現行期待値は `tests/test_transactions.py::test_new_game_or_turn_releases_owner_without_erasing_fault_history`
にも存在する。

## E. Telemetry無効下のexception containment

通常の`AgentRuntime()`へ決定論的な内部`RuntimeError`を注入し、合法END option 1件の
callbackを実行した。

- telemetry enabled: `False`
- runtime fault latched: `True`
- returned action: `[0]`
- returned action is legal index: `True`
- telemetry record count: `0`
- first rejection reason: `TELEMETRY_DISABLED`

内部exceptionをcontainment actionで隠し、外部runnerからは合法actionとして継続できる一方、
fault eventを取得できない監査指摘を再現した。

## 実行方法

A、B、D、Eおよび補助的な旧3-Prize Gust反例:

```text
python -m _local_generated.mega_lucario_audit_repair_20260805.gate0_reproduce
```

契約どおりの2-Prize Gust反例:

```text
python -m mega_lucario_rule_agent.reports.audit_gate0_exact_two_prize_gust
```

## 次Gate

Gate A1ではWallyだけを変更する。固定damage閾値は別閾値へ置換せず、相手Activeの公開attack
outcome、heal前後のKO差、同turnのproductive attack、Supporter優先度を再計算する。
公開attack outcomeがUNKNOWNならsurvival-critical certificateを発行しない。

