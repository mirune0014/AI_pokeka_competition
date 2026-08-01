# Phase 0の収集・学習開始条件

## 実装済み

- [x] 最新v1のmain、deck、archiveをSHA-256で固定した。
- [x] seeded checked engineの実行ファイル11件をmanifestで固定した。
- [x] ゲーム・席ごとに最新v1教師を隔離した。
- [x] 1コールにつき最終 `agent` を1回だけ呼び、直後にテレメトリをdrainする。
- [x] 公開情報だけをseat-relativeにprojectionする。
- [x] 不透明なengine入力、非公開カード、deck順、serial、RNGを方策特徴から除外する。
- [x] エンジンが提示した全合法候補を保持する。
- [x] 同じカードIDを異なる対象へ使う行動を別の行動ベクトルにする。
- [x] 状態104次元、行動102次元の固定encoder schemaを実装した。
- [x] 効果を `KNOWN`、`UNKNOWN`、`NOT_APPLICABLE` で区別する。
- [x] 未実装のカードテキストを既知の0として扱わない。
- [x] Basicのベンチ増加をPLAYにだけ付与し、ATTACKへ継承しない。
- [x] 全合法候補に正の確率を持つ最新v1事前分布を実装した。
- [x] 実encoderと実modelで、教師が選ばなかった行動をargmaxへ反転できることをテストした。
- [x] 学習と配置で同じ適格性判定とfallback契約を使う。
- [x] free MAINの `rank17_exact_parent` だけをPPO対象にする。
- [x] 最新v1のルール所有、retry、reset、rollback、例外、緊急処理を保護する。
- [x] 終局局だけをatomicに公開するcollectorを実装した。
- [x] source、engine、checkpoint、opponent、seat、seed、scheduleをmanifestへ記録する。
- [x] 全episodeの相対パス、byte数、SHA-256を最終manifestへ記録する。
- [x] 最終manifestをdatasetのcommit markerとしてatomic publishする。
- [x] 同一seed・同一方策乱数のA/B正規化トレース照合を実装した。
- [x] trainerが入力checkpointから挙動分布とvalueを再計算する。
- [x] teacher-only、deployment-mode、別checkpoint、偽装挙動行を拒否する。
- [x] PPO更新後にanchor KLを再計算し、hard stop超過時にmodelとoptimizerをrollbackする。
- [x] チェックポイントなしでは最新v1行動へ完全に戻るruntime wrapperを実装した。

## 収集開始ゲート

- [x] 固定sourceの検証がcollection hostで通った。
- [x] unit test 39件とcompileallが通った。
- [x] ゼロ残差checkpointのroundtripで残差が0になった。
- [x] checkpointなしの実戦トレースが最新v1と両席でbyte-identicalになった。
- [x] ゼロ残差checkpointを実際にロードした実戦トレースが最新v1と両席でbyte-identicalになった。
- [x] checked paired runnerが両席でvalid、action errorなし、duplicate mismatchなしになった。
- [x] 実収集のA/B正規化トレースが両席で一致した。
- [x] run manifestにsource、engine、checkpoint、schema、seat、seed、modeを記録した。
- [x] manifestのepisode集合と `episodes/` の完全ファイル集合を一致させた。
- [x] checkpoint hashが空の局をPPOへ入れないことを確認した。
- [x] 実最新v1の `GENERAL_VISIBLE_COUNTERATTACK_READY_ROTATION_V1` 所有コールを保護した。
- [x] 所有開始と所有終了の両コールで `final_action == teacher_action` かつ `ppo_eligible == false` を確認した。

## 学習開始ゲート

- [x] 入力局がterminal、clean、atomic publish済みである。
- [x] 入力局のsource、engine、checkpoint、encoder schemaが一致する。
- [x] PPO行がtraining-modeの実サンプリング行である。
- [x] PPO行にbehavior log probabilityとvalueがある。
- [x] PPO行が非保護、非fallback、free MAIN、rank17である。
- [x] teacher callが1回、telemetry rowが1行である。
- [x] 最終PPO行だけがclean terminal transitionになっている。
- [x] trainerによる状態、行動、残差、value、参照分布、挙動分布の再計算が通った。
- [x] engine、schedule、episode byte、extra/missing/mixed/duplicate、unsafe pathの改変拒否testが通った。
- [x] 86 on-policy行を使う1 epochのPPO更新が完了した。
- [x] 更新後anchor KLがhard stop未満である。
- [x] 更新checkpointをsource receipt付きで再ロードできた。
- [x] 更新checkpointにmanifest SHA、dataset SHA、全PPO設定を保存した。
- [x] 更新checkpointを配置した両席runtime smokeがvalidになった。
- [x] 独立した最終監査で新しいP0/P1 blockerなしのPASS判定を得た。

## Phase 0の判定

少量のon-policy収集と、保守的なPPO実験を開始できます。

この判定は、学習後方策が最新v1より強いことを意味しません。

各checkpointの採否には、固定した相手集団、同一seed、両席、未使用seedによる別の強さ評価が必要です。

## 次の実装

- opponent populationとtrain/eval seedを固定した実験spec
- checkpointごとの収集量、KL上限、打ち切り条件
- latest-v1、Historical-Silver、追加の完全な過去agentに対するpaired evaluation
- 学習した変更局の抽出と、人間が読める差分レポート
- 未知効果が多い頻出カードだけを対象にした明示的effect contract
- 複数checkpointを混ぜない世代管理とpromotion ledger

## Phase 0の範囲外

- engine search/cloneを使うcounterfactual search
- 最新v1のルール所有境界を緩めること
- replayを正解行動ラベルとして模倣すること
- Kaggle package、upload、submission、既存submissionの置換
