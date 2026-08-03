# venv-ptcg 移行ノート（2026-08-04）

## 目的
- `.venv-rl` を実行環境として参照していた運用経路を、移行後は
  `.venv-ptcg` を基準に統一する。
- 既存の監査・履歴証跡（固定実験ログ、比較レポート、履歴audit結果）は
  変更対象外とし、変更理由と対象範囲を追跡可能にする。

## 現役参照（更新）
- `.codex/agents/ptcg-*.toml`
- `docs/gold_replay_progress.md`（現行実験運用ドキュメントの実行例）
- `alakazam/versions/*/verification/run_c2_action_identity_probe.py`

## 変更しない証跡（保全）
- 過去監査レポート、実験ログ、提案実験の古いREADME/spec、比較結果JSON
  （履歴再現性・監査監視のため）

このノートは履歴との分離を示すために追加し、現行参照の変更先を
`.venv-ptcg` に統一して再現手順を運用可能にする。
