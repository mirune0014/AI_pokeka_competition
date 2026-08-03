# 2026-07-17 17:36 JST — submit Alakazam lone-Dunsparce Enriching reserve v1

## Decision

Consume one of five currently available UTC-day Kaggle slots for exactly one
exploratory live probe of the frozen deterministic candidate
`alakazam_lone_dunsparce_enriching_reserve_v1`.

This is not a Bronze/Silver/Gold claim. The purpose is to test whether a rare,
fully certified opener rescue occurs in the live distribution while retaining
the locally dominant parent behavior everywhere else.

## Isolated hypothesis

When Hilda's Energy branch is reached on turn at most 3 with six Prizes, a
lone unenergized Active Dunsparce, empty Bench, no reserve/search card already
in hand, a certified singleton-loss Active threat
`{Solrock, Riolu, Duskull, Staryu}`, sufficient deck clock, and exactly one
offered Enriching Energy, execute the frozen transaction:

`Hilda selects Enriching 13 -> attach that serial to the same Active
Dunsparce -> draw four -> establish one legal reserve before the opponent's
next decision`.

Any mismatch clears the latch and delegates the unchanged parent. The deck,
threat whitelist, reserve priority, and all other rules remain frozen.

## Paired local evidence

- Correct direct-parent schedule: 1,440 equal unique
  `(panel, opponent, seat, seed)` keys; missing/extra/duplicates `0/0/0`.
- Fragile-guard parent `830/1440`; candidate `833/1440`.
- Gain/regression/tie: `3/0/1437`; action/summary/max-step faults `0`.
- Blocks: known `0`, fresh `+1`, new-fresh `+2`.
- Seats: p0 `0`, p1 `+3`.
- Opponents: Starmie `+2`, Dragapult `+1`, all others `0`; every
  block/seat/opponent floor is nonnegative.
- Target aggregate Mega Lucario + Dragapult + Starmie: `+3`.
- Trace schedule: 1,436/1,440 byte-identical; all four changed traces satisfy
  the declared singleton-Dunsparce transaction; inherited fragile gain remains
  a byte-identical win.

The delta is small and all gains are P1, so it is deterministic local
dominance rather than statistical proof. Exact fires in the audited live
slices are `0`; live score motion without an observed fire is not attributed
to this rule.

## Fresh live state before write

Read-only refresh manifest/root verification SHA-256:
`4BFA9A8BB1D79319E9F88807C4334E398B5BAFE6E4C23060B6688A79B414F261` /
`CF975F5EE550C16A54AAA636BE41C5DE489EC7A8472A5EF98924D5DE480DADB4`.

- UTC `2026-07-17` submissions: `0/5`; available before write: `5`.
- `54769337`: `COMPLETE`, score `661.7`, public `24W-23L`.
- `54770067`: `COMPLETE`, score `694.0`, public `22W-25L`.
- Genuine new episode since the prior snapshot: only `86450000`, a v3 win.
  Replay SHA-256
  `AC0E22B51182433506E44E5132382785853FBC7EFB07200F391DEF72360F65FD`.
- The new replay has no candidate-latch fire, no Fez bridge opportunity, and
  no known-broken fact; it safely takes the final Prize at deck count 1.

Neither mature submission is recovering toward the 1000 threshold, and the
new candidate is locally valid rather than filler. The authorized probe is
therefore consistent with the user-requested active use of today's slots.

## Package gates and identity

- Archive: `submission_alakazam_lone_dunsparce_enriching_reserve_v1_20260717.tar.gz`.
- Bytes / SHA-256: `1,991,799` /
  `D67C8A76617C0A3D065857DDBDBB41B3153B15F6536360106E0721A49555F1F2`.
- Package manifest SHA-256:
  `AA0739CB07007BF0005746B13E20DB614FE10072490B60292BCE005727B49998`.
- Candidate source/deck SHA-256:
  `77D111B6061A9A5EF1BCCA383181E1A5EBD67DF10CA45AB0936BE0AAD275785A` /
  `7B413177E5077777F2178143839C0155B03B92BBC8B3A6607621A7D43F351141`.
- Final Sol-Ultra judgment SHA-256:
  `79935687A0EEDC27623E17737ED37857AC7F5029A534CFE4BB5CED92018ED8AE`.
- Isolated import/compile and legal 60-card deck pass; archive member security,
  staging/extraction equality, frozen files, and cache checks pass.
- Packaged both-seat smoke against exact Historical-Silver: 4/4 valid, action
  errors 0, max-step hits 0.

## Submission note and monitoring

Use description:

`Alakazam v5 lone-Dunsparce Enriching reserve; 833/1440, 3G/0R; rare opener probe`

After upload, verify exactly one matching API/CLI row, submission ID, empty
error, and new UTC-day count `1/5`. Monitor public episodes for exact latch
fires and diagnose board formation, backup readiness, attacks, Prize exchange,
and deck clock. Rollback is the exact submitted fragile-Bench guard; no
automatic score-only rollback is authorized.
