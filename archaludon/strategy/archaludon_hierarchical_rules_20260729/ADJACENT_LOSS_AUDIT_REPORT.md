# Adjacent-loss qualitative audit: historical-Silver Archaludon 54927163

## Scope and evidence integrity

This is a read-only audit of the immutable 24-loss set in
`ADJACENT_LOSS_AUDIT_SPEC.md`. Every listed replay was read through its terminal
state and inspected against the exact baseline policy. Only the agent's recorded
hand and public opponent state were used; no opponent hidden-hand reconstruction
or opponent-action imitation was used.

- Exact policy:
  `baseline/historical_silver_archaludon_54495224/main.py`
  (`F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E`)
- Episode rows:
  `evidence/live_54927163_refresh_20260729_0344/submission_54927163_20260729_0344_episodes.csv`
  (`A94A0754A9D2F84B88DB7D64BC126D4E8FA2855CC0769E799A031F6D4702F64E`)
- Extracted opponent decks:
  `evidence/live_54927163_refresh_20260729_0344/decks/`
  (`SHA256_MANIFEST.txt` hash
  `F347CB1D5B3DB5FB1D4D1CE2098C3C53CBED98A542A1AA015FE894E22445F1F8`)
- Raw replays:
  `evidence/live_54927163_refresh_20260729_0344/episode_<EpisodeId>_replay.json`
  for every ID named below.

The source facts relevant to this audit are: current-turn attack routing does not
certify the next attacker (`main.py:414`, `main.py:433`); attachment,
promotion, and evolution scores do not price exposed investment or visible
next-turn Bench damage (`main.py:926`, `main.py:966`, `main.py:1213`); Boss may
be suppressed before a higher-prize Bench KO is considered (`main.py:739`);
Ultra Ball's Alloy-fuel rule can outrank an attack-completing attachment; and
Night Stretcher generally prefers Duraludon over Metal Energy
(`main.py:1092`). `opp_max_damage` exists but is not used by these decisions.

## Exact observed decision states

The observations below are replay facts. Counterfactual outcome claims are
deliberately limited: a missed certified action is identified where public state
is sufficient, but no unplayed line is called a guaranteed game win unless it
immediately takes the last prize.

| Episode / archetype | Exact public decision state and selected actions | Qualitative diagnosis |
|---|---|---|
| `88660007` / Archaludon | Steps 78, 80–83: with Full Metal Lab in play, the Active Archaludon ex had 110 HP remaining and one Metal; a newly evolved Bench Archaludon ex had zero Energy. Assemble Alloy attached both discarded Metals to the damaged Active. Metal Defender failed to KO the full-HP opposing three-Energy Archaludon ex; the Active was then KO'd, leaving the Bench attacker at zero Energy. No attack was available at steps 95 and 104. | **Observed policy failure.** Current-attack completion consumed the complete recovery resource into an exposed, non-KO attacker and broke next-attacker continuity. State-level confidence high; recurrence is unquantified. |
| `88507294` / Archaludon | Steps 37–41: Cinderace at 110 HP could use Turbo Flare; the Bench contained Duraludon with three and zero Energy. The policy retreated, tie-promoted the three-Energy Duraludon, and used Raging Hammer for a non-KO 80 before that Duraludon was KO'd. At steps 73 and 77, equal promotion scores again selected the first-listed, highest-energy Duraludon ahead of lower-investment alternatives; each promoted attacker was KO'd. | **Observed policy failure.** Promotion and attack-route scoring did not preserve invested attackers when the immediate attack could not convert a prize. The best full-game counterfactual is not proven. |
| `88017509` / Mega Lucario | Steps 114–125: both players had one prize left. The Active Archaludon ex had two Energy; the hand contained Boss's Orders and Night Stretcher; the opponent had a 110-HP Solrock on the Bench. Night Stretcher recovered Duraludon instead of a visible discarded Metal, then Lillie's Determination shuffled away the held Boss. Recovering Metal, attaching it, and using the already-held Boss on Solrock would have enabled Metal Defender for the last prize that turn. | **Certified missed lethal.** The generic recovery priority and supporter sequencing overrode an exact public last-prize plan. This is a single exact state, not evidence of its prevalence. |
| `87825800` / Mega Lucario | Step 116: Boss was held while the opposing Active Hariyama had 30 HP remaining and yielded one prize; a Bench Mega Lucario ex had 120/340 HP and yielded three prizes. Boss was scored down because the Active was already KO-able, and Hariyama was attacked. Step 124 again suppressed Boss while the damaged Bench Mega remained KO-able and the Active Mega was not. | **Observed target-selection error.** Active-KO and Mega-Brave suppression masked a publicly certified higher-prize Bench KO. A match win is not inferred. |
| `88584180` / Marnie Grimmsnarl | Steps 89–93: the Active Archaludon ex had two Energy and the hand contained the only visible Metal plus Ultra Ball and other discardable cards. Ultra Ball's 20000 Alloy-fuel score exceeded the attack-completing attachment score of 19700; the selected Ultra Ball discarded that Metal and Night Stretcher. The turn ended with the Active still at two Energy. | **Observed turn-plan/resource error.** Search fuel was valued above the already available attack line. Earlier delayed evolution of an exposed Duraludon may also have reduced survival, but that broader claim has lower confidence. |
| `88247531` / Marnie Grimmsnarl | Steps 114–120: after a KO, the Bench held a healthy one-Energy Duraludon and a 10-HP three-Energy Duraludon. Equal promotion scores chose the healthy one; evolution and both Alloy attachments went to that new Active. The damaged, attack-ready Bench Duraludon remained unevolved and was then KO'd by public Bench damage from Shadow Bullet. | **Plausibly mechanism-addressable.** Evolution/attachment targeting ignored the visible Bench-damage breakpoint and lost the next attacker. Evolving the damaged Bench target would preserve it through that damage, but the full-game result is not proven. |
| `88643491` / Mega Lucario hybrid | Steps 73–77: a visible Cornerstone Mask Ogerpon on the opponent's Bench caused the Ogerpon matchup override even though Mega Lucario was Active. The agent retreated a 30-HP Cinderace into its only four-Energy Duraludon; the Ogerpon-specific Raging Hammer score promoted an 80-damage non-KO into Mega Lucario, and the Duraludon was KO'd. | **Plausible hierarchy leak.** A remote Bench immunity answer overrode the current Active threat. Confidence in the exact mechanism is high; confidence that a different line wins is low. |

