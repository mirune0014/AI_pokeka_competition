# Strategy decision: select sustained-attack prize-lane audit v1

Recorded at `2026-07-17T01:45:48+09:00`.

## Decision

`NO-SELECT` for a behavior-changing rule from the general route-gap audit.
`SELECT` the next behavior-neutral diagnostic:
`alakazam_sustained_attack_prize_lane_audit_v1`.

The exact public Best-5 Alakazam parent remains frozen. No candidate source,
package, or Kaggle state is changed by this decision.

## Evidence binding

| Artifact | SHA-256 |
| --- | --- |
| General audit specification | `281E53EDEAED74CC2B78A543904AFCAD1744B674072EC007E08A138DE07CE308` |
| General audit execution manifest | `CFCB98A57E9D8BA7A5E65B0E44F597FF1D5012AED04038873140086568877F99` |
| General numerical audit | `71FBDEB3D864E1B39243105CA4D0025CC2F662AA47E9C72B6BD4672B9E6970C4` |
| No-attack replay audit | `7B8C66B1D092CD7D3C6A2B4DA5CCD00291FF02D3BEACDABCFCA0EB4F66D4DD0D` |
| Post-attack-gap replay audit | `657C33BB61E8C055A3FA6BF9219222C569512095961288CEA8F501ED1CB54CEC` |

The root independently recomputed the 720 unique schedule keys, 406 wins,
314 losses, the 41 no-attack losses, the 65 post-attack-gap losses, and all
block/seat/opponent totals from raw command summaries plus game traces.

The two qualitative audits found no single mechanism satisfying the frozen
recurrence and H0/H1 safety gate. In particular, the following remain evidence
fragments rather than a patch: seven public missed H0 knockouts, one wrong
promotion, seven lone-Dudunsparce board-outs, and nine ready-Bench/END states.

## Why the next audit is different

The root independently verified 184 losses with at least seven Alakazam
attacks. They cover both blocks and seats and collapse to 72 distinct
`(block, seat, seed)` groups. Of these losses, 140 contain no internal attack
gap, 109 end with own deck zero, and 82 end with opponent Prizes zero
(terminal indicators overlap). The agent is often attacking continuously but
not converting attacks into a winning Prize route before its deck clock.

Therefore the next diagnostic tests one multi-turn family only: public
prize-lane dominance among the current target and legal Boss targets. It must
measure attacks-to-Prize completion after Boss hand-cost, exact damage or
zero-effect status, H1 readiness, public Fezandipiti ex exposure, and guaranteed
deck clock. Fez suppression and generic draw reduction cannot become separate
rules in this audit.

## Frozen rejected boundaries

Neutralization Zone, Acerola, Active-MD/Ultra Ball, visible mill-clock minimum
draw, protected-Great-Tusk Kadabra overlays, and any combination of the small
failure fragments above remain closed. The next audit reuses the exact Best-5
parent and the existing frozen 720 traces; it does not run a candidate.

