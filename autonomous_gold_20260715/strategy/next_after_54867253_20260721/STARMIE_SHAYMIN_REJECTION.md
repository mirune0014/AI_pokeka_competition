# Starmie-Shaymin guard rejection

- Frozen by root: 2026-07-21 22:34 JST
- Candidate: `alakazam_starmie_shaymin_bench_protection_guard_v1`
- Transient source SHA-256: `653E9C634D81B3F72D9E00CA7B39838B1CFD9840EE704BE7420F68003019E0FD`
- Decision: `REJECT; NEVER PACKAGE OR SUBMIT THIS TRANSIENT SOURCE`

The original strategy and live-parent amendment selected a narrow
Starmie-Shaymin bench-protection overlay. Root callback-complete shadow exposed
a controlling contradiction before packaging.

At mandatory target `87203877/S53`, the live parent action is EVOLVE
(`OptionType.EVOLVE=9`), while the transient candidate chooses PLAY Shaymin
(`OptionType.PLAY=7`). The contract simultaneously requires the S53 Shaymin
deployment and forbids suppressing evolutions, attachments, attacks, retreat,
and continuity.

Preserving the inherited evolution resolves the contradiction safely but loses
the target mechanism: evolving the damaged 20-HP Dunsparce creates a 90-HP
Dudunsparce, so the exact remaining-HP-at-most-50 threat predicate becomes
false. The subsequent ATTACH remains protected, and there is no later eligible
Basic PLAY or END while the original threat certificate remains true. Carrying
the stale pre-evolution threat forward would widen the rule and is forbidden.

Historical shadow also proved the transient implementation was over-broad:

- `86969410/S22` replaced an inherited Genesect `142` Dawn choice;
- `86894977/S27` and `86902682/S20` replaced inherited Dunsparce `305` Dawn
  choices, although Dawn ownership was only Shaymin over inherited Abra `741`;
- `86997886/S44` replaced an inherited ATTACH;
- current recorded win `87204965/S38` replaced Abra PLAY with Shaymin and
  required separate retention proof.

The only coherent safe amendment is: Dawn may replace only inherited Abra;
MAIN may replace only an optional fragile Basic PLAY consuming the last slot
or END; all ATTACH/EVOLVE/ABILITY/ATTACK/RETREAT and certified enablers remain
unconditional negatives. That safe amendment leaves only one verified positive
(`87206063/S17`) and no repeated MAIN deployment mechanism. It therefore does
not justify an exploratory submission.

Keep current live submission `54867253`, source SHA
`7838FBFF3CBA3AE5D9142E45B1334B192A5E758CFFA5598AF2A626E5C7D636E3`.
Its episode-`87213204` retreat-to-Powerful-Hand board-out win remains causal
and must not be removed. Reconsider Starmie-Shaymin only after a second natural
state where higher-priority actions complete, the at-most-50-HP threat persists,
Shaymin is legal, the inherited action is eligible Basic PLAY or END, and an
exact-engine branch preserves the full win plan.
