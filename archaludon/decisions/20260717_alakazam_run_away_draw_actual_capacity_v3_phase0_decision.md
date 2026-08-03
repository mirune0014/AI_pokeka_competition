# Alakazam Run Away Draw Actual Capacity v3 — Phase-0 Decision

Date: 2026-07-17  
Role: `ptcg_sol_ultra_worker` Phase-0 judge  
Verdict: **PASS**

## Frozen authority

- Evaluation spec: `0D798B47FDB45D60E99726C7F8CD0FED5A8295F050B527AB868AFCE0EC3524E3`
- Spec freeze receipt: `AB255C9DDF315F45C570D3BAD6FFE35A7C23C5DC278CE15483FF074D555ACE0F`
- Implementation spec / receipt: `56D04BED436DEB46C90211BD31A1CC0022DF472C2B83210D7BFBBD0E3213A201` / `4FA9295EEED501EAF621DF6B887993DB6F53C0E927EFF2AF875BAAAD866EC00E`
- Phase-0 execution manifest: `898E3B556F6612D45E5293C5B8DB524F5F33DB56A426A367411B624CB5FCFED0`
- Independent numerical audit: `456C1EE46F76BEB985CC7F5EA373794D358B030E9366D933BC528BEAC7F06EFD`
- v2 / v3 source: `8E61C70D7BC0136E724C6A2283833DF78CDA39508835CBB9A5BEBDE46CA8CE3B` / `5F8F6578BF98BC285BB468FAD26969A22EDA96378F8E3AE35F134EA70EB91830`
- v3 runtime / deck: `BDEA6ABD3D0B8BB252C0DDA27B3E095432EACD1EFC45E64D96BE1F7FF05A7170` / `7B413177E5077777F2178143839C0155B03B92BBC8B3A6607621A7D43F351141`

## Independent gate verification

All 34 paired keys and 68 policy outputs are unique and complete. All 68 commands exited zero; summaries and traces are valid, with zero action errors, max-step hits, schedule faults, retries, missing files, or frozen-input mismatches.

For the inherited 33 keys, seat-aware recomputation gives case `0→6`, controls `15→15`, and total `15→21`: six gains and zero regressions. All 33 current parent traces byte-match the frozen v2 parent traces, and all 33 v3 traces byte-match the frozen v2 candidate traces; both mismatch counts are zero. Consequently the 28 allowed overlay branches retain the already frozen exact-three-draw and same-turn Powerful Hand evidence, while all 15 controls remain wins.

On `capacity/known/marnie_sota/p1/2026071583`, rerun parent and v3 are identical 168-step p1 losses. Their complete traces are byte-identical at SHA-256 `EF8FAC380265AFF8C5E757592E3BDD19C13A7BB812F771B98A1B00E15A47BA36`; normalizing only the top-level game index reproduces the frozen parent trace SHA-256 `0147334FCDBC4F1A646F9BF37ED1BE813839202CD3CF44BA839D62B0837208C2`. At step 162 the public state is deck one and hand six, and v3 selects option index 2, Powerful Hand attack 1072. There is no later divergence.

The direct v2-to-v3 source diff is exactly one insertion and zero deletions:

```python
and deck_count >= 3
```

It is the selected public, deterministic, stateless capacity guard; no opponent, seat, seed, replay, deck, helper, score, or ordering exception was introduced. Every frozen Phase-0 gate therefore passes conjunctively.

## Authorization boundary

Authorize **only** the exact frozen 1,440-key v3 broad rerun in `EVALUATION_SPEC.md`: 720 reference keys and 720 new-fresh keys, both seats, the frozen nine opponents, seeds, runner, engine, options, schema, and destinations. V3 must execute on every candidate key; v2 candidate results cannot substitute. Parent rows may be reused only after hash and schedule-equality verification. Recompute every unchanged broad gate and review every changed trace before a fresh final Sol-Ultra judgment.

This PASS does not authorize another source edit, adoption, packaging, or a Kaggle write.
