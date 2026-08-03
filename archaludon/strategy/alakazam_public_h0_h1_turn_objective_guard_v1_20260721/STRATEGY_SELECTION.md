# Strategy selection: public H0/H1 turn-objective guard v1

Recorded: 2026-07-21 JST

## Exact parent

- Source: `candidates/alakazam_guarded_teleportation_attack_continuity_v1/main.py`
- Source SHA-256: `4A95DCE0BB095A05F58085DFC450528C5939527E30B9D40E43A76B0CFCE2AE16`
- Runtime SHA-256: `9CA7A415451B84343165EF8A5CDC0D67BBF1B4969A13C984C09B142B4898CD9A`
- Deck SHA-256: `7B413177E5077777F2178143839C0155B03B92BBC8B3A6607621A7D43F351141`

The deck remains byte-identical. The live exploratory overlay in submission
`54857291` is evidence only and is not the implementation parent.

## Unified hypothesis

A deterministic public-state turn-objective guard improves practical Alakazam
strength by applying one lexicographic order before inherited atomic scores:

1. immediate win;
2. avoid a publicly forced loss;
3. preserve a certified current-turn knockout (`H0`);
4. take current Prizes;
5. preserve or form one independently executable next attacker (`H1`);
6. preserve the public deck clock;
7. avoid unnecessary multi-Prize Bench liability;
8. retain the stable parent decision.

This is a testable policy hypothesis, not proof that policy dominates deck or
matchup ceiling.

## Required public certificates

- Unique legal Powerful Hand and unchanged opponent Active.
- Exact remaining HP, Prize value, post-action hand floor, and attack-effect
  protection status.
- H1 reservation by a distinct Pokemon serial, without reusing evolution,
  Energy, retreat, Bench-slot, or recovery resources.
- No hidden-state, opponent-policy, archetype-template, or probabilistic
  assumption.
- Unknown or incomplete metadata delegates to the exact parent.

## Positive anchors

- `87111553/S85`: 14 cards provide 280 against a 270-HP two-Prize Active;
  optional Dunsparce PLAY loses lethal. Select Powerful Hand.
- `87125177/S126`: deck zero, legal Sacred Ash and a nonterminal attack;
  visible Pokemon recovery must precede the attack to avoid the next mandatory
  draw loss.
- `87109941/S111`: deck two, Active Lucky Helmet attachment exposes an exact
  two-card trigger. Change only if a valid public rerank is certifiable without
  assuming the opponent's future policy.

## Retention and regression anchors

- `87128371/S78-S80`: Telepath-to-Abra retains Powerful Hand lethal and forms
  the only paid future line. The guard must allow it.
- `87118684/S114-S125`: a currently unenergized Bench Alakazam later receives
  Telepath and the Active takes lethal. Do not require an already-paid H1 as a
  universal prerequisite for attacking or continuing setup.
- `87121363`, `87123001`, and `87125703`: no exact paid H1 at the relevant
  state; uncertain counterfactuals delegate to the parent.
- Superior Boss routes, final-Prize wins, effect-protected targets, guaranteed
  draw that preserves H0, and certified same-turn recycle retain precedence.

## Rapid live-probe gate

The user authorized submission after large-breakage checks rather than a full
strength evaluation. Before packaging, require:

- Python 3.11 compile/import and final/only callable entrypoint;
- legal deterministic 60-card deck with one ACE SPEC;
- exact positive and negative focused fixtures;
- deterministic current-42 shadow with every difference classified;
- no invalid or out-of-range actions;
- one checked full-engine completion per semantic seat;
- abort/fallback delegates cleanly to the parent;
- package-local both-seat smoke, frozen hashes, and zero caches.

The formal parent remains the rollback. This candidate is an exploratory live
probe and is not formal adoption.
