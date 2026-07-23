# Mandatory-draw reserve / Kadabra resource-first: root implementation gate

- Recorded: 2026-07-19 06:47 JST
- Owner: root
- Parent: `alakazam_parent_end_strict_prize_lead_retreat_ko_bridge_v3`
- Kaggle authorization: none

## Frozen identity

Candidate source/runtime/test/deck SHA-256:

- `main.py`: `3EFFE5520F6B1C2F8283B25ED4A76564BCB3305E213FFA87612BA4A7A2CF606B`;
- `runtime/main.py`: `1E41868984188606AA879305CD5F66F59C8FE5235E94BC1B7CFB3B2013A1D04E`;
- `test_mandatory_draw_reserve_resource_first_v1.py`:
  `FC7217614011CC0DF425C0C5E028A8FF734249258544EE5C2128C1EE5F914953`;
- `deck.csv`: `7B413177E5077777F2178143839C0155B03B92BBC8B3A6607621A7D43F351141`.

The deck contains exactly 60 nonempty rows and is byte-identical to the
parent.  Root independently rehashed the unchanged parent source/runtime/deck
as `49E954F53E043CD79D928DFB2340CCB5D85A17F33CCB824C871CCE153C0C9C95`,
`9CA7A415451B84343165EF8A5CDC0D67BBF1B4969A13C984C09B142B4898CD9A`,
and `7B413177E5077777F2178143839C0155B03B92BBC8B3A6607621A7D43F351141`.

The governing decision is
`decisions/20260719_0602_xerosic_single_swap_reject_and_mandatory_draw_reserve_select.md`,
SHA-256 `15A3DE932A24811442CC009ABE2CE994AD91CBF3DECAB2DB31BD0A43BC531C57`.
Its corrected live anchor is own prizes 2, opponent prizes 3 at step 135.

## Root verification

Root compiled all three Python files in memory under the mandated
`.venv-rl` Python and reran the focused suite with bytecode disabled.  All
16 tests passed in 1.292 seconds.  The suite binds the raw step-135 2/3 Prize
state and checks the full Hammer play, exact Special Energy target, Basic
Psychic-to-the-same-old-Kadabra transaction, deterministic repeated calls,
deck-one Enriching suppression, fixed-draw and variable-search boundaries,
Dudunsparce physical-component accounting, stale-latch clearing, malformed
callbacks, option order, Night Stretcher and Xerosic noninterference, runtime
parity, and the legal deck.

Root then ran fresh checked-engine historical-Silver smoke in both seats with
engine seeding and a 1000-step limit:

- candidate P0, seed `2026071941`: exit 0, 147 steps, result 1, zero action
  errors, no max-step hit; summary/trace SHA-256
  `29B454B0DAE04ACB11A9985778023823314A38C8DAB0C0392D90B39A8F69C9CD` /
  `B55E3383CE70238C57D05BCC33EDB1AFB6B29BB119D7E5A06836890FE1E2424C`;
- candidate P1, seed `2026071942`: exit 0, 145 steps, result 0, zero action
  errors, no max-step hit; summary/trace SHA-256
  `2D86A597D5745A07EA3A081F3168992E4BF58F484D22BBF4E54AEEC8D0A8BD33` /
  `44B0472D22A85D06EE40F4A7C12F9E9D209DCC9B234AFF62D755EBA204A3D162`.

The smoke games are validity checks, not strength evidence.  Both candidate
games lost to historical Silver, so their outcomes do not justify promotion.

## Deliberate conservative boundary

The terminal-win reserve exemption is empty in v1.  Engine inspection did not
support a complete modifier-aware public certificate, so the implementation
does not reuse the parent's optimistic win projection.  Terminal-looking,
near-KO, and hidden-enabler fixtures are all non-exempt.  This is safer than a
false positive but may suppress a draw that would have produced a current-turn
win.  The fixed paired panel therefore requires zero regressions and explicit
inspection that no parent immediate KO was removed.

## Gate

Implementation/engine gate: **PASS for fixed Phase-0 execution only**.

This is not an adoption, packaging, or Kaggle decision.  The immutable paired
panel must independently establish both mechanism exposure and absolute
strength before the candidate can advance.
