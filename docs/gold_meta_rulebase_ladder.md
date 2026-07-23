# Gold Meta Rule-based Ladder

Last updated: 2026-07-14 JST

## 現行の育成方法

このladderは純ルールベースで進める。replay由来の行動一致、相手proxy、
residual RLは候補の主目的・昇格条件にしない。Gold/live replayは正確な60枚、
デッキセオリー、有力な選択肢、自提出の失敗局面を確認するための補助証拠とする。

各trackでは、過去のArchaludon育成と同じ手順を使う。現在の最強baselineを
壊さず、デッキ全体の基本動作と実戦ログの両方から一つのルール仮説を選び、
隔離実装する。過去にSilver水準へ到達した完全実行可能なArchaludonを主アンカー
とし、他の実績済み完全エージェントをanti-regression populationとして用いる。
同一seed・両seatで比較し、勝率だけでなく盤面形成、控えの準備、資源、攻撃継続、
賞品交換、妨害、詰め、変更局面を確認する。負け筋対策だけにも、勝ち筋指標だけにも
偏らない。

## 目的

現在の金圏で確認できる主要デッキを、ファミリーおよび公開された完全な
60枚単位でローカルエージェント化する。各エージェントは既存の汎用ルールを
流用するだけでなく、対応する上位リプレイから専用ルールを作る。

完成したデッキは次の順に昇格させる。

1. 完全な60枚と実行可能な専用ルール
2. デッキセオリーを反映した完全実行可能な専用ルール
3. 固定seedのローカル対戦で既存simple mimicを上回る
4. Kaggle validation成功
5. 銅圏: 最新leaderboardでrank 500以内を複数checkpointで維持
6. 銀圏: 最新leaderboardでrank 100以内を十分な公開試合後に維持

一時的な初期scoreだけでは昇格しない。原則として公開30試合以上を集め、
重大なexecution errorがなく、6時間以上の推移を確認する。明確な初期失敗は
提出ループ正本に従って早期置換してよい。

## 現在の金圏分布

rank 1-20に帰属できた31 seatの内訳は次のとおり。

| Family | Gold seats | Decisions | 主なvariant |
| --- | ---: | ---: | --- |
| Alakazam / Psychic | 17 | 1,391 | `2fb3a358...`、`57050d20...`ほか4種 |
| Marnie / Grimmsnarl | 4 | 400 | Sota、Gonsaku、Kazuki、tw_shinの4種 |
| Cynthia / Garchomp | 4 | 324 | `1106a567...` |
| Kangaskhan / Crustle | 3 | 191 | MPGaming `90afb5a7...`、Alberto `7c1af5a0...`。旧分類名はGreat Tusk |
| Archaludon / Metal | 2 | 183 | Shumpei旧版。現行版は別途89 public games |
| Okidogi / Barbaracle | 1 | 105 | btk15049 `bcd9a7fb...` |

1250点以上の極端な上位sliceはAlakazamとKangaskhan/Crustleだけで構成されるが、
これは金圏全体ではない。金圏全体のコピー対象には上記6 familyを使用する。

## 実装トラック

固定Goldカタログには主要6 family、完全60枚ハッシュ15種がある。これに
同じ60枚でも観測時期の異なるShumpei現行方策を加え、合計16 policy trackを
省略せず育成する。Shumpeiの2 trackは同じdeck hashだが、方策の時点が異なる。
表の順序は着手優先度であり、対象から除外する順序ではない。

| Order | Track | Deck copy | Policy status | 現在の課題 |
| ---: | --- | --- | --- | --- |
| 1 | Shumpei current Archaludon `54588240` | 完了。Energy13、Relicanth2、Articuno1 | 未完。旧simpleはCinderace前提 | 89 public gamesから専用ルールv2を実装 |
| 2 | Alakazam `2fb3a358...` | 完了可能。8 Gold seats | simple mimic多数 | 1 variant専用方策へ統合し、別episode holdout |
| 3 | Alakazam `57050d20...` | 完了可能。5 Gold seats | simple mimic多数 | variant 1と混ぜず独立方策として評価 |
| 4 | MPGaming Kangaskhan/Crustle `90afb5a7...` | 完了可能。Gold 2 episodes | exact名のmimicなし | wall/hand-control/耐久順序を専用化 |
| 5 | Cynthia nasuo445 `1106a567...` | 完了 | exact-source simpleあり | 4 Gold seatsを使ってrule v2化 |
| 6 | Marnie Sota `e66f89f6...` | 完了 | simpleのみ | style固有ルール。全Marnieへ一般化しない |
| 7 | Marnie Gonsaku `e6b3dd20...` | 完了 | simpleのみ | 独立holdoutを維持 |
| 8 | Marnie Kazuki `d256df2c...` | 完了 | simpleのみ | prize/retreat/heal順序を専用化 |
| 9 | Marnie tw_shin `bd7cf5a5...` | 完了 | simpleのみ | Great Tusk対面を含む固有方策 |
| 10 | Okidogi btk15049 `bcd9a7fb...` | 完了可能 | simpleあり | attacker維持とBarbaracle順序を専用化 |
| 11 | Alberto Kangaskhan/Crustle `7c1af5a0...` | 完了可能。Gold 1 episode | 未確認 | MPGaming版とはカード差のある独立variant |
| 12 | Alakazam Michael Long `77feb703...` | 完了可能。Gold 1 seat | 未確認 | 主要2 variantと混ぜず少数variantとして育成 |
| 13 | Alakazam THIRD PTCG `889dfdc6...` | 完了可能。Gold 1 seat | 未確認 | 同一styleの別hashと独立して差分を抽出 |
| 14 | Alakazam THIRD PTCG `9c77ed61...` | 完了可能。Gold 1 seat | 未確認 | `889dfdc6...`とのdeck/policy差を保持 |
| 15 | Alakazam capbloo `edc3cef7...` | 完了可能。Gold 1 seat | simpleあり | 少数variant専用holdoutで評価 |
| 16 | Shumpei catalog Archaludon `4e2473ad...` | 完了。Gold 2 seats | 旧simpleあり | 同じ60枚の旧方策snapshotとして比較対象にする |

完全ハッシュ一覧は次のとおり。

- Alakazam: `2fb3a358e03c652bf2b6259ad0d47137116c599122d28d116799eb54c4150a3c`
- Alakazam: `57050d2022e1a26f26930314459d130e8733d58795e72761f0b87d6f89bb4a1a`
- Alakazam: `77feb703512d5e6286f7a7cff8453f98021a2cd57d0f597a818f18a24db30de6`
- Alakazam: `889dfdc6bf51e10450308966719a75d21023130d6c10b5a45aee1a8948290a33`
- Alakazam: `9c77ed610552d734f4fe329de20cb447a625a858bb0f416009c81755ce41edf0`
- Alakazam: `edc3cef70e22e7c84f3d5212e0d4746645c2c035fcbbd4bc27ebb9d1c8d3792d`
- Archaludon catalog: `4e2473ad9c24dbbab8888c5326e6679ef0e89157e6312457256ebc8346bdc574`
- Cynthia/Garchomp: `1106a5674391397fb0f624f842d2e22261ef41a7af102a3b4e4e3fd58546a878`
- Kangaskhan/Crustle: `7c1af5a04dee97680b6448337595eae4839c972148cc8da87d7d8b10fa4243d6`
- Kangaskhan/Crustle: `90afb5a7dd6805ba5fdd048b227e0fdcbe7dc8516b2ba5016568461210df8be9`
- Marnie/Grimmsnarl: `bd7cf5a519f27cf276f9c6aec17d916b653d5d229866487a00a3f6585d385a9e`
- Marnie/Grimmsnarl: `d256df2c0c2b0008d003b467538b4f9a688d61a858c040f16b8aa5664fa072a9`
- Marnie/Grimmsnarl: `e66f89f69b534f9923139877e1d1089e25a3d77a36630506acba7ea5ee2ba41d`
- Marnie/Grimmsnarl: `e6b3dd205d1c862f7ebe731b9040e8382e57000507ba3f1bee2a47b7c2e3daf9`
- Okidogi/Barbaracle: `bcd9a7fb5655ef37ce50108c53ce0918848a01e002f6d61f329909af0e42bb8b`

二次検証familyとして、Starmie/Froslass、Mega Lucario、Dragapult、
Iono/Bellibolt、Hop/Trevenantを保持する。これらは既存のローカル対戦相手を
anti-regressionに使うが、現在のrank 1-20主要6 familyより先には実装しない。

## 共通合格条件

各trackは次を満たすまでKaggleへ提出しない。

- source replayと完全に一致する60枚multiset
- acting-playerが実際に利用できる情報だけを利用
- setup、supporter、search/discard、evolve、attach、attackを含む基本動作を局面単位で検証
- replay一致率ではなく、固定populationで既存baseline以上の絶対強度を示す
- illegal action 0、import error 0、max-step anomaly 0
- sourceと異なる主要familyにも固定seedでanti-regressionを実施
- archiveのroot構造、agent entrypoint、deck 60枚、source/package equalityを確認

同じfamilyでもdeck hashまたはstyleが違う場合は別trackとして扱う。
特にMarnieの4 styleを1つの平均方策へ混ぜない。

## 現在の着手内容

Shumpei current Archaludonをtrack 1として実装する。

- 公開履歴: 89 public games、50-40、latest fetched score 1067.20
- deck: Duraludon4、Archaludon ex4、Relicanth2、Articuno1、Metal13、
  Stretcher4、Ultra Ball4、Pokegear4、Poke Pad4、Boss4、Carmine4、
  Lillie4、Judge2、Xerosic1、Full Metal Lab4、Hero's Cape1
- 主要motif: 先攻、Duraludon優先setup、Metal discardを作ってAlloy、
  Carmine中心のrefill、2本目のArchaludon維持、Relicanthを実働energy sink、
  Stretcherを次のattackerに使用
- 旧simpleの問題: Cinderace/Explorer前提、ArticunoとCarmine/Judgeの
  明示ルール不足、Relicanth1枚+Ice Creamという古いdeck
