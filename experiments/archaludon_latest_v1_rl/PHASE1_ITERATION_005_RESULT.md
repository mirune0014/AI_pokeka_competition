# Phase 1 Iteration 005 結果

## 結論

Iteration 005 の1回限りの保守的PPO更新は `REJECT` とする。

更新処理、保存処理、Adam状態、830行の更新後推論は正しく再現されたが、リターンが正の正当なEND判断20件すべてでEND確率が低下した。

生成した `candidate.pt` は採用、次反復の開始点、runtime smoke、Kaggle提出のいずれにも使用しない。

## 固定した入力

- 初期checkpoint: `24D8A4EACD9D7B699D327D3F2436F4DA21AC79433038E6FA96F9AE0E50F8FB04`
- manifest: `30BF22BE56E73E8790A40135DD78080217FFAB7598D9646887FD8742D0FCF393`
- dataset: `3D714FC248B597ADD412B1D9B4BAD60DDF6BDEB3DFA652264D763D7A843AC41B`
- base plan: `E47800D5842FDEB0E49B9C0CBC6A4F55D334091DF6D79C253941DCFC28047577`
- provenance correction: `C18C2985EF114746A794A3EB0F9C13058A7266C7C240CF28A2B4A3736BAB4FD8`
- v4 prepare receipt file/self: `63E8599248E62FFD80D548A65109EBCE05E164463FA218C41B33F335D76DC322` / `CD7D8A8E8CA037E0A9D8036C2221AB336CB7F8BEDDA43D765F33F0EEEDD2D0E9`
- execution spec: `D6A67C3A8791BA2A4B6002446E915D2484E32483984FF4C7FF4E8F34FAC72BCB`

実装snapshotは相対POSIXパスのUTF-8バイト順で固定した。

Source snapshotは46ファイルで `FA6BE7FB76977C60D89F5D0505AC7CDE9656442F96905666E6F7605A8EDC2985`、candidate snapshotは49ファイルで `2197C82DF499EE3026F960C6A1690094A2EF5D4FB4863E07267E025BE2BDF940` だった。

旧値 `2B4E0795439843A69ED78EA3EA1567C791271EFEFBF2E4662940CB93F2E5F1BB` はWindows依存順序による履歴値としてのみ保持した。

## 実行結果

凍結した830行をmanifest順の1バッチとして、CPU 1スレッド、fresh Adam、1 optimizer stepで正確に1回だけ更新した。

ゲーム対戦は実行していない。

実行はexit code 2を返し、正規の `rejected` 証跡を生成した。

- output checkpoint: `E7D0CA4DCEEBE33C8043D3C8A45DD9119CFE0E06ACC58F343E9A60BB7F787088`
- rejected receipt file/self: `9E3EEE5F64FD7B38B9A9BBF0C1CD7A3C7C959CC4FA6C4D652B859EE77E44FC93` / `DAE29284F5DA13C5A330A539A0E218B88F698E835EC2D57EFC5FE9DF505AEE39`
- `REJECTED` marker: `280994B23F0ABF8512BB2FB9334A02D27972D4DB8DF7A5E9FFB3650212C85150`

Adamの14 stateはすべてstep 1で、初回更新式から再構成したパラメータと保存checkpointは全要素一致した。

変更されたモデルtensorは10個で、全パラメータと勾配は有限だった。

## 更新後ゲート

4件の明示的な負例では、END確率が `-8.38e-6` から `-9.43e-6` 低下し、教師のsetup行動確率が増加した。

一方、normalized advantageが正の正当END 20件は20件すべてでEND確率が低下し、変化量は `-9.73e-5` から `-3.70e-6` だった。

Raw advantageが正の正当END 31件における変化量の中央値は `-1.5437602996826172e-5` だった。

正当END 43件の一意argmaxは43件すべてで維持した。

全体変動は小さく、mean KLは `1.4739578054211144e-7`、max KLは `5.71420020043731e-7`、max TVは `0.0002245609648525715` だった。

したがって失敗原因は更新量の過大さではなく、最初のactor更新が文脈別の正負を分離できず、END全体を同方向へ動かしたことにある。

## 次の仮説

Iteration 006 は初期checkpointへ戻り、「共有encoderを許容するactor-only二段階ブートストラップ」だけを検証する。

第1ステップではゼロ初期化された `residual_head` 最終層だけを更新し、第2ステップでは同じAdam状態を引き継いで `state_encoder`、`action_encoder`、`residual_head` をactor損失だけで更新する。

`value_head` はoptimizerから除外してbyte-exactに固定し、value lossは0とする。

同一iteration内の再試行、大量対戦収集、runtime smokeは、Iteration 006 のofflineゲートを通過するまで行わない。
