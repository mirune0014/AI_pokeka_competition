# Reject Xerosic single-swap; select mandatory-draw reserve transaction

- Recorded: 2026-07-19 06:02 JST
- Owner: root
- Kaggle write: none

## Final rejection

Reject
`candidates/alakazam_xerosic_immediate_ko_successor_single_swap_v1` and retain
exact-v3 as the executable parent.  Do not mirror-confirm, package, submit, or
stack the rejected candidate.

Frozen evaluation identity:

- candidate source/runtime/deck SHA-256:
  `981CAF68D02100161F99AF548AD1F21C048E1FA01BB618A4A8B0DAAEBF725FAA` /
  `4D34FCE70D9D8DB848E1C3886F154ABE092DD76E8676E3F6308E1AC01B1D74D6` /
  `7B413177E5077777F2178143839C0155B03B92BBC8B3A6607621A7D43F351141`;
- ledger SHA-256:
  `6008E509AC4FE721147D4E890E7451BEAC5E06477808D70EFE15C2383F30F223`;
- root verification SHA-256:
  `AADBB23A8DA76D400F7E75BDD2BFEB46DCB687B1721EA2E263EC537B679770E9`;
- independent Sol-Ultra audit SHA-256:
  `52BCFCD68677368299B03CAF66751508607EB88E57F841F81499CBA2ECD31064`.

The 576-run execution is valid, but parent and candidate are both `86/144`,
with 0 gains, 0 regressions, 144 ties, and byte-identical primary traces on
all 144 keys.  The candidate has zero activations and zero realized successor
transactions.  It fails the absolute-strength, gain, exposure, and mechanism
gates.

## Root-accepted next hypothesis

Name:
`alakazam_mandatory_draw_reserve_kadabra_resource_first_v1`.

Parent and deck:

- direct parent:
  `candidates/alakazam_parent_end_strict_prize_lead_retreat_ko_bridge_v3`;
- parent source/runtime/deck SHA-256:
  `49E954F53E043CD79D928DFB2340CCB5D85A17F33CCB824C871CCE153C0C9C95` /
  `9CA7A415451B84343165EF8A5CDC0D67BBF1B4969A13C984C09B142B4898CD9A` /
  `7B413177E5077777F2178143839C0155B03B92BBC8B3A6607621A7D43F351141`;
- deck remains byte-identical and exactly 60 cards;
- no Xerosic, stage-up, Night Stretcher-target, or Great-Tusk rule is stacked.

Hypothesis: when no fully public, deterministic current-turn win is
certified, preserve one card for the next mandatory draw.  In the exact
publicly exhausted-Alakazam state, establish resource-neutral disruption and
the remaining Kadabra attacker before entering optional draw/search.

## Positive live anchor

Episode `86746844` replay SHA-256
`E7802FA07A96F924D6F18F36C013BA25FA29CCC158B3FD3626488939B7562A8D`.
The authenticated/root refresh is
`live/54802782/refresh_20260719_0524/ROOT_REFRESH_VERIFICATION.md`, SHA-256
`D7FA9CABECBE2DAD3536543B69AD9B446177B4B412E222B2908D32FCC72F8893`.

### Recorded evidence discrepancy

The initial qualitative replay summary and Sol-Ultra selection prose described
step 135 as prizes 2-2.  Root subsequently extracted the exact acting-player
Observation with the checked replay iterator and verified remaining prizes as
**own 2, opponent 3** at steps 135 and 150.  They first become 2-2 at step 167
after the later opposing KO/Prize.  This discrepancy is recorded explicitly;
it is not silently repaired.  Implementation fixtures must use raw 2/3 and
the latch must preserve observed Prize counts rather than hard-code either
value.  The causal deck-out diagnosis and selected rule direction are
unchanged.

- exact-v3, submitted stage-up, and recorded policy are identical on all 82
  target decisions; stage-up did not fire;
- step 135: deck 9, own prizes 2 and opponent prizes 3, old Active Kadabra
  `742/#69` with no Energy, hand Basic Psychic `5/#117` and Enhanced Hammer
  `1081/#100`; both exact Active attachment and Hammer were legal;
- all three Alakazam plus both recovery cards were publicly exhausted;
- exact-v3 entered an optional draw/search chain and depleted deck `9 -> 0`;
- at deck 1 it attached Enriching Energy to Bench Dunsparce while the Basic
  Active attachment and Hammer remained legal;
- it then lost at the next mandatory-draw checkpoint after the opponent KO,
  with prizes still 2-2;
- steps 124-126 prove that Dudunsparce draw, Basic Active attachment, and
  Powerful Hand can resolve, but do not certify a step-135 attack because no
  Alakazam remained.

## Frozen behavioral contract

1. Compute exact-v3's finalized action first.  This is a post-parent overlay;
   unrelated scoring, deck, setup, Xerosic, Night Stretcher, and matchup rules
   remain exact-parent.

