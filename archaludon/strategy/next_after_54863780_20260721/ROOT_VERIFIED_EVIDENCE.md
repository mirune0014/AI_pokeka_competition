# Root-verified successor evidence after Kaggle 54863780

Verified by root on 2026-07-21 JST. This is replay diagnosis and hypothesis
selection evidence. It does not authorize a Kaggle write and does not use
replay actions as imitation labels.

## Immutable identity

- Current exploratory live source: `54863780`,
  `alakazam_certified_terminal_prize_psychic_attach_powerful_hand_transaction_v5`,
  SHA-256
  `C7E6E7DBCBB6357F0B559CEB6D9CC64DAACBDC660AFBDB890F91C5D1F462DA43`.
- Immediate comparison source:
  `alakazam_public_h0_h1_turn_objective_guard_v1`, SHA-256
  `23B89E347565F1782F44494E8ACD89FAB0FEED20C484B2DA14DE1195B908CBE9`.
- Formal rollback source:
  `alakazam_guarded_teleportation_attack_continuity_v1`, SHA-256
  `4A95DCE0BB095A05F58085DFC450528C5939527E30B9D40E43A76B0CFCE2AE16`.
- Root episode snapshot:
  `live/54863780/refresh_20260721_1000_root/refresh_20260721_1000_root_episodes.csv`,
  SHA-256
  `D646D98B5639A823C929F6092943EF844DAC99D652D3C12A2324839D94E3BCCF`.
  It has 29 unique completed rows: one validation and 28 public games. The
  public record is exactly 14-14.

The two root shadows cover the same 29 episodes and 1,725 correct-seat
callbacks. V5 differs from H0/H1 on 0/1,725 actions; V5 differs from the formal
rollback on 0/1,725 actions. Both shadows have zero invalid actions and zero
duplicate mismatches:

- `root_v5_vs_h0h1_shadow.json`, SHA-256
  `4503412B9DD81153B7E9880300B7CB28DA7B0583DF48BD6F05EFECD0A3D65713`;
- `root_v5_vs_formal_shadow.json`, SHA-256
  `E4B504138D17627FF89E979FEA675D2810022AD9E3940DEDB83A8287ED15A030`.

Therefore no realized loss or score movement in this snapshot is caused by
the v5 or H0/H1 overlays relative to the formal rollback. The new mechanisms
did not fire. The 14-14 outcome is immature and diagnoses inherited policy
gaps, not a candidate regression.

## Recurrent opening formation gap

Root replayed the exact H0/H1 source sequentially over all 29 games and
scanned every Poké Pad selection. The deterministic scan is
`live/54863780/refresh_20260721_1000_root/scan_early_poke_pad_abra_gaps.py`,
SHA-256
`C8F91AC6DA8596B942333BCA03F5DC848EEA6F77BC590250FC2D35F2CCDFCA33`.
Its output is
`root_early_poke_pad_abra_gap_scan.json`, SHA-256
`537BAAC038F9678031AF21BEEF65274E20DCBE37D092B575F079E9EEA44CAEB1`.

Across 77 Poké Pad selection screens, the broad predicate “turn at most three,
at most one Abra-line body in play, no Abra in hand, open Bench, Abra offered,
but parent selects another card” occurs nine times: five loss rows and four
win rows. That broad predicate is unsafe because it would preempt productive
evolution searches in wins.

A narrower public threat boundary using only the root-observed opponent Active
IDs `676` and `677` has exactly three first-activation episodes, all losses and
zero wins in this snapshot:

| Episode / first step | Own field | Opponent Active | Parent Poké Pad choice | Legal Abra |
| --- | --- | --- | --- | --- |
| `87175144/S6` | lone Active Abra | `676`, 110 HP | Kadabra | options `0/3` |
| `87168712/S7` | Active Abra; Bench Dunsparce/Psyduck | `676`, 110 HP | Dudunsparce | option `5` |
| `87166423/S7` | Active Dunsparce; Bench Fezandipiti ex; no Abra line | `677`, 80 HP | Dudunsparce | options `1/3/9/11` |

The first game calls a second Poké Pad at S8 and selects Alakazam while still
leaving the sole Abra exposed. A correct transaction must bind the searched
Abra serial and immediately play that exact card before delegating again; a
selection-only score tweak does not close the failure.

This is the most recurrent opening defect in the Mega-Lucario bucket. It also
matches earlier independent live evidence where Poké Pad preferred a draw-
engine/evolution card while no robust Abra line existed. The rule must still
fail closed outside the exact early public-threat boundary because the broad
scan contains four retained wins.

## Ready-Alakazam attack-conversion gap

Root sequentially replayed the exact H0/H1 source at six audited states. The
verifier is
`live/54863780/refresh_20260721_1000_root/verify_ready_alakazam_pivot_states.py`,
SHA-256
`4945949F9F227352173E7AC26DE9A77989CB1E70633F03318474BC35BD512224`;
the output is
`root_ready_alakazam_pivot_state_verification.json`, SHA-256
`6DEE7D8AFA2E2BA8C41360BBC3AE052965520B81A2F10AD72F2F91A7257EA0C6`.

Two independent losses expose the same exact missing slice:

