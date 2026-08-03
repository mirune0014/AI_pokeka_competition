# Cumulative fixed-760 changed-trace qualitative audit

Date: 2026-07-30 JST  
Scope: exactly the four outcome-neutral paired traces assigned by Root; read-only
except for this report and its checksum.

## Evidence authority

- Cumulative candidate `main.py`:
  `BE8C67E387CE4F36344A4B0DE610CAB9976BB07EE49200997D35CCC6C5DBF18A`.
- Exact historical-Silver parent `main.py`:
  `F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E`.
- Integration selection:
  `2797D1C3B590E369FF3B38B20D2783ADAF1223FB0056759AAAEE69AFC453D942`.
- Fixed-760 combined CSV:
  `B58EBC8CF088B9B740651E8058478838D27EB1D0205A1E8CFB4C303276340BB4`.
- Mega Lucario opponent source used only to verify its attack choice:
  `meta_agents/mega_lucario_public_simple/main.py`,
  `A5732DD50FA0F0BC872B6CFC92227B9A61D48F989D97BB282C06F9509E68158F`.

All trace paths below are under
`autonomous_gold_20260715/implementation/archaludon_cumulative_public_hierarchy_after_search_aware_v1/fixed760_raw`.

| Case | Baseline trace SHA-256 | Candidate trace SHA-256 | CSV outcome / callbacks |
|---|---|---|---|
| historical_silver, seat 0, seed 271828201, game 0019 | `352D7C4D84DEE6789CAB979B135673EE091A1C7F9CC32D2C6F4788C4F109C8F6` | `96BE19FE6E3DD42069697F45AFD2A21D74418C50133080435F6500D08340E97A` | parent win / candidate win; 129 / 127 |
| arch_shumpei, seat 1, seed 271958328, game 0015 | `59137753A68475C03FD7A3C5154D5ACE10D44ADF0F414DFCFD802A4BDC237463` | `081F5FBBC944F9F5886A1361E57977A71572FDED3F3E59E3B6C457831D09732D` | parent win / candidate win; 126 / 130 |
| mega_lucario_public, seat 0, seed 271958329, game 0016 | `C4B59DF233D7BADEED59D027E7E49E9C3FFBFAD9E535AB580F75237AEF7BFF61` | `2D55857E674DE036AD50F0B0C93563496FA662563864EBDC3F9D969F0E0D9F95` | parent win / candidate win; 76 / 94 |
| mega_lucario_public, seat 1, seed 271958318, game 0005 | `A18A6849CDE6770755AB1F0ECCB8A7C079B024A4188CC5C8B613DAA25843FE16` | `61418278C0D1CE314FCB70F2056194A0AE4C8BD42C92F971D226C5853F288DAC` | parent win / candidate win; 85 / 95 |

## Attribution limitation

The fixed traces were written without options, scores, or drained cumulative
telemetry. Compact logs also omit serials, while the snapshot omits stadium,
conditions, `supporterPlayed`, and certificate digests. Therefore the raw
JSONL plus source cannot prove the runtime `winning_rule_id`, exact serial
binding, suppression list, or absence of a collision. Attribution below is a
strong semantic inference made at the first divergence, not a telemetry proof:
H4 is the only integrated rule that replaces an inherited parent Attack with
Boss into a unique nonterminal higher-yield KO, and H3 is the only rule that
owns this Ultra Ball discard/search/Turbo Flare transaction.

## Observed decision states

### 1. Historical Silver seat 0: H4 Boss-to-Duraludon

- First divergence: JSONL row/step 104 (file line 105), turn 12, Main.
  Parent `[4]` is inherited Metal Defender `253`; candidate `[2]` plays
  Boss's Orders `1182`.
- Public state: our Archaludon ex had 400 HP, three Metal and Hero's Cape,
  with three Prizes remaining. Opposing Active Archaludon ex had 210/400 HP,
  two Metal and Cape; the only Bench target was Duraludon `169` at 130 HP.
- Candidate then selected that Duraludon, used the same Metal Defender, KO'd
  it, and took one Prize. The parent instead dealt the Full Metal Lab-reduced
  190 to Active, leaving it at 20 HP.
