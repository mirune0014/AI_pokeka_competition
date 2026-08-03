# Future Archaludon hypotheses

These observations are intentionally excluded from the first candidate. They
must be reconsidered one at a time from the strongest accepted parent after the
current live mechanism has been evaluated.

## Prize-route arbitration

- `88417236:70`, `88171291:39`, `87974582:72`, `87892692:48/51`,
  `88096059:114`: Boss was suppressed because the Active was KOable although a
  Bench target yielded more Prizes for the same current attack.
- `87825800:116/124`: a damaged three-Prize Mega Lucario ex was publicly
  KOable on the Bench while the policy took or pursued a lower-value Active.
- Candidate idea: exact same-turn higher-Prize KO certificate, below immediate
  match win and independent of threat forecasting.

## Exact last-Prize resource transaction

- `88017509:114-125`: with one Prize left, held Boss and a 110-HP Solrock on
  the Bench, Night Stretcher recovered Duraludon instead of the visible Metal
  needed to attach, Boss, and Metal Defender for game.
- Candidate idea: reserve every publicly available component of an exact
  same-turn last-Prize line across recovery, attachment, Boss target, and
  attack callbacks.

## Attack-completing Energy reservation

- Root-verified replay:
  `evidence/live_54927163_refresh_20260729_0344/episode_88584180_replay.json`,
  SHA
  `047A9FC4AB682E4F9E22F0AFE8547CB7F3016D98C2021E76C36D75C46CDD27B0`.
- At seat 1, step `90`, Active Archaludon ex `190#67` had exactly two Basic
  Metal `116,117`. Manual attachment was unused and the unique visible hand
  Metal was `8#120`.
- Root independently reran the exact parent scorer:
  - Ultra Ball `1121#81`: `20,000`, `Ultra Ball: fuel Alloy`;
  - attach `8#120` to Active `190#67`: `19,700`;
  - attach it to Bench Duraludon `169#63`: `10,300`;
  - End: `0`; Retreat: `-100`; Night Stretcher: `-500`.
- Ultra Ball therefore won by 300 points. The next discard callback selected
  `8#120` with Night Stretcher, searched Archaludon ex, and reached a state
  with only Retreat/End. Metal Defender `253` was not used that turn.
- Attaching `8#120` to the Active exactly completes printed
  `{M}{M}{M}` Metal Defender. It deals positive deterministic damage but does
  not KO the 310-HP Grimmsnarl, so this is an attack-continuity certificate,
  not a Prize or match-win certificate.
- Future H6 experiment: reserve `(turn, attacker serial, Energy serial,
  attack ID)` when exactly one visible Basic Metal completes the current
  two-Metal Active Archaludon ex attack, attachment is unused, the attack is
  not already legal, public conditions do not block it, and no certified
  terminal/equal-higher-Prize route has precedence. Defer only actions that
  consume the reserved card, attachment, attacker, or turn. Confirm the exact
  attachment, allow safe Stadium/healing/search actions afterward, and select
  attack `253` before Retreat/End.
- Mandatory controls:
  - `88584180:111-114` must retain Full Metal Lab before attachment and Jumbo
    Ice Cream after attachment;
  - `88584180:142-143` remains a parent-identical ordinary attach/attack;
  - zero/two visible Metal, one/three Active Energy, attachment already used,
    blocked/zero-damage attack, Bench-only completion, and a higher-priority
    Prize route do not arm.
- Do not generalize to `never discard Metal`, `always attach before Items`,
  speculative future attacks, Duraludon/Raging Hammer, an episode rule, or a
  claim that this non-KO converts the match. The missed turn-10 attack is
  proven; the alternate full-game win is not.

## Non-KO exposure and next-attacker continuity

The legacy summary below is superseded by two separate sibling hypotheses.
They must not be combined into a generic investment score.

### H7-A — preserve the sole ready successor during a non-KO

- Root-verified replay:
  `evidence/live_54927163_refresh_20260729_0344/episode_88660007_replay.json`,
  SHA `CE2B...AE2F`.
- At callbacks `81-82`, the parent preferred the damaged Active
  (`13,500` then `18,500`) over the zero-Energy Bench Archaludon ex
  (`11,200`) and placed both recovered Metal Energy onto the Active.
- Full Metal Lab reduced Metal Defender to `190`, which did not KO. The
  opponent's visible return attack dealt `190`, KOed that Active, and left the
  Bench Archaludon ex with zero Energy.