- dedicated v2は有効な60枚・実行可能コードだったが、route-awareな進化、
  attach、retreat、Boss、選択context、対面guardを単純scoreへ置換したため、
  11 bucket 132試合で旧simple `101-31`に対し`43-89`となり棄却した。
- v3は旧simpleを土台にし、上記の経路方策を保持したまま、先攻、Articuno、
  Carmine、Judge、Xerosic、Relicanth2、Metal13だけを適応する。

MPGaming Kangaskhan/Crustle trackは正確な60枚とローカル昇格候補まで完了した。
旧分類器はCrustleを含むだけでGreat Tuskと判定していたが、MPGaming/Alberto版に
Great Tuskは0枚である。
MPGaming版のcanonical deck SHA-256は
`ed9cdddb866dbaf9add2600e04edcdc30b7679a623ec2fa1cd13b55d4ce545bf`。
完全60枚はMega Kangaskhan ex 4、Dwebble 4、Crustle 4、Shaymin 1、
Mist Energy 4、Spiky Energy 4、Grow Grass Energy 4、Basic Grass Energy 1、
Buddy-Buddy Poffin 4、Pokegear 3.0 4、Jumbo Ice Cream 4、Switch 4、
Hand Trimmer 1、Hero's Cape 1、Hilda 4、Lillie's Determination 4、
Xerosic's Machinations 4、Boss's Orders 2、Battle Cage 2。
方策はGreat Tuskのmillではなく、Crustleの対ex wall、DwebbleのAscension、
Xerosicの手札妨害、Kangaskhanの耐久・終盤打点を中心に実装する。
Gold 19リプレイから勝ち盤面を測定し、同一seed 600戦でv0-v6を比較した。広い
route/state-machine模倣はsetup・bench・supporter順序を壊し、Gold攻撃判断を
`46/46`一致していたexact-deck v0を下回った。その後、複数line成立後のturn 2に
相手がEnergyをcommitした場合だけXerosicをAscension準備より先に使うv8を隔離した。
開発panelはv0 `374/600`に対してv8 `379/600`、blind holdoutは`378/600`に対して
`380/600`で、11-policy Gold panelも含め合計`+8/1420`かつ対面別回帰0だった。
さらに必須複数選択が`minCount`未満になり得る既存バグを修正し、戦略v8との
1200戦およびGold population 220戦で完全一致を確認した。13-member legality-fix
archiveを準備済みで、次のquota reset後にこの提出版をBronze probeへ進める。

次の実装trackはAlakazam主要variant A `2fb3a358...` とする。deck copy数は多いが、
variantを混ぜないため、variant Aの8 Gold seatを学習・holdoutへ分割し、variant B
`57050d20...`を独立した隣接回帰パネルとして保持してから専用方策を実装する。

## 2026-07-13 現在の昇格状況

Cynthia/Garchomp track 5を現在のlive trackとしている。提出v9 `54630859`は公開10戦で
`5-5`、`551.68`。0-3から5連勝した後にStarmie/Ogerponへ2連敗し、Bronze未到達である。
次候補v11はBuddy-Buddy Poffin後の役割選択だけを明示し、開発720戦`+27`、独立holdout
480戦`+20`、合計`+47/1200`を示した。archiveは準備・検証済みだが、当日枠を消化済みのため
未提出。次回reset時にv9が弱いままならv11を実戦probeし、ArchaludonとGreat Tusk/Crustleの
回帰を重点監視する。銅到達まではtrack 5を継続し、単発敗戦patchではなく、Garchomp主線、
Roserade支援、Power Weight、後続攻撃の成立を合法手・資源・賞品レースと併せて評価する。

### 2026-07-13 Cynthia v12 promotion state

- Live v9 is recovering at 12 public games, 7-5, score 617.35. Its latest
  Dragapult and Mega Lucario wins both formed Garchomp and Roserade support.
- v12 keeps v11 Poffin setup and adds a TO_HAND-only pivot from redundant
  main-line search to Roserade support after two main-line bodies exist.
- Against v11 it scored +8/720 development and 0/480 unused-seed holdout.
  Archaludon improved +6 combined; exact Cynthia was -4 development and 0
  holdout; Great Tusk/Crustle and Ogerpon were -2 combined each.
- v12 matched four changed Gold support-search decisions, had exact duplicate
  controls, and produced no action errors or max-step games.
- Package: `candidate_cynthia_garchomp_nasuo445_v12_support_pivot_20260714.tar.gz`,
  SHA256 `B52DA76B3860299A3F34F4DCFB2E400FC287C33E0776E507BF8EC46559E17B65`.
- Decision: do not replace a recovering v9 now. At the next quota reset,
  refresh the mature live score; use v12 only if v9 remains below Bronze or
  clearly stalls. Track 5 remains active until Bronze and Silver gates.

### 2026-07-13 Cynthia v13 promotion state

- Live v9 is now 21 public games, 9-12, score 549.44. Its latest five games
  were 1-4, so the earlier recovery has clearly failed. Execution is COMPLETE.
- The three new losses do not justify a new matchup patch. v11/v12 already
  change causal Poffin setup decisions in Alakazam and Hop/Trevenant; Marnie
  is action-identical across v9/v11/v12.
- v13 keeps v12 and delays non-final-prize Corkscrew only long enough to take
  the best positive development action with active Garchomp plus Roserade.
- v12 -> v13: +29/720 development and +15/480 untouched blind, total +44/1200.
  Both seats improved; controls were exact with zero errors/max-step games.
- A separate trace panel improved 84 -> 95/160 and shifted attacks from
  Corkscrew Dive toward Draconic Buster while also making first evolution,
  first attack, and first prize earlier on average.
- Package:
  `candidate_cynthia_garchomp_nasuo445_v13_corkscrew_development_order_20260714.tar.gz`,
  SHA256 `97E9092DC7387BABE564E5573DBA2DEB18183D608C683113B5AE769A18B659C7`.
- Decision: v13 supersedes v12 in the next-reset queue. No July 13 slots
  remain. Refresh v9 at/after 09:00 JST and submit v13 unless the fresh state
  materially overturns this mature weak diagnosis. Track 5 remains active.

### 2026-07-13 Cynthia v13 flip audit and freeze

- All 83 gain flips and 39 loss flips were reviewed against the paired
  development and blind manifests. In 38/39 losses, the first divergence was
  the Corkscrew ordering rule; 19 deferred an immediately visible KO.
- The same behavior is not uniformly harmful. Six of eleven representative
  gain retraces also deferred an immediate KO and then won through stronger
  development. The gains include Cynthia, Starmie, Alakazam, Mega Lucario,
  and Marnie states and use benching, evolution, attachment, abilities, and
  Poffin actions rather than one narrow action type.
- Therefore an immediate-KO exemption would remove documented wins, while a
  matchup-only exception is not supported by the public state. Great Tusk
  deck-out pressure and Marnie prize pressure remain live risks, but there is
  no safe repeated separator yet.
- Decision: do not manufacture v14 from the negative flips. Freeze v13 as the
  next-reset probe because it remains +44/1200 on two broad panels and +11/160
  on the independent route trace. Evaluate both intended-board conversion and
  ordinary rule quality after submission: setup, resources, prize tempo,
  attack continuity, matchup spread, and repeated decision errors.

### 2026-07-13 Cynthia v13 live-Kang adjacent check

- Live v9 reached 24 public games, 11-13, score 566.996. The new sequence was
  a loss to DapperOctopus Kangaskhan/Crustle followed by wins over
  Hop/Trevenant and Cynthia/Garchomp. This is a small recovery, but the mature
  score remains below Bronze and does not overturn the replacement case.
- v13 differs from v9 on nine decisions in the Kangaskhan loss, including
  repeated turn-31-to-43 Corkscrew deferrals as the deck falls from seven to
  one card. This is a real timing risk, not sufficient evidence for a patch.
- On an unused 400-game broad Dung-style holdout, v12 296 -> v13 299. Using
  DapperOctopus's exact public 60 cards with the Dung policy produced
  146 -> 155/240, with +4/+5 by seat, exact duplicate controls, and no errors.
- Across all 122 paired flips, turn/full-bench/deck-count gates did not safely
  separate gains from losses. The live-aligned turn>=31, full-bench,
  deck<=8 gate still touches a documented gain and has not recovered a paired
  loss. No v14 is accepted.
- Archive re-audit confirms 13 members, 12 files, `main.py` first, 60 deck
  rows, source equality, Python 3.11 compile, no-`__file__` import, and a
  four-game runtime smoke with zero errors. v13 remains the next-reset probe.

### 2026-07-13 Cynthia v13 live exposure baseline

- Live v9 moved to 27 public games, 12-15, score 561.229 after a Mega Lucario
  win followed by Alakazam and Mega Lucario losses. This is renewed decline,
  not recovery, and strengthens the next-reset replacement decision.
- On all 27 public replays, v13 changes 86 of 1,674 decisions in 22 games.
  The change surface is 44 MAIN decisions, 25 Poffin/TO_BENCH selections, and
  17 TO_HAND selections; turn bands are 20 early, 24 mid, and 42 late.
- Cynthia accounts for 24 mismatches over 8/10 games; Mega Lucario 12 over
  4/5; Hop 13 over 2/2; Ogerpon 13 over 2/2; Alakazam 5 over 2/2; and the one
  Kangaskhan game 9. Marnie is unchanged. Alakazam changes are setup/search
  only, while Ogerpon, Hop, Lucario, and Kang carry Corkscrew timing exposure.
- Current v9 process baseline over 27 games: wide first attack in 21/27
  (77.8%), first-prize wide line 63.0%, Power Weight-to-Garchomp 63.0%, Poffin
  use 70.4%, median missed attack turns after first attack 0. Wide-first-attack
  games won 47.6% versus 33.3% for thin starts.
- Post-submit evaluation will compare these process metrics plus score,
  matchup results, resource depletion, and late low-deck timing. The candidate
  is broad enough to judge after roughly 20 public games, but replacement
  still requires clear failure rather than one exposed loss.

### 2026-07-13 Cynthia theory audit and v17 experiment

