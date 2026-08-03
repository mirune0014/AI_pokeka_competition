# Fragile-Bench Prize-clock v1 — immutable Phase-0 keys

- Date: `2026-07-17` (JST)
- Scope: key materialization only; no source edit, battle, package, promotion
  interpretation, or Kaggle action
- Strategy authority:
  `20260717_alakazam_second_distinct_slot_strategy_select.md`, SHA-256
  `93A130DEE03EEF0F72E38D5F8CEA00A8B7A04B4546841B90D6FAA7842061CAA0`
- Frozen v3 source/deck:
  `5F8F6578BF98BC285BB468FAD26969A22EDA96378F8E3AE35F134EA70EB91830` /
  `7B413177E5077777F2178143839C0155B03B92BBC8B3A6607621A7D43F351141`
- Frozen v3 broad raw-tree digest:
  `5F77DE190AD2DCB94F4EE737D301C6A798BFE4074C45D5A8A8CE27F0A7A4BB78`

`R` below is
`autonomous_gold_20260715/evaluations/alakazam_run_away_draw_actual_capacity_v3/broad`.
Coordinates are trace turn / JSON `step` / one-based physical line. Every
listed row has v3's selected top action `PLAY Abra 741`, a ready Active
Alakazam `743` with legal Powerful Hand `1072`, and was recomputed directly
from the frozen JSONL. File hashes are SHA-256 of the complete trace.

## Exact positive ledger: 9 schedules, 10 events

Each event additionally has opponent Prizes at most three, a conservatively
ready Jetting Blow `1487` or Phantom Dive `154`, and an existing Bench
Alakazam or Bench Kadabra plus in-hand Alakazam.

| Schedule key | Coordinate | Trace under `R` | Trace SHA-256 | Public boundary |
| --- | --- | --- | --- | --- |
| `new_fresh|starmie|p0|2026091707` | T11/S93/L94 | `new_fresh/candidate/starmie/p0/traces/game_0006.jsonl` | `4E9F6C125BCFFF3FDFAD7690FD2A591B89CE2216A5AC7ACB3BD415D21882E3B6` | Active `1031`, E `[3]`, opp P3, Bench `[743,142,140]` |
| `new_fresh|starmie|p0|2026091736` | T9/S82/L83 | `new_fresh/candidate/starmie/p0/traces/game_0035.jsonl` | `7EC5D13655A447198261C8EB891E6BF61F912CE8C0D511C214F5D4773153A8D5` | Active `1031`, E `[3]`, opp P2, Bench `[305,743,305,858]` |
| `new_fresh|starmie|p1|2026091719` | T6/S79/L80 | `new_fresh/candidate/starmie/p1/traces/game_0018.jsonl` | `73F0B60B4EACF6D203396F2C86863392F91996BD1E99414C2A34505B6498539C` | Active `1031`, E `[3]`, opp P3, Bench `[140,743,66,305]` |
| `new_fresh|starmie|p1|2026091719` | T8/S87/L88 | `new_fresh/candidate/starmie/p1/traces/game_0018.jsonl` | `73F0B60B4EACF6D203396F2C86863392F91996BD1E99414C2A34505B6498539C` | Active `1031`, E `[3]`, opp P2, Bench `[140,743,66,305]` |
| `new_fresh|starmie|p1|2026091730` | T8/S80/L81 | `new_fresh/candidate/starmie/p1/traces/game_0029.jsonl` | `364C9462E6850A0C5AB6C2827D5130036959D6C02F9DC3335344C417A5F6B00E` | Active `1031`, E `[3]`, opp P2, Bench `[140,743,305,142]` |
| `fresh|starmie|p0|2026081719` | T9/S86/L87 | `reference/candidate/fresh/starmie/p0/traces/game_0018.jsonl` | `DE26CF2F6582B865C2017D33320FD85C5B916C21B4DEF6C9D20937C56773F743` | Active `1031`, E `[3,3,3]`, opp P3, Bench `[743,66,66]` |
| `fresh|starmie|p1|2026081706` | T10/S98/L99 | `reference/candidate/fresh/starmie/p1/traces/game_0005.jsonl` | `30B1A70885FBF4630D1229487BF7F94C8CD75A5425C31AC869AC754C48F82B92` | Active `1031`, E `[3]`, opp P2, Bench `[142,66,743]` |
| `fresh|starmie|p1|2026081712` | T10/S110/L111 | `reference/candidate/fresh/starmie/p1/traces/game_0011.jsonl` | `E41154CB5F9338304BEAE9818CA8B8C59AD34CC807BFD1C0A3782B0BA3C2BFF4` | Active `1031`, E `[3,3,3]`, opp P3, Bench `[140,142,742,66]` |
| `known|dragapult|p1|2026071585` | T14/S110/L111 | `reference/candidate/known/dragapult/p1/traces/game_0004.jsonl` | `0F50828CF0E6E6B87F784FF0AC19FDB4D4F7EEF5DDF3A96AA78CA32E3EA76373` | Active `121`, E `[5,2]`, opp P2, Bench `[743,305,142,305]` |
| `known|starmie|p0|2026071597` | T5/S47/L48 | `reference/candidate/known/starmie/p0/traces/game_0016.jsonl` | `3D0991D0DB2885A8B991D987DD06038BF1DED1E91129387FC3950367A5DE7814` | Active `1031`, E `[3]`, opp P3, Bench `[742,305]` |

