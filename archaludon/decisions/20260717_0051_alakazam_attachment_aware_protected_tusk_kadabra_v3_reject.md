# Alakazam attachment-aware protected-Tusk Kadabra v3 — Phase 0 reject

- Decision time: `2026-07-17T00:51:00+09:00`
- Decision: **REJECT at Phase 0**
- Phase 1 run: **no**
- Package or Kaggle write: **no**
- Mechanism disposition: terminate the protected-Tusk Kadabra overlay; do not
  add a fourth exception patch.

## Frozen evidence

| Artifact | SHA-256 |
| --- | --- |
| Evaluation specification | `1F07D0B3D868EBA2E433E50608030BB6FD0F4D892158FAB0CA0187B0F6DDF7C5` |
| Candidate source | `7F2BAC096A9BAE6E71471AA8C9FD565BAA3F7D259B008C4B5E98BC72E6DA77E0` |
| Candidate runtime | `95600EA9411EA98A769AC54F469F4AD19C895D9AE8299CEE1F0043B7F8E3C80E` |
| Legal 60-card deck | `7B413177E5077777F2178143839C0155B03B92BBC8B3A6607621A7D43F351141` |
| Phase 0 execution manifest | `96FC21656C730D2C1A262879274764C5A0A0FB1AB7C07C69EE93C3A5A2ACB29B` |
| Phase 0 qualitative audit | `E8FF1698B87957B7DE9A2A6C79A73EA72DCA593E67ED2E6D9DFAA2A9BF5CBEE6` |

## Root numerical recomputation

- 16 native rows on eight unique paired `(seat, seed)` keys.
- Parent/candidate schedule equality: true.
- Parent wins: `0/8`; candidate wins: `2/8`.
- Candidate result regressions: 0.
- Candidate terminal-prize regressions: 0.
- Action errors and max-step hits: 0.
- All 35 frozen-file hashes matched after execution.

| Key | Parent | Candidate |
| --- | --- | --- |
| `p0/1501` | loss, 4 prizes, turn 29 | loss, 4 prizes, turn 39 |
| `p0/1509` | loss, 1 prize | loss, 1 prize; exact trace identity |
| `p0/1541` | loss, 4 prizes | loss, 4 prizes |
| `p0/1579` | loss, 1 prize | loss, 1 prize |
| `p1/1501` | loss, 5 prizes | win, 0 prizes |
| `p1/1536` | loss, 1 prize | win, 0 prizes |
| `p1/1543` | loss, 5 prizes | loss, 5 prizes; exact trace identity |
| `p1/1552` | loss, 1 prize | loss, 1 prize |

The aggregate-looking improvement is real but insufficient because the frozen
action-level safety contract fails.

## Decisive trace failure

At `p0/2026071501` step 38, turn 5, the opponent has protected Great Tusk at
80 HP and the policy has an energized Active Kadabra. The parent evolves a
non-conflicting Bench Abra to Kadabra and continues its draw/search chain. It
finds the visible Hammer/Alakazam route, removes protection, evolves the Active,
and records a `-140` turn-5 Powerful Hand knockout.

The candidate instead attacks immediately for `-60` and does not knock out the
target until turn 7. Terminal prizes eventually tie, but the candidate loses a
parent same-turn knockout. This is an explicit hard reject.

The positive certificate was one-sided: absence of a currently exposed
Hammer/Active-Alakazam route was treated as permission to attack. It did not
prove that the exact parent's still-legal setup prefix could not construct the
route during the same turn.

## Independent contract failures

- `p1/2026071501`: candidate RETREAT preempts the parent's ordinary Hilda
  PLAY/search, even though the parent can complete Hilda and the same-turn
  retreat/Bolt sequence.
- `p1/2026071536`: candidate RETREAT preempts the parent's Battle Cage PLAY.

Both conversions win, but only certified necessary Hammer/Boss actions were
authorized to move ahead of ordinary parent PLAY/ABILITY/search work.

## Preserved positive evidence

- `p0/1579` correctly preserves Active Psychic attachment, full Hammer
  removal, and the same-turn Great Tusk knockout.
- `p0/1541` preserves the certified unprotected Boss knockout.
- `p1/1552` preserves the unprotected Crustle knockout and two full-Hammer
  knockouts, then executes the later three-Bolt lane.
- The Kadabra direct-damage bypass is mechanically valid, but this overlay
  cannot prove when it is safe to stop the parent's within-turn setup.

Because the frozen Phase 0 contract explicitly says to terminate the mechanism
after any safety failure, v3 does not become a baseline and Phase 1 is not run.

