# Phase-0 strategy judgment: Alakazam Run Away Draw cost certificate v2 PASS

- Judgment time: `2026-07-17T04:11:12+09:00`
- Judge: `/root/ptcg_sol_ultra_worker_run_away_final`
  (`gpt-5.6-sol`, Ultra)
- Candidate: `alakazam_run_away_draw_cost_certificate_v2`
- Exact comparison parent: public Best-5 Alakazam
- Decision: **PASS Phase 0**
- Authorization: **only the separately frozen broad-retention evaluation**
- Final adoption/package/Kaggle authorization: **none**

## Bound artifacts

All listed files were read in full and rehashed before judgment.

| Artifact | SHA-256 |
| --- | --- |
| v2 strategy selection | `5078826E2A5D170B59F293400CC87B5B46499E8BA041C3DB2A71593F233F2D47` |
| v1 final rejection | `478D5D0E7506AE70FB6883BC01D96106960894FDD6C599197C92D8BBE2A86F7A` |
| v2 evaluation specification | `A9AA00E468DF4A43ADBDCDDB94EB0DD6732C760C9420BABBC8D547D731351A16` |
| v2 Phase-0 ledger | `1EEE15EDDE4B37C72700FC01F0D1ABA2E195DF6A3AD21DF17C66805A248DB8F5` |
| implementation receipt | `BC19D9CA7FBF8A03E6CEA2EAADA3487BE551FB0EFE5F30DE800FA9D33A4DAC22` |
| execution manifest | `182533829C8D19520BFB6B0AD455145BE4C097DFA258147A3898AC2D87770AF4` |
| numerical audit | `C4625F94E576AF582CA52882265BBDB3323255CA5B9CDF1092BDD69CBC675BA4` |
| eligible trace analysis | `FBB96114C530C2017927126427167288EFFAD46303C68FB9EA81B1690C325980` |
| suppressed trace analysis | `117B99A6D6D2788ED2399D3AB5C6DF5F428D6DA936C94BC656A305FD899DD9C4` |
| candidate source/runtime | `8E61C70D7BC0136E724C6A2283833DF78CDA39508835CBB9A5BEBDE46CA8CE3B` / `B90187F961287F66193009CCA89CF8F30DFCC2F6FF00905259622F328C60816D` |
| parent/candidate deck | `7B413177E5077777F2178143839C0155B03B92BBC8B3A6607621A7D43F351141` |
| v1 numerical/case/control audits | `526B5E0B5E4AA3E693942333A6F2965232C1DE06BB373916096BFB7550A8205F` / `F4B6504EF0EFF9ECA72D20106844852235F1E43710868CD2EE1C001B1CCA5C09` / `2DB82CC64518BC941E7A0B0424CA5C65EFE88DB12B573F0C1149AB3A997A3B67` |

The v1-to-v2 source diff contains only the pure public cost-certificate
helper and its guard around the already-audited score-1550 overlay. It adds no
state, pending action, opponent identity, target-ID table, learned component,
or other score change. The hypothesis remains coherent and interpretable:
non-immediate extra draw is accepted only for an unattached source against a
publicly multi-Prize target; attached or at-most-one-Prize cost requires a
theoretical `h+3` immediate KO.

## Independent raw verification

I recomputed the critical facts from the raw summaries and JSONL traces rather
than accepting the evaluator reports as authority.

- ledger: 33 rows, 33 unique keys, 18 cases, 15 controls, 28 eligible, five
  suppressed; key set exactly matches the frozen v1 Phase-0 set;
- outcomes: parent `15/33`, v2 `21/33`; six gains, zero regressions;
- controls: parent `15/15`, v2 `15/15`;
- all six gains are exactly the frozen six v1 gains;
- all 28 eligible v2 trace files are byte-identical to their frozen v1
  candidate traces;
- all five suppressed v2 traces are byte-identical to their exact parent
  traces through terminal;
- every eligible parent-v2 prefix is identical until the ledger step, where
  the only semantic difference is legal Bench Dudunsparce versus legal
  Powerful Hand;
- all 28 branches independently satisfy the strict integer hit-bound rule and
  public certificate: 11 are cost-requiring immediate-KO states and 17 are
  clean-source/multi-Prize states;