- The live v9 submission is now mature weak at 33 public games, 14-19, score
  549.2219. No games appeared after episode 85693446, and the latest four-game
  sequence was loss, win, win, loss rather than a recovery trend.
- A human-strategy audit was added after confirming that earlier work relied
  too heavily on replay induction. Current guides, the official list, engine
  code, and all four exact Gold replays agree on a Stage-2 midrange plan:
  preserve Gabite search width, establish Garchomp plus Roserade, use
  Corkscrew for tempo, reserve durability resources for the main lane, preload
  a second attacker, and use Buster for conversion rather than availability.
- v13 already covers the first three elements. It does not distinguish Basic
  and Rock Fighting Energy, assign Energy by active/backup role, or gate Buster
  by the resulting prize and continuity state.
- Corkscrew thresholds 5,000 and 4,000 failed development; threshold 3,000 was
  +4/720 development but -5/480 blind with both seats negative. v14-v16 are
  rejected and must not be submitted.
- v17 is limited to Rock-Energy and backup-attacker allocation. Attack scores,
  deck, setup/search, matchup safety, Power Weight, and Spiritomb stay frozen.
  v13 remains the queue fallback until v17 passes both fixed-seed panels.

### 2026-07-13 Cynthia v17 promotion state

- v17 passed development 402 -> 416/720, blind 276 -> 282/480, and an unused
  holdout 272 -> 275/480. Combined delta is +23/1,680 with exact controls and
  zero errors/max-step games.
- Gold agreement improved 145 -> 141 mismatches over 324 decisions. All four
  fixes are intended Rock search/attachment decisions and no prior agreement
  was lost.
- Blind seat 0 was -4, but the holdout was neutral, so that regression did not
  reproduce. Mega Lucario was +1/-3/-2 over development/blind/holdout and is
  undergoing exact-seed component attribution before any narrow exception.
- v17 changes 45/1,942 decisions from submitted v9 over 32 public replays. It
  changes Energy search/attachment and backup allocation without altering the
  deck, attack scores, existing setup/search, Power Weight, or matchup rules.
- Package:
  `candidate_cynthia_garchomp_nasuo445_v17_rock_backup_allocation_20260714.tar.gz`,
  SHA256 `3756036C39C79CD2C9ED483B94FF236FA0BE74FD1B939DB666AFB2DD71D41E80`.
  It has 13 main-first members, exact 60 cards, extracted source equality,
  compile/import/no-`__file__` checks, and a 10-game archive smoke with no
  errors. v17 provisionally supersedes v13 for the next reset.

### 2026-07-13 Cynthia Rock ablation conclusion

- Fresh live state: submission 54630859 has 34 public games, 16-18, score
  565.8767. The last two games were wins, but it remains mature below Bronze.
- v18-v19 removed the bench-backup and active-completion components in stages.
  They scored 102 and 105 versus the v13 Mega Lucario baseline of 106/140 and
  are rejected.
- v20-v21 replaced exact-state ideas with a public deck-theory readiness gate.
  Both tied v13 at 106/140, but retained two known regressions. v21 then scored
  +7/720 development, 0/480 blind, and -4/480 unused holdout. Archaludon was
  -2 in both blind and holdout.
- v21 is rejected despite a +3/1,680 combined total because the holdout and
  repeated Archaludon safety gates failed. v17 remains the packaged next-reset
  probe at +23/1,680 with all three broad panels positive.
- Stop tuning Rock from these exact flips. The next independent Cynthia work
  is Draconic Buster prize conversion with a loaded-backup continuity guard.

### 2026-07-13 Cynthia v22 Buster conversion promotion

- Across 38 Gold/live replays, 41 MAIN states had both Cynthia attacks legal.
  v17 chose Buster in 40/41, including all 17 Corkscrew-also-KO states and
  seven of eight non-KO states. The three recorded Busters were all KOs.
- v22 permits Buster only for a Buster-only KO that finishes the game, takes
  at least two prizes, or has an energized bench main-line attacker. It uses
  only acting-player public state and leaves every v17 setup/resource rule
  unchanged.
- Replay gate: 13 approved states chose Buster 13/13; 28 rejected states chose
  Buster 0/28; reconstruction errors zero. Gold mismatch remains 141/324.
- Full paired evaluation versus v17: +20/720 development, +26/480 blind,
  +8/480 unused holdout, total +54/1,680. Both seats improved in all panels;
  all combined matchup deltas are nonnegative; controls exact, zero errors.
- Package:
  `candidate_cynthia_garchomp_nasuo445_v22_buster_conversion_20260714.tar.gz`,
  SHA256 `2644BD391D286A16414083244A4DE3E2F9B40A1D4D321B7C6009037F81C912C3`.
  Thirteen main-first members, exact 60 cards, compile/import/no-file and
  10-game smoke clean. v22 supersedes v17 for the next reset; v17 is rollback.

### 2026-07-13 Cynthia v22 independent confirmation

- A fourth unused-seed broad panel, 202807131, confirmed v22 over v17 at
  302-279/480 (+23). Both seats improved (+11/+12), eight of 12 matchups were
  positive, two neutral, and the two negatives were bounded at -1 and -2.
- An independent 80-game process trace confirmed the intended mechanism:
  attacks 799->836, missed post-first-attack turns 87->67, Buster 274->138,
  Corkscrew 335->504, and wins 35->43. First-attack timing and line width were
  effectively unchanged, so the gain is post-setup resource continuity rather
  than a replacement for the existing setup and ordinary rule layers.
- Live v9 is now 17-18 over 35 public games at 572.3024 after three wins. It
  remains below Bronze, but all July 13 slots are consumed. Keep v22 selected
  for the next reset and do not spend a slot before then.

### 2026-07-13 Cynthia v22 live gate audit

- The full live corpus is 35 public games and 2,160 decisions. Submitted v9
  reconstructs exactly; v17 changes 146 decisions and v22 changes 173.
- The 27 direct v17-v22 differences are exclusively Buster deferrals: five to
  Corkscrew and 22 to play/attach/ability development actions. No setup,
  search, resource-allocation, or matchup rule changed between the two.
- The new reproducible audit tool finds 41 dual-legal states. Candidate v22
  selects Buster in all 13 approved states and in zero of 28 rejected states.
  Rejected states include every Corkscrew-also-KO and non-KO Buster state.
- Current weak live buckets are Starmie 1-3 and Ogerpon 0-3. Do not patch them
  before v22 live evidence: Starmie improved broadly in local panels, while
  Ogerpon was neutral and may require a later deck/general-policy decision.

### 2026-07-13 Cynthia exact-live deck safety

- The former Ogerpon 0-3 bucket was invalid. Its decks are separate
  Crustle/Munkidori, Cubchoo/Articuno, and Teal Ogerpon/Clefairy/Crustle
  shells. The classifier now requires complete shell signatures and avoids
  single-card false positives. Starmie 1-3 is the only repeated weak family.
- Nine exact live 60-card lists were paired against v17 and v22 using the
  nearest fixed public policy proxy. The final comparison is 305 -> 324/780,
  +19 for v22. All nine styles are nonnegative after confirmation seeds;
  duplicate controls are exact and all reports valid.
- Pure Crustle initially showed -3/80, but an independent 60-game seed was +3
  and moved the three-seed total to 12-12/140. Do not add a Crustle urgency
  exception from the non-reproducing result.
- v22 remains frozen as the next-reset submission. The exact-list panel is a
  safety test, not evidence that the proxy policies reproduce live opponents.

### 2026-07-13 Cynthia v22 strong-policy safety

- Six strong runnable local policies gave v17 159 -> v22 163/360 (+4) at
  seed 202857313. The panel covers two Archaludon policies, MPGaming
  Kangaskhan/Crustle v23, two Marnie styles, and the v22 mirror.
- Initial Shumpei -3 and Marnie Kazuki -1 buckets were repeated on unused seed
  202867313. They became +6 and 0; the confirmation total was 56 -> 62/120.
- Duplicate controls were exact and every report was valid. The non-repeating
  negatives do not justify a matchup patch or candidate rejection.
- v22 remains the next-reset probe. This panel narrows the weak-opponent gap,
  but local policies are still proxies rather than clones of Kaggle behavior.

### 2026-07-13 Cynthia v23 Call-before-evolution promotion

- A taxonomy of v22's 141/324 Gold mismatches found 54 evolution/development
  ordering states, the largest reusable class. The repeated defect was that
  v22 preserved Champion's Call only on the Gabite it was about to evolve,
  while the Gold policy used other legal Calls before any Garchomp evolution.
- v23 narrows the fix to one comparison: any legal Champion's Call ranks above
  a Garchomp-ex-on-Gabite evolution. Higher-scored unrelated actions and every
  non-Garchomp evolution retain their v22 order. This avoids the broad losses
  of the rejected global-priority v2.
- Exact Gold mismatch improves 141 -> 133/324. Eight of ten changed decisions
  become exact recorded Calls; no previously matching decision is lost. On 35
  public v9 games the change surface is 11/2,160 decisions, all evolution ->
  Call, with no unrelated action change.
- Versus v22: historical gates +1/480; two broad seeds -1/1,200; six strong
  policies +4/360; nine exact live decks +1/360. Aggregate is +5/2,400, with
  exact controls, zero action errors, and zero max-step games. Treat the broad
  result as neutral and the candidate as a sequencing probe, not a proven
  large win-rate gain.
- Package:
  `candidate_cynthia_garchomp_nasuo445_v23_allcall_before_evolve_20260714.tar.gz`,
  SHA256 `C8AD5F9BA979EA7A28732DB516C8B0681D310E3924319D08379C67E0C628CCD1`.
  Exact 60 cards, 13 members, five focused tests, compile/import/source match,
  and five-game archive smoke pass. v23 supersedes v22 for the next quota
  reset; v22 is rollback. Current submitted v9 remains 17-18/35 at 572.3024,
  mature below Bronze.

### 2026-07-13 Cynthia v24-v28 opening-width ablation rejected

- Live v9 is now 17-20/37 at 561.3526 after losses to Dragapult and
  Starmie/Froslass. It is mature weak and not recovering.
