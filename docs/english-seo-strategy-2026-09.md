# VidScope 英語市場 SEO / コンテンツ戦略（2026-09-07）

## 1. 現状分析

### 1.1 Search Console サマリー

| 指標 | 値 |
|------|-----|
| 対象 URL | `https://vidscope.app/?lang=en` |
| クリック | 1 |
| 表示回数 | 3 |
| CTR | 33.33% |
| 平均順位 | 2.67 |

サイト全体で唯一クリックを獲得しているのが英語版トップページ（`/?lang=en`）であり、英語市場に対する訴求が他言語より先に反応していると考えられる。

### 1.2 英語 LP のコンテンツ確認

現状の英語版ランディングは、静的 HTML 内の `data-i18n` 属性経由でクライアントサイド i18n（`/static/i18n/i18n.js`）により英語に切り替わる構造になっている。

#### 現行の英語訴求（`static/i18n/i18n.js`）

```784:814:static/i18n/i18n.js
      landing: {
        navFeatures: "Features",
        navHow: "How it Works",
        ...
        heroTitle: "Discover YouTube videos,<br>the <em>smarter</em> way!",
        heroDesc: "VidScope is a next-generation YouTube search & analytics app that instantly finds the best videos using advanced filters for language, region, duration, and more.",
        ...
        feature1Title: "Multilingual & Regional Filters",
        feature2Title: "View Count Ranking",
        feature3Title: "Duration Filter",
        feature4Title: "Keyword Comparison Analysis",
        feature5Title: "Multi API Key Support",
        feature6Title: "Secure by Design",
```

#### 一方で head タグは日本語固定のまま

`static/index.html` も `static/landing.html` も `<title>` / `description` / `og:*` / `twitter:*` が日本語のままである。

```6:8:static/index.html
  <title data-i18n-doctitle="app.docTitle">YouTube動画検索＆分析アプリ | VidScope</title>
  <meta name="description" content="VidScopeアプリでYouTube動画を検索・分析。キーワード検索、言語・地域・再生時間フィルター、再生回数ランキング、チャンネル詳細分析まで無料で利用できます。" />
```

```6:7:static/landing.html
<title>VidScope | 無料のYouTube動画検索＆チャンネル分析ツール</title>
<meta name="description" content="VidScopeは登録不要・APIキー不要ですぐ使えるYouTube動画検索＆チャンネル分析ツール。...">
```

`landing.html` 内のコメントでも同制限が認識されている。

```10:19:static/landing.html
<!--
  hreflang note (SEO limitation, documented per growth-strategy.md audit):
  These URLs use client-side i18n ... They are NOT fully independent SSR pages:
  the raw HTML returned by the server is byte-identical for every hreflang URL,
  and <title>/<meta name="description">/og:*/twitter:* tags below are NOT updated
  per language ... Longer-term fix: real per-language routes/SSR
  (e.g. /en/, /ko/, /zh/) with distinct rendered <head> metadata.
-->
```

これにより、Google が `/?lang=en` をクロールした際、検索結果に表示されるタイトル・スニペットは日本語のまま、または英語ページなのに日本語メタデータで判断されるリスクがある。

### 1.3 英語ページの強みと弱点

#### 強み
- **多言語・地域フィルター**が英語圏の「niche research」「competitor analysis」ニーズにマッチする。
- **比較機能**（複数キーワードの動画数 / 再生回数グラフ比較）は、既存の vidIQ / TubeBuddy とは異なる切り口。
- **アカウント連携不要** / プライバシー重視の訴求は、英語圏でも差別化になりうる。
- 英語 UI は既にほぼ整備済み。

