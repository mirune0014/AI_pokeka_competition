# Evaluation population recovery

## Why a replacement population is required

The selected strategy asked to reuse the prior 200-game historical-Silver
mirror and 480-game adjacent-population schedules from
`isolated_rule_agents/orbit_transfer_archaludon_20260715/EVALUATION_SPEC.md`.

The root recovered the exact engine, runner, historical mirror, seeds, and four
of the six adjacent opponent directories. Two frozen opponent paths no longer
exist in the workspace:

- `submission_marnie_variant_kazuki_boss2_xerosic1_rules`
- `submission_marnie_variant_tonakaiiii_prizemap_munki3boss`

The old adjacent population also had no Alakazam opponent, although Alakazam is
the primary target of H1. Reusing only the surviving four cells would therefore
violate the requested primary-bucket and adjacent-population checks.

## Preserved execution contract

- Engine:
  `analysis_outputs/cynthia_v9_vs_v11_poffin_role_selection_20260713/seeded_engine`.
- Checked runner:
  `tools/run_seeded_paired_suite.py`
  (`5EC25C98F2777FF61DE2DBD0A03A08519A7FEA4B2B4C510B5B8895BC2000E000`).
- Battle runner:
  `tools/run_local_battle.py`
  (`E1ABA0151CDAEE425B858511AA760CE5C5647D555DDEFBD69D7319C29C5B773B`).
- Exact parent:
  `analysis_outputs/reference_agents/historical_silver_archaludon_54495224`
  (`main.py`
  `F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E`,
  `deck.csv`
  `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`).
- Historical mirror seed base: `271828182`, 100 games per seat, 200 paired
  rows, max 1,000 steps.
- Adjacent seed base: `271958313`, 40 games per seat per opponent, max 1,000
  steps.
- Each checked-runner cell executes baseline control A, baseline control B, and
  candidate and must preserve exact duplicate controls.

## Replacement adjacent population

Use seven complete deterministic opponents, producing 560 paired rows:

| label | path | `main.py` SHA-256 | `deck.csv` SHA-256 |
|---|---|---|---|
| `arch_peak` | `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_archattach_ruleinline_20260710` | `9F4A35D7CC2365AC2A9A5B1A684E4C66618FEF08E6DD0635D75EA49AF423313D` | `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A` |
| `arch_shumpei` | `meta_agents/archaludon_shumpei_current_v3` | `A0567DB9CA05121C432A9A0C9833958EEDA595EC4EB64515510805647DA094F8` | `4695E1BE02192385E72D739E40C5BB847BF3D90CE099E55EF189A3CBC80F8CF2` |
| `alakazam_turn_plan` | `autonomous_gold_20260715/candidates/alakazam_certified_turn_plan_conversion_v1` | `E9EF903AE8593758DE76C3911096781E342A0170F3434D9CB35639C991EA7920` | `7B413177E5077777F2178143839C0155B03B92BBC8B3A6607621A7D43F351141` |
| `marnie_kazuki_live` | `meta_agents/marnie_kazuki_live_85083586_simple` | `B2317C6CD6A031912BCFE89D5498B33A056F1D9583C7631E046E4F8ABAD9E59D` | `F75CB0C32939525FF083FCB5C4D6052D413E21644FDAFF81DE717F9121EAEE1B` |
| `mega_lucario_public` | `meta_agents/mega_lucario_public_simple` | `A5732DD50FA0F0BC872B6CFC92227B9A61D48F989D97BB282C06F9509E68158F` | `026F160E0BC581BA97004047CEF3FE0986C7D49FA3B77D6956226E9A70D3252D` |
| `kang_crustle` | `meta_agents/kangaskhan_crustle_mpgaming_v23_heal_role_missing160_guard` | `F3DBBBE854759F7C187C116D6D8705F559E11EEFDEDD3822AAD048BC4E77CA28` | `9FCDEEA4F2E741489261EFCFBC19DA81D88DE9079ED01C076EA7F361F07E993E` |
| `cynthia_v23` | `meta_agents/cynthia_garchomp_nasuo445_v23_allcall_before_evolve` | `1BEEB2EE1B5E82E268459665E37C16996590B4701702ACC0A869A1671148065F` | `606B44F7D6181C57C6CCDD7EE493C72BAF39E684B264886BC01631DBEE8D349C` |

The two newly selected live-simple opponents are deterministic rule-based
complete agents. They are used only as executable anti-overfitting opponents,
not as action labels, learned rankers, or opponent-policy proxies.

## Interpretation gate

The final immutable evaluation specification must bind the frozen candidate
source and deck hashes before execution. It must require:

- 200 exact historical-mirror rows and 560 adjacent rows;
- unique and equal `(panel, opponent, seat, seed)` schedules;
- all baseline-A/baseline-B duplicate controls identical;
- zero action errors, exceptions, and max-step hits;
- baseline-win/candidate-loss flips zero overall, by seat, and in every
  opponent bucket;
- no trigger-external first divergence;
- every natural H1 continuation classified as Boss -> certified Alakazam ->
  Metal Defender;
- no natural start is not a failure of safety, but it is no strength evidence.

The user permits a structurally safe exploratory live probe with zero local
gain. A regression or structural fault still blocks it.
