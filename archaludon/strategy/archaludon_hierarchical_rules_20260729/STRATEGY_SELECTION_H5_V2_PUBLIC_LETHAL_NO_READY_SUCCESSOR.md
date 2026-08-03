# H5 v2 strategy selection: public lethal Active, no ready successor

Selected mechanism:

`H5_V2_PUBLIC_LETHAL_ACTIVE_NO_READY_SUCCESSOR`

This is a fresh direct child of exact historical-Silver:

- `main.py` SHA-256:
  `F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E`;
- `deck.csv` SHA-256:
  `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`.

H1 through H5 v1 remain absent siblings. H5 v1 is a rejected diagnostic
control and is not the source of this candidate.

## Why this repair

H5 v1 correctly found a one-Prize Coated Attack KO but could also take that
KO when it was not urgent and a prepared opposing successor was visible.
The causal separator is not the Prize score:

- the source positive has a presently lethal opposing Active and no ready
  Bench successor;
- both fixed harmful triggers have a nonlethal opposing Active and a visible
  three-Energy successor.

The comeback proxy `our remaining Prizes > opponent remaining Prizes` is
rejected. It can admit a nonlethal conversion while behind and suppress a
necessary lethal-threat removal while tied or ahead.

## Public certificate

At an ordinary MAIN callback:

1. Compute exact historical-Silver's semantic action exactly once.
2. The inherited action must be Raging Hammer `224` from Active Duraludon
   `169`.
3. Retain every H5 v1 structural gate:
   - the Active is evolution-eligible and has exactly three attached Basic
     Metal;
   - a legal non-ex Archaludon `840` evolution targets that exact Active;
   - the current Active, evolution, and opposing Active each yield one Prize;
   - the Coated KO is nonterminal;
   - inherited Raging Hammer's exact effective damage is a non-KO;
   - Coated Attack `1212` deterministically KOs;
   - no equal/higher deterministic direct, alternate-evolution, or
     Boss-to-attack conversion exists;
   - the route uses no attachment, retreat, search, draw, Ability, chance,
     or hidden information;
   - exact parent Ogerpon/endgame non-ex exceptions retain precedence.
4. Project only Raging Hammer's deterministic public consequence. The
   opposing Active must survive.
5. In that public projected state, the surviving opposing Active must already
   have at least one printed attack that:
   - is currently paid by its attached public Energy;
   - is legal under current public state;
   - has fully deterministic damage from current public inputs;
   - would KO our current Duraludon on the opponent's next attack.
6. Attack damage may use only current public inputs explicitly required by
   the printed formula, including current hand/deck counts, HP, damage,
   Energy, status, Tools, Stadium, weakness, resistance, reduction,
   prevention, and persistent restrictions.
7. Do not project draw, attachment, evolution, switch, Ability, Supporter,
   hidden cards, or coin outcomes. Unknown formula, legality, modifier, or
   persistent effect fails closed.
8. Every opposing Bench Pokémon must fail the ready-successor test.
9. A Bench Pokémon is ready when its currently attached public Energy pays
   any printed attack cost upon ordinary promotion. Count both damaging and
   setup attacks.
10. Do not treat prospective Coated Attack protection as proof that a Basic
    successor is unready. Its paid attack still makes it ready.
11. An unknown Bench card, attack cost, Energy identity, legality, or
    persistent restriction prevents proof that the Bench is clear and must
    fail closed.

## Precedence

1. Forced callbacks, legality, and exact terminal win.
2. Existing equal/higher-Prize deterministic conversion.
3. Exact parent Ogerpon/endgame non-ex exceptions.
4. H5 v2.
5. Exact historical-Silver.

H5 v2 must not preempt setup callbacks. It may arm only at the exact Attack
boundary after the complete public certificate passes.

## Transaction

The state machine remains:

`ARMED -> exact 840 evolution -> confirmed EVOLVED -> revalidate -> Coated Attack 1212 -> clear`.

Retain v1's duplicate semantics, snapshots, idempotence, reset behavior,
irreversible-evolution handling, and fail-closed rollback.