#### 弱点・リスク
- **head メタデータが日本語固定**（最大の SEO 障壁）。
- **OG タグ / Twitter カードも日本語**で `og:locale` は `ja_JP` のまま。
- **コンテンツが薄い**。ランディングページのみで、情報型クエリ（`how to ...` / `best ...`）を捕捉するブログコンテンツがない。
- **ソーシャルプルーフ・ユースケースがない**。英語圏では「他のクリエイターが使っている」証拠が重要。
- **表記の揺れ・古い訴求**が散見される。
  - `comparisonVidscopeChannel` では「Anonymous use with no API key」と謳っているが、FAQ では API キーが必要と説明している。
  - 料金表が日本円（¥）表記のまま。

```901:901:static/i18n/i18n.js
        comparisonVidscopeChannel: "<span class='rating-symbol'>×</span><br>Not required. Anonymous use with no API key",
```

```863:864:static/i18n/i18n.js
        faq1Q: "Do I need to provide my own API key?",
        faq1A: "Yes, you need a YouTube Data API v3 key, which you can get for free from Google Cloud Console.",
```

- 削除済み機能（推定収益・エンゲージメント率・エクスポート）は、LP 比較表 `docs/competitor-comparison.md` や一部文言にまだ残っている可能性があるため、英語展開時は注意が必要。

---

## 2. 英語市場の競合・キーワード調査

### 2.1 上位に入ってくるサービス（簡易調査）

| 調査クエリ | 上位サービスの傾向 |
|------------|-------------------|
| `youtube competitor analysis tool` | **vidIQ**、**TubeBuddy**、**Socialinsider**、**Sprout Social**、**Brand24**、**OverseerOS** など。多くは「チャンネル認証」「ブラウザ拡張」「有料プラン」が前提。 |
| `youtube keyword research tool free` | **vidIQ**、**TubeBuddy**、**Keyword Tool**、**Keyword Tool Dominator**、**Ahrefs**、**Fulhar**、**Keysearch** など。無料枠 + 有料アップセルが標準。 |
| `youtube analytics tool free` | **vidIQ**、**Socialinsider**、**Vaizle**、**Viraly**、**YTface**、**Social Blade** など。自チャンネル連携または30日間トライアル型が多い。 |
| `youtube niche research` | **vidIQ Niche Finder**、**TubeLab**、**OutlierKit**、**Vynex** など。AI を活用した「ニッチの需要 / 競合 / 収益化可能性」の判定を売りにしている。 |

### 2.2 競合の強みと隙

| 競合カテゴリ | 強み | 隙（VidScope が刺せるポイント） |
|--------------|------|----------------------------------|
| vidIQ / TubeBuddy | ブラウザ拡張、SEO スコア、自チャンネル最適化 | 自チャンネル認証必須、拡張インストールが必要、情報過多 |
| Social Blade | チャンネル統計・ランキングの認知度 | **動画検索がない**、UI が古い |
| Keyword Tool 系 | キーワードサジェスト | 動画単位の分析、比較グラフが弱い |
| Niche Finder 系 | AI ニッチ診断 | 多くが有料 / クレジット制。シンプルな検索フィルターで代替できる層あり |
| Sprout Social / Brand24 | エンタープライズ向けSNS分析 | 高額。個人クリエイターには過剰 |

### 2.3 VidScope の差別化ポジショニング案

**「No signup, no channel auth, privacy-first YouTube video research & competitor comparison tool」**

- ブラウザ拡張不要、自チャンネル認証不要。
- 言語・地域・再生時間・期間・カテゴリ・再生回数 などの **高度な検索フィルター**で、競合動画やニッチ動画を発見。
- 複数キーワードを **グラフ比較**。
- 検索クエリをサーバーに保存しない **プライバシー重視**設計。
- 英語 / 日本語 / 韓国語 / 中国語 UI 対応。

ただし、「API キー不要」という表現は現在の仕様と矛盾するため、以下に整理する。

- ユーザー自身の YouTube Data API v3 キーを利用（Google Cloud Console で無料発行）。
- サーバー側で API キーを管理・ローテーションする機能もあり、複数キーで安定運用可能。
- 自チャンネル認証は不要。

---

## 3. 推奨アクション（優先順位順）

