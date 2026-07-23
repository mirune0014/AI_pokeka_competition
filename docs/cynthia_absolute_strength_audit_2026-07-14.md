# Cynthia/Garchomp absolute-strength audit

## 結論

提出済みv9が576.6まで低下した主因は、単純な実行エラーではなく、候補昇格の評価設計にある。

1. v22以降はv9よりローカルで明確に強いが、strong/exact-live絶対勝率はv35でも44.17%/41.39%に留まる。
2. v23からv35の改善は同一1,440戦で6勝、0.42 percentage pointsしかない。
3. exact-live9は相手の60枚を再現しているが、相手方策proxyの実リプレイ行動一致率は273/506、53.95%しかない。exact deckはexact policyではない。
4. v35はGold方策一致率をv23から改善せず、191/324、58.95%のままである。
5. 決定論的評価を担当したsubagentは試合実行自体を正しく行ったが、集計時にv23へv35の`candidate_win`を転記した。rootが生CSVの`baseline_win`を再集計し、v23を734勝から728勝へ訂正した。

したがって、`candidate_cynthia_garchomp_nasuo445_v35_reliable_development_before_attack_20260714.tar.gz`の次reset自動提出は停止する。Cynthia trackは継続するが、次の作業は狭いルール追加ではなく、相手方策populationと絶対評価基準の再構築である。

## ライブ基準

- Submission: `54630859`
- Agent: Cynthia/Garchomp v9
- Kaggle CLI snapshot: 2026-07-13 23:52 JST
- Status: `COMPLETE`
- Public score: `576.6`
- Public games: 41
- Record: 19-22
- Repeated severe buckets: Starmie/Froslass 1-4、Crustle/control系合算0-4

## 同一schedule絶対評価

全agentを同じengine、opponent、seat、seedで比較した。v9/v22は再実行し、v23/v35は既存paired CSVをrootが生列から再集計した。全1,440戦でaction errorとmax-step hitは0だった。

| agent | strong 360 | exact-live9 360 | broad 720 | total 1,440 | Wilson 95% |
|---|---:|---:|---:|---:|---:|
| v9 | 112 (31.11%) | 107 (29.72%) | 365 (50.69%) | 584 (40.56%) | 38.05-43.11% |
| v22 | 155 (43.06%) | 143 (39.72%) | 422 (58.61%) | 720 (50.00%) | 47.42-52.58% |
| v23 | 157 (43.61%) | 147 (40.83%) | 424 (58.89%) | 728 (50.56%) | 47.98-53.13% |
| v35 | 159 (44.17%) | 149 (41.39%) | 426 (59.17%) | 734 (50.97%) | 48.39-53.55% |

全候補のexact-live9 bucket floorは0%。v35でもepisode 85678570 proxyへ0-40、episode 85688629 proxyへ1-39である。broad平均の高さだけではこの再発bucketを覆えない。

同一ゲームのpaired差分は次のとおり。

| change | gains | losses | net | paired 95% interval |
|---|---:|---:|---:|---:|
| v9 -> v22 | 227 | 91 | +9.44 pp | +7.07 to +11.82 pp |
| v22 -> v23 | 16 | 8 | +0.56 pp | -0.11 to +1.22 pp |
| v23 -> v35 | 6 | 0 | +0.42 pp | +0.08 to +0.75 pp |

v22以降の累積改善は実在する。しかし、v35の追加効果はライブ枠を使うほど大きくなく、strong/exact-liveの絶対値もBronze probeの根拠として弱い。

## Gold replay agreement

| agent | exact matches | decisions | agreement |
|---|---:|---:|---:|
| v9 | 168 | 324 | 51.85% |
| v22 | 183 | 324 | 56.48% |
| v23 | 191 | 324 | 58.95% |
| v35 | 191 | 324 | 58.95% |

v35はGold replay fidelityを改善していない。なおGold行動は絶対教師ではないため、この値単独で昇格させない。ここでは「デッキ理論をGold方策へ近づけた」という主張の検証値として使う。

## Opponent proxy fidelity

exact-live9で使用した各相手agentを、その元になった実リプレイの相手席へ戻して比較した。

| source episode | archetype | agreement |
|---|---|---:|
| 85678570 | Crustle/Munkidori control | 56/78 (71.79%) |
| 85679036 | Starmie/Froslass | 24/47 (51.06%) |
| 85680524 | Starmie/Froslass | 11/28 (39.29%) |
| 85682411 | Starmie/Froslass | 35/60 (58.33%) |
| 85682893 | Cubchoo/Articuno control | 28/64 (43.75%) |
| 85687191 | Crustle control | 25/35 (71.43%) |
| 85688147 | Starmie/Froslass | 39/50 (78.00%) |
| 85688629 | Kangaskhan/Crustle | 24/74 (32.43%) |
| 85691988 | Teal Ogerpon/Clefairy/Crustle | 31/70 (44.29%) |
| total | 9 policies | 273/506 (53.95%) |

この一致率では、exact-live9は「exact deck panel」であって「live policy panel」ではない。特にKangaskhan/Crustleと複数のStarmie/control方策は、デッキだけを合わせた別の相手として動いている。ローカルの小さなpaired gainをライブ改善へ外挿したことが、今回の主要な評価誤差である。

## Live-loss action surface

41試合中22敗、1,212判断を提出v9の再現行動と比較した。v9は全判断でrecorded actionと一致し、replay復元の基準は正しい。

- v9 -> v22: 89判断、20/22敗で変化
- v22 -> v23: 4判断、4/22敗で変化
- v23 -> v35: 3判断、3/22敗で変化
- v9 -> v35: 96判断、20/22敗で変化

