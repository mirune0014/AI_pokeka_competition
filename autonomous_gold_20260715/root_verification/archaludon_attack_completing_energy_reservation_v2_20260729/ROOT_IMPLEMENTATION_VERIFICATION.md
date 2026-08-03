# Root verification: H6 attack-completing Energy reservation v2

Verified `2026-07-29 17:10-17:15 JST`.

## Frozen identities

- Exact historical-Silver parent `main.py`:
  `F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E`
- Exact parent/candidate `deck.csv`:
  `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`
- Rejected H6 v1 `main.py`:
  `AC798FD2B757D94DDC21EFF07FE53EF4AFB9C139F98EA47DA0A9285ABC5FABB5`
- H6 v2 `main.py`:
  `C2B2E6E2A3170A1E90853CD0128075EA023831C17F2B7263744E371FC826E530`
- Direct parent-to-v2 diff:
  `4A44555CA0BF16E5219614F23EB86CA04EE856FE3F0462043BE99088A316620D`

The candidate is a fresh direct child of the exact parent. Every non-main
runtime file is parent-identical. `main.py` starts with the exact parent bytes
and appends H6 as the sole last-callable `agent` insertion.

The v1-to-v2 policy change is confined to
`_h6_core_valid(..., after_attach=False)`: 16 inserted and 4 deleted lines.
Before attachment, v2 requires a complete hand, exact `handCount`, non-None
cards, positive unique serials, exactly one Basic Metal, and that Metal's
serial equal to the reservation. The post-attachment branch is unchanged.

## Independent Root rerun

Root copied the five frozen verification scripts to this separate destination
and reran them with Python 3.11 and `PYTHONDONTWRITEBYTECODE=1`. Every command
exited `0`.

- structural checks: `16/16`
- focused prior positive/control cases: `6`
- focused prior negative cases: `58`
- rollback cases: `20`
- reset/count/exception cases: `7`
- sibling-context cases: `30`
- new both-seat safe-effect uniqueness cases: `64`
- full transactions: `9`, `37` callbacks
- additional both-seat uniqueness callbacks: `64`
- shadow: `207` files, `11,473` callbacks
- shadow differences: exactly source `88584180:91`
- fail-closed shadow rollbacks: `7`
- invalid actions, exceptions, stale transactions, external differences, and
  max-step hits: all `0`

The source mechanism remains exact: discard Night Stretcher `#90` and Jumbo
Ice Cream `#94`, preserve and attach Basic Metal `#120` to Active Archaludon
ex `#67`, then use Metal Defender `253` for 220 damage (`310 -> 90`) and zero
Prize.

The former destructive case now passes: after arming with sole Metal `[120]`,
a continuation hand `[120,998]` makes core validity false, returns the exact
parent action, and clears the transaction.

Except for `structural_results.json`, whose compiled-file path list correctly
names this independent Root directory, all ten deterministic result and
manifest artifacts are byte-identical to the worker outputs:

- focused results:
  `B72B9A054CAE03F3E350938B89DA72BF50FBA5218841C4E8FE7B5F64AEF5C35E`
- engine transactions:
  `BD4CF049F0465FDB9EAA29A4260C004F496BA949FE8EAC58C5B9FF509619052B`
- v2 uniqueness reproducer:
  `3A9A5631CB1125842C53516CA45F5B2C736525738D8930188F1FC40386697E27`
- shadow summary:
  `E5ED02F7CDFC70EB74D8E5B5A922077D86729C8A350CC5DB8F16B3F382F929E4`
- shadow differences:
  `9E1D8FFB7478F437CFAE5DE564463477FAAC06B1243BBB342D9125DC61D011C9`
- shadow rollbacks:
  `950A1A288543E85A07AF0B0894D1E8F50E1519A8BD0876A570D269DDD3E6E631`
- shadow per-file rows:
  `63A718B1931B8D4F34A8FAB2DFD4C3A61C32E886CA944549AE22109316FA00A1`
- shadow source manifest:
  `A252E906160A83A36DA916593C31766F4586481F1995E6E9C05210A697685EC3`
- engine source manifest:
  `63B7295040CCF6776682C28BAB19CF41AB64B3A1700AFFC2F8EE91C5EAD89640`
- direct parent diff:
  `4A44555CA0BF16E5219614F23EB86CA04EE856FE3F0462043BE99088A316620D`

Candidate runtime has 12 exact members, a legal 60-card deck, one ACE SPEC,
and zero cache members.

## Root decision before fixed evaluation

Implementation and engine safety gates pass. The H6 v1 certificate breach is
closed without widening the selected hypothesis. H6 v2 may proceed to a fresh
immutable fixed-760 execution. It is not yet authorized for packaging or
Kaggle submission.