Add to the snapshot:

- the lethal opposing attack ID;
- its paid Energy cost;
- its exact deterministic damage and every public formula input;
- the projected post-Raging opposing Active HP;
- complete opposing Bench serial, card ID, and attached-Energy snapshot;
- the per-Bench proof that no printed attack is currently payable.

Any target, modifier, formula input, paid-cost proof, opponent-Active threat
result, or Bench-readiness result that changes before attack confirmation
clears the transaction. Before evolution confirmation, delegate unchanged to
the exact parent. After irreversible evolution, clear and recompute from the
actual state.

## Required positive

`87996118:96`:

- Raging Hammer leaves `743#26` alive;
- currently paid Powerful Hand `1072` uses public hand count `22` and
  deterministically deals lethal damage to our Duraludon;
- all five opposing Bench Pokémon have zero Energy and no payable printed
  attack;
- v2 evolves `840#92 -> 169#64`, confirms the exact state, then uses Coated
  Attack `1212` for the KO.

## Required negatives

- Historical-Silver seat 0, seed `271828271`, step `46`: parent-identical.
  Cinderace's paid 50-damage attack is nonlethal and a three-Metal Duraludon
  is visibly ready.
- Historical-Silver seat 0, seed `271828249`, step `36`: parent-identical for
  the same causal reasons.
- `88602602:118/120`: parent-identical because an existing Boss/Raging route
  already takes the same Prize.
- Lethal opposing Active plus any ready Bench attacker: veto.
- Nonlethal opposing Active plus an empty or unready Bench: veto.
- Threat requiring a future draw, Energy, evolution, switch, Ability,
  Supporter, hidden card, or chance: veto.
- A paid Basic Bench attacker remains a ready successor even if prospective
  Coated protection would block its damage.
- Every original H5 v1 negative remains.

## Forbidden generalizations

Do not add:

- prize-disparity or comeback mode;
- Alakazam, Cinderace, archetype, episode, seed, or HP-specific rules;
- opponent-action prediction or hidden-hand inference;
- future attachment/evolution probability;
- generic KO preference, threat ranking, or Bench-Energy heuristics;
- prospective Coated protection as a successor-readiness exemption;
- any H1 through H4 or H5 v1 stack.

## Verification gates

Focused and exact engine:

- complete the exact positive in both logical seats;
- keep both harmful fixed starts parent-identical;
- test lethal/no-successor, lethal/ready-successor,
  nonlethal/no-successor, and uncertain-damage states orthogonally;
- test all duplicate, repeated-callback, reset, rollback, modifier,
  restriction, and irreversible-evolution paths;
- require zero invalid actions, stale transactions, exceptions, or
  max-step hits.

Shadow:

- use the complete frozen replay corpus;
- require 100% certificate-external equality;
- Root inspects every natural trigger;
- every first difference must be exact inherited Raging Hammer versus the
  certified `840` evolution, followed by the intended Coated KO.

Fixed-760:

- require exact schedule and unique-key equality;
- require exact duplicate controls;
- require zero action errors, exceptions, faults, or max-step hits;
- require no regression overall, on the primary anchor, by seat, panel, or
  opponent-seat cell;
- both v1 harmful fixed starts must be parent-identical;
- every difference must be attributable to the selected public
  lethal-threat/no-ready-successor mechanism.

A repeated or new causal regression rejects v2.

## Limited live rule

If fixed-760 is exactly neutral at `478/760` for both policies, with zero
paired gains/regressions, every cell unchanged, both harmful states
parent-identical, and the full shadow contains only the certified source
difference, Root may authorize one limited exploratory live probe after all
package and prewrite checks.

This does not promote v2 to formal parent. Parent-identical live games provide
no evidence. Any causal loss or action fault stops the probe. No public trigger
by roughly 40 games means retain inactive. Formal promotion requires repeated
v2-owned triggers, both-seat safety, at least one mechanism-confirmed match
conversion, and practical absolute strength.