## Per-episode disposition

This table prevents the named mechanism from being inferred onto unrelated
losses. “Variance/strength” is a qualitative attribution, not a deck-building
verdict.

| Episode | Archetype | Audit disposition |
|---|---|---|
| `88660007` | Archaludon | Mechanism-addressable continuity/resource-target failure; exact state above. |
| `88655752` | Archaludon | Thin Duraludon line and delayed rebuild; no clear public-state policy error. Draw variance/opponent setup is the stronger hypothesis. |
| `88643491` | Mega Lucario | Plausible Active-threat hierarchy leak; exact state above. |
| `88584180` | Marnie Grimmsnarl | Mechanism-addressable attack-completion/resource-order error; exact state above. |
| `88563380` | Marnie Grimmsnarl | Primary and backup attackers formed; close attrition loss without a certified bad decision. |
| `88509934` | Archaludon | Cinderace development and attack sequencing were coherent; eventual line exhaustion appears unrelated. |
| `88507294` | Archaludon | Mechanism-addressable promotion/investment-preservation failure; exact state above. |
| `88411737` | Mega Lucario | No Duraludon reached play; Cinderace used Turbo Flare with an empty Bench before the loss. Draw variance dominates. |
| `88391698` | Mega Lucario hybrid | Cornerstone-driven matchup override is plausible, but no independent certified conversion was found; low-confidence policy attribution. |
| `88389000` | Marnie Grimmsnarl | Boss and backup sequencing were coherent. Optional Alloy added excess Energy to a lone ready Active late, but no causal loss claim is supported. |
| `88367994` | Marnie Grimmsnarl | Duraludon/Metal development failed under Budew item lock; variance and opponent pressure dominate. |
| `88356203` | Mega Lucario | Primary and backup Archaludon ex formed and converted a three-prize KO; later resource exhaustion/opponent strength dominates. |
| `88338429` | Mega Lucario | No Duraludon reached play; empty-Bench Turbo Flare line. Draw variance dominates. |
| `88272191` | Marnie Grimmsnarl | Retreat and attacker development were coherent; using a damaged Active before it could be Bench-sniped was defensible. |
| `88247531` | Marnie Grimmsnarl | Plausible evolution/attachment continuity failure under visible Bench damage; exact state above. |
| `88225916` | Marnie Grimmsnarl | Prolonged Metal drought. Defensive evolution might mitigate exposure, but policy causality is low-confidence. |
| `88197270` | Marnie Grimmsnarl | Multiple backup and Boss conversions reached the last-prize stage; no certified held out was visible. |
| `88134743` | Archaludon | Repeated Duraludon without evolution support; draw variance/line fragility dominates. |
| `88017509` | Mega Lucario | Exact public last-prize lethal missed; exact state above. |
| `87868636` | Marnie Grimmsnarl | Primary/backup attackers formed; no publicly killable two-prize target at the critical exchange. |
| `87825800` | Mega Lucario | Mechanism-addressable higher-prize Boss target suppressed; exact state above. |
| `87709435` | Marnie Grimmsnarl | Wide Duraludon board and attacker continuity formed; public evidence favors opponent pressure/attrition. |
| `87701753` | Marnie Grimmsnarl | Archaludon remained energy-short through prolonged Metal drought; variance dominates. |
| `87690776` | Mega Lucario | Cinderace developed one Duraludon, but evolution/backup never arrived; variance/opponent tempo dominates. |

