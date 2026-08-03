# v4 C3 public-survival bench-0 fix5 独立数値監査

日付: 2026-07-30

## 結論

**C3 action gate は FAIL。不採用とする。**

候補と baseline は 700 paired games の全行で勝敗が同じだった。独立再計算は
baseline `452-248 (64.57%)`、candidate `452-248 (64.57%)`、
gain/loss/tie `0/0/700`、差 `0/700 = 0.00pp` である。これは小さな正の改善
ではなく、観測 schedule 上の実用効果が完全に 0 という結果である。
candidate absolute floor `452` は境界値で通過したが、positive overall、
Historical Silver `+3/100`、Silver positive seed block、mechanism reach を
満たさない。

**pure damage/continuity analyzer の C4 shadow への限定継承は可。**
ただし C3 action gate を無効にし、行動置換部を継承しないことが条件である。
根拠は、55,514 callback 全件で unsupported action change、transaction fault、
metric/wrapper exception、structural invalid が 0、raw integrity が PASS であり、
final amendment に固定された静的監査が通過しているためである。この判定は
analyzer 部品の side-effect-free な継承だけを許し、C3 action rule の強さ・到達・
採用を意味しない。

追加 simulation は実行せず、指定された completed outputs だけを読んだ。
source、deck、schedule、runner output、raw result は変更していない。

## 凍結 identity

| 対象 | path / identity | 独立 SHA-256 |
|---|---|---|
| Formal spec | `alakazam_staged_20260729/specs/v4_c3_public_survival_bench0_fix5_formal_execution_spec.md` | `B0E7ED5FE726BFB55E20A535BCD0D58E7BCA550D8C5F7A9D56635015DACCFA4A` |
| Path/retry amendment | `alakazam_staged_20260729/specs/v4_c3_fix5_formal_execution_path_retry_amendment.md` | `7614294084EC942EAD38BC72E5AC4037983F81B63F12290AF61B641DA8C52428` |
| Origin-state amendment | `alakazam_staged_20260729/specs/v4_c3_fix5_collector_origin_state_execution_amendment.md` | `709F7BA89558FD1E12150DE2F6C3296C81C8F4D1ED0679E59F9BEDA28E877A08` |
| Final collector amendment | `alakazam_staged_20260729/specs/v4_c3_fix5_collector_union_final_execution_amendment.md` | `6618E5C8AAC1AF3D51E1AD562F2FB5CCBA94CDEBD01E31178A68D3F0C9A3B991` |
| Baseline adapter | `alakazam_staged_20260729/eval_adapters/alakazam_newdeck_v3_exact_evolution_ko_fix2` | main `426F1BBB71583A691CBF39A07FA8A042CB0AB0600EB43F22F9E4DBD247E5AAEC` |
| Baseline v3 closure | 33 standard closure members | `DC90205DE06AE3E2E41ADC661577096BB02EE5B42AB9F4366FC1A01154745B47` |
| Candidate adapter | `alakazam_staged_20260729/eval_adapters/alakazam_newdeck_v4_public_survival_bench0_fix5` | main `426F1BBB71583A691CBF39A07FA8A042CB0AB0600EB43F22F9E4DBD247E5AAEC` |
| Candidate fix5 closure | 36 standard closure members | `5C1BAD6C505358BFF7550A89F167D3DE19B0D2540C6C54ED85324F961A37E134` |
| Shared 60-card deck | baseline/candidate adapters | `F598F5E578D0440C96DC0492EAECF2E19739B7A23225BE57114A724EF7D0FB94` |
| Damage/continuity analyzer | `planner_public_damage_continuity.py` | `AD14F84C80FC92B95ACB7C585D492910BD46883528CE2F99158AF046EDDAE201` |
| Action wrapper | `planner_public_survival_bench0.py` | `C9E86FFDBD054476E562313808DD08E35E05176F30BE083E1862A370229E3AEC` |
| Final collector | `verification/c3_sidecar_collector.py` | `597D84E8D0913B49AE037D6633B412627DB7CEF52699007F612D9679A7A30F92` |
| Final collector test | `test_v4_c3_sidecar_collector.py` | `FF1ADD6CBE2BACEB8EE37D5508C58B0D0F588088FDBBA2AED99356F1F62AA603` |

