# Phase 0実装検証記録

検証日は2026年7月31日です。

この記録は、収集とPPO更新の実行契約を検証したものです。

方策の強さを検証したものではありません。

## 固定した開始点

最新v1の実体は次の3件で固定しています。

| 対象 | SHA-256 |
|---|---|
| `candidate_exact/main.py` | `AC70708082882C7BA01CFBF81D29F534B95166DFF6BAD11E1EF1FA001A5F79D2` |
| `candidate_exact/deck.csv` | `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A` |
| `submission_archaludon_general_visible_counterattack_ready_rotation_v1_20260731.tar.gz` | `B2992E4A5F97A14127F6E75D4D3F3F528725E34ABC9854F06592B82D8EA24C95` |

seeded checked engineのimmutable runtime manifestは `DAAD95164512EA3F210B4679840FE2CD631300044A6E5F49C41642EABD823089` です。

チェックポイントは、上記の最新v1とengine manifestをまとめてsource receiptとして保持します。

## 現在のschema

現在の有効schemaは次のとおりです。

| 対象 | schema |
|---|---|
| state/action encoder | `encoder-v4` |
| named effect | `effect-features-v3` |
| trajectory | `trajectory-v2` |
| run manifest | `run-manifest-v2` |

状態ベクトルは104次元です。

行動ベクトルは102次元です。

## 静的検証

`unittest` は39件すべて通過しました。

`compileall` も通過しました。

主な検証範囲は次のとおりです。

- 公開情報だけを使うstate projection
- hidden情報とserialの非干渉
- option順序の置換同変性
- 同一カードID・異なる対象の行動分離
- 実encoderと実modelによる非教師行動へのargmax反転
- effectの保守的な `UNKNOWN` 伝播
- Basicのベンチ増加をPLAYにだけ付与するaction conditioning
- 全合法候補のfull support
- train/deployの適格性と50ms timeoutの一致
- NaN、schema failure、invalid selectionの最新v1 fallback
- teacher 1-callとtelemetry 1-row
- clean terminalと最後の適格行への報酬接続
- 別checkpoint、deployment run、teacher-only dataset、偽装挙動行の拒否
- engine receipt、schedule、episode byte、extra/missing/mixed/duplicate fileの拒否
- unsafe run IDとunsafe relative pathの拒否
- PPO更新後KL hard stopのrollback

## action-conditioned effectの回帰確認

checked engineのBasicカード169と通常攻撃223を使う回帰testを追加しました。

カード169をPLAYする候補では `board_bench_delta=KNOWN, value=1` になります。

カード169が攻撃223を使う候補では、この値を継承しません。

実収集episodeにも攻撃223が3候補含まれました。

3候補中、`board_bench_delta=KNOWN, value=1` は0件でした。

## ゼロ残差checkpoint

現在のゼロ残差checkpointは `analysis_outputs/archaludon_latest_v1_rl_phase0_v2_collection_pilot_20260731/initial_zero_v2.pt` です。

SHA-256は `3E86A5B764C2CD654DCF681C4EB83E3C9CBDFBC43CBD4ED5071012EF10F51803` です。

## 最新v1とのゼロ更新一致

`analysis_outputs/archaludon_latest_v1_rl_phase0_v2_zero_checkpoint_action_parity_20260731` で、最新v1本体とゼロ残差modelを実際にロードしたwrapperを比較しました。

両席ともexact側とwrapper側のJSONLは146,732バイトでした。

4ファイルのSHA-256はすべて `836777A2577ADB7E5A1048B7710EA255694D24791878E8AE6E87935CB952B7AF` で、byte-identicalです。

checked paired reportは `analysis_outputs/archaludon_latest_v1_rl_phase0_v2_zero_checkpoint_parity_checked_20260731/report.json` です。

reportのSHA-256は `A3A7922A0259FC9C39B73837774619A6135AB832F3EF44978BC840AB649D133D` です。

reportは `valid: true`、両席、action errorなし、max-step hitなし、duplicate mismatchなしです。

## 実収集pilot

収集manifestは `analysis_outputs/archaludon_latest_v1_rl_phase0_v2_collection_pilot_20260731/rollouts/run_manifest.json` です。

manifestのSHA-256は `AEF930FFDAEE705D471DCA7608EF04282B6E2FC236CC0FFFC65AAFD698D833EA` です。

collection specのSHA-256は `27F6B55FAEEFDDA4BCD016D1CD4D10595F87A5DDC43D4A6339D46B6B95BA3B8A` です。

datasetのSHA-256は `3EE037AC4649BA035D040067173834A35D05923554A646860E0A289AA17D4D59` です。

同一seedのA/B複製を両席で実行しました。

| 席 | decisions | PPO eligible | terminal | duplicate |
|---:|---:|---:|---|---|
| 0 | 86 | 43 | clean | equal |
| 1 | 71 | 43 | clean | equal |

教師呼び出しは合計157回です。

保存した教師telemetryも合計157行です。

