# Root verification: integrated public turn-plan transaction v1

Date: 2026-07-31 JST

## Decision

One exploratory Kaggle live probe is permitted.  This is not a formal
promotion over the submitted General parent.  The candidate is deterministic,
legal, packaged, traceable, and has no known destructive behavior.

## Frozen identities

- Direct submitted parent:
  `archaludon_general_visible_counterattack_ready_rotation_v1/main.py`
  - SHA256:
    `AC70708082882C7BA01CFBF81D29F534B95166DFF6BAD11E1EF1FA001A5F79D2`
- Candidate:
  `archaludon_integrated_public_turn_plan_transaction_v1/main.py`
  - SHA256:
    `3E23CC048CF87E148ACA3E7B017B5B3AAA8C422BD1580BF553222CA79BB466A2`
- Deck:
  - SHA256:
    `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`
  - exactly 60 rows and one ACE SPEC, Hero's Cape
- Strategy contract:
  - SHA256:
    `A428082BDFF1F374527ADD982EFDA8387EC0521554AB769EA43A13B4BB83C02C`
- Exact parent diff:
  - SHA256:
    `67E0B3981C08C4A0C231780FFB77270D14C72599541B3E9191063EFADEEAA1C7`

Only `main.py` differs from the direct parent.  The runtime tree has 12 files
and no cache files.  The module has one top-level `agent`, it is the
loader-last callable, and `_cum_diagnostic_disabled_rules` is empty.

## Integrated mechanisms

The fixed arbitration order adds three rules to the already cumulative General
resolver.

1. Rank 6: equal two-Prize normal-mode Active race.
   It keeps attacking the two-Prize Active and preserves Boss instead of
   switching to a one-Prize Bench target when the public race certificate
   holds.
2. Rank 7: post-Metal-attachment non-ex Archaludon 120-damage conversion.
   It evolves for an immediate Coated Attack KO only when the currently ready
   public Bench successors are nonlethal.  A failed continuation clears
   ownership and recomputes from the actual evolved state.
3. Rank 19: persistent public Boss-access ledger.
   When three Boss are publicly discarded and the last copy is in a complete
   hand, it preserves the last Boss only when a plan-equivalent alternate
   discard retains the same board construction and immediate attack.

The complete rank set is exactly 3 through 19.  Unknown collisions and failed
certificates return to the exact parent action.

## Root checks

- `HASHES.sha256`: 16/16 matched.
- Compile/import with Python 3.11: pass.
- Legal deck and loader ordering: pass.
- NMR: 8 positive and 16 negative focused cases passed.
- PAN: 8 positive, 34 negative, four harmful controls, both engine seats, and
  post-evolution rollback passed.
- Boss ledger: both engine seats completed
  Ultra Ball -> discard -> search -> Bench -> attack.
- Inherited General focused suite: all cases passed.
- Frozen-General shadow: 89 episodes, 4,864 callbacks, zero action
  differences, exceptions, action errors, or telemetry errors.
- Targeted source shadow: 182 callbacks and exactly three intended
  differences, one per new rule.  Each individual rule ablation restored the
  exact parent action.
- Clean archive:
  `submission_archaludon_integrated_public_turn_plan_transaction_v1_20260731.tar.gz`
  - SHA256:
    `0BB57047E258B587F8110F882A10D0EB8FDEEE48323B5C0307E88878FAA118E1`
  - 12 runtime files after extraction, all hashes equal to the candidate, no
    caches.
- Packaged both-seat smoke against historical-Silver:
  - seat 0: 136 steps, action errors 0, no max-step hit;
  - seat 1: 105 steps, action errors 0, no max-step hit.
  - Both games were losses.  Absolute strength is therefore not established,
    but weak local results are not a blocker under the user-authorized
    exploratory live policy.

## Latest submitted-parent evidence before write

Authenticated Kaggle refresh showed submission `55120278` COMPLETE at 830.4.
The fetched episode table has 50 rows, not 50 public games:

- 49 public games: 29 wins, 20 losses;
- one validation game: one win.

Episode CSV SHA256:
`8CC04CAF4805613FB5A5CA5CC7A8B1C7AD7E1FB44973E463AA2DFBFBB108A076`.

The candidate was shadowed in the correct `rurumi` seat over all 49 public
games:

- 2,783 callbacks;
- zero candidate-parent differences;
- zero invalid actions;
- zero exceptions;
- zero telemetry errors.

This is additional safety evidence, not strength or mechanism evidence.  The
three new mechanisms did not occur in these 49 public histories.

Shadow JSON SHA256:
`E21CE85DC340486A32AABB6B04A8AEA4C1C31D012AFB605D7D5F1813EBA7E755`.

At the final 2026-07-31 12:46 JST pre-write refresh, submission
`55120278` still had exactly the same 50 unique episode IDs.  There were zero
added and zero removed IDs.  The refreshed no-download CSV SHA256 was
`741B4E7C8FB7DBD319AAA561C946C7B861723F08CAAEF98D569250C86382281B`.
The current UTC day had zero submissions, so five of five daily slots were
available.  The submitted-parent status remained COMPLETE at 830.4.

## Independent final judgment

The Sol-Ultra strategy judge accepted exactly one exploratory live probe.  It
did not grant formal adoption.  Primary live follow-up must capture genuinely
new episode IDs, compare candidate and parent in the correct seat, inspect
every first difference, and run the winning-rule ablation.  A no-fire result
is safety evidence only.

## Kaggle write

The exact frozen archive was uploaded once at 2026-07-31 03:46:18 UTC.
Kaggle registered it as submission `55126164`, initially PENDING.  The upload
reached 100%; the first CLI process then raised a local CP932
`UnicodeEncodeError` while printing Kaggle's response.  No retry was issued.
An immediate UTF-8 authenticated refresh proved that the submission existed
with the expected filename, 2,091,360-byte size, description, timestamp, and
submission ID.  Post-write UTC-day usage is one of five slots.

The next authenticated refresh showed COMPLETE at 600.0.  The episode service
contained exactly one validation self-play, episode `89077826`, with the
target seat losing; there were zero public ladder games.  Thus 600.0 is only
the validation initial value and is not evidence of live strength or
regression.  The initial episode CSV SHA256 is
`53A8E22FDCBDE8E7EF575FEB6C9C47D5F22E54F0C9493A5E0C0F1F851450679B`.

## Windows sandbox diagnosis

The earlier edit failure was not a source-file ACL, lock, path-length, or
corrupted-installation failure.  The configured default was
`sandbox_mode = "workspace-write"` with Windows `sandbox = "unelevated"`,
while the task exposed two disjoint writable roots: the project and a Codex
visualization directory.  Both installed Codex CLI binaries contain the
explicit fail-closed condition:

`windows unelevated restricted-token sandbox cannot enforce split writable root sets directly; refusing to run unsandboxed`

The patch wrapper therefore refused before opening the target file rather than
falling back to an unprotected process.  The resumed task now has an
unrestricted/full-access permission profile, so the wrapper no longer needs to
represent split writable roots.  Root-level and candidate-directory
`apply_patch` probes both succeeded after restart, and the full candidate edit
and verification completed without another sandbox denial.
