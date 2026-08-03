# Alakazam protected Great Tusk Kadabra lane v2 — Phase 0 reject

- Decision time: `2026-07-17T00:02:00+09:00`
- Decision: **REJECT at Phase 0**
- Phase 1 run: **no**
- Package or Kaggle write: **no**

## Frozen artifacts

| Artifact | SHA-256 |
| --- | --- |
| Evaluation specification | `247CB2527F0594A0D6EF92EFB449E58B290FEF66D5EDE2846C386CAA1BA8049F` |
| Parent source | `DF4D597F593950B0D0C372F3E0BB26C182C4116648977F15ADBB329A6BA922F4` |
| Candidate source | `62529EF8D680A18B2ECC7AC98683B6609F2F6484371BFE92E596255E3C5FED9B` |
| Candidate runtime source | `82F625C3ADD69876586650FDEBB1177ABD6C8AD2E22F37EB5AD0313D9B41CB1B` |
| Shared legal 60-card deck | `7B413177E5077777F2178143839C0155B03B92BBC8B3A6607621A7D43F351141` |
| Phase 0 execution manifest | `454FCDA26477161A3764A81DB92C95F013B9605530B887D6686727ECA23457A2` |
| Phase 0 qualitative trace audit | `DCB67E4DA2F755BFEFD36AB94D46B0E3BC803575D46671759298AE5449AC64FA` |

## Root-verified execution evidence

- Parent and candidate each produced 8 rows on the same 8 unique `(seat, seed)` keys.
- Schedule equality was true; all 16 commands exited zero.
- Action errors and max-step hits were both zero.
- Parent won `0/8`; candidate won `2/8` (`p1/2026071501` and `p1/2026071536`).
- No Phase 1 command was executed.

## Root-verified paired outcomes

Remaining prizes are shown; lower is better.

| Seat / seed | Parent | Candidate | Result judgment |
| --- | ---: | ---: | --- |
| `p0/2026071501` | 4 | 5 | regression |
| `p0/2026071509` | 1 | 1 | exact result/trace identity |
| `p0/2026071541` | 4 | 3 | improvement |
| `p0/2026071579` | 1 | 2 | regression |
| `p1/2026071501` | 5, loss | 1, win | improvement |
| `p1/2026071536` | 1, loss | 0, win | improvement |
| `p1/2026071543` | 5 | 5 | exact result/trace identity |
| `p1/2026071552` | 1 | 1 | same result/prizes; candidate four turns slower |

## Causal trace findings

The bypass mechanism is real. A ready Kadabra's Super Psy Bolt dealt `60`
through the protected Great Tusk state and converted two parent losses into
wins. The off-predicate turn-6 Crustle knockout in `p1/2026071552` was also
prefix-identical and preserved.

The candidate nevertheless failed two mandatory safety clauses:

1. In `p0/2026071579`, the first divergence at step 45 attached Telepath
   Psychic Energy to a Bench Kadabra instead of the Active Alakazam. This
   forfeited the already available attach + Enhanced Hammer + Powerful Hand
   same-turn knockout and cost one prize.
2. In `p0/2026071501`, the first divergence at step 100 attached to a Bench
   Kadabra instead of the unenergized Active Kadabra. The first protected hit
   was delayed by eight turns and the Great Tusk prize was missed before
   deck-out.

These are independent violations of the frozen no-prize-regression and
full-Hammer-KO-preservation gates. The `2/8` win gain therefore cannot justify
Phase 1.

## What survives as evidence

- Preserve the exact parent whenever its current Active Kadabra can become
  ready with the turn's attachment.
- Certify an Alakazam route with a legal same-turn Psychic attachment before
  reserving or feeding a Bench Kadabra.
- Retain the public-state Kadabra bypass only after these higher routes are
  ruled out; do not carry v2 forward as an adopted baseline.