- This matches the H4 source certificate locally: inherited attack identity
  `253`, current yield zero, unique Bench KO yield one, and nonterminal
  target yield below the three remaining Prizes. The visible
  Boss -> target -> same attack transaction completed without an apparent
  stage or target breach.
- Opportunity cost: the candidate spent Boss and abandoned 190 damage on a
  two-Prize Active. The parent converted that chip into the Active KO on turn
  14 and later Bossed a Duraludon for its last Prize; the candidate took the
  Duraludon first and did not finish the Active until turn 16. Both won on
  turn 16. This is valid mechanism exercise, not evidence that the diversion
  is stronger.

### 2. Arch Shumpei seat 1: H4 Boss-to-Duraludon

- First divergence: row/step 49 (line 50), turn 8, Main. Parent `[3]` is
  Metal Defender; candidate `[0]` is Boss.
- Public state: our Archaludon ex was 400 HP with three Metal and six Prizes
  remaining. Opposing Active Archaludon ex was 210 HP with one Metal; the
  only Bench target was 130-HP Duraludon.
- Candidate completed Boss -> Duraludon -> Metal Defender, taking one Prize.
  Parent attacked Active for 190 and left it at 20 HP. This is again locally
  consistent with H4 and the visible transaction completed.
- Opportunity cost was clearer here: parent converted the damaged
  Archaludon ex for two Prizes on turn 10; candidate did not take that Active
  until turn 12. Candidate also consumed an early Boss and later played
  another Boss on turn 18, whereas the parent retained the early Boss line.
  The eventual shared win does not erase the lost Active chip or Supporter
  flexibility.

### 3. Mega Lucario seat 0: H3 Ultra Ball discard transaction

- H3 likely armed at step 22 when both agents played the same Ultra Ball.
  The first differing action is row/step 23 (line 24), turn 2, Ultra Ball
  discard context: parent `[2,4]` discarded Basic Metal `8` plus Boss;
  candidate `[0,4]` discarded Jumbo Ice Cream `1147` plus Boss.
- The source's H3 v2 discard certificate explicitly chooses one Jumbo plus
  one Boss only when the lone Active Cinderace is undamaged and no currently
  legal Turbo Flare target can be KO'd by gusting. The trace shows Cinderace
  at 160/160 with no Bench, opposing Riolu at 80 HP, and Turbo Flare's 50
  damage nonlethal against every visible 80/110-HP target. Thus the public
  portion of that certificate is consistent.
- Candidate then searched Duraludon, benched it, used Turbo Flare `965`, and
  attached three Basic Metal to that exact Bench line (steps 24-30). No
  apparent transaction-stage or target breach occurred.
- Resource opportunity cost: candidate preserved the hand Metal and later
  manually attached it, reaching four Energy on Archaludon ex. Parent put
  Metal into discard, used Assemble Alloy to reach five Energy, and retained
  Jumbo. Parent later used that Jumbo on turn 6 for an observed +80 heal;
  candidate no longer had that option. Candidate subsequently lost an
  Archaludon ex and followed a longer route, although both won.
- Fact versus hypothesis: loss of the later heal option is directly
  observed. Calling the saved Metal surplus in this game is a reasonable
  qualitative inference because both lines exceeded Metal Defender's
  three-Energy cost. Attributing every later board difference to the discard
  is lower confidence because the different Ultra Ball discard also changes
  the shuffled future.

### 4. Mega Lucario seat 1: H4 Boss line exposes a self-lock gap

- First divergence: row/step 41 (line 42), turn 6, Main. Parent `[5]` is
  Metal Defender; candidate `[2]` is Boss.
- Public state after Jumbo healing: our Archaludon ex was 140 HP with three
  Metal and five Prizes remaining. Opposing Active Mega Lucario ex was
  340 HP with two Fighting Energy; its only Bench target was 110-HP Lunatone.
  The immediately preceding opposing attack was Mega Brave `983`.
- Candidate completed Boss -> Lunatone -> the same Metal Defender, taking
  one Prize. Parent instead hit Mega Lucario for 220, leaving it at 120 HP.
  The action sequence is locally H4-certificate-consistent and mechanically
  complete.
