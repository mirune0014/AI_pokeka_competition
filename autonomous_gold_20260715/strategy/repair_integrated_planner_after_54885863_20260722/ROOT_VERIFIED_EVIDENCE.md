# Root-verified evidence after live submission 54885863

## Immutable live evidence

- Submitted agent: `alakazam_integrated_domain_turn_planner_v1`.
- Kaggle submission ID: `54885863`.
- Submitted source SHA-256: `93E2567F4352EE4C4FCEEB3D32B954119F3DC4E8F96DF5498317E781C5804086`.
- Clean archive SHA-256: `4DA4E8FB35D7C83AE6F0A60A0AB741A914BE091591EE0358992A504EEB8D6B98`.
- Episode CSV SHA-256: `05F01458D0B70BD068B0EEA64D17A57B860A0138481CDCFDB15A3D6E92E8CCD7`.
- Kaggle CLI snapshot SHA-256: `7EC38F6147819D00313736A687457E8B032EB81F997B31013288874504F12B00`.
- Root replay-shadow JSON SHA-256: `716D220A8C2E85E6507C3FF19C9561943B62BDB5CAD9432D9E7BABC29FD93741`.
- Bucket A qualitative report SHA-256: `EB76C75CDA79B8C93FFA930F7D7F643B16001B82CF7188C207048897CEB6C393`.
- Bucket B qualitative report SHA-256: `DE26D3E3CBA5097247969ECF97C0F599320AC9CF0603421E77AFE819FFF665B7`.

Root recomputed the episode table directly. Submission 54885863 is complete at
displayed score `533.8` and exact terminal score `533.8550055291732`. It has
one validation game and 19 public games, with public result `8-11`. The UTC
2026-07-21 quota snapshot has two submissions, so three of five slots remain.

The exact clean-package shadow over all 19 public games covered 967 correct-seat
callbacks. It had 15 causal first forks, zero invalid actions, zero duplicate
mismatches, zero parent-call mismatches, zero unclassified overrides, zero
missing traces, zero emergency actions, and zero mandatory fallbacks. Runtime
validity is intact; the live failure is semantic policy breakage.

## Root-verified causal defects

Six of the eleven losses have a directly reproduced integrated-planner
regression as their earliest supported causal defect:

1. `87328101/S20`, seat 1: parent Dawn is replaced by Abra's fixed 10-damage
   Teleportation Attack into a 160-HP Cinderace. The trace has no H1/H2 and
   calls a 16-hit lane certified.
2. `87328994/S18`, seat 1: parent Fezandipiti ex, with visible Kadabra/Alakazam
   evolution options, is replaced by fixed 10 damage into a 150-HP Crustle.
   The trace has no H1/H2 and calls a 15-hit lane certified.
3. `87333954/S32`, seat 0: a legal free Dunsparce Bench play is replaced by
   fixed 10 damage into a 140-HP Hop's Trevenant. The same override repeats
   while the board is removed.
4. `87335926/S52`, seat 1: parent Run Away Draw is replaced by a three-card
   Powerful Hand for 60 counters into a 110-HP Seaking. Run Away Draw
   deterministically reaches six cards, after which the same-turn Powerful
   Hand places 120 counters and takes the visible KO.
5. `87336304/S39`, seat 0: a legal Dunsparce Bench play is replaced by 30
   nonlethal damage into a 110-HP Solrock. The following Powerful Hand already
   had enough damage to KO 110 HP, so the 30 damage did not shorten the lane.
6. `87330854/S25`, seat 1: the only in-play Pokemon is Active Dudunsparce and
   the Bench is empty. `RUN_AWAY_SETUP_CLOCK` overrides parent END, shuffles
   away the sole Pokemon, and the immediately following row is terminal loss.

The source mechanism is independently visible in code. Setup-stop treats any
available attack as a candidate against PLAY/ABILITY/END and assigns it
`preserve_H0_lethal=True`, even when it is nonlethal and there is no H1/H2.
The lane certificate can then make a 14-16-hit current-Active lane outrank
setup without modeling that setup may occur before the same attack. The Run
Away predicate checks only deck count; it does not require a surviving Bench
Pokemon or legal promotion after the source shuffles away.

The other five losses do not justify widening this repair:

- inherited generic-policy weaknesses: `87328524` (missed ready-Alakazam
  retreat/attack and later wrong Mist-Energy Hammer child), `87332922`
  (promoted an unenergized valuable Alakazam into visible lethal), and
  `87335709` (failed to make an exposed one-retreat Genesect ready before a
  visible control trap);
- publicly uncertifiable opening losses: `87330378` and `87331806`, each with
  a sole low-HP Basic and no public Bench/survival line.

Neither independent replay audit attributes any first causal loss to the
`Handheld Fan 2 / Lucky Helmet 1` deck package. Keep that package unchanged in
the next isolated repair so policy and deck causality are not mixed again.

## Decision question for Sol-Ultra

Select exactly one coherent deterministic public-state repair. The root's
preferred hypothesis is one fail-closed **integrated override admissibility
gate**:

- speculative `INTEGRATED_SETUP_STOP_ATTACK` may not replace setup merely
  because an attack is legal or because a multi-hit current-Active lane can be
  enumerated; delegate to the cumulative parent unless the current attack
  produces an exact immediate Prize/terminal gain or preserves an already
  exact lethal floor that the parent action would cross below;
- retain the existing dedicated terminal and `POWERFUL_HAND_FLOOR` routes for
  those exact cases;
- reject Run Away Draw whenever removing its source leaves no in-play Pokemon
  and therefore no legal promotion/surviving board;
- make no inherited retreat, promotion, Hammer, attachment, matchup, or deck
  change in this candidate.

The implementation should be a fresh direct child of the submitted integrated
source, keep `Fan 2 / Helmet 1`, preserve the exact cumulative parent and all
other planner routes, and fail closed to the parent's already valid action.

Mandatory positive fixes are the six rows above. Mandatory retained integrated
routes are live `87329461/S19` Run Away with a surviving Bench, `87329922/S58`
and `87331334/S58` exact Powerful Hand floors, plus every original terminal,
Boss, retreat-handoff, Fan, clock, duplicate, and package structural fixture.
Run the current 19-game callback shadow and historical callback shadow; every
new first difference must be explained. A both-seat smoke is breakage-only:
wins and losses are diagnostic and do not block the user-authorized live probe.

