# Frozen 48-loss decline-KO and alternate-damage audit

## Verdict

All 48 frozen loss replays were inspected: 24 Alakazam losses and 24
adjacent-matchup losses. All 48 replay files are present and the episode IDs
are unique. The exact historical-Silver policy was re-run on the correct
`rurumi` seat obtained from each replay's `TeamNames`; replay actions were not
used as labels.

The audit found no new `HARD_GATE_CANDIDATE`. It found one exact, public,
same-turn ordering mechanism suitable only for an isolated soft-score test:
play Hero's Cape on the current Duraludon before executing the same inherited
non-KO attack when the Cape crosses a fully public, currently payable
return-damage survival boundary. The source is `88643491:77`. This is not a
claim that the alternative wins that replay, and it is not a promotion,
packaging, or Kaggle recommendation.

Two forced-promotion states at `88507294:73/77` support a separate H7-B
investment-preservation hypothesis, but only at low pattern confidence because
both observations come from one replay. They are not the recommended first
mechanism because they trade away current damage and require an opponent-turn
continuation. The Cape transaction instead retains the exact same attack and
damage on the current turn.

Counting one atomic decision transaction as one state, while counting
independent later-turn decisions separately:

| Class | State count | Meaning in this audit |
|---|---:|---|
| `HARD_GATE_CANDIDATE` | 0 | No new terminal, forced-defense, or strictly dominating Prize certificate survived. |
| `SOFT_SCORE_CANDIDATE` | 3 | `88643491:73-77` Cape/order state and independent promotion states `88507294:73` and `88507294:77`. |
| `ALREADY_COVERED` | 16 | Frozen H1/H2/H4 v3/H5 v2/H6/H7-A and Bench-evolution states or mandatory controls. |
| `INSUFFICIENT_PUBLIC_EVIDENCE` | 7 | Harmful-KO/alternate-target claims that require hidden access, a later draw, opponent choice, or an unproved multi-turn result. |

These are certificate inventory counts, not win rates, recurrence estimates,
candidate deltas, or promotion gates.

## Frozen authority and evidence

- Audit specification:
  `autonomous_gold_20260715/strategy/archaludon_hierarchical_rules_20260729/DECLINE_KO_AND_ALTERNATE_DAMAGE_AUDIT_SPEC.md`;
  verified SHA-256
  `F2A0D3DFEFC4030ACEFB0B8B0E27241F17312CB1062E3C9D1A3A0EB6BAE1A141`.
- Exact historical-Silver policy:
  `analysis_outputs/reference_agents/historical_silver_archaludon_54495224/main.py`;
  verified frozen SHA-256
  `F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E`.
- Exact deck:
  `analysis_outputs/reference_agents/historical_silver_archaludon_54495224/deck.csv`;
  verified frozen SHA-256
  `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`.
- Raw replay locator:
  `autonomous_gold_20260715/evidence/live_54927163_refresh_20260729_0344/episode_<ID>_replay.json`.
- The two frozen input specs, two prior reports, episode CSV, and extracted
  deck manifest matched the hashes recorded in the audit specification.

Hashes of the eight replays containing noncovered surviving states:

| Episode | Replay SHA-256 |
|---|---|
| `88507294` | `7E05737E6A994B20C23185B2616797FD557C8CAE2A34A58804FBD25661A00F45` |
| `88643491` | `5C385365DBCA461A5E99B633E00C011CFDCE18ADD7EB0E9DECAF6F4A2FD16DDF` |
| `88417236` | `8FF9C7695C88830C9FD845E1543837E9A01A39B9510B26568EFDC50A21343BC6` |
| `88399026` | `F9C500ABF62ABB1BC8017C87AAF45E4F956BBD95B223FC3124B6F640E83692DB` |
| `88096405` | `20532EE753EE5820A1EB38D2707E192B29A722BEB4D9728062D3F397DE179CB1` |
| `87911107` | `B226C2D87918E2B85E4EE36A0C0B650A7D30D9071683D9F98A376B709FD08718` |
| `88391698` | `62B0F58E36E30193D60C901DFA44F014BB25A98C27619B9AEA379D80985FAC7C` |
| `88134743` | `62A275EE85D5960722CFB667848763BA76D74419282BBD154F2EC594DC7B0848` |

## Observed noncovered decision states

All rows below are from recorded losses. “Parent” means the exact
historical-Silver action recomputed from that public observation. Printed
damage is adjusted for the public Stadium, Weakness, Resistance, protection,
and Tool state where relevant.

