# 2026-07-18 08:48 JST — active-Psychic lone-Dudunsparce survival exploratory probe

## Decision

Permit exactly one exploratory Kaggle submission of
`alakazam_active_psychic_lone_dudunsparce_survival_v1`. This is a live probe,
not adoption over accepted Alakazam v6. Do not use the second remaining
pre-reset slot for the unchanged mechanism.

## Frozen hypothesis and artifact

The active-Psychic immediate-KO branch is locally stronger than v6 but still
has a known sequencing tradeoff. The isolated overlay suppresses Run Away
Draw only when Dudunsparce is the lone Active and the Bench is empty, because
returning the last Pokemon to the deck ends the game immediately.

- candidate source SHA-256:
  `FAB47771161EF7F43C9402B58D38FF240C92B6A2B77FFA6B925DFEA7F990D033`;
- runtime/deck SHA-256:
  `9CA7A415451B84343165EF8A5CDC0D67BBF1B4969A13C984C09B142B4898CD9A` /
  `7B413177E5077777F2178143839C0155B03B92BBC8B3A6607621A7D43F351141`;
- archive:
  `packages/alakazam_active_psychic_lone_dudunsparce_survival_v1_20260718/submission_alakazam_active_psychic_lone_dudunsparce_survival_v1_20260718.tar.gz`;
- archive SHA-256:
  `6AE123061DC273FB3E858C0D86FA897588D4B696871F7561D567F37F1D1E762E`;
- package manifest SHA-256:
  `AB0E2B371F43130E04E27FCC893C7E1AA9CA87F4E06ADC5C3F38D156CBA0CE67`.

## Paired and engine evidence

- Exact live replay `86580164`: the prior policy chooses Ability at S21 as
  lone Active Dudunsparce/no Bench and immediately loses; the overlay chooses
  legal END. The checked seeded engine remains live with Dudunsparce Active.
  The exact comparison JSON SHA-256 is
  `C2954E4CEC36085A80468869C4C1C109869B7A95DF8BF38746925342481F6A49`.
- The checked regression test passed and its source SHA-256 is
  `7B823FC4612BBE5FEB84B66E859FC1883CAD8BF37753E43BAD2C8FEF35FD174D`.
- Fixed overlay schedule: 144 unique equal keys; active-Psychic parent and
  overlay both `84/144`; gains/regressions `0/0`; P0/P1 `45/39`;
  known/fresh `43/41`; all 144 started; action errors and max-step hits zero.
  Execution report SHA-256 is
  `2B0C5EC88D802D6089834ACF8DD2CB617CA63B790B1A2BD62F48BCA46267E029`.
- Clean archive import validates a legal 60-card deck and local package paths.
  Exact Historical-Silver one-game smokes in both candidate seats started and
  completed with zero action errors and no max-step hit.

The strategy judge permits one exploratory probe. It explicitly does not
promote the branch: active-Psychic remains `7/16` against Alakazam Rmy versus
v6's `9/16`, and attach-to-KO can preempt productive setup.

## Mandatory fresh external refresh

Raw snapshot:
`live/54793002/snapshot_20260718_084411`.

- CLI/API/ListEpisodes/extractor exits: all zero;
- current submission `54793002`: `COMPLETE`, score `708.6` on the final
  immediate refresh;
- API and CLI UTC `2026-07-17` source rows: exactly three, refs
  `[54793002,54790261,54779045]`; root interpretation: `3/5` used, two
  pre-reset slots remain;
- prior/current public episodes at the logged snapshot: `21/28`, no prior ID
  missing;
- literal new IDs:
  `[86580705,86581290,86581823,86582373,86582929,86583498,86584059]`;
- root recomputation: new `2-5`, total `15-13`;
- current episode CSV SHA-256:
  `05FA7ED630ED439FCF7012EEF7A04FADEA37C4F95FC536B1A140171B75EFA272`;
- API/CLI raw SHA-256:
  `55EEBC69EA7D42BB1DF948B116FECA4A38030419C3D8DA5FF6FEDE89E3AE6A5A` /
  `D9915A73D4490A322F710A3E40D88268C02F29355D5879251F078A6FC3037FC5`.

The final immediate refresh found one additional completed loss, episode
`86584631`: current rows `29`, total `15-14`, score
`708.69167561454`. Its replay was downloaded successfully, the final episode
CSV SHA-256 is
`87CBE4A5F5BDD8DAE4532F6261B62B78BB00ADA4B463D1185BCB33802F74C631`,
and the quota source set remained the same three refs.

The live parent is complete, weak rather than recovering, and the candidate is
locally justified. The user's practice-first instruction and the expiring
quota justify consuming one slot after replay-download completion and one
last source/hash recheck.

## Post-submit stop condition

Judge score and histories together. If live evidence shows setup-preemption,
another self-removal loss, or P1 failure, freeze this branch and implement a
general setup-before-KO successor. Do not resubmit this unchanged mechanism.

## Submission receipt

- submission ID: `54794301`;
- timestamp: `2026-07-17T23:48:58.000Z` (`2026-07-18 08:48:58 JST`);
- uploaded bytes: `2,007,335`, exactly matching the frozen archive size;
- API filename and description exactly match the frozen archive and intended
  exploratory message;
- initial status: `PENDING`;
- post-write UTC-day source count: `4/5`.

The upload reached 100%, after which the Windows Kaggle CLI process returned a
`UnicodeEncodeError` while printing its accented confirmation text. No retry
was issued. Immediate CLI and API reads independently showed the single new
row `54794301`, proving that the external write succeeded without duplication.
