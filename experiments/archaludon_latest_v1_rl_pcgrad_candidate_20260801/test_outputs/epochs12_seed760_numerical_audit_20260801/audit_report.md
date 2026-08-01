# Epochs-12 exploratory two-panel numerical audit

## Material Passport

- Origin Skill: academic-research-suite / experiment-agent
- Origin Mode: validate
- Origin Date: 2026-08-01
- Verification Status: ANALYZED (raw calculations and receipts reproduced; simulations were not rerun)
- Version Label: epochs12_validation_v1

## Recommendation

**PASS the supplied seed-760 continuation gate and PASS the separately
precommitted combined-64 gate, mechanically.** All artifact, schedule, runtime,
training, and duplicate checks pass. Seed 760 has positive paired net wins
against both anchors and no negative opponent-seat cell. Across the two disjoint
panels, post is **51-13 (79.6875%)**, versus pre **50-14 (78.125%)** and zero
**49-15 (76.5625%)**, with paired **+1/-0** and **+2/-0** respectively.

This is **CAUTION-level continuation evidence, not strength or promotion
evidence**. The combined effects are only +1.5625 and +3.125 percentage points,
their conservative paired 95% intervals include zero, exact McNemar p-values
are 1.0 and 0.5, and every favorable outcome flip comes from seed 760; the
confirmation panel changes no outcome. The exact Historical Silver primary
anchor remains only **3-5 (37.5%)** combined and is **0-4 at seed 760** in all
arms. Passing supports considering another fresh epochs-12 update under the
exploratory loop; it does not justify checkpoint promotion, Kaggle submission,
or a claim of meaningful strength gain.

## Integrity and policy/player mapping

- The seed-760 spec recomputes to
  `FBFE990E1B4C2EB3FD2179B2F674B7EF9E032B117EF46D1AC075BE49488D1E54`;
  the seed-750 confirmation spec recomputes to
  `7557CB0CB1630080A8610E0FEBFB1BF987CAC314479139A9A4E8E52F7E2C401B`.
- All eight runs have 32 unique manifest keys and 32 unique episode keys. The
  normalized schedules, opponent tables, and population receipts are exact
  within each panel; the two seed sets are disjoint, yielding 64 unique combined
  keys. Every checkpoint, manifest, collection-spec, runtime, dataset, and
  episode byte/SHA256 receipt recomputes exactly.
- The training binding passes: D376 input checkpoint, AF9B rollout manifest,
  4155 dataset, 32 fresh games, 748 PPO rows, 12 ordered epoch reports (0-11),
  no early stop, and 27B5 output checkpoint all match the immutable spec.
- Every arm and duplicate is 32/32 clean: 256/256 clean terminals in total,
  zero action errors, zero exceptions, and zero max-step hits.
- Policy mapping was checked per episode: `seat=0` means agent A/player 0 and a
  win requires `terminal_result==0`; `seat=1` means agent B/player 1 and a win
  requires `terminal_result==1`. Candidate-relative `terminal_reward=+1` was
  cross-checked against that mapping with zero errors.
- Both separately executed post duplicate controls are exact game by game:
  zero outcome, terminal-result, decision-count, or engine-step differences,
  and zero differences across all 3,484 decisions for encoded state/action/effect
  inputs, masks/order, residual/value outputs, sampled actions, final
  probabilities/log-probabilities, and next-state hashes. The raw observation
  hash differs in 729 rows because it includes run-variant non-policy material;
  it is excluded only from that raw field, not from any encoded input or policy
  output.

## Matched outcomes and conservative uncertainty

| Panel | Arm | W-L | Rate |
|---|---|---:|---:|
| seed 760 | zero | 22-10 | 68.7500% |
| seed 760 | pre | 23-9 | 71.8750% |
| seed 760 | post | 24-8 | 75.0000% |
| seed 750 confirmation | zero | 27-5 | 84.3750% |
| seed 750 confirmation | pre | 27-5 | 84.3750% |
| seed 750 confirmation | post | 27-5 | 84.3750% |
| combined | zero | 49-15 | 76.5625% |
| combined | pre | 50-14 | 78.1250% |
| combined | post | 51-13 | 79.6875% |

| Scope/comparison | Gains-losses | Delta | Conservative paired 95% interval | Exact McNemar |
|---|---:|---:|---:|---:|
| seed 760, zero to post | 2-0 | +6.250 pp | [-12.268, +23.071] pp | p=0.5 |
| seed 760, pre to post | 1-0 | +3.125 pp | [-12.758, +18.344] pp | p=1.0 |
| seed 750, zero to post | 0-0 | 0 pp | [-12.798, +12.798] pp | p=1.0 |
| seed 750, pre to post | 0-0 | 0 pp | [-12.798, +12.798] pp | p=1.0 |
| combined, zero to post | 2-0 | +3.125 pp | [-6.355, +12.099] pp | p=0.5 |
| combined, pre to post | 1-0 | +1.5625 pp | [-6.598, +9.561] pp | p=1.0 |

