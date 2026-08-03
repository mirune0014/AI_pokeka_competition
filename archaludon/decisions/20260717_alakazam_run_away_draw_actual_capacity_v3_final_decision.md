# Alakazam Run Away Draw actual capacity v3 — final decision

- Date: 2026-07-17 (JST)
- Role: dedicated read-only Sol-Ultra strategy judge
- Verdict: **ACCEPT**
- Adoption: **freeze v3 as the next Alakazam strength parent**

## Frozen authority

| Artifact | SHA-256 |
| --- | --- |
| v3 strategy selection | `C1C5373420B5678A2D08F12F9590813A344F446D75DF8DF2CDE24B897EE9EE02` |
| implementation specification / receipt | `56D04BED436DEB46C90211BD31A1CC0022DF472C2B83210D7BFBBD0E3213A201` / `4FA9295EEED501EAF621DF6B887993DB6F53C0E927EFF2AF875BAAAD866EC00E` |
| evaluation specification / freeze receipt | `0D798B47FDB45D60E99726C7F8CD0FED5A8295F050B527AB868AFCE0EC3524E3` / `AB255C9DDF315F45C570D3BAD6FFE35A7C23C5DC278CE15483FF074D555ACE0F` |
| Phase-0 manifest / numerical audit / decision | `898E3B556F6612D45E5293C5B8DB524F5F33DB56A426A367411B624CB5FCFED0` / `456C1EE46F76BEB985CC7F5EA373794D358B030E9366D933BC528BEAC7F06EFD` / `93CA925D96E2336EFEC403E2A84CE5A960428DB29C9B9E4E88DE3FEF8FAD4B98` |
| broad execution freeze / manifest | `846A702B6857ED04CF6C135D2E0020AE3329D69C7D3E30AA4F9B31D37FBD1DDD` / `8C3CB202A34F336067E640531FEE017846AEDF488FE6A8F463FE30951798040E` |
| broad numerical / gain / regression audits | `05282733F5C48E4873B929A6D689CD1E14DE22E8AF7D01183B42CA34B08C066C` / `CE940C7DFCF3393A9250AB8421ACFA3986B7E44424C362508E92B305C91D7577` / `9F41390A4BF85C2E066EFB502C78709161E85CB11D50335A0CC28631ADDB3C8B` |
| v2 final rejection | `6459D260D1B1E43988F587C6C9130F24069E5999640897D1E6F7AA3D275348EA` |
| exact public Best-5 audit spec / numerical evidence | `281E53EDEAED74CC2B78A543904AFCAD1744B674072EC007E08A138DE07CE308` / `71FBDEB3D864E1B39243105CA4D0025CC2F662AA47E9C72B6BD4672B9E6970C4` |
| public Best-5 source / runtime / deck | `DF4D597F593950B0D0C372F3E0BB26C182C4116648977F15ADBB329A6BA922F4` / `D37DBBE7933F939266D1D1DEEFEEC666CF908A910F56539AFF37936E30CBCBA9` / `7B413177E5077777F2178143839C0155B03B92BBC8B3A6607621A7D43F351141` |
| frozen v3 source / runtime / deck | `5F8F6578BF98BC285BB468FAD26969A22EDA96378F8E3AE35F134EA70EB91830` / `BDEA6ABD3D0B8BB252C0DDA27B3E095432EACD1EFC45E64D96BE1F7FF05A7170` / `7B413177E5077777F2178143839C0155B03B92BBC8B3A6607621A7D43F351141` |

## Conjunctive gate judgment

The exact 1,440-key schedule is complete and equal for parent, v2, and v3. All 54 v3 broad commands exited zero without retry; raw faults, action errors, and max-step hits are zero. The root independently reproduced the raw-tree digest and all submission-critical counts, so there is no numerical or evidence discrepancy.

