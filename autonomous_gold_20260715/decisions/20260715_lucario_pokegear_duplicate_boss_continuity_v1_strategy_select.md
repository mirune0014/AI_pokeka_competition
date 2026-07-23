# Strategy selection - Lucario Pokegear duplicate-Boss continuity v1

## Decision

The required read-only Sol-Ultra judgment selected one isolated implementation
candidate.  It is not an adoption or submission decision.

The rule changes only a Pokegear `TO_HAND` choice in detected Lucario games:
when the turn's Supporter is already used, Boss is already held, no draw
Supporter is held, and the Pokegear options contain both a redundant Boss and
Explorer/Lillie, retain the held Boss and take the draw Supporter.  Explorer
has deterministic priority if both draw Supporters appear.

Exact implementation and point controls are frozen in
`evaluations/lucario_pokegear_duplicate_boss_continuity_v1/IMPLEMENTATION_SPEC.md`.
The candidate must then earn strength over three distinct complete Lucario
agent/deck variants, both seats, and disjoint seed blocks.  Historical Silver
and complete non-Lucario policies remain identity controls.  Any exposure,
follow-through, regression, seat/variant, confidence-interval, or identity
failure retires this exact implementation without loosening.
