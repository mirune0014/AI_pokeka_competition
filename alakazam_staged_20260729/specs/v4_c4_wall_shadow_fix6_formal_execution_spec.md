# C4 wall-shadow FIX6 formal execution specification

Date: 2026-07-30

This file freezes the only authorized formal comparison and shadow-log
schedule for C4. C4 is action-identical to C2. The formal runs may establish
integrity, reach, and natural-agreement evidence; they may not by themselves
authorize an action-changing wall rule.

## Frozen policies

- C2 action baseline:
  `eval_adapters/alakazam_newdeck_v4_next_attacker_distance_shadow_fix4b`
- C2 adapter `main.py`:
  `EAF8763BAE815637DE07C73D039BD1EF54BD8F04B17F6D74C97E73FAE7C7B4C5`
- C2 standard policy closure:
  `29084BC13CB74236ABE557B57A9E633A8F9E88FA83FF22D131C835293E987157`
- C4 candidate:
  `versions/alakazam_newdeck_v4_wall_shadow_fix6`
- C4 evaluation adapter:
  `eval_adapters/alakazam_newdeck_v4_wall_shadow_fix6`
- C4 candidate policy closure:
  `FA46897E4762CB1B55C9DED36EC3A06CA9CF4F9FE7C4233BE8414CC25D86DF4E`
- C4 production `main.py`:
  `09E6406CEDC6939A38FCE86524814171D5E7FFF7197D1FAC4CF3C776EBC0ABA9`
- C4 planner:
  `772ADF9A37DB572FA0CF1B219A387EC1063CD6FD10CD5268A6DBDC29E9652D75`
- C4 collector:
  `770EA508AF3CCFEC549C1C543EB8D04041553236B11C6D5C3CBBA8FF30344BEE`
- Both evaluation decks:
  `F598F5E578D0440C96DC0492EAECF2E19739B7A23225BE57114A724EF7D0FB94`

The C4 wrapper must return the exact C2 Python action object on every callback.
Any value, type, order, object-identity, wrapper-exception, metric-exception, or
`CANDIDATE_APPLIED` fault invalidates the comparison.

## Checked runtime

- Python:
  `.venv-rl/Scripts/python.exe`
- Engine:
  `analysis_outputs/cynthia_v9_vs_v11_poffin_role_selection_20260713/seeded_engine`
- `run_seeded_paired_suite.py`:
  `5EC25C98F2777FF61DE2DBD0A03A08519A7FEA4B2B4C510B5B8895BC2000E000`
- `run_local_battle.py`:
  `E1ABA0151CDAEE425B858511AA760CE5C5647D555DDEFBD69D7319C29C5B773B`
- `combine_staged_panel_results.py`:
  `CABFB6ECB500EF1395B05EDB5A9775193B8A13578E3EDF35C0CED04214175C77`
- `run_alakazam_staged_metric_suite.py`:
  `BCC98229B23C86FC5EB248D3F1E254337008FF4E85BD85224B3B3D6F570F1EEA`
- `alakazam_staged_metrics.py`:
  `78A0BE6E87368939D7FCE590E1AA65B5DFFA228DE224FFB53AA42C8DE1EF295B`

All commands use `-B`, `max_steps=1000`, a fresh destination, and the checked
engine. Failed or partial attempts remain on disk and are not silently repaired.

## Paired 700-game schedule

Run every Cartesian product of:

- seed bases:
  `202608500, 202608510, 202608520, 202608530, 202608540`
- opponents:
  `marnie`, `cynthia`, `alakazam_mirror`,
  `rocket_mewtwo_spidops_proxy`, `kangaskhan_crustle`,
  `historical_silver`, `direct_frozen`
- seats: `0, 1`
- games per seat and cell: `10`

This is 35 panels, 20 paired rows per panel, and 700 paired rows. For each row,
the baseline, candidate, and duplicate-baseline control use the same opponent,
seat, and seed.

The opponent paths and frozen `main.py` / `deck.csv` hashes are:

