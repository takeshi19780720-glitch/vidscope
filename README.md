# YouTube Data API v3 検索・分析 Webアプリ

FastAPI と YouTube Data API v3 を使って、動画検索と基本メタデータ分析を行うシンプルな Web アプリです。

## 機能
- `GET /api/search?q=keyword&max_results=10`
- 取得項目:
  - タイトル
  - 説明
  - タグ
  - 再生回数
  - いいね数
  - コメント数
  - 公開日
  - チャンネル名
  - サムネイル
  - 動画URL

## セットアップ
1. 仮想環境作成（任意）
   - macOS/Linux:
     - `python -m venv .venv`
     - `source .venv/bin/activate`
2. 依存関係インストール
   - `pip install -r requirements.txt`
3. 環境変数設定
   - `cp .env.example .env`
   - `.env` の `YOUTUBE_API_KEY` に有効な API キーを設定

## 起動
- `uvicorn app.main:app --reload`
- ブラウザで `http://127.0.0.1:8000` を開く

## API 例
- `GET http://127.0.0.1:8000/api/search?q=fastapi&max_results=10`

## 注意
- YouTube Data API のクォータ制限に注意してください。