# H3 strategy selection — certified lone-Cinderace line formation

## Decision

Select exactly one next mechanism:

`H3_CERTIFIED_LONE_CINDERACE_ULTRA_BALL_TURBO_FLARE_LINE_FORMATION`

Implement H3 directly from exact historical-Silver. H1 and H2 are unstacked
siblings and must not appear in the source or package.

H3 owns one current-turn plan:

`Ultra Ball -> safe discard pair -> Duraludon -> Bench Duraludon ->
Turbo Flare -> attach the maximum legal Basic Metal to that Duraludon`.

This is a board-formation and attack-effect conversion rule. It is not a
Mega-Lucario matchup marker and it must not infer an opponent's hidden hand.

## Frozen identities

- Exact parent source:
  `analysis_outputs/reference_agents/historical_silver_archaludon_54495224/main.py`.
- Parent source SHA-256:
  `F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E`.
- Parent deck SHA-256:
  `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`.
- Positive replay:
  `live/55064711/refresh_20260729_0630/episode_88684114_replay.json`.
- Positive replay SHA-256:
  `A2EAB58DB12221A9BB6D31AE56499193CF3DC294AE162320F03499E1CB1A9534`.
- Positive callback:
  episode `88684114`, row `20`, seat `0`, turn `2`.

## Root-verified positive

At row `20`:

- our board is exactly one full-HP Cinderace `666#14` with one Basic Metal and
  an empty Bench;
- both players have six Prizes;
- opposing Active Lunatone has `110` HP;
- Turbo Flare `965` is a legal `50`-damage non-KO;
- Ultra Ball `1121#21` is legal;
- hand is exactly:
  Archaludon ex `190`, Boss `1182`, Hero's Cape `1159`, Ultra Ball `1121`,
  Lillie `1227`, and Ice Cream `1147`;
- parent action is `[3]`, Lillie; it later attacks at row `25` with the Bench
  still empty;
- the opponent does not KO Cinderace on its immediately following turn;
- our row `42` starts turn `4` still with a lone Cinderace;
- the opponent plays Gravity Mountain at row `64`, attacks with Aura Jab
  `982` at row `65`, and the no-Pokémon loss completes at row `70`.

The replay's row-20 stored action `[4]` is not a Turbo Flare choice from the
row-20 observation. It belongs to the preceding Metal attachment. No test may
use the stored action as an action label.

## Public count-only access certificate

H3 may use only public counts and the fixed legal deck list. It must never
read hidden deck or Prize contents.

For a target card with `K` unseen copies distributed across `N = deckCount +
prizeCount` hidden positions, the probability that at least one copy is in
the deck is:

`P(deck access) = 1 - C(prizeCount, K) / C(N, K)`,

with probability `1` when `K > prizeCount`.

At the positive, all four Duraludon are unseen, `deckCount=46`,
`prizeCount=6`, and:

`P = 1 - C(6,4)/C(52,4) = 0.9999445932219041`.

The H3 threshold is fixed at `0.999`. Known public access also passes. No
opponent identity, hidden-card pattern, replay frequency, or learned proxy may
modify this threshold.

Root correction: at row `20`, eleven Basic Metals are unseen, not ten. Since
at most six can be Prized, at least five are in the deck. Turbo Flare therefore
has a deterministic supply of at least three Basic Metals before Ultra Ball.
The implementation must recompute this lower bound from public zones and the
fixed deck count; it must not peek at the hidden deck.

## Arm certificate

At an ordinary `MAIN` callback, H3 may arm only when every condition holds:

1. Our board contains exactly one Pokémon: Active Cinderace and empty Bench.
2. Cinderace is not affected by a public condition or modifier that makes
   Turbo Flare probabilistic or illegal.
3. Turbo Flare is legal, is not a KO, and is not an exact same-turn match win.
4. Bench space exists.
5. A legal Ultra Ball is in hand.
6. No Basic Duraludon is already in our Active, Bench, or hand.
7. Duraludon `169` known access passes, or its count-only access probability
   is at least `0.999`.
8. Public Basic-Metal counts prove that at least three Metals remain in the
   deck after the Ultra Ball play.
9. Exactly two deterministic safe discards can be selected while protecting:
   the Ultra Ball, all current attack-completing Energy, any visible Basic
   backup, the sole visible Archaludon ex needed for the searched Duraludon,
   the last visible draw/access Supporter, and every component of an exact
   current-turn terminal conversion.
10. At the positive, the only certified safe pair is Ice Cream while the
    full-HP Active cannot use it, plus Boss while the opposing Bench is empty
    and no current Boss conversion exists.
11. No exact same-turn terminal attack, terminal Boss route, or mandatory
    engine callback has higher precedence.
12. Benching the 130-HP Duraludon does not create a public, deterministic
    immediate multi-Prize or board-loss regression from a visible spread
    effect.

If more than one semantic safe discard pair exists, choose the
lexicographically lowest pair by `(card id, serial)` after all protection
rules. Do not use score ties.

## Precedence

1. Mandatory engine callbacks and hard legality.
2. Exact same-turn match win or already-complete parent terminal conversion.
3. Public deterministic board-loss or harmful-attack veto.
4. H3 complete transaction.
5. Exact historical-Silver.

H3 never imports H1/H2 precedence or state.

## Transaction and engine-map requirement

