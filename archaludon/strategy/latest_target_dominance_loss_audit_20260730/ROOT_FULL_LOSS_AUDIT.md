# Submission 55099164: root loss and regression audit

## Scope

- Submission: `55099164`
- Submitted policy: `archaludon_cumulative_public_one_turn_target_dominance_v1`
- Submitted source SHA-256: `6504E0E3EA69D59EAB5F9A73E306D70695A0E76ECA8D347C97F1EB43AEE31B7A`
- Direct parent SHA-256: `DEE5092B6785DF7A63752C7AAE497051D08DCC62F7723CD9786225A0C5A99DE8`
- Episode evidence: 54 public games, 32 wins and 22 losses
- Episode CSV SHA-256: `5F568156AE4F77F6D0F75ABA210B1202C92FD2E42512A46B5FA760453690A0DB`
- Correct-seat callbacks replayed: 3,093

## Regression conclusion

The submitted target-dominance overlay caused no observed live regression.

- Submitted-policy versus recorded-action mismatches: 0
- Submitted-policy versus direct-parent action differences: 0
- New-rule proposal or owner events: 0
- Invalid actions: 0
- Exceptions: 0

The overlay therefore did not worsen any of the 54 public games, but it also
had no live coverage. The live score must not be causally attributed to this
overlay.

Its exact rejection counts were:

- activation boundary: 2,145
- parent was not an exact supported attack: 840
- incomplete or unsupported public state: 99
- unsupported opponent board: 9

The correct response is to retain the non-firing rule and add independently
auditable rules for the verified live defects. Removing it would not repair
any observed loss.

## Public matchup result

| Opponent archetype | W-L |
|---|---:|
| Alakazam | 2-5 |
| Archaludon | 6-3 |
| Cynthia | 1-1 |
| Dragapult | 2-2 |
| Great Tusk / Crustle | 1-0 |
| Hop / Trevenant | 1-1 |
| Iono / Bellibolt | 1-1 |
| Kangaskhan / Crustle | 1-2 |
| Marnie / Grimmsnarl | 3-3 |
| Mega Abomasnow / Kyogre | 2-0 |
| Mega Lucario | 10-3 |
| Starmie / Froslass | 1-1 |
| Unknown | 1-0 |

This sample shows a clear Alakazam weakness, but the replay audit did not find
a public-state action fork strong enough to certify a repair in five of those
seven games. Matchup score alone is not used as an action label.

## High-confidence preventable losses

### 88917360: protect the future attacker before Lillie

Hero's Cape was legal on the sole Bench Duraludon before Lillie. Playing the
Tool did not consume the Supporter action, and the same Lillie remained legal.
That Duraludon later became Archaludon ex.

The observed damage line without Cape was:

`300 -> 180 -> heal to 260 -> Voltaic Chain 320 -> KO`

With Cape it is:

`400 -> 280 -> heal to 360 -> Voltaic Chain 320 -> 40 HP`

Required mechanism: play Cape before an irreversible hand-changing action when
the target is a publicly certified next attacker, then resume the cached parent
action.

### 88917846: spend Cape and preserve Turbo Flare continuity

Hero's Cape was legal before Turbo Flare on the future reserve Duraludon. The
opponent's following Unfair Stamp discarded the unused Cape. That line later
became an Archaludon ex and took Draconic Buster for 320 from 300 HP; Cape
would leave 80 HP.

A second exact fork occurred late in the game: the policy retreated while
Turbo Flare remained legal. Attaching the visible Basic Metal to the backup
Duraludon and using Turbo Flare had a public deck-accounting floor of at least
two remaining Metal for acceleration.

Required mechanisms:

1. Cape before the same-turn future-attacker transaction.
2. Complete the visible Turbo Flare continuity line before a non-terminal
   retreat.

### 88923881: convert the powered line into the non-ex attacker

Crustle's public Mysterious Rock Inn blocked damage from Pokemon ex. A fully
powered Duraludon had a legal non-ex Archaludon evolution and payable Coated
Attack. The policy left it unevolved and ended, leaving no visible damage route
through the immunity.

Required mechanism: a strict immunity registry that evolves a ready Duraludon
into the supported non-ex attacker when ex attacks cannot deal damage.

### 88932139: rotate to the healthy ready attacker before attacking

At the critical callback:

- Active Archaludon ex: 80 HP, three Metal
- Bench Archaludon ex: 260 HP, three Metal
- Opponent Active Mega Starmie ex: 330 HP, one Water
- Full Metal Lab was public

The policy used Metal Defender from the wounded Active. Retreating to the
healthy, fully powered backup preserved the same 220 damage. The visible next
Jetting Blow for 90 could not KO the backup, preserving next-turn lethal.

Required mechanism: before a non-terminal attack, rotate only when a unique
healthy ready backup preserves the attack and publicly survives every
currently payable visible counterattack while the current Active does not.

### 88947304: preserve the one-prize Active pivot

The policy evolved a zero-Energy, immobile Active Duraludon into a stranded
two-prize Archaludon ex. A Bench Duraludon already had one Metal, while exactly
one Metal was public in discard for Assemble Alloy. Evolving the nearer-ready
Bench line preserved the one-prize Active pivot and created attack access.

Required mechanism: route Archaludon ex evolution to a unique nearer-ready
Bench Duraludon when evolving the zero-Energy Active produces a stranded
two-prize target. The rule must not fire if the Active evolution itself becomes
immediately attack-ready and survivable.

## Losses without a certified repair

The remaining 17 losses were dominated by one or more of:

- no visible Metal or delayed setup;
- opponent engine strength with no publicly provable alternative line;
- spread or counter damage where a different action was not shown to survive;
- a prize exchange where hidden future cards determined the better line;
- an overwhelming attack that also KOed the plausible recovered alternative.

These games remain diagnostic evidence, but they are not used to create
episode-shaped actions.

## Selected implementation scope

Implement `PUBLIC_NEXT_ATTACKER_CONTINUITY_SUITE_V1` as independent hard gates
under one public-state continuity hypothesis:

1. Cape before a certified future-attacker irreversible action.
2. Turbo Flare continuity before a non-terminal retreat.
3. Immunity-aware ready non-ex evolution.
4. Healthy-ready pre-attack rotation.
5. Sacrificial-Active preserving Bench evolution routing.

The existing target-dominance overlay remains installed. Every new mechanism
must expose proposal, rejection and transaction-owner telemetry, fail closed
on ambiguity, and be verified against its exact source replay plus close
negative controls. Broad local win rate is not an adoption gate for this
repair cycle; destructive breakage is.

## Authoritative raw artifacts

- Evidence root:
  `autonomous_gold_20260715/evidence/latest_target_dominance_submission_refresh_20260730`
- Root exact live shadow:
  `autonomous_gold_20260715/root_verification/latest_target_dominance_submission_55099164_20260730`
- Bucket-B qualitative report SHA-256:
  `6FF422D6FE28BFEFA6BFEA78B8189438CD070C8264185986976A4061AAB64436`
