# Root-verified evidence for the next isolated rule

## Exact live parent

- Submission: `54841997`
- Source: `candidates/alakazam_exposed_dudunsparce_run_away_ready_alakazam_ko_transaction_v1/main.py`
- Source SHA-256: `CB52F1737417EAEEAEF226CFF79ABD4FA58119E3F2AF1D448DFBE5D68722E213`
- Rollback parent SHA-256: `FB739274DDD5410251B0E9B5B21663D2E87328DBCEDA99AC1D68E2438EB47390`
- Current status at 11:02 JST: `COMPLETE`, public `7-6`, exact score `653.2527636938034`, UTC quota `1/5 used`, `4 remaining`.
- Root both-seat shadow over validation plus thirteen public games: `1,861` callbacks, `0` invalid, `0` candidate-parent action differences, `0` Run Away latch starts. The new overlay has therefore not fired in any observed live state, and score movement is not attributed to it.

## Old-parent losses, mechanically verified

Every listed replay was re-executed with its exact submitted source. Across all twelve old-parent loss replays inspected so far, recorded actions were reproduced, actions were legal, the previous direct-terminal overlay did not activate, and there were no source-parent action differences. Qualitative causal labels remain hypotheses, but the listed public decision facts were checked from raw rows.

### Independent high-confidence three-prize Active KO misses

1. `86974207`, Mega Lucario, step `77`, turn `5`: Active Alakazam had Telepath Psychic Energy and hand `19`; opposing Active Mega Lucario ex had exactly `380` HP remaining and was worth three prizes. Powerful Hand option `27` was legal and exactly KO'd it. The parent instead attached Lucky Helmet, reducing the hand below the KO threshold. The same exact KO was declined again at step `81`.
2. `86981695`, Mega Lucario, step `138`, turn `9`: opposing Active Mega Lucario ex had `40` HP and was worth three prizes. Immediate Powerful Hand option `8` was legal. The parent instead played Boss, selected one-prize Lunatone, and KO'd that target.

These are two independent public paths with the same invariant: a currently available, statically certifiable Powerful Hand KO of a three-prize Active was abandoned for an optional hand-spending action.

### Other high-confidence or medium-high public misses

- `86975174`, step `21`: Boss was played with no attack option or lock conversion while Hilda was legal and no attacker was ready; the next action ended the turn.
- `86978513`, step `37`: attached a second Psychic Energy to stranded Active Dudunsparce instead of the hypothesized evolve / Run Away / promote / attach / attack route; first Powerful Hand was delayed to turn `9`, then deck-out.
- `86980154`, step `29`: promoted the only field Abra rather than expendable Dunsparce when public Cosmic Beam 70 KO'd either; attacker-line loss was amplified by prize placement.
- `86981074`, step `84`: attached Enriching Energy to energyless Active Alakazam although Telepath Psychic Energy was simultaneously legal on the same target; the Colorless attachment prevented attacking that turn.
- `86982778`, setup step `3`: chose 70-HP Psyduck Active over 110-HP Genesect; public Cosmic Beam 70 immediately KO'd Psyduck and the board collapsed.
- `86985056`, steps `28` and `30`: twice evolved an unenergized Abra instead of the only Telepath-energized Abra while Kadabra supply was scarce and no ready attacker existed; after the Active KO, only unenergized Kadabra could be promoted.

### Lower-confidence or opponent-dominated rows

- `86975805`: Dawn over Hilda left Active Alakazam unenergized before an observed Stage-1 KO route, but later Team Rocket effect prevention and deck-out dominate.
- `86977398`: Poffin selected two Abra over Psyduck into public Duskull; later Cursed Blast plus Jetting Blow converted the fragile board.
- `86979616`: no certified policy miss after Unfair Stamp plus Dragapult attacker attrition; all visible draw engines were used.
- `86984483`: forced lone Fezandipiti ex opener and Mega Lucario tempo dominate; a Rare Candy conversion row is only low-confidence.

## Evidence identities

- Early-two report SHA-256: `F542346AC8929ABCC59C5A74372518B9CC1CA35B5AAE25A3A83F413250F7411E`
- Early-two raw audit JSON SHA-256: `6DCC9C4CD4999EE0A5D178C98161D400EAFD0E75BBDC5560E2DC1452F332C69A`
- Late-two report SHA-256: `0EB478E05377CA77C4CAC0ADEFAAEED43EF863404A7C7D918FC50BFCD9B71C7B`
- Late-two raw audit JSON SHA-256: `C97A79A95BEFA47648A958D9BC28B358B4D0CA264CE4CBCCC569A77015BB68E1`
- New16 set A report SHA-256: `D5FE0F4F89621B628664343E6C0C7E03470304F8B3AFFB4CE23FF83A95630407`
- New16 set A decision TSV SHA-256: `327FDBF78BFA95A3E45B1C7726FD773A61F5F1BF2D504D801D783C2B330D74A7`
- New16 set B report SHA-256: `97ABCA2AF2537A9882D152B7BFAC17D6C1615502EC93CAB60856B46255950E42`
- New16 set B shadow JSON SHA-256: `F281666BFD5FA42EFED40CC8B1225FD0C41882FF433911353528679832276BE5`
- Current public-fourteen root shadow report SHA-256: `A71FAB4F28F9835CFB64314F3DDECED2658DE2ECA60D51324420BD3B21BB1E3D`

