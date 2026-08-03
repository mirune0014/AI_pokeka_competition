# Decision: reject Alakazam visible mill-clock minimum draw v1

- Decision time: 2026-07-16 23:16 +09:00
- Parent retained: exact public Best-5 Alakazam
- Candidate: `alakazam_visible_mill_clock_minimum_draw_v1`
- Decision: **REJECT before Phase 1**
- Kaggle action: none

## Bound artifacts

- candidate source SHA256:
  `02684FDBF5EBD9617BD9BDFEA302069EFEFB197F67633C210B280AAEAE1B6E86`
- candidate runtime-wrapper SHA256:
  `87A835E90E94EA0AFF680F829ED26EB531FB5DF5851A2DD9195977B111B5EDCC`
- unchanged 60-card deck SHA256:
  `7B413177E5077777F2178143839C0155B03B92BBC8B3A6607621A7D43F351141`
- immutable evaluation specification SHA256:
  `47FC21C895E2B5CDABC09A1676546962FF0B23FFB2CF5A686FEEE2B68143CD71`
- runtime-path erratum SHA256:
  `004EDC7FC1C3B8FC7C9F878D6E602EB0E3FAB170B98BAF47B993D39B8C277531`
- corrected Phase-0 execution manifest SHA256:
  `515F0128BDB40FD19B4D7BB5FA461504B5A6720B5B49835AF9E39CAC06263BBB`
- qualitative Phase-0 audit SHA256:
  `29072D0E82D282F87374AEE3D635D75D27865147BB91C1B2E3113EEA2696523B`

The first failed execution tree and its manifest remain preserved. Its manifest
SHA256 is
`CB2DE73EC87DC71314856E0D27DECDC1CDA53B173F2408BB3E6C22084D0BFC2A`.
That runtime-path failure produced no candidate game and is not gameplay
evidence.

## Root-verified execution

The corrected run used the exact eight frozen `(seat, seed)` keys for both
parent and candidate. Root recomputation found:

- 16 commands and 16 zero exits;
- 16 unique one-row summaries and exact parent/candidate schedule equality;
- 16 nonempty traces;
- zero action errors, max-step hits, or unstarted rows;
- parent `0/8` wins and candidate `3/8` wins.

The result flip alone is not an adoption gate. The frozen trace gate required
at least four of eight keys to start with suppressed optional deck consumption
versus ATTACK/minimum enabler, preserve any parent same-turn knockout, and turn
the saved deck into an additional attack or prize.

## Trace decision

Only three keys qualified:

- `p0/2026071509`;
- `p0/2026071541`;
- `p1/2026071501`.

The strict result is `3/8`, below the required `4/8`. In addition:

- `p0/2026071501` replaced a parent same-turn knockout with a two-hit route;
- `p1/2026071552` replaced a parent same-turn knockout with five Kadabra hits;
- `p0/2026071579` took two prizes versus the parent's five;
- `p1/2026071536` was a real board-out win, but its first divergence was a
  Lucky Helmet attachment that neither consumed deck nor triggered a draw.

The exact candidate therefore hard-fails Phase 0. No Phase-1 aggregate,
retention suite, package, or live submission is permitted for this artifact.

## Separate causal discovery

The `p1/2026071501` gain exposed a different public card interaction:

- Mist Energy (`11`) and Rock Fighting Energy (`20`) prevent effects of
  attacks;
- Powerful Hand (`1072`) places damage counters and recorded `0` into the
  protected Great Tusk;
- Super Psy Bolt (`1071`) deals ordinary damage and recorded `-60` after Great
  Tusk's Psychic weakness, taking the knockout.

This is not used to rescue or relabel the rejected mill-clock candidate. It is
forwarded to the read-only strategy judge as evidence for a new isolated
special-defense bypass hypothesis. That next hypothesis must preserve every
unprotected parent same-turn knockout and must not carry over the rejected
general mill-clock overlay.
