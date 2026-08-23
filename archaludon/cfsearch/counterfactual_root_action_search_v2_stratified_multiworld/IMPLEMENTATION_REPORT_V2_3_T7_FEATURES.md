# T7 formal feature classification V2.3

Date: 2026-08-16 (JST)

## Fixed invariants

The accepted Historical-Silver Archaludon parent and its deck are unchanged.
This work is a public-state diagnostic only: no candidate policy, parent edit,
deck edit, Kaggle package, or Kaggle submission was created.

- parent agent SHA-256: `506E1A75062EE22BEE550C303C74D44A141EF6F8A6AD0DB6AEADBD9211085CB6`
- deck SHA-256: `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`

## Import-audited formal rerun

The 64-root formal realized-seeded-world discovery was rerun after adding a
mechanical import audit to every fresh branch process. All 172 branches report
the seeded-engine `cg` module, with `engine_import_ok=true`; no branch was
invalidated for import shadowing.

The rerun remains mechanically identical to the earlier formal ledger:

| measure | value |
|---|---:|
| roots | 64 |
| parent rows | 64 |
| alternative rows | 108 |
| valid comparable alternatives | 108 |
| public root/prefix mismatches | 0 |
| action errors | 0 |
| max-step hits | 0 |
| gains | 8 |
| regressions | 9 |
| net | -1 |

The audited branch ledger is under
`_local_generated/analysis_outputs/archaludon_counterfactual_root_action_search_v2_stratified_multiworld/t7_formal_discovery64_v22_normalized_import_audited/`.

## Public feature classification

`classify_t7_formal_v23.py` loads only card/attack metadata from the explicitly
supplied seeded engine and records its `cg` path. It computes target area,
card identity, serial, energy count before/after the forced attach, minimum
printed attack cost and deficit, attack-ready/unlocked status, evolution and
Archaludon-in-hand flags, retreat legality, and exact/unknown attack and KO
features. `OptionType.ATTACK=13` and `OptionType.END=14` are handled
separately. Unknown modifiers are preserved as `UNKNOWN`, never coerced to
False.

The final classification output is under
`_local_generated/analysis_outputs/archaludon_counterfactual_root_action_search_v2_stratified_multiworld/t7_formal_feature_classification_v23_final/`.

The 108 comparable branches classify as:

- direction: T7A 40, T7B 38, T7C 19, same-target duplicate 11;
- alternative primary role: R1 7, R2 4, R3 33, R4 42, R5 21, OTHER 1;
- engine import shadow rows: 0.

Under GPT PRO's strict public predicates P1–P5, no branch matched a complete
predicate family. In particular, the apparent Active-surplus-to-Bench cases
usually changed retreat legality or contained an unknown attack/KO modifier;
these were correctly excluded rather than widened after seeing outcomes.
No discovery or exploratory candidate gate was applied, and no candidate was
created.

## Reproducibility hashes

- audited formal report: `72F537FBFB5D1164F35150F4A93F4E4FC897097AF542B738C7B4426C762D72CB`
- audited branch ledger: `B5D65F553B6A056BED1C2408D69221B75F20141DC1710317F16F33B5757413EF`
- feature report: `9EBC1496BAE15627FF229673C8457118FB9ACA089FBD59C1F72E744877DD39A8`
- classified rows: `21F2DFE5F67F3E5AFD50FE82CADD3A513D1F22E368B1B17F1240EE6A9BC74E9E`
- import-audited runner source: `BEF2D6B4CF7EBC7E28EFA68C5FB3C506287B72B096675AB5DA5ACDB83687D548`
- classifier source: `2F82DB17C4917A199C810B98FB5100DCE7E5CA9C822EDB71A51BE0A7430216A2`

Next status: `NO_T7_SIGNAL`; await GPT PRO's decision whether to stop or
specify a new public-state diagnostic. No parent or candidate change is
authorized by this result.