Seat-aware wins are public Best-5 parent `819/1440`, rejected v2 `830/1440`, and v3 `829/1440`. V3 retains `412/720` versus parent `406/720` in reference (`+6`), `417/720` versus `413/720` in new-fresh (`+4`), and combined `+10`, with 11 gains, one regression, and exact one-sided sign tail `13/4096 = 0.003173828125`. Reference known/fresh deltas are `+1/+5`; reference p0/p1 are `+3/+3`; new-fresh p0/p1 are `+2/+2`; combined p0/p1 are `+5/+5`. Thus the absolute reference gate and every block, panel, and seat floor pass.

Historical-Silver is flat in both panels (`29 -> 29`, `31 -> 31`). Every combined opponent delta is nonnegative, including flat floors for Historical-Silver, Mega Lucario, Dragapult, and Alakazam Rmy. All 15 frozen controls remain wins. Absolute strength and adjacent-matchup retention therefore pass together; the result is not supported only by one loss bucket or one opponent.

Isolation is exact. V3 byte-matches v2 on 1,439 complete traces and normalized results. On the sole excluded key, `reference/known/marnie_sota/p1/2026071583`, v3 byte-matches the public Best-5 parent instead. The v2-to-v3 behavioral source diff is exactly the selected public, deterministic, stateless conjunct `deck_count >= 3`; the deck is unchanged.

The semantic rejection that controlled v2 is repaired rather than hidden by its favorable terminal result. The rejected key has deck one and can draw only one card, so v3 correctly declines a fixed `h+3` certificate and restores the parent's Powerful Hand action. Across all 45 retained first divergences, public deck count is at least seven, the first Run Away Draw resolves exactly three draws, both hit-bound and source/target-cost certificates hold, and a same-turn Powerful Hand follows. Phase 0 independently retained all six target gains and all 15 controls while reverting the short-capacity anomaly exactly.

## Residual risk and why it does not reject v3

The sole regression remains `new_fresh/starmie/p1/2026091719`. Its branch is predicate-valid and draws exactly three, but the freed Bench slot is filled by a 50-HP Abra under visible Jetting Blow pressure; the extra exposed Prize removes the turn on which a backup Alakazam would otherwise finish. This is a real public prize-exchange weakness, not a defect introduced by the capacity guard. It is bounded by one regression, a flat new-fresh Starmie aggregate, a positive combined Starmie floor (`+3`), and the passing both-seat and population floors.

The rule is not an atomic multi-action plan. Only 9/45 attacks are the next trace action; 36/45 have intervening actions. Of 44 unchanged-target branches, 38 preserve the predicted realized hit reduction, six spend enough cards to lose it, and one further branch changes target. Only 18/45 changed-turn attacks KO. Run Away Draw also changes deck order and later RNG consumption. These limits prohibit treating later terminal outcomes as causal action labels, but they do not falsify the frozen public first-action certificate or any conjunctive retention gate.

## Final authorization boundary

**Authorize the root to freeze and adopt this exact v3 source/runtime/deck as the next Alakazam strength parent, package it unchanged, and use one locally justified live Kaggle submission.** The submission authorization is conditional on a fresh Kaggle quota, score, and genuinely-new-public-episode refresh, followed by frozen-file checks, compile/import, legal 60-card validation, deterministic action validity, and packaged both-seat smoke with zero known-broken behavior. The root retains the final external write and must record the refreshed state, package hashes, row totals, schedule equality, errors, hypothesis, target matchups, and this decision.

This decision does **not** authorize a source patch before the adopted artifact is frozen, does not authorize a claim that Alakazam is already live Bronze, and does not authorize interpreting later seeded RNG divergence as causal proof. V2 remains rejected; only the semantically corrected v3 is adopted.

## Exactly one next rule direction (investigation only)

Investigate a **public two-turn fragile-Bench prize-clock guard after Run Away Draw**: when the post-draw hand offers a low-HP one-Prize Basic and the visible opposing attack can take it with Bench damage, decline benching it unless that placement publicly creates an H1-ready successor or strictly advances the earliest Prize-taking turn. This single direction targets the Starmie failure as a multi-step `draw -> bench -> opponent spread -> successor/prize clock` route using only current public state; it is not selected for implementation by this decision.
