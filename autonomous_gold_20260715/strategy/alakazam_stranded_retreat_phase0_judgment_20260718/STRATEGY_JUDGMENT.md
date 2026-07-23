# Final Phase-0 judgment: stranded-Active retreat bridge v1

Date: 2026-07-18 JST  
Decision: **REJECT frozen v1 for packaging and live submission. BUILD exactly
one successor: the same atomic retreat route, but allow START only when the
exact parent policy's finalized MAIN choice is ordinary END.**

## Evidence and judgment

The exact parent remains
`candidates/alakazam_active_psychic_lone_dudunsparce_survival_v1`, source /
runtime / deck SHA-256
`FAB47771161EF7F43C9402B58D38FF240C92B6A2B77FFA6B925DFEA7F990D033` /
`9CA7A415451B84343165EF8A5CDC0D67BBF1B4969A13C984C09B142B4898CD9A` /
`7B413177E5077777F2178143839C0155B03B92BBC8B3A6607621A7D43F351141`.
The rejected candidate is frozen at source SHA-256
`B0688E8CC9F0543BDD08DB776FFEA7E44A0919480896CB1952A2A678B1862BAB`.

The execution freeze, execution report, independent audit, parent raw tree,
candidate raw tree, and root verification reproduce as
`22E5DF8BC5BE43F4A9238B0D6C4B4D3BCE54F46C9D581C5DF91CD4583537AEC1`,
`7B0DED8C80D358F1A8BFE9E3C478C9D686877B15D3FDC9BDA03630C1E1486534`,
`EC725C8FBEA55B8B4BD9F97763DA88E0B5EFB30B5FB325FC70210CA45752F890`,
`91AFE71E7462F998A722EFAC0F55E7916EDFFD598EA4EA55A0D7567CE73E2272`,
`0929E3E35B2108CBA2F3CC0865075839E8B868E21FAC75056F6BF06B124931B7`,
and
`DEE9BB5FD7D9E7E038332624A70FA6B5A0C5CEA4B862AD1DDC303C9786B56B1`.
The panel is clean: 144 exact keys, both seats and identical seeds, zero
execution/action/max-step faults, and 16/16 changed routes complete
`RETREAT -> exact payment -> Alakazam -> Powerful Hand KO` in one turn.

Nevertheless v1 scores `83/144` against `84/144`: one gain, two regressions,
P0 `44 < 45`, fresh `39 < 41`, and Alakazam-Rmy `6 < 7`. It therefore fails
four precommitted floors. More importantly, this is not sampling noise hiding
an unexplained loss: the two regressions begin by preempting productive Boss's
Orders and Hilda choices; the sole gain preempts Dawn. Across the 16 starts,
only three parent first choices are END. Those three routes are all
outcome-tied; the remaining starts cut ahead of setup, gust, attachment,
evolution, or Ability sequencing.

For Alakazam, hand development is damage, evolution and Psychic placement are
backup readiness, and Boss is target/prize control. Paying retreat Energy and
exposing the energized Alakazam before those actions can win a quick Prize,
but can also lose the following prize exchange. Thus the transaction is
valid; its priority is not. User-authorized practical live testing does not
justify spending a slot on this known sequencing defect when a strict-subset
successor preserves the proved live repair.

Live replay `86585479`, SHA-256
`8F0D9978D57F33B47862EC3D7F1A02E56BB6FEC16BC0715620937F0D33961B28`,
still requires the route. The parent usefully plays Boss at S142/S143 but then
chooses END at S144 with Fezandipiti ex stranded, a payable retreat, and a
ready Alakazam. END-gating therefore preserves the useful Boss sequence and
replaces the actual losing decision. The later ten public games were `6-4` at
submission score `652.9`; frozen v1 changed `0/707` recorded target callbacks.
That is retention evidence, not positive activation evidence
(`QUALITATIVE_NEW10_DIAGNOSIS.md` SHA-256
`C3DF7486FFBF000B71A81A5FB5ABF5FEBE6B0B32636D12D96E5696F41A634A8C`).

