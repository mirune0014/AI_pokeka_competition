# ポケカ公式ビジュアライザー 日本語カード表示

Kaggle のポケカコンペで、提出一覧やリーダーボードから開いた**公式ビジュアライザー**を自動で日本語表示するローカル Chrome 拡張です。

導入後は対戦履歴の JSON や episode ID を手入力する必要はありません。

## 使い方

1. 配布 ZIP を展開します。
2. Chrome では `chrome://extensions`、Edge では `edge://extensions` を開きます。
3. 右上の「デベロッパー モード」を有効にします。
4. 「パッケージ化されていない拡張機能を読み込む」を押します。
5. 展開した `ptcg-japanese-visualizer-extension` フォルダーを選びます。
6. Kaggle の提出一覧またはリーダーボードから対戦履歴を開き、`Open Visualizer` を押します。

`https://ptcgvis.heroz.jp/Visualizer/Replay/...` が開くと、次が自動で日本語になります。

- 盤面・手札などのカード画像
- カード名
- ワザ名
- ログと選択欄に現れる既知のカード名・ワザ名

右上に「日本語カード表示」と出れば拡張が動作しています。

### 旧版から更新する場合

`0.1.0` では公式ビジュアライザーが画像を XHR で読み込むため、カード画像だけ英語のままになる不具合がありました。`0.1.1` で修正済みです。

1. 新しい ZIP を別の場所へ展開します。
2. 拡張機能の管理画面で旧版を削除します。
3. 新しく展開したフォルダーを「パッケージ化されていない拡張機能を読み込む」で選びます。
4. 開いている公式ビジュアライザーを再読み込みします。

## 安全性と対象範囲

- 対戦履歴を外部サーバーへ送信しません。
- Kaggle の提出、対戦結果、Notebook を変更しません。
- 対象 URL は公式ビジュアライザーの Replay ページだけです。
- 日本語画像と日英対応表は、コンペで配布されている `Card_ID List_JP.pdf`、`EN_Card_Data.csv`、`JP_Card_Data.csv` から生成しています。
- 個人のローカル閲覧用途を前提としています。カード画像を含む ZIP の公開・再配布は避けてください。

非公式の別ビジュアライザーを公開する方式ではなく、コンペ運営が案内している公式ビジュアライザー上の表示だけを差し替えます。利用時は最新のコンペ規約も確認してください。

## データの更新

コンペ側のカードデータが更新された場合は、次の順で再生成できます。

```powershell
python -m pip install pymupdf pillow

node .\scripts\build-data.mjs `
  "C:\path\to\EN_Card_Data.csv" `
  "C:\path\to\JP_Card_Data.csv" `
  .

python .\scripts\extract-japanese-card-images.py `
  "C:\path\to\Card_ID List_JP.pdf" `
  .
```

テストと ZIP 作成:

```powershell
node .\tests\test-core.mjs
.\scripts\package.ps1
```
