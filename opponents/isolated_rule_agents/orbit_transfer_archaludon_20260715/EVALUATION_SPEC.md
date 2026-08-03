# Orbit-transfer Archaludon immutable evaluation specification

## Decision and scope

This experiment keeps the exact historical-Silver Archaludon deck and policy as
the baseline.  It transfers one Orbit Wars idea into a pure deterministic rule:
semantic terminal intent is ranked ahead of nonterminal utility only when the
current public observation proves that a currently legal attack takes every
remaining Prize.  It does not use reinforcement learning, imitation, replay
action labels, an opponent-policy proxy, or persistent cross-observation state.

The isolated hypothesis is **fail-closed terminal conversion**.  The candidate
may change only the score of the currently legal MAIN/ATTACK option.  The proof
is recomputed from the current observation and must fail closed for status,
damage prevention/reduction, unresolved public effects, unknown types, an
ongoing Coated Attack barrier against a Basic attacker, or an unmodelled attack.

## Frozen source receipts

- Historical archive:
  `submission_archaludon_gtmidguard_lucariobev_crustledeckguard.tar.gz`.
- Archive SHA256:
  `69BC01010FA2963781E6CD18CBA4773E0372127763DBB7AAF5E2081E1A156809`.
- Baseline directory:
  `isolated_rule_agents/orbit_transfer_archaludon_20260715/baseline_exact`.
- Baseline `main.py` SHA256:
  `F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E`.
- Candidate directory:
  `isolated_rule_agents/orbit_transfer_archaludon_20260715/candidate_terminal_conversion`.
- Candidate `main.py` SHA256:
  `5382920827F0159D847741B494C8ADD19E0A4C840AEB0697D6ADBBD9D27C3277`.
- Shared `deck.csv` SHA256:
  `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`.
- Focused test SHA256:
  `E99047A08D4B4E16E0A1A27DBECB38C7744D0154753385868442E7522557AE3A`.
- Engine:
  `analysis_outputs/cynthia_v9_vs_v11_poffin_role_selection_20260713/seeded_engine`.
- Engine canonical tree SHA256:
  `586B92FDEA892CBB147D4C6A113575CCD98E4FC90528BABB6E8F7294D0CBEBF2`
  over 26 sorted `relative_path\0size\0file_sha256\n` rows.
- Paired runner SHA256:
  `5EC25C98F2777FF61DE2DBD0A03A08519A7FEA4B2B4C510B5B8895BC2000E000`.
- Battle runner SHA256:
  `E1ABA0151CDAEE425B858511AA760CE5C5647D555DDEFBD69D7319C29C5B773B`.

## Stage 0: implementation contract

Focused tests must cover final-Prize lethal priority, nonfinal KO, short damage,
confused/asleep/paralyzed, Full Metal Lab, Resistance, visible prevention and
unknown effects, ongoing Coated Attack, Raging Hammer damage, deterministic
tie-breaking, per-observation recomputation, and exact trigger-free baseline
scores.  Python compile, normal import, and a 60-card deck check must pass.

## Stage 1: primary historical-Silver mirror anchor

- Opponent:
  `analysis_outputs/reference_agents/historical_silver_archaludon_54495224`.
- Opponent `main.py` SHA256:
  `F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E`.
- Opponent `deck.csv` SHA256:
  `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`.
- Seed base: `271828182`.
- Games: 100 per seat, both seats, 200 paired rows.
- Max steps: 1000.
- Destination:
  `isolated_rule_agents/orbit_transfer_archaludon_20260715/evaluation/historical_silver`.

## Stage 2: complete adjacent-policy population

- Seed base: `271958313`.
- Games: 40 per seat per opponent, 480 paired rows.
- Max steps: 1000.
- Destination:
  `isolated_rule_agents/orbit_transfer_archaludon_20260715/evaluation/adjacent_population`.

