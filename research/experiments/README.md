# Experiments Archive

このフォルダは、現在不採用または終了済みの学習系実験を保存する場所です。
現行のKaggle提出候補ではありません。

## Archaludon RL系列

`archaludon_latest_v1_rl*`には、残差PPO、温度調整、PCGrad、行動模倣、
complete-action BC、DAggerなどの記録があります。

最終的に以下が確認されたため停止しました。

- PPOの4、12、24 epoch比較はすべて`261/320`で、実効行動が変化しなかった。
- complete-action BCは`229～248/320`で、基準`261/320`を下回った。
- DAgger round 1後も`745/960`で、基準相当の`81.5625%`へ届かなかった。
- Historical-Silver対面が基準より大きく悪化した。

主要記録:

- `archaludon_latest_v1_rl_pcgrad_candidate_20260801/EPOCH_SWEEP_4_12_24_RESULT.md`
- `archaludon_latest_v1_rl_pcgrad_candidate_20260801/COMPLETE_ACTION_BC_2000_RESULT.md`
- `archaludon_latest_v1_rl_pcgrad_candidate_20260801/COMPLETE_ACTION_BC_DAGGER1_RESULT.md`

## 再開条件

ユーザーが明示的に再許可し、`AGENTS.md`の技術方針を更新した場合だけ、
新しい独立実験として再開します。既存の学習済み候補を決定論的ルールベースの
正式成果物へ混ぜません。
