# Presubmit decision

Decision time: `2026-08-01 14:40 JST` (`2026-08-01 05:40 UTC`).

## Candidate

- Name: `archaludon_practice_first_terminal_and_role_commitment_v1`
- Candidate policy SHA-256:
  `5A0F4BE26EE0AB0B05200A4640301141F58CDDDAD1750D65EA2D1986CE52E7B5`
- Archive:
  `autonomous_gold_20260715/packages/archaludon_practice_first_terminal_and_role_commitment_v1_clean_20260801_1436/submission_archaludon_practice_first_terminal_and_role_commitment_v1_20260801.tar.gz`
- Archive SHA-256:
  `E8F735A7504F906D85B0D767FCC0E3C6AD7E31614786326DE620640A6F45B4E1`

## Hypotheses and target failures

- Convert a publicly certain game-winning attack instead of spending the turn
  on search, Supporter, attachment, evolution, retreat, or redundant Pokemon
  development.
- Do not consume a hand card and Bench slot on Duraludon when the play adds no
  public tactical or continuity role and the same exact nonterminal attack is
  already available.

Expected improvements are fewer terminal misses and fewer purposeless Bench
commitments.  Required holds protect board-out coverage, Turbo Flare targets,
visible conversions, the first backup, one-Prize walls, and exact-reply
improvements.

## Evidence level

The user explicitly replaced the former proof-heavy workflow with a practical
submit-and-repair loop.  Therefore the fixed evidence for this exploratory
write is intentionally limited to compile/import, legal deck, final loader,
focused firing/hold/negative fixtures, deterministic retry, clean packaging,
and both-seat runtime smoke.  Those checks passed with zero action errors.
No broad local win-rate claim is made; the packaged smoke was 1-1.

## Fresh Kaggle state

- Relevant Archaludon `55126164`: `COMPLETE`, score `814.6`, 52 public games,
  record `32-20`.
- Fresh episode table has 38 IDs beyond the prior frozen 15-row snapshot.
- UTC `2026-08-01` quota before write: `0/5` used, `5/5` remaining.
- Candidate source and archive hashes are new and have not been submitted.

## Decision

`SUBMIT_ONE_EXPLORATORY_LIVE_PROBE`.

This is not a formal promotion over `55126164`.  It consumes one slot to learn
whether the two human-fundamentals rules fire and whether their interaction is
beneficial or harmful in live play.  Do not retry the upload blindly after a
Windows console error; refresh submissions first.