| Episode / step | Prize clock | Active | Ready destination | Target | Parent | Certified alternative |
| --- | --- | --- | --- | --- | --- | --- |
| `87175722/S64` | `6-6` | paid Kadabra | unique paid Alakazam `s72` | one-Prize `380`, 100 HP, public-clear | Super Psy Bolt 30 | retreat option `2`, then Powerful Hand 120 KO |
| `87170471/S73` | `5-6` | paid Kadabra | unique paid Alakazam `s71` | one-Prize Kadabra, 50 HP, public-clear | Super Psy Bolt 30 | retreat option `5`, then Powerful Hand 300 KO |

Both already satisfy the inherited strict post-KO Prize-lead condition. They
do not activate the existing stranded-retreat transaction only because that
transaction rejects every state with a legal attack and is called only when
the finalized parent action is END. This is a clean policy boundary: replace
only a finalized Super Psy Bolt with the already checked retreat -> exact
payment -> frozen Alakazam promotion -> Powerful Hand transaction when that
transaction takes a certified immediate KO.

The exact negative controls are:

- `87176878/S94`: paid Active Kadabra and a ready Alakazam exist, but the
  target is not publicly clear because it retains Mist Energy; parent Super
  Psy Bolt must remain unchanged.
- `87166999/S142`: Active Fezandipiti has a legal retreat and a ready Alakazam,
  but 200 Powerful Hand is below the 320-HP target and the parent finalized
  END; remain parent-identical.

Two other losses have Active Dudunsparce and a ready Alakazam
(`87170471/S130`, `87169861/S95`), but they require a distinct Run Away Draw
mobility transaction, not retreat. That sibling mechanism already has prior
art and must not be stacked into the Kadabra candidate without a separate
selection and full evaluation.

## Three-Prize H0 lethal cliff

The exact three-Prize current-snapshot scan is
`root_three_prize_h0_crossings.json`, SHA-256
`2C8786A2CAA8EDFC0849A21BFE70E7E08F01FA0CD2A570E4D5C5FF670E8FACCD`.
It finds three crossings. Only `87163630/S97` is a loss: hand 17 certifies 340
Powerful Hand into a 340-HP Mega Lucario ex, but Poffin begins a same-turn
sequence that attacks from hand 14 for 280 and misses the KO. The other two
crossings are wins where Poffin -> Enriching or Dawn preserves the KO and
performs useful setup. A blanket immediate-attack rule is therefore rejected.

The broad immediate three-Prize candidate and its refined pre-KO setup
transaction were previously rejected and must not be resubmitted. A future
retry would need a materially new public guarantee for KO-preserving setup;
it is not the safest immediate successor.

## Root ranking for strategy judgment

1. **Certified parent-Super-Psy-Bolt retreat-to-ready-Alakazam KO conversion.**
   It has two independent exact loss anchors, immediate public KO value, two
   strong negatives, and can reuse the already tested stranded-retreat state
   machine while narrowing start ownership to a finalized attack. Its main
   risk is spending the Kadabra's attached Energy and exposing Alakazam; keep
   all inherited public-clear, exact-payment, unique-destination, Prize-lead,
   deck-clock, fingerprint, duplicate, and rollback checks.
2. **Early threat-bound Poké Pad Abra search-to-play transaction.** It has
   three loss episodes and no win exposure under the narrow observed threat
   boundary, but it is a larger multi-callback formation intervention and can
   delay evolution or reduce Powerful Hand. It should be the next sibling if
   the retreat slice is rejected or after one practical probe.
3. **Three-Prize H0 setup lock.** Do not retry now because prior art was
   rejected and two of three current crossings used productive setup.

Select exactly one isolated successor. Do not stack mechanisms. The user
prefers a practical live probe after major-breakage checks, but an illegal,
invalid, nondeterministic, unpackaged, duplicate, or known-broken source
remains forbidden.

## 10:35 JST root refresh addendum

The checked episode refresh then reached 38 unique completed rows: one
validation plus 37 public games. The exact CSV is
`live/54863780/refresh_20260721_1035/refresh_20260721_1035_episodes.csv`,
SHA-256
`29F8F4378BE61DF37243C69A0FBD3AB13094AD39817668907172508C1CC94360`.
The exact nine-ID set difference over the 10:00 snapshot is 6-3, making the
cumulative public record 20-17. Authenticated Kaggle CLI reports `COMPLETE`
at `641.2`. No submission has UTC date 2026-07-21, so the reset quota is 0/5
used and 5/5 available.

Root shadowed all nine new replays against both comparison sources. V5 versus
H0/H1 and V5 versus formal are both action-identical on every callback, with
zero invalid actions and zero duplicate mismatches. The output is
`live/54863780/refresh_20260721_1035/root_new9_v5_vs_parents_shadow.json`,
SHA-256
`ABCA715C32330C73B82150963A77C4EDE6308C3DACC5F15481C57C8C09BCB6A5`.
The script SHA-256 is
`EC92A05B99281C1C6186AF817CFC5C217434441E88A05CC56AC525B1D29CF5AF`.
Thus the nine-game improvement in record still provides no candidate-specific
causal evidence; all observed play remains inherited.
