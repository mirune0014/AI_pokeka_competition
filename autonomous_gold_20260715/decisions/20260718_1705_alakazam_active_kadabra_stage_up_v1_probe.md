# 2026-07-18 - Active-Kadabra stage-up v1 exploratory probe

Status: **submitted once as `54802782`; validation complete, public games pending**  
Owner: root  
Rollback: exact strict-Prize v3

## Isolated hypothesis

When exact v3 has finalized Active Kadabra's Super Psy Bolt but cannot obtain
the best exact KO, evolve the already powered Active Kadabra directly into
Alakazam, accept certified Psychic Draw for exactly three cards, revalidate
the full public state, and use Powerful Hand only when it produces a strictly
higher exact Prize yield.

The rule fails closed on unsafe deck count, Mist Energy, Rock Chestplate,
status, transient or unknown prevention, target/count/fingerprint changes,
duplicate ambiguity and any incomplete draw/attack/resolution boundary.  It
does not inspect drawn-card identity.  The 60-card deck is unchanged.

## Frozen local evidence

- exact parent v3 source SHA-256:
  `49E954F53E043CD79D928DFB2340CCB5D85A17F33CCB824C871CCE153C0C9C95`;
- candidate source/runtime/deck SHA-256:
  `6F773CD374D27CA01D2DD97C12D70A705E5BB38749E735B451BCD72876838581` /
  `9CA7A415451B84343165EF8A5CDC0D67BBF1B4969A13C984C09B142B4898CD9A` /
  `7B413177E5077777F2178143839C0155B03B92BBC8B3A6607621A7D43F351141`;
- implementation diff SHA-256:
  `D989CA6879722F766134BC1B4765FBAF333A7BFC980AAF35DA04654568B40589`;
- fixed schedule SHA-256:
  `4271E31503F37EFE4B1BBB9ED2D3569D79D9C1E9B2A20387CCAC131F28346010`;
- execution freeze/report SHA-256:
  `D058898AD3AFC02638723C048CC1F945C17EBC44DC77CD2347194A78EF31F41C` /
  `644AC5B6AE8E5627D40C67F31422ABCFB64F65A6FC8F602184DA4FA2CF1E79D4`;
- independent numerical audit SHA-256:
  `9C2F63C8015BE80401EEFF0324623E7E8F4A6D4304FEA3463E6FD846C1172DBA`;
- root Phase-0 verification SHA-256:
  `614C14810365A44F1A2C094FAA19BD0F62A3177435DE644B9A77376EDCF25BDC`;
- corrected final judgment SHA-256:
  `4F8DA0EB8C17D45F092335F58429785D9647D327E26FD695ED2303C52411B790`;
- live-evidence addendum SHA-256:
  `BB590B1C440698CA97A96AFD463D617F1F1ABBA9A45F99C35C4281230C6138C7`.

The fixed comparison has exact schedule equality over 144 unique rows:
candidate and v3 are both `86/144`, P0 `45/72`, P1 `41/72`, known `44/72`
and fresh `42/72`.  Every opponent bucket is equal.  There are zero gains,
zero regressions, zero action errors and zero max-step hits.

Only two traces change, both Marnie/P1 losses.  Both complete the intended
`EVOLVE -> YES/draw3 -> Powerful Hand -> resolution` transaction and convert
an exact KO, but neither changes the terminal result.  They expose the main
risk: spending three deck cards from start deck counts four or five.  This
passes the practical live-probe gate but fails strict adoption; v3 remains the
accepted baseline regardless of live score.

Root reran the 12 focused tests after discovering a distinct turn-plan live
serialization gap.  All passed, including checked-engine complete
transactions S119/S128/S137 at Powerful Hand 380/400/420, the exact draw
offer and resolution, 48 named retention callbacks and 532 complete-v3-win
callbacks.  The stage-up implementation validates the new Alakazam top
serial and the old Kadabra source inside `preEvolution`; it does not repeat
the rejected top-level old-source lookup.

## Corrected preceding live evidence

Root verification of the 26 new `54799469` episodes is SHA-256
`5A02189DACF9871DAAA803DA9C8E33576B0C3BC2BC0822860BD15CFF2B6C308D`.
The submitted turn-plan source reproduces all 1,741 recorded callbacks and
differs from v3 five times.  One reserve-attachment transaction completes;
four Abra-to-Kadabra evolution latches are incomplete but fail-closed, after
which exact-v3 fallback coincidentally selects the same YES and attack.