The interval is a conservative Bonferroni-Clopper-Pearson interval for the
paired multinomial gain and loss probabilities. It avoids treating the absence
of observed adverse flips as proof that adverse flips are impossible. These 64
structured fixed keys also reuse seed values across opponents, so the interval
is a sensitivity summary, not iid deployment-population inference.

## Buckets, seats, seeds, and floors

| Opponent (8 games/arm combined) | zero | pre | post | Post delta vs zero / pre |
|---|---:|---:|---:|---:|
| historical_silver | 3-5 | 3-5 | 3-5 | 0 / 0 pp |
| alakazam_public | 7-1 | 7-1 | 7-1 | 0 / 0 pp |
| alakazam_rmy_live | 4-4 | 5-3 | 5-3 | +12.5 / 0 pp |
| marnie_kazuki_live | 7-1 | 7-1 | 8-0 | +12.5 / +12.5 pp |
| mega_lucario_public | 7-1 | 7-1 | 7-1 | 0 / 0 pp |
| starmie_public | 7-1 | 7-1 | 7-1 | 0 / 0 pp |
| dragapult_live | 8-0 | 8-0 | 8-0 | 0 / 0 pp |
| ogerpon_cornerstone_public | 6-2 | 6-2 | 6-2 | 0 / 0 pp |

No opponent or opponent-seat cell regresses. The two zero-to-post gains are
`alakazam_rmy_live|seat0` and `marnie_kazuki_live|seat1`; the sole pre-to-post
gain is `marnie_kazuki_live|seat1`. Each is one game, so the apparent 25- or
50-point small-cell delta is not a stable effect estimate.

| Arm | player 0 / seat 0 | player 1 / seat 1 | Seat gap |
|---|---:|---:|---:|
| zero | 27-5 (84.375%) | 22-10 (68.750%) | 15.625 pp |
| pre | 28-4 (87.500%) | 22-10 (68.750%) | 18.750 pp |
| post | 28-4 (87.500%) | 23-9 (71.875%) | 15.625 pp |

Post seed rates are 12/16 (75.0%) at 731200750, 15/16 (93.75%) at 731200751,
14/16 (87.5%) at 731200760, and 10/16 (62.5%) at 731200761: a **31.25-point
range**. The recurring severe discovery-panel floor is Historical Silver at
0/4 overall and 0/2 in each seat for zero, pre, and post. Combining it with a
3/4 confirmation result raises the displayed anchor rate to 3/8 but does not
show learning: its paired delta remains exactly zero. The combined post
opponent-seat floors are `historical_silver|seat1` and
`alakazam_rmy_live|seat1`, each 1/4 (25%).

## Aligned policy effect

| Scope/comparison | Exact / changed action traces | Aligned PPO rows | Probability rows changed | TV mean / median / max | Argmax changes | Sampled-action changes |
|---|---:|---:|---:|---:|---:|---:|
| seed 760, pre to post | 25 / 7 | 773 | 773 | .002060 / .001664 / .014110 | 0 | 7 |
| seed 760, zero to post | 26 / 6 | 791 | 791 | .003106 / .002555 / .020364 | 0 | 6 |
| seed 750, pre to post | 31 / 1 | 774 | 774 | .002126 / .001838 / .011124 | 0 | 1 |
| seed 750, zero to post | 30 / 2 | 767 | 767 | .003170 / .002686 / .016961 | 0 | 2 |
| combined, pre to post | 56 / 8 | 1,547 | 1,547 | .002093 / .001725 / .014110 | 0 | 8 |
| combined, zero to post | 56 / 8 | 1,558 | 1,558 | .003138 / .002571 / .020364 | 0 | 8 |

The update has an observable stochastic policy effect, but it is slight:
every aligned PPO vector changes numerically, yet no unique argmax changes.
Eight of 64 action traces change versus each anchor, producing only two and one
favorable outcome flips and no adverse flip on this fixed schedule. The
confirmation panel demonstrates policy movement without any outcome movement.

## Raw bindings

