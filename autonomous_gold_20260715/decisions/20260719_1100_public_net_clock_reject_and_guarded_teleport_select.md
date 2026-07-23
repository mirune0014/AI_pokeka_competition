# Reject public net clock; select guarded Teleportation continuity

- Recorded: 2026-07-19 11:00 JST
- Owner: root
- Kaggle write: none
- Authenticated state at 10:40 JST: submission `54802782` complete at
  displayed `725.5`, episode set unchanged at 57/57, `0/5` UTC-day slots used

## Final rejection

Reject `alakazam_public_net_deck_delta_prize_clock_v1`. Do not package,
submit, adopt, or stack any portion of it.

Frozen candidate source/runtime/deck SHA-256:

- `48A17C780D40BE6A2EC5F49673DF535DFDBF6C6526F180653E40F2A55563294A`;
- `B17E9056B5CCD78EAB7BBA5B52090AEA473D450AF278447A261EC5F94CA5442A`;
- `7B413177E5077777F2178143839C0155B03B92BBC8B3A6607621A7D43F351141`.

Root and independent audit agree: exact-v3 `86/144`, candidate `85/144`,
`0 gains / 1 regression`; P0 `45 -> 44`, P1 `41 -> 41`, known `44 -> 44`,
fresh `42 -> 41`, and Historical Silver `8 -> 7`. Every other opponent bucket
is unchanged. Structure and duplicate controls are exact.

There are 52 natural first differences, but no gain. The sole positive-net Run
Away activation stays a loss. Helmet suppression causally creates the sole
Silver regression. Terminal Helmet suppression and a Psychic Draw NO without
a publicly forceable Energy-ready backup violate the behavioral contract.
Retain no code or submechanism; the clean Run Away fixture is research evidence
only.

Submission-critical report SHA-256:

- root final verification:
  `D8F1D3996C4F2CBF7534B1A66AB8582F7D3E4688F62A1E20BC7F93D4F5481700`;
- numerical report/result:
  `83C329B3B6D83A220075ECD1D49CAD73CE586925D919AF60AB145C129B948819` /
  `D14F0B0EA7B4A6FAC4FBC0A438AAF9874227CCBD3558CF8A93152C1F7DE762AE`;
- qualitative report/evidence:
  `BCDDCE162ABA94C5B1B7E6489DDA52A204D18077410B93A413207B270839A9CD` /
  `B19AD482C98A20F8C60A6C083B432606F6F630AFD9F7705EFD531838B44E2702`.

## Selected next hypothesis

Name: `alakazam_guarded_teleportation_attack_continuity_v1`.

Parent only:
`candidates/alakazam_parent_end_strict_prize_lead_retreat_ko_bridge_v3`.

- parent source/runtime/deck SHA-256:
  `49E954F53E043CD79D928DFB2340CCB5D85A17F33CCB824C871CCE153C0C9C95` /
  `9CA7A415451B84343165EF8A5CDC0D67BBF1B4969A13C984C09B142B4898CD9A` /
  `7B413177E5077777F2178143839C0155B03B92BBC8B3A6607621A7D43F351141`.

The deck is byte-identical and exactly 60 cards. No rejected net-clock,
Xerosic, reserve, Fez, stage-up, draw, Run Away, evolution-target, Boss, or
matchup rule may be inherited.

## Public behavioral contract

Compute exact-v3's finalized action first. Override only its finalized MAIN
`RETREAT` with Abra's Teleportation Attack when all predicates are exact:

1. Active is unstatused Abra with public Psychic Energy, legal Teleportation,
   at least one legal Bench switch target, and no existing transaction latch.
2. Before acting, predict exact-v3's counterfactual retreat promotion with a
   pure helper over current public Bench order:
   - Alakazam `100 + 10 * attached-energy-count`;
   - Kadabra `90` if opponent Active HP is at most 30, otherwise `30`;
   - Abra `10`;
   - Dunsparce or Dudunsparce `5`;
   - every other Pokemon `1`.
3. Require one unique highest-scoring Bench target. Record its serial, card ID,
   Bench index and score. Any tie, switch restriction, target exclusion, or
   unknown relevant effect delegates unchanged.