v35固有の3判断はStarmie/Froslass 85682411、Crustle control 85687191、Alakazam 85690540に各1回だけである。Starmie 5試合だけを見た以前の「1/250判断」という記録はその範囲では正しいが、全敗戦で見てもv35固有の作用面は3/1,212に留まる。反実仮想勝利の証拠はない。

## Meta-weighted diagnostic

現在41試合の頻度で既存proxy結果をpost-stratifyすると、proxyで覆えるのは34/41試合、82.93%である。Hop/Trevenant 3、unknown 2、Mega Abomasnow/Kyogre 2は未収載である。

| agent | covered-frequency estimate |
|---|---:|
| v9 | 51.37% |
| v22 | 60.67% |
| v23 | 61.30% |
| v35 | 61.86% |

これは独立blind評価ではない。相手proxy自体の行動一致率が53.95%であり、17.07%のライブ質量も未収載なので、提出判断には使わない。むしろローカル推定と576.6の乖離を測るdistribution-mismatch診断である。

## Process correction

低コストsubagentは決定論的なコマンド実行に限定して引き続き利用できる。ただし、以下はrootの必須確認事項とする。

1. `baseline_win`と`candidate_win`を生CSVから別々に再集計する。
2. schedule key `(panel, opponent, seat, seed)`の完全一致を確認する。
3. 相手のdeck hashだけでなく、source replayに対する方策行動一致率を記録する。
4. relative deltaの前に、absolute win rate、bucket floor、seat splitを確認する。
5. 「new episode」「recovering」「archetype」の意味ラベルはrootが元CSV/replayで再確認する。

## 次の実験

1. Starmie/Froslass、Kangaskhan/Crustle、Crustle/controlのpolicy proxyをsource replay単位で再構築する。異なるstyleを平均化しない。
2. 各proxyについてsource replayとheld-out replayのsemantic action agreementを測る。setup、search/evolve、attack、prize conversionを別々に集計する。
3. 再構築populationでv22/v23を再評価する。v35は比較対象として残すが、提出候補にはしない。
4. 次候補は、absolute strong/exact値を実用上改善し、少なくとも1つの反復live-loss bucketを改善し、0%級floorを残さないことを要求する。
5. 既存の盤面形成、resource、prize race、tactical safetyを同時評価し、勝ち筋だけ、または負け筋だけの単一指標へ戻さない。

## Raw evidence

- `analysis_outputs/cynthia_absolute_strength_audit_20260713/root_verified_audit.json`
- `analysis_outputs/cynthia_absolute_strength_audit_20260713/summary.json`
- `analysis_outputs/cynthia_absolute_strength_audit_20260713/v9_raw_per_game.jsonl`
- `analysis_outputs/cynthia_absolute_strength_audit_20260713/v22_raw_per_game.jsonl`
- `analysis_outputs/cynthia_absolute_strength_audit_20260713/opponent_proxy_fidelity_summary.csv`
- `analysis_outputs/cynthia_absolute_strength_audit_20260713/live_loss_action_surface_summary.csv`
- `analysis_outputs/cynthia_absolute_strength_audit_20260713/live_loss_action_surface_aggregate.csv`

## 2026-07-14 root semantic proxy re-audit

The root reran all nine source-policy checks with canonical semantic actions and
immutable input hashes. Raw option-index differences that selected the same
card and meaning are no longer counted as policy errors. The corrected total is
289/506 exact semantic decisions (57.11%), versus the earlier raw-index total
of 273/506 (53.95%). This correction is real but does not change the conclusion
that the panel copies decks more accurately than policies.

Agreement by semantic phase across the nine source replays:

| phase | decisions | agreement |
|---|---:|---:|
| setup | 19 | 68.42% |
| search selection | 74 | 75.68% |
| evolve | 31 | 77.42% |
| attack | 57 | 77.19% |
| main ability | 10 | 0.00% |
| main play | 114 | 42.98% |
| main attach | 61 | 37.70% |
| main end | 54 | 35.19% |

The low main-action figures are not only harmless action reordering. The shared
Starmie proxy omitted Snorunt, Mega Froslass ex, Energy Search, Switch, Black
Belt's Training, and Gravity Mountain despite those cards being present in the
exact deck. It also read `supporterPlayed` from `PlayerState`; the engine exposes
that flag on `State`. Supporter scoring therefore raised `AttributeError` and
the agent silently used its first-option exception fallback. This is a confirmed
opponent-model implementation defect.

A style-isolated hookbook prototype added the missing deck roles and corrected
the state field. Against hookbook's two exact-deck replays, semantic matches
changed from 37/60 and 33/64 to 37/60 and 43/64. On two exact-deck replays from
other players, it changed by -4/39 and -1/43. The result supports keeping policy
styles separate: the prototype is useful for the hookbook bucket but must not
replace every Starmie/Froslass proxy. It is not submission evidence.

An independent July 2 public sample found episode 83281668 (Yushin Ito) with the
same exact deck as source episode 85680524. It remains unused for candidate
tuning and can serve as a held-out policy check for that separate style.

Root-verified outputs:

- `analysis_outputs/opponent_policy_rebuild_20260714/source_fidelity_v1/`
- `analysis_outputs/opponent_policy_rebuild_20260714/hookbook_style_v1b_source_heldout/`
- `analysis_outputs/opponent_policy_rebuild_20260714/hookbook_exactdeck_adjacent_blind_v0/`
- `analysis_outputs/opponent_policy_rebuild_20260714/top_episode_sample_latest/2026-07-02-decks/`
