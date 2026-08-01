# More-training seed-750 exploratory numerical audit

## Recommendation

**FAIL the supplied continuation gate.** The completed 32-key panel does not
establish improvement from the two added fresh PPO updates and does not support
continuing the exact same update configuration. Zero, pre, and post all finish
**27-5 (84.375%)** on exactly the same outcomes. Both post comparisons therefore
have **0 paired gains, 0 paired losses, 0 net wins, and a 0 percentage-point
effect**. This does not reject RL; it only withholds support for repeating this
specific update configuration. The panel is explicitly exploratory and has no
promotion or Kaggle-submission validity.

The added updates did move the policy numerically, but the practical effect is
small on this panel: pre-to-post changes every one of 772 aligned PPO probability
vectors, with mean TV 0.001021, median 0.000788, and maximum 0.004797, but changes
zero unique argmaxes. One aligned sampled action changes, changing one of 32
action traces, without changing any outcome. Positive aggregate strength must
not be inferred from the common 84.375% rate because both anchors achieve the
same result.

## Integrity and duplicate control

- The final bound comparison spec is SHA256
  `70B2CDAE9DA8CC8F0BFFA233E9849409186F52618932F3326C4B00AED9574766`.
- Every arm has 32 unique `(opponent_id, seat, seed)` manifest rows and 32
  unique episode rows. All four key sets (zero, pre, post, post duplicate) equal
  the exact 8-opponent x 2-seat x 2-seed schedule.
- All checkpoint, manifest, collection-spec, runtime-receipt, episode-receipt,
  schedule, and dataset hashes recompute exactly. All 128 episode file byte
  counts and SHA256 receipts match.
- Zero, pre, post, and duplicate each have 32/32 clean terminals, zero action
  errors, zero max-step hits, zero exceptions, and no terminal/player mapping
  error. Zero/pre/post respectively contain 1580/1580/1577 decisions.
- The identical-policy post control has the same 32 outcomes and decision
  counts and exact equality across all 1577 decisions for encoded state vectors,
  action vectors, effect features, behavior action order, final actions, final
  probabilities, engine steps, and next-public-state hashes. Every required
  difference count is zero. There are 337 differing `raw_observation_sha256`
  values; the bound spec excludes this field because it contains run-variant
  material outside the policy input, while all encoded inputs and downstream
  outputs remain exact.

Policy/player mapping was audited explicitly: when `seat=0`, the tested policy
is agent A/player 0 and wins when `terminal_result==0`; when `seat=1`, it is agent
B/player 1 and wins when `terminal_result==1`. Wins and losses below were
recomputed from candidate-relative `terminal_reward` (`+1`/`-1`) and then
cross-checked against that mapping.

## Matched outcomes and uncertainty

| Arm | W-L | Rate | Clean | Errors | Max-step |
|---|---:|---:|---:|---:|---:|
| zero | 27-5 | 84.375% | 32/32 | 0 | 0 |
| pre | 27-5 | 84.375% | 32/32 | 0 | 0 |
| post | 27-5 | 84.375% | 32/32 | 0 | 0 |

| Comparison | Gains-losses | Net / delta | Conservative paired 95% interval | Exact McNemar |
|---|---:|---:|---:|---:|
| zero to post | 0-0 | 0 / 0.00 pp | [-8.94, +8.94] pp | p=1.0 |
| pre to post | 0-0 | 0 / 0.00 pp | [-8.94, +8.94] pp | p=1.0 |

Because all 32 observed paired differences are zero, the empirical paired
bootstrap distribution is degenerate at `[0, 0]`; that describes this fixed
panel but is not a credible generalization interval. The reported conservative
interval instead uses the exact one-sided 95% Clopper-Pearson upper bound on an
unseen discordance probability after 0/32 observed discordances
(`1 - 0.05^(1/32) = 8.9368%`) and the fact that the absolute paired effect cannot
exceed discordance. It assumes the 32 keys are independent/exchangeable; because
this is a structured fixed panel with reused seed values, treat it as a
sensitivity bound, not promotional population inference.

## Seats, seeds, opponents, and floors

All zero-to-post and pre-to-post subgroup deltas are exactly zero.

| Bucket | zero | pre | post | Post delta vs each anchor |
|---|---:|---:|---:|---:|
| player 0 / seat 0 | 15-1 (93.75%) | 15-1 | 15-1 | 0 pp |
| player 1 / seat 1 | 12-4 (75.00%) | 12-4 | 12-4 | 0 pp |
| seed 731200750 | 12-4 (75.00%) | 12-4 | 12-4 | 0 pp |
| seed 731200751 | 15-1 (93.75%) | 15-1 | 15-1 | 0 pp |

The 18.75-point seat gap and 18.75-point seed gap recur identically in all three
arms, so they are schedule sensitivity rather than evidence for or against the
added updates.