Before editing the policy, the implementation worker must produce a
callback-map report for the exact engine showing every context between:

`Ultra Ball play` and `three Metals attached to the reserved Duraludon`.

The policy stages must follow the observed engine callbacks, not guessed
context numbers. At minimum they must cover:

1. choose the stored Ultra Ball;
2. choose the stored safe discard pair;
3. choose Basic Duraludon from the revealed Ultra Ball search;
4. after Duraludon is publicly observed in hand, play that serial to the Bench;
5. after the Bench serial is confirmed, choose Turbo Flare;
6. choose the maximum legal number, up to three, of lowest-serial Basic Metals;
7. choose only the reserved Benched Duraludon for every required Energy target
   callback;
8. clear after the attack/effect is publicly confirmed.

Snapshot at arm:

`(seat, turn, Prize counts, Cinderace serial/HP/Energy, Ultra Ball serial,
safe discard serials, protected hand serials, deckCount, prizeCount,
Duraludon unseen count/probability, Basic-Metal public count/lower bound,
opposing Active/Bench/public modifiers, option signature)`.

A returned action never advances the stage. Advance only when the next public
observation or log proves the previous semantic action resolved. Repeated
identical callbacks return the same semantic choice with the lowest legal
indices.

Clear on deck request, new game, result, turn/seat change, missing source or
reserved target, unexpected board or protected-hand mutation, unavailable
expected option, completed attack, or exception. Before any card is consumed,
clear and delegate to the parent on mismatch. After a consumed card, rollback
clears only H3 state and delegates from the actual current observation.

If Ultra Ball search publicly reveals no Duraludon, choose zero cards only
when legal, clear, and delegate. Never choose another Pokémon as a hidden
fallback.

## Required positives

1. Exact row-20 first difference:
   parent Lillie versus H3 Ultra Ball.
2. Exact-engine completion of the entire transaction with the positive hidden
   state, ending with the searched Duraludon Benched and the maximum legal
   Basic Metals attached.
3. Both-seat synthetic equivalent with changed card serials.
4. Permuted legal-option order at every stage.
5. Repeated callback idempotence at every stage.
6. A separately generated non-Lucario opponent state satisfying the same
   public certificate and completing the transaction.
7. A probability-boundary positive at exactly `P >= 0.999` and a negative just
   below `0.999`, computed only from public counts.

## Required negatives

Exact replay negatives:

- `88411737`, rows `17`, `25`, `27`, seat `0`, replay SHA-256
  `A5EE7C17FDB344CCB815485429C9F3AA2E73543AB19B407EC2003A4C0BB60595`:
  lone-Cinderace Turbo Flare states with no Ultra Ball;
- `88338429`, rows `16`, `18`, seat `0`, replay SHA-256
  `C3E7D8FEAAB9274A8F28F10BF80E2DE840B760D6F0E7D329675D3D2FC043C247`:
  same required no-Ultra-Ball negative.

H3 must also remain parent-identical when:

- any successor is already in play or hand;
- no Ultra Ball, insufficient safe discards, or protected-card conflict exists;
- Turbo Flare is illegal, probabilistic, a KO, or a current terminal win;
- the count-only Duraludon access probability is below `0.999`;
- fewer than three Basic Metals are publicly guaranteed to remain in deck;
- visible spread or damage modifiers make the new Duraludon a deterministic
  worse Prize/board loss;
- multiple or ambiguous callbacks cannot be mapped to the stored semantic
  card/target;
- an H1, H2, higher-Prize Boss, non-KO exposure, Bench-damage, or promotion
  example is encountered outside the H3 certificate.

## Forbidden generalizations

Do not implement:

- “always Ultra Ball with an empty Bench”;
- generic backup search;
- opponent/archetype/episode/row/seed/serial matching;
- Mega-Lucario, Gravity Mountain, or Aura Jab hidden-hand inference;
- hidden deck or Prize inspection;
- learned matchup frequency or opponent-policy proxy;
- generic discard scoring;
- H1/H2 stacking;
- other attackers, search cards, or attack effects.

## Shadow, engine, and evaluation gates

- Verify parent/deck/strategy/replay hashes before edits.
- Compile/import, loader-last `agent`, legal 60 cards, ACE SPEC exactly one,
  exact runtime closure, and cache-free candidate.
- Full latest replay-corpus correct-seat shadow with zero invalid actions and
  exceptions.
- The positive's first difference must be exactly `88684114:20`.
- The recorded Lillie continuation at row `21` must make H3 clear cleanly with
  no downstream ownership leakage.
- Both exact negative replays must have zero differences.
- Root must inspect every other natural first difference.
- Exact-engine complete transaction in both seats, changed serials, permuted
  options, duplicate semantic options, every rollback stage, new-game reset,
  and exception fallback.
- Fixed 760 parent/H3 evaluation on identical seeds and both seats, with
  retained action traces. Require zero command/action/max-step faults, zero
  paired regressions, no seat or primary-anchor regression, and no adjacent
  floor regression.
- Require at least two completed engine transactions, both seats represented,
  including the positive and one non-Lucario synthetic state.

A structurally clean candidate may receive one exploratory live probe only
after the H1/H2 queue and a separate final Sol-Ultra judgment. Neutral or weak
local win rate does not by itself block the user-authorized exploratory probe,
but invalid actions, incomplete transactions, trigger-external divergence, or
any paired regression do.