Closure は relative path、NUL、uppercase member SHA-256、NUL、byte count、LF
を lexical order で連結して再計算した。両 closure、adapter main、deck、
production member は frozen identity と一致した。

## Paired 700 局の独立再計算

`tools/run_local_battle.py` の `result` は winner player index である。
policy seat 0 の全 105 run では policy が agent A/player 0、seat 1 の全
105 run では policy が agent B/player 1 に置かれていた。したがって
`win = (result == 0)` を seat 0 に、`win = (result == 1)` を seat 1 に
別々に適用した。player-0 win counter を seat 1 に再利用していない。

全 35 `attempt_1` の baseline A、baseline B、candidate summary
2,100 raw rows を直接読み、combined 700 行へ join した。

- expected / actual schedule rows: `700 / 700`
- unique `(opponent, policy_seat, seed)`: `700`
- missing / unexpected / duplicate schedule keys: `0 / 0 / 0`
- selected commands: `210`; nonzero exit: `0`
- raw result invalid、not-started、action error、max-step hit: すべて `0`
- `seed == seed_base + game`: mismatch `0`
- raw summary と combined result/win/steps: mismatch `0/700`
- baseline A/B duplicate control:
  `seed,result,steps,turn,action_errors,hit_max_steps` mismatch `0/700`
- 特に duplicate の per-game result と decision count (`steps`) は
  `700/700` exact match

35 panel の selected raw file 350 個に対する portable manifest
（`relative path NUL SHA NUL bytes LF`、sorted）の SHA-256 は
`A684587DB41B053F83E52A406C94228A75ED7D5F156349E7494068745FC226C9`。

### Aggregate と paired uncertainty

| Policy | W-L | Rate | two-sided Wilson 95% |
|---|---:|---:|---:|
| Baseline | 452-248 | 64.57% | [60.96%, 68.03%] |
| Candidate | 452-248 | 64.57% | [60.96%, 68.03%] |

Paired gain/loss/tie は `0/0/700`、net `0.00pp`、exact McNemar
two-sided `p=1.0`。仕様で従来使用された 50 actual-seed cluster の
one-sided 95% t lower bound は、全 cluster difference が 0 のため
overall、adjacent、Silver のすべて `0.000pp` である。

この退化 interval だけで未知の discordance を 0 と断定しないため、
0 discordances を観測したときの one-sided 95% Clopper-Pearson upper
bound `q_U = 1 - 0.05^(1/n)` と
`candidate-baseline >= -q_U` を使う保守的 paired sensitivity も計算した。

| Scope | Games | Net | Spec seed-cluster lower | Conservative exact paired lower | Gate |
|---|---:|---:|---:|---:|---|
| Overall | 700 | 0.00pp | 0.000pp | -0.427pp | PASS (`>=-1pp`) |
| Adjacent 6 | 600 | 0.00pp | 0.000pp | -0.498pp | PASS (`>=-1pp`) |
| Historical Silver | 100 | 0.00pp | 0.000pp | -2.951pp | PASS (`>=-3pp`) |

lower-bound gate の通過は、positive-delta gate の失敗を覆さない。

### 対面別

各行で baseline と candidate の W-L/rate は同じである。

| Opponent | Baseline | Candidate | Rate | Candidate Wilson 95% | Delta |
|---|---:|---:|---:|---:|---:|
| Marnie | 69-31 | 69-31 | 69% | [59.37%, 77.22%] | 0/100 |
| Cynthia | 73-27 | 73-27 | 73% | [63.57%, 80.73%] | 0/100 |
| Alakazam mirror | 81-19 | 81-19 | 81% | [72.22%, 87.49%] | 0/100 |
| Rocket Mewtwo/Spidops proxy | 38-62 | 38-62 | 38% | [29.10%, 47.79%] | 0/100 |
| Kangaskhan/Crustle | 71-29 | 71-29 | 71% | [61.46%, 78.99%] | 0/100 |
| Historical Silver | 56-44 | 56-44 | 56% | [46.23%, 65.33%] | 0/100 |
| Direct frozen | 64-36 | 64-36 | 64% | [54.24%, 72.73%] | 0/100 |

