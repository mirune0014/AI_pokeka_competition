# Rule 2 trial implementation report

## Scope

- Accepted parent: `archaludon_historical_silver_single_resolver_salvage_v1`
  (`main.py` SHA-256
  `153D8461FB66927DB9731CBE614B71FF5398B8EAE8980AE0BB4D46ADD0E8792A`).
- Trial: `archaludon_historical_silver_single_resolver_salvage_rule2_trial_v1`.
- Added rule only: `EXACT_LONE_ACTIVE_REPLY_KO_CONTINUITY_V1`.
- The trial keeps Rule 1 in the same `main.py`, calls the unchanged exact
  Historical-Silver module once per callback, and has one final `agent`, one
  `_resolve`, and at most one Rule 2 transaction owner.
- No score function, chooser, deck, search rule, Supporter rule, Boss rule,
  generic effect simulator, hidden-hand inference, or lookahead was added.

## Behavior

Rule 2 starts only when the exact parent selected one registered nonterminal
attack from the sole Active, the own Bench is empty, and a fixed-fingerprint,
currently paid attack on the opposing Active has a public conservative lower
bound that KOs the own Active without ending the game by Prizes. Unknown Tool,
Stadium, status, Energy, attack, option binding, or effect information returns
the exact parent action.

The allowed registry is exactly attacks `61/223/224/253/965/1212/1072`.
Normal reply damage subtracts public Resistance and exact Full Metal Lab; it
does not add Weakness. Powerful Hand is handled as damage counters. A current
Coated Attack against a Basic opposing attacker does not certify a normal
damage reply KO.

Exactly one complete preparation route must exist:

1. one exact hand Duraludon or Relicanth PLAY, then the frozen attack;
2. one exact Night Stretcher PLAY, one exact discarded Duraludon/Relicanth
   recovery, that same serial's PLAY, then the frozen attack; or
3. sole Active Duraludon EVOLVE to non-ex Archaludon, only when inherited
   damage leaves raw HP above the frozen reply, current Basic Energy pays
   Coated Attack, and Coated Attack remains non-KO.

Every continuation rebinds serial/target/attack semantics against the current
option order. Same-prompt retries return the same semantic action. Any route
postcondition failure clears the owner and returns the exact parent action.

## Frozen hashes

| File or tree | SHA-256 |
|---|---|
| trial `main.py` | `D2BC5FCC82A5A507B7C5CC9FEDAAC4ED6EA0BE1622EBE99EFC74B6E6A926FC62` |
| exact Historical-Silver `_historical_silver_parent.py` | `F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E` |
| exact `deck.csv` | `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A` |
| focused fixture | `873639AEC82300AA50546FB3DFC0660745BFBC67E2155CDC3EC8119A3A5EFB3E` |
| final smoke seat 0 summary | `986060BAE23025D865E8485345804B3B8CCAD579E8AF6DE543DCF2717D2F8089` |
| final smoke seat 1 summary | `4894F78FC0A3D070698D4B619299A9F587D27014A00B54706033471C025C1A14` |
| current-shadow tree, 45 reports | `901F80150D3119E9A098CD0F36B97F5EA6AE933048282E87CFC1C9DDBA6EEDEE` |
| historical-shadow tree, 32 reports | `7C31C6534B6FF4750D8FAA6761E63456A570CC42E779403BD9BD2C353CEBB83E` |

All non-`main.py` regular candidate files are byte-identical to the accepted
parent. The exact parent and deck hashes match the frozen requirement.

## Verification

### Focused fixture

Command:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
py -3.11 -B -m unittest discover -s autonomous_gold_20260715/implementation/archaludon_historical_silver_single_resolver_salvage_rule2_trial_v1/tests -p test_*.py -v
```

Final outcome: exit 0; 9/9 test groups passed. Coverage includes both seats for
all three positive routes, Metal Defender and Powerful Hand replies, option
reversal, duplicate retry at direct/evolution/Night recovery/Night Basic
stages, route multiplicity, parent non-attack, parent KO, existing Bench,
unpaid or unregistered reply, final-Prize reply, status/Tool/Stadium unknowns,
Coated-vs-Basic defense, transaction abort, Rule 1 retention, and structural
one-agent/one-resolver/one-parent-call checks.

### Compile/import/deck/loader/cache

In-memory compile covered final `main.py`, exact parent, and fixture. Import
passed. Deck count is 60 and ACE SPEC count is 1. AST counts are one top-level
`agent` and one `_resolve`; `agent` contains one `_parent.agent` call. The
final `agent` remains the last locally defined callable. No `__pycache__` or
`.pyc` remains under the trial candidate or evidence directory.

### Both-seat exact-engine smoke

The checked `tools/run_local_battle.py` and seeded engine ran the trial once in
each seat against exact Historical-Silver.

- candidate seat 0, seed `803202611`: 108 steps, action errors 0, max-step false;
- candidate seat 1, seed `803202612`: 42 steps, action errors 0, max-step false.

Both games reached a normal terminal result. No archive was created.

### Checked replay shadow

`tools/compare_replay_agent_actions.py` compared accepted Rule 1 parent against
this trial on the same frozen corpus used for Rule 1:

- 45 readable current reports;
- 32 deterministic historical-sample reports;
- 4,262 callbacks total;
- candidate-parent differences: 0;
- invalid option positions or comparison exceptions: 0.

Current episode `89287701` remains the already-known malformed source and was
not replaced. There were no first differences to classify. Consequently this
shadow proves retention and runtime safety but gives zero natural Rule 2
starts.

## Known tradeoff and evaluator gate

The rule is intentionally conservative: any Tool, non-Full-Metal-Lab Stadium,
Special Energy, special condition, unregistered attack, multiple preparation
route, or uncertain effect keeps the parent. This may make the rule dormant;
the contract forbids widening it in response.

Run the frozen fixed160 from this final source. If shadow plus fixed160 still
has zero natural starts, preserve this implementation record but do not merge
the trial into the accepted parent. Otherwise inspect every Rule 2 first
difference and apply the frozen gains/regressions, seat/opponent floor, and
fault gates. No fixed160/fixed760, package, commit, push, or Kaggle operation
was performed here.