That rejects the preceding candidate's evolution branch.  It does not
exercise this candidate: exact stage-up versus v3 has zero differences over
the same 1,741 callbacks, with output SHA-256
`DC0CD449CAD25721B4983288D1854CCB34D41E41E4DAA36B9C859952A56AA1C3`.
The independent final re-judgment therefore retains one isolated exploratory
probe, with first-activation completion monitored strictly.

## Clean package gate

- package manifest SHA-256:
  `20CF222C9F9EAD5E9B752B81CD9D44C900292E303CBD009AD8AB00E50F39526D`;
- archive:
  `packages/alakazam_active_kadabra_pre_attack_stage_up_v1_clean_20260718/submission_alakazam_active_kadabra_pre_attack_stage_up_v1_20260718.tar.gz`;
- archive bytes/SHA-256:
  `2,016,141` /
  `0610981A1D6D1493D612E71DF32F6D5076DD12631161CFEC925D3886261057A0`;
- clean stage and re-extraction: 12 identical files, 5,648,414 bytes,
  framed tree SHA-256
  `447961A2EB04A99C4966044FDA82693B41D3D4F70A63B23EA0E4518AF525C17C`;
- legal deck: 60 rows, 23 unique IDs, copy caps valid, one ACE SPEC;
- package-local compile/import/callable/deterministic initial deck: pass;
- cache, bytecode, absolute and traversal members: zero;
- Historical-Silver packaged smoke: both seats complete normally, action
  errors zero, no max-step hit.

## Target and retention questions

Primary target: a three-Prize exact conversion against Mega Lucario.
Secondary targets: one- or two-Prize conversions in Alakazam mirrors and
Marnie-like resource-pressure games.  Mandatory risk split: start deck `4-5`
versus `>=6`, subsequent attack continuity and deck-out.

For every live activation, count completion only if this latch itself governs
EVOLVE, YES, exact draw resolution, Powerful Hand and resolution.  Identical
fallback behavior is not completion.  Any incomplete/fail-open route, invalid
action, prevention violation, failed exact KO or attributable v3-win loss
causes immediate rejection and rollback.

## Immediate authenticated refresh and authorization

Root immediate verification SHA-256 is
`36FE343086FE513FAE1F338F5039462EE184260EF6570D862BFC92DBF49B8AC0`.
The authenticated 17:05-17:07 JST refresh has seven collection exits zero,
all stderr empty, UTC-day quota `2/5`, three slots remaining and candidate
filename matches API/CLI `0/0`.  Both prior submissions remain COMPLETE with
empty errors: `54799469` at `772.3` and exact v3 `54797361` at `758.1`.
These scores are not attributed to either rule.

Both submission populations add exactly 15 genuinely new IDs with no missing
prior ID.  All 30 replays download and validate exactly once.  Exact stage-up
and v3 are identical on all 1,135 new `54799469` callbacks and all 1,066 new
v3 callbacks, with zero invalid actions.  No new state exercises the stage-up
rule or violates its live serialization contract.  One additional preceding
turn-plan evolution start repeats its already rejected incomplete fail-closed
boundary; that separate mechanism is not stacked here.

Archive/source/deck/package hashes remain frozen and package cache entries
remain zero.  The Goal is not already achieved.  All immediate-write
conditions pass.

Authorize exactly one upload now, near the three-hour cadence, with the ASCII
description:

`Alakazam Active-Kadabra stage-up v1; 86/144 parity; exploratory live probe`

Do not retry any local terminal-print exception until authenticated API and
CLI reads establish whether the upload row exists.

## Submission receipt

Root issued exactly one Kaggle submission command at 17:11 JST.  Upload and
terminal confirmation both exited 0; no retry occurred.

- submission ID: `54802782`;
- timestamp: `2026-07-18T08:11:08.000Z`
  (`2026-07-18 17:11:08 JST`);
- filename:
  `submission_alakazam_active_kadabra_pre_attack_stage_up_v1_20260718.tar.gz`;