| Opponent (4 games/arm) | zero | pre | post | Delta |
|---|---:|---:|---:|---:|
| historical_silver | 3-1 | 3-1 | 3-1 | 0 pp |
| alakazam_public | 3-1 | 3-1 | 3-1 | 0 pp |
| alakazam_rmy_live | 2-2 | 2-2 | 2-2 | 0 pp |
| marnie_kazuki_live | 4-0 | 4-0 | 4-0 | 0 pp |
| mega_lucario_public | 4-0 | 4-0 | 4-0 | 0 pp |
| starmie_public | 4-0 | 4-0 | 4-0 | 0 pp |
| dragapult_live | 4-0 | 4-0 | 4-0 | 0 pp |
| ogerpon_cornerstone_public | 3-1 | 3-1 | 3-1 | 0 pp |

The recurring severe floor hidden by the aggregate is
`alakazam_rmy_live` as player 1/seat 1: **0-2 (0%) in zero, pre, and post**.
At opponent aggregate level the floor is 2-2 (50%), and no opponent is at or
below 25%. These cells are only two and four games respectively, so the floor is
descriptive, but the exact recurrence means the added updates did not touch it.

## Aligned policy effect

Alignment requires the same matched key and decision index plus exact state
vector, action vectors, effect features, behavior action-order hash and option
order, actor-option mask, and legal-option mask. Unaligned downstream states are
excluded from probability and argmax comparisons.

| Comparison | Exact traces | Aligned PPO rows | Probability rows changed | TV mean / median / max | Unique argmax changes | Aligned sampled-action changes |
|---|---:|---:|---:|---:|---:|---:|
| pre to post | 31/32 | 772 | 772 | 0.001021 / 0.000788 / 0.004797 | 0 | 1 |
| zero to post | 31/32 | 772 | 772 | 0.001355 / 0.001139 / 0.005837 | 0 | 1 |

For both comparisons, 1567 decision-index slots have exact encoded alignment;
one episode changes trace and decision count (1580 to 1577, three unmatched
decisions). The observed action change satisfies the no-hard-minimum
"observable policy effect" check, but zero argmax changes, tiny TV, and zero
outcome changes do not establish a practically meaningful improvement.

## Raw bindings

| Arm | Raw output | Checkpoint SHA256 | Manifest SHA256 | Dataset SHA256 |
|---|---|---|---|---|
| zero | `experiments/archaludon_latest_v1_rl_pcgrad_candidate_20260801/test_outputs/more_training_eval_zero_seed750_20260801` | `24D8A4EACD9D7B699D327D3F2436F4DA21AC79433038E6FA96F9AE0E50F8FB04` | `332E1093654A5A228B9382F1770DEEB37C89BE6B72164ACCC1C422A48584BD8B` | `1ADC94919DB726F21CE40295F09B4A72EE1947B3B764A3C66E726918C073E0BB` |
| pre | `experiments/archaludon_latest_v1_rl_pcgrad_candidate_20260801/test_outputs/more_training_eval_pre_seed750_20260801` | `F87587785CF1C47E1399C9FEC761346341C7D9BDB47F1EBA778AD9FA5970912E` | `B3C8F2D8A95F6F62B77C6AF624E06D932053967AD3425C149DB13A78B0896131` | `8240BD344A9318E32874F35CB4DCDA453389B80D4713215E211C20FBCE984552` |
| post | `experiments/archaludon_latest_v1_rl_pcgrad_candidate_20260801/test_outputs/more_training_eval_post_seed750_20260801` | `D376294BFB405224185828A6BAB1EAE8D17D57972B0A55CE922A700D10AAB5D4` | `2F6D241FEFBA858611F9A8F440DA3F54122B02E724A1D1C8374BE806E912C5E4` | `6D0EA78C0780EB3E2B5B3858C9CC661EB38706AD179B8E69FAE340001D91589D` |
| post duplicate | `experiments/archaludon_latest_v1_rl_pcgrad_candidate_20260801/test_outputs/more_training_eval_post_seed750_duplicate_20260801` | `D376294BFB405224185828A6BAB1EAE8D17D57972B0A55CE922A700D10AAB5D4` | `78AE6BD7D31F8516655549015BA1335CE80920BEEC2F632E063C353F63617DB1` | `C7614BE0661C4E271B22AAA4DC265DA0C6440BDB364E5078F45AAD4FAD303DC9` |

The opponent population file is SHA256
`03BEC83E1259F03F81C7A7191469572AF28890354EF7AA9B7E3EAEC3923DC1C0`.
The reproducible calculation script is SHA256
`267942C45C111A748EEAA95281773AC5FD7BDD9D8CC1CB32E6FA7FD7F7C22E8D`;
its compact calculation output is SHA256
`24B491AEDA148828B923ABF4E8DB72FFA0D2E160D5D93F152F9E272A16261445`.

## Gate disposition

- Artifact integrity: **PASS**.
- Exact identical-policy duplicate control: **PASS**.
- Runtime safety: **PASS**.
- Positive post paired net versus both zero and pre: **FAIL** (0 versus each).
- No seat or opponent paired-net regression: **PASS** (every delta is 0).
- Observable policy effect, with no precommitted hard minimum: **PASS**, but
  practically slight (one sampled action, zero argmaxes, zero outcomes).
- Continue the exact configuration: **FAIL / unsupported by this panel**.
- Promotion strength: **not evaluated; explicitly invalid for promotion**.