- Future isolated experiment: before a publicly certified non-KO, veto an
  allocation that places the only available Energy on the exposed Active when
  this leaves every Bench successor without a payable printed attack and the
  opponent Active already has a payable deterministic KO.
- Required negatives: the current attack KOs; the Active survives every
  payable public return attack; another Bench Pokemon remains ready; the
  allocation itself creates an immediate Prize or terminal line; Energy must
  be placed on the Active by a forced effect.
- This is a continuity rule, not a blanket preference for Bench Energy or a
  claim that the alternative wins the recorded game.

### H7-B — choose the expendable promotion only when it does not forfeit an attack

- Root-verified replay:
  `evidence/live_54927163_refresh_20260729_0344/episode_88507294_replay.json`,
  SHA `7E057...F45`.
- At forced-promotion callbacks `73` and `77`, all Duraludon had the same
  inherited score (`8,000`) despite materially different investments:
  `3/2/0` Energy and later `2/0` Energy. The tie exposed the
  highest-investment Duraludon while lower-investment legal sacrifices existed.
- Callback `38` is a mandatory negative. Promoting the invested Duraludon was
  correct there because the held Archaludon `840#32` enabled a same-turn
  Coated Attack `1212` KO on the 110-HP Cinderace; the parent had assigned the
  evolution a negative score.
- Future isolated experiment: during a forced promotion, prefer the
  lowest-future-value legal sacrifice only when no candidate can be proven to
  attack or produce an immediate higher-priority Prize line this turn. When a
  promotion plus visible hand/evolution/attachment resources completes an
  attack, that exact attack-completing route overrides the sacrifice rule.
- Required negatives: unique legal promotion; terminal Prize line; only one
  Pokemon remains; an invested candidate is the sole provable same-turn
  attacker; retreat or switching immediately undoes the exposure.
- Do not generalize this to `always promote the lowest-Energy Pokemon`.

- `88660007:78-83`: Assemble Alloy put both Metals onto a damaged Active for a
  public non-KO; the Active was KOed and the new Bench Archaludon ex remained at
  zero Energy.
- `88507294:37-41/73/77`: promotion ties repeatedly exposed the
  highest-investment Duraludon for non-KO attacks while lower-investment legal
  sacrifices existed.
- Candidate idea: a narrow non-KO plus visible-retaliation veto that preserves
  the sole ready or highest-investment successor. Do not implement a generic
  “save Energy” preference.

## Forced-Active recovery before redundant Bench investment

- Live H1 loss `88683647`, seat `0`, callback row `39` on turn `6`:
  Lisia's Appeal had stranded a confused, 0-Energy Active Duraludon while a
  one-Energy Duraludon sat on the Bench. A Metal attachment to the Active
  immediately reopened Hammer In and advanced its two-Energy retreat, but the
  parent selected the Bench because of its unconditional Crustle Bench-Energy
  bonus, then ended the turn.
- The same priority kept the Active at zero Energy while later Metals were
  added to Bench targets at callbacks `63`, `78`, `89`, and `95`. The agent
  attacked on turns `2` and `4` and never restored attack continuity.
- Future isolated hypothesis: if a forced Active cannot attack or retreat,
  prioritize an attachment that immediately enables its attack or advances a
  deterministic escape before redundant Bench investment, subject to exact
  confusion/self-damage, Spiky Energy, Prize, and successor-value guards.
- H1 was parent-identical across all `44` callbacks; this is not an H1 or H2
  repair. Risks are weakening a three-Energy successor and investing into an
  Active that should instead be sacrificed.

## Visible mill-lethal draw-supporter guard

- In the same loss, callback row `92` on turn `36`, our deck count was `2`
  with an eight-card hand and an attack-ready visible Great Tusk opposing us.
  The parent gave Lillie's Determination a Crustle low-deck refill bonus,
  resolved to deck count `1`, and Great Tusk's next Land Collapse milled the
  final card before our draw.
- Future isolated hypothesis: project the post-resolution public deck count
  of a draw Supporter and suppress it when a visible legal mill attack
  deterministically empties the deck before our next draw, unless the same
  turn contains a certified interruption or match win.
- This must use only public card counts and visible attack legality, not the
  replay's hidden draw order. Risks include giving up the only draw into an
  escape, attacker, Boss, or immediate KO.