Adjacent 6 opponents は双方 `396-204 (66.00%)`、delta `0/600`。

### Seat と seed sensitivity

| Split | Baseline | Candidate | Rate | Delta |
|---|---:|---:|---:|---:|
| Seat 0 = policy at A/player 0 | 235-115 | 235-115 | 67.14% | 0/350 |
| Seat 1 = policy at B/player 1 | 217-133 | 217-133 | 62.00% | 0/350 |
| Seed base 202608500 | 96-44 | 96-44 | 68.57% | 0/140 |
| Seed base 202608510 | 81-59 | 81-59 | 57.86% | 0/140 |
| Seed base 202608520 | 94-46 | 94-46 | 67.14% | 0/140 |
| Seed base 202608530 | 90-50 | 90-50 | 64.29% | 0/140 |
| Seed base 202608540 | 91-49 | 91-49 | 65.00% | 0/140 |

差分の seat/seed sensitivity は全 split で 0。一方、絶対 rate は seat 間
`5.14pp`、seed base 間 `10.71pp` の spread がある。
Historical Silver の 20-game blocks は
`15,11,11,10,9` wins、delta はすべて 0、positive block は `0/5`。

### 平均に隠れる絶対 floor

relative regression は game、opponent、opponent-seat、seed-base、
opponent-seed block のどこにもない。しかし同一結果は、baseline の弱点を
そのまま保持したことでもある。

- Rocket proxy は aggregate `38%`、seat 1 は `17/50 = 34%`。
- Rocket の seed blocks は `6,5,12,9,6 / 20`
  (`30%,25%,60%,45%,30%`) で、5 blocks 中 3 blocks が 30% 以下。
  これは overall 64.57% に隠れる recurring severe floor である。
- Historical Silver は seed blocks が `75%,55%,55%,50%,45%` と広く、
  最低 block は 45%。candidate はこの floor を改善していない。

## Metric 90 blocks / 900 games

全 block ledger と全 900 summary rows を再計算した。

| Suite | Blocks / games | Manifest SHA-256 | Ledger SHA-256 | Execution summary SHA-256 |
|---|---:|---|---|---|
| `metrics/formal_v4_c3_public_survival_bench0_fix5_trace_a_retry1` | 30 / 300 | `6C21260BA2D3E1D2BE64246330FD5642A1D2BCDE6930B88270FCAD70DEAF29B2` | `D47166280394D06CA88F9628F7A7B2CA778F3B61DD53CA0F41DABF0984210135` | `F21FA7B6218E3AF44254F771422D8F5687B186843043C994DF1229B8574AE344` |
| `alakazam_staged_20260729/metrics/formal_v4_c3_public_survival_bench0_fix5_trace_b` | 20 / 200 | `157105FD0249DA63C6748E68ED0E4640B5FB0376AFE6EB76FB6630658B8971DC` | `5BBB7C85075B1153C735768761EE31717C23C1E648E09CCAEF16A709B8D72818` | `ABA204D8B31FB06B31531729FD9DB10BDA7528507236A9196F17E9C81292793C` |
| `metrics/formal_v4_c3_public_survival_bench0_fix5_trace_c` | 20 / 200 | `DAE3FB9DE5CDDE024FB3A83368385F2086D78A085A2D7B17FB8ABDB6B1FB4A00` | `AC74EC0934ADA81F684D93D23C8478E041ECB7CE4B9BA5BA099A4C764328DAF3` | `BD2F3C90AD565B2C67231BC8D49948F95D1314ECFA07CD94F718018F44EF432A` |
| `metrics/formal_v4_c3_public_survival_bench0_fix5_megalucario_reach1` | 20 / 200 | `15514F80157DC0CCD59CF489FEAB454CE3A2F8141ADE3C9396A8651520DF17F4` | `A01166BDBB51754FE2DD0F1EBD3C5DFD80EAD429BA0E5AE02B158D73042ADA95` | `B26F55F3E0CDE2CAD6E15385F2826CDA64622ADE802AF3F1BE864EB4EF07E214` |

