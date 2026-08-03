# Root cumulative-v2 shadow over episode 88876193

Verification time: 2026-07-30 07:59 JST.

## Frozen inputs

- prior episode CSV:
  `live/55083165/refresh_20260730_0724/submission_55083165_20260730_0724_episodes.csv`,
  SHA-256
  `183D47E34201562C8F58B0812C2A42C4DFFE25056DF3D95B8F9A57C4C2259327`;
- refreshed episode CSV:
  `live/55083165/refresh_20260730_0756/submission_55083165_20260730_0756_episodes.csv`,
  SHA-256
  `750A6192D95BF53CFB33B8A9EBFD263A9E9E4378B9CD0A3FE4CAA88EA09513D9`;
- exact set difference: `{88876193}`;
- replay SHA-256:
  `6402F4863863254A7624227EC6998E16C1A3DB326988D56DB48B21362A99AC9D`;
- target seat: `0`;
- result: loss;
- score movement: `822.850721011959 -> 818.4833755066902`;
- cumulative-v2 source SHA-256:
  `DEE5092B6785DF7A63752C7AAE497051D08DCC62F7723CD9786225A0C5A99DE8`;
- exact historical-Silver source SHA-256:
  `F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E`.

## Results

- replay files: `1`;
- correct-seat callbacks: `50`;
- parent/candidate action differences: `0`;
- rule starts or collisions: `0`;
- attribution: exact historical-Silver on all `50` callbacks;
- invalid actions, action errors, caught/outer exceptions, emergency
  fallbacks, stale/two-owner states, unknown collisions, and max-step hits:
  all `0`.

Runner SHA-256:
`0E633C5917CE2C2A987DA27EA0C4B918EC29DD2F5C261487B17440B0665A8012`.

Summary JSON SHA-256:
`403757614921C0977C9B75938212D818EB37B83E4832703E061CF5D00564E6D2`.

## Decision

This loss does not expose a cumulative-v2 implementation defect because the
candidate would make no action difference from exact historical-Silver. It
does not block the authorized eight-rule exploratory live probe. Any unrelated
strategic weakness remains outside the pre-submit source.
