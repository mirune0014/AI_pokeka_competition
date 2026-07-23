# Reject Fez exposure guard; select public net-deck-delta prize clock

- Recorded: 2026-07-19 09:10 JST
- Owner: root
- Kaggle write: none
- Current authenticated quota after reset: `0/5` used, five remaining

## Final Fez-candidate rejection

Reject
`candidates/alakazam_prize_safe_fez_ex_exposure_guard_v1`. Do not package,
submit, adopt, or stack it.

Frozen execution identity:

- source/runtime/deck SHA-256:
  `EAC344241AFB0CA4F4575262854D4479A58B4B6FC62E07DDD9F5B7050DDC3BDE` /
  `6B28707D38773B974EBE9A9393D356FEEDF4CBB36A6D30BC9B9C37CF4D61B1D9` /
  `7B413177E5077777F2178143839C0155B03B92BBC8B3A6607621A7D43F351141`;
- successor ledger/completion SHA-256:
  `BC31B85E66D0E2DC10768B387626AC1F9D1C5A86F391F9412CA8A33A2D88ED2F` /
  `B4AB06673158E101E3B85BEDACEA4621FD4A550E862DBBA4C644F74803124D67`;
- root verification:
  `evaluations/alakazam_prize_safe_fez_exposure_guard_v1/fixed_phase0_incremental_20260719/ROOT_FIXED_PHASE0_INCREMENTAL_VERIFICATION.md`;
- final independent calculator/result/report/manifest SHA-256:
  `2BA007E7DEDCA0CA9D3E8FBF5491AE4E94FB0A561AA29E0D12C6D9181AE4AEB7`,
  `B5446D9CDEAB610DF8CC52F8F157736DD25405D9476498F077C6AF57A4CFB6D6`,
  `7894CD67617A0D7D05E7278146EF0AE24EE61A0B42557C253E677F70CFC74F8E`,
  `C223E97F85085F48006B3F5C643B6B7343C041B08ECA53A0494852BF0DB5E45D`.

Root and Sol-Ultra agree exactly: exact-v3 is `86/144`, reserve-v1 and the
Fez successor are both `87/144`; the successor is `1G/0R` against exact-v3
but `0G/0R` against its direct parent. Historical Silver is `8/16`. Only one
parent/successor trace changes and it remains a loss. The candidate therefore
fails total `87<88`, exact gains `1<2`, incremental gains `0<1`, Silver
`8<9`, and repeated-mechanism exposure. Zero defects and regressions establish
safety only and cannot rescue these frozen failures.

## Selected next hypothesis

Name: `alakazam_public_net_deck_delta_prize_clock_v1`.

Parent: exact-v3 only:
`candidates/alakazam_parent_end_strict_prize_lead_retreat_ko_bridge_v3`.

- parent source/runtime/deck SHA-256:
  `49E954F53E043CD79D928DFB2340CCB5D85A17F33CCB824C871CCE153C0C9C95` /
  `9CA7A415451B84343165EF8A5CDC0D67BBF1B4969A13C984C09B142B4898CD9A` /
  `7B413177E5077777F2178143839C0155B03B92BBC8B3A6607621A7D43F351141`.

The deck remains byte-identical. Do not inherit the rejected reserve, Fez,
Xerosic, stage-up, or other sibling overlays.

## Live causal anchor

Episode `86778139`, replay SHA-256
`E81761637DE5281CFB03345F3E1C5576400ED5353334E7AB907C905A98B5271F`,
is an Alakazam mirror with strong setup, attack continuity, and a late
three-Prize lead. The submitted inherited policy lost by deck exhaustion.
Public avoidable expenditures were Psychic Draw at steps 108, 110 and 128,
Active Lucky Helmet at 131 and missed positive-net Run Away Draw at 141/143.
This is one causal game and not population proof, but it supports one coherent
multi-step net-deck corridor better than isolated bad-action patches.

