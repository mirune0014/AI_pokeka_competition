# Root verification: first Turbo Flare exact-role fill census

Decision: `STOP__FIRST_TURBO_EXACT_ROLE_FILL_NOT_ACTIONABLE`

No candidate source may be created from this hypothesis. The fixed numerical
implement gate failed and its thresholds are not relaxed.

## Provenance

- parent `main.py`: `558EE5DB29E001428B0D59813613FABEE8E15B96E422746C104BDFAB4DC22DB6`
- deck: `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`
- manifest: `90A512D5C9AE5EAD8DF92F370C32716959EC0929F9465451E7BB0926DBEB5A68`
- strategy: `E3E6C7BBA58DB125FCF2594FD0EA3A2DE826563DDE5B96DD95682BB213C0389D`
- retry execution specification: `09A9038B12432E80031E13BE8BA608BE287FBFE1FF6C8819658E8CF00BFA97D9`
- retry runner: `558EF4BEBEE3A213886F98F7E1F0452F61090953A0DD61291B03C958C02E471B`
- independent Sol-Ultra audit: `96422EB1DA77FAEEB6762BA3D63082BFBCF14E03A3383B4EC1C4F54BD7953BB8`

Root recomputed the raw output hashes directly:

- callback rows: `FED101B77BD55E9BFE9E25C17AC63F2E2693CCFA05EDFFCC56C3C92B9D70EE49`
- transaction rows: `F8516840B8700DDD2D2E78AE350D2A5B2EDC316BBC1BE094C8A61BC05E8F9A34`
- predicted differences: `55CCD26BD89C833416F6C14C23DE8FB0ADF32ED3DDDCA63193A5C5FA5E2A7BC1`
- copied manifest: `90A512D5C9AE5EAD8DF92F370C32716959EC0929F9465451E7BB0926DBEB5A68`
- summary: `4F520F733D2620CABBEB7F1EF0A123521F6307FDE108DD64BA3E82EDE3347D2A`

The deterministic operator's initial prose omitted two hexadecimal characters
from the transaction hash. The operator's supplied value is not authoritative;
the 64-character value above is the root-verified file hash and is the value
used by the independent audit.

## Root recomputation

- manifest: 207 replay files, 209 target seats
- parent calls: 25,880; unique raw keys: 25,880
- first-Turbo transactions: 133; unique transaction keys: 133; both seats
- callback rows: 1,132; unique semantic callback keys: 1,132
- identical engine retry presentations collapsed: 489
- predicted first differences: 10 callbacks in 10 transactions and 10 replays,
  spanning both seats
- parent-equal controls: 1,122 callbacks in 123 transactions, both seats
- predicted classifications: 10 `OVERFILL_AVOIDANCE`, 0 retargets
- invalid parent actions: 0
- invalid contract actions: 0
- hidden-information uses: 0
- H3 changes: 0
- owner collisions: 0
- non-Turbo changes: 0
- semantic-copy differences: 0
- predicted-row errors: 0

The root counts agree with the independent Sol-Ultra audit.

## Gate result and qualitative boundary

The immutable gate required at least 24 immediate semantic differences over at
least 16 transactions and 12 replays. The evidence has only 10/10/10, so the
gate fails before implementation.

All ten first differences reduce the `ATTACH_TO` Energy count. Eight occur with
an empty Bench and reduce three selected Energy to zero. Two occur with one
partially powered Duraludon and reduce three selected Energy to its exact
two-Energy deficit. There are no exact-role target redirects. These are safe
resource-cleanup boundaries, but they are too sparse and mostly do not alter a
payable attacker. They do not justify adding another transaction layer to the
formal parent.

The failed attempt-1 destination and the successful retry destination remain
preserved. No source edit, local matchup simulation, package, or Kaggle write
follows from this stopped hypothesis.