- The next opposing turn is the blocker. On the parent branch Mega Lucario
  used Aura Jab `982`, dealing the Full Metal Lab-reduced 100 and leaving our
  Archaludon ex at 40 HP. On the candidate branch the returned Mega Lucario
  used Mega Brave `983`, dealt 240, KO'd that two-Prize Archaludon ex, and
  discarded its three Metal. The opponent source scores Mega Brave above
  Aura Jab and gives it an additional KO bonus, so Aura Jab on the parent
  branch is evidence Mega Brave was unavailable there, not a voluntary
  lower-scored choice. Bossing Mega Lucario off Active made Mega Brave
  available again on the candidate branch.
- This is a mechanism-first loss despite the eventual candidate win:
  H4's one-Prize diversion released a public attack lock and immediately
  conceded a two-Prize attacker plus three attached Metal.
- Source defect: `_h4_persistent_effects_supported()` only fails closed on a
  prior attack whose text contains `during your opponent` plus a
  damage/attack/Weakness marker. Mega Brave's public restriction is
  `During your next turn, this Pokémon can't use Mega Brave`, so the H4
  certificate admits a gust that changes the legal next-turn attack set.
  This is a certificate completeness/safety defect, not a failure to execute
  the written Boss transaction.

## Failure hypothesis and practical-live answer

Observed mechanics separate the failures from deck construction and variance:
the deck is identical, the first differences are deterministic policy
actions, and all four transactions reach their intended immediate actions.
Cases 1 and 2 expose the known H4 Boss-versus-Active-chip opportunity cost.
Case 3 exposes an H3 heal-versus-Metal resource trade. Case 4 is qualitatively
stronger: it demonstrates a public, mechanism-caused attack-lock release and
an immediate adverse Prize/resource exchange.

**Yes: case 4 is a qualitative blocker to an exploratory live probe of this
exact candidate hash.** Outcome neutrality is not sufficient because the
candidate's rule caused the dangerous state transition. There is no observed
mechanical transaction or target-binding breach in the four traces, but
collision/precedence correctness cannot be certified from these telemetry-free
JSONLs.

## Narrowly testable countermeasures

1. Make H4 fail closed when the opposing Active is under a public
   self-restriction or attack lock that can be changed by switching, including
   Mega Brave `983`. Recreate case 4 in both seats and with serial/option
   permutations: the locked fixture must retain the parent's Active attack;
   an otherwise identical no-lock control must still complete the H4 Boss
   transaction.
2. Add a focused H3 resource fixture for case 3: when saved Metal is already
   surplus to a guaranteed three-Energy line and Jumbo is the only heal,
   require fail-closed parent behavior or a certificate that proves the heal
   has no current survival value. Keep a paired control where the retained
   Metal is genuinely attack-completing so setup coverage is not suppressed.

Regression risks are overbroad attack-text matching that disables legitimate
H4 conversions, and an H3 surplus guard that starves setup when Metal is
prized or otherwise unavailable. Both countermeasures need exact-engine,
both-seat positive and negative fixtures before another practical decision.

## Raw rows for independent quantification

Use the combined CSV keys above and these one-indexed JSONL lines; do not infer
frequency from this four-game set.

- Case 1:
  baseline `historical_silver/...p0_baseline_a/game_0019.jsonl` line 105 and
  lines 115-129; candidate `...p0_candidate/game_0019.jsonl` lines 105-108
  and 117-127.
- Case 2:
  baseline `adjacent_population/...arch_shumpei_p1_baseline_a/game_0015.jsonl`
  line 50 and lines 53-126; candidate
  `...arch_shumpei_p1_candidate/game_0015.jsonl` lines 50-53, 69-70, 105-109,
  and 124-130.
- Case 3:
  baseline `...mega_lucario_public_p0_baseline_a/game_0016.jsonl` lines
  23-31, 48-49, and 76; candidate
  `...mega_lucario_public_p0_candidate/game_0016.jsonl` lines 23-31, 47-50,
  and 76-77.
- Case 4:
  baseline `...mega_lucario_public_p1_baseline_a/game_0005.jsonl` lines
  41-44; candidate `...mega_lucario_public_p1_candidate/game_0005.jsonl`
  lines 41-48.

The evaluator should recompute per branch: semantic first action, Boss plays,
attack IDs, immediate Prize movement, later KO of our attacker, attached
Metal lost, and callback total. Any broader frequency claim requires the
corresponding raw trace paths outside this deliberately bounded audit.
