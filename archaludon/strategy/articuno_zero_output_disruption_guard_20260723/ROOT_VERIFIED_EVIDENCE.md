# Root-verified evidence: public Articuno zero-output defect

## Immutable inputs

- Live submission: Kaggle `54906455`.
- Public loss: episode `87485519`, target seat `0`, replay SHA-256 `E4296E1DA5F2192C0CF67CCD0859B15766CDCEBE3B7C618164F254A6901BC02C`.
- Episode CSV SHA-256: `F694BB09AB81BDB5CAA54FB50430041C07B063A9DA52B26DD80F8A96A6E83BFA`.
- Candidate v4 policy SHA-256: `B89DCB6363CBD6ADF094115CF0CF5B93D6B9975A2505E1B976F387AAE8A198CD`.
- Formal-parent policy SHA-256: `6AEF53400B9413037FB79DDCB9BE752A632FF4E0803B1D00EE84F188C44EDB6C`.
- Prior repeated-defect report SHA-256: `37481B016563D005E9C2A544F5318BB40FA169A12F7C5DBDAD49330FCD3DA742`.

## Causal isolation

The correct-seat candidate-parent shadow is bound by immutable spec SHA-256 `BB81D16D89243ACBE7F2516DD96638B6D0EF0F7529F05FC9EA22B5ECC1E8D358`.

Root independently recomputed from raw files:

- candidate raw SHA-256 `D46274D7F2BC12A0DDD162207CAA92A6FC57914CC5BE6306255AE456E3D1EA48`;
- parent raw SHA-256 `F7EAB650C355B2BDA68A21C96830AEC140771BA6A07A8FFFB5191CDF8E97A238`;
- comparison SHA-256 `371E23C05B0F42E7C62EB584AD4FA74246DEB379FE96F01D1B657FB80CAECB1E`;
- one replay, `83` candidate callbacks, `83` parent callbacks, `83` unique keys per side, and exact ordered schedule equality;
- zero action differences, v4 starts, v4 aborts, invalid actions, duplicate mismatches, parent-call mismatches, emergencies, mandatory fallbacks, or unclassified differences.

Episode `87485519` is therefore an inherited-parent failure. V4 did not participate.

## Exact public states

Root read the frozen replay directly.

- At step `75`, opposing Articuno `414` was public on the Bench.
- At step `87`, Active Alakazam `743/s13` chose option `14`, Powerful Hand `1072`, into Active Basic Team Rocket's Mewtwo ex `431/s65`. Retreat option `15` was legal. Enhanced Hammer `1081` was public in hand at index `0`, and its play option was legal at raw option `0`.
- The protected Mewtwo had Basic Energy `1` and Team Rocket's Energy `15`; every other visible opposing attached Energy was Basic. Energy `15` was the unique visible Special Energy target.
- The zero-counter resolution and subsequent Alakazam loss are reflected by the forced-promotion state at step `93`.
- At step `105`, the next Active Alakazam chose option `15`, Powerful Hand `1072`, in the same protected state; Enhanced Hammer was again legal at raw option `0`.
- The second zero-output exchange and Alakazam loss are reflected by step `111`.

## Frozen card metadata

The formal parent's frozen card table reports:

- Articuno `414`: exact name `Team Rocket's Articuno`, Basic, skill text `Prevent all effects of attacks used by your opponent?s Pok?mon done to your Basic Team Rocket?s Pok?mon. (Existing effects are not removed. Damage is not an effect.)`.
- Mewtwo ex `431`: exact name `Team Rocket's Mewtwo ex`, Basic, attack `608` Erasure Ball, cost `{P}{P}{C}`, base damage `160`.
- Enhanced Hammer `1081`: exact text `Discard a Special Energy from 1 of your opponent?s Pok?mon.`.
- Alakazam `743`: Stage 2, attack `1072` Powerful Hand, cost `{P}`, damage field `0`, exact text `Place 2 damage counters on your opponent?s Active Pok?mon for each card in your hand.`.
- Team Rocket's Energy `15` supplies the two Psychic/Dark units represented by the engine; after its removal the visible Mewtwo retains only one Basic unit and Erasure Ball is unpaid.

## Positive and negative controls

The prior report for episode `87087898` records repeated zero-counter Powerful Hands into protected Basic Team Rocket Pok?mon. The same replay records ordinary successful Powerful Hand damage and KOs into evolved Team Rocket Porygon2 and Honchkrow while Articuno remained relevant. Those evolved targets are mandatory negative controls for any guard.

No opponent identity, archetype label, private hand, hidden deck order, or replay-derived opponent policy is required.
