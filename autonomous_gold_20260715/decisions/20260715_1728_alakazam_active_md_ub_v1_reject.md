# Decision: reject Alakazam Active-MD Ultra Ball v1

- Decision time: 2026-07-15 17:28:19 +09:00
- Candidate: `historical_silver_alakazam_active_md_ub_v1`
- Final result: `REJECT / RETIRE EXACT IMPLEMENTATION`
- Deployed parent: `historical_silver_kc_lone_nonex_v1`
- Package created: NO
- Kaggle submission: NO
- Daily submission slot consumed: NO

## Bound evidence

- Frozen specification:
  `autonomous_gold_20260715/evaluations/alakazam_active_md_ub_v1/EVALUATION_SPEC.md`
  (`86F40E2800E78B7DAC87C5C03DE6EAD38E2709C877CA93FD41E7B80C3A08DA09`).
- Execution manifest:
  `autonomous_gold_20260715/evaluations/alakazam_active_md_ub_v1/EXECUTION_MANIFEST.md`
  (`9BA3DB8CFA21338A903F60A7E251386FD55D1AD93A57D58A781CFDABBBF22A21`).
- Candidate `main.py`:
  `6A4CF23D1900FBCD4813474FEC61FA786318361A81121FBB0913AC3D48DAC0F7`.
- Root numerical verification:
  `autonomous_gold_20260715/evaluations/alakazam_active_md_ub_v1/ROOT_NUMERICAL_VERIFICATION.md`
  (`DC93D0707834C5C93AAF90F4298996E4893A8DEF6B4235A5C213AC09C932ED2E`).
- Root trace verification:
  `autonomous_gold_20260715/evaluations/alakazam_active_md_ub_v1/ROOT_TRACE_VERIFICATION.md`
  (`5694AB9CF0D28D24BCCDA9EC7DDC19842D5863DC0F7A0DA98C86922ABD5D7970`).
- Independent numerical audit:
  `76F061BB85E41203B7ED3B21073AE8167D5C9BB47DE526D4F879DCE274A5AD8D`.
- Independent reference/fresh trace audit:
  `9DC4B4983B1AC57EADDF877F1951B2EBA185FE85EB909A80D1770FE0E5FC2C21`.
- Independent policy-adjacent trace audit:
  `7B2B9BF26B9691A6C4298ABF14D800512420B0C09A4A61B27DED6C48AAD887D7`.

Root and independent numerical calculations agree with discrepancy count zero.

## Gate disposition

| Gate | Status | Submission-critical evidence |
| ---: | --- | --- |
| 1 | PASS | All schedules, hashes, raw rows, duplicate controls, errors, and historical references reproduce. |
| 2 | PASS | Six first divergences are legal, on-predicate Ultra Ball plays; off-predicate divergences are zero. |
| 3 | PASS | Reference target `112 -> 113`, delta `+1/160`, one gain, zero regressions. |
| 4 | **FAIL** | Fresh target `216 -> 215`, delta `-1/320`, zero gains, one regression. |
| 5 | **FAIL** | Combined target `328 -> 328`, delta zero; paired CI `[-0.0057807301130759145, 0.0057807301130759145]`. |
| 6 | PASS | All six routes realize exact cost, `190` search, Active evolution, three Metal, attack `253`, and same-turn KO; exception counts are zero. |
| 7 | PASS | Policy-adjacent delta `+1/160`, no regression. |
| 8 | PASS | All required non-Alakazam result and step fields are identical. |
| 9 | PASS | Broad panel `520 -> 521`; no opponent regression. |

The broad `+1` is the frozen duplicate of the reference-RMY gain and is not an
additional independent improvement.

## Causal rejection reason

The fresh regression at exact Alakazam p1 seed `2026071729` is caused by the
rule despite complete mechanical realization. It converts an intentionally
expendable one-prize Active Duraludon into a two-prize Archaludon ex to take a
one-prize knockout. The opponent immediately takes two prizes from that ex.
The parent concedes only one prize with the sacrificial Duraludon, later uses
Night Stretcher to recover a backup Duraludon, and survives to opponent
deck-out. The candidate reaches the opponent's final prize with no backup two
turns earlier.

The current trace value `M=3` for reference seed `2026071601`, versus older
documented values 4/5, is recorded but non-decisional: the predicate still
passes and the route still realizes.

## Final Sol-Ultra judgment and boundary

The read-only Sol-Ultra strategy judge issued explicit **REJECT**:

- keep `historical_silver_kc_lone_nonex_v1` deployed;
- retire this exact candidate;
- do not package or submit it;
- do not broaden, retune, patch, or add stateful forcing to it.

The only lesson carried into future independent hypothesis selection is an
evidence constraint: a same-turn knockout must be evaluated together with its
change in prize liability, whether the Active is intentionally expendable,
and whether backup/recovery continuity survives the changed sequence. This
decision does not authorize a follow-on code change.
