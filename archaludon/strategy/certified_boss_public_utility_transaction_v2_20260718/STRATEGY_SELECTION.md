# Certified Boss public-utility transaction v2

## Decision

Implement one generalized Boss certificate directly from the exact accepted
Alakazam v6 parent.  The rejected v1 is implementation reference only.  This
is a practice-first candidate: local play is used to reject broken behavior,
while live games provide the final distribution test.

The v1 suppression was too broad: it lost 9 of the fixed 144 pairs and changed
which duplicate Boss remained in hand.  The v2 must preserve the exact Boss
option, serial/fingerprint and target selected by the parent, and may retain a
top-ranked Boss only through one of these public-state branches:

1. exact same-turn KO with a uniquely legal certified attack and prize gain at
   least as large as the guaranteed current-Active gain;
2. higher-prize near-KO, with exact residual HP in `1..20`, target worth at
   least two prizes and strictly more than the current-Active guaranteed gain;
3. public tempo control where all Energy units, printed attack costs and
   retreat cost are exact, no attack is currently payable, retreat is positive,
   and the target is Basic, has retreat cost at least two, or has exact attached
   Energy while remaining unable to attack.

The tempo branch releases after the exact switch and does not force an attack.
Unknown or mismatched state fails closed to a fresh legal parent choice.  Existing
Fez/Hilda/Enriching/Run Away latches and singleton-loss protections retain
priority.  Uncertified top Boss is suppressed.

## Required boundaries

- Reject the five observed live bad Boss starts.
- Preserve exact duplicate-Boss identity.
- Preserve exact KO, Fez-at-10 near-KO, and certified energy/retreat-tax cases.
- Reject Fez-at-30, equal-prize Hydrapple-at-10, unenergized Stage-1 Kadabra
  retreat one, free-retreat Mimikyu/Cinderace, attack-ready Alakazam, and
  unknown or variable energy/cost states.
- Boss-nontop states must remain identical to the exact v6 parent.

## Short local gate

Run the candidate on the immutable 144-row schedule against the reused exact
v6 parent rows.  Require valid deterministic execution with no action errors or
max-step hits; total wins at least 78, P0/P1 at least 44/34, known/fresh at
least 39/39, Rmy/Oselcoun/Historical-Silver at least 9/7/5, and every other
opponent no more than one win below the parent.  Inspect every first difference.
Passing this gate authorizes packaging and a live probe; it is not treated as
proof of Bronze strength.

## Ownership

Sol-Ultra selected the rule and later judges the fixed evidence.  Sol-xhigh
implements and root independently verifies, packages and performs every Kaggle
write.  No subagent may submit.