teacher call count、telemetry row count、checkpoint receipt、encoder schemaの不一致はありません。

失敗台帳は作られていません。

公開episodeのSHA-256は次のとおりです。

| 席 | SHA-256 |
|---:|---|
| 0 | `CAEF242703CB768AE0D2EA92454E17F4F8C226CAE3AFB3EEDB7DA9C88BD79E0D` |
| 1 | `57994589ADC140EF2022FB00E764573FE48DFA6E5FDDA6A4FDEBF5C4828E2628` |

## manifestによるdataset closure

collectorは空の出力先だけを受け付けます。

収集中は不完全なpending manifestだけを置きます。

全episodeのatomic publishとreceipt作成後に、pending manifestを最終 `run_manifest.json` へatomic replaceします。

最終manifestは、source、engine、checkpoint、opponent、schedule、各episodeの相対パス、byte数、SHA-256、identity、dataset SHA-256を保持します。

trainerは `--manifest` だけをdataset入口として受け付けます。

trainerは現在のfrozen sourceとengineを再検証し、manifest、入力checkpoint、schedule、dataset hash、episode header、`episodes/` の完全ファイル集合を照合します。

未記載file、欠損file、1 byte改変、重複ID、重複 `(seat, seed)`、run混在、path traversalを拒否するnegative testが通っています。

`audit/` の複製記録はtraining file setに入れません。

## 最新v1ルール所有の実証

`analysis_outputs/archaludon_latest_v1_rl_phase0_v2_owner_duplicate_20260731` で、seed `731200101`、seat 0をA/B複製しました。

正規化した意思決定列のSHA-256はA/Bとも `CF448D13EE352A5DA25F16DFDCA8A42DAA496CB100C82711DC115D988613E3C4` です。

decision 83では `GENERAL_VISIBLE_COUNTERATTACK_READY_ROTATION_V1` が所有権を取得しました。

RL側は `final_action == teacher_action == [4]`、`ppo_eligible == false`、`protected == true` としました。

decision 84では同ルールの所有終了が通知されました。

RL側は `final_action == teacher_action == [0]`、`ppo_eligible == false`、`protected == true` としました。

episodeはclean terminalで、88 decisions中45行だけがPPO eligibleでした。

episodeのSHA-256は `8E43E11005D3858C0EFCD72AB4F883E58282FD11A49F2A61770C06C4565DE37F` です。

失敗台帳は作られていません。

## PPO更新pilot

両席の86 on-policy行を使い、1 epochだけ更新しました。

trainerは入力checkpointからstate、action、residual、value、`q_latest`、最終確率、behavior log probabilityを再計算してから受理しました。

入力checkpointのSHA-256は `3E86A5B764C2CD654DCF681C4EB83E3C9CBDFBC43CBD4ED5071012EF10F51803` です。

出力checkpointは `analysis_outputs/archaludon_latest_v1_rl_phase0_v2_collection_pilot_20260731/ppo_v2_pilot_001.pt` です。

出力checkpointのSHA-256は `9C7FDD69FC5409DFE6BED401032E5890E392705EB26135307415781D1AA03204` です。

更新後anchor KLは `4.785661076311953e-07` でした。

hard stopによる打ち切りやrollbackは発生していません。

出力checkpointにはmanifest SHA、collection spec SHA、schedule SHA、dataset SHA、全episode receipt、全PPO設定を保存しました。

出力checkpointは同じsource receiptとencoder schemaで再ロードできました。

`analysis_outputs/archaludon_latest_v1_rl_phase0_v2_ppo_checkpoint_runtime_smoke_20260731/report.json` の両席runtime smokeも `valid: true` でした。

この2局の勝敗は強さ判定には使いません。

## 旧pilotの無効化

`encoder-v3`、`effect-features-v2`、`trajectory-v1` で作成した旧pilot datasetとcheckpointは継続学習に使いません。

旧ゼロcheckpoint `F31E4190...` は、現在のloaderで `checkpoint encoder schema/dimension mismatch` として拒否されることを確認しました。

旧PPO checkpoint `87E5E15B...` も学習成果としては破棄扱いです。

## 判定

Phase 0の収集契約とPPO更新契約は実行可能です。

少量のon-policy収集と保守的な学習実験を開始できます。

独立した最終監査でも、新しいP0/P1 blockerなしのPASS判定でした。

ただし、`ppo_v2_pilot_001.pt` を最新v1より強い候補として昇格させる根拠はまだありません。

次段階では、先にtrain/eval seed、対戦相手集団、収集量、KL上限、昇格条件を固定し、未使用seedのpaired evaluationを行います。

## 既知の副作用

初回のworker smokeで、ignoredかつuntrackedの `analysis_outputs/traces/game_0000.jsonl` が上書きされました。

trackedな復元元は見つかりませんでした。

その後の全シミュレーションでは専用のtrace directoryを明示しています。

Kaggle package、upload、submission、DiscussionやNotebookの外部書き込みは行っていません。