- v24 added a turns-1-2 rule that puts available Gible/Roselia/Spiritomb and
  width/search plays before the first Rock Fighting Energy or Power Weight
  while the main line has fewer than two bodies and no Energy. Gold mismatch
  improved 133 -> 130/324 without losing a prior exact action.
- Initial paired evidence was positive: +5/720 development, +1/360 strong,
  and +7/480 on an unused broad seed. Exact-live lists then scored -2/360,
  followed by -1/240 on the two negative Crustle buckets; both regressions
  were player-1 pure-Crustle games.
- Action traces showed that the broad rule delayed Power Weight or Rock under
  visible Dwebble/Crustle pressure. v25-v27 tested general pressure guards;
  v28 used the already-public Crustle line marker. Although v28 restored both
  known flips, a fresh gate was broad 0/480, strong 0/360, exact Crustle
  -1/240, combined -1/1,080. Controls were exact and errors/max-step were zero.
- Reject v24-v28. Do not package or submit them. Keep v23 as the next-reset
  probe because its Call-before-evolution correction remains the best
  validated theory change; v22 remains rollback.

### 2026-07-13 Cynthia v29-v31 rotation ablation rejected

- Local state telemetry was extended to capture Active and Bench HP, Energy,
  and Tool state, then 320 games were audited for damaged-Active rotation
  opportunities. This tested the deck theory that a loaded or heavily damaged
  Garchomp should sometimes move to the Bench before it collapses.
- v29 rotated at 200 or more damage with a ready backup and regressed the
  broad/strong aggregate by two games. v30 restricted the trigger to 300 or
  more damage or four Active Energy and was only +1/1,080. v31 added an
  immediate Corkscrew-KO veto, but that removed the only Archaludon gain and
  left the broader result neutral.
- The public state did not separate beneficial tank rotation from surrendering
  attack tempo safely enough. Reject v29-v31 and retain the telemetry/audit for
  future state-value learning rather than adding a brittle rule.

### 2026-07-13 Cynthia v35 reliable development selected

- A live Starmie/Froslass audit found a deck-plan difference rather than a
  single tactical mistake: all three losses failed to charge a backup attacker,
  while the win built two Garchomp and two Roserade. A Gold-replay cross-check
  found seven comparable windows, with four supporting and three contradicting
  a generic delay-attack rule. This justified only a narrow guaranteed-action
  ordering rule.
- v32 broadly forced backup development before a non-winning attack and lost
  one Starmie game. v33 excluded Poffin and immediate Active KOs and improved
  broad/strong panels, but had an exact-list regression. v34 narrowed the state
  to an Active one-Energy Garchomp with no Energy-ready backup and gained
  11/1,920, but direct Gible and unrestricted Gong choices still produced
  adjacent losses.
- v35 keeps only reliable public-state development before a non-immediate-KO
  attack: attach Energy to a benched Gible/Gabite/Garchomp, evolve a benched
  Gible/Gabite, recover Gible with Night Stretcher when space exists, or use
  Fighting Gong only with an empty Bench and four or five prizes remaining.
  Direct Gible and Poffin are not forced; normal v23 scoring can still choose
  them. Immediate KOs and every unrelated v23 rule remain unchanged.
- Stage-one paired gates were +2/360 exact-live, +2/720 broad, +2/360 strong,
  and +3/480 broad holdout: +9/1,920 with no negative opponent bucket. Blind
  gates were +1/480 broad, +1/240 strong, and 0/360 exact-live: +2/1,080.
  Total result is 1,584 -> 1,595/3,000 (+11), with exact duplicate controls,
  zero action errors, and zero max-step games.
- Selected package:
  `candidate_cynthia_garchomp_nasuo445_v35_reliable_development_before_attack_20260714.tar.gz`,
  SHA256 `E691A08AC140EC7D91733BC7D70D381D3064742F0ED41F19CB524071B9ED2FA7`.
  It has the exact Gold 60 cards and 13 runtime members. Source/archive hashes,
  `py_compile`, normal import, no-`__file__` execution, and a 10-game two-seat
  archive smoke are clean; packaged and source results are byte-identical.
  Fifteen focused v34/v35 tests pass.
  v35 supersedes v23 for the next quota-reset probe. v23 is the rollback.
- Fresh live state at 2026-07-13 20:30 JST is submission 54630859 COMPLETE at
  559.1698, 18-22 over 40 public games. The latest loss is Hop/Trevenant
  episode 85732359. Starmie/Froslass remains the only repeated severe bucket
  at 1-4. This is mature weak, not a recovering submission.
- Public-snapshot attribution confirms the change is narrow. Across 250
  reconstructable decisions in the five Starmie/Froslass games, v35 differs
  from v23 once: episode 85682411 step 56 changes a non-KO Corkscrew attack to
  Night Stretcher while Gible is discarded and Bench space exists. The other
  249 decisions are unchanged. Three of four Starmie losses lacked a viable
  backup, but two never reached a v35-eligible state; do not claim this rule
  solves the whole matchup.
- On latest Hop/Trevenant loss 85732359, v23 and v35 are identical in all 49
  reconstructable decisions because Garchomp ex never becomes Active. Treat
  that singleton as an opening/readiness stress case, not a reason for a Hop
  patch or for rejecting the broader v35 probe.

### 2026-07-13 Cynthia v36 Starmie Gible-order probe rejected

- Two Starmie losses outside v35 were audited for an earlier main-line action.
  Episode 85688147 had no missed legal development action. Episode 85679036
  had one turn-2 state where v35 attached Rock Energy before benching a second
  Gible, but it still benched that Gible later in the same main phase.
- v36 tested only this publicly identifiable order under visible Staryu/Mega
  Starmie: with one main-line body and a direct Gible play legal, rank Gible
  one point above the currently selected Energy attachment. It cannot trigger
  in the documented Dwebble/Crustle contradiction states.
- The exposed exact-Starmie panel was +1/64 and reproduced one loss-to-win
  trajectory; Crustle checks were exact and a 480-game broad panel was neutral.
  The required blind panel did not confirm it: 426 -> 425/600 (-1), with no
  game flip or measurable turn-2 readiness gain. The negative exact bucket
  was 71-71 on a second unused-seed 120-game rerun.
- Reject v36 for promotion. It is neutral safety after rerun, not repeated
  improvement. The failure is not when the second Gible is benched within the
  turn; it is the later Gabite/evolution supply and survival route. Keep v35
  as the next-reset probe.

### 2026-07-13 Cynthia v37-v39 Poke Pad route rejected

- The remaining Gold mismatch taxonomy contains 48 search/support-related
  states. The only repeated public cluster was early Poke Pad into Gible in
  episodes 85023189 and 85023208. Actual observations expose a stable public
  `select.effect.id == 1152` Poke Pad marker; the Gold win 85023194 provides a
  turn-3/full-board negative control.
- v37 combined early Poke Pad-before-attachment with Gible-over-Gabite target
  selection. It changed the intended eight Gold decisions and scored +11/720
  broad, +4/360 strong, and +8/360 exact-live: +23/1,440. Three initial
  negative cells were rerun; Cynthia and Starmie reversed positive, while the
  Archaludon loss did not repeat in that combined-policy confirmation.
- Controlled ablation showed that main-action ordering was not the gain:
  v38 main-only was -3/1,440. v39 target-only captured +22/1,440 and reached
  +32/2,400 after negative-bucket confirmations. However, Archaludon player 0
  repeated at -3/180 on two unused seeds and finished -6/210 with the original
  cell. This is a real adjacent-policy regression despite the strong aggregate.
- Archaludon target-shift traces contained six beneficial and nine harmful
  flips. Their visible board, hand, deck count, Energy, and line-width features
  were effectively indistinguishable. No public-state guard separates them;
  opponent identity is not an acceptable guard. Reject v37-v39 and do not run
  blind promotion panels. Keep v35 selected.
- Roserade-before-Champion's-Call also appeared in six Gold states, but five
  came from losses and no public feature separates necessity from preference.
  Do not add that rule either.

### 2026-07-13 Cynthia v40-v41 early Poke Pad route rejected

- A bounded audit of the five live Starmie/Froslass games found two losses
  where an older, publicly evolution-eligible Gible was exposed while Poke Pad
  could access Gabite before the next attack. The single bucket win used that
  route successfully. Two other losses already reached Garchomp by turn 5, so
  the pattern is a setup leak, not a complete matchup explanation.
- v40 used the public `appearThisTurn == false` marker but lacked a turn bound.
  Replay attribution showed the intended turn-2/3 changes plus eight late
  changes in Crustle episode 85678570, so v40 was rejected at stage 0.
- v41 added only `turn <= 3`. It preserved three semantic Starmie trigger
  windows and changed zero decisions in the Crustle negative control. Focused
  tests passed and all paired controls were exact with zero action errors or
  max-step games.
- v41 improved Starmie/Froslass by +5/600, broad by +5/720, six strong by
  +1/360, and the full main matrix by +5/1,440. Exact-live was -1/360 and the
  exact negative cell reversed to +1/120 on confirmation.
- The Archaludon safety population failed twice: -4/420, then -2/420 on an
  independent schedule, pooled -6/840. All executed panels were still only
  +5/3,000. Reject v41 and skip blind promotion panels; v35 remains selected.
- A separate four-game Crustle/control audit found a structural one-prize
  exchange disadvantage rather than one repeated setup error. The only narrow
  avoidable leak was a nonterminal one-prize Buster without a loaded backup,
  which v35 already rejects through the inherited selective-Buster gate.

### 2026-07-14 Cynthia absolute audit; v35 probe suspended

- Root independently re-aggregated identical strong, exact-live9, and broad
  schedules. Absolute totals are v9 584/1,440 (40.56%), v22 720/1,440
  (50.00%), v23 728/1,440 (50.56%), and v35 734/1,440 (50.97%). v35 remains
  only 159/360 (44.17%) strong and 149/360 (41.39%) exact-live9, with a 0%
  exact bucket floor.
