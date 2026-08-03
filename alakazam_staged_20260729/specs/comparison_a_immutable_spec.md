# Comparison A immutable specification

## 目的

Comparison Aは、`alakazam_800_frozen`と`alakazam_newdeck_v0_port`を同一opponent、seed、seatで比較する。

これは既存方策下での実運用上のデッキ差と移植健全性を測る比較であり、純粋なデッキ効果とは解釈しない。

## 凍結入力

- Repository commit: `54f09edb2b3f6dd2def7c2c49efde16dfeda97c9`。
- Engine: `analysis_outputs/cynthia_v9_vs_v11_poffin_role_selection_20260713/seeded_engine`。
- Engine canonical tree SHA-256: `586B92FDEA892CBB147D4C6A113575CCD98E4FC90528BABB6E8F7294D0CBEBF2`。
- Paired runner SHA-256: `5EC25C98F2777FF61DE2DBD0A03A08519A7FEA4B2B4C510B5B8895BC2000E000`。
- Battle runner SHA-256: `E1ABA0151CDAEE425B858511AA760CE5C5647D555DDEFBD69D7319C29C5B773B`。
- Deterministic audit SHA-256: `0E26EAB255E2D0E75598895D5278847D8AD877EDD9C4F09C308B54413EBC3BD6`。
- Baseline policy closure SHA-256: `2CB86DF243271B20045D8FDF526F9874F9880AD354B7928DF62A86E428111BD1`。
- Candidate policy closure SHA-256: `D9ADBC03054AB1D2FFD1E1955D734DB1D14DA74C9D1088249A271F98EBCECD46`。
- Baseline normalized deck hash: `f2e179fb82cb91504ccd207d707ca5e7be8afc7228df26a7b287c6205064507c`。
- Candidate normalized deck hash: `4414e8995e50c7a00d4b6aa7d9229f63c1dff5261643ec7cd86c4e329113ed69`。
- Baseline adapter: `alakazam_staged_20260729/eval_adapters/alakazam_800_frozen`。
- Candidate adapter: `alakazam_staged_20260729/eval_adapters/alakazam_newdeck_v0_port`。
- Adapter `main.py` SHA-256: `827AED76A69D8D6CF81C15A88C3C77C58F272892BD1C1D3415714DAA05C70745`。

Policy closureは、凍結版のtop-level Python 30ファイル、`runtime/main.py`、`deck.csv`の同一相対パス集合について、`path + NUL + uppercase file SHA-256 + NUL + size + LF`を辞書順に連結してSHA-256を取る。

v0固有のテスト、receipt、verification出力はclosureへ含めない。

## 対戦相手

| label | path | main.py SHA-256 | deck.csv SHA-256 |
|---|---|---|---|
| `marnie` | `meta_agents/marnie_sota_live_85033057_simple` | `B65E61837F19E08BC75D016BFDCF3F31CCAC44957592145454020B72777631BA` | `D875568AA29003A376F0AA23693252635232B0B5B9B53883030A8613E827864E` |
| `cynthia` | `meta_agents/cynthia_garchomp_nasuo445_v80_legal_complete_role_cycle` | `730E62AA749F6CC57ADA91F4E55D6B364DDAE2B12A303FA559453B3A5FE3E937` | `606B44F7D6181C57C6CCDD7EE493C72BAF39E684B264886BC01631DBEE8D349C` |
| `alakazam_mirror` | `meta_agents/alakazam_oselcoun_live_85035844_simple` | `9BD4FDBCCBD43786F689232B36D01A107BE16B4423EB91966DC964846031A2DC` | `33F38523C965D5DD57EB806B51B4706FEA476E4BFA96A1F314860F6413949B94` |
| `rocket_mewtwo_spidops_proxy` | `meta_agents/rocket_mewtwo_spidops_kashiwashira_20260703_simple` | `ECD6487B92441D2DC1ED6AA86376D0DCFB54FD0ACEEBBE4C28571FB9C0004D4B` | `E0BD6B4438A699B58D94375989147FC0BD81E5634512CEB261BE6D1D41F51EFA` |
| `kangaskhan_crustle` | `meta_agents/kangaskhan_crustle_mpgaming_v13_backupkang_two_growline` | `71250880337D6CDA1919BF4914DE32009D1267C84F6AED3496A690BE0C8F8F95` | `9FCDEEA4F2E741489261EFCFBC19DA81D88DE9079ED01C076EA7F361F07E993E` |
| `historical_silver` | `analysis_outputs/reference_agents/historical_silver_archaludon_54495224` | `F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E` | `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A` |
| `direct_frozen` | `alakazam_staged_20260729/eval_adapters/alakazam_800_frozen` | `827AED76A69D8D6CF81C15A88C3C77C58F272892BD1C1D3415714DAA05C70745` | `A7B6C7972915D09F6314C42633AA89D82B55DDF0A7199F7138E681FA52516529` |

Rocket対面は利用可能なMewtwo/Spidops agentによるrough proxyであり、ワナイダーを含む完全一致代理ではない。

## 固定日程

- Seed bases: `202608500`, `202608510`, `202608520`, `202608530`, `202608540`。
- 各seed base、opponent、seatのgames: `10`。
- 実seed集合: `202608500..202608549`。
- Seats: `0`, `1`。
- Max steps: `1000`。
- Matchup当たり: 50 seeds × 2 seats = 100 paired rows。
- 全体: 7 matchups × 50 seeds × 2 seats = 700 paired rows。
- Runner child invocations: 5 seed bases × 7 matchups × 2 seats × 3 roles = 210。
- 実行ゲーム総数: baseline 700、duplicate baseline 700、candidate 700。

## 出力契約

出力先は`alakazam_staged_20260729/evaluations/comparison_a_50x2`とする。

checked runnerが`manifest.jsonl`、`paired_results.csv`、`cell_summary.csv`、`report.json`を生成する。

その後、checked auditが`numerical_audit.json`を生成する。

`paired_results.csv`は700行で、`(opponent, seat, seed)`が一意でなければならない。

baselineとcandidateは完全に同じ`(opponent, seat, seed)`集合を持たなければならない。

`manifest.jsonl`は210行で、全child processのexit codeが0でなければならない。

`report.json.valid`はtrue、duplicate mismatchは0、action errorとmax-step hitは0でなければならない。

timeout専用列はchecked runnerに存在しないため、nonzero exit、manifest runtime、child summary欠落をtimeoutまたは実行失敗の代理証拠として別記する。

## 比較Aの判定

比較Aの勝率は、純粋なデッキ効果と呼ばない。

v1へ進む必要条件は、invalid action、uncaught exception、timeout、max-step hitがすべて0であること、新規カードが未処理fallbackへ流れないこと、保存済み共有方策の判断差が0であることである。

勝率、paired delta、対面別、seat別の値は併記するが、単一勝率閾値だけでv0を失格にしない。

境界的な結果は、後続版を含む比較で主要対面200 seeds以上へ拡張する候補として記録する。