### Same-turn Cape ordering: one recommended soft mechanism

`88643491`, seat `0`, turn `8`, row `77`, context `MAIN`, Prizes `5-5`,
`SOFT_SCORE_CANDIDATE`:

- Our Active was Duraludon `169#5`, `130/130` HP, with four Basic Metal
  `#61/#56/#59/#52` and no Tool. The Bench contained only Cinderace
  `666#11`, `30/160` HP, with Metal `#60`.
- The visible hand was Boss's Orders `1182#38`, Basic Metal `8#62`, Hero's
  Cape `1159#37`, and Lillie's Determination `1227#46`.
- The opposing Active was Mega Lucario ex `678#93`, `340/340` HP, with Rock
  Fighting Energy `20#78` and no Tool. Rock Fighting Energy publicly provides
  Fighting Energy. The opposing Bench was Cornerstone Mask Ogerpon ex
  `117#79` with one Fighting, Hariyama `674#81` with two Fighting, Lunatone
  `675#83` with zero Energy, and Mega Lucario ex `678#92` with zero Energy.
  No Stadium or Special Condition applied.
- Relevant legal actions were Hero's Cape to Active Duraludon, score `8,000`;
  Hammer In `223`, score/damage `30`; Raging Hammer `224`, base and effective
  damage `80`; and End, score `0`. The remote Cornerstone marker made
  `apply_overrides()` return `25,000` for every Duraludon Raging Hammer at
  `main.py:564`, even though Mega Lucario, not Cornerstone, was Active.
  Historical-Silver therefore selected Raging Hammer immediately.
- Raging Hammer is a certified non-KO: `340 - 80 = 260` HP. Mega Lucario's
  Aura Jab `982` costs one Fighting and does `130`; it was already payable
  from `20#78`. Mega Brave `983` costs two Fighting and was not currently
  payable. Duraludon has no Fighting Weakness and there was no reduction, so
  Aura Jab exactly KOs the uncapped `130`-HP Duraludon.
- Hero's Cape's printed effect raises the attached Pokemon's HP by `100`.
  An exact-engine branch from row `77` selected Cape option `[2]`, producing
  Duraludon `169#5` at `230/230` with `1159#37`. The exact same inherited
  Raging Hammer remained legal as option `[3]`; selecting it left Mega Lucario
  at `260/340` and Duraludon at `230/230`. Thus the current-turn damage,
  target, Prize result, and attack ID are identical, while the currently
  payable Aura Jab would leave Duraludon at `100` HP instead of KOing it.
  No hidden-card fact enters this current-turn projection or its certificate.

Observed certificate: `Cape -> the same Raging Hammer` strictly improves the
immediate public board while preserving the exact current attack. It proves a
survival boundary against the opponent Active's currently payable attack; it
does not force the opponent to choose Aura Jab, forbid a future attachment
into Mega Brave, stop a hidden Boss, or prove the replay converts to a win.
That opponent-choice limitation keeps the state soft rather than hard.

The first earlier opportunity was row `75`: after Explorer found Cape, the
parent scored retreat `13,000`, Cape on Duraludon `8,000`, and Turbo Flare
`50`, then retreated. Row `77` is the smaller owned difference because it
requires no change to Explorer, retreat, promotion, target, or attack—only
Cape before the already selected attack.

### H7-B forced-promotion states: soft, not selected first

`88507294`, seat `0`, recorded loss:

| Row | Context; turn / Prizes | Public state and legal actions | Classification |
|---|---|---|---|
| `73` | `TO_ACTIVE`; turn `7`, `6-4` | A forced promotion offered Duraludon `169#3` with three Metal, `169#6` with two, and `169#5` with zero. All were `130/130`, Tool-free, and scored exactly `8,000`; `main.py:1287` ignores Energy, and the tie break at `main.py:1308` chose first-listed `#3`. Opposing Active Archaludon ex `190#83` was `300/300` with three Metal under Full Metal Lab `1244#15`. On the following turn, Raging Hammer's `80` was reduced to `50`, a non-KO. The opposing Metal Defender's `220` was reduced to `190`, still lethal to Duraludon. Promoting `#5` would preserve both invested Bench bodies but forfeit current damage. | `SOFT_SCORE_CANDIDATE` |
| `77` | `TO_ACTIVE`; turn `9`, `6-3` | After `#3` was KOed, the independent forced promotion offered two-Metal `169#6` and zero-Metal `169#5`, again tied at `8,000`; first-listed `#6` was selected. Opposing `190#83` was `250/300` with three Metal under Full Metal Lab. The only payable attack was Hammer In: printed `30`, effective `0`; the opposing effective Metal Defender remained lethal at `190`. Choosing `#5` preserves the two-Metal body but still depends on the opponent's later action and our later attachment/access. | `SOFT_SCORE_CANDIDATE` |