The repeated `2026091719` schedule is intentionally one battle with two
qualifying `PLAY Abra` events; it is one paired key, not two games.

## Exact deterministic boundary controls: 16 schedules

Selection was frozen without outcomes. Within each available opponent-seat
cell, choose the earliest tuple by block order `known < fresh < new_fresh`,
then seed, turn, and step. A cell with no qualifying row contributes no key.
The first three groups differ from the positive predicate at the named
boundary; Historical-Silver and both mirror groups are non-target identity
controls with H0, opponent Prizes at most three, and stage dominance present.

| Boundary | Schedule key | Coordinate | Trace under `R` | Trace SHA-256 | Public boundary |
| --- | --- | --- | --- | --- | --- |
| ready spread, P4-6 | `known|dragapult|p0|2026071598` | T7/S74/L75 | `reference/candidate/known/dragapult/p0/traces/game_0017.jsonl` | `C74B4DF060BC7292780E7E00764C165FD289945CC071110A1C5FFB345D3FAD8B` | Active `121`, E `[2,5,2]`, opp P5, stage 1 |
| ready spread, P4-6 | `known|dragapult|p1|2026071581` | T10/S106/L107 | `reference/candidate/known/dragapult/p1/traces/game_0000.jsonl` | `E1C3E9DFA697759D686F75D31CC61D109B433AF70C7475376B0C0EB701757066` | Active `121`, E `[2,5]`, opp P4, stage 1 |
| ready spread, P4-6 | `fresh|starmie|p0|2026081714` | T7/S68/L69 | `reference/candidate/fresh/starmie/p0/traces/game_0013.jsonl` | `F34A5831C6B7C0BA9CAA02EFC69164B6EBE76B88C215A354120BD1C0D6840D06` | Active `1031`, E `[3]`, opp P5, stage 1 |
| ready spread, P4-6 | `known|starmie|p1|2026071591` | T6/S73/L74 | `reference/candidate/known/starmie/p1/traces/game_0010.jsonl` | `CF5C058BA9C66EAB89DABA63DEBA3DEA9BF1BA2D03D1FF49131FD246FE1DBCB0` | Active `1031`, E `[3,3]`, opp P4, stage 1 |
| no stage dominance | `new_fresh|dragapult|p0|2026091718` | T7/S50/L51 | `new_fresh/candidate/dragapult/p0/traces/game_0017.jsonl` | `D4E0DFD9D4410ADAAABBE1A188E0E9D06A6E87F6F165AC97566D225DE38CA2D2` | Active `121`, E `[5,2]`, opp P3, stage 0 |
| no stage dominance | `new_fresh|starmie|p0|2026091716` | T9/S109/L110 | `new_fresh/candidate/starmie/p0/traces/game_0015.jsonl` | `0E7EEB8DB28332D1140C410D2FBE8644BAB7A7F899CCDF215134C7AEBEE2E39F` | Active `1031`, E `[3,3,3]`, opp P3, stage 0 |
| no stage dominance | `known|starmie|p1|2026071595` | T8/S67/L68 | `reference/candidate/known/starmie/p1/traces/game_0014.jsonl` | `E01EA59266647FA96DC51DDDC9E2FCEE8FE8D5ACCCB48E663E71E9C957B25B4E` | Active `1031`, E `[3,3]`, opp P3, stage 0 |
| no ready spread Energy | `fresh|dragapult|p0|2026081708` | T25/S144/L145 | `reference/candidate/fresh/dragapult/p0/traces/game_0007.jsonl` | `2128782D2B43111DF419B74B054D8A8CE27195F99C3141A207A50D7C21A489C9` | Active `121`, E `[2]`, opp P2, stage 1 |
| no ready spread Energy | `new_fresh|starmie|p0|2026091706` | T11/S113/L114 | `new_fresh/candidate/starmie/p0/traces/game_0005.jsonl` | `74F3C6A8F9B18A95D77E58C4CAF530DB5FAC9E6A8E90BEA1C821564A9B2F1635` | Active `1031`, E `[]`, opp P3, stage 1 |
| no ready spread Energy | `new_fresh|starmie|p1|2026091726` | T10/S89/L90 | `new_fresh/candidate/starmie/p1/traces/game_0025.jsonl` | `0122A87DDCED7418C98C05BD5B25D4C654E27A08257C9D90A2F6FAB8B8D31B1C` | Active `1031`, E `[]`, opp P3, stage 1 |
| Historical-Silver | `known|historical_silver|p0|2026071596` | T9/S125/L126 | `reference/candidate/known/historical_silver/p0/traces/game_0015.jsonl` | `304464B0B8EB1DAE229751E9F5979F5CF2EF3613F9714F51A61F23DEEAED0EB4` | Active `190`, E `[8,8,8,8,8]`, opp P3, stage 1 |
| Historical-Silver | `new_fresh|historical_silver|p1|2026091706` | T11/S103/L104 | `new_fresh/candidate/historical_silver/p1/traces/game_0005.jsonl` | `1080BE3EE5C7B8E784D66CD3FE6D8E527087B2867C3503C88CE6F684CB98066E` | Active `190`, E `[8,8,8]`, opp P3, stage 1 |
| Alakazam OSELCOUN | `known|alakazam_oselcoun|p0|2026071581` | T15/S167/L168 | `reference/candidate/known/alakazam_oselcoun/p0/traces/game_0000.jsonl` | `619F97AF08CF6B140F8DF02B0943B2AD072DE7B91E1D6646ED3113135C66A5A9` | Active `743`, E `[19]`, opp P2, stage 1 |
| Alakazam OSELCOUN | `known|alakazam_oselcoun|p1|2026071597` | T10/S125/L126 | `reference/candidate/known/alakazam_oselcoun/p1/traces/game_0016.jsonl` | `9F4B4628458536B0179621FE8EB8EE17E02B1C455D5B0D41B6617AE9D68DCFE3` | Active `743`, E `[5]`, opp P3, stage 1 |
| Alakazam Rmy | `known|alakazam_rmy|p0|2026071592` | T15/S137/L138 | `reference/candidate/known/alakazam_rmy/p0/traces/game_0011.jsonl` | `E81FA680F0171C9417AAD1DBCE241B773EA7132FA8BBD0487A1FD4E22162F6F9` | Active `743`, E `[5,19]`, opp P2, stage 1 |
| Alakazam Rmy | `known|alakazam_rmy|p1|2026071584` | T12/S146/L147 | `reference/candidate/known/alakazam_rmy/p1/traces/game_0003.jsonl` | `87BD9A7ABD87693501F68F490BAE0758FB30504B469739BA71899CF0603F9AE3` | Active `743`, E `[19]`, opp P3, stage 1 |

## Execution boundary

Phase 0 is exactly 25 unique paired schedules: 9 positive keys plus 16
boundary keys, one parent and one candidate game per key in the recorded
seat, for 50 one-game commands. The two positive events in
`new_fresh|starmie|p1|2026091719` remain one schedule. No additional seed,
opponent, retry, replacement control, or inferred counterfactual is permitted
without a new pre-execution specification. This appendix supplies keys only;
all promotion gates remain those in the strategy decision.
