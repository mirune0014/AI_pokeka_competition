# Alakazam Neutralization Zone v1 verification

## Scope

The v0 directory materializes the public Best-5 notebook's `deck.csv` and
`main.py` writefile payloads unchanged, with one conventional terminal newline
added by `apply_patch`. The focused test checks the complete payload text.

The v1 deck changes only card 13 (Enriching Energy) to card 1247
(Neutralization Zone). The existing Fezandipiti behavior is unchanged.
The rule uses only visible Pokémon, visible attached energy, public attack
costs, current prizes, current HP, hand contents, and the current Stadium.

Zone is eligible only for a visible ex whose public attack cost is met now or
after one attachment while our Active is non-Rule-Box. Spending the one hand
card is vetoed when it loses an immediate Powerful Hand KO, except for a
publicly certified final-prize ex KO threat. A ready Boss KO is also preserved.
Battle Cage is limited to visible Dragapult-line counter pressure, is a fallback
when Zone is not selected, and never overwrites an active Zone.

Fail-closed limitation: the final-prize override recognizes only printed base
attack damage at least equal to the Active's current HP. It does not guess
dynamic damage from attack text, hidden modifiers, future switches, Weakness,
or Resistance.

## Commands and exits

- `py -3.11 -m py_compile <v0/main.py> <v1/main.py> <test_zone_candidate.py>` — exit 0.
- `py -3.11 <v1/tests/test_zone_candidate.py>` — exit 0; output
  `zone candidate focused tests: PASS`.
- First root-working-directory smoke against v0 — exit 1 before battle start:
  the public notebook opens `deck.csv` during module import, while the checked
  runner changes directory only when calling the agent.
- Checked-engine self-play smoke from the v1 directory:
  `py -3.11 <repo>/tools/run_local_battle.py --engine-dir <seeded_engine> --agent-a <v1> --agent-b <v1> --games 1 --max-steps 1200 --seed-base 1247001 --engine-seed --summary <v1/smoke_summary.json>`
  — exit 0; seed 1247001, 19 steps, `action_errors=0`, `hit_max_steps=false`.

This is an execution smoke only, not matchup evidence or a promotion claim.

## SHA256

- Source notebook: `736F98EF271FB7C21DEDFBA0B0635EB9EB149B05BD952A88D7C51EF4993D9431`
- v0 `main.py`: `DF4D597F593950B0D0C372F3E0BB26C182C4116648977F15ADBB329A6BA922F4`
- v0 `deck.csv`: `7B413177E5077777F2178143839C0155B03B92BBC8B3A6607621A7D43F351141`
- v1 `main.py`: `31B28A5ACFCF1B50B0E8F37851593E4F4B92BED95DE9B781E0F5E2C250C3C955`
- v1 `deck.csv`: `65FF12E790AA9A6844CAC3CD530A06897FCDD0C7194B530348B56ED9760347F0`
- `tests/test_zone_candidate.py`: `F8DFF1B743EDC484120C31B0A3D1D3A291C93CAFF0A6A42C3E2D871EEC1B7D87`
- `smoke_summary.json`: `5A18509C3280FC1F3B29E0501AE6D48F47EFC25CFF1D0565895B9918E1F9F2C2`

## Runtime compatibility follow-up

The audited parent `main.py` and `deck.csv` files were left unchanged. Each
agent now also has a `runtime/` directory. Its wrapper temporarily changes to
the parent directory while importing the audited parent source, restores the
caller's working directory in `finally`, and exposes the parent's callable
`agent`. Each runtime deck is byte-identical to its parent deck.

Commands and exits:

- Runtime wrapper `py_compile`, followed from repository root by checked
  `tools.ptcg_common.load_agent`, two identical initial observations, and exact
  60-card deck-return checks for both runtimes — exit 0; output
  `root-cwd runtime syntax/import/deck-return/determinism: PASS`.
- `py -3.11 tools/run_seeded_paired_suite.py --engine-dir analysis_outputs/cynthia_v9_vs_v11_poffin_role_selection_20260713/seeded_engine --baseline autonomous_gold_20260715/candidates/alakazam_neutralization_v0_public_best5_exact/runtime --candidate autonomous_gold_20260715/candidates/alakazam_neutralization_v1_zone/runtime --opponent historical_silver=autonomous_gold_20260715/baseline/historical_silver_archaludon_54495224 --games-per-seat 1 --seed-base 1247002 --max-steps 1200 --output-dir autonomous_gold_20260715/evaluations/runtime_smoke`
  — exit 0.
- Independent output assertions — exit 0: `valid=true`, 2 paired rows (one per
  seat), 4 populated baseline/candidate policy-result fields, 2 cell rows, 6
  subprocess manifest runs, 6 raw summary rows, all subprocess exit codes 0,
  zero action errors, zero max-step hits, zero duplicate mismatches, and no
  invalid reasons.

Runtime and checked-smoke SHA256:

- v0 runtime `main.py`: `D37DBBE7933F939266D1D1DEEFEEC666CF908A910F56539AFF37936E30CBCBA9`
- v0 runtime `deck.csv`: `7B413177E5077777F2178143839C0155B03B92BBC8B3A6607621A7D43F351141`
- v1 runtime `main.py`: `6F08E9292D87A0A069CCDBECBA39B49B6D577FD6C84B781BB3DE3D797712811B`
- v1 runtime `deck.csv`: `65FF12E790AA9A6844CAC3CD530A06897FCDD0C7194B530348B56ED9760347F0`
- `runtime_smoke/report.json`: `8C3B52F91280BB3C74EBD6B91EC4107B32B47AE3E8DDC37090045700941FEA58`
- `runtime_smoke/paired_results.csv`: `4C7CD671390C1BA734E7CB6ED948995A7FE31DAFEAF6A1CE968C4DA26E917925`
- `runtime_smoke/cell_summary.csv`: `9B7F9304ED73F96EC1F1E1C88CD5177CA6879DBC2759333D2477526FA74EFDD8`
- `runtime_smoke/manifest.jsonl`: `B3BD68038FE843C875659C2ABFEB46A44E3AF562114FFC3F90924FF46784B8C6`
