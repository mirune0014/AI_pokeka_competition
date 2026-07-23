# Pre-write decision: merge-v1 single-entrypoint deployment repair

- Decision time: 2026-07-20 05:10 JST
- Owner and only permitted Kaggle writer: root
- Decision: submit exactly one rapid deployment-repair probe
- Adoption/promotion: no
- Promotion baseline and rollback: source-transition v2, submission `54831507`

## Hypothesis and failure diagnosis

Submission `54837775` did not test the intended game policy. Its archive had
two top-level `agent` definitions. Kaggle Environments `1.14.11`
`get_last_callable` executes source into a dictionary and chooses the last
callable by insertion order; rebinding the earlier `agent` key did not move it.
The selected helper returned Boolean `False` rather than the initial 60-card
deck, producing `Validation Episode failed.`

The isolated repair makes only two lexical changes to the exact failed source:

1. rename the first `agent` directly to
   `_source_transition_v2_parent_agent`;
2. delete the later alias assignment.

Every function body, final `agent`, deck, runtime wrapper, engine file, and
game rule is unchanged.

## Frozen implementation and identity evidence

- Failed source:
  `7A97719A8B7FA84DEB01F823599E738FED0DB70AEF2A3815AA08D8340B5CD796`
- Repaired source:
  `2EA9450384765938939F286E24D17E25C2D5B678430388FED34B8133CB1F93DD`
- Exact diff:
  `772A9BABD4146C7701A1A906E56476B85A2CA773960A7B9FBB24BFFCB940CD28`
- Deck:
  `7B413177E5077777F2178143839C0155B03B92BBC8B3A6607621A7D43F351141`
- Runtime wrapper:
  `9CA7A415451B84343165EF8A5CDC0D67BBF1B4969A13C984C09B142B4898CD9A`

Focused six groups pass. Current-47 replay shadow covers 47 unique episodes
and 3,125 callbacks: failed-versus-repaired action differences `0`, latch
projection differences `0`, invalid actions `0`, and the same six authorized
differences versus source-transition v2. Root independently reran all 3,125
callbacks and reproduced the exact evidence SHA-256
`A8809E2B94763F262F08E450629E56906B97BA3907D815BAEECD74A89DB99DFB`.

Independent Sol-Ultra numerical audit passed all 42 checks and returned
`PASS_DEPLOYMENT_EQUIVALENCE_SKIP_NEW_COMPACT72`. Its report SHA-256 is
`7A5B0F66BF023AE143A382A73A87DDAD46E35D86300B93B85E0EA069FCE55D98`.
The previous merge compact72 remains the transferred strength evidence:
candidate and source-transition each `38/72`, P0 `20/36`, P1 `18/36`,
paired `0G/0R`, duplicate `72/72`, and zero faults. This is parity evidence,
not promotion evidence.

## Frozen package gate

- Archive:
  `packages/alakazam_evolve_active_ready_draw_survival_v3_merge_v1_single_entrypoint_fix_v1_clean_20260720/submission_alakazam_evolve_active_ready_draw_survival_v3_merge_v1_single_entrypoint_fix_v1_20260720.tar.gz`
- Bytes: `2,033,158`
- SHA-256:
  `B0802D97A4C09CA719FF665DF3E094F18CAE4D549F6889C580DEF95E0DB33CB8`
- Package manifest:
  `3E36313D2021D46FE50BC72892471FA6DA9C61EB416E410A8B46CDA40A5CBA3B`

The archive has exactly 12 files and zero cache/bytecode members. Windows and
WSL validation of the re-extracted bytes both select the sole final `agent`
through the exact vendored loader and receive the legal 60-card deck with one
ACE SPEC. Windows exact-seed Historical-Silver smoke passed from both seats in
132/146 callbacks with zero action errors and no max-step hit; traces are
byte-identical to the failed-source smoke. WSL completed 20 self-plays and one
Historical-Silver game per seat with all games started, zero action errors,
and zero max-step hits.

## Immediate authenticated refresh

Refresh directory:
`live/54837775/prewrite_single_entrypoint_fix_20260720_0505`.

- Authenticated API SHA-256:
  `54F461CCC20439A920FCC5937B38F4EF5B652C009EC259A47B31DA368F401D89`
- CLI SHA-256:
  `2E224EAF77C710E43AFDF8CAA43E129A68E4F7C5C41DF4C7DB0962D6A87CC015`
- API and CLI agree that UTC day `2026-07-19` has `3/5` submissions used;
  two slots remain.
- Failed `54837775`: `ERROR`, no score, exact error
  `Validation Episode failed.`
- Source baseline `54831507`: `COMPLETE`, score `756.9`.
- Current source episode CSV: 49 unique rows, SHA-256
  `948BDB21940B9463296FD92395FADDCFD44813879F2F0314D1C89E44CD9DC6E8`.
- Against the frozen 47-row snapshot, exact set difference is two public wins:
  `86937695` and `86943566`, SHA-256
  `3B796E87298FDC4447539CE45F71828CD1635040D997CBE150F6FEF846F6066D`.
- Root replay shadow of those two episodes covered 91 callbacks. It found zero
  invalid actions, zero failed-versus-repaired differences, zero duplicated
  repaired-instance differences, zero latch differences, and zero
  repaired-versus-source differences. Evidence SHA-256:
  `48F1BEBC85642897C659D6581B0B863C562506C97360B4CBC567C8A40CC2B318`.

There is no new blocker, unclassified activation, dominated activation,
nondeterminism, or invalid action in the refreshed evidence.

## Final judgment and write rule

The final Sol-Ultra strategy judgment is
`PERMIT RAPID DEPLOYMENT-REPAIR RESUBMISSION`. Submit only the frozen archive
above, once, with description:

`Alakazam merge v1 single-entrypoint repair; 3125/3125 exact policy identity`

Immediately refresh API/CLI after the command. A CLI encoding failure after a
complete upload must not trigger a retry. Record the unique remote ID, bytes,
filename, timestamp, description, owner/team, quota, and status.

`COMPLETE` is mandatory before interpreting score, wins, losses, or strategy.
If validation is `ERROR`, do not repeat this archive; resume deployment
diagnosis. If `COMPLETE`, classify only genuinely new public episodes and keep
source-transition v2 as the promotion baseline until live evidence supports a
separate adoption decision.
