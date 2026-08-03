# Rule 3 parent-prefix repair: root pre-fixed160 verification

Date: 2026-08-03 JST

## Frozen inputs

- Parent: `autonomous_gold_20260715/final/archaludon_historical_silver_single_resolver_salvage_v1`
- Parent `main.py`: `D966E455E5110F9D5616195AEAAC8663E6A92F310DAFC4B7F79E4D37149A9C62`
- Candidate: `autonomous_gold_20260715/candidates/archaludon_historical_silver_single_resolver_salvage_rule3_repair_v2`
- Candidate `main.py`: `4287A616E1611F5697964D9F4065978EED1CEA72CDB48C9F63F1430D69106C35`
- Historical-Silver module: `F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E`
- Deck: `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`
- Original Rule 3 amendment: `196BD3C4F5324615BD6E01D2694C45850942D64001E7C4931D219836884716EB`
- Parent-prefix controlling amendment: `C55458C1A8AD4649845BDAE707067DAD295EF7D1F938DF5371E2502EF263344C`
- Focused runner: `4220BA32F161D0F5297A7B28053989236A2FEA71EEB117289F8E3D92229C4481`
- Focused results: `00C314EB8C856B7F1B48092B4C4F23331B47AF9B000FE498B40C34981D0FDBD8`
- Implementation report: `BAF074429CA05D8CCE7791478052A2095419E45A5AC83F2F80793536C57FD214`

## Independent root checks

- Rule 3 focused fixtures: `276/276` passed, exit `0`.
- Inherited Rule 1/4/5 tests: `28/28` passed, exit `0`.
- Candidate and test sources compile and import.
- The deck has exactly 60 cards and exactly one ACE SPEC (`1159`).
- There is one top-level `agent`, one `_resolve`, one shared owner, and one
  static Historical-Silver parent call per callback.
- The final top-level callable is `agent`.

## Checked-engine natural transactions

All games used the checked seeded engine at
`analysis_outputs/cynthia_v9_vs_v11_poffin_role_selection_20260713/seeded_engine`.

### Active Duraludon to Archaludon ex, candidate seat 1

- Opponent: `meta_agents/archaludon_shumpei_current_v3`
- Seed: `271958323`
- Candidate and parent: 135 steps, result `1`, action errors `0`, no max-step.
- Candidate and parent traces are byte-identical:
  `5923D684ABF8F00A543B8A7C420B1485396108950F2E06C18E732C5FEAB4744C`.
- Rule 3 owned 20 candidate callbacks, including Ultra Ball, physical costs,
  search, Active evolution, Assemble Alloy, Lillie, Poké Pad/search, another
  Ultra Ball/search, two Basic placements, and the parent's Metal Defender.
- Rule 3 completed once with `metal_defender_observed`.
- Irreversible abort faults: `0`.
- Telemetry: `telemetry_active.jsonl`, SHA-256
  `A774A2E911B3AE41008164E26A7F6E4941E2F1DD7460FC75CA2709347E5CCA84`.

This repairs the pre-amendment candidate's 102-step loss caused by forcing
Metal Defender before Historical-Silver's same-turn setup prefix.

### Turbo Flare, candidate seat 0

- Opponent: `meta_agents/archaludon_shumpei_current_v3`
- Seed: `271958324`
- Candidate and parent: 53 steps, result `1`, action errors `0`, no max-step.
- Candidate and parent traces are byte-identical:
  `6F72DF73861AEAF706A5AEDEB9B9288C3D70BA55A43AF2C0344EFE362497EA8F`.
- Rule 3 owned 10 candidate callbacks and completed once with
  `turbo_attack_and_attachments_observed`.
- The previous physical Basic Metal copy/order difference is absent.
- Irreversible abort faults: `0`.
- Telemetry: `telemetry_turbo.jsonl`, SHA-256
  `0465D6DE920483A6859A000D695B5F1DC888411233748ED4738BF7521E5D3B76`.

### Former illegal first-turn route

- Opponent:
  `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_archattach_ruleinline_20260710`
- Candidate seat 0, seed `271958318`.
- Candidate and parent: 133 steps, result `0`, action errors `0`, no max-step.
- Candidate and parent traces are byte-identical:
  `615B1F4279E1E976E580BB94E169E338CBE8684F982BD436FB6F30ECB336F8EE`.
- Rule 3 selected callbacks/completions/irreversible aborts: `0/0/0`.
- Telemetry: `telemetry_former.jsonl`, SHA-256
  `5881D37932F8EDE7599B6D2917B32D49D97FBDE58FCCAB5557DEF15C2B4E6A5A`.

The telemetry runner is `run_rule3_telemetry.py`, SHA-256
`4AEB8EE6AD2605E5715C068657002687A09B36EB4997640C7BB42DC8901E3AC1`.

## Fixed160 decision

Preconditions pass. Freeze this candidate SHA and rerun the exact
Historical-Silver mirror, Arch Peak, Alakazam, and Marnie schedule with 20
seeds in both seats, using a new immutable output destination. The prior
fixed160 output belongs to candidate SHA `1C5676...` and is not promotion
evidence for this SHA.