- uploaded bytes: `2,016,141`, exactly equal to the frozen archive;
- description:
  `Alakazam Active-Kadabra stage-up v1; 86/144 parity; exploratory live probe`;
- initial status: `PENDING`, empty score and error;
- post-write filename matches: API `1`, CLI `1`;
- post-write UTC-day rows: API `3`, CLI `3`, therefore `3/5` used and two
  slots remain;
- post-write command exits: all three zero; captured stderr: all empty.

Post-write raw hashes:

- command exits: `27FEF0B67F4D8BAA24937E6CC643851CEE1F697AE4211DF2C85585AE9548C836`;
- API/CLI snapshots:
  `344826B88CE5731C24475819DFBC38D3E10D59DD473FEB9283813DEE82E7BFA6` /
  `BB2789508A5EA6AC745CAB25838757A64B0E63B1870442C5B75E23162FF661D4`;
- candidate API/CLI source rows:
  `572194D9DC775F61B192E513B3A89C7FEAA36DB556A70061A1B27571946C5450` /
  `4E8F8D4C550F1F7F52D39E8E28719C944E42C838E4541377F642A3B7EE8EAA82`;
- UTC quota API/CLI source rows:
  `7A21C1FC7F6BFDC56F42294B9A104440C7AF5E8C1F607885767889431F892EEB` /
  `C99739A7F1332993B08B5EF2A9A13CD0FC7F9A47C2CFE1A713A734DE6E3EADFD`;
- post-write raw manifest:
  `3AA6EA5B1784DABA548F89B035B2014328C912603E5AEF15950E29EAB47D3A77`.

The same post-write read shows the preceding turn-plan at `781.6` and exact
v3 at `758.1`; this movement is not attributed to either overlay and did not
cause the write.  Monitor `54802782` through validation and public episodes,
counting only stage-up latch activations as mechanism evidence.

## Initial validation completion

At 17:13 JST, authenticated API and CLI both show `54802782` as `COMPLETE`
at `600.0`, with empty error.  The episode source contains exactly one
self-match validation row, episode `86652903`, target reward `1`; no public
episode exists yet.  A self-match necessarily has one winner and one loser,
so this proves execution acceptance but is not public-strength or stage-up
mechanism evidence.

- validation candidate API/CLI row SHA-256:
  `43D9BE3BE8A097B6475023772C0640C80A3F1E281ECE246B36B22FFFD8ED3240` /
  `FD621DC6865F3B93EC283324CA39FB04E14F03648DE991DD53A39052E2CD5A23`;
- initial episode CSV/JSON SHA-256:
  `954D03050825523F2D5C7463EE14397624FC83BD1D9B4E6A1037F8B840570EF1` /
  `3369319D25B29AA819988E4C6981BF314434F17BF4A5B9BF6888B2BE22501D98`;
- validation snapshot manifest SHA-256:
  `A27810620E1A3A9C7C81D67ED35F7383A02938EC31E4F0DB96B4CA581B836312`.

The first immediate episode-list attempt occurred while the row was still
PENDING and returned HTTP 200 with an empty body, causing the checked listing
tool to exit 1 before producing a valid episode list.  Root did not retry the
upload.  The new post-validation snapshot above is authoritative and the
listing tool exits 0.

## First two public games

At 17:24 JST the submission is `COMPLETE 779.8` after two public wins,
episodes `86653576` and `86654113`.  Root public verification SHA-256 is
`3A9325D6D6CBC95C07248CDAE23FF3DD6F4A12B6EFCD97B538EB161E4D378F42`.

Exact stage-up and v3 choose identical actions on all 116 target callbacks;
the stage-up rule starts zero times and all actions are valid.  The wins and
score movement are therefore inherited-policy evidence, not mechanism
evidence.  Continue monitoring for the first actual stage-up transaction;
v3 remains rollback.

At 17:31 JST two more public games produce win/loss, for a public sequence of
`W,W,W,L` and latest episode score `767.4646902966393`.  Root increment
verification SHA-256 is
`AD2A2D68858FD8B81D82FBA48CD2B0031D3423841754C2C7231BD43F87303DA7`.
The new pair adds 138 valid callbacks with zero stage-up-versus-v3
differences.  Across all four public games the mechanism has still not fired
in 254 callbacks, so no result is causally attributed to it.
