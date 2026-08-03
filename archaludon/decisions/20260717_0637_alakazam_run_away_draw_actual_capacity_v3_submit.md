# Submit decision: Alakazam Run Away Draw actual capacity v3

- Root decision time: `2026-07-17T06:37:00+09:00`.
- Decision: **submit the exact accepted v3 archive now**.
- Expected UTC-day quota transition: `1/5 -> 2/5` for `2026-07-16`.
- User cadence: use the four remaining slots; this is the first of the two
  distinct near-term candidates, not a slot-conservation exception.

## Candidate and hypothesis

The deterministic public-state rule replaces the inherited immediate
Powerful Hand with Bench Dudunsparce Run Away Draw only when three public
draws strictly reduce the target's hit bound, the source/target cost is
certified, and the physical deck contains at least three cards. The final
capacity guard removes v2's sole one-card short-draw semantic defect.

- Candidate source/deck SHA-256:
  `5F8F6578BF98BC285BB468FAD26969A22EDA96378F8E3AE35F134EA70EB91830` /
  `7B413177E5077777F2178143839C0155B03B92BBC8B3A6607621A7D43F351141`.
- Final Sol-Ultra ACCEPT decision SHA-256:
  `FC3D38CAA1DE6EF519570320B02CC7B8B56FCADA7457E17D638D550882C8F32B`.

## Paired local evidence

The exact fixed schedule has 1,440 unique parent/candidate keys with exact
schedule equality, both seats, nine opponents, old and collision-free new
seeds, zero action errors, zero max-step hits, zero raw faults, and no retry.
Public Best-5 wins `819`; v3 wins `829` (`+10`), with reference `+6`,
new-fresh `+4`, both seats `+5`, 11 gains, one regression, and exact sign
tail `13/4096`. Historical-Silver is flat in both panels, every combined
opponent floor is nonnegative, and all 15 controls remain wins.

V3 byte-matches rejected v2 on 1,439 traces and the parent on the sole
capacity key. All 45 retained branches have public deck at least seven,
both certificates, exactly three first-ability draws, and a same-turn
Powerful Hand. Target buckets are multi-turn conversion versus Starmie,
Kangaskhan/Crustle, Marnie, Great Tusk, and Alakazam; Historical-Silver,
Mega Lucario, Dragapult, seats, and mirrors are retention controls.

Broad numerical audit SHA-256:
`05282733F5C48E4873B929A6D689CD1E14DE22E8AF7D01183B42CA34B08C066C`.

## Package and runtime gates

- Archive:
  `autonomous_gold_20260715/packages/alakazam_run_away_draw_actual_capacity_v3_20260717/submission_alakazam_run_away_draw_actual_capacity_v3_20260717.tar.gz`.
- Bytes / SHA-256:
  `1,987,358` /
  `FF1A86BA186EAE196EB3CC00A8170CD381682A6C5E61F8B364FE0C0069CBC146`.
- Archive members: 13; unsafe/cache members: 0.
- Staging/extraction files: 12/12; missing/extra/mismatch: 0/0/0.
- Corrected isolated import: exit 0; callable agent; legal 60 integer rows.
- Extracted-package smoke: four started valid games across both policy
  seats, command exits 0/0, action errors 0, max-step hits 0.
- Package manifest SHA-256:
  `E10CFB924DB6CD50AB5F7796732047167C3511D5287193696C127AD98DC0FCCC`.

## Immediate Kaggle refresh and replacement basis

Read-only API and CLI snapshots both contain 48 submissions and exactly one
UTC `2026-07-16` row. Current submission `54757713` is `COMPLETE`, score
`874.2`, with 68 unique public episodes and a `38-30` raw reward record.
The frozen prior had 51 IDs; the exact current-minus-prior set contains 17
IDs and prior-minus-current is empty. The added results are `7-10`; all 17
new replays were downloaded and parsed. Latest episode `86361280` is a loss
and moves score `879.7053976167438 -> 874.2422588818276`. The current agent
is mature, below 1000, and is not protected as a recovering submission.

Root independently reproduced the 51/68 schedules, exact 17-ID addition,
zero removal, API/CLI one-row quota, target status/score, archive hash, and
17 replay files / 52,683,886 bytes. Collection manifest SHA-256:
`968B848D315B9CA188742A8A8C02C233E34BC8865268096A7D1380AADBC35814`.

## Write boundary

Submit from the exact package directory with description:

`Alakazam v3 actual-capacity Run Away Draw; +10/1440, 11G/1R; live probe`

After the CLI returns, immediately refresh API/CLI status, quota, validation
error fields, and initial public episodes. Record the submission ID and
archive identity. Do not claim live Bronze until live results support it.
