# Comparison B compliance immutable specification

## 目的

Comparison Bは、同一60枚を使う`alakazam_newdeck_v0_port`と
`alakazam_newdeck_v1_package_compliance`を、同一opponent、seed、seatで比較する。

差分は9枠パッケージへの適応ルールだけであり、一般的な連続攻撃最適化、
v2ルール、対面名・seed・replayを条件とする分岐は含めない。

旧`comparison_b_v0_vs_v1_immutable_spec.md`と旧出力は、
適合監査前の暫定v1を評価した履歴として保持し、本比較へ混ぜない。

## 凍結入力

- Repository commit at branch start:
  `54f09edb2b3f6dd2def7c2c49efde16dfeda97c9`
- Engine:
  `analysis_outputs/cynthia_v9_vs_v11_poffin_role_selection_20260713/seeded_engine`
- Engine canonical tree SHA-256:
  `586B92FDEA892CBB147D4C6A113575CCD98E4FC90528BABB6E8F7294D0CBEBF2`
- Paired runner SHA-256:
  `5EC25C98F2777FF61DE2DBD0A03A08519A7FEA4B2B4C510B5B8895BC2000E000`
- Battle runner SHA-256:
  `E1ABA0151CDAEE425B858511AA760CE5C5647D555DDEFBD69D7319C29C5B773B`
- Combiner SHA-256:
  `CABFB6ECB500EF1395B05EDB5A9775193B8A13578E3EDF35C0CED04214175C77`
- Deterministic audit SHA-256:
  `0E26EAB255E2D0E75598895D5278847D8AD877EDD9C4F09C308B54413EBC3BD6`
- Baseline policy closure SHA-256:
  `D9ADBC03054AB1D2FFD1E1955D734DB1D14DA74C9D1088249A271F98EBCECD46`
- Candidate policy closure SHA-256:
  `89F8315A4B0A8B25D8CAAF12DBBB88012DD9C5AC278E1D8455DDD0298ECDF69C`
- Baseline and candidate normalized deck hash:
  `4414e8995e50c7a00d4b6aa7d9229f63c1dff5261643ec7cd86c4e329113ed69`
- Baseline and candidate raw deck SHA-256:
  `F598F5E578D0440C96DC0492EAECF2E19739B7A23225BE57114A724EF7D0FB94`
- Baseline adapter:
  `alakazam_staged_20260729/eval_adapters/alakazam_newdeck_v0_port`
- Candidate adapter:
  `alakazam_staged_20260729/eval_adapters/alakazam_newdeck_v1_package_compliance`
- Both adapter `main.py` SHA-256:
  `C38C357D28CB4E8401815220E385B5542B385B7AB2984719E30DBAF9503CC2AC`

Policy closureは、top-level Pythonのうちテストを除くファイル、
`runtime/main.py`、`deck.csv`を対象とする。
相対pathを辞書順に並べ、
`path + NUL + uppercase file SHA-256 + NUL + size + LF`
を連結してSHA-256を取る。

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

`direct_frozen` adapter `main.py` SHA-256は
`B99DE98C53E777332B5F21036E1F634A2BBD9FD1BD22C3049F9467A953F1E8A2`、
deck SHA-256は
`A7B6C7972915D09F6314C42633AA89D82B55DDF0A7199F7138E681FA52516529`
である。

Rocket対面はMewtwo/Spidops agentによるproxyであり、
今回観測されたMewtwo ex/Ariados完全一致対面ではない。

## 固定schedule

- Seed bases:
  `202608500`, `202608510`, `202608520`, `202608530`, `202608540`
- 各seed base・opponent・seatのgames: `10`
- Seats: `0`, `1`
- Max steps: `1000`
- 合計: 7 matchups × 50 seeds × 2 seats = 700 paired rows
- Manifest: 210 rows
- Child summaries: 2100 rows
- Expected paired schedule SHA-256:
  `619BA954971C33FDC698810A58DF1E2C0786FFF16B6A0CCD2715DC33B04FD076`
- Expected manifest schedule SHA-256:
  `9277E7463E1372FCE8095BD86A79FA35EC616177034CBEA7894BCBC5419AAAB3`

## 実行と出力

- Panel root:
  `alakazam_staged_20260729/evaluations/comparison_b_compliance_panels`
- Combined root:
  `alakazam_staged_20260729/evaluations/comparison_b_compliance_combined`
- Comparison name:
  `comparison_b_v0_vs_v1_compliance`
- 1 panelは1 opponent・1 seed base・両seat・10 gamesである。
- attempt directoryはfreshとし、最初のvalid attempt以降を作らない。
- 最大3 attemptsとし、失敗attemptは削除せずprovenanceへ残す。
- 実行ledger:
  `alakazam_staged_20260729/evaluations/comparison_b_compliance_panels/execution_ledger.jsonl`

有効な最終結果は、700 unique `(opponent, seat, seed)`、
schedule完全一致、全child exit 0、action error 0、max-step 0、
duplicate mismatch 0を満たさなければならない。

Comparison Bではv0も再実行し、旧Comparison Aや旧Comparison Bの勝敗行を
baselineとして流用しない。

## 判定に必要な安全条件

- invalid action、uncaught exception、timeout、max-step、
  first-legal fallbackがすべて0である。
- 同一状態でv1専用ルールが非発火なら、
  v0のaction、Reason Code、transaction、fallbackを保存する。
- 追加カードがgeneric未処理fallbackへ流れない。
- 削除カードを前提にする自分側の旧ルールが発火しない。
- Boss SWITCH callbackで相手Activeの5状態が解除され、
  child promptが凍結したenvelopeに一致する。

有効性はoverallだけでなく、対面別、seat別、paired gain/loss、
追加9枠の発火・成功・abort、first attack、attack gap、
post-KO continuity、hand sizeを併記する。

主要対面に説明不能な大幅悪化があれば、v2へ進めない。
