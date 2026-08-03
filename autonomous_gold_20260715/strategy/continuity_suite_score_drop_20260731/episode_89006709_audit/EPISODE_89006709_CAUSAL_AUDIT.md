# Episode 89006709 causal audit

## Scope and integrity

- Sole replay: `autonomous_gold_20260715/evidence/continuity_suite_score_drop_refresh_20260731/episode_89006709_replay.json`
  - SHA-256: `3039AABB52326B3478B50F69C9372CFD058FCC853AF84DD6A29D2555171AB45B`
- Replay inventory: `SHA256SUMS.txt`
  - verified SHA-256: `DCDF5AAD4917BD7191FEB37BB104920869346ABDA8DE7E05DF6E9806992986AF`
- Final suite source SHA-256:
  `E7F8B3A6E84BD129BBDF5C49C524446BF3DFBE9C95C16F069F435CA104DCF65C`
- Direct-parent source SHA-256:
  `6504E0E3EA69D59EAB5F9A73E306D70695A0E76ECA8D347C97F1EB43AEE31B7A`
- Seat 1 (`rurumi`) lost, reward `-1`.

## Verdict

`SACRIFICIAL_ACTIVE_BENCH_EVOLUTION_ROUTING_V1` was **beneficial, medium
confidence**, relative to the direct parent's Active-63 evolution. It was not
the evident cause of this loss. The game-outcome counterfactual remains
indeterminate because declining the turn-10 knockout changes the opponent's
hidden prize draw and later policy, but the public continuation makes a parent
flip to a win implausible.

## Exact divergence state and transaction

Immediately before the step-84 callback (seat 1, turn 9, action count 6):

- Full Metal Lab was in play; the manual Energy attachment and Supporter had
  already been used.
- Own prizes/deck/hand count: `5 / 14 / 6`.
- Active Duraludon `serial63`: `30/130 HP`, zero Energy, no Tool.
- Bench Archaludon ex `serial69` (from Duraludon 66): `320/400 HP`, Hero's
  Cape, Metals `115,120,121`; it was already attack-ready.
- Bench Duraludon `serial64`: `130/130 HP`, Metal `116`.
- Hand: Archaludon 91, Archaludon ex 67, Archaludon ex 70, Archaludon 92,
  Explorer's Guidance 103, Cinderace 73.
- Exactly one public Metal was in discard: `serial119`.
- Opponent Active Mega Lucario ex `serial3`: `340/340 HP`, Metal `57`; Aura
  Jab (`attackId=982`, one Energy) was already payable. Bench included Mega
  Lucario ex 6 with three Energy, two Lunatone, and Riolu 9.
- Opponent prizes/deck/hand count: `5 / 25 / 3`.

The shadow row records the only candidate/parent difference:

- Parent: evolve Archaludon ex 67 onto Active Duraludon 63.
- Candidate/recorded: evolve Archaludon ex 67 onto Bench Duraludon 64.

Recorded transaction continuation:

- Step 85 log: ex 67 evolved Bench 64; the new ex had `300 HP` and retained
  Metal 116.
- Steps 85-87: accept Assemble Alloy, bind the sole discard Metal 119, and
  target the newly evolved ex 67.
- Step 88 log/state: Metal 119 attached to ex 67, leaving it at full `300 HP`
  and two Energy. Active 63 remained the damaged one-prize pivot; ex 69
  remained the ready attacker.

## Earliest downstream consequence

The first causal consequence is at steps 91-96:

- On opponent turn 10, Mega Lucario ex 3 attached a second Energy and used
  Aura Jab at step 91. Full Metal Lab reduced 130 to exactly 100. Duraludon 63
  fell from 30 HP to zero.
- Aura Jab then loaded two more Energy onto the opposing Bench Mega Lucario;
  Duraludon 63 moved to discard at step 94. The opponent took one prize at
  step 95 (five to four).
- At steps 95-96, seat 1 promoted the already-ready, Cape-bearing ex 69.
- At steps 98-99, ex 69 immediately used Metal Defender (`attackId=253`) for
  220, taking opposing ex 3 from 340 to 120.

Under the parent Active-63 evolution, the 100 existing damage would carry onto
the 300-HP Archaludon ex, leaving 200 HP before the attack. The same already
payable Aura Jab would leave it at 100 HP, not knock it out. Assemble Alloy
could add at most the sole public discard Metal, so that Active would have at
most one Energy against a three-Energy attack cost and a two-Energy retreat
cost. Thus the parent route preserves a stranded two-prize Active and blocks
promotion of ready ex 69. The candidate instead concedes one prize to obtain
immediate attack access.

This comparison is deterministic through the survival/knockout fork. Later
actions are not deterministic: no knockout means no opponent prize draw, and
turn-11 search choices could diverge. Those hidden branches prevent a proven
winner counterfactual, but they do not supply a public parent advantage.

## Relevant recorded continuation

- Turn 12, steps 109-113: Wally's Compassion fully healed opposing ex 3,
  returned its Energy, and Aura Jab reduced own ex 69 from 320 to 220.