| Panel/arm | Raw output path | Checkpoint SHA256 | Manifest SHA256 | Dataset SHA256 |
|---|---|---|---|---|
| 760 zero | `experiments/archaludon_latest_v1_rl_pcgrad_candidate_20260801/test_outputs/epochs12_eval_zero_seed760_20260801` | `24D8A4EACD9D7B699D327D3F2436F4DA21AC79433038E6FA96F9AE0E50F8FB04` | `D04988C9072A51966FE78CEC7B557EF3425F849A84264BF481AFD259C535171D` | `A9E2DB1B46C3B50A75FF8C7AFB6774D3C0F1CF8A942708BBC24BBCEE3FC962C7` |
| 760 pre | `experiments/archaludon_latest_v1_rl_pcgrad_candidate_20260801/test_outputs/epochs12_eval_pre_seed760_20260801` | `D376294BFB405224185828A6BAB1EAE8D17D57972B0A55CE922A700D10AAB5D4` | `A5295A808F2568E8F3FFB2FDF0BD28AAF69773EEEBD2FFB116AA81FD5B5D1F9C` | `14803514F4CC3976DF4B793587E9729FD5018D67ED4649A4DFC10166B1750F37` |
| 760 post | `experiments/archaludon_latest_v1_rl_pcgrad_candidate_20260801/test_outputs/epochs12_eval_post_seed760_20260801` | `27B57A8CE0A9A7862651732C850294E5ED48930563994CF3DE1320A40F7D0302` | `CE94A85FA6294AD96B2581BCDF0940FD837756B3678826BE98CA2752B9F53BBE` | `41E1355123A4A5D1286C7A2C1C51ED76712CFF78C6E66C4E404D85CA6A438398` |
| 760 post duplicate | `experiments/archaludon_latest_v1_rl_pcgrad_candidate_20260801/test_outputs/epochs12_eval_post_seed760_duplicate_20260801` | `27B57A8CE0A9A7862651732C850294E5ED48930563994CF3DE1320A40F7D0302` | `9019AD9FD0E100F1086E7F1C708DE5A6E545AEDD241044F01C1F0AC0D48F2947` | `8A9949CB62953E276DBF0B374B14152FB52F590D9BE95E1C8A9B612D96AC9416` |
| 750 zero | `experiments/archaludon_latest_v1_rl_pcgrad_candidate_20260801/test_outputs/more_training_eval_zero_seed750_20260801` | `24D8A4EACD9D7B699D327D3F2436F4DA21AC79433038E6FA96F9AE0E50F8FB04` | `332E1093654A5A228B9382F1770DEEB37C89BE6B72164ACCC1C422A48584BD8B` | `1ADC94919DB726F21CE40295F09B4A72EE1947B3B764A3C66E726918C073E0BB` |
| 750 pre | `experiments/archaludon_latest_v1_rl_pcgrad_candidate_20260801/test_outputs/more_training_eval_post_seed750_20260801` | `D376294BFB405224185828A6BAB1EAE8D17D57972B0A55CE922A700D10AAB5D4` | `2F6D241FEFBA858611F9A8F440DA3F54122B02E724A1D1C8374BE806E912C5E4` | `6D0EA78C0780EB3E2B5B3858C9CC661EB38706AD179B8E69FAE340001D91589D` |
| 750 post | `experiments/archaludon_latest_v1_rl_pcgrad_candidate_20260801/test_outputs/epochs12_eval_post_seed750_confirmation_20260801` | `27B57A8CE0A9A7862651732C850294E5ED48930563994CF3DE1320A40F7D0302` | `50CCD6406EE5A1E8F3B40B3F477D4F94F4FBD579FBF420FF96CD0B64B6444B45` | `7E0604C693DBD7702535DAE9CC2DC5B2ED737785276231F366AF5758A9A0F142` |
| 750 post duplicate | `experiments/archaludon_latest_v1_rl_pcgrad_candidate_20260801/test_outputs/epochs12_eval_post_seed750_confirmation_duplicate_20260801` | `27B57A8CE0A9A7862651732C850294E5ED48930563994CF3DE1320A40F7D0302` | `713B4C0A01BE2781A16D5DE0D45BA4BE853E640B7D007C7E44CEA5F7A078CB4A` | `C212F99353AF4990C798BAF149FCF80645CC46526F74BB39CC6A41AE6E015E04` |

The opponent population file hashes to
`03BEC83E1259F03F81C7A7191469572AF28890354EF7AA9B7E3EAEC3923DC1C0`.
The reproducible calculation script hashes to
`6AB6621495B94556ECA5035F5AE9D6046AD2876340481A6A12F6D8633121C2DF`;
its calculation output hashes to
`AA62EF8347045B95E4D407449D8F4333E02141FB6592615274480AA9816A4D1C`.

## Gate disposition and assumptions

- Seed-760 artifact/training integrity: **PASS**.
- Seed-760 exact duplicate and runtime safety: **PASS**.
- Seed-760 positive paired net versus zero and pre: **PASS**.
- Seed-760 no negative opponent-seat cell: **PASS**.
- Seed-760 continue-epochs-12 gate: **PASS mechanically**.
- Combined positive paired net, runtime, both duplicates, and no Historical
  Silver regression: **PASS**.
- Precommitted combined-64 gate: **PASS mechanically**.
- Practical/statistical improvement: **not established**; intervals include
  zero, effect is one or two flips, and anchor strength remains poor.
- Promotion/Kaggle validity: **FAIL / explicitly out of scope**.

The statistical fallacy scan covers 11/11 categories. Relevant cautions are the
selected opponent panel (not a population sample), many descriptive subgroup
looks, and the exploratory origin of seed 760. There is no aggregate/subgroup
direction reversal, no attrition, and no causal or deployment-strength claim.
The complete calculation records all assumptions and all 11 checks.