## Sole immediate successor

Create
`candidates/alakazam_parent_end_stranded_retreat_ko_bridge_v2` directly from
the exact `FAB477...` parent, not from rejected B0688. Port the certified v1
latch and atomic payment/promotion/attack implementation without broadening
its public-state predicate. The only semantic change from v1 is START timing.

Advance an already-active retreat latch before ordinary parent scoring, with
the same exact-state checks and same-observation stale-latch delegation as v1.
For a new START, first execute the parent's complete decision pipeline on the
current observation: inherited active-Psychic and Fez transactions, scoring,
Run Away Draw and fragile-bench overlays, and Fez-bridge start all retain their
current precedence. After the final deterministic `desc_indices` winner is
known, START is eligible only when all of these are true:

1. context is MAIN; the parent's selected action is exactly one option and
   that option is `OptionType.END`; no inherited or new latch is active;
2. the full v1 certificate still holds: nonattacking public Active, no legal
   ATTACK, unspent retreat, positive exact retreat cost, exact payable
   single-unit Energy, public energized Bench Alakazam, public Powerful Hand
   KO, safe visible deck/prize clock, and unique protected serials;
3. no card ID, opponent, episode, seat, seed, or turn-specific predicate is
   added.

If the parent selects PLAY, ATTACH, EVOLVE, ABILITY, RETREAT, ATTACK, or any
other non-END action, return it unchanged and do not create or mutate the new
latch. Re-evaluate from the resulting later MAIN observation. If that later
parent choice becomes END and the certificate remains true, bind the current
source, destination, target, payment, hand/deck/prizes/stadium and execute:

`RETREAT -> exact energy payment -> frozen Alakazam promotion -> immediate
Powerful Hand KO`.

Any stale or ambiguous callback clears the latch and delegates wholly to the
exact parent; never restart it in the same observation. Preserve the
lone-Active-Dudunsparce guard and every inherited transaction verbatim. Do not
stack attack-target, Dudunsparce-resource, or setup-before-KO rules into this
candidate.

## Required boundaries and permission

Before a live probe require compile/import, legal 60, source/runtime parity,
repeated-callback determinism, exact checked-engine payment plus SWITCH and
TO_ACTIVE routes, all stale/ambiguous fail-close controls, and both-seat
packaged smoke.

On replay `86585479`, S142 must remain the parent's Boss, S143 its exact target
selection, and S144 must be the first difference: END becomes RETREAT, exact
Psychic payment, Alakazam `743/s13` promotion, and same-turn Powerful Hand KO.
The 13 v1 boundaries that previously preempted a productive non-END action
must retain that parent action. The three v1 END boundaries must still finish
the atomic route without an outcome regression. The ten new public histories
must remain `0/707` different, and all inherited active-Psychic, S134/S135/S143,
S21 lone-Dudunsparce, and recorded-win fixtures must remain valid.

Run the unchanged fixed 144-key schedule (SHA-256
`4271E31503F37EFE4B1BBB9ED2D3569D79D9C1E9B2A20387CCAC131F28346010`)
against the exact parent. Require 144/144 clean rows; total at least `84`, P0
at least `45`, P1 at least `39`, known at least `43`, fresh at least `41`,
Alakazam-Rmy at least `7`, Historical-Silver at least `7`, and no opponent
bucket more than one below parent. Every first difference must be a parent
END replaced by the certified transaction; both prior regression keys must
remain parent wins. No 1,440-game broad run is required if these safety gates
pass.

**Permission:** frozen v1 B0688 is rejected and must not be packaged or
submitted. The sole v2 successor is approved for isolated implementation and,
only after all boundaries above pass and root refreshes Kaggle state, one
practical live probe. Until then it is not an adopted baseline.
