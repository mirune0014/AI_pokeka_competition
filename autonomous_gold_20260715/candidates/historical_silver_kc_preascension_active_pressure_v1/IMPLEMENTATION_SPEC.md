# Immutable implementation specification: Snotted Up escape v1

Frozen before source creation at 2026-07-15 10:04 JST.  This authorizes one
isolated deterministic source candidate only.  It does not authorize a deck
change, package, or Kaggle submission.

## Parent and destination

- exact parent:
  `autonomous_gold_20260715/baseline/historical_silver_archaludon_54495224`
- parent `main.py` SHA256:
  `F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E`
- parent `deck.csv` SHA256:
  `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`
- isolated destination:
  `autonomous_gold_20260715/candidates/historical_silver_snotted_escape_v1`
- `deck.csv` and bundled `cg/` must remain byte-identical to the parent.
- Only destination `main.py` may differ from the parent source.

## Root-verified evidence

The frozen trace reproduction and strict actual-cost audit are in
`autonomous_gold_20260715/evaluations/historical_silver_cubchoo_snotted_trace_seed2026071621`.

- diagnosis spec SHA256:
  `01FAD9623FE51AF3A22183167AC24C652A1CFF3D301A6341C120F730BE498971`
- active strict-positive CSV SHA256:
  `FD6A61CA614F424345D63CA2AE32444656BA517D4E68B5E04509D5435708DCB7`
- strict opportunities: 144 total, seat 0 87, seat 1 57;
  141 in losses and 3 in wins.
- Independent root recomputation had zero key differences.
- Gravity Gemstone 1166 removed seven printed-cost false positives.
- Matching wins require useful setup/evolution to retain priority over the
  escape.  The escape is selected over END, not forced as the first action.
- Sol-Ultra strategy judgment: `SELECT` this one source rule.

## Exact rule

Do not change deck construction, attack scoring, promotion scoring, setup,
search, attach, evolution, supporter, or matchup logic.

At a MAIN Retreat option, preserve the existing `13000` attack-ready retreat.
Otherwise return exactly score `1` for the new escape only when every condition
below holds:

1. `_opp_last_attack_id == 716`.
2. The current Active can pay at least one printed attack with positive damage
   or a beneficial public effect.
3. The current MAIN prompt contains no legal Attack option.
4. The Retreat option is legal (it is the option currently being scored).
5. The Bench Pokemon that the unchanged existing promotion policy would choose
   can currently pay a printed attack with positive damage or beneficial public
   effect against the visible opponent Active.  A Cornerstone-blocked route is
   not positive.
6. After the retreat and promotion, at least one *different* Pokemon remains as
   an attack-ready reserve for the next lock.  The former Active may count only
   with its Energy after the actual retreat payment.  Another unchanged Bench
   Pokemon may also count.  The reserve requirement may be waived only if the
   promoted Pokemon has a checked same-turn attack that immediately wins the
   game.

The actual retreat cost is conservatively computed as:

```text
max(0,
    printed retreat cost
    + count(Gravity Gemstone 1166 attached to either Active)
    - 2 if Air Balloon 1174 is attached to the retreating Active else 0)
```

No hypothetical Switch card is admitted.  The candidate must not infer a
learned action, replay label, or opponent-policy proxy.

## Priority and safety invariants

- Existing useful PLAY, ATTACH, and EVOLVE scores remain above `1`.
- Active evolution that clears the lock and enables Metal Defender remains
  above the escape.
- END remains `0`.
- If the strict predicate fails, retain the exact parent tank score `-5000` or
  generic score `-100` as applicable.
- The unchanged promotion policy must actually choose the attack-ready target;
  do not add a new target-selection override.
- The rule must stop applying after a promoted Pokemon has a legal Attack
  option.

## Required worker checks

- Copy the exact parent into the isolated destination without touching the
  parent or any other candidate.
- Keep `deck.csv` and `cg/` byte-identical.
- Compile the destination source.
- Run a small deterministic smoke check that reaches the new branch and one
  negative control if possible, but do not run or interpret the frozen full
  evaluation and do not submit.
- Return a concise source diff, hashes, smoke commands, exits, and observed
  action types.  Numerical promotion remains the root's separate workflow.
