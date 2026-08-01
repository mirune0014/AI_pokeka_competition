# Phase 1 locked-split PPO v1 result

## Purpose

Run the real PPO trainer once without allowing the fixed 830-row batch to score
itself. Whole trajectories, rather than individual decisions, are assigned to
training or validation.

## Immutable inputs

- Input checkpoint SHA-256: `24D8A4EACD9D7B699D327D3F2436F4DA21AC79433038E6FA96F9AE0E50F8FB04`
- Rollout manifest SHA-256: `30BF22BE56E73E8790A40135DD78080217FFAB7598D9646887FD8742D0FCF393`
- Dataset SHA-256: `3D714FC248B597ADD412B1D9B4BAD60DDF6BDEB3DFA652264D763D7A843AC41B`
- Split spec SHA-256: `67435BD52C0B6F0693A33C1855AC2BC7B5C212D444E19ADE453DE50BFCB8FE23`
- Split selection digest: `001FDDF47C1B38C12FA053D4D1B58728294EFF7B150737274FCA80D57C179BBE`

The split contains 24 training trajectories / 618 PPO rows and 8 validation
trajectories / 212 PPO rows. Validation has one trajectory from each opponent,
four from each seat, four from each seed, and a 6-win / 2-loss outcome mix.
GAE is computed inside each whole trajectory. Training advantages are normalized
from training rows only; validation uses its own normalization and is evaluated
under `torch.no_grad()`.

## Execution

- Device: CPU
- PPO epochs: 4
- Games generated: 0
- Wall time: 13.5 seconds
- Early stop or rollback: no

## Held-out validation result

| Metric | Before training | After epoch 4 | Delta |
|---|---:|---:|---:|
| Total loss | 0.138532773 | 0.118092962 | -0.020439811 |
| Policy loss | -0.000000011 | -0.000127490 | -0.000127480 |
| Value loss | 0.284660667 | 0.244026959 | -0.040633708 |
| Anchor KL | 0 | 0.000005082 | +0.000005082 |
| PPO ratio minimum | 0.999999524 | 0.985678256 | -0.014321268 |
| PPO ratio maximum | 1.000000477 | 1.013959169 | +0.013958693 |

Validation total loss decreased by about 14.8%, and validation value loss
decreased by about 14.3%. The policy term also moved in the favorable direction,
while the final KL and probability ratios remained conservative.

## Output and interpretation

- Reload-verified checkpoint: `test_outputs/phase1_split_ppo_v1/trained.pt`
- Checkpoint SHA-256: `DFCAC3270EFE9CDF34A63E89900D27FC37DEB6D9494B5925E8B35774D2ABA44E`
- Reloaded optimizer state entries: 14

This is a successful end-to-end vanilla PPO update and a usable checkpoint for
fresh rollout collection. It is not yet evidence of stronger game play: no new
games were generated, and the held-out trajectories still come from the same
fixed collection. The next step is to collect new on-policy games from this
checkpoint, then update from those fresh trajectories.