### P0. 英語ページの head メタデータを英語にする

検索結果で英語スニペットを出すための最重要タスク。

- `/?lang=en` へアクセスしたとき、サーバー側または edge 関数で以下を英語に変更する。
  - `<title>`: `VidScope | Free YouTube Video Search & Competitor Analysis Tool`
  - `<meta name="description">`: 英語版の価値提案を 150〜160 字にまとめる。
  - `og:title`, `og:description`, `twitter:title`, `twitter:description`
  - `og:locale`: `en_US`
- 構造化データ（`WebSite`, `SoftwareApplication`）の `description` も英語にする。
- 長期的には `/en/` など言語別パスを作り、各ページで独立した `<head>` を返す。

### P1. 英語 LP コピーのブラッシュアップ

- **Hero タイトル・description** を検索キーワードを意識した表現に。
  - 例: "Free YouTube Competitor Analysis Tool — Search, Filter & Compare Videos in Any Language"
- **「API key not required」表記を修正**。FAQ と整合させる。
- **料金表の通貨を USD に変更**（英語圏向け）。
- **「No signup / No channel auth / Privacy-first」**を上位に配置した CTA ブロックを追加。
- **ソーシャルプルーフ/ユースケース**を追加。
  - "For YouTube creators", "For marketers", "For educators" などのセクション。

### P2. 英語ブログ記事を公開して情報型クエリを捕捉

競合調査で上位に入る情報型クエリに対して、ブログ記事でアクセスを取る。

### P3. ディレクトリ登録

- **AlternativeTo**、**SaaSHub**、**Product Hunt**、**G2** などに英語版プロフィールを作成。
- 説明文は Hero コピーと統一し、キーワードを自然に含める。

### P4. 内部リンクと CTA の最適化

- ブログ記事から `/app?lang=en` へ導線を設置。
- ランディングに "Read our guide" などセカンダリー CTA を追加。
- 固定ナビゲーションの CTA を強化。

### P5. 技術的 hreflang/canonical の見直し

- `canonical` を言語別に出し分ける（現状は `https://vidscope.app/` 固定）。
- `hreflang` は維持しつつ、`x-default` を英語 or 日本語のどちらにするか方針決定。
- サイトマップに `/en/` や `/?lang=en` を明示。

---

## 4. 英語ブログ記事企画案

### 記事案 1: Listicle（比較・商談クエリ）

**タイトル案**
- `7 Best Free YouTube Competitor Analysis Tools in 2026 (Compared)`
- `Best Free YouTube Competitor Analysis Tools: A Side-by-Side Comparison`

**ターゲットキーワード**
- best free youtube competitor analysis tools
- youtube competitor analysis tool free
- youtube competitor analysis free

**構成案**
1. What is YouTube competitor analysis?（定義・なぜ重要か）
2. What to look for in a competitor analysis tool（チェックリスト：価格、拡張不要、多言語対応、プライバシーなど）
3. Tool comparison table
   - VidScope
   - vidIQ
   - TubeBuddy
   - Social Blade
   - Socialinsider
   - OverseerOS
   - OutlierKit
4. Pros/cons for each tool
5. Which tool is right for you?（クリエイター / マーケター / 研究者別）
6. CTA: Try VidScope for free → `/app?lang=en`

**VidScope の入れ方**
- 表の中で「無料で始めやすい / 自チャンネル認証不要 / 多言語フィルター」を強調。
- 推定収益・エンゲージメント率・エクスポート機能は削除済みなので言及しない。

### 記事案 2: How-to ガイド（情報型・長尾クエリ）

**タイトル案**
- `How to Do YouTube Competitor Analysis: A Step-by-Step Guide for Creators`
- `YouTube Competitor Analysis for Small Channels: A Beginner's Guide`

**ターゲットキーワード**
- how to do youtube competitor analysis
- youtube competitor analysis guide
- how to analyze youtube competitors

