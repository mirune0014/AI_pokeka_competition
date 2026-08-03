# Root implementation verification

Date: 2026-07-30 JST

Decision at this stage:
`IMPLEMENTATION_AND_ENGINE_GATE_PASS__FIXED760_PENDING`

## Frozen identity

- candidate:
  `archaludon_cumulative_public_hierarchy_megabrave_lock_veto_v2`
- candidate `main.py` SHA-256:
  `DEE5092B6785DF7A63752C7AAE497051D08DCC62F7723CD9786225A0C5A99DE8`
- exact deck SHA-256:
  `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`
- direct rejected cumulative parent SHA-256:
  `BE8C67E387CE4F36344A4B0DE610CAB9976BB07EE49200997D35CCC6C5DBF18A`
- formal historical-Silver rollback SHA-256:
  `F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E`
- controlling Sol-Ultra repair judgment SHA-256:
  `A263871FFB639DB2BB0A535642CFE534434E838ADC1665BE31637FEA66DC112B`
- Root verification specification SHA-256:
  `B26A08A6F414988DE4EFEA5D8788C2F0A27221074BA6A0B6F54B4BD33A7076C3`
- worker implementation report SHA-256:
  `776363B2842D5B4DA98D02FAC6F387D12D4C99282D02848D7DB60599A1919E88`
- H4 repair ledger SHA-256:
  `5283B4ADE5CBE6D391E5C0CAF9438C745C33E961FDADAC0CC2F52751B7C7D5C1`

## Direct source inspection

Root compared the child directly to its cumulative source parent. Only
`main.py` differs; the other 11 runtime files and deck are byte-identical.
There is exactly one loader-last `agent`, 12 runtime files, a legal 60-card
deck with one ACE SPEC, and zero cache files.

The only behavioral edit is:

1. identify the repaired component as
   `H4_PUBLIC_MEGA_BRAVE_SELF_LOCK_VETO_V1`;
2. before `_h4_build_certificate` constructs or mutates a certificate, return
   ineligible when `_opp_last_attack_id == MEGA_BRAVE` (`983`);
3. retain all other rule code, ranks, collision behavior, transaction/reset
   behavior, exact-parent scoring, and deck.

Remaining direct-source changes are identity and frozen-ledger metadata. Root
found no episode, seed, opponent-identity, or replay-future marker.

## Root command verification

Root reran with Python 3.11 and `PYTHONDONTWRITEBYTECODE=1`:

- compile verification;
- focused Mega Brave lock/no-lock matrix;
- H2, search-aware, H1, H5v2, repaired H4, H6v2, Hero, and H3v2 suites;
- exhaustive collision registry;
- structure/import/legal-deck validation.

Every command exited `0`.

Root's first attempt to rerun the changed-trace smoke in the worker's
implementation directory exited `1` because the checked script correctly
refused to overwrite its existing immutable output directory. This is a
duplicate-output refusal, not a candidate failure. Root copied the unchanged
checked script to this separate verification directory and ran it into a fresh
destination.

## Independent changed-seed execution

Root's fresh four-case smoke report SHA-256 is
`BA49CA41B5BB4B2DBF5CBCB2713D5B262AB39D0673E295B8B58D88461E167593`.

- historical-Silver seat 0 seed `271828201`: retained nonidentity;
- Arch Shumpei seat 1 seed `271958328`: retained nonidentity;
- Mega Lucario seat 0 seed `271958329`: retained nonidentity;
- Mega Lucario seat 1 seed `271958318`: historical/repaired trace identity.

The repaired Mega Lucario seat-1 trace is
`4ACC6B2747C12FA26D9E4F548225E021BF91F020CDABE34A4328BD0759D2D3E2`,
result `1`, 85 decisions. At the old first divergence, the child uses the exact
parent's Metal Defender. The next opponent attack is Aura Jab `982`; the
three-Metal Archaludon remains Active at 40 HP.

## Independent 261-replay union

Root copied the unchanged checked union runner and exact component manifest to
this separate verification directory, then reran all 261 replays and 14,464
callbacks.

- parent action differences: `27` in `23` files;
- isolated component comparisons: `115,712`;
- isolated eligibility/action/certificate mismatches: `0`;
- collision sizes: 14,416 clear callbacks and 48 one-rule callbacks;
- transaction starts/clears: `33/33`;
- identical retry checks: `48`;
- invalid actions, caught/outer exceptions, emergency fallbacks, unknown
  collisions, stale/two-owner states, owner switches, retry parent calls, and
  max-step hits: all `0`.

Root outputs match the worker's reported content hashes:

- `union_shadow_differences.csv`:
  `04DAD74EE2A09141D313E92718F083CA2EB811AF26C3430D044921832630CAD7`;
- `union_shadow_first_differences.csv`:
  `7517572716141EA6581E74D8238A69F565EDAD63F5FE406E205A399F39E1B77C`;
- `union_shadow_per_file.csv`:
  `E2CCB3D59504C0D4EB9377FDDC49D3594A663A6D480F1A651C8ABB73D4BF6817`;
- `union_shadow_source_manifest.csv`:
  `19E27FA3AE78C89C8D93DE3427EC12F4B905B8F8DC96649F30C20CFDA0B8BE5B`.

The repaired child removes only the tracked-Mega-Brave H4 activation at
episode `87825800`, callback row `124`; it preserves the exact parent's Metal
Defender there.

## Fixed evaluation handoff

The checked fixed-760 launcher SHA-256 is
`A733DA2606F12B367E20B999C89A1FB305E3C9279915C3491107DC2D438A06DB`;
its launch specification SHA-256 is
`E49A84DF8A8DB478000A733A72A40162E3F0429934A55B43F4CE3C7DABCAEC50`.
Root verified all frozen authorities and confirmed the new raw output
destination did not exist before handing the exact command to the designated
deterministic evaluation runner.

No archive or Kaggle write is authorized until the fresh fixed-760 output,
independent numerical audit, Root recomputation, and final Sol-Ultra practical
judgment complete.