合計は `90/90` unique block keys、`900/900` unique game keys。
manifest schedule、`.venv-rl` Python、`--engine-seed`、policy-to-player mapping、
adapter/deck/opponent/runner hashes は一致した。nonzero exit、timeout、
partial block、stderr、summary hash/row、not-started、invalid result、
action error、max-step、missing/empty trace、missing/empty sidecar はすべて 0。
不完全な original Shard A は path/retry amendment に従って一切含めていない。

## Collector integrity と mechanism reach

4 accepted suites の 900 raw sidecars を全件走査した。

- sidecar portable input manifest:
  `3FB626031AF16A0F61098DAFC38A7554AEBE9F7C69DC0F0E223DA6F57A3B02E6`
- `CALL_START / CALL_END`: `55,514 / 55,514`
- unique fully-qualified callback keys: `55,514`
- duplicate、cross-source duplicate、unmatched、pairless sidecar: すべて `0`
- path/event identity、`seed=seed_base+game`、schema 5、rule、parent/candidate
  closure mismatch: すべて `0`
- selected/applied mismatch、action identity flag failure、unsupported action
  change: すべて `0`
- transaction fault、metric/wrapper exception、structural invalid、
  decision/state-evidence conflict: すべて `0`

raw から final collector を読み取り専用で再計算すると、55,514 rows の
canonical JSONL SHA-256 は
`D191973FD7967F1E48E2773C8BC51FE1834E0D51122247E9C88F4619784933BE`、
summary SHA-256 は
`95155FE090A6CFCF8A5DD3FBA79505E10A368BD051F8A02AC3B3B2D191C15E97`
となり、保存済み union outputs と byte-exact に一致した。

しかし全 55,514 callbacks の transaction stage は `NO_ACTION`。
guard は `SAFE_NO_ACTION=51,985`、`UNSUPPORTED_NO_ACTION=3,527`、
`HIGH_COUNTERMEASURE_COST_NO_ACTION=2` で、許可された二つの action guard は
一度も発火していない。

| Reach gate | Required | Raw recomputation | Result |
|---|---:|---:|---|
| Supported threat/action states | >=30 | 0 | FAIL |
| Promotion/removal contexts in supported origin states | >=10 | 0 | FAIL |
| Continuity classes in supported origin states | all 4 | 0/4 | FAIL |
| Seats | 2 | 0 | FAIL |
| Opponents / non-mirror opponents | >=3 / >=2 | 0 / 0 | FAIL |
| Floor and cap action guards | both | neither | FAIL |
| Unsupported action changes | 0 | 0 | PASS |
| Integrity faults | 0 | 0 | PASS |

callback-level analyzer rowsには continuity
`REPEATABLE_READY=9`、`RECHARGE_REQUIRED=8`、`NO_READY_ATTACK=9`、
`UNKNOWN=0` と promotion/removal context 2,513 件がある。しかしこれらは
すべて `NO_ACTION` callback であり、同一 origin decision の許可 guard に
属さない。final collector semantics に従い、supported reach を水増しする
証拠には使用しない。collector integrity は `PASS`、reach は
`INSUFFICIENT_EVIDENCE` であり、raw evaluation 自体が invalid なのではない。

## Acceptance gates

| Gate | Recomputed result | Pass/fail |
|---|---:|---|
| Candidate wins `>=452/700` | `452/700` | PASS（境界） |
| Overall paired delta positive | `0/700` | **FAIL** |
| Historical Silver `>=+3/100` | `0/100` | **FAIL** |
| Silver both seats nonnegative | `0/50`, `0/50` | PASS |
| Silver positive 20-game blocks `>=2/5` | `0/5` | **FAIL** |
| Adjacent six `>=-2/600` | `0/600` | PASS |
| Every opponent `>=-2/100` | 全 7 対面 `0/100` | PASS |
| Every opponent-seat `>=-2/50` | 全 14 cell `0/50` | PASS |
| Overall / adjacent paired lower `>=-1pp` | exact sensitivity `-0.427/-0.498pp` | PASS |
| Silver paired lower `>=-3pp` | exact sensitivity `-2.951pp` | PASS |
| Mechanism reach | supported states `0` | **FAIL / INSUFFICIENT** |
| Raw integrity | all checked fault counts `0` | PASS |

