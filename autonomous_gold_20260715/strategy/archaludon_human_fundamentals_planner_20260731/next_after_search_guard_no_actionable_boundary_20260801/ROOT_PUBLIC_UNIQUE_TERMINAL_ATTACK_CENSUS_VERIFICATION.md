# Root verification: public unique terminal-attack dominance v1

Decision: `STOP__PUBLIC_UNIQUE_TERMINAL_ATTACK_DOMINANCE_NOT_BROADLY_ACTIONABLE`

No candidate source is authorized or created from this frozen census.  The
behavioral principle is correct in every observed causal position, but the
precommitted breadth and control gates do not pass and are not relaxed after
seeing the result.

## Frozen evidence

- strategy SHA-256:
  `7165420EB6F84BC28CFDC1096F9C8851B85196796B916015AC7B8696CB48EB43`
- runner SHA-256:
  `1F52AA13AC94105C0226BD0E14263938EF45CB870A46D63E201B43C45756A0B4`
- execution specification SHA-256:
  `ADCC1FC4DB60C6150A7CC9E7BB57A8E53C8180DA1FF71B8F07C850B28C70F2E2`
- exact parent / deck SHA-256:
  `558EE5DB29E001428B0D59813613FABEE8E15B96E422746C104BDFAB4DC22DB6` /
  `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`
- deterministic execution: exit `0`, elapsed `613593 ms`, stderr empty,
  cache files `0`
- `all_callback_rows.csv` SHA-256:
  `B7CAF6E47882E231CB5C1EAB3B418200B994CF3209BDA98C4F69A4D64D71E308`
- `causal_first_differences.csv` SHA-256:
  `BD296E8382842F07B52BA9EBB1897377B23EF3EB6193B94747A24C4A77C13AFD`
- `source_manifest.json` SHA-256:
  `90A512D5C9AE5EAD8DF92F370C32716959EC0929F9465451E7BB0926DBEB5A68`
- `summary.json` SHA-256:
  `9295E94658B030A282069BD009F89565CE5A93F0FFA2B75359EA23B1B0985EEB`
- independent Sol-Ultra audit SHA-256:
  `F41954FFA3538D77B1495FDAF153EC15F9FE1499BFF7E27CF220FBD718B57B69`

## Root recomputation

The root read the raw CSVs rather than accepting `summary.json` as authority.

- 25,880 callback rows and 25,880 unique
  `(replay, seat, step, turn, snapshot)` keys;
- exact 207-replay manifest and 209 target seats;
- exactly 15 causal rows, one per 15 distinct replay-seat groups;
- seats `8 / 7`;
- causal families: `PLAY_ITEM_SEARCH 5`, `PLAY_SUPPORTER 2`,
  `PLAY_ITEM_OTHER 2`, `ATTACH 2`, `PLAY_POKEMON 2`, `EVOLVE 1`,
  `RETREAT 1`;
- ten non-search causal rows across six non-search families;
- largest family share `5/15 = 33.33%`;
- 22 parent-equal terminal controls across 21 replays and both seats;
- 5,862 identical retries, zero nonidentical retries;
- zero invalid parent/contract action, hidden-information flag, predicted owner
  collision, semantic-copy prediction, predicted error, or unclassified clear
  MAIN row.

The root independently replayed each of the 15 causal callbacks from reset
through the target step.  All 15 reproduced the bound snapshot, exact parent
semantic, empty pre/post owner vector, unique legal terminal attack, valid
bound action, `EXACT` public combat certificate, payable Energy, KO, and either
Prize exhaustion or an exactly empty opposing Bench.  Labels are
`GOOD_CAUSAL 15/15`.

Attack distribution was Metal Defender `11` and Turbo Flare `4`.  Terminal
witnesses were empty opposing Bench `9`, Prize exhaustion `5`, and both `1`.

## Fixed-gate result

Passes:

- integrity;
- zero violations;
- both-seat floor (`8 / 7`);
- family concentration;
- qualitative causal correctness.

Fails:

- causal volume: `15/24` and `15/16` required replays;
- family breadth: only search has at least three rows, versus three families;
- outside-search row floor: `10/12` (family breadth itself passes);
- parent-equal controls: `22/24` (21 replays and both seats pass);
- literal known-residue equality.

The four old search-census callbacks are all preserved.  The broad all-family
scan also finds three legitimate search-terminal callbacks outside the old
purpose-filtered surface, so its raw search result is seven rows / six starts,
Pad five / Ultra two, Metal Defender five / Turbo Flare two.  This is useful
diagnostic evidence, but the frozen gate required exact equality, not
containment, so it remains a failure rather than a post-hoc amendment.

## Consequence

The parent demonstrably misses some certain wins across seven action families,
but this particular isolated rule is not implemented because the frozen
pre-edit contract required materially broader natural coverage.  The next
hypothesis must use this verified gap without changing this decision, stacking
an unauthorized terminal layer, or narrowing to replay/card exceptions.
