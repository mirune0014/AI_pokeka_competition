# Submit decision: Alakazam fragile-Bench Prize-clock guard v1

Decision time: `2026-07-17T07:44:00+09:00`  
Decision: **SUBMIT exactly once** as the user-requested mechanism-distinct
second slot.

## Candidate and package

- Source/deck: `60D61F4269566B5E922EA9044A32A0B3BA5BB769F8AE9959E86C0EDCB008A9C9` / `7B413177E5077777F2178143839C0155B03B92BBC8B3A6607621A7D43F351141`.
- Archive: `submission_alakazam_fragile_bench_prize_clock_guard_v1_20260717.tar.gz`, 1,988,204 bytes, SHA-256 `BED19D45137617A934B6D1EFFBF6502F3C8C7593FF43709DD25DF1047180CC40`.
- Package manifest: `10EC5999A0BCB8183643326C992B23412FD521E0ABE06E9A283ACE4F5E85BFB9`.
- Final ACCEPT: `27DF6097B5488907EFDBFE4953DDC616E10BF7F48050F1425EEA35F8A4465E09`.
- Broad audit: `B532657B64DE87E08A6C3536A97F24E63D3FA1CA9E484CB60A308FED4B426E71`.

Compile/import, legal 60 cards, clean archive/extraction identity, archive
membership, deterministic repeat, both-seat packaged smoke, valid actions,
and frozen hashes all pass. There is no known P1 or broken behavior.

## Hypothesis and paired evidence

When accepted v3 would Bench a stage-dominated 50-HP Abra while a ready
Starmie/Dragapult can immediately take that Bench Prize, suppress the Abra but
retain current Powerful Hand and the existing H1 evolution line. The exact
1,440-key comparison is parent 829 to candidate 830, one gain, zero
regressions, 1,439 ties; all blocks/seats are nonnegative, Starmie is +1,
1,432 traces are identical, and all eight differences satisfy the public
predicate. This is a narrow exploratory advantage (`p=0.5`), not statistical
proof or a Bronze claim.

## Fresh live state and quota

Pre-submit collection manifest SHA-256:
`BE9D40AC2D87579CB50E1FC3E7D08B166C83D91E0950EFDE3550E78EE063CA21`.
Authenticated API and CLI each show 49 total submissions and exactly two rows
on UTC date `2026-07-16`, so today is `2/5` used and three slots remain. Current
submission `54769337` is COMPLETE, score `657.0`, error description empty.
The public set grew from 3 to 15 episodes; all 12 genuinely new replays were
downloaded once. Latest score moved 633.1478671563907 to 657.068332082517,
but one terminal uptick is not treated as established recovery. The outgoing
candidate is fully valid and deliberately targets a different mechanism.

Submission description:
`Alakazam v4 fragile-Abra prize guard; 830/1440, 1G/0R; distinct Starmie probe`

Submit the exact archive once. If the client reports a post-upload display or
encoding failure, query authenticated API/CLI before any retry; never duplicate
an accepted submission.