| label | path | main.py SHA256 | deck.csv SHA256 |
|---|---|---|---|
| arch_peak | `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_archattach_ruleinline_20260710` | `9F4A35D7CC2365AC2A9A5B1A684E4C66618FEF08E6DD0635D75EA49AF423313D` | `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A` |
| arch_shumpei | `meta_agents/archaludon_shumpei_current_v3` | `A0567DB9CA05121C432A9A0C9833958EEDA595EC4EB64515510805647DA094F8` | `4695E1BE02192385E72D739E40C5BB847BF3D90CE099E55EF189A3CBC80F8CF2` |
| cynthia_v23 | `meta_agents/cynthia_garchomp_nasuo445_v23_allcall_before_evolve` | `1BEEB2EE1B5E82E268459665E37C16996590B4701702ACC0A869A1671148065F` | `606B44F7D6181C57C6CCDD7EE493C72BAF39E684B264886BC01631DBEE8D349C` |
| kang_v23 | `meta_agents/kangaskhan_crustle_mpgaming_v23_heal_role_missing160_guard` | `F3DBBBE854759F7C187C116D6D8705F559E11EEFDEDD3822AAD048BC4E77CA28` | `9FCDEEA4F2E741489261EFCFBC19DA81D88DE9079ED01C076EA7F361F07E993E` |
| marnie_kazuki | `submission_marnie_variant_kazuki_boss2_xerosic1_rules` | `6315AD0E9442D30DAF4350426679088949D0C07D4D5E340D38D3B3708EAF6F34` | `364A2C4DFD93059175636E2BB62EE99C9D6CFA76B65512C68CB339CDB5A250D5` |
| marnie_tonakai | `submission_marnie_variant_tonakaiiii_prizemap_munki3boss` | `7A14D4956183CCC9646260CBAE05A4C49C09DFD04B14942B6E55FC061F0203D8` | `9ED0BD99B23360545F82E88BD5ACD1928A9DD8F9C6446A898A7BE8EFDA1925D8` |

## Required raw contract

Use only `tools/run_seeded_paired_suite.py`.  Each schedule cell must run
baseline control A, baseline control B, and candidate.  Required outputs are
`manifest.jsonl`, `cell_summary.csv`, `paired_results.csv`, and `report.json`.
The paired schema is:

`seed_base,opponent,seat,game,seed,baseline_result,candidate_result,baseline_win,candidate_win,baseline_steps,candidate_steps`

The evaluator and root must independently verify unique
`(opponent, seat, seed)` keys, exact schedules, row totals, all command exit
codes, exact duplicate controls, and zero action errors/max-step hits.

## Frozen adoption gate

- Every first divergence is a certified terminal attack versus a nonterminal
  baseline action; there are no trigger-external divergences.
- Every certificate immediately ends in a Prize-based win; false certificates
  are zero.
- Baseline-win/candidate-loss flips are zero in every family and seat.
- At least one baseline-loss/candidate-win flip is required to call this a
  strength improvement.
- If outcomes are identical and only terminal wins use fewer actions, retain
  the artifact as a safe Orbit-transfer experiment but do not call it the new
  strongest agent.

## Frozen first-divergence trace audit

After the paired schedule completes, rerun baseline and candidate separately on
the exact same Stage 1 and Stage 2 cells with `tools/run_local_battle.py`,
engine seeding, full game counts, max 1000 steps, and scored traces.  For policy
seat 0 use the policy as `agent-a`; for seat 1 use it as `agent-b`.  Store all
outputs only below:

`isolated_rule_agents/orbit_transfer_archaludon_20260715/evaluation/trace_audit`

Use `tools/compare_local_trace_first_divergences.py` over every matching trace
pair.  The trace gate requires:

- the number of divergent traces equals the paired-result step-difference
  count;
- every candidate first divergence selects an ATTACK scored
  `terminal conversion` against a baseline nonterminal action;
- the candidate divergence is its final recorded decision and its summary
  result is a win for the candidate seat;
- all paired losses are action-identical; and
- there is no divergence outside the certified terminal-conversion surface.