- v23 -> v35 is six wins over 1,440 games (+0.42 percentage points). This is a
  real fixed-schedule gain but not a practically sufficient replacement case.
- The nine exact-live deck proxies reproduce only 273/506 (53.95%) source
  opponent decisions. They are exact-list tests, not exact-policy tests. This
  distribution mismatch invalidates submission claims based on small deltas.
- Gold agreement remains 191/324 (58.95%) for both v23 and v35. v35 changes
  only three of 1,212 decisions across all 22 live losses relative to v23.
- The low-cost evaluator executed schedules correctly but mistakenly assigned
  v35's `candidate_win` counts to v23. Root corrected the report from 734 to
  728 v23 wins and made raw-column verification mandatory.
- Suspend the v35 next-reset submission. Stay on the Cynthia track and rebuild
  the Starmie, Kangaskhan/Crustle, and control policy population before another
  candidate is selected. See `docs/cynthia_absolute_strength_audit_2026-07-14.md`.

### 2026-07-14 Cynthia v53 rejected; v54 Call bridge specified

- The active strategy is deterministic deck-theory rules. Replay-derived
  opponent-policy reconstruction is not the main workstream and is not a
  submission gate. The historical actually-Silver Archaludon remains the
  primary absolute-strength anchor.
- v53 tried to finish one existing backup line immediately before an approved
  Buster. On the frozen 200-game two-seat Silver schedule it moved only
  `47 -> 48/200`, with paired `+1`, seat deltas `+1/0`, and block deltas
  `+1/0/0/0`. It failed the absolute, paired, both-seat, and block gates.
  Reject v53, stop that late pre-Buster branch, and keep exact v52 only as the
  development baseline.
- The next single theory rule is the two-Gabite Champion's Call bridge. When
  unchanged v52 has used a first Call with exactly one Gabite, no Garchomp,
  and an old Gible, select a second Gabite, evolve that old Gible, use the new
  Gabite's Call, then return to exact v52 for Garchomp and support routing.
- Root action-surface audit found 172 eligible events in 125 games, including
  87 baseline-loss games and both seats. All 47 natural second-Gabite choices
  completed the evolution and second Call in the same turn. This establishes
  mechanism legality, not strength.
- v54 is authorized only for isolated implementation and the same frozen
  200-game primary gate. It must reach at least `55/200`, paired `+8`, improve
  both seats and at least two blocks, and preserve exact controls. No package
  or Kaggle submission is authorized before those gates pass.
- Fresh live state remains submission 54630859 Cynthia v9, COMPLETE at 596.0.
  It is mature weak, but there is no valid replacement candidate yet.

### 2026-07-14 Cynthia v54 rejected; v55 stopped before implementation

- v54's two-Gabite Call bridge was correctly isolated and passed 58 root-run
  focused/regression tests, engine import, no-`__file__` execution, exact deck,
  and source-scope checks. On the frozen Silver anchor it scored `51/200`
  against v52's `47/200`, with paired gains/losses `15/11`, seat deltas
  `+3/+1`, and blocks `0/+3/-2/+3`.
- The movement is directionally positive but fails the precommitted `55/200`
  and `+8/200` gates; exact McNemar p is `0.5572`. Reject v54, do not package or
  submit it, and do not inherit it into a cumulative baseline. Exact v52
  remains the development baseline.
- Sol Ultra selected one materially different next hypothesis: during an
  already-resolving Buddy Poffin, replace a baseline two-Gible pair with
  Gible+Roselia only in the one-Gible/no-support foundational state. This
  targets the full attacker-plus-support opening rather than another Call or
  late-attack patch.
- Root audited all 227 Poffin resolutions in the fixed v52 Silver traces.
  Only 28 distinct games qualified, split 15/13 by seat and `12/3/5/8` by
  seat/block. Although 21 were baseline losses and every proposed pair was
  legal, the frozen prerequisites of 30 games and five per block failed.
- Do not implement or widen v55. No candidate, archive, or Kaggle submission
  was created. Return to a new strategy judgment with v52 unchanged.

### 2026-07-14 Cynthia v56 rejected on card mechanics

- Sol Ultra proposed attaching Basic Fighting Energy to an Active zero-Energy
  Cynthia's Roserade so it could attack while preserving Benched Gible/Gabite
  development. Root first found adequate public-state exposure: 35 games,
  21/14 by seat, all four seat/block cells covered, 24 baseline-loss games,
  and a legal Basic Fighting attachment in every event.
- The root card-catalog check then disproved the causal mechanism. Roserade's
  Leaf Step costs one Grass plus two Colorless, while this exact deck contains
  five Basic Fighting and four Rock Fighting Energy and zero Grass Energy.
  Fighting attachment cannot enable Leaf Step. Roserade's role in this list is
  Cheer On to Glory support, not a practical secondary attacker.
- Reject v56 before implementation or evaluation. No candidate, test, archive,
  or Kaggle submission was created, and exact v52 remains the sole development
  baseline. Future hypotheses must verify card text, attack cost, Energy
  compatibility, and the full legal sequence before exposure counts can
  authorize implementation. Full evidence is in
  `analysis_outputs/cynthia_v56_active_roserade_energy_bridge_20260714/MECHANICS_REJECTION.md`.

### 2026-07-14 Cynthia v57 Roserade support-role rule rejected

- Root verified that the exact list has no Grass Energy, so Roserade cannot pay
  Leaf Step's Grass cost. v57 therefore tested one isolated classification
  correction: remove Roserade from `active_is_main_attacker`, affecting only
  the existing Boss's Orders scoring path. Exact v52 remained otherwise
  unchanged.
- The frozen historical-Silver Archaludon schedule scored `47 -> 44/200`.
  Paired gains/losses were `1/4`; seat deltas were `-2/-1`; 50-game block
  deltas were `-1/-1/-1/0`. Exact two-sided McNemar p was `0.375`.
- Root verification found 200 unique paired keys, exact duplicate controls,
  six successful commands, 600/600 started summary rows, zero action errors,
  and zero max-step hits. The negative result is not an execution artifact.
- Reject v57 and do not inherit, package, archive, or submit it. Mechanically
  correct role labeling did not prove a stronger policy: Boss selection while
  Active Roserade cannot attack may still carry stall, disruption, or future
  target value. Exact v52 remains the sole development baseline.
- Full immutable evidence is in
  `analysis_outputs/cynthia_v57_roserade_support_role_20260714/RESULT.md`.

### 2026-07-14 Cynthia v58 core bridge selected for live probe

- Root trace analysis found a positive sequence failure rather than a narrow
  matchup patch. Exact v52 often used a non-KO 20/40-damage Gible/Gabite
  attack while a legal Poffin, Fighting Gong, Poke Pad, Forest, Gible, or
  Roselia setup bridge remained available. The frozen surface covered 82/200
  historical-Silver games and all four seat/block cells.
- v58 changes only this ordering: when the visible chip cannot KO and the
  Garchomp/Roserade/two-main-line core is incomplete, use the highest existing
  positive bridge score first, then re-evaluate. Deck, targets, scores, deck
  floors, KO handling, and every unrelated context remain exact v52.
- On the fixed historical-Silver anchor, v52 `47/200` became v58 `61/200`.
  Paired gains/losses were `14/0`, seats improved `+8/+6`, and 50-game block
  deltas were `+4/+4/0/+6`. Every first divergence was the intended bridge,
  and all 14 gains still attacked with Dragonslice in the same turn.
- On an unused-seed six-agent safety population, v52 `225/480` became v58
  `241/480`. Every opponent bucket improved: two Archaludon styles `+3/+4`,
  Cynthia `+3`, Kangaskhan/Crustle `+4`, and two Marnie styles `+1/+1`.
  Both stages had exact duplicate controls, zero action errors, and zero
  max-step hits.
- Selected archive:
  `candidate_cynthia_garchomp_nasuo445_v58_core_bridge_before_chip_20260714.tar.gz`,
  SHA256 `D875845890484DF5F124C653DDDA13F1F2003F3A9C2DB679BB7C2A67609FE8A5`.
  It has 13 members with `main.py` first, the exact 60-card list, matching
  extracted hashes, clean import/no-`__file__` checks, and exact two-seat
  source-versus-package smoke results.
- Pre-submit hypothesis, risk, rollback, and immutable evidence are recorded
  in `analysis_outputs/cynthia_v58_sequence_audit_20260714/RESULT.md`.
- Kaggle submission `54666167` was accepted at 2026-07-14 09:45 JST.
  Validation episode `85834265` completed at `600.0` with no execution error;
  the first direct fetch contains validation only, so public live evaluation
  remains pending.

### 2026-07-14 Cynthia v58 early live recovery and v59-v61 audit

- At the 11:12 JST direct fetch, v58 had 20 public games, record `12-8`, and
  score about `548.0`. It opened `2-5` but then ran `10-3`, so it is recovering
  and must not be replaced without a materially stronger candidate.
- The first five losses exposed two coherent sequence defects. In Dragapult
  loss `85836064`, a one-Energy Benched Garchomp was ready by turn 5 while a
  zero-Energy Roserade remained Active; the first attack was delayed until
  turn 19. In Ogerpon loss `85835485`, Poke Pad selected Gabite with a sole
  Active Gible and empty Bench, followed by an immediate board-clear loss.
- v59 tried the minimum-cost route from a support Active to an energized Bench
  Garchomp. On the frozen Silver anchor it changed v58 `61 -> 62/200`, but the
  five gains and four losses missed the predeclared `+4` gate. v60 deferred
  activation behind legal evolution and Champion's Call; it scored
  `61 -> 61/200`, with two gains, two losses, and seat deltas `-1/+1`.
  Reject both activation candidates. The remaining gains and losses could not
  be separated without schedule-specific prize-exchange guards.
- v61 narrowly corrected the empty-Bench Poke Pad choice. Root reconstruction
  confirms it chooses Gible instead of Gabite in episode `85835485`, and 11
  focused tests pass. The historical-Silver panel was exactly unchanged at
  `61/200`, with zero gains and zero losses, so it missed the frozen `+6`
  absolute-strength gate. Retain it only as a verified future cumulative
  correction; do not run Stage 2, package, or submit it alone.
