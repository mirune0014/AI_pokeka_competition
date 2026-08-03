# Strategy selection — Neutralization Zone property-bound damage prevention v1

## Decision

The next authorized operation is a read-only taxonomy and semantic census.
No candidate source edit is authorized yet.

The hypothesis is:

`NEUTRALIZATION_ZONE_PROPERTY_BOUND_DAMAGE_PREVENTION_V1`

When exact catalog metadata and the one visible Stadium prove that
Neutralization Zone is active, attack damage is prevented exactly when the
attacker is an exact Pokemon ex or Mega Pokemon ex and the damaged Pokemon has
no Rule Box.  The transition is symmetric for Active and Bench attack-damage
components.  It does not prevent damage-counter placement or other attack
effects.  Exact ignore-effects attacks continue to ignore the protection.

The semantic transition must propagate through damage, KO, Prize, finish,
public return routes, survival, hits to KO, attack continuity, backup
conversion, and post-reply resource ledgers.  It assigns no score and owns no
action transaction.  Unknown identities fail closed to the exact parent.

## Why this precedes Boss and another card-use overlay

The frozen Jumbo Ice Cream census ended with zero earliest-independent
actionable decisions.  Its exact failure audit nevertheless exposed a broader
coverage problem:

- 225 rows lacked a complete public return/backup certificate;
- 128 rows failed on an unsupported visible Stadium;
- 70 rows failed on unsupported visible skills or tools.

A Boss target cannot be ranked exactly while a visible Stadium may turn the
claimed damage, KO, and Prize into zero.  Read-only inspection provisionally
identified Neutralization Zone as the largest deterministic combat-relevant
Stadium subgroup.  Spikemuth Gym is more frequent, but its deck search is not
an exact public combat transition.

## Immutable inputs

- Exact parent:
  `candidates/archaludon_purpose_first_pokegear_boss_transaction_v1/main.py`
- Parent SHA-256:
  `558EE5DB29E001428B0D59813613FABEE8E15B96E422746C104BDFAB4DC22DB6`
- Corpus:
  `live/55070349/refresh_20260729_1241/shadow_corpus_196_prior_plus_11_new`
- Manifest:
  `next_after_metal_allocation_fail_20260801/night_stretcher_callback_census_raw/source_manifest.json`
- Manifest SHA-256:
  `90A512D5C9AE5EAD8DF92F370C32716959EC0929F9465451E7BB0926DBEB5A68`
- Frozen Jumbo opportunity CSV SHA-256:
  `093573F0C9D5E47EF6EA5E8277E6DD137078D06C07FC20BF8241606B14CCB1D9`
- Frozen Jumbo summary SHA-256:
  `BB38450572DD285FEDAD3B79616CDEE22A0A32AC626111038605CE2239EF085C`
- Independent Jumbo numerical audit SHA-256:
  `1AD2E6036CCD988D478E2D6138E323D41712978FF5E564B158FAB6FEAF52C48D`

Expected exact metadata, which root must verify rather than assume:

- card ID `1247`;
- exact card and skill name `Neutralization Zone`;
- normalized skill-text SHA-256
  `CF3FB44117E74C1FC5AC792A4721CD1EA345A1CAA0A861931A59A46A842FD877`.

## Frozen census outputs

The runner must refuse to overwrite:

- `freeze_pre_edit_neutralization_zone_semantic_census.py`;
- `pre_edit_neutralization_zone_semantic_census_raw/gap_identity_rows.csv`;
- `pre_edit_neutralization_zone_semantic_census_raw/opportunity_rows.csv`;
- `pre_edit_neutralization_zone_semantic_census_raw/summary.json`.

The taxonomy must reproduce all 423 frozen Jumbo plan failures as exactly
225 `RETURN_UNKNOWN`, 128 `UNSUPPORTED_STADIUM`, and 70
`UNSUPPORTED_SKILL_TOOL`, and partition every Stadium row by exact card ID,
name, and normalized text hash.

## Natural-coverage implement/stop gate

All thresholds are fixed before execution.

- exactly 207 replays, 209 target seats, and 25,880 single parent calls;
- zero manifest mismatches, duplicate raw keys, or invalid parent actions;
- at least 40 Neutralization-Zone independent turns, both seats, 12 replays;
- at least 24 affected current-or-return attack certificates, both seats,
  eight replays;
- at least 12 hard plan-ranking differences and eight predicted first-action
  differences, both seats, six and four replays respectively;
- at least three examples each of ex/Mega-ex damage being prevented, non-ex
  damage remaining legal, Rule-Box targets remaining unprotected, and exact
  public return damage being prevented;
- at least two blocked source identities and four protected target identities;
- every predicted first difference must be root-audited `GOOD_CAUSAL`;
- zero hidden-card assumptions, name-only classifications, opponent-ID logic,
  unsupported Rule-Box types, partial damage/effect conflation, or
  unknown-as-zero.

Failing any gate means
`STOP__INSUFFICIENT_NATURAL_SEMANTIC_COVERAGE`; thresholds must not be relaxed.
Passing every gate authorizes one isolated registry edit directly from parent
SHA `558EE5DB...`.  Cornerstone Stance, Spikemuth search, and broader Boss
ranking remain out of scope.

