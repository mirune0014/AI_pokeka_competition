# Alakazam loss audit: exact historical-Silver Archaludon

## Scope and evidence

This is a read-only, public-state audit of the 24 losses frozen in
`ALAKAZAM_LOSS_AUDIT_SPEC.md`. Every listed raw replay and the exact baseline
source were inspected. Opponent actions were not treated as labels, and no
hidden hand was reconstructed.

- Policy:
  `analysis_outputs/reference_agents/historical_silver_archaludon_54495224/main.py`
  (`F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E`).
- Episode CSV:
  `autonomous_gold_20260715/evidence/live_54927163_refresh_20260729_0344/submission_54927163_20260729_0344_episodes.csv`
  (`A94A0754A9D2F84B88DB7D64BC126D4E8FA2855CC0769E799A031F6D4702F64E`).
- Deck manifest:
  `autonomous_gold_20260715/evidence/live_54927163_refresh_20260729_0344/decks/SHA256_MANIFEST.txt`
  (`F347CB1D5B3DB5FB1D4D1CE2098C3C53CBED98A542A1AA015FE894E22445F1F8`).
- Raw replay locator:
  `autonomous_gold_20260715/evidence/live_54927163_refresh_20260729_0344/episode_<EPISODE_ID>_replay.json`.

The exact policy reproduced the recorded target choices at the aligned decision
observations used below.

## Observed source behavior

- `main.py:873-882` returns `save Boss: can KO Active` whenever the current
  Active is KOable and that KO is nonterminal, except when a Bench KO itself
  wins. It does not compare a higher-prize Bench KO or a unique visible threat.
- If Boss is admitted, `main.py:1273-1279` ranks killable targets by prize value
  and attached energy. Thus the existing target scorer already selects
  Fezandipiti ex over a one-prizer and, in episode `88457867`, the energized
  Alakazam over zero-energy Dunsparce.
- `main.py:931-940` hard-disables non-ex Archaludon outside Ogerpon or the
  narrow final-prize gate. `main.py:378-383,433-449` models only Archaludon ex
  as an immediate Duraludon evolution attack route.
- The public Alakazam damage estimator at `main.py:462-484` is used by the Ice
  Cream rule but not by Boss arbitration or a general win/normal/comeback mode.

## Exact decision evidence

`Prizes A-B` means our prizes remaining followed by the opponent's.

| Replay row | Public state | Recorded baseline decision | Qualitative diagnosis |
|---|---|---|---|
| `88457867`, turn 12, steps `142-144,152,155-157` | Prizes 3-2; our Active Archaludon ex `190`, 300 HP/3 Energy. Opponent Active Dunsparce `305`, 70 HP; Bench has the only visible attack-ready Alakazam `743`, 140 HP/1 Energy, plus three zero-Energy Dunsparce. Public opponent hand/deck counts are 21/7. | Pokégear `1122` selected Boss `1182`; Boss then scored `-500`, Explorer was played, and Metal Defender KOed Dunsparce. Alakazam was promoted and Powerful Hand `1072` logged `-440` to `190` for the final two prizes. | High-confidence source-gate error; medium-confidence loss-changing hypothesis. Boss could KO the unique visible ready attacker, leaving no visible Alakazam-line successor. Unknown future cards prevent certainty about the game result. |
| `88417236`, turn 10, step `70` | Prizes 5-6; Active Duraludon `169`, 30/230 HP and 3 Energy; opponent Active Alakazam 140 HP, Bench Fezandipiti ex `140` at 150 HP. Raging Hammer is 280. | Boss scored `-500`; Raging Hammer KOed the one-prize Active although the same attack also KOed the two-prize Bench target. | Exact prize-route miss caused by the same Boss hard gate; outcome effect uncertain. |
| `88171291`, turn 4, step `39` | Prizes 6-6; zero-retreat Cinderace Active and attack-ready Archaludon ex on Bench; opponent Active Dunsparce 70 HP and Bench Fezandipiti ex 210 HP. | Boss scored `-500`; Explorer was preferred. | Exact two-prize-versus-one-prize Boss miss; later resource collapse prevents a confident game-result claim. |
| `87974582`, turn 6, step `72` | Prizes 5-5; Active Archaludon ex 300 HP/3 Energy; Active Alakazam 140 HP and Bench Fezandipiti ex 210 HP. | Boss scored `-500`; Metal Defender KOed the Active. | Exact prize-route miss; loss-changing confidence is low because visible Alakazam pressure remains. |
| `87892692`, turn 4, steps `48,51` | Prizes 5-5; Active Archaludon ex 300 HP/3 Energy; Active Alakazam 140 HP and Bench Fezandipiti ex 210 HP. | Boss scored `-500`; Explorer was played, then Metal Defender KOed the Active. | Exact prize-route and turn-plan commitment miss; outcome effect uncertain. |
| `88096059`, turn 10, step `114` | Prizes 3-3; Active Archaludon ex 300 HP/3 Energy; Active Alakazam 90 HP, Bench Fezandipiti ex 210 HP and two other visible Alakazam; opponent hand/deck counts 26/3. | Boss scored `-500`; Metal Defender KOed the Active. | Exact prize-route miss, but opponent board/hand strength makes causal confidence for the loss low. |
| `87996118`, turn 8, steps `93,95,96` | Prizes 5-3; Active full-HP Duraludon with 3 Energy; opponent Active Alakazam at 90 HP; non-ex Archaludon `840` is legal and in hand. | Non-ex evolution scored `-1000`; Raging Hammer dealt 80 rather than Coated Attack's 120 KO. | High-confidence tactical conversion error; loss-changing confidence is low-to-medium because other public threats remain. Do not bundle this with the first Boss test. |
| `88602602`, turn 10, steps `118,120` | Prizes 4-1; the same 3-Energy Duraludon/non-ex evolution breakpoint exists against a 90-HP Alakazam. | Non-ex evolution scored `-1000`; Boss pulled an 80-HP Kadabra and Raging Hammer KOed it. | Supporting source-gate observation only; the opponent already needs one prize, so superiority is unproven. |
| `88454146`, turns 4/6/8/10, steps `39,63,80,90` | Archaludon ex remains at 2 Energy with no Metal Energy in the shown hand at each cited end-turn decision. | End turn. | Resource-state failure; these rows do not isolate policy from deck construction or draw variance. |
| `88163977`, turns 2/4 and 8/10/12, steps `19,29,43,51,64` | Duraludon has 0 Energy in the first two rows; Archaludon ex has 1 Energy in the later rows, again with no Metal Energy in the shown hand. | End turn. | Resource-state failure; deck construction versus variance is not identifiable from this replay alone. |

