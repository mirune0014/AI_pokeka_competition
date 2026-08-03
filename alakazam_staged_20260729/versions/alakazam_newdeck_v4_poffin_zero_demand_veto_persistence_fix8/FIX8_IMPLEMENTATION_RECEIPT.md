# Fix8 implementation receipt

## 対象と動作意図

- Base:
  `alakazam_staged_20260729/versions/alakazam_newdeck_v4_next_attacker_distance_shadow_fix4b`
- Isolated destination:
  `alakazam_staged_20260729/versions/alakazam_newdeck_v4_poffin_zero_demand_veto_persistence_fix8`
- Rule:
  `V4_POFFIN_ZERO_DEMAND_VETO_PERSISTENCE_FIX8`

この候補が変更するのは、transaction-freeな通常MAINでC2親がBuddy-Buddy Poffinを選び、公開情報だけからPoffin需要0を証明できた場合だけである。

初回は全Poffin PLAY optionを除いた観測cloneで同じC2親を再評価し、stable option keyが元観測に一意に対応するときだけ、その非Poffin actionへ変更する。

同一turn内でcanonical eligibilityが同じままPoffinが再提案された場合は、独立latchによって同じ拒否を継続する。

canonical eligibilityには、owner、turn、first player、通常MAIN証明、全Poffin PLAY stable key、A/N/F、own fieldの構造fingerprint、公開／未知のAbra・Dunsparce在庫、公開partition、normal capacity、Abra final-slot exception、zero-demand reasonを含む。

`turnActionCount`はeligibility hashへ含めず、巻き戻り検出用のclockとしてのみ保存する。

fieldの構造fingerprintはline identityだけを含み、energy/tool attachmentは含まない。
したがって、手張りを挟んでもPoffin需要が変わらない限りlatchを維持する。

owner、turn、eligibility、公開在庫、A/N/Fが変わった場合はreleaseして再計算する。
turn/action count巻き戻り、game result、handshake、外部`reset()`、公開状態不整合でもclearする。

active V1/integrated/parent transactionと非MAIN callbackでは親actionをそのまま保持する。
inherited transactionまたはV1 transactionがcallback内で完了し、delegateがPoffinを返した場合は、そのcallback内で再判定する。

曖昧・欠損stable key、filtered rerank失敗、元観測への非一意rebind、違法actionは、親C2 actionと親post-stateを保持してfail-closedする。

## C1から取り込んでいない動作

次の動作は実装していない。

- Poffin child optionの選択変更
- AbraとDunsparceのrole substitution
- Poffin child cardinality変更
- physical card serialまたはoption orderの変更
- `_apply_v4_poffin_main`
- `await_v4_poffin_*`
- `_v4_poffin_child_decision`
- `_v4_select_poffin_roles`
- C1のPoffin transaction

production sourceを対象にしたsymbol検索は
`C1_CHILD_ROLE_SUBSTITUTION_SYMBOLS_ABSENT`であった。

## 変更ファイル

- `planner_deck_adaptation_v1.py`
  - bytes: `180420`
  - SHA-256:
    `9B6B6F627D1529A475239129A92EAEDA5564B42771AA2618260A34E6AB1666D8`
  - 独立latch、canonical eligibility、filtered parent rerank、trace、transaction completion seamを追加した。
- `main.py`
  - bytes: `9583`
  - SHA-256:
    `E65C3801B095830D47CE3658001DC06203E1C6E001768A433E8567E034A03263`
  - Fix8 traceをsidecar surfaceへ公開し、handshake時にlatchをresetして完全な親deck handshakeへ委譲する。
- `test_v4_poffin_zero_demand_veto_persistence_fix8.py`
  - bytes: `20925`
  - SHA-256:
    `CC755AC943541BE000E0C402573127CE26D0FBB2E62C4A45B59D4C703684705C`
  - 15個のFix8専用テストを追加した。

deck、runtime loader、runtime deck、C2 shadow analyzer、既存test、verification、frozen submissionは変更していない。

baseとの差分は次のとおりである。

```text
ADDED 1
  test_v4_poffin_zero_demand_veto_persistence_fix8.py
REMOVED 0
CHANGED 2
  main.py
  planner_deck_adaptation_v1.py
UNCHANGED 55
```

## Hash

closure algorithmは、top-levelの非test Python、top-level `deck.csv`、`runtime/main.py`を相対path順に並べ、
`path + NUL + uppercase SHA-256 + NUL + byte size + LF`を連結してSHA-256を取る。

```text
BASE_CLOSURE_FILE_COUNT 34
BASE_CLOSURE_SHA256
29084BC13CB74236ABE557B57A9E633A8F9E88FA83FF22D131C835293E987157

CANDIDATE_CLOSURE_FILE_COUNT 34
CANDIDATE_CLOSURE_SHA256
EFB56EF6FDC551B3E44ACA2F7EEC1F805A2E37C3834EE629F7C4637FB0CF1E76
```

implementation treeはcache、bytecode、`*_RECEIPT.md`、継承された
`V0_IMPLEMENTATION_RECEIPT.md`を除く全fileへ同じrow algorithmを適用した。