4. The predicted target cannot currently pay any public attack. It also cannot
   be made attack-ready this turn because attachment is already used or no
   visible hand Energy can legally ready it.
5. Besides Teleportation, Retreat and End, no current MAIN option has positive
   exact-v3 score or could become positive solely because the predicted target
   becomes Active. A PLAY option is allowed only when its public score is at
   most zero and invariant under the switch.
6. Exclude confusion, nonterminal Teleportation KO, public retaliation,
   prevention, reflection, forced zone change, switch suppression, or unknown
   relevant text. Unknown or malformed state fails closed.
7. Choose Teleportation. On its immediate SWITCH callback select the recorded
   serial, not a post-damage recomputation. If absent, delegate to exact-v3 for
   a legal fallback, clear the latch and mark a semantic failure. Clear after
   the switch, terminal KO, player/turn change, or unexpected callback.
8. Every nonmatching state delegates bit-for-bit to exact-v3. Repeated
   identical callbacks return the same action.

Retreat payment changes only Active Abra Energy; it does not change Bench
membership/order or SWITCH scores. The pre-attack prediction therefore matches
the parent promotion unless an explicitly excluded public effect intervenes.

## Root exposure census and fixtures

Root found exactly 12 exact-v3 callbacks that choose RETREAT while
Teleportation is legal. Four produce a same-turn attack after retreat and are
mandatory negatives:

- `fresh_general|great_tusk|p0|2026101802`;
- `known_target|dragapult|p0|2026071593`;
- `known_target|kangaskhan_crustle|p0|2026071599`;
- `known_target|marnie_sota|p0|2026071599`.

Eight retreat lines produce no same-turn attack. Two have additional PLAY
choices and remain fail-closed unless their exact score/invariance is proved.
The six conservative natural positives uniquely predict an unenergized
Kadabra and have no additional MAIN PLAY:

- Oselcoun P0 / `2026071600`;
- Rmy P0 / `2026071600`;
- Dragapult P0 / `2026071600`;
- Historical Silver P1 / `2026071599`;
- Mega Lucario P0 / `2026071593`;
- Mega Lucario P0 / `2026071600`.

Required positive fixtures include live `86774226`, frozen Dragapult P0 /
`2026071600` step 30, and Silver P1 / `2026071599` step 56. The frozen
Dragapult state has an energized Bench Abra, but exact-v3 uniquely predicts
the unenergized Kadabra (`30 > 10 > 5`); this corrected target-local
certificate supersedes the rejected global no-ready-Bench wording.

Additional negatives: tied prediction, ready or visibly forceably-ready
predicted target, any positive/switch-enabled MAIN continuation, no Bench,
non-Abra Active, illegal attack, status, public reaction uncertainty, stale or
unexpected latch callback, and all nonmatching parent actions.

Require compile/import, exact parent prefix, legal byte-identical deck,
source/runtime parity, option-order invariance, repeated-call determinism,
complete checked-engine attack-to-switch transaction, all 12 exposure
controls, live replay control, both-seat smoke and zero caches before Phase-0.

## Fixed Phase-0 gates

Use schedule SHA-256
`4271E31503F37EFE4B1BBB9ED2D3569D79D9C1E9B2A20387CCAC131F28346010`
with primary/duplicate controls for both policies.

- candidate at least `88/144`, at least `2 gains / 0 regressions`;
- Historical Silver at least `9/16`, including at least one Silver gain;
- P0 at least `45/72`, P1 at least `42/72`;
- known at least `44/72`, fresh at least `43/72`;
- Great Tusk at least `4/16`, Rmy at least `7/16`, Kangaskhan at least
  `11/16`, and no opponent decline;
- at least four natural activations across both seats and two opponents,
  including Silver and a fresh key;
- the four parent attack-continuation negatives remain identical through the
  retreat decision;
- every first difference is RETREAT versus certified Teleportation, at least
  one gain begins causally there, and no mechanism-first regression occurs;
- zero execution, action, max-step, duplicate, schedule, hash or semantic
  defects.

Only a complete pass permits packaging and a fresh root-only Kaggle decision.