- Turn 13, steps 116-118: Lillie's Determination found Metal 112; step 117
  attached it to Bench ex 67, making the routed line three-Energy ready. Ex 69
  again used Metal Defender.
- Turns 14-16, steps 121-134: a second Wally's Compassion reset opposing ex 3;
  repeated Aura Jabs reduced ex 69 to 20 HP while Metal Defender repeatedly
  left the opponent at 120.
- Turn 17, step 138: ex 69 finally knocked out Mega Lucario ex 3 and took three
  prizes (five to two).
- Turn 18, steps 140-145: Mega Lucario ex 6 was promoted; Aura Jab knocked out
  the 20-HP ex 69. The opponent took two prizes (four to two).
- Turn 19, steps 146-150: routed ex 67 was promoted with three Energy. Boss's
  Orders pulled Lunatone 14, Metal Defender knocked it out, and seat 1 went
  from two prizes to one.
- Turn 20/21, steps 154-159: Mega Brave (`attackId=983`) reduced ex 67 from
  300 to 60; Night Stretcher recovered Duraludon 65, which was benched and
  given Metal 122; ex 67 attacked Mega Lucario ex 6 to 120.
- Turn 22, steps 163-164: Aura Jab dealt the final 100 to ex 67. The opponent
  took its last two prizes and won.

The routed Bench evolution therefore supplied both the immediate sacrificial
pivot and the later ready replacement. It did not create an attack-access,
retreat-lock, Energy-allocation, survival, prize-yield, or target-selection
regression in the recorded line.

## Certificate transfer from episode 88947304

The action did **not** generalize incorrectly in causal direction. The central
88947304 mechanism transferred: a zero-Energy one-prize Active was publicly
knockable as a Basic but would survive as a stranded two-prize evolution, so
Bench evolution preserved the sacrificial pivot and unlocked a ready attacker.

The certificate's explanatory attribution is nevertheless incomplete in this
episode. Unlike 88947304, a third line—Cape-bearing ex 69—was already fully
ready. Ex 67 was not the immediate next attacker; ex 69 was. The rule does not
check for that already-ready third line, so “evolve the unique nearer-ready
Bench target” is not the precise reason the action helped here. The precise
reason was that leaving Basic 63 Active allowed the publicly payable Aura Jab
to remove a one-prize pivot and free ex 69, whereas Active evolution would
survive and obstruct it. This is a scope/attribution mismatch, not a harmful
false positive in episode 89006709.

## Independent preventable decision

The clearest independent policy failure occurs at steps 136-142, not step 84.
At step 137, own Active ex 69 had `20/400 HP` and three Energy; Bench ex 67 had
`300/300 HP` and three Energy. Opposing Active ex 3 had `120/340 HP`, so either
own ex could preserve the same 220-damage knockout. Retreat was legal, but the
recorded policy attacked from ex 69.

After the knockout, every visible, currently payable ungusted response from a
fresh 340-HP Mega Lucario was at most Mega Brave's 270, reduced to 240 by Full
Metal Lab. Ex 67 would therefore survive at 60 HP. Instead, the opponent
promoted ex 6 and used Aura Jab for 100 at step 142, removing ex 69 and taking
two prizes. Rotating before the step-138 knockout would have preserved the
attack and denied that immediate active knockout under the visible line.

This is a high-confidence avoidable survival/prize-sequencing error. Whether it
flips the final winner is still indeterminate because a changed Active permits
hidden gust or different opponent play, but it is materially more plausible as
a loss contributor than the step-84 evolution route.

## Failure hypothesis and regression risks

- Primary observed pressure: opponent strength/resource loop—two Wally's
  Compassion resets, multiple powered Mega Lucario ex, and a three-prize
  attacker that Archaludon's 220 damage could not one-shot.
- Policy contribution: failure to rotate from the 20-HP attacker at step 137,
  followed by a two-prize knockout.
- Deck construction and variance: not separable from this single replay; no
  deck-construction claim is certified.
- Counterfactual risks: hidden Boss's Orders could punish a benched wounded ex;
  altered prize draws and search choices invalidate deterministic continuation
  past the first changed knockout; sacrificial routing would be risky when the
  Basic is not publicly knockable or the evolved Active becomes payable.

No implementation change is proposed by this audit.

## Raw rows for numerical/root verification

- Replay observations/logs for seat 1 at steps `84,85,88,95-99,115-118,
  126-138,145-149,154-159`, and seat 0 at steps `89-94,99-113,118-124,
  130-145,150-164`, in the immutable replay above.
- Exact shadow difference:
  `autonomous_gold_20260715/root_verification/continuity_suite_score_drop_20260731/submission_55113800/candidate_parent_differences.csv`,
  data row 2.
- Attribution transaction callbacks:
  the episode-89006709 rows for steps 84-87 in
  `autonomous_gold_20260715/root_verification/continuity_suite_score_drop_20260731/submission_55113800/callbacks.csv`.
- Episode summary:
  the episode-89006709 row in
  `autonomous_gold_20260715/root_verification/continuity_suite_score_drop_20260731/submission_55113800/per_episode.csv`.

These rows should be quantified only by the numerical evaluator/root; this
single-game audit makes no frequency, rate, promotion, or slot-use judgment.