```text
BASE_IMPLEMENTATION_TREE_FILE_COUNT 57
BASE_IMPLEMENTATION_TREE_SHA256
F9C78B5A14A5734C53E29FC9C57BDD660C09FD73F825E1659EB7830C7846F44B

CANDIDATE_IMPLEMENTATION_TREE_FILE_COUNT 58
CANDIDATE_IMPLEMENTATION_TREE_SHA256
401D4DAC46292F4EC689646EA532EC2F6A196829FFFE1B0D733AEB24790D111B
```

deck identity:

```text
deck.csv rows 60
deck.csv SHA256
F598F5E578D0440C96DC0492EAECF2E19739B7A23225BE57114A724EF7D0FB94
runtime/deck.csv byte-identical true
runtime/main.py unchanged SHA256
5100355E5756C16B4E38276DA79551A7F9D1F47D62B863C295D9302B06AE4A24
```

## 検証

すべてPython 3.11で実行し、次のengine import pathを使用した。

```powershell
$env:PYTHONPATH='C:\Users\amuam\project\AI_pokeka_competition\alakazam_staged_20260729\submissions\alakazam_newdeck_v4_c2_safe_final_20260730\runtime_smoke_extract'
```

Fix8専用test:

```powershell
py -3.11 -B -m unittest -q test_v4_poffin_zero_demand_veto_persistence_fix8.py
```

結果:
exit `0`、`Ran 15 tests`、`OK`。

専用testは次を含む。

- 初回zero-demand veto
- 同一eligibilityでの継続veto
- `turnActionCount`増加を跨ぐ保持
- energy attachmentを跨ぐ保持
- A/N/F changeによるrelease／再計算
- 公開inventory changeによるrelease／再計算
- turn change、action-count rollback、外部reset
- runtime handshake/new-game reset
- active transaction優先
- inherited transactionの同callback完了後再veto
- V1 transactionの同callback完了後再veto
- unique stable rebind
- missing／ambiguous rebindのfail-closed
- rerank例外時の元parent object保持
- 非発火action identity
- Poffin child actionのparent object・physical serial・order identity
- Cynthia型の即時再提案
- Marnie型の他action後再提案

全回帰:

```powershell
py -3.11 -B -m unittest discover -q -p 'test_*.py'
```

結果:
exit `0`、`Ran 207 tests`、`OK`。

compile:

```powershell
@'
from pathlib import Path
from tokenize import open as tokenize_open
paths = (
    sorted(Path('.').glob('*.py'))
    + sorted(Path('runtime').glob('*.py'))
    + sorted(Path('verification').glob('*.py'))
)
for path in paths:
    with tokenize_open(path) as handle:
        compile(handle.read(), str(path), 'exec')
print('COMPILE_OK', len(paths))
'@ | py -3.11 -B -
```

結果:
exit `0`、`COMPILE_OK 45`。

deck validation:

```text
DECK_ROWS 60
DECK_COLUMNS_EXACT_ONE True
RUNTIME_DECK_BYTE_EQUAL True
```

runtime handshake smoke:

```text
module.agent({'select': None, 'current': None, 'logs': []})
RUNTIME_HANDSHAKE_SMOKE_OK 60
POFFIN_ZERO_DEMAND_LATCH is None
```

## 既知の制限と評価側の確認事項

- 旧C1 discordant traceは完全なengine observationを持たないため、Cynthia/Marnie型testは同じmulti-callback機構を固定公開状態で再構成したものであり、勝率証拠ではない。
- 公開60枚partition、Poffin PLAY key、field identity、role inventoryのいずれかを証明できない場合は発火しない。
- zero-demand理由は
  `NO_LEGAL_EMPTY_BENCH`、
  `PUBLIC_ROLE_BASICS_DEPLETED`、
  `ZERO_NORMAL_CAPACITY_NO_ABRA_EXCEPTION`、
  `ZERO_ROLE_DEMAND`
  に限定している。
- filtered parent rerankがparent transactionを開始した場合は、その完全なparent post-stateを保持する。
- この実装はlocal win-rate、matchup improvement、採用を主張しない。

評価側は、同一seed・両seatでC2とFix8を比較し、少なくとも次を確認する必要がある。

1. Cynthia `seat1 seed202608520`とMarnie `seat1 seed202608536`で、初回拒否後の同一eligibility再提案を継続拒否すること。
2. Poffin childのcardinality、Abra/Dunsparce選択、physical serial/orderがC2と完全一致すること。
3. Rocket、Historical Silverを含む全panelで、C1 role substitution由来のfirst divergenceが存在しないこと。
4. action error、max-step、transaction abort、ambiguous rebindが0であること。
5. traceのARM/HOLD/RELEASE/FAIL_CLOSED、eligibility hash、parent/proposed/applied actionがcallback生ログから監査できること。
6. rerank後に始まるparent transactionが次callbackでも正常に継続すること。

## Archiveと外部操作

archive/packageは作成していない。
Kaggle API、upload、submission、Notebook、Discussion、Codex configurationには触れていない。