| Label | Path | Main SHA-256 | Deck SHA-256 |
|---|---|---|---|
| marnie | `meta_agents/marnie_sota_live_85033057_simple` | `B65E61837F19E08BC75D016BFDCF3F31CCAC44957592145454020B72777631BA` | `D875568AA29003A376F0AA23693252635232B0B5B9B53883030A8613E827864E` |
| cynthia | `meta_agents/cynthia_garchomp_nasuo445_v80_legal_complete_role_cycle` | `730E62AA749F6CC57ADA91F4E55D6B364DDAE2B12A303FA559453B3A5FE3E937` | `606B44F7D6181C57C6CCDD7EE493C72BAF39E684B264886BC01631DBEE8D349C` |
| alakazam_mirror | `meta_agents/alakazam_oselcoun_live_85035844_simple` | `9BD4FDBCCBD43786F689232B36D01A107BE16B4423EB91966DC964846031A2DC` | `33F38523C965D5DD57EB806B51B4706FEA476E4BFA96A1F314860F6413949B94` |
| rocket_mewtwo_spidops_proxy | `meta_agents/rocket_mewtwo_spidops_kashiwashira_20260703_simple` | `ECD6487B92441D2DC1ED6AA86376D0DCFB54FD0ACEEBBE4C28571FB9C0004D4B` | `E0BD6B4438A699B58D94375989147FC0BD81E5634512CEB261BE6D1D41F51EFA` |
| kangaskhan_crustle | `meta_agents/kangaskhan_crustle_mpgaming_v13_backupkang_two_growline` | `71250880337D6CDA1919BF4914DE32009D1267C84F6AED3496A690BE0C8F8F95` | `9FCDEEA4F2E741489261EFCFBC19DA81D88DE9079ED01C076EA7F361F07E993E` |
| historical_silver | `analysis_outputs/reference_agents/historical_silver_archaludon_54495224` | `F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E` | `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A` |
| direct_frozen | `alakazam_staged_20260729/eval_adapters/alakazam_800_frozen` | `B99DE98C53E777332B5F21036E1F634A2BBD9FD1BD22C3049F9467A953F1E8A2` | `A7B6C7972915D09F6314C42633AA89D82B55DDF0A7199F7138E681FA52516529` |

Per-panel output:
`evaluations/v4_c4_wall_shadow_fix6_panels/<seed>_<opponent>/attempt_1`.

Combined output:
`evaluations/v4_c4_wall_shadow_fix6_combined_attempt1`.

Required combined schema has one unique row for every
`(opponent, seat, seed_base, game, seed)` and includes:
`baseline_result`, `candidate_result`, `baseline_win`, `candidate_win`,
`baseline_steps`, and `candidate_steps`.

Acceptance for shadow integrity requires:

- exactly 700 unique rows and exact schedule equality;
- candidate and baseline results equal on all 700 rows;
- duplicate-baseline controls equal;
- no action errors or max-step hits;
- every subprocess exits zero.

## Shadow metric schedule

Run C4 only, ten games per block, both seats, five seed bases.

1. `formal_v4_c4_wall_shadow_fix6_trace_a`
   - Marnie, Cynthia, Alakazam mirror
   - seed bases `202608500..202608540`
   - 30 blocks / 300 games
2. `formal_v4_c4_wall_shadow_fix6_trace_b`
   - Rocket Mewtwo/Spidops, Kangaskhan/Crustle
   - same five seed bases
   - 20 blocks / 200 games
3. `formal_v4_c4_wall_shadow_fix6_trace_c`
   - Historical Silver, direct frozen Alakazam
   - same five seed bases
   - 20 blocks / 200 games
4. `formal_v4_c4_wall_shadow_fix6_megalucario_reach1`
   - `mega_lucario_aib4`, `mega_lucario_fujiborozoukin`
   - seed bases `202609500, 202609510, 202609520, 202609530, 202609540`
   - 20 blocks / 200 games

The two Mega Lucario opponents use:

| Label | Path | Main SHA-256 | Deck SHA-256 |
|---|---|---|---|
| mega_lucario_aib4 | `meta_agents/mega_lucario_aib4_live_84983544_simple` | `51A672D2FB57429E9CDA31C8DB3C3B48281535E6CBB594F0A39898A1998C1099` | `2A541D7BF3D9E6B36037123F53F4DFEF6348223F79FD27095DAFC602A5357C19` |
| mega_lucario_fujiborozoukin | `meta_agents/mega_lucario_fujiborozoukin_live_85033862_simple` | `51A672D2FB57429E9CDA31C8DB3C3B48281535E6CBB594F0A39898A1998C1099` | `D6B1417B848C75991BCF1EA5FE96E65A2B8A56FEC27DCD95DDC51005A6C1E90E` |

The union is exactly 90 blocks / 900 games. The collector is invoked once
over all four suite roots with the exact C4 closure above.

Integrity `FAIL` exits 2. An intact run with insufficient reach exits 0 and is
reported as `INSUFFICIENT_EVIDENCE`.

Minimum C5 consideration gates:

- 24 unique STRICT public pair states;
- 40 unique PRESERVE_CHANCE pair states;
- both seats;
- at least three opponents, including two non-mirror opponents;
- at least two STRICT opponent buckets;
- at least 12 verified natural parent agreements;
- at least eight same-game, trace-complete outcomes;
- zero action-identity, metric-exception, sparse-schema, closure, raw-binding,
  state-conflict, outcome-counterexample, or `CANDIDATE_APPLIED` faults.

If any gate fails, C5 is a documented no-op. If all gates pass, a Sol-Ultra
strategy judge may select at most one of A, B, or C for an isolated
action-changing candidate. `PRESERVE_CHANCE` is never action-changing in the
first version.

## Root verification

The root independently recomputes:

1. baseline and candidate wins from raw paired rows;
2. key uniqueness and exact schedule equality;
3. row, manifest, exit, action-error, and max-step totals;
4. collector integrity and reach counts from raw JSONL;
5. SHA-256 for every submission-critical output.

Subagent summaries are informational until these checks agree.