Row `38`, context `SWITCH`, is the mandatory parent-identical negative. The choices were
three-Metal `169#6` and zero-Metal `169#3`, but the visible hand held non-ex
Archaludon `840#32` and the opposing Cinderace `666#87` was at `110/160`.
Promoting the invested body enables evolution followed by Coated Attack
`1212` for an exact `120`-damage KO. A lowest-Energy promotion rule would
forfeit that public Prize route.

These two positive rows establish repeated tie scoring in one game, not
cross-game recurrence. The qualitative policy hypothesis is that forced
promotion should account for exposed investment only when every
attack-capable promotion is a certified non-KO, every legal promoted body is
publicly KOed by the same currently payable return envelope, and no visible
same-turn KO/terminal route exists. Because this intentionally sacrifices
damage and remains multi-turn, it is weaker evidence than the Cape-first
transaction.

### Harmful-KO and alternate-target rows lacking a public certificate

| Episode:row | Seat; context; turn; Prizes | Observed public state and historical-parent choice | Why evidence is insufficient |
|---|---|---|---|
| `88417236:45` | `1`; `MAIN`; `8`; `6-6` | Duraludon `169#65`, `230/230` with Hero's Cape and three Metal, faced Dunsparce `305#16`, `40/70`, zero Energy. Hammer In `30` leaves `10`; Raging Hammer `80` KOs; End is `0`; Boss is suppressed at `-500`. Parent chose Raging Hammer. Bench Abra `741#4` had Telepath Psychic `19#24` plus Psychic `5#22`, while the opponent hand count was `5`. | Keeping Dunsparce Active delays the visible Bench, but a hidden attachment makes Trading Places payable and other hidden switch access is unknown. No forced defense, Prize superiority, or match conversion is public. |
| `88399026:122` | `1`; `MAIN`; `10`; `2-2` | Duraludon `169#66`, `130/130`, three Metal, faced zero-Energy Dunsparce `305#13`, `70/70`. Hammer In `30` is a non-KO; Raging Hammer `80` is a one-Prize KO; End is `0`. Parent chose Raging. Bench Alakazam `743#26` had Psychic `5#4`; opponent hand count was `22`. | Dunsparce's one-Energy Trading Places and retreat were unpaid at the snapshot, but next-turn hidden attachment/switch access is necessary to know whether declining the KO actually constrains Alakazam. |
| `88096405:98` | `0`; `MAIN`; `10`; `4-1` | Duraludon `169#6`, `130/130`, three Metal, faced zero-Energy Dunsparce `305#100`, `70/70`. Hammer `30` is a non-KO; Raging `80` KOs. Bench Alakazam `743#81` was `90/140` with Psychic `5#113`; opponent hand count was `28`. Parent chose Raging. The replay then publicly logged Alakazam promotion and Powerful Hand `1072` for the final Prize. | The observed response proves the printed attack existed and was payable, not that it would recur. With a hidden hand and next draw, the audit cannot certify that Hammer forces Dunsparce to remain Active. |
| `87911107:97` | `1`; `MAIN`; `8`; `4-3` | Duraludon `169#65`, `130/130`, three Metal, faced zero-Energy Abra `741#17`, `50/50`. Hammer leaves `20`; Raging KOs. Bench Alakazam `743#25`, `90/140`, had Psychic `5#4`; opponent hand count was `23`. Parent chose Raging. | Teleportation Attack and retreat were unpaid at the snapshot, but attachment/switch/evolution access is hidden. The proposed delay has no deterministic current-turn Prize or terminal certificate. |
| `87911107:113` | `1`; `MAIN`; `10`; `3-2` | Duraludon `169#66`, `130/130`, three Metal, faced zero-Energy Dunsparce `305#13`, `70/70`. Hammer leaves `40`; Raging KOs. Bench Alakazam `743#27` at `140/140` with Psychic `5#3` and `743#25` at `90/140` with Psychic `5#4` were both attack-payable; opponent hand count was `25`. Parent chose Raging. The replay then logged promotion of `#27` and Powerful Hand for `520`, KOing Duraludon. | Leaving Dunsparce might delay those attackers, but only if hidden attachment/switch access fails. The logged response is not an opponent-policy label and does not prove an alternate game result. |
| `88391698:73-76` | `0`; `MAIN -> SWITCH -> MAIN`; `8`; `5-4` | The parent evolved lone Duraludon into non-ex Archaludon `840#32`, `180/180`, four Metal. With opposing Mega Lucario ex `678#64` at `290/340` and two Fighting Active, Boss scored `4,200` over Coated Attack `120`; the target callback chose zero-Energy Lunatone `675#74`, `110/110`, then Coated Attack KOed it. | Attacking the current Mega for `120` is a non-KO and leaves its already payable Mega Brave `270`, which KOs our lone Active. Delaying the Lunatone KO or choosing a different target becomes better only through an opponent deviation or later hidden access; no public superiority is certified. |
| `88134743:55` | `0`; `MAIN`; `6`; `6-5` | Active Archaludon ex `190#7`, `300/300`, three Metal, faced zero-Energy Duraludon `169#78`, `130/130`. Metal Defender `220` KOs; End is `0`; parent attacked. Opposing Bench Archaludon ex `190#80`, `300/300`, already had three Metal. | Leaving the stranded Active may delay the ready Bench attacker, but Duraludon's retreat costs two and public Energy is zero; evolution, attachment, switch, and the later continuation are hidden. No forced block or complete conversion is proven. |

