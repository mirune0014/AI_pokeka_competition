# Controlling automation handoff update — 2026-07-22 07:38 JST

This file supersedes all earlier current-live, quota, integrated-candidate,
and next-write statements in `AUTOMATION_HANDOFF.md`.

Current live submission is Kaggle `54888159`, exploratory candidate
`alakazam_integrated_override_admissibility_gate_v1`. The exact submitted
policy SHA-256 is
`974C4EACFA730D4CC0FAB7A84F82A0E5F004CC3443B39AF517673B630AB98CE1`;
the clean archive SHA-256 is
`A9C9B8162332B6F3CA00FC62C0991317EF6920360B18F35EF94F3902DBCD593F`.
Never resubmit this exact source or archive.

Authenticated Kaggle API at 07:37 JST reported `COMPLETE` at `600.0`. The
episode service contained exactly one completed validation self-play,
`87350866`, and zero public ladder games. The validation result is target loss
and opponent win; it establishes deployment, not live strength. Post-write UTC
quota is `3/5` used and `2/5` remaining. Refresh before treating any of these
facts as current. Submission record is `live/54888159/SUBMISSION_RECORD.md`.

The direct diagnostic parent is
`alakazam_integrated_domain_turn_planner_v1`; its policy SHA-256 is
`A67FFC697DE6552C617244CCDD1D6077685B925792DEA39CA2FA16DE8572F477`.
The repair changes only `planner_final_policy.py`. It rejects uncertified
integrated chip/setup-stop overrides and sole-board Run Away, returning the
exact cumulative-parent action, while retaining certified Powerful Hand and
safe Run Away cases. The immediate targets are the live parent failures where
speculative Abra/Kadabra attacks displaced setup/draw and Run Away removed the
last Pokemon. This is an exploratory repair, not formal adoption.

Prewrite safety is complete: compile/import, legal 60-card deck with one ACE,
loader-only/last, cache-free package, deterministic duplicate handling, fixed
both-seat smoke, and callback-complete live/historical shadows passed with
zero invalid actions or untraceable overrides. Package manifest SHA is
`068D8F7E379F3E0363726CA7110B1A60EC9CA9421052680A3D67FCC0EA7D1589`;
verification JSON SHA is
`99A5D053A79BD7D9293A4ABBA85B09B5EC5370ED279E440A9B712D9C11527EE8`.

On the next wake, refresh authenticated submissions, UTC quota, and exact
episode IDs first. At the first public game, then near 5/10/20/40 public
games, download every genuinely new replay and shadow the submitted child
against the direct integrated parent in the correct seat. Inspect every first
difference and track `ADMISSIBILITY_REJECT`, retained certified overrides,
invalid/duplicate/emergency states, and mechanism-attributable outcomes.
Score movement without a policy difference is not causal evidence. Do not
stack a new policy onto the exploratory child before this evidence. Root alone
may package or write to Kaggle; two daily slots remain, but never spend one on
a duplicate, invalid, illegal, unpackaged, or known-broken artifact.
