# Night Stretcher census freeze provenance amendment

## Scope

This is a provenance-only amendment to `STRATEGY_SELECTION.md`.

- Frozen behavior contract SHA-256: `70B0FFD9482BA5E23F5D2200713171810B9C30F250D7762EF23CF7A87C8B8D0F`
- The behavior, implementation boundary, ownership rules, shadow thresholds, fixtures, and fixed760 adoption gates are unchanged.
- The strategy document's older census-document SHA reference is superseded for evidence provenance only. The strategy file itself is not edited.

## Authoritative frozen census

- Census document: `ROOT_NIGHT_STRETCHER_CALLBACK_CENSUS.md`
- Census SHA-256: `FB678439010339062EDAD08D9D0909A4FA8EDA2CB3D2F3DEFD395950C48DFABE`
- Generator SHA-256: `2E676D05412C1647E737EC136E73C0543F86CA09757836D52DA6F8E7FE6DCD08`
- Source manifest SHA-256: `90A512D5C9AE5EAD8DF92F370C32716959EC0929F9465451E7BB0926DBEB5A68`
- Callback rows SHA-256: `136DE7C57BDD4582A84B2F84FA790773CE8463FE6FD67DB4BE005185BD6F1179`
- Summary SHA-256: `3F3AD57FB2A16A502AD43E219018266FC925212ECBFF8FE9059135366BFFB355`

Frozen core facts remain: 186/186 valid Night Stretcher callbacks across 123 replays and both seats; every callback has `minCount=maxCount=1`; legal empty selections are 0; and the prior PLAY census has 168 unique turns. Replay actions are aligned to the preceding observation through the saved next-row action.

## H2 ownership control

Exactly one of the 186 rows has the existing H2 owner:

- episode `88017509`, seat `1`, turn `12`, step `117`;
- historical target: Duraludon `169`;
- formal-parent target: Basic Metal `8#113`;
- owner: `H2_CERTIFIED_LAST_PRIZE_STRETCHER_METAL_BOSS` before and after the parent call.

This row remains an H2 control and must be delegated completely to the formal parent. It cannot count toward the new rule's starts, differences, purpose buckets, or mechanism evidence.

## Supersession rule

For all implementation and evaluation provenance, use the hashes in this amendment and the latest census SHA `FB6784...DFABE`. They supersede the older census SHA embedded in the unchanged strategy document. No behavioral statement or numeric gate in behavior-contract SHA `70B0...B8D0F` is amended.
