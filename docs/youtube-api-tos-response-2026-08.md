# YouTube API コンプライアンス審査 違反対応報告書

- 対象: VidScope（YouTube Data API利用アプリケーション）
- 元審査レポート: `docs/youtube-api-tos-violations-v1-2026-08-08.pdf`
- 対応期限: 2026-08-19（7営業日以内）
- 本文書の用途: Googleへの返信作成の素材

---

## 違反① III.D.1c — 複数プロジェクト番号の使用について

**指摘内容**: このAPI Clientで複数のプロジェクト番号を使用しているか。

**回答**:
本API Clientで使用しているGoogle Cloudプロジェクト番号は **`484828457875`の1つのみ** です。複数のプロジェクト番号を使い分けている事実はありません。

VidScopeのAPIキー管理機能（設定モーダル内「複数キーの登録」）は、同一プロジェクト内で発行された複数のAPIキーをクォータ超過時にローテーションするためのものであり、複数のプロジェクト番号を使用するものではありません。

**修正**: コード修正は不要（違反状態ではないため）。

---

## 違反② III.C.1 — サムネイル最小サイズ 120×70px

**指摘内容**: 再生を開始するYouTubeサムネイルは最低120px幅×70px高でなければならない。

**問題箇所**:
1. リスト表示（テーブル形式）のサムネイル: `.list-thumb-wrap` が固定 `80px × 45px` で表示されており、**明確に違反**していた。
2. 急上昇TOP10表示のサムネイル: `.top10-card` の `min-width: 120px` に対し、サムネイルは16:9アスペクト比のため最小時に高さが約67.5pxとなり、**70px未満で違反**していた。
3. カード表示（メインの検索結果グリッド）のサムネイル: グリッド最小幅280px（16:9で約157px高）のため通常時は問題なかったが、極端な低解像度環境でも保証されるよう安全策を追加。

**修正内容**:
- `static/style.css` の `.list-thumb-wrap` と内部 `img` を `120px × 70px` に変更（`min-width`/`min-height` も追加）。
- `.list-col-thumb`（テーブルのセル幅）を140pxに拡張し、サムネイルがはみ出さないよう調整。
- `.top10-card` の `min-width` を120pxから128pxに拡張。
- `.top10-thumb-wrap` に `min-width: 120px; min-height: 70px` を追加し、アスペクト比計算に依存せず最低サイズを二重に保証。
- `.thumb-play-btn img`（カード・リスト共通のサムネイル画像）に `min-width: 120px; min-height: 70px` を追加。

**確認方法**: `static/style.css` の該当クラスに `min-width` / `min-height` が明記されており、CSSの計算上どのブレークポイント・表示形式でも120×70pxを下回らないことを確認済み。

---

## 違反③ III.E.4.a-g — 30日超データ保存 + エクスポート機能

### a) 30日超のAPI統計データ保存について

**調査結果**: `supabase_schema.sql` を確認した結果、Supabaseに存在するテーブルは以下の4つのみ：
- `page_views`（アクセスログ：IPアドレス、国、UA等）
- `search_queries`（検索クエリログ：キーワード、フィルター条件等）
- `contacts` / `contact_replies`（お問い合わせ内容）

**YouTube APIから取得した動画データ（再生回数・いいね数・コメント数・チャンネル登録者数など）を保存するテーブルは存在しません。**

`app/main.py` の検索エンドポイントはYouTube Data APIをリアルタイムに呼び出し、レスポンスをそのままクライアントに返すのみで、動画統計データをDBに書き込む処理は一切実装されていません（`app/analytics.py` の `log_search_query` が保存するのは検索キーワードや条件のみで、YouTube APIレスポンス自体は含まれません）。

**結論**: 該当する違反状態は無し。コード修正は不要。この事実を報告する。

### b) 検索結果全体のエクスポート機能の削除

**問題箇所**:
- フロントエンド: CSVエクスポートボタン（`export-csv-btn`）、Excelエクスポートボタン（`export-xlsx-btn`）と、それらを実装する `exportCsv()` / `exportXlsx()` / `buildCsvRows()` / `csvEscape()` 関数（`static/app.js`）。
- 外部ライブラリ: SheetJS (`xlsx.full.min.js`) の読み込み（`static/index.html`）。
- バックエンド: エクスポート専用APIエンドポイントは元々存在していなかったため、削除対象なし。

**修正内容**:
- `static/index.html` からエクスポートボタン2つと、XLSXライブラリの `<script>` タグを削除。
- `static/app.js` から `exportCsv`, `exportXlsx`, `buildCsvRows`, `csvEscape` 関数、およびボタンのイベントリスナーを完全に削除。
- クリップボードコピー等の類似機能は元々実装されていなかったことを確認済み。
- `static/i18n/i18n.js` から関連する翻訳キー（`exportCsv`, `exportXlsx`, `exportHeader.*`, `noExportData`, `csvExported`, `xlsxExported`, `xlsxSheetName`）を4言語（日本語・英語・韓国語・中国語）すべてから削除。

