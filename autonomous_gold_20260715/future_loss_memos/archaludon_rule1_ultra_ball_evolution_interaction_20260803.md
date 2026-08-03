# Rule 1後のUltra Ball進化先相互作用メモ

Date: 2026-08-03 JST

固定760の`arch_shumpei / seat 1 / game 32 / seed 271958345`では、Rule 1の
初期Duraludon配置後、Historical-Silver由来のUltra Ball検索がArchaludon exではなく
重複Duraludonを選び、早期進化を失った。

これはRule 1の初期配置自体を明確な悪手とする証拠ではない。同じ初期手札形状が
Kangaskhan戦ではgainを生み、直接の勝敗因果も中信頼である。一方、進化可能な
Duraludonが既に場にいるUltra Ball局面で「追加Basic」と「即時進化札」を比較する
独立課題としては再検討価値がある。

現v1には追加しない。拒否済みRule 3を補修して積み直さず、将来版で次を満たす一規則
としてのみ検証する。

- 公開情報だけで今ターンまたは次ターンの進化・攻撃継続が証明できる。
- 追加Basicの盤面継続価値と進化札の即時価値を同時に比較する。
- Rule 1を一律停止しない。
- 同じinitial shapeで観測されたKangaskhan gainを潰さない。
- 不明・同値・検索後経路未完結ではHistorical-Silverへ戻る。
