# Rule 3 repair v2 root pre-fixed160 verification

Date: 2026-08-03 JST

## Frozen inputs

- Parent: `autonomous_gold_20260715/final/archaludon_historical_silver_single_resolver_salvage_v1`
- Parent `main.py`: `D966E455E5110F9D5616195AEAAC8663E6A92F310DAFC4B7F79E4D37149A9C62`
- Candidate: `autonomous_gold_20260715/candidates/archaludon_historical_silver_single_resolver_salvage_rule3_repair_v2`
- Candidate `main.py`: `1C5676A97783B17D0A4B1D2D647777975463CF8759DA534A62CA47F2D0C39BE2`
- Historical-Silver module: `F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E`
- Deck: `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`
- Controlling amendment: `196BD3C4F5324615BD6E01D2694C45850942D64001E7C4931D219836884716EB`
- Focused runner: `7AF10EC95CB9B71AEF180240DB68E1B37E7EC64208763117A782C352818CB7C7`
- Focused results: `BD2D946DDD49FE5851B51A56249E63A6050CCEE1A1046AF656A771D9EFC75478`

## Root checks

- Focused Rule 3 fixtures: `158/158` passed.
- Inherited Rule 1/4/5 tests: `28/28` passed.
- Twelve Python files compiled; import and immutable metadata checks passed.
- The deck has exactly 60 cards and exactly one ACE SPEC (`1159`).
- There is one top-level `agent`, one `_resolve`, one shared owner, and one static Historical-Silver parent call per callback.
- The final top-level callable is `agent`.

## Checked-engine natural transactions

### Turbo Flare, candidate seat 0

- Opponent: `meta_agents/archaludon_shumpei_current_v3`
- Seed: `271958324`
- Result: 53 steps, action errors 0, no max-step hit.
- Rule 3 began with planned costs `Cinderace 11 + Full Metal Lab 15`.
- Historical-Silver selected physical costs `Metal Energy 52 + Cinderace 11`.
- The repair adopted the exact parent pair, preserved the parent search copy, searched Duraludon 3, placed it, used Turbo Flare, and attached three exact Metal Energy to it.
- Terminal receipt: `turbo_attack_and_attachments_observed`.
- Irreversible aborts: 0.

Evidence: `turbo_seat0_seed271958324`.

### Active Duraludon to Archaludon ex, candidate seat 1

- Opponent: `meta_agents/archaludon_shumpei_current_v3`
- Seed: `271958323`
- Result: 102 steps, action errors 0, no max-step hit.
- The transaction preserved physical costs `Metal Energy 122 + Cinderace 74`, preserved the parent search copy Archaludon ex 68, evolved Active Duraludon 63, activated Assemble Alloy, attached exact Metal Energy 113 and 122, and used Metal Defender.
- Terminal receipt: `metal_defender_observed`.
- Irreversible aborts: 0.

Evidence: `active_ex_seat1_seed271958323`.

### Former illegal first-turn failure

- Opponent: `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_archattach_ruleinline_20260710`
- Candidate seat 0, seed `271958318`.
- Parent and candidate each completed 133 steps with result 0, action errors 0, and no max-step hit.
- The complete trace files are byte-identical with SHA-256 `350D9A7103BB9E0036CBFD09A235ACB1658A1C49F65CA44477A504AA9627DC6A`.
- Rule 3 therefore does not start on the former illegal first-turn evolution route.

Evidence: `seed271958318`.

## Fixed160 decision

Preconditions pass. Freeze and execute the exact Historical-Silver mirror, Arch Peak, Alakazam, and Marnie schedule with 20 seeds in both seats. Any irreversible Rule 3 abort remains an implementation defect to repair, not a reason to abandon the strategy.
