# Root fixed-760 numerical recomputation

Date: 2026-07-30 JST

Decision:
`DESTRUCTIVE_NUMERICAL_GATE_PASS__STRENGTH_NOT_DEMONSTRATED`

This is Root's direct recomputation from the fresh repaired-child raw output.
It is independent of the execution runner's prose and precedes the independent
Sol-Ultra numerical audit.

## Frozen evidence

- candidate `main.py` SHA-256:
  `DEE5092B6785DF7A63752C7AAE497051D08DCC62F7723CD9786225A0C5A99DE8`
- exact historical-Silver `main.py` SHA-256:
  `F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E`
- deck SHA-256:
  `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`
- launch specification SHA-256:
  `E49A84DF8A8DB478000A733A72A40162E3F0429934A55B43F4CE3C7DABCAEC50`
- combined physical CSV SHA-256:
  `A44950A597DED7FF34A94D8BB77AA34024732FCE15EC4230AC469FE45B450356`
- execution manifest SHA-256:
  `41DA0C390920A4A6770C225DE487519949715DCBCCAA13D5B6D291F16AA31C1E`

Both checked panel commands exited `0`. The manifest records the exact frozen
schedule hash and candidate hash.

## Schedule and fault verification

- physical CSV rows: `760`;
- unique `(panel, opponent, seat, seed)` keys: `760`;
- duplicate key groups: `0`;
- exact required ten-column schema: pass;
- exact frozen schedule equality: pass;
- historical rows: `200`;
- adjacent rows: `560`;
- summary files / summary rows: `48 / 2,280`;
- retained trace files: `2,280`;
- missing starts, nonbinary results, nonzero role exits, action-error rows, and
  max-step rows: all `0`;
- observed decision range: `17..197`, below `max_steps=1000`;
- identical-policy baseline A/B trace pairs: `760`;
- byte mismatches in baseline A/B pairs: `0`;
- both checked reports: `valid=true`, empty invalid-reason lists, duplicate
  mismatch count `0`.

Root applied the correct result convention: the tested policy wins on
`result==0` in seat 0 and `result==1` in seat 1.

## Recomputed outcomes

| Scope | Historical-Silver | Repaired child | Delta |
|---|---:|---:|---:|
| Overall | 478/760 | 478/760 | 0 |
| Historical anchor | 100/200 | 100/200 | 0 |
| Adjacent population | 378/560 | 378/560 | 0 |
| Seat 0 | 243/380 | 243/380 | 0 |
| Seat 1 | 235/380 | 235/380 | 0 |

Paired candidate-only gains / parent-only wins are `0 / 0`. Every
opponent/seat cell is identical:

| Opponent | Seat 0 | Seat 1 | Total |
|---|---:|---:|---:|
| historical-Silver | 58/100 | 42/100 | 100/200 |
| Alakazam Gold | 32/40 | 30/40 | 62/80 |
| Arch Peak | 19/40 | 20/40 | 39/80 |
| Arch Shumpei | 17/40 | 23/40 | 40/80 |
| Cynthia | 33/40 | 34/40 | 67/80 |
| Kangaskhan/Crustle | 15/40 | 13/40 | 28/80 |
| Marnie/Kazuki | 32/40 | 36/40 | 68/80 |
| Mega Lucario | 37/40 | 37/40 | 74/80 |

The severe inherited Kangaskhan/Crustle floor remains unchanged rather than
improved.

## Exact trajectory prediction

Exactly three result/decision-count pairs differ, all parent-win/child-win:

| Panel / opponent | Seat | Seed | Parent steps | Child steps |
|---|---:|---:|---:|---:|
| historical / historical-Silver | 0 | 271828201 | 129 | 127 |
| adjacent / Arch Shumpei | 1 | 271958328 | 126 | 130 |
| adjacent / Mega Lucario | 0 | 271958329 | 76 | 94 |

Root compared all 760 baseline/candidate trace-file byte hashes. Exactly these
three traces differ.

The repaired target key, adjacent Mega Lucario seat 1 seed `271958318`, is
parent-identical:

- result: `1 / 1`;
- decisions: `85 / 85`;
- baseline trace SHA-256:
  `A18A6849CDE6770755AB1F0ECCB8A7C079B024A4188CC5C8B613DAA25843FE16`;
- repaired trace SHA-256:
  `A18A6849CDE6770755AB1F0ECCB8A7C079B024A4188CC5C8B613DAA25843FE16`.

Thus the frozen repair prediction is satisfied exactly. The dangerous
Mega-Brave-lock-clearing branch is removed without changing any other fixed
trajectory.

## Interpretation

The repaired child passes the frozen destructive numerical gate: no outcome,
panel, seat, opponent/seat floor, duplicate control, or runner fault regresses.
It demonstrates no local strength improvement because all 760 paired outcomes
remain tied.

The numerical pass is not formal-parent promotion or Kaggle authorization.
Independent numerical audit, final qualitative Sol-Ultra judgment, clean
package verification, and a fresh authenticated quota/status/episode refresh
remain required.