All seven rows are `INSUFFICIENT_PUBLIC_EVIDENCE`. The generic parent branch
at `main.py:1065-1067` scores attacks by immediate printed damage and End at
zero, which explains Raging-over-Hammer and attack-over-End. The observations
identify a possible harmful-KO blind spot, but they do not justify a rule:
every claimed advantage requires information or actions beyond the current
public certificate.

## Frozen covered states

These 16 atomic states are controls, not new recommendations:

| Frozen owner | Count | Exact states |
|---|---:|---|
| H1 | 1 | `88457867:142-157` unique ready Alakazam threat-removal transaction. |
| H2 | 1 | `88017509:114-125` exact last-Prize recovery/attach/Boss/attack transaction. |
| H4 v3 | 9 | Positives `88417236:70`, `87974582:72`, `88096059:114`, `88171291:60`, `87825800:116`, `87825800:124`; mandatory parent-identical controls `87825800:110-114` (ambiguous), `87892692:48-51` (supporter used), and `88171291:39` (retreat required). |
| H5 v2 | 2 | `87996118:93-96` positive and `88602602:118-120` existing-route negative. |
| H6 | 1 | `88584180:90-93` attack-completing Metal before resource consumption. |
| H7-A | 1 | `88660007:78-83` sole-ready-successor Alloy allocation. |
| Bench-evolution audit | 1 | `88247531:114-125` evolution of the damaged three-Energy Bench Duraludon before visible Bench damage. |

Overlapping controls were counted once. In particular, H4's equal-Prize
negative at `88457867:144`, no-attack negative at `88017509:114`, and
attachment-required negative at `88584180:90` are already represented by
H1, H2, and H6 respectively.

The 28 episodes with no surviving high- or medium-confidence callback were:

- Alakazam: `88614404`, `88479736`, `88454146`, `88385224`, `88323824`,
  `88244115`, `88242194`, `88232035`, `88191793`, `88163977`, `87994013`,
  `87935410`, `87842092`.
- Adjacent: `88655752`, `88563380`, `88509934`, `88411737`, `88389000`,
  `88367994`, `88356203`, `88338429`, `88272191`, `88225916`, `88197270`,
  `87868636`, `87709435`, `87701753`, `87690776`.

Their prior resource stalls, line exhaustion, opponent pressure, or apparent
draw variance do not become decline-KO certificates merely because the
recorded result was a loss.

## One narrowly testable countermeasure

Recommendation: isolate a **pre-attack Hero's Cape survival transaction** as a
soft experiment directly from exact historical-Silver. Do not stack H1/H2/H4/
H5/H6/H7-A or use an opponent/archetype label.

The certificate should trigger only when all of the following are public and
exact:

1. the cached exact parent action is an attack with a uniquely identified
   attacker serial and attack ID;
2. that exact attack is a deterministic non-KO and is not a current terminal,
   higher-Prize, or forced-defense line;