全共通 gate ではないため、recommendation は **REJECT C3 action change**。
positive aggregate delta だけで強さを推定しておらず、そもそも positive delta
は存在しない。

## 使用した raw/report hashes

| Input | SHA-256 |
|---|---|
| `combined_paired_results.csv` | `50AC17BD9DABE801D22D86F84765536E2CCC58EA535F528DAF6FE43F4262B851` |
| `validation_report.json` | `860B05DEBA4108F7F94DE4C9C80680FF0B38F0979BCDC0B14C72B47FA1D3CB33` |
| `root_combined_runner_report.json` | `EDDDD58B29B7531C5EF09B7D9E638D3C18BEE62CC734E57AB6016A9306B1EEB5` |
| `root_independent_paired_audit.json` | `99D376DD46257B5A5A2BC15A1F9220EA6AE57FB0BAC7BA838D330A82015A1812` |
| `root_independent_metric_audit.json` | `3F0AC1FB99E8A8E813CD611EB782F574039D7C3BC461B9B527DD2C46CA0F5F89` |
| `combination_provenance.json` | `94DF59CAF37F7A83A006928841DEA0874AA39564F1BC90CEAFEB574F7785CE34` |
| `combined_manifest.jsonl` | `807471E233B97D0CE2CBC659F43FEDDA1AAE65635ACEA97B03F73542ED270D27` |
| Union `c3_callback_audit_rows.jsonl` | `D191973FD7967F1E48E2773C8BC51FE1834E0D51122247E9C88F4619784933BE` |
| Union `c3_mechanical_summary.json` | `95155FE090A6CFCF8A5DD3FBA79505E10A368BD051F8A02AC3B3B2D191C15E97` |

既存 runner/root audit の submission-critical counts と本再計算の不一致は 0。
それらの prose や aggregate を証拠として代用せず、raw rows から先に再計算した。

## 再現計算と仮定

1. Windows の repository Python command はすべて
   `.venv-rl/Scripts/python.exe` を使用した。
2. paired key は `(seed_base, opponent, seat, game, seed)`、
   comparison key は `(opponent, seat, seed)`。expected set を spec の
   7 opponents × 2 seats × 5 seed bases × 10 games から構成した。
3. policy win は `int(result == seat)`。gain/loss は同じ row 内の
   candidate/baseline win flag の差から計算した。
4. Wilson は標準 two-sided 95% score interval (`z=1.95996398454`)。
   spec lower bound は 50 actual-seed cluster の paired difference に対する
   one-sided 95% t bound。0-discordance sensitivity は上記 exact 式。
5. metric expected set は各 supplied manifest と formal/path amendment の
   opponent × seat × seed-base × game から構成し、ledger、summary、trace、
   sidecar を全件 join した。
6. collector callback key は
   `(version, opponent, seat, seed_base, seed, game, callback_ordinal)`。
   reach は final amendment の live origin stages
   `PROPOSED/ARMED/DUPLICATE_REBIND` だけを使い、`NO_ACTION` context は
   reach に数えなかった。
7. supplied exact paths を正式化する path/retry amendment を binding
   provenance として使用し、incomplete original Shard A と Shard B の
   auxiliary `file_hashes.csv` は除外した。
8. pure analyzer の静的監査は final amendment に固定された
   focused `14/14`、candidate regression `254/254`、`py_compile` exit 0
   を supplied provenance として扱った。本数値監査では tests を再実行せず、
   root がその静的証拠を直接再確認することを前提とする。

本 Markdown の通常の file SHA-256 は、自己参照で本文を変えないよう、
最終書き込み後の親 handoff に記録する。