**確認方法**: `static/app.js` / `static/index.html` に `export` という文字列が含まれないことをgrepで確認済み。個別の動画情報（1件ずつのYouTube URLへのリンク等）は元々「一括エクスポート」に該当しないため対象外。

---

## 違反④ III.E.4h — 独自算出指標の削除（最重要）

### a) 推定収益（Estimated Revenue）の削除

**問題箇所**:
- バックエンド: 該当ロジックは無し（元々フロントエンドのみで算出）。
- フロントエンド（`static/app.js`）: CPM設定値管理（`loadCpm`, `saveCpm`, `loadGenreCpm`, `saveGenreCpm`, `GENRE_CPM_DEFAULTS`）、推定収益計算・整形（`formatRevenue`）、各表示箇所での収益算出・表示（検索結果カード、リスト表示、カテゴリ別推定収益グラフ、比較サマリーの平均推定収益、ソート機能）。
- UI（`static/index.html`）: ジャンル別CPM設定モーダル全体（CPM相場参考テーブルを含む）。
- CSS（`static/style.css`）: `.revenue-badge`, `.revenue-note`, `.cpm-form`, `.cpm-input-wrap`, `.genre-cpm-*`, `.cpm-reference` 等の関連スタイル。

**修正内容**: 上記すべてのコード・UI要素・CSSを完全に削除（コメントアウトではなく削除）。カードのレイアウトは推定収益バッジ部分を除去し、再生回数・いいね数・コメント数の表示のみで自然に収まるよう調整。リスト表示・比較サマリーの「推定収益」列も削除し、テーブル幅を再調整。

**ブログ記事の扱い**: `static/blog/youtube-cpm-rpm-calculation-guide.html` および `static/blog/youtube-genre-cpm-guide.html` は、YouTube APIを呼び出さない静的な教育コンテンツであることを確認済み。ユーザー指示に基づき、これらのブログ記事自体（CPM計算の考え方の解説）はそのまま残置。

**マーケティングページの整合性対応**: `static/landing.html` および `static/comparison-section.html` で「推定収益シミュレーション」機能を宣伝していた箇所（機能紹介カード、料金プラン比較表、他社比較表）は、機能削除後に実態と矛盾するため、実在する機能（キーワード比較分析、お気に入り管理等）の紹介に置き換えた。`docs/marketing-copy.md`（未コミット変更あり）には一切触れていない。

### b) エンゲージメント率（Engagement Rate）の削除

**問題箇所**:
- バックエンド（`app/youtube_client.py`, `app/models.py`）: `engagement_rate = view_count / subscriber_count` の算出とAPIレスポンスへの格納。
- フロントエンド（`static/app.js`）: エンゲージメント率フィルター（`engagement-filter` セレクトボックスとその判定ロジック）、エンゲージメント率分布グラフ、カード・リスト表示でのエンゲージメント率表示、比較サマリーの平均エンゲージメント率、ソート機能。
- UI（`static/index.html`）: エンゲージメント率フィルターのセレクトボックス、エンゲージメント率分布グラフのcanvas要素。

**修正内容**: バックエンドのAPIレスポンスから `engagement_rate` フィールドを完全に削除。フロントエンドの表示・フィルター・グラフ・ソート機能を完全に削除。関連する4言語の翻訳キーも削除。

**確認方法**: `app/youtube_client.py`, `app/models.py`, `static/app.js`, `static/index.html` のいずれにも `engagement` という文字列が残っていないことをgrepで確認済み（API検索エンドポイントの実レスポンスにも `engagement_rate` フィールドが存在しないことをcurlで確認済み）。

---

## 保持したデータ（YouTube APIが直接返す値）

以下はYouTube Data APIが直接返す値であり、独自算出指標ではないため、指示どおり表示を維持した：
再生回数（view_count）、いいね数（like_count）、コメント数（comment_count）、チャンネル登録者数（subscriber_count）、動画の長さ、公開日、カテゴリ、タグ等。

---

## 動作確認

- ローカルサーバー起動後、以下を確認:
  - 検索API（`/api/search`）: 正常応答、`engagement_rate` フィールド無し。
  - チャンネル情報API（`/api/channel/{id}`）: 正常応答。
  - `/app`（検索画面）、`/`（ランディングページ）、`static/app.js`, `static/style.css`, `static/i18n/i18n.js`: いずれも200応答。
- 検索・チャンネル表示等の基本機能に影響がないことを確認。動画再生（YouTube embed iframe）ロジックは今回変更していない。

## 変更ファイル一覧

- `app/models.py`, `app/youtube_client.py`（バックエンド: engagement_rate削除）
- `static/index.html`, `static/app.js`, `static/style.css`（フロントエンド: エクスポート・推定収益・エンゲージメント率の削除、サムネイル最小サイズ対応）
- `static/i18n/i18n.js`（4言語の翻訳キー整理）
- `static/landing.html`, `static/comparison-section.html`（マーケティング文言の実態整合性対応）
