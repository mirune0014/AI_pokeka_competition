# Root cumulative-v2 shadow over episode 88874389

Verification time: 2026-07-30 07:24 JST.

## Frozen inputs

- prior episode CSV:
  `live/55083165/refresh_20260730_prewrite_latest/prewrite_20260730_episodes.csv`,
  SHA-256
  `A409B4B47305FEDEDFF6A3F02CFFF3988F7AE3432873E1FC3161857BFA836CA7`;
- refreshed episode CSV:
  `live/55083165/refresh_20260730_0724/submission_55083165_20260730_0724_episodes.csv`,
  SHA-256
  `183D47E34201562C8F58B0812C2A42C4DFFE25056DF3D95B8F9A57C4C2259327`;
- exact set difference: `{88874389}`;
- replay SHA-256:
  `A71FAEC94377FA5C576CB3BBBF63E5209D69C96F256B59960CAA74FADF14EF14`;
- submitted Hero source seat: `1`;
- result: loss;
- score movement: `827.0950072730493 -> 822.850721011959`;
- cumulative-v2 source SHA-256:
  `DEE5092B6785DF7A63752C7AAE497051D08DCC62F7723CD9786225A0C5A99DE8`;
- exact historical-Silver source SHA-256:
  `F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E`.

## Root execution

The frozen union-shadow runner was loaded through
`run_new1_shadow.py`, SHA-256
`7B9DE4FF6E7A6752D262553772F27FF3774CE87A83D8777E1AC2F3B19F81BC14`.
The first accidental invocation used Python 3.9 and failed during import
before any policy callback because the runtime requires Python 3.10 or newer.
The authoritative rerun used `py -3.11` and completed successfully.

## Results

- replay files: `1`;
- correct-seat callbacks: `73`;
- parent/candidate action differences: `0`;
- rule starts or collisions: `0`;
- attribution: exact historical-Silver on all `73` callbacks;
- invalid actions, action errors, caught/outer exceptions, emergency
  fallbacks, stale/two-owner states, unknown collisions, and max-step hits:
  all `0`.

Summary JSON SHA-256:
`BD41323875C708ADBA2DC7FA1069019097743309A600F4ACE01748546EE23CC6`.

## Decision

This loss does not expose a cumulative-v2 implementation defect because the
candidate would make no action difference from exact historical-Silver.
It does not block the already authorized eight-rule exploratory live probe.
Any unrelated strategic weakness belongs in a separate future-loss memo and
must not be stacked into the pre-submit source.
