# v4 C1 ポフィン fix3 固定paired評価仕様

## 状態

この仕様は、C1候補の固定fixture・回帰・closureをrootが再確認し、B0の候補非参照絶対基準を先に固定した後に作成した。

```text
ABS_FLOOR = 452 / 700
```

B0 root verification:

`alakazam_staged_20260729/reports/v4_b0_fix2_absolute_baseline_root_verification.md`

SHA-256:

`F61586CE0B656E7E8C5EA3795F811CF171A5BEAF76945397CDC0C0339D07CEFA`

## 方策

Baseline:

- path:
  `alakazam_staged_20260729/versions/alakazam_newdeck_v3_exact_evolution_ko_fix2`
- closure、33 files:
  `DC90205DE06AE3E2E41ADC661577096BB02EE5B42AB9F4366FC1A01154745B47`
- planner:
  `255FD9E1303E8E6DFB286952023A7F086CD233B4E5D5030EDBE06313A40697B7`
- adapter:
  `alakazam_staged_20260729/eval_adapters/alakazam_newdeck_v3_exact_evolution_ko_fix2`
- adapter main:
  `426F1BBB71583A691CBF39A07FA8A042CB0AB0600EB43F22F9E4DBD247E5AAEC`

Candidate:

- path:
  `alakazam_staged_20260729/versions/alakazam_newdeck_v4_poffin_role_cardinality_fix3`
- closure、33 files:
  `DE7FCD20A1B3362E845B8573DC6178E32B13F250EA8AC8619B7BA0AA704D271D`
- planner:
  `A23BF536227465661FD98087299D2672400E918DB9B168DFEB2B9C3CF60A4D9E`
- focused test:
  `FE9B93E73E9D0250A482DCBB66226C8F5E30883054849B8CBCEC212C07556874`
- implementation receipt:
  `07BBE5CBE6233AD46B4DA089891D69293CCFAE5956B8006B2F17089F4A7A9882`
- adapter:
  `alakazam_staged_20260729/eval_adapters/alakazam_newdeck_v4_poffin_role_cardinality_fix3`
- adapter main:
  `426F1BBB71583A691CBF39A07FA8A042CB0AB0600EB43F22F9E4DBD247E5AAEC`

Common deck、60 rows:

`F598F5E578D0440C96DC0492EAECF2E19739B7A23225BE57114A724EF7D0FB94`

## 仕様

- umbrella contract:
  `B0657D0118847F2DDF7680E6D75AE28F2DF6CF42EE338B6355ADDC731F454783`
- C1 immutable behavior:
  `F5301C098EC76C306CD1392078EEB78B6B1F14530C60103A662564714FA65883`
- static-review amendment:
  `592963EDE071F6B7DC023EA952F4A22D8D2E5FD45B5EDB51BA4DF43E5D8DEE11`

## checked runtime

- Python:
  `.venv-rl/Scripts/python.exe`
- engine:
  `analysis_outputs/cynthia_v9_vs_v11_poffin_role_selection_20260713/seeded_engine`
- engine tree:
  `466638706BD5C6915E25D1B3CB9E3D966390FBC263F4ED3153108E29C0194FFF`
- paired runner:
  `tools/run_seeded_paired_suite.py`
- paired runner SHA-256:
  `5EC25C98F2777FF61DE2DBD0A03A08519A7FEA4B2B4C510B5B8895BC2000E000`
- battle runner SHA-256:
  `E1ABA0151CDAEE425B858511AA760CE5C5647D555DDEFBD69D7319C29C5B773B`
- combiner:
  `tools/combine_staged_panel_results.py`
- combiner SHA-256:
  `CABFB6ECB500EF1395B05EDB5A9775193B8A13578E3EDF35C0CED04214175C77`

## 固定schedule

- opponents: 7
- policy seats: 0、1
- seed bases:
  `202608500, 202608510, 202608520, 202608530, 202608540`
- games per seat per panel: 10
- actual seed:
  `seed_base + game_index`
- max steps: 1000
- candidate rows: 700
- baseline A duplicate-control rows: 700
- baseline B rows: 700

Opponents:

```text
marnie
  meta_agents/marnie_sota_live_85033057_simple
cynthia
  meta_agents/cynthia_garchomp_nasuo445_v80_legal_complete_role_cycle
alakazam_mirror
  meta_agents/alakazam_oselcoun_live_85035844_simple
rocket_mewtwo_spidops_proxy
  meta_agents/rocket_mewtwo_spidops_kashiwashira_20260703_simple
kangaskhan_crustle
  meta_agents/kangaskhan_crustle_mpgaming_v13_backupkang_two_growline
historical_silver
  analysis_outputs/reference_agents/historical_silver_archaludon_54495224
direct_frozen
  alakazam_staged_20260729/eval_adapters/alakazam_800_frozen
```

## panel output

```text
alakazam_staged_20260729/evaluations/v4_c1_poffin_fix3_panels/
  <seed_base>_<opponent>/attempt_1/
```

既存outputを上書きしない。失敗または不完全なpanelだけ、rootの確認後に `attempt_2`、`attempt_3` を新規作成する。

Combined output:

`alakazam_staged_20260729/evaluations/v4_c1_poffin_fix3_combined`

## 実行分割

Runner A、12 panels:

```text
202608500 × all 7 opponents
202608530 × marnie, cynthia, alakazam_mirror,
            rocket_mewtwo_spidops_proxy, kangaskhan_crustle
```

Runner B、12 panels:

```text
202608510 × all 7 opponents
202608530 × historical_silver, direct_frozen
202608540 × marnie, cynthia, alakazam_mirror
```

Runner C、11 panels:

```text
202608520 × all 7 opponents
202608540 × rocket_mewtwo_spidops_proxy, kangaskhan_crustle,
            historical_silver, direct_frozen
```

各runnerはchecked runnerのraw出力path、command、exit codeだけを返し、勝率・差・採否を解釈しない。

## 完全性条件

- 35 panel
- 35 first-valid attempts
- 700 unique `(opponent, policy_seat, seed)` / version
- baseline A/Bのresult、steps、turn、action errors、max-step、context countsが全件一致
- baseline/candidate schedule完全一致
- nonzero exit 0
- timeout 0
- unstarted 0
- action errors 0
- max-step 0
- invalid result 0
- missing row 0
- duplicate row 0
- raw panelとcombinedの差0

## 行動変更候補の採用条件

候補は次をすべて満たす。

- candidate wins `>= 452`
- overall paired delta が正
- Historical Silver `>= +3/100`
- Historical Silver両seatが非負
- Historical Silverの20-game seed block 5個中2個以上が正
- 他6 opponents合計 `>= -2/600`
- 各opponent `>= -2/100`
- 各opponent-seat `>= -2/50`
- one-sided 95% paired lower bound:
  - overall、adjacent `>= -1pp`
  - Historical Silver `>= -3pp`
- C1の変更機構が実際に到達し、意図した後続を完了
- すべての完全性条件を通過

## C1 trace到達条件

paired結果とは別にchecked metric suiteを実行し、次を満たす。

- exact Poffin child context 30件以上
- 両seat
- 3 opponents以上、非ミラー2以上
- proposed cardinality 0、1、2を各5件以上
- changed/vetoed selection 10件以上
- `MAIN_RERANK_UNCERTIFIED_PARENT_PRESERVED` 0件
- `HIDDEN_ZONE_TARGET_WHIFF` を失敗ではなく合法任意0枚として区別
- transaction fault、stale abort、metric exception 0

到達不足は `INSUFFICIENT_EVIDENCE` であり、採用ではない。