- Full evidence is in
  `analysis_outputs/cynthia_v59_activate_ready_garchomp_audit_20260714/RESULT.md`
  and
  `analysis_outputs/cynthia_v61_empty_bench_pad_basic_audit_20260714/RESULT.md`.

### 2026-07-14 Cynthia v63 Crustle counter selected

- Root replay diagnosis found a card-mechanics failure in live losses
  `85857115` and `85853253`: v58 repeatedly Corkscrewed Active Crustle for
  zero damage despite a public same-turn lethal Spiritomb route.
- v63 changes only this exact sequence. It Benches/energizes Spiritomb if
  needed, free-retreats a damaged Active Garchomp ex, promotes Spiritomb, and
  uses lethal Raging Curse. Every step recomputes legality and otherwise falls
  back to exact v58.
- Two complete Crustle policies improved `40->114/200` and `152->168/200`.
  Combined paired gains/losses were `90/0`, both seats improved in both
  panels, and all 90 full traces completed the approved lethal route.
- Historical-Silver Archaludon remained exactly `61/200`. The six-agent
  population improved `241->270/480`; all `+29` came from
  Kangaskhan/Crustle and five non-Crustle buckets were outcome-equivalent.
- Across 1,280 paired rows there were 1,280 unique keys, exact duplicate
  controls, and zero command, action, or max-step failures. Eleven focused
  tests and package checks pass.
- Selected archive:
  `candidate_cynthia_garchomp_nasuo445_v63_crustle_spiritomb_counter_20260714.tar.gz`,
  SHA256 `3B5D881AFC6E6C56BADF8EFC261A8B00AFF1A0CAD3C5B9F14BC7B95EA0FD7AA5`.
  It has 13 members and the exact evaluated 60-card list.
- The generic `audit_paired_results.py` block-direction boolean marks
  zero-delta controls false; that is not this experiment's frozen nonnegative
  safety gate. The raw control equivalence and this audit-label mismatch are
  recorded explicitly in
  `analysis_outputs/cynthia_v63_crustle_spiritomb_counter_20260714/RESULT.md`.
- Current live v58 was COMPLETE at 618.0 after 38 public games, so the
  established early-replacement condition is met. v58 remains the rollback.
- Kaggle accepted v63 as submission `54673338` at 2026-07-14 14:11 JST.
  Validation episode `85870909` completed at `600.0` with no execution
  error. The initial direct fetch contains validation only.

### 2026-07-14 Cynthia v64 Boss conversion guard rejected

- By the 16:16 JST root fetch, live v63 had 31 public games, record `15-16`,
  and score `624.8`. The intended Crustle route was `3-0`, but Starmie was
  `1-3`, Archaludon `0-2`, and the overall submission remained weak.
- Root replay reconstruction confirmed one repeated tactical defect. In
  episodes `85872552` and `85874127`, v63 assigned its `Boss for KO` score
  while the Active Pokemon could not pay for a same-turn attack. Sol Ultra
  selected only a fail-closed same-turn Boss conversion guard for isolated
  implementation; no other live-loss patch was combined with it.
- v64 corrected both reconstructed states and passed 17 focused v63/v64 tests,
  including ordinary Boss pressure and the accepted v63 Crustle sequence.
- The precommitted historical-Silver hard gate then regressed from `61/200`
  to `49/200`. Paired gains/losses were `4/16`; seats changed `33->26` and
  `28->23`; four 50-game blocks changed `-3/-4/-2/-3`. Exact McNemar p was
  `0.0118179321`.
- Root verified all 200 unique schedule keys, the frozen seeds, six zero-exit
  commands, exact duplicate controls, and zero action errors or max-step hits.
  This is a policy regression, not an execution artifact.
- Reject v64. Do not package, submit, or inherit it. The two live examples
  establish a real defect but do not justify a broad guard that removes useful
  disruption/future-target value. Full evidence is in
  `analysis_outputs/cynthia_v64_boss_same_turn_conversion_guard_20260714/RESULT.md`.
- Full reruns of all 20 paired flips confirmed that every first divergence was
  v63's `Boss for KO` versus a v64 fallback. Root parsing of the actual switch
  logs found 11 regression targets were Duraludon `169` and five were Cinderace
  `666`; Full Metal Lab was active in 12 regressions. The guard removed valuable
  prize/development/disruption lines rather than failing because of one
  unrelated fallback score.
- Root also corrected a qualitative subagent claim before it entered a
  decision: the two live false-Boss targets were Froslass `104` in `85872552`
  and Staryu `1030` in `85874127`, not Froslass in both games. Their shared
  signature is matchup-level, so an exact-card exception is not a coherent fix.
- A fresh 16:41 JST fetch had 39 public games at `20-19`, score `640.6`.
  Current verified buckets are Alakazam `5-2`, Mega Lucario `5-3`,
  Crustle/control `3-0`, Starmie/Froslass `1-3`, and Archaludon `0-2`.
  The latest eight-game window was `5-3`, a modest recovery but still below
  the established weak-submission threshold; no replacement exists yet.

## 2026-07-14 Cynthia Fighting Gong readiness audit

- v65 was a no-op because Fighting Gong is represented as optional `0,1`, not
  required `1,1`; the discrepancy was recorded rather than treated as strategy
  evidence.
- Corrected v66 activated on all 15 frozen certificate games and nowhere else,
  selected and attached Energy `15/15`, but changed the historical-Silver
  anchor from `146/600` to `144/600` with paired gains/losses `0/2`.
- None of 12 certificate losses converted, and only one of three certificate
  wins survived. The entire Energy-over-Gible branch is rejected; no
  outcome-conditioned narrowing is retained.
- Root evidence:
  `analysis_outputs/cynthia_v65_fighting_gong_readiness_audit_20260714/V66_STAGE1_RESULT.md`.
- Next pre-implementation direction: certified attach-before-Boss conversion,
  preserving exact v63 Boss behavior unless the complete typed
  attach/Boss/attack/KO route is public and legal.

## 2026-07-14 Cynthia attach-before-Boss audit rejected

- The direction above was audited before implementation on the expanded
  historical-Silver schedule: 600 games, both seats, six 50-game blocks.
- There were 85 mechanical states where v63 selected `Boss for KO`, had no
  current attack option, and could attach Fighting Energy to the Active.
  Sixty-four met the conservative typed-cost and visible-KO certificate.
- The certificate population was not sparse: both seats (`34/30`), all six
  blocks (`9/10/10/6/10/19`), 25 win controls, and 39 losses.
- Exact v63 nevertheless already completed
  `Boss -> Active attach -> Corkscrew Dive KO` in `64/64` certificates. The
  expected attack and a KO score reason were also present in `64/64`.
- Reordering the attachment before Boss has no demonstrated missing conversion
  to repair. Reject without implementation, local candidate evaluation,
  packaging, or submission. Do not outcome-narrow this branch.
- The other 21 states had Active Roserade. One Fighting attachment cannot pay
  Leaf Step's Grass plus two Colorless cost, so they are not an alternative
  certified subset.
- Root evidence:
  `analysis_outputs/cynthia_v67_attach_before_boss_audit_20260714/RESULT.md`.
- At the same root refresh, live v63 remained weak but unchanged at 42 public
  games, `22-20`, score `648.9205`; latest episode `85902594` was a win. No
  replacement candidate exists from this rejected branch.

## 2026-07-14 Cynthia v68 expanded Poffin role audit rejected

- Sol Ultra next selected the same role-balanced Poffin hypothesis previously
  stopped as v55. It was eligible for a new exposure audit only because a new
  600-game exact-v63 Silver-anchor schedule now exists; the old 200-game v55
  rejection remains valid.
- The larger schedule found 70 qualifying games, enough to pass the mechanical
  coverage gates: seats `32/38`, blocks `15/12/9/14/8/12`, 27 win controls,
  43 losses, and legal `Gible + Roselia` pairs in `70/70`.
- Exact v63 naturally established Roselia/Roserade before its next attack in
  `62/70` exposures. Only eight missing-route certificates remained, covering
  four blocks with one win and seven losses.
- The frozen causal minimums were 24 certificates, five blocks, 16 losses, and
  six wins. Reject v68 before implementation; do not outcome-, turn-, seat-,
  block-, or opponent-filter the eight residual states.
- Root evidence:
  `analysis_outputs/cynthia_v68_poffin_role_pair_expanded_audit_20260714/RESULT.md`.

## 2026-07-14 Cynthia v69 one-shot Roselia bridge rejected

- Sol Ultra selected a direct support-foundation hypothesis: before a non-KO
  Corkscrew Dive with no Roselia/Roserade in play, Bench one legal Roselia from
  hand and then return to exact v63 for the same-turn attack.
- The frozen 600-game historical-Silver audit found 72 exposed games, both
  seats (`38/34`), and all six blocks. All 172 event rows had a legal direct
  Roselia play, absent support line, and non-KO Corkscrew selection.
- Exposure was heavily outcome-skewed: only five baseline wins versus 67
  losses. The precommitted gate required at least 16 win controls so that a
  proposed development rule could be checked against successful trajectories.
- Reject before implementation. The trigger is a useful failure-state marker,
  but it is not causal evidence that Roselia-first converts those games. Do not
  recover it with turn, prize, seat, seed, opponent, or outcome filtering.
- Root evidence:
  `analysis_outputs/cynthia_v69_one_shot_roselia_bridge_audit_20260714/RESULT.md`.

## 2026-07-14 Cynthia v70 multi-prize Spiritomb conversion rejected

- Sol Ultra selected a mechanics-complete extension of v63: use a ready or
  immediately ready Spiritomb to convert visible damage on a free-retreating
  Active Garchomp into a guaranteed same-turn KO of a multi-prize Active.
- The 600-game historical-Silver exposure gate passed strongly. There were 116
  distinct missing-route games, seats `58/58`, all six blocks, 30 wins and 86
  losses, legal/lethal certificates `116/116`, and zero natural v63 routes.
