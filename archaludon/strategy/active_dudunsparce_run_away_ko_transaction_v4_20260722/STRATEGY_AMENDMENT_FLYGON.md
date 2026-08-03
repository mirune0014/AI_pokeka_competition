# V4 controlling amendment: mixed owner-turn/reactive skills

This amendment supersedes the claim that every skill containing
`once during your turn` is necessarily inert during the owner's off-turn.

The legal-pool audit found Flygon `824`, Sandy Flapping. Its normalized text
contains both `once during your turn` and a second activation route when the
Active Flygon is Knocked Out by attack damage. It therefore must not enter the
no-effect envelope.

An opponent visible Pokemon skill is admissible only when:

1. its normalized text contains exact `once during your turn`; and
2. it contains neither `damaged by an attack` nor
   `knocked out by damage from an attack`.

Empty skill lists remain admissible. All other skill texts reject the start.
This retains Kadabra Psychic Draw, Drakloak Recon Directive, and Dusclops Cursed
Blast in the mandatory natural starts while rejecting Flygon Sandy Flapping.

Focused tests must add Flygon `824` as an exact parent-END/no-latch negative.
The legal-pool audit artifact must enumerate all currently admitted owner-turn
skills and separately show that Flygon is rejected. No broader exception is
authorized.