3. Hero's Cape is visibly in hand, the same Tool-free Active attacker is the
   unique distinct survival-qualifying target, and at least one legal Cape
   option resolves to that exact attacker serial; other nonqualifying legal
   Tool targets do not enter the transaction;
4. at least one deterministic attack printed on the opposing Active is
   currently payable and KOs the uncapped attacker;
5. every currently payable deterministic attack from that opposing Active
   remains below the Cape-raised HP, after public Weakness, Resistance,
   Stadium, Tool, protection, and status modifiers;
6. playing Cape does not consume or change attack payment, and the next
   callback presents the exact same stored attack ID against the same target;
7. no hidden card, future attachment, chance effect, matchup name, episode ID,
   or opponent-policy assumption is used.

Transaction outline: snapshot the seat, turn, action count, Prize counts,
attacker/target serials and fingerprints, Cape serial, exact attack ID,
current and capped HP, public damage envelopes, board modifiers, and option
fingerprint; emit the lowest-position semantic Cape option; on the next novel
callback revalidate the whole snapshot and emit only the stored attack ID;
then clear. Duplicate callbacks return the cached action without advancing.
Missing/duplicate serials, option mutation, unexpected board change, rollback,
turn/seat/result/new-game transition, or any unsupported calculation clears
and delegates fail-closed. Both logical seats, duplicate options, reset,
rollback, and parent-identical negative transactions are required.

Mandatory negatives include: current attack KOs or ends the match; return
damage is already below current HP or still reaches capped HP; return attack
needs a hidden attachment, switch, evolution, chance, or dynamic text; Active
  already has a Tool; Cape has zero or multiple materially distinct options
  targeting the certified attacker; the stored attack disappears or changes
  after Cape; protection,
status, Stadium, Weakness, or Resistance is unsupported; and every frozen
H1/H2/H4/H5/H6/H7-A/Bench transaction. `88507294:38` remains the explicit
H7-B negative where an invested promotion enables a visible current-turn KO.

## Qualitative failure hypothesis and regression risks

Observed policy failures are decision-local:

- immediate attack score can outrank a same-turn defensive setup action even
  when the setup preserves the exact attack and crosses a public survival
  breakpoint (`88643491:77`);
- forced-promotion target scoring ties all Duraludon at `8,000` regardless of
  Energy investment (`88507294:73/77`);
- generic damage scoring prefers a Prize now over a possible Active lock, but
  the proposed lock is not certifiable from public state in the seven
  decline-KO rows.

The primary Cape regression risk is spending the unique ACE SPEC Tool on a
non-ex attacker when a later target would be more valuable. The public
survival improvement is exact, but the opponent may attach into a larger
attack, gust around the capped Active, decline to attack, or otherwise choose
a line not captured by the current payable envelope. The mechanism therefore
must remain narrow and soft. H7-B has the additional risk of forfeiting
current damage and stranding a zero-Energy Active; its two callbacks are from
one game, so pattern confidence is low.

Nothing in these tactical rows distinguishes deck construction from draw
variance for the separate Metal/evolution drought losses. The new Cape state
is a policy-ordering observation; the unconverted harmful-KO rows remain a
mixture of policy hypothesis, hidden-access uncertainty, and opponent
strength.

## Raw rows for Sol-Ultra quantification

No frequency or outcome delta is inferred here. A numerical evaluator should
use the raw replay files above and these exact rows:

- recommended Cape mechanism:
  `episode_88643491_replay.json`, seat `0`, rows `73-77`, with first proposed
  difference at `77`; quantify the parent attack against the exact
  `Cape -> same attack` transaction and retain row `75` as an ordering control;
- H7-B soft rows:
  `episode_88507294_replay.json`, seat `0`, rows `37-41`, `73-74`, and
  `77-78`; rows `73` and `77` are positives and row `38` is mandatory
  parent-identical;
- insufficient harmful-KO/target rows:
  `episode_88417236_replay.json:45`,
  `episode_88399026_replay.json:122`,
  `episode_88096405_replay.json:98-103`,
  `episode_87911107_replay.json:97-99,113-117`,
  `episode_88391698_replay.json:73-81`, and
  `episode_88134743_replay.json:55`;
- covered-control rows are the 16 entries in the frozen-owner table and must
  remain semantically parent-identical unless their already-owned mechanism is
  the subject of a separate experiment.

Any frequency, paired outcome, seat sensitivity, regression, or uncertainty
claim belongs to a Sol-Ultra numerical evaluator using those raw paths. This
audit makes no numerical pass/fail judgment.
