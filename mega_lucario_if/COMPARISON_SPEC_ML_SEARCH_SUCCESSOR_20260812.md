# ML-SEARCH-SUCCESSOR-V1 比較仕様

## 固定した入力

- baseline source: `c2f3a8e9730b4a94daf24dcd6460f72e63533211`
- baseline tree: `f24058245177abf24c3e156ac688e1909a78bd0b`
- baseline agent: `mega_lucario_rule_agent/`（deck SHA-256 `5ddb7ca2790518e3c1eac6e2ff8b7fdb6ff0a817bf888536349a090ec7582a9f`）
- parent absolute reference: `4cfdffae54561c9b6b054f4a9d461536ef573385`
- candidate worktree: `C:/Users/amuam/project/AI_pokeka_competition-megarucario-search-successor-v1`
- engine: `C:/Users/amuam/project/AI_pokeka_competition/_local_generated/analysis_outputs/cynthia_v9_vs_v11_poffin_role_selection_20260713/seeded_engine/`
- engine `cg/cg.dll` SHA-256: `0c6153f9206366f2588e5c601ab086ea997a66e80e4feb6d95635b2987c9929b`
- seeded engine `cg/game.py` SHA-256: `b88e6e0223ff8fcbb789f6b2b094b9556b2725a624ac69ae5c367ce822f1e3bc2`

## 候補の分離

- B0: 現行HEAD + Aura Jab context receipt 修正のみ。
- C1: B0 + `ML-SEARCH-SUCCESSOR-V1` の4 rule。
- B0 commit: `2030b96` (B0 context fix + KO後終端receipt修正; source commit `7fee00c47edd6d6a6a4789b53986a17ff1878143` をcherry-pick)
- C1 commit: `7fee00c47edd6d6a6a4789b53986a17ff1878143`
- B0 fixed worktree: `C:/tmp/mega_lucario_b0_fixed_20260812`
- ルールID: `R_BENCH_SUCCESSOR_RIOLU_V1`, `R_SEARCH_SUCCESSOR_POKE_PAD_RIOLU_V1`, `R_SEARCH_SUCCESSOR_FIGHTING_GONG_RIOLU_V1`, `R_SEARCH_SUCCESSOR_ULTRA_BALL_RIOLU_V1`。
- B0とC1は別commitにし、B0の fault gate と C1の戦術効果を分離する。

## 保留中の評価入力

- historical Silver: `archaludon/baseline/historical_silver_archaludon_54495224` 相当。
- adjacent: `arch_peak`, `arch_shumpei`, `alakazam_capbloo_gold`, `marnie_kazuki_live`, `mega_lucario_public`, `kang_crustle`, `cynthia_v23`。
- 新規holdout topology: historical 100 seeds/seat、adjacent各40 seeds/seat、両席、各cell duplicate baseline、合計760 unique keys。
- seed base: historical `1732050807`、adjacent `1732051007`（既存D3/D4のseed baseと重複させない）。
- B0 fixed preflight: arch_peak seat1 40 games, seed `1732051007`; 40/40 completed, validation/runtime/transaction/action faults 0, max-step 0. Reproduced game4 seed `1732051011` now completes Aura transaction.
- max steps `1000`、trace options `true`、traces `true`。
- 対象キー、engine seed API、全opponentパスとhashは実行前に再検証する。上記engineの `BattleStartSeeded` が使用可能であることをpreflightで確認済み。

## 採用ゲート

schedule equality、baseline duplicate完全一致、runtime/transaction/action fault・max-step 0、C1-B0 paired net `>=+5`、絶対勝数がparent reference以上、historical/adjacent・両席の悪化なし、2以上の独立bucketで新rule起点のgain、をすべて満たす場合だけ採用候補とする。
