# Root verification: Task 5 Poké Pad search plan

Date: 2026-08-02 JST

## Scope and frozen inputs

- Parent: `archaludon_public_pre_attack_executable_successor_bench_zero_continuity_gate_v1`
- Parent `main.py` SHA-256: `CAF2C696AE9F6102C1A4A8E67649C309104064CAABF9643865BE766D91BDE8DD`
- Candidate: `archaludon_public_poke_pad_declared_executable_role_transaction_v1`
- Candidate `main.py` SHA-256: `2B23D3AFC63A5BDC4BC7765CE1656725ED01890D161E3D23DCC672BE7FCCCFF4`
- Deck SHA-256: `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`
- Rule: `PUBLIC_POKE_PAD_DECLARED_EXECUTABLE_ROLE_TRANSACTION_V1`

The candidate changes only `main.py`; the other 11 package entries are
byte-identical to the parent. The source diff is confined to the existing PFC
Poké Pad state/transaction region. It adds 574 lines and removes 184 lines.

## Implemented behavior

The rule is entered only after the cumulative parent has already selected
Poké Pad. Before emitting that action it declares one of two executable roles.

1. `DURALUDON_EXECUTABLE_SUCCESSOR`
   - bind Poké Pad on play;
   - choose a revealed Duraludon deterministically;
   - bind the returned physical copy;
   - place it when legal;
   - hand off to the existing Turbo Flare / energy / attack-continuity planner.
2. `NONEX_COATED_ATTACK_CONVERSION`
   - admit non-ex Archaludon only when the complete public same-turn
     evolve-to-Coated-Attack KO route is executable;
   - complete Pad, return-to-hand, evolve, attack and resolution as one owner.

If the declared target is absent, the transaction chooses an empty selection
only when that is legal and returns to the frozen exact attack on the following
MAIN callback. It does not substitute another Basic. Cinderace 666 is explicitly
excluded as a mid-game placement target because Explosiveness is setup-only.

## Root checks

### Focused transaction fixtures

- Command: `py -3.11 -B run_focused_fixtures.py`
- Result: `69/69` passed, `0` failed.
- Result SHA-256: `38EC63F37454779B0A991752751BE0A53DF1E50559BFA1702BB2251B93CF0530`
- Covered both seats, both admitted roles, complete callback continuations,
  absent-target return, capacity loss, duplicate/permutation stability,
  malformed/terminal callbacks, owner precedence and zero double-owner states.

### Historical replay shadows

- Episode `89347400`: 11 decisions, 0 invalid actions, 0 parent-candidate
  differences.
- Episode `89285518`: 74 decisions, 0 parent-candidate differences.
  Comparator output SHA-256:
  `75268BD613E4D5723CD02DDE6BA2F003632F3A1C77D7A0FC7713B30FBE97E75D`.
- Episode `89282820`: 60 decisions, 0 parent-candidate differences.
  Comparator output SHA-256:
  `15C31D6CD81FCF644FA7FEFD5B10C1A51367BF145CAD8FA238E5A91C55BBD414`.

The replay comparisons show that Task 5 does not perturb the recorded ordinary
paths. Multi-callback ownership is proven by the focused engine-shaped fixtures,
not inferred from static replay snapshots.

### Package and execution safety

- Compile/import: pass; final AST callable is `agent` and import returns a
  callable.
- Package entries: 12; deck: legal 60 cards; ACE SPEC count: 1.
- Cache artifacts: 0.
- Structural result SHA-256:
  `9B7FAA35535536F80725BD07B248E5A65F30AC3C6E4F09EA1E99AEA0720E80CF`.
- Candidate as first seat: 128 steps, action errors 0, max-step false.
- Candidate as second seat: 140 steps, action errors 0, max-step false.

## Verdict

**PASS for Task 5 implementation and as the parent of Task 6.**

An independent Sol-Ultra strategy judgment also returned **ACCEPT** with no
concrete contract or safety violation. It retained the same limitation: no
natural replay in this check produced a Task-5 action difference, so absolute
strength and ladder improvement remain unproven.

This verdict establishes deterministic validity, complete admitted-role
transactions and preservation of the checked parent paths. It is not a claim
of improved ladder win rate, and it does not authorize a Kaggle write by itself.
