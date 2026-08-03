# Root implementation verification

- Verified at: 2026-07-21 11:19 JST
- Candidate: `alakazam_finalized_super_psy_bolt_retreat_ready_alakazam_ko_bridge_v1`
- Direct parent: `alakazam_public_h0_h1_turn_objective_guard_v1`
- Frozen strategy SHA-256: `23F3483ED52D938E722586F04360E799D3463B818C76A81A0EA1D3646F71F538`

## Frozen artifacts

- Candidate `main.py`: `7838FBFF3CBA3AE5D9142E45B1334B192A5E758CFFA5598AF2A626E5C7D636E3`
- Parent `main.py`: `23B89E347565F1782F44494E8ACD89FAB0FEED20C484B2DA14DE1195B908CBE9`
- Runtime `runtime/main.py`: `9CA7A415451B84343165EF8A5CDC0D67BBF1B4969A13C984C09B142B4898CD9A`
- Deck: `7B413177E5077777F2178143839C0155B03B92BBC8B3A6607621A7D43F351141`
- Exact parent/candidate diff: `4C50DAA8436E33870E1D9088C274EC75D30E878F000D7395E507C3A95B291E8D`
- Implementation receipt: `9EC7F3B859392B1693378A392B6331C96641E0B944B5A926CD9DA16C1CE61D57`
- Verification results: `2F0030087C7B6E76750D1596F3C4F78145411F61EDB27A171E61CD376D028823`

## Root-independent functional gate

Root reran the checked-engine and focused suites from the frozen source:

- Eight exact-engine routes passed: four natural start states, each in both semantic seats.
- Every route completed RETREAT, exact Energy payment, promotion of the frozen Alakazam, Powerful Hand, exact public KO damage, resolution, and delegation of Prize selection.
- Fail-closed suite: 8/8 passed, covering stale and malformed callbacks, uniqueness, protection, strict-Prize-lead, deck-clock, payment, and rollback boundaries.
- Exact replay identity boundaries passed.
- Inherited END-retreat and productive non-END boundaries passed unchanged.
- Compile/import, final callable loader ordering, deterministic duplicate handling, legal 60-card deck, and exactly one ACE SPEC passed.
- Historical-Silver smoke passed in both seats with zero action errors and zero max-step hits.
- Candidate and implementation trees contain zero `.pyc`, `.pyo`, and `__pycache__` files.

## Root-independent callback-complete shadow

Root reran `run_callback_complete_shadows.py` from the frozen files (exit 0, PASS):

- Current 38 rows: 2,340 callbacks; candidate-parent 4 differences, all 4 classified; candidate-formal 4 differences, all 4 classified; zero invalid actions; zero duplicate mismatches.
- Historical 186 rows: 11,866 callbacks; candidate-parent 5 differences, all 5 classified; candidate-formal 14 differences, exactly the 5 new starts plus 9 inherited H0/H1 differences; zero invalid actions; zero duplicate mismatches.
- Current shadow SHA-256: `D0C44AB3754D32D225ABF3DEE52215B8A9B4C75AFE259A64ACE78204584ECFC8`
- Historical shadow SHA-256: `BC1DCA3A1ACEE89CD1EA70827B34F061BC98C7794F599513847B070B1691AF82`

The four current starts span both seats and are exactly:

- `87170471/S73`, seat 1, loss
- `87173427/S142`, seat 0, win
- `87175722/S64`, seat 1, loss
- `87176302/S48`, seat 0, win

The historical-only starts are `87076890/S137`, `87082407/S62`, `86903767/S49`, `86910372/S55`, and `86911980/S70`, spanning both seats.

## Root decision

The candidate has no known execution, legality, loader, determinism, state-latch, package-source, or adjacent-boundary break. Its only action changes are the frozen finalized-Super-Psy-Bolt retreat-to-ready-Alakazam KO bridge. This satisfies the user-requested major-breakage gate and is permitted for one exploratory live probe after a clean package gate and authenticated pre-write refresh. It is not a formal parent or formal adoption.
