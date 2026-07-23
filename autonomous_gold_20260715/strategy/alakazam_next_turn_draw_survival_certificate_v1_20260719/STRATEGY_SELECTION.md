# Strategy selection: Alakazam next-turn draw survival certificate v1

Selected: 2026-07-19 JST  
Owner: root  
Sol-Ultra verdict: `ACCEPT-TO-IMPLEMENT`  
Scope: one isolated exact-v3 sibling; no EVOLVE, Starmie-formation, forced-discard, recycle, or learned-policy stacking

## Parent and evidence boundary

- Parent: `candidates/alakazam_parent_end_strict_prize_lead_retreat_ko_bridge_v3`.
- Parent source SHA-256: `49E954F53E043CD79D928DFB2340CCB5D85A17F33CCB824C871CCE153C0C9C95`.
- Runtime SHA-256: `9CA7A415451B84343165EF8A5CDC0D67BBF1B4969A13C984C09B142B4898CD9A`.
- Deck SHA-256: `7B413177E5077777F2178143839C0155B03B92BBC8B3A6607621A7D43F351141`.
- Live evidence: submission `54831507` initial ten games, verified in `live/54831507/refresh_20260719_2255/ROOT_INITIAL10_VERIFICATION.md`.
- Live shadow SHA-256: `070C3CE0D941E2A238B44CBD1B28CEC6213899CBDC0685801BBA3FA13B1E72B9`.

The submitted EVOLVE rule reproduced 669/669 recorded actions with zero invalid actions but scored 5-5 overall and 4-5 externally. Its two activations were locally successful and not identified as causal loss defects. It is not stacked into this candidate.

## Selected defect

The parent computes `can_win_this_turn` from hypothetical target damage and Prize value, then sets `safe_draws=999` without requiring a currently ready attacker or a legal immediate attack. Generic YES/NO handling also always prefers YES. This can waive the deck clock even when no public final-Prize route exists.

Two independent mirror losses contain exact causal opportunities:

- Episode `86892228`, observation step 155: Alakazam optional draw takes deck `3 -> 0`; the ready Active can KO only a one-Prize Dudunsparce while two Prizes remain. The opponent ends, and the target immediately loses at the next mandatory draw.
- Episode `86893328`, observation step 158: Enriching Energy takes deck `2 -> 0`; Active Genesect has no terminal attack. After the opponent's KO, the target immediately loses at its next turn boundary.

The selected rule is `NEXT_TURN_DRAW_SURVIVAL_CERTIFICATE`: project the exact deterministic deck delta and suppress the optional fixed draw whenever it leaves no next-turn card and no certified same-turn game-ending attack exists.

## Behavioral contract

Compute the exact-v3 finalized action first, then apply a narrow post-parent transformer. Do not globally rewrite generic YES scoring or `safe_draws`.

Recognized fixed effects only:

- Kadabra Psychic Draw: `D' = D - min(D, 2)`;
- Alakazam Psychic Draw: `D' = D - min(D, 3)`;
- Enriching attachment: `D' = D - min(D, 4)`;
- Fezandipiti draw: `D' = D - min(D, 3)`;
- Dudunsparce Run Away Draw: `D' = D - min(D, 3) + 1 + preEvolution + Energy + Tools`, using engine-verified resolution order and exact stack counts.

Intervene only when `D > 0`, the exact parent-selected fixed effect produces `D' < 1`, and no terminal certificate exists. Preserve every `D == 0` action to avoid recreating the rejected hand-budget mechanism.

- At an exact owned Kadabra/Alakazam `ACTIVATE` callback with unique YES and NO, select NO.
- At MAIN, mask only the unsafe fixed effect and select the highest parent-ranked legal ATTACK; if no such attack exists, select the unique END.
- Do not start a new search, draw, evolution, attachment, or setup chain as fallback.
- Preserve safe effects and every Dudunsparce return whose exact post-effect deck leaves at least one card.

Terminal exemption requires a complete, unique, currently ready Active Alakazam, a unique legal Powerful Hand option, unchanged current opponent Active, publicly counter-susceptible target, exact post-effect hand count sufficient for KO, and either final-Prize yield or opponent board-out. It may not depend on Boss, a hidden identity, a future evolution/attachment, a hypothetical attacker, or a Bench target.

If lethal already exists before the effect, attack immediately. If the fixed effect is necessary for lethal, use one fail-closed latch:

`await_effect_resolution -> await_attack -> await_resolution`

Revalidate turn/player, attacker and target serials/fingerprints, Prize counts, exact hand/deck delta, attachments, blockers, and the unique attack at every stage. Ordinary suppression uses no latch.

## Positive and retention fixtures

Required positive first-order differences:

- `86892228/S155`: parent YES, candidate NO.
- `86893328/S158`: parent Enriching attachment, candidate ATTACK if a certified legal attack exists, otherwise unique END.

Required unchanged controls:

- `86893328/S152` and `S154`: preserve both deck-positive/safe Dudunsparce returns.
- `86895528/S142`: preserve safe Alakazam draw `7 -> 4`.
- `86896074/S114`: preserve safe Enriching use from deck 11.
- Preserve Starmie episodes `86892774`, `86894977`, and `86894415`; energized-versus-unenergized evolution policy is a separate later sibling.
- Preserve `D == 0`, inherited-latch, mandatory-selection, malformed, ambiguous, incomplete, and unknown-effect behavior exactly.
- Preserve the fixed Historical-Silver terminal win and the Kangaskhan/Crustle deck-zero control.

## Rapid gates

Before fixed evaluation:

- exact parent/deck/runtime identity, compile/import, legal 60 cards, deterministic repeated callbacks, and zero cache artifacts;
- focused capacity-boundary, option-permutation, Dudunsparce stack/order, terminal/near-terminal, inherited-latch, and fail-closed tests;
- checked live serialization for both positives and listed controls;
- initial-ten common-prefix shadow: 669 callbacks, zero invalid actions, exactly the two authorized first-order differences and no unrelated differences.

Compact fixed schedule:

- all nine fixed opponents;
- both seats;
- seeds `2026071586`, `2026071600`, `2026101801`, `2026101804`;
- exactly 72 identical paired keys.

Exploratory-live floor:

- candidate at least 42/72 and not below exact-v3 overall;
- neither seat below exact-v3 and each at least 20/36;
- Historical-Silver at least 4/8 and not below parent;
- combined two mirrors at least 7/16 and not below parent;
- no opponent-bucket decline, paired regression, action error, max-step hit, duplicate mismatch, or schedule defect;
- at least two authorized activations, spanning both seats if naturally exposed;
- every changed trace is the intended positive-deck-to-zero prevention or a certified terminal latch.

This floor permits an explicitly labeled practical live probe only. It does not permanently promote the rule.
