# v4 Fix7 ベンチ0・END・シェイミ限定候補の実局面スクリーニング仕様

日付: 2026-07-31

## 目的

`BENCH0_END_SHAYMIN_EMERGENCY_FIX7` が、根拠となった4つの公開局面で実際に発火し、3つの既存敗北を勝利へ変え、1つの既存勝利を維持するかを先に確認する。

この実行は、候補のproduction採用を決定しない。

4局面のスクリーニングを通過した場合だけ、7対面700組とMega Lucario 2系統を含む900組の正式比較へ進む。

## 固定する入力

BaselineはC2 action pathとする。

```text
alakazam_staged_20260729/eval_adapters/
  alakazam_newdeck_v4_next_attacker_distance_shadow_fix4b
```

- C2 production closure: `29084BC13CB74236ABE557B57A9E633A8F9E88FA83FF22D131C835293E987157`
- 検証済みC2 archive: `9F4DE9078E522501F99AEA97FC1D8319C3C81C93869EA1D2D5E2CEE2239B5E1A`
- adapter `main.py`: `EAF8763BAE815637DE07C73D039BD1EF54BD8F04B17F6D74C97E73FAE7C7B4C5`

CandidateはFix7単独候補とする。

```text
alakazam_staged_20260729/versions/
  alakazam_newdeck_v4_bench0_end_shaymin_fix7
alakazam_staged_20260729/eval_adapters/
  alakazam_newdeck_v4_bench0_end_shaymin_fix7
```

- candidate rule closure: `575B3F524AD007D0CA055B0647A03DD363C8FB06CEC028E29AA10460CBBECE5B`
- candidate implementation-tree: `AC567CA4D6D40715D51C59FD94BAA57A16BEDADC0A59CA53FC0A7D4F04CE9AC4`
- `planner_public_survival_bench0.py`: `779A3F47ECBB352C688320A7D3EC1EC2FD6A9C56A11D5867D5F141BB678AFD0A`
- observed fixture manifest: `086BCA09DAB2B941029BBB00C947C12B711BE80152266885DCB35950A8B64E63`
- candidate adapter `main.py`: `3D7F7D86EE5F49DF5E1555C4E6A219F2C5A4E0A4FB4FF1E5EBDE2A33B69E2E0D`

共通deckは60枚で、SHA-256は次とする。

```text
F598F5E578D0440C96DC0492EAECF2E19739B7A23225BE57114A724EF7D0FB94
```

## 固定する実行系

- Python: `.venv-rl/Scripts/python.exe`
- engine: `analysis_outputs/cynthia_v9_vs_v11_poffin_role_selection_20260713/seeded_engine`
- engine tree: `466638706BD5C6915E25D1B3CB9E3D966390FBC263F4ED3153108E29C0194FFF`
- paired runner: `tools/run_seeded_paired_suite.py`
- paired runner SHA-256: `5EC25C98F2777FF61DE2DBD0A03A08519A7FEA4B2B4C510B5B8895BC2000E000`
- battle runner SHA-256: `E1ABA0151CDAEE425B858511AA760CE5C5647D555DDEFBD69D7319C29C5B773B`
- metric runner: `tools/run_alakazam_staged_metric_suite.py`
- metric runner SHA-256: `BCC98229B23C86FC5EB248D3F1E254337008FF4E85BD85224B3B3D6F570F1EEA`
- games per seat/panel: `10`
- seats: `0, 1`
- max steps: `1000`

## 固定する4パネル

| panel | opponent path | seed base | 根拠局面 |
|---|---|---:|---|
| historical_silver_202608520 | `analysis_outputs/reference_agents/historical_silver_archaludon_54495224` | 202608520 | seat 1、game 2、seed 202608522 |
| kangaskhan_crustle_202608520 | `meta_agents/kangaskhan_crustle_mpgaming_v13_backupkang_two_growline` | 202608520 | seat 0、game 2、seed 202608522 |
| marnie_202608510 | `meta_agents/marnie_sota_live_85033057_simple` | 202608510 | seat 1、game 8、seed 202608518 |
| mega_lucario_aib4_202609500 | `meta_agents/mega_lucario_aib4_live_84983544_simple` | 202609500 | seat 1、game 3、seed 202609503 |

paired出力は次へ保存する。

```text
alakazam_staged_20260729/evaluations/
  v4_fix7_bench0_end_shaymin_targeted_4panel_20260731/
    <panel>/
```

candidate sidecar出力は次へ保存する。

```text
alakazam_staged_20260729/metrics/
  formal_v4_fix7_bench0_end_shaymin_targeted_4panel_20260731/
    <panel>/
```

各paired panelは20 unique `(opponent, policy_seat, seed)` 行を生成する。

4パネル合計は80 unique paired行、baseline 80ゲーム、candidate 80ゲームとする。

metricは各パネル20ゲーム、合計80 candidateゲームとする。

## 実行者の制約

`ptcg_eval_runner` は、上記のchecked runnerと固定scheduleだけを実行する。

独自aggregateを作らず、command、exit code、raw path、manifest、row count、hashだけを返す。

数値解釈と採否判断を行わない。

## 機械的な完全性条件

- 全paired/metric child exit codeが0。
- timeout、unstarted、action error、max-step、invalid resultが0。
- 各paired panelが20 unique key。
- baselineとcandidateのscheduleが完全一致。
- metric sidecarのCALL_STARTとCALL_ENDが完全対応。
- candidate rule closureとrule versionが全callbackで一致。
- stale index、duplicate/rebind fault、transaction fault、wrapper exception、metric exceptionが0。

## スクリーニング通過条件

4つの根拠局面について、baselineの既知結果を再現する。

- Historical Silver: baseline loss。
- Marnie: baseline loss。
- Mega Lucario AIB4: baseline loss。
- Kangaskhan/Crustle: baseline win。

Candidateは4局面で正確に1回ずつ発火し、`END → Shaymin Hand-to-Bench → END` を完了する。

Candidateは3つのbaseline lossをすべてwinへ変え、Kangaskhan/Crustleのbaseline winを維持する。

80組全体でbaseline winからcandidate lossへの反転を0とする。

自然reentry mismatch、saved-END回復、abort、faultを0とする。

3つの改善局面では、単なる終局遅延ではなく、次の自ターン到達と、その後の盤面形成、攻撃、またはサイド取得の少なくとも一つをserial付きtraceで確認する。

一つでも満たさない場合、Fix7は正式900組へ進めず、production pathはC2のままとする。

## 通過後の正式比較

スクリーニング通過時だけ、固定7対面・5 seed block・両seatの700組と、Mega Lucario 2系統200組を同一seedで実行する。

正式比較の採用条件は、Sol-Ultra戦略判定で定めた次を最低条件とする。

- candidate `>=454/700`。
- candidate `>=638/900`。
- Historical Silver、Marnie、Mega Lucario AIB4が各`+1/100`以上。
- Kangaskhan/Crustleの既存勝利局面を維持。
- 全opponent、opponent-seat、10-game cellに負deltaがない。
- baseline reachで4発火、parent transaction 3件とPrize-futile 10件は非発火。
- 全発火で自然END reentry mismatchとfaultが0。

900組だけではproduction採用を確定しない。

別seed確認でunique fire 12件以上、両seat各4件以上、3対面以上、baseline winからcandidate lossが0であることを追加で要求する。