## Current-submission loss evidence

- `86987527`, Kangaskhan-Crustle: at Enhanced Hammer step `62`, the policy removed benched Crustle's Mist Energy. Removing the Active 130-HP Crustle's unique Mist instead would have left hand `7`, suppressed Boss, and certified `140` Powerful Hand counters. This is a high-confidence local target/transaction error, medium-confidence game flip.
- `86988084`, Archaludon: fragile four-Abra setup and late unenergized-Alakazam sequencing; opponent had a ready backup and one prize, so no narrow high-confidence game flip was established.
- `86990847`, Dragapult: root re-execution covered `70` target callbacks with `0` recorded mismatches, invalid actions, or Run Away latch starts. At step `42`, the policy attached a second Psychic Energy to damaged Active Dudunsparce instead of the public `attach bench Alakazam -> Run Away -> promote -> Powerful Hand` KO transaction. At step `67`, it missed a separate `attach Active -> Flip the Script -> exact 320 Powerful Hand KO` transaction. Root audit SHA-256: `94391F1B0497A6E66B3DAFAC2C1436E99BD254F3571DBAAE34342A2F089F3FA8`.
- `86991907`, Archaludon: Boss selected free-retreat, energized Cinderace instead of unenergized Retreat-Cost-2 Duraludon, so no turn was bought. The later inherited Active-Psychic-KO transaction worked. The two Archaludon losses share slow tempo but not one narrow mechanism, so they do not outrank repeated exact KO misses.
- `86992980`, Kangaskhan-Crustle: at the analogous Hammer prompt, the Active had two Mist Energy. Removing either one left protection, so a single Hammer could not certify an immediate KO. This does not repeat the unique-Active-Mist invariant from `86987527`.
- `86993519`, Mega Lucario: Hero's Cape set the Active to `440` HP. Available Powerful Hand counts were `320/300` on turn 7 and `360` on turn 9; no immediate three-prize Active KO was available. This does not repeat or contradict the exact guard proposed from `86974207/86981695`.

Current-audit identities:

- `86987527/86988084` report SHA-256: `F9D4B407667461EC2B0EA0B4112C0C6628FA8BEE48E243729D4FAE2278BDBA7E`
- `86987527/86988084` raw decision CSV SHA-256: `704B9A482835E3CEB9CC299182B5FABB74134FD06183BD13663CF12A3E4150F1`
- `86991907` report SHA-256: `E177D4E03D8D169D024FAC3120AC6C28932710B7B01435266F2971D4DEEE3AB6`
- `86991907` raw decision CSV SHA-256: `2169D22BBD6A2CADD86F9BCB8342B0DCF961F45D43CFE17D55F8D90E38584D71`
- `86992980/86993519` report SHA-256: `89F080FA53CC0C0024E49F770E5F106173CC75B69760EC1FB91877565DAEB871`
- `86992980/86993519` raw decision CSV SHA-256: `8D6CC1853FF9592EE704D1A15B8AB5B0E03A8608D234A3A1183996097BA44111`

## Explicit competing hypotheses for one-rule selection

1. **Certified immediate Active three-prize Powerful Hand guard.** Two independent direct misses (`86974207`, `86981695`). Adapt the existing exact direct-terminal certificate but require `prize_count(active) == 3`; attack before any optional hand-spending or Boss action. Latest Mega Lucario loss must remain a negative because `360 < 440`.
2. **Attach-first exposed-Dudunsparce KO transaction.** Current Dragapult loss `86990847` step `42` had an already evolved, unenergized bench Alakazam, Telepath Energy in hand, unique Run Away, and a certified post-draw KO. Extend the current transaction with `attach bench attacker -> Run Away -> promote -> attack`. Old `86978513` is an analogous family but additionally requires evolving Kadabra first, so it is not the same narrow predicate.
3. **Active attach plus fixed-draw KO transaction.** Current Dragapult loss step `67` had `attach Active -> Flip the Script -> exact 320 KO`; one direct state only.
4. **Unique-Active-Mist Hammer transaction.** One direct state (`86987527`); latest Crustle loss is a certified two-Mist negative.

The judge must select exactly one. It should explicitly weigh repeated causal support and low regression risk against the user's request to improve complete multi-step attack conversion rather than accumulate replay-specific one-action exceptions.

## Strategy-judge constraints

- Select exactly one coherent deterministic public-state rule from the exact submitted source `CB52...E213`; do not stack unrelated fixes.
- Prefer a repeated causal invariant over a one-replay exception.
- Replays may diagnose public state and resource/prize sequencing only; do not imitate recorded actions or model opponent policy.
- Fail closed on hidden effects, ambiguous target identity, attack modifiers, status, protection, or multi-prompt uncertainty.
- The new rule must retain the existing Run Away transaction and every historical overlay without changing unrelated states.
- Candidate implementation must use a newly spawned Fast `ptcg_candidate_worker`; subagents never write to Kaggle.

All current loss audits in this selection cutoff are complete. Later episodes, if any, are a separate future-evidence set and must not be silently folded into this frozen selection.
