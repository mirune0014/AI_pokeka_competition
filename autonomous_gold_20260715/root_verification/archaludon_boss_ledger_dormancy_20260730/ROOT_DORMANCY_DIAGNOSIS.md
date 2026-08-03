# Boss access ledger dormancy diagnosis

## Conclusion

The fixed-760 dormancy is primarily **absence of the complete tactical
opportunity**, not a demonstrated recognition failure.

There were many near-miss positions, so “nothing remotely similar happened”
would be inaccurate.  However, no callback satisfied the rule's complete
public-state contract.  The only callback with the core `one Boss held + three
Boss publicly discarded` inventory was already a terminal one-Prize position,
where preserving Boss was unnecessary and the parent won immediately.

## Diagnostic method

- Frozen policy:
  `archaludon_persistent_public_boss_access_ledger_last_copy_guard_v1`
- Frozen policy SHA-256:
  `AACAC0B2E47C495A971A6CFCA91A393DBAC4A567291F849DB7912E9F26E9D3A3`
- Schedule: the same fixed 760 games, opponents, seats, and seeds used by the
  immutable evaluation.
- The diagnostic adapter returned the frozen policy's action without changing
  it and recorded its detached post-decision resolver state.
- Diagnostic games: `760`
- Candidate wins: `478`
- Action errors, start failures, and max-step hits: `0 / 0 / 0`
- Exact `(seed, result, steps, turn, action_errors, hit_max_steps)` mismatches
  against the original candidate run: `0 / 760`
- Candidate-controlled callbacks recorded: `42,159`

The telemetry adapter therefore preserved the evaluated trajectories.

## Funnel from broad resemblance to the exact rule

| Public decision layer | Count |
|---|---:|
| Candidate-controlled callbacks | 42,159 |
| Exact Ultra Ball two-card discard callbacks | 950 |
| Boss in hand | 497 |
| Boss and Metal Energy in hand | 351 |
| Boss, Metal Energy, non-ex Archaludon, and Archaludon ex in hand | 41 |
| The above four IDs present and parent chose Boss + Metal | 14 |
| Parent chose Boss + Metal across all Ultra Ball callbacks | 156 |
| Complete rule emitted | 0 |

The 950 exact Ultra Ball callbacks were suppressed as follows:

| Resolver result | Count |
|---|---:|
| Context or public-board gate ineligible | 547 |
| Four-copy public Boss certificate ineligible | 394 |
| Plan-equivalence or superior public target ineligible | 9 |
| Emitted | 0 |

For the 156 callbacks where the parent actually chose Boss + Metal:

| First failed layer | Count |
|---|---:|
| Context or public-board gate | 74 |
| Four-copy public Boss certificate | 82 |
| Reached plan-equivalence gate | 0 |

None of the 82 certificate failures had the exact public inventory of one Boss
in hand and three Boss in public discard.  The nine callbacks that passed the
four-copy certificate did not have the parent Boss + Metal discard action, so
the guard had nothing to replace.

## The sole exact Boss-inventory position

Exactly one parent Boss + Metal callback in the 760 games had:

- four tracked Boss cards;
- one Boss in hand;
- three Boss in public discard.

It was Historical-Silver seat 0, seed `271828218`, step `147`, turn `16`.
The player had one Prize remaining, a ready three-Energy Archaludon ex, and the
opposing Active Archaludon ex had `110 HP`.  Metal Defender dealt lethal damage,
the player took the final Prize, and the game ended as a win at step `151`.

This position was rejected before emission and would also fail the explicit
`more than one Prize remaining` plan gate.  That is a correct terminal
exclusion, not evidence that the rule failed to recognize a needed last-copy
reservation.

## Recognition-failure check

There were 418 general fail-closed callbacks elsewhere in the 42,159-decision
run, but **zero** of the 950 exact Ultra Ball discard callbacks ended with the
generic fail-closed resolver reason.  Every target-context callback received a
specific context, four-copy-certificate, or plan-equivalence classification.

Therefore this run does not show a target decision that should have fired but
was missed because the callback was unrecognized.  It does show that the rule
is intentionally narrow: hidden or uncertain Boss access cannot satisfy the
public four-copy certificate.  A real hidden-state opportunity may exist, but
the permitted public-state policy cannot claim it without evidence.

## Evidence hashes

- Resolver telemetry:
  `fixed760_resolver_telemetry_retry2.jsonl`
  SHA-256
  `5E5AE2ECE2AE1A52D9A61DAC12A8600112E05D6794C64978D9A7754C0E673826`
- Execution manifest:
  `execution_manifest_retry2.json`
  SHA-256
  `144FFDC685C9ECE03078B40E0A99422223EA91D7C1A4F0C56DBB23DFB5D0E393`
- Diagnostic adapter:
  `diagnostic_agent/main.py`
  SHA-256
  `D8A95024D7042F0466DC909695A64D903F076B7B85101F4E596B058535AAAB59`
- Diagnostic driver:
  `run_diagnostic_fixed760.py`
  SHA-256
  `70F106E02B76CB55149FC7464D7EE0A216ABD0900A7D8E3BB52F1EDAA403B512`