**構成案**
1. Why competitor analysis matters for small channels
2. Step 1: Identify 3–5 competitors in your niche
3. Step 2: Find their top-performing videos（ここで VidScope の「期間フィルター + 再生回数ソート」を紹介）
4. Step 3: Compare keywords / titles / tags / thumbnails
5. Step 4: Spot content gaps using language & region filters
6. Step 5: Track upload timing and trends（曜日・時間帯グラフの活用）
7. Free template / checklist download（メール登録を促す場合）
8. CTA: Start your research with VidScope

### 記事案 3: 追加候補（将来的）

- `How to Find Low-Competition YouTube Niches with Free Tools`
- `YouTube Keyword Research for Small Channels: A Practical Guide`

---

## 5. 英語 LP 改善案（詳細）

### 5.1 タイトル / メタ description 案

**案 A（検索キーワード重視）**
- Title: `VidScope | Free YouTube Competitor Analysis & Video Search Tool`
- Description: `Research YouTube competitors without signup or channel auth. Filter by language, region, duration, and views. Compare keywords with charts. Free to use.`

**案 B（差別化重視）**
- Title: `VidScope — Privacy-First YouTube Research Tool for Creators`
- Description: `Discover trending videos and analyze competitors across languages and regions. No browser extension, no channel login. Start for free.`

### 5.2 Hero セクション案

```
[h1] Free YouTube Competitor Analysis Tool
[sub] Search, filter, and compare YouTube videos across languages and regions — without signing up or connecting your channel.
[CTA] Start Searching Free  |  See How It Works
```

### 5.3 追加セクション案

| セクション | 目的 |
|------------|------|
| **Use cases** | クリエイター / マーケター / 教育者 / 研究者 |
| **Why VidScope?** | 拡張不要・認証不要・多言語対応・プライバシー重視 |
| **Trusted by creators** | 実績や声があれば（現状なければ保留） |
| **Comparison table** | 既存の表を更新し、削除済み機能を除外 |

### 5.4 修正が必要な古い表記

| 箇所 | 現状 | 修正案 |
|------|------|--------|
| `comparisonVidscopeChannel` | "Anonymous use with no API key" | "No channel login required" |
| `step1Title` | "Create an Account" | アカウント登録が不要なら削除 or 修正 |
| 料金表 | ¥980 / 月 | $6.99 / 月 など英語圏価格に |
| Hero description | "next-generation" など抽象的表現 | 具体的なユースケースを先に |

---

## 6. AlternativeTo / SaaSHub 用の英語説明文案

```
VidScope is a free, privacy-first YouTube research tool for creators and marketers.
Search and filter videos by language, region, duration, category, and view count;
compare multiple keywords with charts; and analyze competitor channels —
all without signing up or connecting your YouTube account.
```

```
VidScope helps you find winning YouTube videos and understand your niche faster.
Use advanced filters to research competitors across countries and languages,
spot trending content, and compare keyword performance side by side.
```

---

## 7. 測定指標（KPI）

| 指標 | 現状 | 目標（3ヶ月後） |
|------|------|----------------|
| 英語版トップのクリック数 | 1 | 50 / 月 |
| 英語版表示回数 | 3 | 1,000 / 月 |
| 英語ブログ記事の流入 | 0 | 1 記事あたり 100 セッション |
| 英語ページの平均順位 | 2.67 | トップ 10 入りを維持・拡大 |
| ディレクトリからのリファラー | 0 | AlternativeTo / SaaSHub から計測開始 |

---

## 8. 次のステップ

1. 本戦略を確認・承認。
2. P0 / P1 の英語 head メタデータと LP コピー修正を実装（別タスク）。
3. 記事案 1 または 2 のドラフト作成・公開（別タスク）。
4. AlternativeTo / SaaSHub 登録用テキストでプロフィール作成。
5. 4 週間後に Search Console / アナリティクスで効果測定。

---

*調査日: 2026-09-07*
