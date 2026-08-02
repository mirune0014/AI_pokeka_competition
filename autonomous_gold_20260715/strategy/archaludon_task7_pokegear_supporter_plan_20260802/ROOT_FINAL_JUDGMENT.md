# Task 7 root final judgment

## Decision

`ACCEPT_FOR_COMMIT_AND_PUSH`

This is a practical-safety acceptance for Task 7. It is not a claim of local
or live strength promotion.

## Frozen artifacts

- Candidate `main.py` SHA-256:
  `8364A91B1DAF48968D9D5C3BBA257D43546E27AB7076841A5400124048602E28`
- Deck SHA-256:
  `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`
- Focused result SHA-256:
  `6DDD98AD638E10E9639F5B4F558C81606472E0DB7C9B6448EDE73A9B0C1F9DCA`
- Shadow result SHA-256:
  `8F485FC97927BC8CB91D2F0C6246400322239AA2B3ECFECD8D328F2DAD1F02D8`
- Structural result SHA-256:
  `9B94727F8E0818CE0CC550F69DA6B3404D70DAFE75923A8B4D2E3326785743D8`
- Implementation report SHA-256:
  `8F940EF67FBE8EFA01E98B592294F3535EA221211C2A3C3075EC55140308797B`

## Root verification

- Focused fixtures rerun: 94/94 PASS.
- Structure rerun: package 12 entries, only `main.py` differs, legal 60 cards,
  ACE SPEC 1, final/imported callable `agent`, cache-free.
- Replay shadow: 252 readable replays, 13,829 decisions, ten differences in
  nine replays, all `T7_EXACT_TERMINAL_BOSS`, unexpected differences zero.
- Episode 89292594 converts Explorer into the exact terminal Boss route.
- Lunar Cycle is locally classified as an own-turn hand engine only when exact
  metadata matches; global effect maps are restored after every Task 7 oracle
  call.
- The initial Gear-certificate ordering defect was repaired. Both seats now
  produce the same Boss, selected route and certificate hash when only option
  order changes, and duplicate retry is recorded without advancing ownership.
- Extracted both-seat smoke completed with zero action errors and no max-step
  hit.

The independent Sol-Ultra final judge returned `ACCEPT` for this repaired SHA.

