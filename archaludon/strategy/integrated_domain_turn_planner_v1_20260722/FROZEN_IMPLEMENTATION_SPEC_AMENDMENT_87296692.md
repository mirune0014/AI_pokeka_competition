# Controlling amendment — episode 87296692 setup continuity

This amendment supplements, and does not weaken, the frozen integrated-domain
planner specification.

At episode `87296692`, turn 3, step 20, the public field has Active Dunsparce,
Bench Genesect, no Abra line, no attached Energy, deck 44 and six Prizes. The
Hilda second `TO_HAND` prompt offers Basic Psychic, multiple Telepath Psychic
Energy copies and one Enriching Energy. The current and cumulative Boss parent
choose Telepath even though no Psychic target exists, it cannot advance H0,
and no paid/certified H1 exists. Unique unspent Enriching provides a mandatory
four-card setup draw within the safe turn-based deck clock.

Required integrated invariant and fixture:

- During a Hilda Energy selection, when H0 takes zero Prizes, no paid/certified
  H1 attacker exists, no Psychic target can use Telepath's public Bench effect,
  Enriching is unique and unspent, and the ordered deck clock safely budgets
  four draws, select/reserve Enriching and carry the transaction through its
  legal attachment before permitting END.
- Genesect's mere presence on Bench must not satisfy H1 readiness.
- At step 27, with Active Dudunsparce at zero Energy, only Genesect on Bench,
  no Abra line, deck 42/six Prizes and no other action certifying H1, Run Away
  Draw must outrank END under the same plan. This is a safety backstop, not a
  replay-action label: it follows from the public H0/H1/DeckClock objective.
- Fail closed to the cumulative parent if Enriching uniqueness, effect
  availability, target/attachment continuation or the four-draw clock cannot
  be certified.

Both S20 and S27 must be focused fixtures. Failure to cover them is a missing
required principle implementation and therefore a structural gate failure;
their eventual match outcome is not a local-win adoption gate.
