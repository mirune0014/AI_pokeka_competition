# Alakazam Run Away Draw Cost Certificate v2 — Final Decision

Date: 2026-07-17  
Role: `ptcg_sol_ultra_worker` final rule-level judge  
Verdict: **REJECT**

## Authority and frozen inputs

- Broad evaluation spec SHA-256: `0F2D265C9727FBB2CFE1946BF89DCFC130487E55622424576C139011D34E4BF1`
- Broad freeze receipt SHA-256: `C8C7FDE2EF6BA4E03CDECAF42E783C866180A39969A219096002BF0AB782849F`
- Broad execution manifest SHA-256: `1FFC56906F26005BFF024DB9AF5C9890D73F43A1C2F07F0F4B4403E227F51F6E`
- Broad numerical audit SHA-256: `5FE38D2B880ED7D055A0DC7300C04410D95740991EFF5004A6FAAD03B30D4B2D`
- Broad regression analysis SHA-256: `000489A9717B45E27E5C49C4415FA5B0D9F1F050CD221EB354D03695CE827CF9`
- Broad gain analysis SHA-256: `AF2AF37B1491729DE1469C8E07C017C6A0FA1CB540E2821F96F25F5157BD4453`
- Phase-0 decision SHA-256: `C599B2ED5D6BB1003F18A52F04AFA443FC0467782CF66A803D2F7C675ADD0149`
- Phase-0 numerical / eligible / suppressed audits SHA-256: `C4625F94E576AF582CA52882265BBDB3323255CA5B9CDF1092BDD69CBC675BA4`, `FBB96114C530C2017927126427167288EFFAD46303C68FB9EA81B1690C325980`, `117B99A6D6D2788ED2399D3AB5C6DF5F428D6DA936C94BC656A305FD899DD9C4`
- Frozen v2 source SHA-256: `8E61C70D7BC0136E724C6A2283833DF78CDA39508835CBB9A5BEBDE46CA8CE3B`
- Frozen v2 runtime SHA-256: `B90187F961287F66193009CCA89CF8F30DFCC2F6FF00905259622F328C60816D`
- Frozen deck SHA-256: `7B413177E5077777F2178143839C0155B03B92BBC8B3A6607621A7D43F351141`

## Recomputed broad result

The 1,440 paired keys are unique and schedule-equal. Reference changed from `406` to `413` wins (`+7`); new-fresh changed from `413` to `417` (`+4`); combined changed from `819` to `830` (`+11`). There were 12 gains and one regression, with combined seat deltas `P0 +5` and `P1 +6`; all opponent-panel combined deltas were non-negative. The exact sign-test probability is `14/8192 = 0.001708984375`. Frozen Gates 1–7 therefore pass.

## Gate 8 disagreement and resolution

The numerical audit marked Gate 8 PASS because every first change satisfied the predicate implemented in v2. That is a correct syntactic reading of the code, but it is not sufficient for final adoption of the selected strategy hypothesis.

Across all 1,440 pairs there were 46 first divergences. Forty-five Run Away Draw actions actually drew three cards. The sole exception was:

`reference / known / marnie_sota / p1 / seed 2026071583`, first divergence at step 162.

At that public state the deck contained one card, prizes one, and hand six. v2 selected Run Away Draw over the parent's Powerful Hand because `safe_draws` used the winning-line sentinel and the overlay evaluated the fixed `h+3` certificate. The ability could physically draw only one card, so hand size became seven and the Powerful Hand hit bound remained three rather than falling from three to two. A later second ability drew two more cards, but that does not retroactively certify the first action under the selected fixed-three-draw hypothesis.

Thus the gain analyst's semantic FAIL is controlling: v2's public-state predicate admits a branch where its claimed `h+3` cost certificate is false. This is not ordinary post-draw RNG decay; the insufficient capacity was known before the action from public `deckCount == 1`. The branch happened to become a win, but outcome benefit cannot substitute for a coherent interpretable certificate.

## Final authorization

**Reject v2 for adoption.** Do not package it and do not submit it to Kaggle. Preserve all frozen evidence. The rejection is narrowly semantic and does not negate the strong numerical result or Gates 1–7; it requires only the independently selected v3 capacity guard documented separately.
