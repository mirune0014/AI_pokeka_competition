# Comparison B runtime-certified immutable specification

## 目的

同一60枚を使う`alakazam_newdeck_v0_port`と
`alakazam_newdeck_v1_package_runtime_certified`を、同一opponent、seed、
seatで比較する。

差分は9枠パッケージへの適応ルールと、そのルールが開始した処理を
最後まで所有するための実行時修正だけである。

一般的な連続攻撃最適化、v2ルール、対面名・seed・replayを条件とする
分岐は含めない。

旧`comparison_b_v0_vs_v1_compliance_immutable_spec.md`とその出力は、
428件の不可逆PLAY後transaction abortが判明したため
`SUPERSEDED_RUNTIME_TRANSACTION_ABORT`とする。

## 凍結入力

- Repository commit at branch start:
  `54f09edb2b3f6dd2def7c2c49efde16dfeda97c9`
- Runtime-completion contract SHA-256:
  `304F9945BE90D2716083B39137AD83521FE6EB2B3FBA031ADA727B0B6677F3FE`
- Runtime fixture amendment SHA-256:
  `60FB4284E1854C63AA6CB7A8CF6EBDB26F2FCD3F17D3055B90A41E305EAD26B3`
- Runtime-certified provenance manifest SHA-256:
  `EAE5D0B1960588B92982B7AF098703E191A4A062475E1BA88ADFF8B7C0328D13`
- Engine:
  `analysis_outputs/cynthia_v9_vs_v11_poffin_role_selection_20260713/seeded_engine`
- Engine source/runtime tree SHA-256:
  `466638706BD5C6915E25D1B3CB9E3D966390FBC263F4ED3153108E29C0194FFF`
- Engine tree file count: `11`
- Python executable:
  `C:\Users\amuam\project\AI_pokeka_competition\.venv-rl\Scripts\python.exe`
- Python version:
  `3.11.6 (tags/v3.11.6:8b6ee5b, Oct  2 2023, 14:57:12) [MSC v.1935 64 bit (AMD64)]`
- Paired runner SHA-256:
  `5EC25C98F2777FF61DE2DBD0A03A08519A7FEA4B2B4C510B5B8895BC2000E000`
- Battle runner SHA-256:
  `E1ABA0151CDAEE425B858511AA760CE5C5647D555DDEFBD69D7319C29C5B773B`
- Combiner SHA-256:
  `CABFB6ECB500EF1395B05EDB5A9775193B8A13578E3EDF35C0CED04214175C77`
- Metric runner SHA-256:
  `BCC98229B23C86FC5EB248D3F1E254337008FF4E85BD85224B3B3D6F570F1EEA`
- Metric summarizer SHA-256:
  `1679DCFFEF79D72A69A8CD49B6EA9A056A88FE120F75639B77740FA65EFF8A03`
- Baseline policy closure SHA-256:
  `D9ADBC03054AB1D2FFD1E1955D734DB1D14DA74C9D1088249A271F98EBCECD46`
- Candidate policy closure SHA-256:
  `B8E4F9C50B41AE9B62FA726E7BD124E44E0A36252E80C0182576BFEB9EE2BFEF`
- Candidate planner SHA-256:
  `73B1E2F1DF63B621C837253590C86841F9FC960BF0751850FD95419EE13AB077`
- Baseline and candidate normalized deck hash:
  `4414e8995e50c7a00d4b6aa7d9229f63c1dff5261643ec7cd86c4e329113ed69`
- Baseline and candidate raw deck SHA-256:
  `F598F5E578D0440C96DC0492EAECF2E19739B7A23225BE57114A724EF7D0FB94`
- Baseline adapter:
  `alakazam_staged_20260729/eval_adapters/alakazam_newdeck_v0_port`
- Candidate adapter:
  `alakazam_staged_20260729/eval_adapters/alakazam_newdeck_v1_package_runtime_certified`
- Both adapter `main.py` SHA-256:
  `C38C357D28CB4E8401815220E385B5542B385B7AB2984719E30DBAF9503CC2AC`

Engine source/runtime treeは、engine root以下のファイルから
`__pycache__`配下と`.pyc`を除外し、Windows `Path`順で並べる。

各行を
`relative_path.as_posix() + "|" + uppercase_file_sha256 + LF`
としてASCII連結し、その852 bytesのSHA-256を取る。

Policy closureは、top-level Pythonのうちテストを除くファイル、
`runtime/main.py`、`deck.csv`の33ファイルを対象とする。

相対pathを辞書順に並べ、
`path + NUL + uppercase_file_sha256 + NUL + size + LF`
をUTF-8連結してSHA-256を取る。

## 対戦相手

