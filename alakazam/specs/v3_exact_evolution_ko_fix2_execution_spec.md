# v3 進化後確定KO優先 fix2 実行仕様

## 凍結identity

- 不変仕様:
  `alakazam_staged_20260729/specs/v3_exact_evolution_ko_fix2_immutable_spec.md`
- 不変仕様 SHA-256:
  `64B0E5459816954E81CC55853BABE68FD2D23C6413AB6D01D64F88E6EBFF47E9`
- 親:
  `alakazam_staged_20260729/versions/alakazam_newdeck_v3_psychic_draw_optional_fix1`
- 親 policy closure:
  `7124EA621B02E58D9143149A33EAA79DB44E1AEF6D206560D17BA7146DF7D590`
- 親 planner:
  `4C6F246A256A7C6B327ECFCB81E507E0E1D9E62D8B99D28FAF444BF3AAEA1929`
- 候補:
  `alakazam_staged_20260729/versions/alakazam_newdeck_v3_exact_evolution_ko_fix2`
- 候補 policy closure:
  `DC90205DE06AE3E2E41ADC661577096BB02EE5B42AB9F4366FC1A01154745B47`
- 候補 planner:
  `255FD9E1303E8E6DFB286952023A7F086CD233B4E5D5030EDBE06313A40697B7`
- 候補 focused test:
  `test_v3_exact_evolution_ko_fix2.py`
- focused test SHA-256:
  `A8ABFF15D89658FF340484369BEBAD07BDB8D86D9481D1BE78D8383D5A5EAB7F`
- 共通 deck:
  `F598F5E578D0440C96DC0492EAECF2E19739B7A23225BE57114A724EF7D0FB94`
- replay:
  `C:/Users/amuam/Downloads/88844273.json`
- replay SHA-256:
  `9E749F259D90655BE4C17F1795C15D277132C02E0167310394216609B90A7EBF`
- Python:
  `C:/Users/amuam/project/AI_pokeka_competition/.venv-rl/Scripts/python.exe`
- engine/PYTHONPATH:
  `C:/Users/amuam/project/AI_pokeka_competition/analysis_outputs/cynthia_v9_vs_v11_poffin_role_selection_20260713/seeded_engine`
- engine tree SHA-256:
  `466638706BD5C6915E25D1B3CB9E3D966390FBC263F4ED3153108E29C0194FFF`

## 出力先

`alakazam_staged_20260729/evaluations/v3_exact_evolution_ko_fix2/runner_recheck_attempt_1`

既存のsource、fixture、spec、他のevaluationを変更しない。

## 実行順

全Pythonコマンドでengine directoryを`PYTHONPATH`の先頭へ入れ、`PYTHONDONTWRITEBYTECODE=1`を設定する。

1. 候補focused:

   ```text
   python.exe -B -m unittest -v test_v3_exact_evolution_ko_fix2.py
   ```

   cwdは候補ディレクトリ。期待件数は11。

2. 候補full:

   ```text
   python.exe -B -m unittest discover -v -p test_*.py
   ```

   cwdは候補ディレクトリ。期待件数は166。

3. 親full:

   ```text
   python.exe -B -m unittest discover -v -p test_*.py
   ```

   cwdは親ディレクトリ。期待件数は155。

4. 変更source compile:

   `planner_deck_adaptation_v1.py`と`test_v3_exact_evolution_ko_fix2.py`をUTF-8で読み、Python組み込み`compile()`を使う。`.pyc`は生成しない。

## raw evidence schema

各コマンドについて次を保存する。

- command
- cwd
- effective `PYTHONPATH`
- `PYTHONDONTWRITEBYTECODE`
- start/end timestamp
- exit code
- stdout path、byte count、SHA-256
- stderr path、byte count、SHA-256
- unittestの場合は末尾の`Ran N tests`と`OK`をそのまま記録

全体を`execution_manifest.json`へ保存する。

## 合格条件

- 4コマンドすべてexit code 0。
- focused 11、候補full 166、親full 155。
- checked-engine testを含むfocused suiteでfailure/error 0。
- compile対象2ファイル。
- source、fixture、specを実行中に変更しない。

この実行は機構・回帰検証であり、勝率または採用判断を行わない。
