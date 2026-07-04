/* VidScope i18n engine (vanilla JS, no build step)
 * Usage:
 *   window.VidScopeI18n.t(key, params)
 *   window.VidScopeI18n.applyTranslations(root)
 *   window.VidScopeI18n.setLanguage(lang)
 *   window.VidScopeI18n.getLang() / getLocale()
 * Elements:
 *   data-i18n="key"              -> textContent
 *   data-i18n-html="key"         -> innerHTML (rich text)
 *   data-i18n-placeholder="key"  -> placeholder attribute
 *   data-i18n-title="key"        -> title attribute
 *   data-i18n-aria-label="key"   -> aria-label attribute
 *   .content-en / .content-ja    -> legal dual-block toggle (privacy/terms)
 */
(function () {
  "use strict";

  var DICT = {
    ja: {
      common: {
        themeToggleToDark: "ダークモードに切替",
        themeToggleToLight: "ライトモードに切替",
        settingsTitle: "設定",
        langLabel: "言語",
        footer: {
          privacy: "プライバシーポリシー",
          terms: "利用規約",
          contact: "お問い合わせ",
          app: "アプリを使う",
          home: "VidScope",
          copyright: "© 2026 VidScope. All rights reserved.",
        },
      },
      app: {
        docTitle: "VidScope — YouTube動画の発見をもっとスマートに！",
        search: {
          placeholder: "キーワード",
          countSuffix: "件",
          submitBtn: "検索",
          compareBtn: "比較モード",
          compareTitle: "複数キーワードを比較",
        },
        compare: {
          keyword1Title: "キーワード1",
          keyword2Placeholder: "キーワード2",
          keyword2Title: "キーワード2",
          keyword3Placeholder: "キーワード3（任意）",
          keyword3Title: "キーワード3（任意）",
        },
        filters: {
          durationLabel: "動画長さ",
          durationAll: "すべて",
          durationShort: "ショート（3分以下）",
          durationNormal: "通常（3分超）",
          publishedLabel: "期間",
          publishedAll: "全期間",
          published24h: "24時間",
          published1w: "1週間",
          published2w: "2週間",
          published1m: "1ヶ月",
          published2m: "2ヶ月",
          published3m: "3ヶ月",
          published6m: "6ヶ月",
          published1y: "1年間",
          categoryLabel: "ジャンル",
          categoryAll: "すべて",
          engagementLabel: "エンゲージメント率",
          engagementAll: "すべて",
          engagementLevel1: "10〜30%未満",
          engagementLevel2: "30〜70%未満",
          engagementLevel3: "70〜150%未満",
          engagementLevel4: "150〜300%未満",
          engagementLevel5: "300%以上",
          viewCountLabel: "再生回数（万回以上）",
          viewCountPlaceholder: "例: 10",
          languageLabel: "言語",
          languageAll: "すべて",
          regionLabel: "国",
          regionAll: "すべて",
        },
        lang: {
          ja: "日本語", en: "英語", ko: "韓国語", zh: "中国語",
          es: "スペイン語", pt: "ポルトガル語", hi: "ヒンディー語",
          fr: "フランス語", de: "ドイツ語", ar: "アラビア語",
        },
        region: {
          JP: "日本", US: "アメリカ", KR: "韓国", CN: "中国",
          IN: "インド", GB: "イギリス", BR: "ブラジル", FR: "フランス",
          DE: "ドイツ", TW: "台湾",
        },
        category: {
          "1": "映画・アニメ", "2": "自動車・乗り物", "10": "音楽",
          "15": "ペット・動物", "17": "スポーツ", "19": "旅行・イベント",
          "20": "ゲーム", "22": "人物・ブログ", "23": "コメディ",
          "24": "エンタメ", "25": "ニュース・政治", "26": "ハウツー・スタイル",
          "27": "教育", "28": "科学・テクノロジー", "29": "非営利・社会活動",
          other: "その他・未分類", unknown: "不明",
        },
        popularKeywordsTitle: "人気キーワード",
        popularKeywordCountUnit: "{{count}}回",
        xlsxSheetName: "検索結果",
        graphHideAll: "全グラフ非表示",
        graphShowAll: "全グラフ表示",
        graphHide: "非表示",
        graphShow: "表示",
        exportHeader: {
          title: "タイトル", channel: "チャンネル名", views: "再生回数",
          likes: "いいね数", comments: "コメント数", subscribers: "登録者数",
          engagement: "エンゲージメント率", duration: "動画の長さ(秒)",
          published: "公開日", genre: "ジャンル", tags: "タグ", url: "動画URL",
        },
        historyTitle: "検索履歴",
        historyClearBtn: "履歴をクリア",
        favoritesTitle: "お気に入り",
        favoritesClearBtn: "すべて削除",
        favoritesAddTooltip: "お気に入りに追加",
        favoritesRemoveTooltip: "お気に入りを解除",
        favoritesRemoveBtn: "削除",
        top10Title: "TOP 10",
        top10ScrollBtn: "検索結果全て ▼",
        trend: {
          title: "トレンド分析",
          toggleAllHide: "全グラフ非表示",
          toggleAllShow: "全グラフ表示",
          resetBtn: "表示リセット",
          colorLabel: "グラフカラー",
          colorResetBtn: "リセット",
        },
        graph: {
          hide: "非表示",
          show: "表示",
          countryChart: "国別動画数",
          countryViewChart: "国別再生回数（合計）",
          viewChart: "再生回数分布",
          engagementChart: "エンゲージメント率分布",
          categoryChart: "カテゴリ別動画数",
          categoryViewChart: "カテゴリ別再生回数（合計）",
          categoryRevenueChart: "カテゴリ別推定収益（合計）",
          tagChart: "タグ TOP10",
          titleWordChart: "タイトルキーワード TOP10",
          weekdayChart: "曜日別投稿動画数",
          hourChart: "時間帯別投稿動画数",
          correlationChart: "動画時間 - 再生回数相関",
        },
        exportCsv: "CSVエクスポート",
        exportXlsx: "Excelエクスポート",
        resultsTitle: "検索結果",
        cardViewTitle: "カード表示",
        listViewTitle: "リスト表示",
        modal: {
          settingsTitle: "⚙️ 設定",
          apiKeyTitle: "APIキー管理",
          apiKeyDesc: "YouTube Data API v3のAPIキーを管理できます。複数登録するとクォータ超過時に自動ローテーションします。",
          adminPwPlaceholder: "管理者パスワード",
          newKeyPlaceholder: "新しいAPIキー（AIzaSy...）",
          addBtn: "追加",
          manualSummary: "APIキーの取得方法",
          manualStep1: "Google Cloud Console にアクセス",
          manualStep1Suffix: "にアクセス",
          manualStep2: "新しいプロジェクトを作成（またはプロジェクトを選択）",
          manualStep3: "左メニュー →「APIとサービス」→「ライブラリ」",
          manualStep4: "「YouTube Data API v3」を検索して「有効にする」",
          manualStep5: "「APIとサービス」→「認証情報」→「認証情報を作成」→「APIキー」",
          manualStep6: "作成されたAPIキーをコピーして上の入力欄に貼り付け",
          manualNote: "※ 複数のプロジェクトでキーを作成すると、クォータ超過時に自動でローテーションされます。",
          genreCpmTitle: "ジャンル別CPM設定",
          genreCpmDesc: "ジャンルごとにCPMを個別設定します。設定したCPMが各動画の推定収益計算に使用されます。",
          shortVideoLabel: "ショート動画",
          genreResetBtn: "全てデフォルトに戻す",
          genreSaveBtn: "保存",
          cpmRefTitle: "📊 CPM相場（参考）",
          cpmRefFinance: "金融・投資系",
          cpmRefRealEstate: "不動産・BtoB",
          cpmRefEducation: "教育・ハウツー",
          cpmRefIt: "IT・ガジェット",
          cpmRefHealth: "健康・美容",
          cpmRefGame: "ゲーム",
          cpmRefEntertainment: "エンタメ・雑談",
          cpmRefMusic: "音楽",
          cpmRefKids: "子供向け",
          cpmRangeFinance: "1,000〜2,000円+",
          cpmRangeRealEstate: "1,000〜2,000円+",
          cpmRangeEducation: "200〜800円",
          cpmRangeIt: "200〜600円",
          cpmRangeHealth: "150〜500円",
          cpmRangeGame: "50〜200円",
          cpmRangeEntertainment: "50〜150円",
          cpmRangeMusic: "30〜100円",
          cpmRangeKids: "20〜80円",
          cpmUnit: "円",
          cpmRefNote1: "※ 国・地域・季節・広告枠・視聴者属性により大きく変動します",
          cpmRefNote2: "出典: Shopify Japan、StockSun株式会社、VLINK MAG等のウェブ記事を総合した目安値",
          videoOpenBtn: "YouTubeで開く",
          channelTitle: "チャンネル詳細",
          channelSubscribers: "登録者数",
          channelTotalViews: "総再生回数",
          channelVideoCount: "動画数",
          channelFoundedYear: "開設年",
          channelLatestVideos: "最新動画",
          channelOpenPageBtn: "YouTubeでチャンネルを開く",
          channelLoading: "読み込み中...",
          channelVideosUnavailable: "動画情報を取得できませんでした。",
          channelFetchFailed: "チャンネル情報の取得に失敗しました",
          channelUnknownYear: "不明",
          channelYearSuffix: "年",
          channelViewCountLabel: "再生回数: {{value}}",
        },
        status: {
          searching: "検索中...",
          noExportData: "エクスポート対象がありません。先に検索してください。",
          csvExported: "{{count}}件をCSVエクスポートしました",
          xlsxExported: "{{count}}件をExcelエクスポートしました",
          searchFailed: "検索に失敗しました",
          compareNeedTwo: "比較モードは2つ以上のキーワードが必要です",
          comparing: "比較検索中...",
          compareComplete: "比較完了: {{keywords}}（各キーワードの件数: {{counts}}）",
          compareCountUnit: "{{count}}件",
          resultsShown: "{{shown}}件表示中（取得: {{total}}件）{{filterText}}",
          quotaExceeded: "APIクォータの上限に達しました",
          noResults: "結果がありませんでした。",
          keysLoadFailed: "キーの取得に失敗しました",
          keyAddFailed: "追加に失敗しました",
          cpmRangeError: "1〜1000の範囲で入力してください",
          cpmSaved: "CPMを {{value}}円 に保存しました",
          genreCpmError: "全て1以上の値を入力してください",
          genreCpmSaved: "ジャンル別CPMを保存しました",
          genreCpmReset: "全てデフォルト値に戻しました",
          keyDeleteBtn: "削除",
        },
        chartFilter: {
          tag: "タグ: {{value}}",
          viewRange: "再生回数: {{value}}",
          engRange: "エンゲージメント率: {{value}}",
          country: "国: {{value}}",
          weekday: "曜日: {{value}}",
          hour: "時間帯: {{value}}時",
          titleWord: "タイトル: {{value}}",
        },
        historyTag: {
          period: "期間:{{value}}",
          duration: "時間:{{value}}",
          category: "カテゴリ:{{value}}",
          language: "言語:{{value}}",
          region: "地域:{{value}}",
        },
        card: {
          publishedLabel: "公開日",
          genreLabel: "ジャンル",
          viewsLabel: "再生回数",
          likesLabel: "いいね",
          commentsLabel: "コメント",
          subscribersLabel: "登録者数",
          engagementLabel: "エンゲージメント率",
          durationLabel: "長さ",
          revenueLabel: "推定収益",
          revenueTooltip: "推定収益（参考値）: 再生回数 × CPM({{cpm}}円) ÷ 1000",
          revenueNote: "※参考値",
          tagsLabel: "タグ",
          noTags: "タグなし",
          previewAria: "動画をプレビュー",
        },
        list: {
          thumbnail: "サムネイル",
          title: "タイトル",
          channel: "チャンネル",
          genre: "ジャンル",
          subscribers: "登録者数",
          views: "再生回数",
          engRate: "ENG率",
          duration: "長さ",
          published: "公開日",
          revenue: "推定収益",
          durationValue: "{{m}}分{{s}}秒",
        },
        compareSummary: {
          title: "比較サマリー",
          keyword: "キーワード",
          avgViews: "平均再生数",
          avgEngagement: "平均エンゲージメント率",
          count: "動画数",
          avgRevenue: "推定平均収益",
          countUnit: "{{count}}件",
        },
        quotaAlert: {
          heading: "⚠️ APIクォータの上限に達しました",
          message: "YouTube Data APIの1日あたりの使用上限を超えました。<br>新しいAPIキーを追加すると検索を続行できます。",
          addKeyBtn: "APIキーを追加する",
          dismissBtn: "閉じる",
        },
        chart: {
          axisCount: "件数",
          axisCategory: "カテゴリ",
          axisTag: "タグ",
          axisViewRange: "再生回数レンジ",
          axisEngRange: "エンゲージメント率レンジ",
          axisCountryLang: "国・言語",
          axisHour: "時間帯",
          axisWeekday: "曜日",
          axisWord: "ワード",
          axisViewSumMan: "再生回数合計（万回）",
          axisRevenueSum: "推定収益合計（千円）",
          axisDurationMin: "動画の長さ（分）",
          axisViews: "再生回数",
          tooltipTitle: "タイトル: {{value}}",
          tooltipLength: "長さ: {{value}}分",
          tooltipViews: "再生回数: {{value}}",
        },
        weekday: { "0": "日", "1": "月", "2": "火", "3": "水", "4": "木", "5": "金", "6": "土" },
        hourLabel: "{{h}}時",
        country: {
          ja: "日本", en: "英語圏", ko: "韓国", zh: "中国",
          es: "スペイン語圏", pt: "ポルトガル語圏", hi: "インド",
          fr: "フランス語圏", de: "ドイツ語圏", ar: "アラビア語圏",
          ru: "ロシア", id: "インドネシア", th: "タイ", vi: "ベトナム",
        },
        units: { oku: "億", man: "万", sen: "千" },
        videoIframeTitle: "YouTube動画",
        footerPrivacy: "プライバシーポリシー",
        footerTerms: "利用規約",
      },
      landing: {
        navFeatures: "機能",
        navHow: "使い方",
        navPricing: "料金",
        navFaq: "FAQ",
        navCta: "アプリを開く →",
        heroBadge: "YouTube Data API v3 搭載",
        heroTitle: "YouTube動画の発見を<br>もっと<em>スマート</em>に！",
        heroDesc: "VidScopeは、言語・地域・再生時間などの高度なフィルターで最適な動画を瞬時に見つける、次世代のYouTube検索・分析アプリです。",
        heroBtnPrimary: "🎬 無料で始める",
        heroBtnSecondary: "機能を見る",
        slide1: "🔍 キーワード検索 → 結果表示",
        slide2: "📊 トレンド分析グラフ",
        slide3: "🎬 検索結果一覧",
        slide4: "▶️ 動画プレビュー",
        featuresLabel: "Features",
        featuresTitle: "検索を、もっと自由に。",
        featuresDesc: "VidScopeは、YouTubeの標準検索では届かない高精度なフィルタリングを実現します。",
        feature1Title: "多言語・地域フィルター",
        feature1Desc: "日本語、英語、韓国語、中国語など言語別に動画を絞り込み。地域指定でローカルトレンドも発見。",
        feature2Title: "再生回数ランキング",
        feature2Desc: "再生回数順の正確なソートで、人気動画を一目で把握。エンゲージメント率も自動計算。",
        feature3Title: "再生時間フィルター",
        feature3Desc: "ショート動画、通常動画、長尺動画を簡単に切り替え。目的に合った動画だけを表示。",
        feature4Title: "推定収益シミュレーション",
        feature4Desc: "CPMベースで動画の推定収益を自動算出。ジャンル別CPMのカスタム設定にも対応。",
        feature5Title: "マルチAPIキー",
        feature5Desc: "複数のAPIキーを登録可能。クォータ超過時に自動ローテーションで、検索が止まらない。",
        feature6Title: "セキュア設計",
        feature6Desc: "管理者認証、レート制限、セキュリティヘッダーを標準装備。安心して運用できます。",
        howLabel: "How it works",
        howTitle: "3ステップで始める",
        howDesc: "難しい設定は不要。すぐに使い始められます。",
        step1Title: "アカウント登録",
        step1Desc: "メールアドレスで無料アカウントを作成。30秒で完了します。",
        step2Title: "APIキーを設定",
        step2Desc: "Google Cloud ConsoleでAPIキーを取得し、設定画面から登録。",
        step3Title: "検索開始",
        step3Desc: "キーワードとフィルターを設定して、最適な動画を発見しましょう。",
        pricingLabel: "Pricing",
        pricingTitle: "あなたに合ったプランを。",
        pricingDesc: "個人利用から本格運用まで、柔軟にスケール。",
        freeTitle: "Free",
        freePriceSuffix: "/月",
        freeDesc: "個人利用に最適",
        freeF1: "1日100回の検索",
        freeF2: "基本フィルター（言語・期間）",
        freeF3: "APIキー 1個",
        freeF4: "再生回数ランキング",
        freeF5: "推定収益分析",
        freeF6: "チャンネル分析",
        freeF7: "優先サポート",
        freeBtn: "無料で始める",
        proBadge: "人気 No.1",
        proTitle: "Pro",
        proPriceSuffix: "/月",
        proDesc: "クリエイター・マーケター向け",
        proF1: "無制限検索",
        proF2: "全フィルター利用可能",
        proF3: "APIキー 無制限",
        proF4: "再生回数ランキング",
        proF5: "推定収益分析",
        proF6: "チャンネル分析",
        proF7: "優先サポート",
        proBtn: "Proを始める",
        entTitle: "Enterprise",
        entPrice: "要相談",
        entDesc: "チーム・企業向け",
        entF1: "全Pro機能",
        entF2: "チームメンバー管理",
        entF3: "APIキー 無制限",
        entF4: "カスタムダッシュボード",
        entF5: "データエクスポート（CSV）",
        entF6: "SLA保証",
        entF7: "優先サポート",
        entBtn: "お問い合わせ",
        faqLabel: "FAQ",
        faqTitle: "よくある質問",
        faq1Q: "APIキーは自分で用意する必要がありますか？",
        faq1A: "はい、YouTube Data API v3のAPIキーが必要です。Google Cloud Consoleから無料で取得できます。設定画面に取得手順のガイドも用意しています。",
        faq2Q: "APIのクォータ制限はどうなりますか？",
        faq2A: "YouTube Data APIのデフォルトクォータは1日10,000ユニットです。VidScopeは複数APIキーの自動ローテーションに対応しているため、クォータを効率的に活用できます。",
        faq3Q: "無料プランに期限はありますか？",
        faq3A: "いいえ、無料プランに期限はありません。検索回数の制限はありますが、基本機能をずっとお使いいただけます。",
        faq4Q: "データは安全ですか？",
        faq4A: "VidScopeはユーザーデータを一切収集・保存しません。検索クエリはYouTube APIに直接送信され、サーバーにログとして残ることもありません。",
        faq5Q: "プランの変更やキャンセルはできますか？",
        faq5A: "はい、いつでもプランの変更・キャンセルが可能です。日割り計算で返金対応いたします。",
        ctaTitle: "さあ、始めましょう。",
        ctaDesc: "VidScopeで、YouTube動画の検索体験を変える。",
        ctaBtn: "🎬 無料で始める",
      },
      contact: {
        docTitle: "お問い合わせ | VidScope",
        heading: "お問い合わせ",
        subtitle: "ご質問、ご要望、データ削除リクエストなど、お気軽にお問い合わせください。",
        nameLabel: "お名前",
        namePlaceholder: "山田 太郎",
        emailLabel: "メールアドレス",
        emailPlaceholder: "example@email.com",
        categoryLabel: "カテゴリ",
        categoryPlaceholder: "選択してください",
        categoryGeneral: "一般的なお問い合わせ",
        categoryBug: "不具合の報告",
        categoryFeature: "機能のリクエスト",
        categoryDataDeletion: "データ削除リクエスト",
        categoryPrivacy: "プライバシーに関する質問",
        categoryOther: "その他",
        messageLabel: "お問い合わせ内容",
        messagePlaceholder: "お問い合わせ内容をご記入ください...",
        submitBtn: "送信する",
        submittingBtn: "送信中...",
        successHeading: "✓ 送信完了",
        successMessage: "お問い合わせありがとうございます。<br>内容を確認の上、ご連絡いたします。",
        backToTop: "トップページに戻る",
        submitFailed: "送信に失敗しました。時間をおいて再度お試しください。",
      },
      privacy: {
        docTitle: "プライバシーポリシー | VidScope",
      },
      terms: {
        docTitle: "利用規約 | VidScope",
      },
    },
    en: {
      common: {
        themeToggleToDark: "Switch to dark mode",
        themeToggleToLight: "Switch to light mode",
        settingsTitle: "Settings",
        langLabel: "Language",
        footer: {
          privacy: "Privacy Policy",
          terms: "Terms of Service",
          contact: "Contact",
          app: "Use App",
          home: "VidScope",
          copyright: "© 2026 VidScope. All rights reserved.",
        },
      },
      app: {
        docTitle: "VidScope — Discover YouTube videos, smarter!",
        search: {
          placeholder: "Keyword",
          countSuffix: "results",
          submitBtn: "Search",
          compareBtn: "Compare Mode",
          compareTitle: "Compare multiple keywords",
        },
        compare: {
          keyword1Title: "Keyword 1",
          keyword2Placeholder: "Keyword 2",
          keyword2Title: "Keyword 2",
          keyword3Placeholder: "Keyword 3 (optional)",
          keyword3Title: "Keyword 3 (optional)",
        },
        filters: {
          durationLabel: "Duration",
          durationAll: "All",
          durationShort: "Short (≤3 min)",
          durationNormal: "Standard (>3 min)",
          publishedLabel: "Period",
          publishedAll: "All time",
          published24h: "24 hours",
          published1w: "1 week",
          published2w: "2 weeks",
          published1m: "1 month",
          published2m: "2 months",
          published3m: "3 months",
          published6m: "6 months",
          published1y: "1 year",
          categoryLabel: "Category",
          categoryAll: "All",
          engagementLabel: "Engagement Rate",
          engagementAll: "All",
          engagementLevel1: "10–30%",
          engagementLevel2: "30–70%",
          engagementLevel3: "70–150%",
          engagementLevel4: "150–300%",
          engagementLevel5: "300%+",
          viewCountLabel: "Views (10K+)",
          viewCountPlaceholder: "e.g. 10",
          languageLabel: "Language",
          languageAll: "All",
          regionLabel: "Region",
          regionAll: "All",
        },
        lang: {
          ja: "Japanese", en: "English", ko: "Korean", zh: "Chinese",
          es: "Spanish", pt: "Portuguese", hi: "Hindi",
          fr: "French", de: "German", ar: "Arabic",
        },
        region: {
          JP: "Japan", US: "United States", KR: "South Korea", CN: "China",
          IN: "India", GB: "United Kingdom", BR: "Brazil", FR: "France",
          DE: "Germany", TW: "Taiwan",
        },
        category: {
          "1": "Film & Animation", "2": "Autos & Vehicles", "10": "Music",
          "15": "Pets & Animals", "17": "Sports", "19": "Travel & Events",
          "20": "Gaming", "22": "People & Blogs", "23": "Comedy",
          "24": "Entertainment", "25": "News & Politics", "26": "Howto & Style",
          "27": "Education", "28": "Science & Technology", "29": "Nonprofits & Activism",
          other: "Other / Uncategorized", unknown: "Unknown",
        },
        popularKeywordsTitle: "Popular Keywords",
        popularKeywordCountUnit: "{{count}}",
        xlsxSheetName: "Search Results",
        graphHideAll: "Hide All Graphs",
        graphShowAll: "Show All Graphs",
        graphHide: "Hide",
        graphShow: "Show",
        exportHeader: {
          title: "Title", channel: "Channel", views: "Views",
          likes: "Likes", comments: "Comments", subscribers: "Subscribers",
          engagement: "Engagement Rate", duration: "Duration (sec)",
          published: "Published Date", genre: "Genre", tags: "Tags", url: "Video URL",
        },
        historyTitle: "Search History",
        historyClearBtn: "Clear History",
        favoritesTitle: "Favorites",
        favoritesClearBtn: "Remove All",
        favoritesAddTooltip: "Add to Favorites",
        favoritesRemoveTooltip: "Remove from Favorites",
        favoritesRemoveBtn: "Remove",
        top10Title: "TOP 10",
        top10ScrollBtn: "All Results ▼",
        trend: {
          title: "Trend Analysis",
          toggleAllHide: "Hide All Graphs",
          toggleAllShow: "Show All Graphs",
          resetBtn: "Reset View",
          colorLabel: "Graph Color",
          colorResetBtn: "Reset",
        },
        graph: {
          hide: "Hide",
          show: "Show",
          countryChart: "Videos by Country",
          countryViewChart: "Views by Country (Total)",
          viewChart: "View Count Distribution",
          engagementChart: "Engagement Rate Distribution",
          categoryChart: "Videos by Category",
          categoryViewChart: "Views by Category (Total)",
          categoryRevenueChart: "Est. Revenue by Category (Total)",
          tagChart: "Top 10 Tags",
          titleWordChart: "Top 10 Title Keywords",
          weekdayChart: "Videos by Weekday",
          hourChart: "Videos by Hour",
          correlationChart: "Duration vs. Views Correlation",
        },
        exportCsv: "Export CSV",
        exportXlsx: "Export Excel",
        resultsTitle: "Search Results",
        cardViewTitle: "Card View",
        listViewTitle: "List View",
        modal: {
          settingsTitle: "⚙️ Settings",
          apiKeyTitle: "API Key Management",
          apiKeyDesc: "Manage your YouTube Data API v3 keys. Registering multiple keys enables automatic rotation when quota is exceeded.",
          adminPwPlaceholder: "Admin password",
          newKeyPlaceholder: "New API key (AIzaSy...)",
          addBtn: "Add",
          manualSummary: "How to get an API key",
          manualStep1: "Go to Google Cloud Console",
          manualStep1Suffix: "",
          manualStep2: "Create a new project (or select an existing one)",
          manualStep3: "Left menu → \"APIs & Services\" → \"Library\"",
          manualStep4: "Search for \"YouTube Data API v3\" and enable it",
          manualStep5: "\"APIs & Services\" → \"Credentials\" → \"Create Credentials\" → \"API Key\"",
          manualStep6: "Copy the created API key and paste it into the field above",
          manualNote: "* Creating keys across multiple projects allows automatic rotation when quota is exceeded.",
          genreCpmTitle: "CPM Settings by Genre",
          genreCpmDesc: "Set CPM individually per genre. The configured CPM is used to calculate each video's estimated revenue.",
          shortVideoLabel: "Short Videos",
          genreResetBtn: "Reset All to Default",
          genreSaveBtn: "Save",
          cpmRefTitle: "📊 CPM Reference Rates",
          cpmRefFinance: "Finance & Investing",
          cpmRefRealEstate: "Real Estate & B2B",
          cpmRefEducation: "Education & How-to",
          cpmRefIt: "IT & Gadgets",
          cpmRefHealth: "Health & Beauty",
          cpmRefGame: "Gaming",
          cpmRefEntertainment: "Entertainment & Chat",
          cpmRefMusic: "Music",
          cpmRefKids: "Kids",
          cpmRangeFinance: "¥1,000–2,000+",
          cpmRangeRealEstate: "¥1,000–2,000+",
          cpmRangeEducation: "¥200–800",
          cpmRangeIt: "¥200–600",
          cpmRangeHealth: "¥150–500",
          cpmRangeGame: "¥50–200",
          cpmRangeEntertainment: "¥50–150",
          cpmRangeMusic: "¥30–100",
          cpmRangeKids: "¥20–80",
          cpmUnit: "JPY",
          cpmRefNote1: "* Varies greatly by country, region, season, ad placement, and audience.",
          cpmRefNote2: "Source: Estimated benchmark compiled from web articles by Shopify Japan, StockSun Inc., VLINK MAG, etc.",
          videoOpenBtn: "Open in YouTube",
          channelTitle: "Channel Details",
          channelSubscribers: "Subscribers",
          channelTotalViews: "Total Views",
          channelVideoCount: "Videos",
          channelFoundedYear: "Founded",
          channelLatestVideos: "Latest Videos",
          channelOpenPageBtn: "Open Channel on YouTube",
          channelLoading: "Loading...",
          channelVideosUnavailable: "Could not retrieve video information.",
          channelFetchFailed: "Failed to retrieve channel information",
          channelUnknownYear: "Unknown",
          channelYearSuffix: "",
          channelViewCountLabel: "Views: {{value}}",
        },
        status: {
          searching: "Searching...",
          noExportData: "No data to export. Please search first.",
          csvExported: "Exported {{count}} items to CSV",
          xlsxExported: "Exported {{count}} items to Excel",
          searchFailed: "Search failed",
          compareNeedTwo: "Compare mode requires at least 2 keywords",
          comparing: "Comparing...",
          compareComplete: "Comparison complete: {{keywords}} (item counts: {{counts}})",
          compareCountUnit: "{{count}}",
          resultsShown: "Showing {{shown}} (fetched: {{total}}){{filterText}}",
          quotaExceeded: "API quota limit reached",
          noResults: "No results found.",
          keysLoadFailed: "Failed to load keys",
          keyAddFailed: "Failed to add",
          cpmRangeError: "Please enter a value between 1 and 1000",
          cpmSaved: "CPM saved: ¥{{value}}",
          genreCpmError: "All values must be 1 or greater",
          genreCpmSaved: "Genre CPM saved",
          genreCpmReset: "Reset to default values",
          keyDeleteBtn: "Delete",
        },
        chartFilter: {
          tag: "Tag: {{value}}",
          viewRange: "Views: {{value}}",
          engRange: "Engagement: {{value}}",
          country: "Country: {{value}}",
          weekday: "Weekday: {{value}}",
          hour: "Hour: {{value}}:00",
          titleWord: "Title: {{value}}",
        },
        historyTag: {
          period: "Period:{{value}}",
          duration: "Duration:{{value}}",
          category: "Category:{{value}}",
          language: "Language:{{value}}",
          region: "Region:{{value}}",
        },
        card: {
          publishedLabel: "Published",
          genreLabel: "Genre",
          viewsLabel: "Views",
          likesLabel: "Likes",
          commentsLabel: "Comments",
          subscribersLabel: "Subscribers",
          engagementLabel: "Engagement",
          durationLabel: "Length",
          revenueLabel: "Est. Revenue",
          revenueTooltip: "Estimated Revenue (reference): Views × CPM(¥{{cpm}}) ÷ 1000",
          revenueNote: "*Reference only",
          tagsLabel: "Tags",
          noTags: "No tags",
          previewAria: "Preview video",
        },
        list: {
          thumbnail: "Thumbnail",
          title: "Title",
          channel: "Channel",
          genre: "Genre",
          subscribers: "Subscribers",
          views: "Views",
          engRate: "Eng. Rate",
          duration: "Length",
          published: "Published",
          revenue: "Est. Revenue",
          durationValue: "{{m}}m {{s}}s",
        },
        compareSummary: {
          title: "Comparison Summary",
          keyword: "Keyword",
          avgViews: "Avg. Views",
          avgEngagement: "Avg. Engagement Rate",
          count: "Videos",
          avgRevenue: "Avg. Est. Revenue",
          countUnit: "{{count}}",
        },
        quotaAlert: {
          heading: "⚠️ API Quota Limit Reached",
          message: "You have exceeded the daily usage limit of the YouTube Data API.<br>Add a new API key to continue searching.",
          addKeyBtn: "Add API Key",
          dismissBtn: "Close",
        },
        chart: {
          axisCount: "Count",
          axisCategory: "Category",
          axisTag: "Tag",
          axisViewRange: "View Count Range",
          axisEngRange: "Engagement Rate Range",
          axisCountryLang: "Country / Language",
          axisHour: "Hour",
          axisWeekday: "Weekday",
          axisWord: "Word",
          axisViewSumMan: "Total Views (10K)",
          axisRevenueSum: "Total Est. Revenue (¥1K)",
          axisDurationMin: "Duration (min)",
          axisViews: "Views",
          tooltipTitle: "Title: {{value}}",
          tooltipLength: "Length: {{value}} min",
          tooltipViews: "Views: {{value}}",
        },
        weekday: { "0": "Sun", "1": "Mon", "2": "Tue", "3": "Wed", "4": "Thu", "5": "Fri", "6": "Sat" },
        hourLabel: "{{h}}:00",
        country: {
          ja: "Japan", en: "English-speaking", ko: "Korea", zh: "China",
          es: "Spanish-speaking", pt: "Portuguese-speaking", hi: "India",
          fr: "French-speaking", de: "German-speaking", ar: "Arabic-speaking",
          ru: "Russia", id: "Indonesia", th: "Thailand", vi: "Vietnam",
        },
        units: { oku: "00M", man: "10K", sen: "K" },
        videoIframeTitle: "YouTube video",
        footerPrivacy: "Privacy Policy",
        footerTerms: "Terms of Service",
      },
      landing: {
        navFeatures: "Features",
        navHow: "How it Works",
        navPricing: "Pricing",
        navFaq: "FAQ",
        navCta: "Open App →",
        heroBadge: "Powered by YouTube Data API v3",
        heroTitle: "Discover YouTube videos,<br>the <em>smarter</em> way!",
        heroDesc: "VidScope is a next-generation YouTube search & analytics app that instantly finds the best videos using advanced filters for language, region, duration, and more.",
        heroBtnPrimary: "🎬 Get Started Free",
        heroBtnSecondary: "See Features",
        slide1: "🔍 Keyword Search → Results",
        slide2: "📊 Trend Analysis Charts",
        slide3: "🎬 Search Results List",
        slide4: "▶️ Video Preview",
        featuresLabel: "Features",
        featuresTitle: "Search, unrestricted.",
        featuresDesc: "VidScope delivers precision filtering beyond what YouTube's standard search can offer.",
        feature1Title: "Multilingual & Regional Filters",
        feature1Desc: "Narrow down videos by language — Japanese, English, Korean, Chinese, and more. Specify a region to discover local trends.",
        feature2Title: "View Count Ranking",
        feature2Desc: "Accurate sorting by view count reveals popular videos at a glance. Engagement rate calculated automatically.",
        feature3Title: "Duration Filter",
        feature3Desc: "Easily switch between short, standard, and long-form videos. Show only what fits your purpose.",
        feature4Title: "Estimated Revenue Simulation",
        feature4Desc: "Automatically calculates estimated video revenue based on CPM, with customizable CPM per genre.",
        feature5Title: "Multi API Key Support",
        feature5Desc: "Register multiple API keys. Automatic rotation on quota exceeded keeps your search running.",
        feature6Title: "Secure by Design",
        feature6Desc: "Built-in admin authentication, rate limiting, and security headers for peace of mind.",
        howLabel: "How it works",
        howTitle: "Get started in 3 steps",
        howDesc: "No complicated setup required. Start using it right away.",
        step1Title: "Create an Account",
        step1Desc: "Sign up for a free account with your email address. Takes 30 seconds.",
        step2Title: "Set an API Key",
        step2Desc: "Get an API key from Google Cloud Console and register it in the settings screen.",
        step3Title: "Start Searching",
        step3Desc: "Set your keyword and filters to discover the perfect videos.",
        pricingLabel: "Pricing",
        pricingTitle: "Find the plan that fits you.",
        pricingDesc: "Scale flexibly from personal use to full-scale operation.",
        freeTitle: "Free",
        freePriceSuffix: "/mo",
        freeDesc: "Best for personal use",
        freeF1: "100 searches per day",
        freeF2: "Basic filters (language, period)",
        freeF3: "1 API key",
        freeF4: "View count ranking",
        freeF5: "Estimated revenue analysis",
        freeF6: "Channel analysis",
        freeF7: "Priority support",
        freeBtn: "Get Started Free",
        proBadge: "Most Popular",
        proTitle: "Pro",
        proPriceSuffix: "/mo",
        proDesc: "For creators & marketers",
        proF1: "Unlimited searches",
        proF2: "All filters available",
        proF3: "Unlimited API keys",
        proF4: "View count ranking",
        proF5: "Estimated revenue analysis",
        proF6: "Channel analysis",
        proF7: "Priority support",
        proBtn: "Start with Pro",
        entTitle: "Enterprise",
        entPrice: "Contact Us",
        entDesc: "For teams & organizations",
        entF1: "All Pro features",
        entF2: "Team member management",
        entF3: "Unlimited API keys",
        entF4: "Custom dashboard",
        entF5: "Data export (CSV)",
        entF6: "SLA guarantee",
        entF7: "Priority support",
        entBtn: "Contact Us",
        faqLabel: "FAQ",
        faqTitle: "Frequently Asked Questions",
        faq1Q: "Do I need to provide my own API key?",
        faq1A: "Yes, you need a YouTube Data API v3 key, which you can get for free from Google Cloud Console. A step-by-step guide is available on the settings screen.",
        faq2Q: "What about API quota limits?",
        faq2A: "The default quota for the YouTube Data API is 10,000 units per day. VidScope supports automatic rotation across multiple API keys, so you can use quota efficiently.",
        faq3Q: "Does the free plan expire?",
        faq3A: "No, the free plan never expires. There are search limits, but you can use the core features indefinitely.",
        faq4Q: "Is my data safe?",
        faq4A: "VidScope does not collect or store any user data. Search queries are sent directly to the YouTube API and are never logged on our servers.",
        faq5Q: "Can I change or cancel my plan?",
        faq5A: "Yes, you can change or cancel your plan at any time. Refunds are prorated accordingly.",
        ctaTitle: "Let's get started.",
        ctaDesc: "Transform your YouTube video search experience with VidScope.",
        ctaBtn: "🎬 Get Started Free",
      },
      contact: {
        docTitle: "Contact | VidScope",
        heading: "Contact Us",
        subtitle: "Feel free to reach out with questions, requests, or data deletion requests.",
        nameLabel: "Name",
        namePlaceholder: "John Smith",
        emailLabel: "Email Address",
        emailPlaceholder: "example@email.com",
        categoryLabel: "Category",
        categoryPlaceholder: "Please select",
        categoryGeneral: "General Inquiry",
        categoryBug: "Bug Report",
        categoryFeature: "Feature Request",
        categoryDataDeletion: "Data Deletion Request",
        categoryPrivacy: "Privacy Question",
        categoryOther: "Other",
        messageLabel: "Message",
        messagePlaceholder: "Please enter your message...",
        submitBtn: "Submit",
        submittingBtn: "Submitting...",
        successHeading: "✓ Submitted",
        successMessage: "Thank you for contacting us.<br>We will review your message and get back to you.",
        backToTop: "Back to Home",
        submitFailed: "Submission failed. Please try again later.",
      },
      privacy: {
        docTitle: "Privacy Policy | VidScope",
      },
      terms: {
        docTitle: "Terms of Service | VidScope",
      },
    },
  };

  var STORAGE_KEY = "vidscope_lang";
  var SUPPORTED = ["ja", "en"];
  var DEFAULT_LANG = "ja";
  var LANG_FLAGS = { ja: "🇯🇵", en: "🇺🇸" };
  var LANG_NAMES = { ja: "日本語", en: "English" };

  function detectLang() {
    try {
      var params = new URLSearchParams(window.location.search);
      var urlLang = params.get("lang");
      if (urlLang && SUPPORTED.indexOf(urlLang) !== -1) return urlLang;
    } catch (e) { /* noop */ }
    try {
      var saved = localStorage.getItem(STORAGE_KEY);
      if (saved && SUPPORTED.indexOf(saved) !== -1) return saved;
    } catch (e) { /* noop */ }
    return DEFAULT_LANG;
  }

  var currentLang = detectLang();

  function lookup(dict, key) {
    var parts = key.split(".");
    var o = dict;
    for (var i = 0; i < parts.length; i++) {
      if (o == null || typeof o !== "object" || !(parts[i] in o)) return undefined;
      o = o[parts[i]];
    }
    return o;
  }

  function t(key, params) {
    var str = lookup(DICT[currentLang], key);
    if (str === undefined) str = lookup(DICT[DEFAULT_LANG], key);
    if (str === undefined) return key;
    if (params) {
      Object.keys(params).forEach(function (k) {
        str = str.replace(new RegExp("\\{\\{" + k + "\\}\\}", "g"), params[k]);
      });
    }
    return str;
  }

  function applyTranslations(root) {
    var scope = root || document;
    scope.querySelectorAll("[data-i18n]").forEach(function (el) {
      el.textContent = t(el.getAttribute("data-i18n"));
    });
    scope.querySelectorAll("[data-i18n-html]").forEach(function (el) {
      el.innerHTML = t(el.getAttribute("data-i18n-html"));
    });
    scope.querySelectorAll("[data-i18n-placeholder]").forEach(function (el) {
      el.setAttribute("placeholder", t(el.getAttribute("data-i18n-placeholder")));
    });
    scope.querySelectorAll("[data-i18n-title]").forEach(function (el) {
      el.setAttribute("title", t(el.getAttribute("data-i18n-title")));
    });
    scope.querySelectorAll("[data-i18n-aria-label]").forEach(function (el) {
      el.setAttribute("aria-label", t(el.getAttribute("data-i18n-aria-label")));
    });
    scope.querySelectorAll("[data-i18n-value]").forEach(function (el) {
      el.setAttribute("value", t(el.getAttribute("data-i18n-value")));
    });
    // legal dual-block toggle (privacy.html / terms.html)
    var legalLang = SUPPORTED.indexOf(currentLang) !== -1 ? currentLang : DEFAULT_LANG;
    var hasLegalBlocks = scope.querySelector(".content-en, .content-ja");
    if (hasLegalBlocks) {
      scope.querySelectorAll(".content-en, .content-ja").forEach(function (el) {
        el.classList.remove("active");
      });
      scope.querySelectorAll(".content-" + legalLang).forEach(function (el) {
        el.classList.add("active");
      });
    }
    document.title = t("app.docTitle") !== "app.docTitle" && document.querySelector('[data-i18n-doctitle]')
      ? t(document.querySelector('[data-i18n-doctitle]').getAttribute('data-i18n-doctitle'))
      : document.title;
    var titleEl = document.querySelector("[data-i18n-doctitle]");
    if (titleEl) document.title = t(titleEl.getAttribute("data-i18n-doctitle"));
  }

  function updateLangUI() {
    document.querySelectorAll("[data-lang-current]").forEach(function (el) {
      var lang = currentLang;
      el.textContent = (LANG_FLAGS[lang] || "") + " " + (LANG_NAMES[lang] || lang.toUpperCase());
    });
    document.querySelectorAll(".lang-option").forEach(function (el) {
      el.classList.toggle("active", el.getAttribute("data-lang") === currentLang);
    });
  }

  function setLanguage(lang) {
    if (SUPPORTED.indexOf(lang) === -1) return;
    currentLang = lang;
    try { localStorage.setItem(STORAGE_KEY, lang); } catch (e) { /* noop */ }
    document.documentElement.setAttribute("lang", lang);
    applyTranslations();
    updateLangUI();
    document.dispatchEvent(new CustomEvent("vidscope:langchange", { detail: { lang: lang } }));
  }

  function getLang() { return currentLang; }
  function getLocale() { return currentLang === "ja" ? "ja-JP" : "en-US"; }

  function initLangSwitcher() {
    document.querySelectorAll(".lang-switcher").forEach(function (sw) {
      var btn = sw.querySelector(".lang-switcher-btn");
      var menu = sw.querySelector(".lang-switcher-menu");
      if (!btn || !menu) return;
      btn.addEventListener("click", function (e) {
        e.stopPropagation();
        var willOpen = !menu.classList.contains("open");
        document.querySelectorAll(".lang-switcher-menu.open").forEach(function (m) { m.classList.remove("open"); });
        if (willOpen) menu.classList.add("open");
      });
      menu.querySelectorAll(".lang-option").forEach(function (opt) {
        opt.addEventListener("click", function () {
          setLanguage(opt.getAttribute("data-lang"));
          menu.classList.remove("open");
        });
      });
    });
    document.addEventListener("click", function () {
      document.querySelectorAll(".lang-switcher-menu.open").forEach(function (m) { m.classList.remove("open"); });
    });
  }

  function init() {
    document.documentElement.setAttribute("lang", currentLang);
    applyTranslations();
    updateLangUI();
    initLangSwitcher();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  window.VidScopeI18n = {
    t: t,
    applyTranslations: applyTranslations,
    setLanguage: setLanguage,
    getLang: getLang,
    getLocale: getLocale,
  };
})();
