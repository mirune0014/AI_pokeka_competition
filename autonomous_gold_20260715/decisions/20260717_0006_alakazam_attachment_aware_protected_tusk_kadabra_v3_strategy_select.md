# Alakazam attachment-aware protected-Tusk Kadabra v3 — strategy selection

- Selection time: `2026-07-17T00:06:00+09:00`
- Read-only strategy judge: `/root/ptcg_sol_ultra_worker`
- Parent: exact public Best-5 Alakazam, source SHA-256
  `DF4D597F593950B0D0C372F3E0BB26C182C4116648977F15ADBB329A6BA922F4`
- Selected candidate: `alakazam_attachment_aware_protected_tusk_kadabra_v3`
- v2 adoption status: rejected; v3 must be rebuilt from the exact parent.

## Selected hypothesis

The v2 mechanism is retained only as evidence: Super Psy Bolt can damage a
protected Great Tusk while Powerful Hand cannot. Its two safety failures share
one cause: the once-per-turn Energy attachment was diverted to a Bench lane
before evaluating the shortest prize route starting from the current Active.

The single v3 hypothesis is therefore:

> Against protected Great Tusk 58 only, exhaust every public same-turn prize
> route and every attackable Active Kadabra route before reserving a Bench
> Kadabra. Use a ready Bench Kadabra only when it is actionable now; otherwise
> fail closed to the exact parent.

## Fixed priority

1. Immediate game win.
2. Boss-assisted or Active unprotected same-turn Alakazam knockout.
3. Attachment-aware full-Hammer same-turn Alakazam knockout.
4. Ready Active Kadabra Super Psy Bolt.
5. Active Kadabra that becomes ready with this turn's legal Psychic attachment.
6. Legal retreat to a ready Bench Kadabra and Super Psy Bolt this turn.
7. A Bench Kadabra setup only when no Active route exists and the setup is
   publicly executable; all other states use the exact parent.

The rule is recomputed from each public Observation. It has no hidden state,
opponent-policy estimate, learned component, replay action label, or draw/mill
suppression.

## Phase 0 termination rule

v3 receives one counterfactual attempt on the same eight frozen pairs. If any
result, prize, same-turn knockout, off-predicate identity, or required positive
conversion gate fails, the protected-Tusk Kadabra mechanism is terminated and
must not enter Phase 1.

