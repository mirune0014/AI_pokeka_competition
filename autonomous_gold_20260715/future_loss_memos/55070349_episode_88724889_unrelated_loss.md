# Future-loss memo: H3 submission 55070349, episode 88724889

## Scope and causal boundary

- Submission: `55070349`, H3 v2 line-formation Explorer-veto.
- Episode: `88724889`, target seat `0`, public loss.
- Correct-seat shadow: 30 callbacks, H3-owned callbacks `0`,
  H3-parent action differences `0`, rollbacks `0`, invalid actions `0`,
  exceptions `0`.

This loss contains no H3 behavior. It is not evidence for an H3 defect or H3
strength. The ideas below are separate future hypotheses and must not be
stacked into H3.

## Future hypothesis A: remove a visible Bench successor instead of chipping a non-KO Active

At step `59`:

- our Active is Archaludon ex `190#10`, 300 HP, three Metal Energy;
- our Bench is Duraludon `169#6`, 130 HP, two Metal Energy;
- hand contains two Boss's Orders `1182`, Archaludon ex `190`, Lillie
  `1227`, and one Metal;
- opposing Active is Mega Lucario ex `678#75`, 340 HP, two Fighting Energy;
- opposing Bench includes Riolu `677#72`, 80 HP, a public successor into a
  second Mega Lucario ex;
- Metal Defender `253` deals 220, so it does not KO the current Active but
  does KO the visible Riolu;
- Boss is legal and the Supporter is unused.

The historical parent first attached Metal to the Bench, then at step `60`
used Metal Defender into the Active for 220. The opponent later removed the
Bench Duraludon, our Archaludon KO'd the damaged Mega Lucario, and the second
Mega Lucario line took the final board KO.

Candidate question:

> When the inherited attack cannot KO the current Active, but Boss plus that
> same attack can KO a unique visible evolution seed for the opponent's next
> already-demonstrated high-damage attacker, should threat removal outrank
> non-KO Active damage?

This is a promising bench-threat-denial example, but not yet a hard rule.
Moving the current Mega Lucario to the Bench may let it return through a
publicly unknown future switch/retreat route, and the replay does not prove
that removing Riolu wins. A future isolated candidate needs:

- same inherited attack before and after Boss;
- public proof that the Bench target is a relevant successor lineage;
- current-Active non-KO and target KO certificates;
- attack-continuity and Prize-route comparison;
- a veto for terminal or higher-Prize current-Active routes;
- negative tests for cheap retreat/switch, multiple equivalent successors,
  and targets whose removal does not reduce the opponent's next-turn attack
  set.

Evaluate this as a bounded future-value rule, not an unconditional Boss rule.

## Future hypothesis B: board-collapse mode before a nonterminal attack

The same position has only two Pokémon. The visible opposing board has an
already-powered Mega Lucario and a second Riolu lineage. Taking the
nonterminal 220-damage attack does not win this turn and leaves both of our
Pokémon inside the opponent's demonstrated 300-damage sequence.

A future comeback/survival mode should ask whether a nonterminal attack leaves
an unavoidable public two-KO board-collapse route. If so, it may prioritize a
certified additional Basic, durable evolution, or disruption route before
attacking.

This replay does not supply a deterministic positive for that rule:

- no Basic Pokémon is already in hand at step `59`;
- evolving the Bench still leaves it within the demonstrated 300 damage;
- Lillie is legal but its useful draw is hidden and probabilistic;
- the available observations do not prove that delaying the attack survives.

Therefore this is a search target, not an implementation authorization. Find a
separate replay or exact-engine state with a public, legal survival route
before turning it into a hard gate.

