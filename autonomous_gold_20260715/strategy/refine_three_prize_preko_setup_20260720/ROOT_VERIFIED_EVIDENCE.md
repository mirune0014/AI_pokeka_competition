# Root-verified evidence for the next three-prize KO rule

Frozen by root on 2026-07-20 before the next strategy judgment. This packet
does not authorize implementation or a Kaggle write.

## Live state

- Current submission: `54841997`, exact submitted source parent
  `alakazam_exposed_dudunsparce_run_away_ready_alakazam_ko_transaction_v1`,
  SHA-256 `CB52F1737417EAEEAEF226CFF79ABD4FA58119E3F2AF1D448DFBE5D68722E213`.
- Authenticated CLI at 2026-07-20 13:00 JST: `COMPLETE`, public score `654.3`.
- Current UTC day has one submission, so four of five slots remain.
- The 13:00 episode refresh contains 42 unique rows; the prior 22-ID set is an
  exact subset and the set difference is 20 IDs:
  `86998420,86998974,86999503,87000036,87000569,87001091,87001670,87002204,87002733,87003272,87003809,87004339,87004875,87005308,87005452,87006016,87006555,87007126,87008303,87008841`.
- Root-recomputed current episode CSV SHA-256:
  `C0F62E2247A5FAE99CFFE61CA4283E74FDFBE2E1C40DF8D847EB86E95A92DD57`.
  The low-cost collector had reported an earlier transient hash
  `30D1D688...A5C8`; this disagreed after its final CSV rerun and is explicitly
  rejected rather than silently repaired. Nineteen new replay files are
  nonempty; `87005452` is zero bytes and is not usable evidence.
- These 20 newly listed episodes are replacement/monitoring context only. They
  are not causal inputs to the rule selection below.

## Broad v1 result

Candidate `alakazam_certified_active_three_prize_powerful_hand_ko_v1` is an
isolated sibling of the submitted parent, source SHA-256
`7C06F05A27ADB8B1B5312F8C8DC1E5728C106F0E9BE79CF4F4A517791A7343BB`.

Implementation evidence:

- focused 42-check result:
  `3D5814290691B0B63DABF007775E4CD55349A6B472E1CADF8670C55C6BD72EB4`
- 9,266-callback replay shadow with 63 unique certified differences:
  `B0B1E14F3C7091BC2EA7F6CB20F9BB5F09F0D13135F9FED0B9A590BA1014860D`
- root-recorded Sol-Ultra qualitative audit:
  `85696595D2D080CF62B64F9D703E6DE6023D5B1437DBE0163C20FFA879E0B658`

Fixed compact-72 evidence:

- freeze: `CBA41855B0BD6F6114ECB03AFB3163ECB90079373754C28FAD71C03BB372C3C9`
- ledger: `6239D2B8899CCE7D5E6D43E15DC2550F7D09E45CBEF2C2DAE7460640B8F51D64`
- completion: `6B8DD0D3721C2DAA33A4716F51D2E4D897C2745DA5D215E8C986949FFECD4871`
- root recompute: `74D2CA1135A691BD9BAE6E2B4F972F147659C7326C33626A2D2EC7111AB9ADAD`
- independent numerical report:
  `108A0A4D2FC230225D66F87DF29D4D3FAEB4CA5B5F8DFA2432870E97F8EACCAF`
- independent machine result:
  `D6F83EE9E9D8D1230344047F306DF575FFDDA1BA31B0A915D4D963FCBECE5A28`

Root and the independent Sol-Ultra evaluator agree exactly: baseline and
candidate are 38/72 overall, 20/36 p0, 18/36 p1; gains zero, regressions zero;
all nine opponent floors unchanged; candidate duplicate identity 72/72; all
216 commands exit zero with zero action errors, max-step hits, schedule faults,
or trace mismatches. This is numerical retention only, not improvement.

## Causal first-change audit

The 63 shadow differences collapse to ten first changed episode/seat paths;
the other 53 are later recorded callbacks after an earlier counterfactual
attack. Every public attack/HP/prize/protection certificate is syntactically
true. Sol-Ultra rejected broad v1 because seven first changes suppress useful,
deterministic setup that preserves the same three-prize KO.

| First change | Parent route | Exact judgment |
| --- | --- | --- |
| `86991375/53/s1` | Dunsparce -> Dudunsparce; 14 cards still KO 280 HP, then Run Away Draw raises hand to 17. | allow setup, then lock KO |
| `86968875/97/s0` | Dunsparce -> Dudunsparce; 19 cards still KO 340 HP, then draw three. | allow setup, then lock KO |
| `86969947/60/s1` | Dunsparce -> Dudunsparce; public deck 18 guarantees draw three and restores lethal into 340 HP. | allow setup, then lock KO |
| `86972084/130/s1` | Abra -> Kadabra; 18 cards still KO 80 HP and the on-evolve Psychic Draw draws two. | allow setup, then lock KO |
| `86974207/77/s0` | Lucky Helmet attach drops exact 380 damage to 360 into 380 HP. | attack now |
| `86976336/85/s1` | Playing Abra drops exact 280 damage to 260 into 280 HP. | attack now |
| `86981695/121/s0` | Night Stretcher has a visible recovery target and is hand-neutral before the same 40-HP KO. | allow recovery, then lock KO |
| `86898285/57/s0` | Enriching-Energy Dunsparce -> Dudunsparce -> Run Away Draw raises hand 15 to 17 and frees bench. | allow setup, then lock KO |
| `86901033/155/s1` | Playing Dunsparce drops exact 440 damage to 420; three prizes end the game. | attack now |
| `86909242/107/s0` | Dunsparce -> Dudunsparce; 14 cards still KO 60 HP, then draw three. | allow setup, then lock KO |

The original `86981695/138` Boss miss is later counterfactual evidence if Night
Stretcher is preempted at step 121. A corrected policy must allow the exact
Night Stretcher recovery and then prevent the subsequent Boss from switching
away the already lethal three-prize Active.

## Decision requested from the strategy judge

1. Issue the final adopt/reject judgment for broad v1 using both the numerical
   PASS and qualitative FAIL.
2. Select exactly one coherent replacement rule from the exact submitted
   parent, not by stacking broad v1.
3. Prefer a multi-step public transaction if it can be made fail-closed:
   allow an exact Dudunsparce evolution/Run Away Draw, Kadabra on-evolve
   Psychic Draw, or Night Stretcher recovery only when its public post-route
   hand lower bound retains the same three-prize KO, then lock the unique
   Powerful Hand attack against the unchanged target. Attack immediately when
   the parent's exact hand-consuming action crosses below lethal, when the KO
   takes all remaining prizes, or when exact Boss would switch away the lethal
   Active.
4. If that unified transaction is too broad for one safe candidate, choose the
   narrowest mechanism-complete subset and explain why. Do not key on replay,
   team, opponent policy, or target card name; public card identities used to
   execute a real deterministic transaction are allowed.
5. Specify exact positives, negatives, latches, state restoration, duplicate
   behavior, hidden-information boundaries, and the minimum fixed/live-shadow
   gate for the Fast implementation worker.