The two other new mirror losses remain separate evidence. Their recovery,
Xerosic-discard, evolution/retreat and Boss gaps are not stacked here.

## Behavioral contract

Compute exact-v3 first and overlay only optional Psychic Draw, Lucky Helmet
attachment and Dudunsparce Run Away Draw. Use public state only.

1. Tight clock: `deck_count <= 3 * own_prizes + 2`, unless a fully public
   same-turn final-Prize or board-out attack is already certified.

2. Psychic Draw: choose NO only under a tight clock when the current public
   hand/board already certifies the current attack or KO without the three
   unknown cards and a separate next-attacker route is certified. Preserve
   YES if the extra 60 Powerful Hand damage is required, current legality or
   backup is not certified, or this turn wins. Never assign an identity to an
   unknown draw.

3. Lucky Helmet: under a tight clock suppress attachment to the Active or a
   Pokémon publicly certified to become Active before the next own turn when
   this turn is not terminal. Preserve exact-v3 outside the tight clock, on a
   terminal turn, or for a Dudunsparce whose exact Run Away stack is positive-
   net and safe. Recompute from card serials on every callback.

4. Run Away Draw: count the serial-distinct Dudunsparce, full evolution stack,
   attached Energy and attached Tools returned as `R`; projected deck is
   `D' = D + R - 3`. Under a tight clock prefer the legal Dudunsparce with
   greatest `R` only when `R>3`, `D'>own_prizes`, another Pokémon remains, and
   removing it does not break the certified current attack or backup. Never
   remove the only Pokémon. Delegate when identities/counts are ambiguous,
   `R<=3`, the projected floor fails, or a final-Prize attack is certified.

5. Outside these action families delegate byte-for-byte to exact-v3. Do not
   change setup, evolution, recovery, discard, ordinary Energy, retreat, Boss,
   targeting, damage, attacks, or the deck.

## Required focused gates

Positive replay fixtures reconstruct `86778139` steps 108/110/128 as NO,
step 131 as no exposed-Active Helmet, and steps 141/143 as Run Away Draw from
Dudunsparce serial 17. The latter returns Dunsparce stack plus Enriching Energy
plus Helmet: `R=4`, deck `3 -> 7 -> 4`, above three Prizes.

Negative fixtures preserve Psychic Draw when +60 is needed or no separate
backup exists; preserve a certified final-Prize attack; preserve normal Helmet
outside the tight clock; reject Run Away when it is the only Pokémon, `R<=3`,
`D'<=prizes`, or board continuity breaks. Missing serial/effect identity,
mandatory prompts and stale callbacks fail closed.

Require compile/import, exact parent/deck identity, legal 60 cards,
determinism, option-order invariance, complete checked-engine multi-step
transactions, and both-seat smoke before Phase-0.

## Fixed Phase-0 gates

Use the existing 144-key both-seat nine-opponent schedule SHA-256
`4271E31503F37EFE4B1BBB9ED2D3569D79D9C1E9B2A20387CCAC131F28346010`
with identical-policy duplicate controls.

- at least `88/144` and `2G/0R` versus exact-v3;
- Historical Silver at least `9/16`;
- P0 at least `45/72`, P1 at least `42/72`;
- known at least `44/72`, fresh at least `43/72`;
- Great Tusk at least `4/16`, Alakazam Rmy at least `7/16`,
  Kangaskhan/Crustle at least `11/16`, and no opponent decline;
- zero exits, action errors, max-step, duplicate, schedule, hash or malformed
  defects;
- all replay fixtures pass;
- at least two natural changed keys, including one draw/Helmet conservation
  and one positive-net Run Away activation;
- every first difference satisfies the contract and at least one paired gain
  begins with the intended net-deck mechanism.

Sol-Ultra selects immediate Fast Sol-xhigh implementation. User consultation
is not required because every branch is expressible as a deterministic public-
state certificate.
