# Continuity suite live-score diagnosis

## Scope

This is analysis only. No policy or deck source is changed.

The prior task asked for preventable-loss discovery and regression analysis.
Implementation requires a separate, explicit user instruction.

## Compared submissions

| Submission | Source | Public games | W-L | Current score |
|---|---|---:|---:|---:|
| 55099164 | direct parent | 55 | 32-23 | 763.724781 |
| 55113800 | continuity suite | 33 | 19-14 | 690.390899 |
| 55116478 | exact same continuity-suite archive | 1 | 1-0 | 715.101510 |

The two continuity-suite submissions use the exact same source and archive.
The second score has only one public game and is not a converged estimate.

## Raw win-rate comparison

- Continuity suite: 19/33 = 57.58%
- Current direct parent: 32/55 = 58.18%
- Direct parent before its newest loss: 32/54 = 59.26%

The suite versus current-parent difference is only -0.61 percentage points.
Its independent Newcombe 95% interval is
`[-21.27, +19.48]` percentage points. Fisher's exact test gives `p = 1.0`.
The available games do not establish a strength regression.

Wilson 95% intervals:

- 19/33: 40.81% to 72.76%
- 32/55: 45.03% to 70.26%
- 1/1: 20.65% to 100%

The one-game repeat cannot be used as a stable estimate.

## Why equal records produced different scores

The direct parent and suite both had exactly 19 wins and 14 losses after their
first 33 public games.

At that same game count:

| Submission | W-L | Score | Mean opponent initial score |
|---|---:|---:|---:|
| Direct parent | 19-14 | 741.2 | 683.0 |
| Continuity suite | 19-14 | 690.4 | 638.8 |

The score system is path- and opponent-sensitive:

- The parent won its first public game and moved from 600 to 707.5.
- The suite lost its first public game and moved from 600 to 492.9.
- That first suite loss was parent-identical; no new rule fired.
- The suite then recovered to 690.4 over the next 32 games.
- The exact same source's repeat won its only public game and moved from 600
  directly to 715.1.

The 24.71-point spread between two identical-source submissions is direct
evidence of live-score sampling sensitivity, although one game versus 33 games
is insufficient to estimate a stable variance.

## Matchup composition

Over the first 33 games, the direct parent obtained:

- Mega Lucario: 7-2
- Archaludon mirror: 4-0

The suite obtained:

- Mega Lucario: 5-6
- Archaludon mirror: 0-1

The suite compensated elsewhere and still reached the same overall 19-14
record, but its wins came against a lower-rated opponent sample. This explains
why equal W-L records produced different ratings.

## Exact policy-difference audit

Root replayed all 33 public suite games:

- callbacks: 1,691
- candidate-parent action differences: 1
- episodes with a difference: 1
- recorded-action mismatches: 0
- invalid actions: 0
- exceptions: 0

Thirteen of the fourteen losses were exactly parent-identical at every action.
They cannot have been caused by the five new continuity rules.

The sole difference was episode 89006709, step 84:

- Parent: evolve the damaged, zero-Energy Active Duraludon 63.
- Suite: evolve the one-Energy Bench Duraludon 64.
- Rule: `SACRIFICIAL_ACTIVE_BENCH_EVOLUTION_ROUTING_V1`.

The qualitative counterfactual audit judges the suite action beneficial with
medium confidence:

- the one-prize Active was allowed to absorb Aura Jab;
- the already ready, Cape-protected Archaludon ex 69 was promoted and attacked
  immediately;
- the newly evolved Bench line was subsequently charged and became the next
  ready attacker;
- the parent Active-evolution route would leave a damaged, zero-to-one-Energy,
  two-prize Active that survives but cannot attack or retreat efficiently.

The parent route flipping the loss is publicly implausible, although hidden
post-divergence draws prevent absolute proof.

Therefore the only observed live firing does not support the hypothesis that
the suite caused the score drop.

## Separate inherited policy defect

Episode 89006709 also exposes a different, inherited limitation later in the
game.

At steps 136-142:

- Active Archaludon ex 69 had 20 HP;
- Bench Archaludon ex 67 had 300 HP and three Energy;
- moving to the healthy attacker preserved the same knockout;
- the policy attacked from the 20-HP Active and exposed two prizes to Aura Jab.

The installed healthy-ready rotation rule recognizes only its exact
Mega-Starmie source lane and did not generalize to this visible Mega-Lucario
lane.

This is a credible future countermeasure candidate, but it is not implemented
in this analysis task.

## Parent-identical loss buckets

The thirteen parent-identical losses consisted of:

- Mega Lucario: 5
- Alakazam: 3
- Mega Starmie: 1
- Archaludon/Cinderace mirror: 1
- Team Rocket Spidops/Mewtwo: 1
- Dragapult: 1
- Great Tusk/Crustle: 1

These represent inherited setup, matchup-engine, prize-tempo and resource
failures rather than regressions introduced by the suite.

## Conclusion

The current evidence does not show that the new implementation is weaker.

The observed score decline is principally explained by:

1. every new submission restarting at 600;
2. an early first-game loss instead of the parent's first-game win;
3. lower-rated opponents;
4. a materially worse sampled Mega-Lucario block;
5. only 33 games, with the repeat having only one public game.

The new suite changed one of 1,691 live decisions. That change was beneficial,
not harmful. A genuine inherited weakness was found in the later
healthy-attacker rotation decision, but no source modification is authorized
or performed here.

## Evidence

- Raw refresh:
  `autonomous_gold_20260715/evidence/continuity_suite_score_drop_refresh_20260731`
- Root shadows:
  `autonomous_gold_20260715/root_verification/continuity_suite_score_drop_20260731`
- Causal audit:
  `autonomous_gold_20260715/strategy/continuity_suite_score_drop_20260731/episode_89006709_audit/EPISODE_89006709_CAUSAL_AUDIT.md`
