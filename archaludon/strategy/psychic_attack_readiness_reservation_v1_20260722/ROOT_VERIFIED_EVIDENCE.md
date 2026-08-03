# Root-verified evidence — Psychic attack-readiness reservation v1

This file records direct root checks used to authorize the frozen candidate.
Replay outcomes diagnose public board and resource sequencing only; they are
not action labels or opponent-policy proxies.

## Live checkpoint and structural parent evidence

- Submission: Kaggle `54888159`, exact submitted parent for this candidate.
- At the 35-public checkpoint: 18 wins, 17 losses, score `634.7`.
- Episode CSV SHA-256:
  `F62802463145C05147AAF7808AD73B5BCB19A6958C30669AF42E989C04CAE24A`.
- Correct-seat submitted-child shadow: 2,202 unique callbacks, zero invalid
  actions, duplicate mismatches, parent-call mismatches, emergencies,
  mandatory fallbacks, or missing classifications. Raw SHA-256:
  `DAF2A0167C7C8B4B00AF2A04DF2E3B8BD41672391894888FBCE8356D2603401E`.
- Direct-parent comparison SHA-256:
  `1E6672FDD9895FB42B67D0603F625E0FF93B81570D0F72C1A6A28F945685AC0C`.
  It contains 18 distinct first forks, all exact `ADMISSIBILITY_REJECT`
  repairs; no first fork is unclassified.
- At the later quick checkpoint: 38 public games, 20 wins and 18 losses,
  score about `645.2`. The exact three new games are one loss and two wins and
  are submitted-child/direct-parent identical over 257 callbacks. Quick CSV
  SHA-256:
  `BE3BC8855948303411957B423C195E5F233EF17903548BCF890F13D9C3B8A48D`;
  comparison SHA-256:
  `B66030ED772B4ABAF966613593076B4B00BD4F12FBA8E40FBEED831589F0351A`.

These facts justify preserving the submitted admissibility child as the
implementation parent. They establish structural safety and mechanism
frequency, not causal improvement.

## Directly checked positive states

The root opened each replay state and independently matched its recomputed
correct-seat callback row in `public35_child_raw.json`. Replay `action` is
stored one engine step behind the observation; callback keys below use the
observation's public `step` value.

### 87368866 / seat 0 / S77 — Active Alakazam H0

- Ordinary MAIN, turn 5, `energyAttached=False`.
- Active: Alakazam `743`, serial 13, no Energy.
- Visible hand Energy: Enriching `13/s62`, Telepath `19/s61`, Basic Psychic
  `5/s56`.
- Recorded parent action: option 2, Enriching to Bench Dudunsparce.
- Exact legal alternatives: option 6 Telepath to Active; option 18 Basic
  Psychic to Active.
- The recomputed callback semantic is ATTACH source `13`, selected option 2.
- On the next MAIN callback, the Active remains unenergized and the ordinary
  attachment budget has been consumed; the parent uses Run Away rather than
  attacking.

### 87355030 / seat 1 / S73 — Active Kadabra H0

- Ordinary MAIN, turn 8, `energyAttached=False`.
- Active: Kadabra `742/s69`, no Energy.
- Visible hand Energy: Enriching `13/s122`, Telepath `19/s118`.
- Recorded parent action: option 6, Enriching to Bench Dunsparce.
- Exact legal alternative: option 13, Telepath to Active Kadabra.
- The next callback leaves Kadabra unenergized and the manual attachment spent;
  the parent uses a Bench ability instead of Super Psy Bolt.

### 87351582 / seat 0 / S34 — Bench Alakazam H1

- Ordinary MAIN, turn 5, `energyAttached=False`.
- Active: Psyduck `858/s21`, no Energy. Bench includes Alakazam `743/s12`, no
  Energy.
- The only visible Psychic Energy is Telepath `19/s60`.
- Recorded parent action: option 5, Telepath to Active Psyduck.
- Exact legal alternative: option 6, the same physical Telepath Energy to Bench
  Alakazam.
- Later recomputed callbacks show retreat at S38, Alakazam promotion at S40,
  and END at S41 with the attachment already spent and no Energy/attack option.

### 87356191 / seat 0 / S28 — Bench Kadabra H1

- Ordinary MAIN, turn 3, `energyAttached=False`.
- Active: Genesect `142/s20`, no Energy. Bench includes Kadabra `742/s8`, no
  Energy.
- The only visible Psychic Energy is Telepath `19/s58`.
- Recorded parent action: option 2, Telepath to Active Genesect.
- Exact legal alternative: option 4, the same physical Telepath Energy to Bench
  Kadabra.
- Later recomputed callbacks show retreat at S37, Kadabra promotion at S39,
  and END at S40 with the attachment spent and no attack.

### Existing correct behavior retained

In `87365156`, seat 0, S71 the parent attaches Basic Psychic `5` to Kadabra;
at S72 it uses Super Psy Bolt `1071`. The candidate must reproduce both exact
actions while tracing a parent-identical reservation transaction.

## Fail-closed boundaries checked

- `87352178`, seat 0, S58: Active Alakazam has Hammer, Stadium, and END options,
  but no visible Basic/Telepath Psychic and no attack. A candidate must not
  synthesize readiness.
- `87351582`, seat 0, S41: Active Alakazam is unenergized after the attachment
  has been spent; only Items and END are legal.
- `87356191`, seat 0, S40: Active Kadabra is unenergized after the attachment
  has been spent; only Items, a Dudunsparce ability, and END are legal.
- `87368297/S36` and the checked `87367596` states have public protection that
  makes Powerful Hand's counter placement zero. They are negative fixtures,
  not permission to attack.

Therefore the candidate may intervene only at the earlier attachment budget,
where a physical visible Energy, one unique attacker, one exact target, and a
positive attack after resolution are all proven. It must not manufacture an
Energy, force Hilda/Dawn, infer a search result, or attack merely because the
parent later reaches END.

## Root decision

The repeated mechanism appears in at least four independently observed games
and spans both current-H0 and reserved-H1 cases. It is more coherent than the
secondary Boss-without-conversion, protection/clock, or terminal-survival
hypotheses and can be implemented as one public-state resource transaction.
Root therefore authorizes exactly the frozen
`psychic_attack_readiness_reservation_v1` candidate. Local win rate is
nonblocking under the user's practical-probe instruction; every structural,
transaction, positive, negative, and retention gate remains mandatory.
