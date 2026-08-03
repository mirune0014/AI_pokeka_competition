# Final rule judgment: H1 exploratory live probe

## Verdict

Permit one exploratory live probe of the exact frozen
`archaludon_certified_endgame_alakazam_boss_transaction_v1`, source SHA-256
`CC7C2C53EC49BF4C690D6CD686DFB8BBA0041F1EA8F174C8B91135FBBA33DC49`.

This is a safety permission only. H1 is not accepted as the formal parent and
has no demonstrated strength gain.

## Evidence

- H1 is a direct child of exact historical-Silver and retains the exact deck.
- Across 10,319 historical callbacks, it changes exactly
  `88457867:144`.
- The exact engine completes Boss `1182` -> unique Alakazam `743` -> Metal
  Defender `253`.
- Trigger-external equality is 10,318/10,318; invalid actions and exceptions
  are zero.
- Independent numerical audit
  `NUMERICAL_AUDIT.md`
  (`7F427959C752405FFCD446EA66AECDFE9997754EE05FEF569240BA10824E1B5C`)
  finds parent and candidate exactly 478/760, with zero gains, regressions,
  discordances, action errors, or max-step hits.
- Root recomputation
  `ROOT_NUMERICAL_RECOMPUTATION.md`
  (`E6A606A5925C882BD5E07D6F52A95894755A5792CE76E8FAFF758751DEC6E589`)
  agrees.
- Current-parent loss `88669861` contains zero H1 action differences and is
  unrelated.

The mechanism is coherent: at exact 3/2 Prizes, both available KOs take the
same one Prize, but the Boss line removes the unique visible Alakazam whose
public Powerful Hand damage takes the opponent's final two Prizes. It does not
use hidden information or model opponent behavior.

## Pre-submit conditions

Root must package only the frozen candidate source and unchanged deck, verify
archive contents and hashes, rerun package validation and both-seat smoke,
reject any hash drift, and submit no stacked rule or broader planner.

## Monitoring and rollback

Shadow every new correct-seat callback after submission. Immediately reject H1
and return to exact historical-Silver on the next slot if any of the following
is verified:

- execution failure, invalid action, exception, nondeterminism, or max-step;
- a trigger outside exact 3/2 and the complete public certificate;
- a trigger-external first difference;
- a target other than the unique certified Alakazam;
- failure to complete Boss -> stored target -> Metal Defender;
- transaction state leaking across turn, seat, or game;
- an H1-caused regression where the legacy Active KO avoids a loss that Boss
  creates;
- mature live performance becoming clearly weak around 700 or below.

Ordinary score noise and unrelated losses are not rollback evidence.

An H1 activation counts only when the parent/candidate first difference is at
the certified MAIN callback, exact 3/2/equal-one-Prize/unique-ready-terminal
Alakazam conditions hold, Boss selects the stored serial, and Metal Defender
KOs it.

H1 may become the formal parent only after at least two independent live
activations, exact mechanism confirmation in both, no attributable regression,
no trigger-external fault, and mature absolute performance not practically
weaker than the exact parent. Until then, later candidates remain direct
children of exact historical-Silver.