| label | path |
| --- | --- |
| `marnie` | `meta_agents/marnie_sota_live_85033057_simple` |
| `cynthia` | `meta_agents/cynthia_garchomp_nasuo445_v80_legal_complete_role_cycle` |
| `alakazam_mirror` | `meta_agents/alakazam_oselcoun_live_85035844_simple` |
| `rocket_mewtwo_spidops_proxy` | `meta_agents/rocket_mewtwo_spidops_kashiwashira_20260703_simple` |
| `kangaskhan_crustle` | `meta_agents/kangaskhan_crustle_mpgaming_v13_backupkang_two_growline` |
| `historical_silver` | `analysis_outputs/reference_agents/historical_silver_archaludon_54495224` |
| `direct_frozen` | `alakazam_staged_20260729/eval_adapters/alakazam_800_frozen` |

Rocket対面はMewtwo／Spidops agentによるproxyであり、公開7日間で観測した
Mewtwo ex／Ariados完全一致対面ではない。

## 固定schedule

- Seed bases:
  `202608500`, `202608510`, `202608520`, `202608530`, `202608540`
- 各seed base・opponent・seatのgames: `10`
- Seats: `0`, `1`
- Max steps: `1000`
- 合計: 7 matchups × 50 seeds × 2 seats = 700 paired rows
- Expected manifest rows: `210`
- Expected child summaries: `2100`
- Expected paired schedule SHA-256:
  `619BA954971C33FDC698810A58DF1E2C0786FFF16B6A0CCD2715DC33B04FD076`
- Expected manifest schedule SHA-256:
  `9277E7463E1372FCE8095BD86A79FA35EC616177034CBEA7894BCBC5419AAAB3`

## 出力先

- Smoke metric root:
  `alakazam_staged_20260729/metrics/smoke_v1_runtime_certified_seed202608500`
- Panel root:
  `alakazam_staged_20260729/evaluations/comparison_b_runtime_certified_panels`
- Combined root:
  `alakazam_staged_20260729/evaluations/comparison_b_runtime_certified_combined`
- Formal metric root:
  `alakazam_staged_20260729/metrics/formal_v1_runtime_certified_7opp_50seed`
- Formal metric summary:
  `alakazam_staged_20260729/metrics/formal_v1_runtime_certified_7opp_50seed_summary`
- Comparison name:
  `comparison_b_v0_vs_v1_runtime_certified`

1 panelは1 opponent・1 seed base・両seat・10 gamesとする。

attempt directoryはfreshとし、最初のvalid attempt以降を作らない。

失敗attemptは削除せずprovenanceへ残す。

## 実行前gate

- immutable sourceの106件とcandidateの120件がすべて成功する。
- candidate条件を持つ9関数のASTがsourceと一致する。
- `agent()`内のcandidate呼出順がsourceと一致する。
- source candidate、過去v2、既存評価出力を変更しない。
- candidateとadapterのdeckは60枚でbyte-identicalである。
- smokeの全callbackで`removed_rule_hit_status=KNOWN`である。
- smokeで発火したBoss、Hammer、Lana、Xerosic、Alakazamのtransactionは
  完了し、`V1_TRANSACTION_ABORT`と
  `V1_IRREVERSIBLE_ABORT_FAULT`が0である。
- smokeのinvalid action、exception、timeout、max-step、
  first-legal fallbackが0である。

## 有効な最終結果

- 700 unique `(opponent, seat, seed)`。
- schedule完全一致。
- child exit code 0。
- action error、max-step、timeout、unstarted、invalid winnerがすべて0。
- baseline duplicate control A/Bの
  `seed,result,steps,turn,action_errors,hit_max_steps`差が0。
- formal metric 700行とpaired rowsのschedule、result、stepsが完全一致。
- 全candidate callbackで`removed_rule_hit_status=KNOWN`。
- 発火した全v1 transactionについて、
  `transaction starts = transaction completes`。
- `V1_TRANSACTION_ABORT=0`。
- `V1_IRREVERSIBLE_ABORT_FAULT=0`。
- candidate-owned child callbackでv0 delegateを呼ばない。
- generic fallbackとfirst-legal fallbackが0。

いずれかを満たさない場合、勝率が改善していてもComparison BはFAILとし、
v2を重ねない。

## 判定時の集計

overallだけでなく、対面別、seat別、seed-base別、paired gain/loss、
discordant exact p値を併記する。

first attack、attack gap、post-KO continuity、second line、攻撃時手札、
Powerful Hand counter、追加カード露出・使用、fallback、decision timeも
併記する。

post-KO等は方策ごとに分母が変わるため、単純差を同一eventのpaired因果効果と
解釈しない。