## Qualitative failure hypothesis

**Observed:** the exact baseline scores the current action locally. It has no
single public-state certificate that protects an already invested next attacker,
reserves the resources of an exact prize-conversion plan, or vetoes a lower-prize
target when a higher-prize KO is already available.

**Hypothesis:** one hierarchy defect connects the strongest states above:
immediate local action value can outrank a certified turn plan. It appears as
attaching into a doomed Active, exposing the highest-investment promotion,
discarding the only attack-completing Energy, recovering a Pokémon over lethal
Energy, or suppressing a higher-prize Boss target. This is a policy hypothesis,
not a statement about how frequently it occurs. The remaining dispositions show
that draw variance, structural dependence on Duraludon plus Metal, and opponent
pressure also explain losses that this certificate should not try to “fix.”

## One narrowly testable countermeasure

Add a **public certified-turn-plan reservation** before ordinary local scores:

1. First reserve any exact last-prize line, then any same-turn higher-prize KO,
   using only current hand, discard, board, legal actions, known attack damage,
   weakness/resistance, Stadium, tools, and prize values.
2. If no such conversion exists, and the proposed attack is a public non-KO
   into an opposing attacker that can already KO the proposed Active on its
   next attack, do not spend the sole attack-completing Energy, evolution, Alloy
   attachments, or highest-energy promotion on that exposed line when a legal
   lower-investment current target or survivable next-attacker allocation exists.
3. Hold the certificate only for the current turn; recompute after each action.
   Do not condition it on episode ID, opponent hidden hand, or archetype label.

The first deterministic state tests should be the cited steps in `88017509`,
`87825800`, `88584180`, `88660007`, and `88507294`. The expected assertion is
selection of the certified action/resource reservation, not a replay-derived
opponent action or guaranteed match result.

## Regression risks

- Preserving investment can concede necessary damage or feed a low-investment
  prize; the veto must require a public non-KO plus visible retaliation, not a
  generic “save Energy” preference.
- Damage certification must model Stadium, weakness/resistance, tools, and
  attack restrictions exactly. The unused `opp_max_damage` helper is not itself
  a safe certificate and should not import assumptions about hidden cards.
- A higher-prize Boss target is not automatically superior if it is not KO-able
  now or if switching it re-enables a dangerous effect; require the actual KO
  and prize certificate.
- Recovering Metal for an immediate plan can starve line rebuilding when the
  plan is not complete. Reserve it only when every remaining legal component is
  already public and available.
- Active-threat priority in hybrid boards must retain a genuine answer to
  Cornerstone Mask; it should prevent a remote blocker from overriding the
  current combat calculation, not delete blocker handling.

## Raw rows for independent quantification

No recurrence, rate, delta, or promotion judgment is made here. A Sol-Ultra
numerical evaluator or the root can quantify any proposed recurrence directly
from:

- Episode CSV rows for:
  `88660007, 88655752, 88643491, 88584180, 88563380, 88509934, 88507294,
  88411737, 88391698, 88389000, 88367994, 88356203, 88338429, 88272191,
  88247531, 88225916, 88197270, 88134743, 88017509, 87868636, 87825800,
  87709435, 87701753, 87690776`.
- The corresponding exact
  `evidence/live_54927163_refresh_20260729_0344/episode_<EpisodeId>_replay.json`
  files, plus the same-ID rows in `decks/archetypes.csv`, `decks/decks.csv`, and
  `decks/deck_cards.csv`.
- Decision-state rows requiring direct recomputation:
  `88660007` steps 78, 80–83, 95, 104;
  `88507294` steps 37–41, 73, 77;
  `88017509` steps 114–125;
  `87825800` steps 116 and 124;
  `88584180` steps 89–93;
  `88247531` steps 114–120;
  `88643491` steps 73–77.

