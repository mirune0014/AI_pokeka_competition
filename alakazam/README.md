# Alakazam Staged Development

Alakazamの段階開発専用ワークスペースです。

## 正式基準

最終戦略判断では、C2のaction pathを提出基準として維持しています。

- 判断レポート: `reports/v4_c5_final_strategy_judgment_20260730.md`
- C2系統のソース:
  `versions/alakazam_newdeck_v4_next_attacker_distance_shadow_fix4b/`
- 固定評価用adapter:
  `eval_adapters/alakazam_newdeck_v4_next_attacker_distance_shadow_fix4b/`

後から作られた`fix7`、`fix8`、`fix9`、v5、v6などは、名前が新しくても
自動的な正式採用ではありません。各`reports/`または`specs/`の採否を確認します。

## フォルダ

| フォルダ | 用途 |
|---|---|
| `versions/` | 候補ソースと段階的修正 |
| `reports/` | 数値評価と最終判断 |
| `specs/` | 固定比較契約、要件、amendment |
| `fixtures/` | 公開局面を再現する入力 |
| `eval_adapters/` | 固定評価用の実行入口 |
| `diagnostics/`、`first_divergence/` | 差分診断 |
| `evaluations/`、`metrics/`、`submissions/` | ローカル生成物。Gitでは原則無視 |

## 新しい開発

新候補は`versions/`に独立フォルダを作り、親、仮説、採否条件を`specs/`に
固定してから実装します。正式採用になった候補は、このREADMEの正式基準を
更新して一意に示します。