- all 28 ability resolutions have exactly three immediate draw logs and hand
  `h+3`, followed by Powerful Hand in the same public turn;
- coverage is exactly 16/18 cases and 12/15 controls, both blocks, both seats,
  eight opponents, and 24 distinct `(block, seat, seed)` groups;
- the five suppressions independently reproduce the two one-Prize non-KO
  controls, one one-Prize non-KO case, and two attached non-KO states; both v1
  control regressions return to their parent wins;
- raw output validity is 66 summaries and 66 traces, 8,420 trace rows, zero
  action errors, zero max-step hits, zero invalid/unstarted rows, and no
  missing, unexpected, or duplicate policy key.

The raw-tree digests independently reproduce the manifest:

| Tree | Files | Bytes | Rows | SHA-256 |
| --- | ---: | ---: | ---: | --- |
| summaries | 66 | 99,702 | 66 | `846876D5028BEAA5349150F95EDFA1EA527E420DCCFE3B5F1F53B3E42CD94D25` |
| traces | 66 | 16,866,765 | 8,420 | `2B07F8F13902DF5C5557AC0F454777B59F334677F28444A63A22ED85C30A043D` |
| all raw | 132 | 16,966,467 | 8,486 | `4B11FF393B594B572DD20360FC0F3A86B51EF2644652C536522A596ECFAB345A` |

## Conjunctive gate judgment

| Gate | Judgment | Reason |
| ---: | --- | --- |
| 1 | **PASS** | bound receipt has compile/import, legal identical deck, deterministic focused checks, and both-seat smoke; execution has exact 33 pairs, 66 zero exits, and no faults |
| 2 | **PASS** | all 28 eligible first divergences are the exact legal overlay; complete trajectories and results equal v1 |
| 3 | **PASS** | all five suppressed states choose parent Powerful Hand and remain parent-identical with no later divergence |
| 4 | **PASS** | 28/28 draw exactly three, attack same turn, and satisfy both strict hit-bound and cost certificate |
| 5 | **PASS** | exact 16 case and 12 control branch coverage across the required blocks, seats, opponents, and groups |
| 6 | **PASS** | all 15 parent-win controls, immediate KOs, ready attackers, and pre-branch public states are preserved |
| 7 | **PASS** | all six frozen gains remain wins; case `6/18`, control `15/15`, regressions `0`, paired net `+6/33` |
| 8 | **PASS** | all divergences, five suppressions, six result changes, four attached opportunities, and three realized-hand-decay states were inspected without an atomic-route claim |

Every frozen Phase-0 gate therefore passes. There is no exception, relaxed
threshold, or post-hoc repair in this judgment.

## Realized-hand caveat

The three disclosed decay states remain:

- fresh Mega Lucario p1 `2026081720`: bound `3 -> 2 -> 3`;
- known OSEL p0 `2026071589`: bound `2 -> 1 -> 2`;
- known OSEL p1 `2026071581`: bound `2 -> 1 -> 2`.

They do not invalidate the frozen v2 hypothesis because it is explicitly a
stateless public pre-action certificate, not an atomic two-action commitment.
All three are case losses, none is counted among the six gains, and the
required qualitative audit discloses rather than hides them. They do limit
the claim: Phase 0 proves correct guarded activation and targeted retention,
not that every draw produces a realized lower attack bound. Broad evaluation
must determine whether this non-atomic behavior remains beneficial across
unselected seeds, seats, and matchups.

## Exact next-step boundary

**Authorize only broad retention under the already frozen conditional design.**
The root may now freeze a separate broad-retention execution manifest and
delegate deterministic execution of:

1. the 720-key reference schedule on known `2026071581..2026071600` and
   fresh `2026081701..2026081720`; and
2. the 720-key new-fresh schedule on collision-free
   `2026091701..2026091740`.

Candidate source, runtime, deck, parent, opponents, engine, and checked runner
must remain frozen. The broad run must be followed by an independent
Sol-Ultra numerical audit, root recomputation, required regression/gain trace
review, and a new final Sol-Ultra adoption judgment against every frozen
threshold.

This decision does **not** authorize a source edit, another Phase-0 guard,
packaging, submission, Kaggle write, or final adoption. The targeted `21/33`
population is deliberately selected and is not a broad or live win-rate
estimate.

