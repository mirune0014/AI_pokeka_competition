## Material Passport

- Origin Skill: experiment-agent
- Origin Mode: plan
- Origin Date: 2026-08-01
- Verification Status: UNVERIFIED
- Version Label: code_plan_v1

# PPO epoch一括比較計画

iteration004を学習開始点およびbaselineとし、4・12・24 epochを3個の独立したfresh-rollout seedブロックで比較する。

各seedブロックでは1つの新規32試合rolloutから3条件へ分岐する。
これにより、同じ学習seed内ではepoch数だけが変わる。
学習率、報酬、相手集団、初期checkpoint、データ量は固定する。

評価は未使用seed 20個、8相手、両席で行う。
各checkpointは320試合、iteration004を含む全10 armで合計3,200試合となる。
学習rolloutを含む総試合数は3,296試合である。

報告対象は総勝率、iteration004とのpaired差、相手別勝率、席順別勝率、平均ターン数、行動エラー、最大手数到達、重大異常行動率に限定する。
重大異常行動は「保護されたdecisionで最終行動がteacher行動と異なること」と事前定義する。

個別試合、個別局面、行動確率、全行動一致は分析しない。
条件間で再現性のある明確な性能差が出た場合に限り、別工程で原因分析する。
