# Root verification: Rule 8

Decision before fixed160: **PASS TO FROZEN FIXED160**.

This is permission to execute the required immutable schedule, not acceptance
of Rule 8.

## Frozen identity

- Rule 5 parent `main.py`: `D966E455E5110F9D5616195AEAAC8663E6A92F310DAFC4B7F79E4D37149A9C62`.
- Rule 8 candidate `main.py`: `B0BD42D71617EEA041AFCF54F84B9C92FD894A2A3A6BD1CCAD95645CD1952507`.
- Deck: `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`.
- Strategy: `6E9B540F6FC7E5927222725B1ED0D0280D10EE5989B24BD49D1D6E984303C04F`.
- Controlling amendment: `C6AAD9BAB0A3FC6F66A608236C22DA08F58D4A726E10AD7EAA035D456F17A6D5`.

## Independent source review

The parent/candidate diff adds only the Rule 8 constant, stateless exact
consequence and Pareto-proof helpers, the Rule 8 proposal/start function, the
final Rule 8 call after the existing Rule 5 Boss branch, and documentation
strings. It does not alter the Historical-Silver scorer, parent policy, deck,
existing Rules 1/4/5 behavior, transaction owner, or public interface. Rule 7
is absent.

The final resolver order is active owner, Rule 5 exact current win, Rule 4
materialization, Rule 5 strict higher-Prize Boss transaction, Rule 8 exact
same-Active dominance, then the once-computed Rule 5 parent action. Rule 8 is
stateless and cannot own or continue a transaction.

The only permitted semantic difference is the same Duraludon and target with
`ATTACK 223 -> ATTACK 224`. The proposal records the physical identities,
Energy refs, printed costs, zero resource/effect consequences, exact outcomes,
and strict dimensions. Every unsupported or ambiguous input returns the Rule 5
action.

## Root-executed checks

- Focused and inherited suite: 32/32 passed.
- Compile/import/layout verifier: passed.
- Top-level `agent`: one; `_resolve`: one; static parent call in `agent`: one.
- Runtime final callable: `agent`; Rule 7 absent.
- Deck: 60 cards; ACE SPEC: one.
- Cache paths: zero.
- Checked two-seat replay shadow rerun: 46 current plus 207 historical source
  paths, 252 readable replays, 30,977 callbacks, zero invalid actions, zero
  wrapper exceptions, zero natural Rule 8 starts, and zero differences.
- One known source replay (`89287701`) remains malformed at its existing JSON
  truncation and is not interpreted.
- Both-seat checked-engine smoke reported termination below 1,000 steps and
  zero action errors.

## Fixed160 gate

Run exactly the frozen 160-key schedule from Rule 5 versus Rule 8. Every first
difference must have a persisted same-attacker/same-target strict Pareto proof.
Any fault, unclassified difference, or harmful first difference rejects the
rule. If fixed160 also has zero natural starts, the controlling outcome is
`DEFER-DORMANT`; do not widen or integrate Rule 8.
