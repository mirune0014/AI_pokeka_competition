# Decision: submit Alakazam Psychic readiness parent continuation v3

Timestamp: 2026-07-22 14:55 JST

Decision: `SUBMIT_EXPLORATORY_REPAIR`.

## What is improved

V2 reserved Psychic Energy for a ready Kadabra or Alakazam, but then forced the attack too early. That preempted useful parent actions such as Telepath Abra search, Boss's Orders, Dawn, evolution, Item, Ability, retreat, and other setup.

V3 keeps the Energy reservation and changes only the continuation rule:

1. Preserve the parent's exact Telepath search.
2. Preserve every exact non-END parent MAIN action.
3. Attack over `END` only when the original exact readiness certificate still holds.
4. Preserve the narrowly certified H1 mandatory-promotion route, then apply the same rule.

This directly repairs repeated live defects rather than adding a new unrelated heuristic.

## Evidence bound to the decision

- Direct parent policy: `C289127BF6457AB3A451CE17017457103013224ED6714A78E8819B90E9F22ABD`.
- Candidate policy: `6AEF53400B9413037FB79DDCB9BE752A632FF4E0803B1D00EE84F188C44EDB6C`.
- Verification result: `C0F9E11F45938914A3D55CEA0CDF5413270A79FE25672EB6E1D326DDC678FF4F`.
- Latest-seven comparison: `3AA8BA32CE587E67513FCE752BEDD2C6F68B3A2118FD232086A572B6E1D3E7CA`.
- Archive: `36567B8654C547C4F33AB3840BA04DD196290993D761F62752B616F8D93F5E62`.
- Manifest: `929EC6C0A19A68535A63427B3DE0255411724611FAF46935ED5D4A7E4A80421F`.
- Authenticated live state before write: submission `54893740`, COMPLETE, 21 public games at 11-10, score `607.5447241030487`, UTC quota 1/5 used and 4/5 remaining.

Breakage gates passed: compile/import, loader shape, legal 60-card deck with one ACE SPEC, cache-free package, deterministic duplicates, exact H0/H1 full-engine transactions in both seats, current and historical shadows, latest-seven no-drift shadow, and packaged both-seat smoke. No invalid action or control fault is known.

Submit with a description that states the actual change: `Alakazam parent-continuation v3; preserves Telepath, Dawn, Boss and setup; attacks only over END`.
