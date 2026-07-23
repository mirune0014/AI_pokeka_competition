# Final strategy judgment: Alakazam Run Away Draw hit-bound v1 REJECT

- Judgment time: `2026-07-17T03:23:11+09:00`
- Judge: `/root/ptcg_sol_ultra_worker_run_away_final`
  (`gpt-5.6-sol`, Ultra)
- Exact parent: public Best-5 Alakazam
- Candidate: `alakazam_run_away_draw_hit_bound_v1`
- Kaggle/package/Phase-1 authorization: **none**

## Bound evidence

| Artifact | SHA-256 |
| --- | --- |
| v1 strategy decision | `2048CB114F6A4BB36C8F06260CED0BE067F0EBB64C8419117E64BEA8DCF4F100` |
| implementation specification | `B96BE44CF80993CE60578B1A0069D3C8AB7F165A8471C870143917F6A8754589` |
| evaluation specification | `9BE7C8705879CECA48EB35C3CA674F4EDBB28D487282A2601AD05C6C4B8DE8B7` |
| implementation receipt | `DE749AFC71EC759F664A81F00BBE43A3B7F127A97050E5CF5BD0AB07DC50BD11` |
| Phase-0 key ledger | `A6934CE3318DD0F7551464A273900371B2BBD250E796E1F04DFBA2AF1D7CA094` |
| execution manifest | `DBCA315A95E859F39142FFDB9182419B373CCA7CF383CE619CB5522D690A14F5` |
| numerical audit | `526B5E0B5E4AA3E693942333A6F2965232C1DE06BB373916096BFB7550A8205F` |
| case trace analysis | `F4B6504EF0EFF9ECA72D20106844852235F1E43710868CD2EE1C001B1CCA5C09` |
| control trace analysis | `2DB82CC64518BC941E7A0B0424CA5C65EFE88DB12B573F0C1149AB3A997A3B67` |
| exact parent source | `DF4D597F593950B0D0C372F3E0BB26C182C4116648977F15ADBB329A6BA922F4` |
| v1 source | `E3A035D61A144E37F3986F534EF25CA885746A3D4ACBE5BFE636CA7B7C515FAC` |
| byte-identical deck | `7B413177E5077777F2178143839C0155B03B92BBC8B3A6607621A7D43F351141` |

The manifest and raw audit agree on 33 paired schedules, 66 valid commands,
8,439 valid trace rows, exact schedule equality, zero action errors, zero
max-step hits, and no malformed or duplicate result. The root independently
recomputed the submission-critical outcomes from the raw summaries.

## Frozen v1 judgment

**REJECT without exception.**

The targeted branch is real: all 18 loss-derived cases and all 15 controls
reach an exact common prefix and first differ only as legal Bench
Dudunsparce Run Away Draw versus parent Powerful Hand. Every ability draws
three cards and is followed by a same-turn Powerful Hand. The candidate
converts six parent losses and produces a targeted paired net of `+4/33`.

That positive result does not satisfy the frozen conjunctive gate:

| Population | N | Parent wins | Candidate wins | Gains | Regressions |
| --- | ---: | ---: | ---: | ---: | ---: |
| case | 18 | 0 | 6 | 6 | 0 |
| control | 15 | 15 | 13 | 0 | 2 |
| total | 33 | 15 | 19 | 6 | 2 |

Gate 6 required all `15/15` parent-win controls to remain wins. Only `13/15`
remain wins. The two exact-prefix regressions are:

1. fresh Kangaskhan/Crustle, Alakazam p0, seed `2026081712`:
   parent `W`, v1 `L` by deck-out after the non-KO branch;
2. known Starmie, Alakazam p1, seed `2026071590`:
   the selected Dudunsparce carries Lucky Helmet `1156`; parent `W`, v1 `L`.

Because the gate was frozen as conjunctive, the six gains, `+4` paired net,
legal second-copy behavior, and exact three-card draws cannot override those
regressions. The attached-Enriching case is additionally a legal but
non-converting `L -> L` resource-cost branch. Only `30/33` branches retain a
strictly smaller hit bound at the realized attack hand, so v1 also does not
establish an atomic draw-then-attack route.

Do not run broad retention, package, submit, promote, patch in place, or
reinterpret `alakazam_run_away_draw_hit_bound_v1`. Any successor must be a
new isolated hypothesis with a new frozen specification.

