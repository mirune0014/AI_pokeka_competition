# v4 B0 fix2 絶対強度基準 実行仕様

## 親契約

- 不変契約:
  `alakazam_staged_20260729/specs/v4_setup_survival_wall_pipeline_immutable_contract.md`
- SHA-256:
  `B0657D0118847F2DDF7680E6D75AE28F2DF6CF42EE338B6355ADDC731F454783`

候補の対戦結果を集計・閲覧する前に、B0の絶対強度を凍結する。

## B0 identity

- source:
  `alakazam_staged_20260729/versions/alakazam_newdeck_v3_exact_evolution_ko_fix2`
- policy closure、33 files:
  `DC90205DE06AE3E2E41ADC661577096BB02EE5B42AB9F4366FC1A01154745B47`
- planner:
  `255FD9E1303E8E6DFB286952023A7F086CD233B4E5D5030EDBE06313A40697B7`
- deck:
  `F598F5E578D0440C96DC0492EAECF2E19739B7A23225BE57114A724EF7D0FB94`

## 実行環境

- Python:
  `C:/Users/amuam/project/AI_pokeka_competition/.venv-rl/Scripts/python.exe`
- engine:
  `C:/Users/amuam/project/AI_pokeka_competition/analysis_outputs/cynthia_v9_vs_v11_poffin_role_selection_20260713/seeded_engine`
- engine tree:
  `466638706BD5C6915E25D1B3CB9E3D966390FBC263F4ED3153108E29C0194FFF`
- launcher:
  `tools/run_alakazam_staged_metric_suite.py`
- launcher SHA-256:
  `BCC98229B23C86FC5EB248D3F1E254337008FF4E85BD85224B3B3D6F570F1EEA`
- battle runner SHA-256:
  `E1ABA0151CDAEE425B858511AA760CE5C5647D555DDEFBD69D7319C29C5B773B`
- metric common SHA-256:
  `78A0BE6E87368939D7FCE590E1AA65B5DFFA228DE224FFB53AA42C8DE1EF295B`
- 参照manifest:
  `alakazam_staged_20260729/metrics/formal_frozen_7opp_50seed/suite_manifest.json`
- 参照manifest SHA-256:
  `4BD79050DD5C1A3A846F69D6F539A5384DCA9C2E1DAC56C7576B02F0FCEA744D`

## 凍結schedule

- opponents: 7
- seats: 0, 1
- seed bases:
  `202608500`, `202608510`, `202608520`, `202608530`, `202608540`
- games per block: 10
- games per opponent: 100
- total games: 700
- blocks: 70
- max steps: 1000
- watchdog: 180 seconds per block

opponent paths:

```text
marnie=C:/Users/amuam/project/AI_pokeka_competition/meta_agents/marnie_sota_live_85033057_simple
cynthia=C:/Users/amuam/project/AI_pokeka_competition/meta_agents/cynthia_garchomp_nasuo445_v80_legal_complete_role_cycle
alakazam_mirror=C:/Users/amuam/project/AI_pokeka_competition/meta_agents/alakazam_oselcoun_live_85035844_simple
rocket_mewtwo_spidops_proxy=C:/Users/amuam/project/AI_pokeka_competition/meta_agents/rocket_mewtwo_spidops_kashiwashira_20260703_simple
kangaskhan_crustle=C:/Users/amuam/project/AI_pokeka_competition/meta_agents/kangaskhan_crustle_mpgaming_v13_backupkang_two_growline
historical_silver=C:/Users/amuam/project/AI_pokeka_competition/analysis_outputs/reference_agents/historical_silver_archaludon_54495224
direct_frozen=C:/Users/amuam/project/AI_pokeka_competition/alakazam_staged_20260729/eval_adapters/alakazam_800_frozen
```

## fresh出力

`alakazam_staged_20260729/metrics/formal_v4_b0_fix2_7opp_50seed`

既存directoryへ再実行、削除、上書き、途中結果のpoolをしない。
機械的失敗時は`attempt_N`の新規出力へ、同一commandを変更せず再実行する。

## 実行command

workspace rootをcwdとし、次を一つのprocessとして実行する。

```text
.venv-rl/Scripts/python.exe -B tools/run_alakazam_staged_metric_suite.py
  --engine-dir analysis_outputs/cynthia_v9_vs_v11_poffin_role_selection_20260713/seeded_engine
  --version b0=alakazam_staged_20260729/versions/alakazam_newdeck_v3_exact_evolution_ko_fix2
  --opponent marnie=meta_agents/marnie_sota_live_85033057_simple
  --opponent cynthia=meta_agents/cynthia_garchomp_nasuo445_v80_legal_complete_role_cycle
  --opponent alakazam_mirror=meta_agents/alakazam_oselcoun_live_85035844_simple
  --opponent rocket_mewtwo_spidops_proxy=meta_agents/rocket_mewtwo_spidops_kashiwashira_20260703_simple
  --opponent kangaskhan_crustle=meta_agents/kangaskhan_crustle_mpgaming_v13_backupkang_two_growline
  --opponent historical_silver=analysis_outputs/reference_agents/historical_silver_archaludon_54495224
  --opponent direct_frozen=alakazam_staged_20260729/eval_adapters/alakazam_800_frozen
  --seed-base 202608500
  --seed-base 202608510
  --seed-base 202608520
  --seed-base 202608530
  --seed-base 202608540
  --games-per-block 10
  --max-steps 1000
  --watchdog-seconds 180
  --output-dir alakazam_staged_20260729/metrics/formal_v4_b0_fix2_7opp_50seed
```

実processでは上記各pathを解決済み絶対pathとして渡してよい。
version、opponent、schedule、games、max steps、watchdog、出力identityは変更しない。

## runnerが返すraw evidence

解釈せず、次だけを返す。

- exact command
- cwd、Python、環境変数
- start/end時刻
- process exit code
- stdout/stderr path、bytes、SHA-256
- output directory
- `suite_execution_summary.json`
- `suite_manifest.json`
- block数、complete block数
- 各summary、sidecar、battle traceの存在
- source、deck、engine、toolの実行時SHA-256

## root検証

rootがraw summaryから独立に次を再計算する。

- 700 unique `(opponent, policy_seat, seed)`
- 各opponent 100、各seat 350、各seed base 140
- policy seat 0は`result == 0`、seat 1は`result == 1`を勝ちとする
- overall、opponent、seat、opponent-seat、20-game seed blockの勝敗
- action error合計
- max-step hit
- invalid result
- unstarted／missing game
- process exitとblock completeness

検証済みoverall winsを最初の`ABS_FLOOR`として別のroot verificationへ保存する。
この段階では候補の改善・採否を判断しない。