## Visible Bench-damage survival

- `88247531:114-120`: the damaged three-Energy Bench Duraludon remained
  unevolved and was KOed by visible Bench damage while evolution resources were
  spent on a healthier Active.
- Candidate idea: when an exact visible next attack reaches a Bench Pokemon's
  current HP but not its post-evolution HP, reserve the evolution for that
  invested Bench target.

## Current Active threat versus remote matchup marker

- `88643491:73-77`: a Bench Cornerstone Mask Ogerpon activated the Ogerpon
  override while Mega Lucario was Active, leading to an 80-damage non-KO and
  exposure of the only four-Energy attacker.
- Candidate idea: current-Active combat danger takes precedence over a remote
  blocker marker unless the current action actually advances the blocker
  answer without sacrificing the only attacker.

## Non-ex 120-damage tactical breakpoint

- `87996118:93/95/96` and `88602602:118/120`: a three-Energy Duraludon could
  evolve into non-ex Archaludon and use 120-damage Coated Attack to KO a
  90-HP Alakazam, but the blanket non-ex evolution suppression prevented it.
- Candidate idea: allow the evolution only when the exact 120-damage attack
  creates a current KO that the existing Duraludon attack cannot create, while
  accounting for prize liability and successor continuity.

## Structural or deck observations, not current policy candidates

- Multiple Alakazam losses had no Metal Energy in hand while attackers remained
  below the attack requirement (`88454146`, `88163977`).
- Several adjacent losses never established Duraludon or an evolution line.

## Low-confidence additional-Basic deck test

- Live H1 loss `88680842`, rows `3`, `11`, `22`, and `28`, began with a
  forced lone Duraludon and never produced a Bench or legal search action.
  Harlequin removed the opening evolution before it became legal, after which
  the public actions were forced or sound and H1 remained parent-identical.
- Candidate idea: an isolated one-card deck test adding one benchable Basic,
  with no H1/H2 policy change.
- This is low-confidence evidence from one game, not a supported deck edit.
  Any later test must predeclare the cut and compare identical seeds in both
  seats while measuring setup, backup readiness, attack continuity, and every
  adjacent matchup. Risks include a weaker consistency slot, a Bench target
  exposed to Jetting Blow, and disruption of Duraludon/Cinderace and
  Boss/Metal/Lab balance.
- Qualitative report:
  `live/55064711/refresh_20260729_0601/LOSS_ANALYSIS.md`
  (`CA29840536DB84690C2FD63437A648D24BFB8472423C97DECD9D7D7485B17C3B`).
- These are deck consistency/variance observations. They must not be “fixed” by
  widening an unrelated action rule.

## Sole-board backup before a nonterminal attack

- Live H1 loss `88684114`, seat `0`, remained on a lone Cinderace for the
  entire game. At row `20` on turn `2`, after attaching Metal, the public
  choices still included Ultra Ball while the deck visibly contained Basic
  Duraludon, but the parent chose Turbo Flare with no Bench.
- The opponent already showed two Riolu and a developed board. On its next
  turn it evolved Mega Lucario ex, played Gravity Mountain, attached, and
  Aura Jab KOed the lone Cinderace for an immediate no-Pokemon loss. H1 was
  parent-identical at all `18` callbacks, so this is unrelated to H1.
- Future isolated hypothesis: when our board has exactly one Pokemon, no
  immediate terminal win exists, and a currently legal deterministic search
  can put a Basic backup onto the Bench without discarding an attack-critical
  unique resource, complete the search-and-bench transaction before making a
  nonterminal attack.
- This should be a general board-survival certificate, not a Mega-Lucario
  episode rule and not an assertion that the opponent certainly held Gravity
  Mountain. Its value is avoiding an otherwise single-KO game loss when
  backup access is already public.
- Required negatives include: exact current match win; no legal Basic remains;
  Ultra Ball's two-card discard crosses below a certified current/next-turn
  attack; Bench placement creates a worse exact Prize loss; the Active attack
  itself deterministically creates the needed backup; mandatory effect
  callbacks; and a board that already has a legal successor.
- Risks: spending two important cards for a backup that is not actually
  needed, delaying a stronger Supporter/search sequence, exposing a low-value
  Bench target, or preempting Turbo Flare's own Energy acceleration. Evaluate
  this separately from H2 on identical seeds in both seats.
