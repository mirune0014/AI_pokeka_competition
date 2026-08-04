# Mega Lucario 監査修正チェックポイント

## 固定目的

`mega_lucario_implementation_audit_20260805.md` と添付修正契約に従い、現行版を
`MEGA_LUCARIO_RULE_AGENT_FOUNDATION_AND_UNVALIDATED_POLICY_V1` として凍結した上で、
元要件の不一致を Gate 0 → A1 → A2 → A3 → A4 → B1 → B2 → C → D の順に修正する。

最終的な採用可否はコード経路やfixture数ではなく、self-contained package、fault 0、
fixed160、未調整fixed760、および意図したfirst differenceで判定する。

## 開始状態

- 記録日: 2026-08-05
- repository: `C:\Users\amuam\project\AI_pokeka_competition`
- 元branch: `codex/megalucario-rule-based-agent`
- 修正branch: `codex/megalucario-audit-repair-20260805`
- 開始HEAD: `4cfdffae54561c9b6b054f4a9d461536ef573385`
- 監査対象implementation commit: `8c8f43b1478d0d64239ed5190f50a04409dd6f61`
- 元upstream: `origin/codex/megalucario-rule-based-agent`
- remote: `https://github.com/mirune0014/AI_pokeka_competition.git`
- Python: `3.9.13`
- pytest: `8.4.2`
- ruff: `0.15.9`

## 読み取り専用入力

| 入力 | bytes | SHA-256 |
|---|---:|---|
| `C:\Users\amuam\Downloads\mega_lucario_rule_based_agent_requirements_20260804.md` | 53,726 | `47cb7fe3d426a14281699e6882f37ea24ce5979a11f1c2a15cf5bc7edaf5e0d7` |
| `C:\Users\amuam\Downloads\mega_lucario_implementation_audit_20260805.md` | 15,608 | `2a50ab0d0be3e5492cceeee084880e49f68ccda0aa8af1a3f371f3e2e8d2704f` |
| `C:\Users\amuam\.codex\attachments\fe33f533-42b9-4524-ab56-8db668cdffd6\pasted-text.txt` | 17,152 | `6793ae2a4427b7eb18de2926b397630d25ad7174fa96ed25efb8542bc0434f68` |

開始時の `git ls-files -- mega_lucario_rule_agent` は41件。各ファイルの
`relative_path,sha256` をpath順にLF結合し末尾LFを付けたmanifest digestは、
`dfcfde72c43140ff59074cfac30e8903b5a90c94aac92951ad9110219e5c71ea`。

## 所有権境界

- 修正対象: `mega_lucario_rule_agent/**` と、この修正専用の `_local_generated/**`。
- 監査報告、元要件書、添付契約、既存分析ZIPは読み取り専用。
- Kaggle提出、Notebook公開、Discussion投稿は本修正の非目標。
- 新branchのpushはrootだけが行い、実施時点で外部書込み権限を再確認する。

開始時から存在する次の変更は別作業のユーザー所有物であり、stage・編集・削除しない。

- `alakazam/versions/*/verification/run_c2_action_identity_probe.py` 7件
- `archaludon/comparisons/historical_silver_vs_task9_20260802/SOL_ULTRA_NUMERICAL_AUDIT_CALC.py`
- `archaludon/numerical_audits/**/audit*.py` 5件
- `archaludon/root_verification/archaludon_boss_ledger_dormancy_20260730/run_diagnostic_fixed760.py`
- `infrastructure/scripts/bootstrap_ptcg_venv.ps1`
- `research/experiments/archaludon_latest_v1_rl_pcgrad_candidate_20260801/scripts/run_complete_action_bc_2000.ps1`
- `research/experiments/archaludon_latest_v1_rl_pcgrad_candidate_20260801/scripts/run_complete_action_dagger1.ps1`
- `docs/venv_migration_repair_20260804.md`（untracked）

## 正確な定義

- `parent`: 開始HEADの `mega_lucario_rule_agent`。
- `candidate`: このbranchで監査契約に従って変更した同ディレクトリ。
- `focused fixture`: 添付契約がGateごとに列挙した必須正例・負例。期待値は弱めない。
- `official cg`: repository内で現行公式sample submission由来と追跡可能な無改変ディレクトリ。不明なら推測せず `PACKAGE_BLOCKED_MISSING_OFFICIAL_CG`。
- `UNKNOWN`: 公開attack/effect/receipt/engine表現を厳密に再計算できない状態。強いcertificateを発行せず既定fallbackへ戻す。
- `完成`: fixed760のnet paired gain gate、fault 0、self-contained artifactを含む元要件の全条件を満たす状態。

## 凍結した検証順

1. Gate 0の5反例を修正前コードで再現し、proposal/reason/certificate/first rejection reasonを保存。
2. A1 Wallyだけを修正し、A1 focused fixture合格後に進む。
3. A2 Capeだけを修正し、A2 focused fixture合格後に進む。
4. A3 Gustだけを修正し、A3 focused fixture合格後に進む。
5. A4 route固有verifierを実装し、caller factsだけの証明を拒否。
6. B1 transaction terminal receipt、B2 verification telemetry/fault昇格を順に実装。
7. Cで公式cgを同梱したartifactをclean unpack・arbitrary cwd・ambient cgなしで検証。
8. D1 focused/full tests、D2固定8戦×2、D3 fixed160、D4未調整fixed760を順に実施。

複数戦術を一度に変更しない。fixed760を見た後に条件を調整しない。

## 現在のcheckpoint

- 完了phase: 開始状態・入力hash固定、専用branch作成、元要件・監査・契約の再読
- 現在phase: Gate 0 read-only reproduction
- code変更: なし
- destructive action: なし
- external write: なし
- deviation: なし
- 次action: Gate 0用fixtureを既存builderで作成し、A〜Eの現行挙動を保存する

