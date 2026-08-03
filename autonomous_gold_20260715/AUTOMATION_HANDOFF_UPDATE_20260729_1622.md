# Automation handoff update — 2026-07-29 16:22 JST

This file supersedes stale current-live, H6, H7-A, and execution statements in
`AUTOMATION_HANDOFF_UPDATE_20260729_1504.md`.

## Controlling scope

Continue the active Goal and obey repository `AGENTS.md`. Root owns planning,
raw verification, documentation, packaging, and every Kaggle write. Keep all
competition edits under `autonomous_gold_20260715`; existing repository
artifacts are read-only inputs. Use deterministic public-state rules only.
Candidate implementation workers alone use Fast `ptcg_candidate_worker`.
Never stack sibling experiments.

Exact formal parent remains historical-Silver Archaludon:

- source:
  `analysis_outputs/reference_agents/historical_silver_archaludon_54495224/main.py`
- source SHA:
  `F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E`
- deck SHA:
  `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`

## Current live H5 v2

Submission `55073442`,
`archaludon_public_lethal_active_no_ready_successor_nonex_120_ko_v2`,
remains the sole live exploratory probe.

- submitted: `2026-07-29 15:01:49 JST`
- source:
  `E493C692198FE3699269F3CAFECD3010815DDE5EA2B3002321DDE109F9566798`
- archive:
  `EDCD7EC09C3A45C5C6B3C6648AF5E048A53CD2BC41C2C60DCE8BF7C923FCA004`
- latest authenticated checkpoint: `2026-07-29 16:14-16:18 JST`
- status: `COMPLETE`
- public record: `13-5`
- exact score: `813.1635762897763`
- UTC quota: `2/5` used, `3/5` remaining
- latest checkpoint:
  `live/55073442/refresh_20260729_1614/ROOT_EIGHTEEN_PUBLIC_CHECKPOINT.md`
- checkpoint SHA:
  `E011D25B76C0AB895F4C9871CEA30F942CE5CD00B8B005B7A872400EBADBD6BF`

All 18 public replays remain H5-parent identical. The complete 225-file corpus
has 12,442 callbacks; its only difference is historical source
`87996118:96`. There is no H5-owned defect and no causal H5 win/loss evidence.
Do not attribute the 13-5 record or score to H5.

Do not replace H5 before approximately `2026-07-29 18:01:49 JST` unless a
destructive H5-owned defect appears. Refresh near 20/40 public games and at the
three-hour maturity checkpoint. Never resubmit the exact source/archive.

## H6 implementation and fixed evaluation

H6 is the isolated direct-parent child:

`candidates/archaludon_attack_completing_energy_reservation_v1`.

- source:
  `AC798FD2B757D94DDC21EFF07FE53EF4AFB9C139F98EA47DA0A9285ABC5FABB5`
- deck unchanged:
  `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`
- frozen strategy:
  `CF154A409B13FB985226EB1D68B291BBB2C31E46F704C4FCD971A979513D198D`
- Root implementation verification:
  `evaluations/archaludon_attack_completing_energy_reservation_v1/root_reverification_20260729/ROOT_IMPLEMENTATION_VERIFICATION.md`
- Root verification SHA:
  `CED715895E5FB1BBA2BA98015FBBB41D761F59BB386CD4D03AC4152F87C5F8BA`

Root independently reran structural, focused, exact-engine, and complete-shadow
gates. Outputs were byte-identical to the worker outputs. The sole shadow
difference is `88584180:91`: preserve Metal `#120`, discard Night Stretcher
and Jumbo Ice Cream, inherit the exact search, attach `#120` to the Active,
and attack Metal Defender. There were zero external differences or faults.

Fresh fixed-760 inputs:

- spec:
  `implementation/archaludon_attack_completing_energy_reservation_v1/fixed760_spec.json`
- spec SHA:
  `277C5E553B4BE03696DB48B6BC42B79385CA26624D25036DC3AA577ACFA9A278`
- executor SHA:
  `AD432903888D23BA4AD6C23D4DB63E9E262C6EBB0326F73D4E3ED320D341473E`
- immutable output:
  `evaluations/archaludon_attack_completing_energy_reservation_v1/fixed760_raw_20260729`

`/root/run_archaludon_h6_fixed760` is executing the exact 200+560 schedule as a
low-cost deterministic runner. It must not interpret results. After execution,
use one `ptcg_local_evaluator`, Root recomputation/trace inspection, then one
`ptcg_sol_ultra_worker` for final adoption/live judgment. Do not package or
submit H6 before those gates and H5 maturity.

## H7-A and remaining analysis

H7-A strategy decision is `SELECT_IMPLEMENTATION_EXPERIMENT_ONLY`:

- report:
  `strategy/archaludon_hierarchical_rules_20260729/STRATEGY_SELECTION_H7A_SOLE_READY_SUCCESSOR_CONTINUITY.md`
- report SHA:
  `D5B900A869078E76D71A4FB3ABF214D40C7A3AC341576F44E03EF1CBADA3C62F`

The isolated row-82 rule can preserve the only Bench Pokemon made
attack-payable by the final Assemble Alloy Metal while the Active's certified
non-KO attack exposes it to a visible return KO. It is not live-worthy yet:
Full Metal Lab makes the preserved Hammer In deal zero to the current Active,
and exact-parent promotion still chooses another unready Pokemon. H7-B
promotion is separate and must not be stacked.

Bench-damage strategy evidence is frozen at:

- `BENCH_DAMAGE_FUTURE_VALUE_AUDIT.md`
  `74C135E9F005F9BADC8C94933FF069F4F23B584183683D7AB0B2811F04F83A9C`
- `ROOT_BENCH_DAMAGE_AUDIT_VERIFICATION.md`
  `4D8AC5B31817B4857A8520A5D862FFBCC5CCD6029ACD9188A0D4E0AD84F0A1AB`

It proves only the alternate row-115 Bench evolution option in replay
`88247531`, not a winning continuation.

The broader 48-loss decline-KO/alternate-damage audit is frozen by:

`strategy/archaludon_hierarchical_rules_20260729/DECLINE_KO_AND_ALTERNATE_DAMAGE_AUDIT_SPEC.md`

SHA:
`F2A0D3DFEFC4030ACEFB0B8B0E27241F17312CB1062E3C9D1A3A0EB6BAE1A141`.

Collect its final read-only report. Do not mix any discovered mechanism into
H5 or H6.

## Resume order

1. Refresh authenticated H5 status, UTC quota, and exact episode set.
2. Shadow every genuinely new H5 replay against exact historical-Silver in the
   correct seat.
3. Collect mechanical H6 fixed-760 completion.
4. Run independent numerical audit, Root recomputation and every changed-trace
   inspection, then final Sol-Ultra judgment.
5. At H5 three-hour maturity, retain it inactive unless H5-owned natural
   evidence supports otherwise.
6. Only then decide whether H6 is a safe next live probe. Root alone packages
   and submits.
7. H7-A, H7-B, bench future value, and any decline-KO mechanism remain
   separate later siblings.

The Goal remains active until all user-agreed hierarchy mechanisms have
sufficient isolated implementation and destructive-fault-free verification.