- This was a meaningful alternate transaction on the anchor. Twenty-two first
  certificates otherwise used a non-final Buster KO, while many others spent
  the attachment on Garchomp; Spiritomb could take the same KO while retaining
  the main attacker's Energy.
- The frozen cross-matchup gate failed. Across four fixed live Starmie/Froslass
  episodes, 25 observations reached damaged Garchomp versus a multi-prize
  Active with legal retreat and no immediate game-winning Garchomp attack, but
  zero had legal Spiritomb-plus-Energy route material.
- Reject before implementation. Do not remove the Starmie corroboration after
  seeing the result or retain an Archaludon/card-ID/turn/outcome subset. No
  candidate, evaluation, package, or submission was created.
- Root evidence:
  `analysis_outputs/cynthia_v70_multiprize_spiritomb_audit_20260714/RESULT.md`.

## 2026-07-14 Cynthia v71 post-KO Unfair Stamp rejected

- Sol Ultra selected one isolated disruption-and-recovery transaction: after
  an opposing-turn KO, use a legally available Unfair Stamp when public hand
  counts guarantee at least a two-card swing for both players, an attack is
  preserved, and no legal attack immediately wins the game.
- The frozen 600-game historical-Silver audit found only 15 certificate games,
  below the required 32. Seat counts were `7/8`, below 12 each. All six seed
  blocks appeared, but all 15 certificates were baseline losses and there were
  zero win controls, below the required 12.
- The frozen live corroboration also failed: the four fixed
  Starmie/Froslass episodes, containing one win and three losses, had zero
  qualifying states.
- Reject before implementation. This is a failure-state marker, not evidence
  that Stamp restores Cynthia's coherent sequence. Do not retain an opponent-,
  turn-, card-, seat-, seed-, block-, or outcome-filtered subset.
- Root independently recomputed the CSV counts and verified that the audited
  runtime source is byte-identical to canonical v63.
- Root evidence:
  `analysis_outputs/cynthia_v71_postko_unfair_stamp_audit_20260714/RESULT.md`.

## 2026-07-14 Cynthia v72 pre-KO continuity attachment rejected

- Root replay inspection found a real continuity defect in Archaludon loss
  `85883400`: before a non-final Corkscrew KO, exact v63 left two Benched
  Gabite unenergized despite an unused attachment and three legal Fighting
  Energies. The other Archaludon loss `85871520` did not share the route; its
  only Energy was required to make Active Corkscrew legal.
- Sol Ultra selected a generic, mechanics-complete extension of v63's existing
  pre-Buster backup attachment: attach to the furthest-developed unenergized
  Benched main line, revalidate, then execute the same non-final Corkscrew KO.
- The frozen 600-game audit found only nine complete certificates, below 32.
  Seats were `3/6`, only four of six blocks appeared, and win/loss controls
  were `3/6`, below `16/16`.
- All nine mechanical certificates were valid and exact v63 naturally
  completed zero, but all four fixed Starmie/Froslass episodes had zero
  qualifying states.
- Reject before implementation. One correct live-loss correction does not
  establish a safe generic rule. Do not retain a narrowed subset.
- Root evidence:
  `analysis_outputs/cynthia_v72_preko_continuity_attach_audit_20260714/RESULT.md`.
- The post-audit root refresh added one public win, episode `85912239` versus
  ZZDirty. v63 is now 43 public games, `23-20`, score `654.1267`. This remains
  mature weak below 700, but neither v71 nor v72 is a valid replacement.

## 2026-07-14 Cynthia v73 Unfair Stamp classification rejected

- Mirror loss `85915432` exposed a real classification defect: exact v63
  boosted Unfair Stamp with raw score `5200` above a legal Corkscrew Dive with
  raw score `15000` because every positive `PLAY` is treated as generic
  development. The later loss was deck exhaustion, not an incorrect optional
  Corkscrew draw.
- Sol Ultra selected a generic correction for preimplementation audit only:
  remove Stamp from `corkscrew_development_index`, while retaining its ordinary
  score and every other v63 sequence.
- The 600-game historical-Silver gate passed: 52 certificates, seats `27/25`,
  all twelve seat-block cells, wins/losses `33/19`, and direct legal
  Stamp-retaining Corkscrew in `52/52`.
- The fixed live gate failed. Six of 45 public games qualified, but they were
  one each from Cynthia mirror, Okidogi/Barbaracle, Alakazam, Archaludon, Mega
  Lucario, and Mega Abomasnow/Kyogre. No repeated mixed bucket contained both a
  qualifying win and loss.
- Reject before implementation and do not remove the live corroboration gate
  post hoc. The defect is real, but the replacement timing is not yet shown to
  improve a recurring live structure.
- Root evidence:
  `analysis_outputs/cynthia_v73_unfair_stamp_not_generic_development_audit_20260714/RESULT.md`.
- Fresh live state used by the audit: 45 public games, `24-21`, score
  `657.9008`; latest pair was an Alakazam win and Cynthia mirror loss. No valid
  replacement candidate exists.

## 2026-07-14 Cynthia v74 no-conversion paid retreat rejected

- Sol Ultra identified a broad base-policy defect: generic retreat has score
  `600`, so v63 may discard the Active's only Energy, promote an unenergized
  equal-or-lower-stage Pokemon, gain no attack, and immediately end.
- The frozen 600-game Stage-A audit passed strongly: 250 certificates, seats
  `121/129`, all twelve seat-block cells, wins/losses `58/192`, exact one-Energy
  discard and immediate no-attack END in `250/250`, and zero productive routes.
- The fixed 46-game live gate failed. Eleven public episodes qualified overall,
  but repeated weak buckets contributed only one loss each: Starmie/Froslass
  `85874127` and Archaludon `85883400`. Neither had a qualifying win.
- Because the live gate failed, the status-observable 600-game rerun was not
  performed. Unknown status did not count as a pass. Reject before
  implementation and do not recover the branch through post-hoc narrowing.
- The finding remains important for a future Cynthia base-policy rebuild:
  generic retreat scoring creates a very broad resource-loss surface even
  though this exact veto lacks the required weak-bucket timing evidence.
- Root evidence:
  `analysis_outputs/cynthia_v74_no_conversion_paid_retreat_audit_20260714/RESULT.md`.
- Fresh live state is 46 public games, `25-21`, score `665.7591`, after
  Alakazam win `85916370`. No valid replacement candidate exists.

## 2026-07-14 Cynthia post-v74 replay recheck: no valid hypothesis

- Sol Ultra judged that the current evidence does not support another complete,
  public-state Cynthia transaction. No implementation, package, or submission
  was started.
- Root reran the checked rotation audit on both Archaludon losses. Nineteen
  damaged-Active/Benched-Garchomp states were found, but none had an
  Energy-ready backup and none produced a retreat. The shared 110-HP endgame is
  real, but repairing it requires the already rejected v29-v31
  attachment-and-rotation surface.
- Root reran the checked Buster audit on the four frozen Starmie/Froslass games.
  Exact v63 made two Buster choices; both satisfied the existing approval rule
  and zero were classified unsafe. One was a nonterminal multi-prize KO in a
  loss and one was a board-clear KO in a win, which is insufficient evidence
  for changing selective Buster timing.
- Boss-without-attack examples remain on rejected v64, and the lone Roselia
  collapse does not define a recurrent complete transaction.
- The 20:52 JST refresh added no games: v63 remains 46 public games, `25-21`,
  score `665.7591`. Keep v63 active until new evidence supports a rule that
  clears the frozen recurrence, legality, mixed-outcome, and live-bucket gates.
- Root evidence:
  `analysis_outputs/cynthia_post_v74_replay_recheck_20260714/RESULT.md`.

### 21:52 JST extension: third Boss-without-attack loss, v64 stays rejected

- New public episode `85925599` was an Alakazam loss. Exact v63 used Boss from
  an attackless Active Roserade at step 131 and immediately ended after target
  selection.
- This is the third live Boss-without-attack example overall, but the earlier
  two are Starmie/Froslass losses and the new one is the only Alakazam example.
  All three are losses; no repeated bucket has a mixed successful control.
- The evidence therefore still fails the frozen live admission gate and does
  not justify reopening broad v64, which previously reduced the
  historical-Silver result from `61/200` to `49/200`.
- Live v63 is now 47 public games, `25-22`, score `660.9259`. No valid
  replacement candidate exists and no slot was used.

## 2026-07-15 Cynthia v75 selected after practical-corpus exhaustion

- The final frozen v63 corpus has 48 public games, record `25-23`, latest
  episode `85937023`, and score `656.9808`. A final direct refresh added no
  episodes and reproduced CSV SHA256
  `5EE1F3B77AED3405F53D601C5C0B7A62E2C654566C5DA1EF9FF190425B252F93`.
- v75 retains v63 and changes one coherent sequence: during forced promotion,
  prefer a visible Gible/Gabite route that can become a complete Garchomp ex
  attack on the next turn, subject to visible-Garchomp and last-prize guards.
- Historical-Silver Archaludon improved `146->148/600`, paired gains/losses
  `2/0`, and the six-agent adjacent population improved `270->271/480` with
  no negative bucket. All controls were exact and all execution checks passed.
- Cumulative v76 was rejected at only `148->150/600`, below its frozen +6
  adoption gate. v77 corrected two repeated Rock-Energy placements in public
  Alakazam losses but was exactly neutral, `477->477/600`, against six complete
  Alakazam policies. It is also rejected.
- Every identified practical target in v59-v77 is now accepted or frozen as
  rejected/withheld. With no new live games, the corpus is exhausted for safe
  deterministic corrections; the next evidence source is one v75 live probe.
- Selected archive:
  `candidate_cynthia_garchomp_nasuo445_v75_forced_promotion_attack_route_20260714.tar.gz`,
  SHA256 `0E04FC733FCB8702E20970E11734066E7C545F04ED55F015B0EAE08AF2F14EE2`.
  Fresh extraction confirmed 13 members, exact evaluated source, exact 60-card
  deck, compile/import/no-`__file__` execution, and the existing two-seat
  ten-game package smoke has zero errors.