No cited certificate depends on Bench damage. The relevant target-selection
errors are Boss routes, while the terminal attacks below target the Active.

## Qualitative failure hypothesis

- **Policy:** the unconditional nonterminal Active-KO Boss suppression collapses
  distinct prize-route and visible-threat states. Episode `88457867` is the
  clearest loss-changing state because known Boss access was obtained and then
  discarded by the hierarchy.
- **Deck/resource/variance:** the exact energy stalls above contain no legal
  tactical conversion. They should not be attributed to the Boss defect.
- **Structural matchup and opponent strength:** a one-prize Alakazam can trade
  into Archaludon ex for two prizes once its public hand is large. Multiple
  visible evolved attackers, as in `88096059`, weaken any claim that one target
  change fixes the game. This is a qualitative structural hypothesis, not a
  deck-change recommendation.

## One recommended certificate for an isolated test

Insert a guarded **endgame threat-removal Boss override** before
`save Boss: can KO Active`:

> In the Alakazam matchup, when the opponent has at most two prizes remaining,
> our two-prize Active is within the public next-turn Powerful Hand damage
> floor, the current Active KO is nonterminal, and Boss plus the already
> available attack KOs the unique visible attack-ready Alakazam while leaving
> no visible ready successor, allow Boss and target that Alakazam.

This certificate uses only public prize count, HP, hand count, Energy, board
identity, legal options, and current attack damage. It changes the exact
`88457867:144` decision without adding an opponent-policy proxy. Keep the
strictly higher-prize Boss cases and the non-ex 120-damage breakpoint as
separate later hypotheses rather than broadening this first test.

Regression risks:

- Boss consumes the turn's Supporter and may abandon an energy/search plan.
- A hidden draw can still rebuild an attacker; the certificate must claim only
  removal of the visible ready threat.
- The override must remain below a current terminal win and require that the
  Boss KO itself is legal and attack-complete.
- Do not generalize it to every KOable Bench attacker or to other matchups
  without adjacent-matchup evaluation.

## Raw rows for numerical evaluation

The Sol-Ultra evaluator/root should quantify any frequency or candidate effect
from the raw replay paths, not from this prose:

- Primary certificate: `88457867` decision rows `142-144,152` and consequence
  rows `153,155-157`.
- Same Boss hard gate, different route value:
  `88417236:70`, `88171291:39`, `87974582:72`,
  `87892692:48,51`, `88096059:114`.
- Separate non-ex breakpoint:
  `87996118:93,95,96`, `88602602:118,120`.
- Resource controls:
  `88454146:39,63,80,90`, `88163977:19,29,43,51,64`.

Terminal engine log rows for replay coverage (`743/1072` is Alakazam/Powerful
Hand; damage values retain the engine's negative sign):

| Episode | Step | Target | Damage |
|---|---:|---:|---:|
| `88614404` | 84 | `190` | -500 |
| `88602602` | 125 | `169` | -520 |
| `88479736` | 119 | `190` | -420 |
| `88457867` | 157 | `190` | -440 |
| `88454146` | 94 | `190` | -460 |
| `88417236` | 123 | `169` | -420 |
| `88399026` | 140 | `666` | -480 |
| `88385224` | 111 | `190` | -500 |
| `88323824` | 138 | `190` | -380 |
| `88244115` | 130 | `190` | -420 |
| `88242194` | 144 | `190` | -460 |
| `88232035` | 135 | `190` | -360 |
| `88191793` | 152 | `190` | -420 |
| `88171291` | 124 | `169` | -420 |
| `88163977` | 67 | `190` | -340 |
| `88096405` | 103 | `169` | -580 |
| `88096059` | 136 | `666` | -620 |
| `87996118` | 119 | `190` | -500 |
| `87994013` | 118 | `169` | -520 |
| `87974582` | 137 | `190` | -600 |
| `87935410` | 163 | `190` | -400 |
| `87911107` | 129 | `190` | -560 |
| `87892692` | 105 | `190` | -380 |
| `87842092` | 108 | `190` | -460 |

This audit makes no win-rate aggregation, candidate comparison, numerical
promotion judgment, or Kaggle-slot recommendation.