2. Maintain one card for the next mandatory draw in a nonterminal state.  For
   every explicitly covered optional deck effect, conservatively compute the
   public post-resolution deck count.  Mask the action/count only when it can
   leave fewer than one card.  Cap variable-count searches at
   `deckCount - 1`; select zero only when the engine says zero is legal.
   Covered families must be explicit and engine-verified: Fez draw, Psychic
   Draw evolutions, Enriching Energy, Telepath search, Dudunsparce Run Away
   Draw, Poffin, Poke Pad, Hilda, Dawn, and any additional effect the worker
   intentionally includes.  Unknown effects fail closed to the parent.

3. The only reserve exemption is an exact, public, deterministic current-turn
   game win.  It must bind the ready attacker, target, counter/damage rules,
   Prize or board-out result, and every intervening action.  It may not depend
   on hidden identities, future search, hypothetical evolution, Boss
   acquisition, or projected attackers.  An exemption creates a latch that
   forces the certified attack next.

4. Start the Kadabra resource-first transaction only when all predicates are
   exact:

   - MAIN, same player and turn, no conflicting emergency latch;
   - all three Alakazam plus Night Stretcher and Sacred Ash are publicly
     exhausted;
   - no ready Bench attacker exists;
   - Active is old, unstatused Kadabra with no Energy;
   - exactly one Basic Psychic-to-that-Active option exists;
   - exactly one Enhanced Hammer play and one unambiguous opponent-Active
     Special Energy target exist;
   - exact-v3 is about to begin or continue an optional draw/search chain;
   - no certified immediate win exists.

   Required order:
   `Hammer play -> exact Special Energy target -> Basic Psychic to the same
   Active Kadabra -> exact-v3 among reserve-safe actions`.

5. Latch turn/player, own Active and opponent Active serials, Basic/Hammer/
   target serials, deck count, Prize counts, and stage.  Repeated identical
   callbacks return the cached action.  Any unexpected board delta,
   turn/player change, malformed callback, missing/ambiguous option, or
   conflicting latch clears the resource transaction and delegates to
   exact-v3.  The generic reserve guard remains independently fail-closed.

6. Do not alter Night Stretcher targets, Xerosic behavior, Great-Tusk-specific
   logic, setup, or any ordinary action whose verified effect leaves the one
   card reserve intact.

## Required engine verification and focused tests

Before implementation promotion, verify exact draw/search counts and zero-
selection legality for every covered effect; Dudunsparce shuffle accounting
including pre-evolutions/Energy/Tools; Enriching short-deck behavior and the
mandatory-draw loss checkpoint; Hammer context/ownership/target serial;
Basic-to-old-Kadabra attachment and later Super Psy Bolt legality; Psychic
Draw/Telepath timing; terminal-win certificates; callback caching and option
order.

Focused fixtures must include:

- step 135: Hammer target then Basic-to-same-Active, deterministic repeats;
- step 150/deck 1: Enriching and every deck-zero action suppressed;
- deck 1/2 Poffin and Poke Pad zero/capped selection;
- Fez, Psychic Draw, Telepath, Enriching, Dudunsparce reserve boundaries;
- Dudunsparce net-deck accounting with attached component variants;
- certified final-win exemption immediately followed by pinned attack, plus
  near-KO and hidden-enabler negatives;
- negative resource ordering when any Alakazam/recovery remains, ready Bench
  attacker exists, status/attachment conflicts, Hammer/Basic/target is absent
  or ambiguous, turn changes, or latch is stale;
- exact-parent step-87 Night Stretcher, all Xerosic callbacks, early setup, and
  unrelated opponents;
- compile/import, parent/deck hashes, legal 60 cards, source/runtime parity,
  option-order invariance, repeated-call determinism, and both-seat checked-
  engine smoke.

## Fixed evaluation gates

Use the existing 144-key schedule SHA-256
`4271E31503F37EFE4B1BBB9ED2D3569D79D9C1E9B2A20387CCAC131F28346010`
with identical-policy duplicate controls.

- candidate at least `88/144`, at least two paired gains, zero regressions;
- Historical Silver at least `9/16`;
- P0 at least `45/72`, P1 at least `41/72`, neither below parent;
- known at least `44/72`, fresh at least `42/72`;
- Great Tusk at least `4/16`, Alakazam Rmy at least `7/16`, no opponent decline;
- zero action errors, max-step hits, duplicate differences, schedule defects;
- at least four reserve activations spanning both seats and seed blocks;
- every first difference is an authorized resource-first or reserve action;
- at least two changed games convert the saved reserve into another own turn,
  attack, Prize, or win; merely delaying deck-out does not count;
- no parent immediate KO or certified current-turn win is removed.

If Phase-0 passes, freeze a new 128-game Alakazam mirror confirmation:
Oselcoun and Rmy, both seats, 32 predetermined seeds per opponent/seat, half
established and half fresh.  Require candidate `>=64/128`, at least four gains,
zero regressions, nonnegative each seat/opponent/seed half, at least eight
reserve activations, four complete resource-first transactions spanning both
seats/opponents, and at least two parent immediate deck-outs converted into an
additional attack or Prize.

No live probe is currently authorized.  Eligibility would require all gates,
independent numerical agreement, root raw verification, package/both-seat
smoke, frozen-file checks, and an authenticated pre-submit refresh.  Current
authenticated state is score `739.8548731331897`, record 31-22, and 2/5 slots
remaining until the 09:00 JST reset.
