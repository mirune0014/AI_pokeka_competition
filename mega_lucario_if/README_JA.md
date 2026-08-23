# Mega Lucario If 方策作業メモ

このディレクトリは、既存の Mega Lucario 方策をコピーせずに、次の戦術バッチを設計・検証するための薄い作業領域である。初回調査では戦術 If、汎用 planner、提出物、Kaggle 書き込みを追加しない。

## 基準方策

- 実装参照先: `../mega_lucario_rule_agent/`
- 現在の worktree: `C:/Users/amuam/project/AI_pokeka_competition-megarucario`
- 調査時 HEAD: `c2f3a8e9730b4a94daf24dcd6460f72e63533211`
- 注意: 現在の `codex/megarucario` の HEAD は Archaludon 系先端であり、Mega Lucario の本体は祖先コミット群から継承されている。`reports/PACKAGE_MANIFEST.json` の旧 branch/commit は現 HEAD と一致しない。
- 固定デッキ: `../mega_lucario_rule_agent/deck.csv`（60 枚）。定義は `card_meta.py:DECK_COUNTER` と照合する。
- 提出 entrypoint: `../mega_lucario_rule_agent/main.py:agent`

このディレクトリから本体を import する実装はまだ置かない。候補を採用する際は、本体の route/proposal 層へ最小差分として反映し、同じデッキ・resolver・effect・telemetry を使う。

## 最初に確認した統合位置

- state/options: `mega_lucario_rule_agent/state_view.py:build_semantic_options`, `build_public_state`
- route/proposal: `mega_lucario_rule_agent/routes.py:enumerate_requirement_routes`
- 既存の優先順位: `mega_lucario_rule_agent/resolver.py:proposal_rank_key`（`ResolverTier`、保証 prize、不可逆資源、決定的 tiebreak）
- effect/transaction: `mega_lucario_rule_agent/transactions.py` の各 `build_*_plan` と `public_effects.py:build_public_effect_registry`
- raw action/containment: `mega_lucario_rule_agent/main.py:AgentRuntime._issue_resolution`, `_contained_action`, `act`
- rule 追跡: `Proposal.rule_id` → `resolver.resolve_proposals` の evaluation → `telemetry.py:TelemetryRecorder.record_resolution`, `record_transaction`, `record_fault`

## 次の戦術バッチ候補（実装前）

1. **ML-SEARCH-SUCCESSOR-V1**
   - 目的: Fighting Gong / Ultra Ball / Poké Pad を使って Riolu または次のアタッカーを確保し、ベンチ形成までを一経路で完了する。
   - 既存 rule 候補: `R_SEARCH_FIGHTING_GONG_ROUTE_CRITICAL_V1`, `R_SEARCH_ULTRA_BALL_SAFE_GUARANTEED_V1`, `BASIC_BENCH_ENGINE_COMPLETION`, `BASIC_BENCH_BOARD_OUT_BACKUP`。
   - 主な変更位置: `routes.py:enumerate_fighting_gong_routes`, `enumerate_ultra_ball_routes`, `enumerate_basic_bench_routes`, `enumerate_requirement_routes`。
   - 根拠: 監査 D4 の first-difference 12件中、resource/board sequencing が6件。Ultra Ball と basic bench の差が再現している。
   - 非衝突理由: 検索・後続形成 family に限定し、同ターンの確定攻撃 route の優先順位を直接変更しない。

2. **ML-ATTACK-COMPLETION-V1**
   - 目的: 既に攻撃可能、または Switch・手貼り・PPP・進化で攻撃可能になる場合に、余計な setup を挟まず attack まで完了する。
   - 既存 rule 候補: `DIRECT_ATTACK_COMPLETION_982`, `FALLBACK_LEGAL_ATTACK_982`, `FALLBACK_LEGAL_ATTACK_976`, `R_PPP_EXACT_MINIMUM_BREAKPOINT_V1`, `R_SWITCH_READY_ATTACKER_V1`, `R_ATTACH_002_CONTINUITY_V1`。
   - 主な変更位置: `routes.py:enumerate_attack_routes`, `enumerate_active_attack_completion_routes`, `enumerate_minimal_ppp_routes`, `enumerate_switch_routes`, `enumerate_continuity_attach_routes`。
   - 根拠: D4 の immediate attack before setup/attach 差3件。ただし active attack completion 自体は earliest difference 0で、現時点の強化根拠は未確定。
   - 非衝突理由: attack completion proof を持つ route だけを対象にし、`proposal_rank_key` の既存 tier を維持する。

3. **ML-LINE-CONTINUITY-V1**
   - 目的: Riolu → Mega Lucario ex の進化線、Aura Jab 用エネルギー、次ターンの後続を切らさない。
   - 既存 rule 候補: `R_EVO_MEGA_ATTACK_OR_PROTECTION_V1`, `R_AURA_JAB_CONCENTRATED_COMPLETION_V1`, `R_ATTACH_002_CONTINUITY_V1`, `R_WALLY_THREE_PRIZE_REBOOT_V1`, `R_CAPE_EXPLICIT_PROTECTION_V1`。
   - 主な変更位置: `routes.py:enumerate_evolution_routes`, `enumerate_aura_continuity_routes`, `enumerate_continuity_attach_routes`, `enumerate_wally_routes`, `enumerate_cape_routes`。
   - 根拠: D4 で continuity attach と fallback attack が first difference になった一方、Wally/Cape の自然な selected evidence は未確認。
   - 非衝突理由: 進化・継続資源 family に限定し、prize取得済みの attack route を上書きしない。

4. **ML-END-GUARD-V1**
   - 目的: 合法な attack/transaction の進展が残る状態で不適切な END に落ちない。resolver failure や runtime fault 後は既存 containment を維持する。
   - 既存 rule 候補: `ACTIVE_ATTACK_COMPLETION_RULE_ID`, `SAFE_FALLBACK`, `FAULT_BOUNDARY_REACHED` の観測強化。新しい END 抑制 engine は作らない。
   - 主な変更位置: `main.py:AgentRuntime._decide_checked`, `_contained_action`, `fallback.py`、既存 telemetry。
   - 根拠: 旧 Gong 初動の END 停止は `8c8f43b` で修正済み。監査 D4 では Aura Jab transaction の `UNEXPECTED_CONTEXT_REF` が3戦残存。
   - 非衝突理由: 戦術選択ではなく fault/terminal 境界の安全策として、通常 route のカード優先順位を変更しない。

## 実装前の必須ゲート

監査 D4 の Aura Jab transaction は engine の `contextCard` 契約と不一致で、`UNEXPECTED_CONTEXT_REF` が3戦発生した。次の候補評価前に、この既知 fault を fixture で再現・修正し、同一 seed/seat の paired runner で action error、max-step、runtime/transaction fault をゼロ確認する。候補採用条件は監査報告の `fixed760 net +5以上`、fault 0、両席安全性、主要 matchup floor、意図した rule 起点の gain とする。

## 初回推奨

Aura Jab の fault gate を先に解消した後、最初の If 戦術バッチは **ML-SEARCH-SUCCESSOR-V1** を推奨する。D4 で最も多い差分 family（resource/board sequencing）に対応し、既存の検索・ベンチ・ledger・resolver を一つの経路として検証できるためである。実装・評価・提出は次の指示まで保留する。