- Full exhaustion and rollback contract:
  `analysis_outputs/cynthia_practical_exhaustion_20260715/RESULT.md`.
- Kaggle accepted the selected archive as submission `54691310` at
  2026-07-15 00:42 JST. Validation completed at `600.0` with episode
  `85946875` and no execution error. Exact v63 and v75 reproduced all recorded
  validation actions in both seats with zero mutual differences, so the
  forced-promotion rule did not trigger and the validation game is
  non-discriminating. Continue with public-game action attribution.
- The first three public games were `2-1`, score `701.5114`: wins over
  Starmie/Froslass and Alakazam, and a loss to Archaludon metal. Exact v63 and
  v75 were action-identical in all three replays (`59`, `71`, and `70`
  decisions), so the new forced-promotion rule has not triggered and the
  sample is non-discriminating for its effect.
- The Archaludon loss contains a new late-game Energy-routing observation: a
  second Energy was attached to a 110-HP Active Garchomp while a full-HP
  Benched Garchomp already had one Rock Energy and could visibly become a
  Buster attacker after free retreat. This is held as a hypothesis, not a
  one-replay rule. Full initial observation:
  `analysis_outputs/kaggle_live/submission_54691310_cynthia_v75/INITIAL_OBSERVATION.md`.
- At the 2026-07-15 01:04 JST refresh, a fourth public game was added: win
  `85948865` versus Alakazam. The submission is `3-1` at `766.7231`. Exact v63
  and v75 were again action-identical (`19` decisions), leaving the live
  forced-promotion trigger count at zero. Keep v75 active and treat the run as
  non-discriminating for the new rule until an attributed trigger occurs.

## 2026-07-15 Cynthia v80 proactive role-completion cycle selected

- The first 20 public v75 games contained zero v75-only decisions, and the live
  score settled near `667.4`. Rather than wait only for another loss pattern,
  v80 strengthens Cynthia's ordinary deck sequence before a paid non-KO attack.
- The ordered transaction is: complete one visible Garchomp route, establish
  Roserade, establish a second main line, then prepare an energized backup.
  It never displaces a visible KO. Nested resolution is disabled on turn 1,
  and Poffin completes every legal selection with v75's original ranking after
  retaining the required role target.
- Historical-Silver improved `148->183/600`, gains/losses `51/16`, with both
  seats and all six 100-game blocks positive. The six-agent adjacent population
  improved `271->293/480`; all six opponent buckets were nonnegative versus
  v75. Both clustered 95% confidence intervals excluded zero.
- Six focused contract tests, immutable schedule controls, execution health,
  archive identity, and ten-game source/package equivalence all passed.
- Selected archive:
  `candidate_cynthia_garchomp_nasuo445_v80_legal_complete_role_cycle_20260715.tar.gz`,
  SHA256 `F5B7756804BA270B5CB1BED0CC1AAC6954CD48E0BA47C5BF08D22B9D976717C6`.
  Rollback remains v75 SHA256
  `0E04FC733FCB8702E20970E11734066E7C545F04ED55F015B0EAE08AF2F14EE2`.
- Pre-submit evidence and monitoring contract:
  `analysis_outputs/cynthia_v80_legal_complete_role_cycle_20260715/PRE_SUBMIT_EVIDENCE.md`.
- Kaggle accepted the archive as submission `54695488` at 2026-07-15 03:11
  JST. The local CLI's CP932 display exception occurred after upload; a fresh
  list confirmed exactly one new submission. Initial status is `PENDING`.

### Fixed live target after a manual submission

- The user later submitted `54697107`,
  `orbit_archaludon_terminal_conversion_experimental_20260715.tar.gz`, as the
  newest row. It is user-owned and outside this Cynthia analysis loop unless
  the user explicitly asks otherwise.
- Cynthia v80 remains the fixed live-history target by submission ID
  `54695488`; row position or "latest submission" must not be used to select
  episodes.
- The latest root-verified snapshot has 38 public games, record `23-15`, and
  score `649.5061`; latest episode is `85981631`. Always refresh this fixed ID
  directly rather than reading the second visible row by position.
- In the three newest games, v75-v80 attribution was `0/84` differences for win
  `85980571`, `1/78` for loss `85981103`, and `0/106` for loss `85981631`.
  The sole v80-specific choice was Night Stretcher at step 95 of `85981103`,
  followed by a three-Gabite Champion's Call development chain. This is a live
  diagnostic for possible role-cycle overdevelopment, not yet enough evidence
  for a one-game corrective rule.
- Frozen snapshot:
  `analysis_outputs/kaggle_live/submission_54695488_cynthia_v80/monitor_54695488_secondrow_final_20260715_episodes.csv`,
  SHA256 `68A5CDB4486F8833E9DF140CD1C9D8FBF1FF6A159FC6C6295A5504B2567D2E55`.

### v83 continuity-first deployment rejected

- v83 tried to preserve and immediately deploy a Basic returned by a search
  while Cynthia had only one Pokemon in play. Full trace inspection showed
  that a target-preserving immediate deployment was not a generally correct
  transaction: the clean deployment-only example was a loss, while apparent
  gains depended on changing the search target.
- Historical-Silver performance regressed from `183/600` to `179/600`, with
  paired gains/losses `4/8`. Reject and freeze the deployment-latch family;
  do not recover it with opponent, turn, seat, seed, or outcome filters.
- Root audit:
  `analysis_outputs/cynthia_v83_continuity_first_search_deploy_20260715/ROOT_AUDIT.md`.

### v84 static board-completion handoff rejected

- v84 tested a proactive theory rather than a live-loss patch: after the
  visible Garchomp/Roserade/backup core was complete, stop generic development
  and hand priority to Corkscrew pressure.
- This reduced historical-Silver performance from `183/600` to `149/600`,
  paired gains/losses `5/39`. Both seats and all six 100-game blocks regressed;
  execution and schedule controls were exact, so the result is a policy
  failure rather than a runner error.
- A statically complete board is not a dynamically complete attack engine.
  Continued development can preserve reserve renewal, Energy flexibility,
  disruption recovery, and later attack continuity. Reject and freeze the
  whole v84 handoff family rather than narrowing it post hoc.
- Root audit:
  `analysis_outputs/cynthia_v84_core_complete_pressure_handoff_20260715/ROOT_AUDIT.md`.

### v85 trace-preserved continuity evidence

- Root collected a fresh unused-seed, both-seat, 160-game v80 corpus against
  historical-Silver Archaludon with full traces and legal options. v80 scored
  `45/160`: seat 0 `23/80`, seat 1 `22/80`; all runs completed without action
  errors or max-step hits.
- The checked analyzer had a display-only hard-coded `v23` title and `/100`
  seat denominators. It now uses a generic title and dynamic row counts; the
  underlying game metrics were unchanged.
- Structural correlations are hypothesis generators, not rule labels. No
  Garchomp by Cynthia's own turn 3 occurred in 57 games and won once.
  Garchomp plus Roserade by turn 3 won `39/82`; adding an Energy-bearing backup
  won `12/21`. First Buster with an Energy-bearing backup won `20/37`, versus
  `18/71` without one. Attack gaps after the first attack were uncommon, so
  the leading question is early engine establishment and resilient reserve
  preparation rather than a generic "attack more" override.
- Evidence bundle:
  `analysis_outputs/cynthia_v85_continuity_evidence_20260715`.

### v86 bench-Gabite shelter rejected before implementation

- The delayed-Garchomp trace review found a repeated baseline sequence: when
  an energized Active Gible and one or more Benched Gible could all receive the
  first Gabite, v80 preferred the Active by `20200` over `19000`, used
  Champion's Call, and often lost that only Stage 1 before the next own turn.
- Root converted the observation into a deterministic audit over all 160
  traces. There were 48 public opportunities. The strict post-trajectory set
  contained 35 rows across 31 games, split `13/22` by seat; every row had a
  public Garchomp route, no immediate Active-Gabite KO score, and a later
  Active-Gabite discard. All 35 baseline rows were losses.
- This is mechanism evidence but not a legal trigger. "The Active Gabite will
  be knocked out" is future information. A present-state rule would also fire
  when Gabite survives, while conceding Dragonslice damage, durability, and a
  prize by leaving Gible Active. With no mixed successful controls, Sol Ultra
  rejected v86 before implementation as an outcome-correlated loss marker.
- Do not implement, narrow, package, or submit the bench-Gabite shelter rule.
  Root audit outputs:
  `analysis_outputs/cynthia_v86_bench_gabite_shelter_audit_20260715`.
- The independent Buster-continuity review produced no other non-frozen
  transaction. Its examples reduced to the already tested v46 Full Metal Lab
  correction, v72/v83 reserve preparation, v84 pressure handoff, or terminal
  timing. Start the next proactive cycle on a different deck-theory dimension.

### v80 live role-cycle audit after 40 public games

- The fixed target `54695488` reached `25-15` after 40 public games, score
  `664.1727`. The two newest games, `85983110` and `85982167`, were wins with
  zero v75-v80 action differences across `87` and `53` decisions.
- Root compared every public replay. v80 differed from v75 in 22 decisions
  across 15 games; those submitted trajectories were `9-6`, and v80 matched
  every recorded action. Night Stretcher was selected by v80 in three of the
  differences, split `2-1` by game result.
- Loss `85981103` does not establish overdevelopment. The Stretcher route
  recovered Gabite, completed three Champion's Calls, retained a legal
  Dragonslice, produced two Garchomp ex on the following turn, and preserved
  attacks through turn 12. Cynthia had already fallen three prizes behind;
  Mega Lucario won the two-prize exchange first.
- Freeze the anti-Stretcher/anti-Call idea as unsupported. Detailed root audit:
  `analysis_outputs/cynthia_v80_live_role_cycle_audit_20260715/ROOT_AUDIT.md`.
- A subsequent fixed-ID refresh reached `27-16` after 43 public games, score
  `672.9964`. A new v80-specific win completed Poffin, Roselia/Gible bench
  ordering, Champion's Call, and Poke Pad before Corkscrew. Difference-bearing
  live trajectories are now `10-7`; the anti-development conclusion is
  unchanged.
