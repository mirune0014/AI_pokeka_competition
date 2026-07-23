# Reject Sacred Ash timing v1; select recycle-backed draw-budget corridor v1

Recorded: `2026-07-19 14:14:36 +09:00`  
Owner: root  
Kaggle authorization: none

## Completed candidate disposition

Candidate `alakazam_public_sacred_ash_reserve_timing_v1` is rejected as a
parent, package, live submission, and exploratory submission. Preserve it
only as unstacked research evidence. Exact-v3 remains the parent.

Authoritative root evaluation report:
`14610B9F40D10EA81AA06501B45BEFDE7F7AAAC942DD66F271C02685DF66F614`.
Independent numerical report:
`0ED8B6F4797F25D36A16B4C1FE7E6D32719E293B777A37B2CE94564A1230F27C`.

The matrix was structurally valid but exact-v3 and candidate were both
`86/144`, with `0G/0R`. Silver remained `8/16`, Rmy `7/16`, mirrors `15/32`,
P1 `41/72`, and fresh `42/72`. Six certified holds activated with zero
defects; half were same-turn reorderings, and the higher-yield/extra-Prize
cases never changed an outcome. No evidence is missing for rejection.

## Selected exact-v3 sibling

Select one Phase-A-only hypothesis:

`alakazam_recycle_backed_draw_budget_corridor_v1`

No source edit, package, archive, or submission is yet authorized. A strict
next-turn-only Sacred Ash hold is not selected: it would remove same-turn
reorderings but retain delayed cases already shown not to flip outcomes. The
selected corridor instead coordinates multiple public deck expenditures and
can alter the terminal deck clock.

## Public variables

- `D`: own deck count;
- `P`: own Prizes remaining;
- `B = D - P - 1`: optional-draw budget after reserving the Prize/start-draw
  floor;
- tight clock: `1 <= P <= 6` and `D <= 3P + 2`;
- `u`: unique serial-exact Bench Dudunsparce;
- `R(u) = 1 + preEvolutionCount + energyCardCount + toolCount`;
- `D_recycle = D + R(u) - 3`;
- `h`: unique visible Lucky Helmet serial;
- `ready_now`: Active Alakazam has public Psychic Energy, legal Powerful
  Hand, and visible current-hand damage already converts the certified target
  without unknown draws;
- `ready_backup`: a distinct attacker is Energy-ready, or can become ready
  this turn using only visible evolution/Energy resources and the unused
  attachment. Hidden cards never satisfy readiness.

## Corridor admission

Start only at an optional Alakazam Psychic Draw prompt when all are true:

1. exact-v3 finalized `YES`, with unique option/effect/serial mapping;
2. tight clock, nonterminal turn, `ready_now`, and `ready_backup`;
3. unique Bench `u` has a complete serial-distinct stack, legal unused Run
   Away Draw, is not the only Pokémon, and its removal preserves both
   readiness witnesses;
4. visible `h` can legally attach to `u`, and `R(u) + 1 >= 4`;
5. no same-turn final-Prize/board-out route and no exact-v3 transaction latch;
6. player, turn, card, zone, effect, option, and text metadata are complete.

Record player, game, turn, `u`, `h`, initial `D/P/B/R`, and readiness
fingerprints. Ambiguity fails closed.

## Coordinated actions

1. **Psychic Draw:** choose `NO` while the corridor remains valid and the draw
   is unnecessary for current damage/readiness. A second same-turn optional
   draw may be declined only after complete revalidation; otherwise delegate.
2. **Lucky Helmet:** on the same turn, only when exact-v3 would attach recorded
   `h`, attach it to recorded Bench `u`. Do not discard or suppress it. The
   attachment must raise certified return payload to at least four, and may
   not redirect a Helmet from an attacker after readiness fails.
3. **Run Away Draw:** retain the corridor across turns. At the first own MAIN
   with `D <= P + 1`, choose recorded `u` only when `R(u) >= 4`,
   `D_recycle > P`, the ability is legal, another Pokémon remains, and removal
   preserves current plus backup attack continuity. Delegate before the
   brink.

Repeated identical callbacks must return the identical action.

## Release and abort

Release after the certified Run Away transaction, a terminal route, or a
recovered non-tight clock. Abort and delegate on player/game mismatch,
missing or changed serial, Dudunsparce/Helmet zone loss, prior ability use,
failed readiness, active parent latch, disruption that breaks the plan,
unexpected callback, ambiguity, malformed metadata, or unknown relevant
text. Record any post-first-difference abort as an incomplete exposure; no
promotion is permitted if one causes a regression.

## Frozen Phase-A census gate

Before any implementation, census all exact-v3 optional Psychic Draw prompts,
Lucky Helmet attachments, and Run Away options in the frozen 144 primary
traces plus live episode `86778139`. Link public serials across turns and
record every variable above.

Implementation may proceed only with:

- at least four fully certified opportunities across both seats, both blocks,
  at least three opponents, including an Alakazam mirror and Silver or Great
  Tusk;
- at least two complete Draw -> Helmet -> Run Away sequences;
- exact certification of live locators `108/110`, `131`, and `141/143`; a
  locator failing readiness becomes a negative, never a patched positive;
- frozen negatives: live step `128`; Silver fresh/P0/2026101803 unready
  Active-Helmet; Kangaskhan known/P0/2026071586 terminal Helmet; Dragapult
  known/P1/2026071599 unenergized-backup draw; all final-Prize, only-Pokémon,
  `R<=3`, `D_recycle<=P`, ambiguous-serial, and active-latch states.

Targets: Alakazam mirrors and Historical Silver endurance; a certified Great
Tusk recycle exposure is secondary. Mega Lucario, Dragapult, terminal
Kangaskhan, and the prior Silver regression are negative controls.

## Frozen Phase-0 retention gates

If Phase A passes and a new Fast candidate worker later implements the single
corridor, require:

- at least `89/144`, `3G/0R`, gains in both seats and both blocks;
- Silver at least `9/16` with a gain, Rmy at least `8/16`, combined mirrors at
  least `16/32` with a gain;
- P0 at least `45/72`, P1 `42/72`, known `44/72`, fresh `43/72`;
- no opponent decline and every named negative parent-identical;
- at least four completed natural corridors across both seats/blocks, all
  three action stages represented, and at least two complete three-stage
  transactions;
- at least one causal gain where retained deck/start draw enables an
  additional attack, Prize, or non-deck-out finish;
- zero incomplete-plan regressions, semantic defects, action errors,
  max-step hits, duplicate mismatches, schedule drift, or hash drift.
