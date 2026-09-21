create or replace function is_bot_page_view(user_agent text, ip text, path text)
returns boolean language sql immutable as $$
  select
    -- UAパターン一致（bot/spider/crawler等の部分一致 + Google系/SEOツール系/AI系クローラー個別列挙）
    (
      user_agent is not null and (
        lower(user_agent) ~ '(bot|spider|crawler|curl|wget|go-http-client|python-requests|python-urllib|libwww-perl|scrapy|httpclient|java/|okhttp|postmanruntime|axios|node-fetch|masscan|nmap|nikto|sqlmap|zgrab|agency)'
        or lower(user_agent) like '%google-inspectiontool%'
        or lower(user_agent) like '%googleother%'
        or lower(user_agent) like '%google-extended%'
        or lower(user_agent) like '%feedfetcher-google%'
        or lower(user_agent) like '%google favicon%'
        or lower(user_agent) like '%apis-google%'
        or lower(user_agent) like '%storebot-google%'
        or lower(user_agent) like '%google-cloudvertexbot%'
        or lower(user_agent) like '%mediapartners-google%'
        or lower(user_agent) like '%adsbot-google%'
        or lower(user_agent) like '%ahrefsbot%'
        or lower(user_agent) like '%semrushbot%'
        or lower(user_agent) like '%dotbot%'
        or lower(user_agent) like '%mj12bot%'
        or lower(user_agent) like '%rogerbot%'
        or lower(user_agent) like '%blexbot%'
        or lower(user_agent) like '%seznambot%'
        or lower(user_agent) like '%petalbot%'
        or lower(user_agent) like '%bytespider%'
        or lower(user_agent) like '%gptbot%'
        or lower(user_agent) like '%chatgpt-user%'
        or lower(user_agent) like '%claudebot%'
        or lower(user_agent) like '%ccbot%'
        or lower(user_agent) like '%amazonbot%'
        or lower(user_agent) like '%meta-externalagent%'
        or lower(user_agent) like '%meta-externalfetcher%'
        or lower(user_agent) like '%yandexbot%'
        or lower(user_agent) like '%applebot%'
        or lower(user_agent) like '%bingpreview%'
        or lower(user_agent) like '%headlesschrom%'
        -- 2026-09-05追加: 8/30スパイク残存266の内訳から検出されたAI/SNSクローラー
        or lower(user_agent) like '%perplexity-user%'
        or lower(user_agent) like '%claude-user%'
        or lower(user_agent) like '%facebookexternalhit%'
        or lower(user_agent) like '%whatsapp/%'
        or lower(user_agent) like '%wordpresschecker%'
        -- 2026-09-12/13スパイク追加: 脆弱性スキャナー系UA
        or lower(user_agent) like '%nuclei%'
        or lower(user_agent) like '%gobuster%'
        or lower(user_agent) like '%xray%'
        -- 2026-09-12/13追加: Mobile Safari 13.0.3 / iOS 13.2.3 詐称パターン
        -- 本物のUAは Version/13.0.3 + Mobile/15E148 + Safari/604.1(WebKitビルド) を含む。
        -- ボットは Version/13.0.3 と Mobile/15E148 を詐称するケースがあるため、
        -- これらと iOS 13.2.3 の組み合わせを検出対象とする。
        or (
          lower(user_agent) like '%mobile/15e148%'
          and (
            lower(user_agent) like '%version/13.0.3%'
            or lower(user_agent) like '%safari/13.0.3%'
          )
          and (
            lower(user_agent) like '%ios 13.2.3%'
            or lower(user_agent) like '%iphone os 13_2_3%'
            or lower(user_agent) like '%13_2_3%'
          )
        )
      )
    )
    or
    -- 既知のbot/クローラーIPレンジ（UA偽装対策。43.128.0.0/10 = Tencent Cloud、66.249.64.0/19 = Googlebot）
    -- 2026-08-30スパイク対応: Tencent Cloud追加レンジ(1.12.0.0/14, 118.24.0.0/16, 101.32.0.0/15)を追加
    -- 2026-09-05追加: DigitalOcean /24, AWS EC2 us-east-2/eu-west-1 /24, GCP us-central1 /24
    -- 2026-09-05追加(2): 8/30スパイクの残存主要クラウドスクレイパー /24 x5 (GCP x2, Azure, Vultr, OVH)
    (
      ip is not null and ip != '' and ip ~ '^[0-9.]+$' and (
        inet(ip) <<= inet '43.128.0.0/10'
        or inet(ip) <<= inet '1.12.0.0/14'
        or inet(ip) <<= inet '118.24.0.0/16'
        or inet(ip) <<= inet '101.32.0.0/15'
        or inet(ip) <<= inet '66.249.64.0/19'
        or inet(ip) <<= inet '167.71.6.0/24'
        or inet(ip) <<= inet '3.151.194.0/24'
        or inet(ip) <<= inet '54.77.166.0/24'
        or inet(ip) <<= inet '35.254.67.0/24'
        or inet(ip) <<= inet '35.185.159.0/24'
        or inet(ip) <<= inet '34.78.15.0/24'
        or inet(ip) <<= inet '20.104.81.0/24'
        or inet(ip) <<= inet '170.64.159.0/24'
        or inet(ip) <<= inet '158.69.55.0/24'
        -- 2026-09-05追加(3): 8/30スパイク残存266の内訳から特定された追加ボット群
        or inet(ip) <<= inet '45.148.10.0/24'
        or inet(ip) <<= inet '37.66.170.0/24'
        or inet(ip) <<= inet '150.109.119.0/24'
        -- 2026-09-09追加: 直近アクセスログから検出された追加ボット/スキャナー群
        -- Vultr Japan: 167.179.69.76 でPHP脆弱性スキャンを実施
        or inet(ip) <<= inet '167.179.69.0/24'
        -- Tencent Cloud: Mobile Safari 13.0.3 / iOS 13.2.3 を偽装したボット群
        or inet(ip) <<= inet '82.156.0.0/15'
        or inet(ip) <<= inet '119.45.0.0/16'
        -- Google Cloud: root pathへ不自然なアクセス（Other/Other）
        or inet(ip) <<= inet '34.26.102.0/24'
        -- DigitalOcean: 137.184.227.0/24 (Chrome 131), 188.166.67.0/24 (Netherlands Other/Other)
        or inet(ip) <<= inet '137.184.227.0/24'
        or inet(ip) <<= inet '188.166.67.0/24'
        -- Microsoft Azure: 20.172.36.0/24 (Chrome Mobile WebView 60 old)
        or inet(ip) <<= inet '20.172.36.0/24'
        -- Scaleway? France: 51.15.215.0/24 (duplicate Chrome hits)
        or inet(ip) <<= inet '51.15.215.0/24'
        -- US Other/Other
        or inet(ip) <<= inet '66.132.186.0/24'
        -- Hong Kong Other/Other
        or inet(ip) <<= inet '199.45.155.0/24'
        -- 2026-09-12/13スパイク追加: Tencent Cloud上のMobile Safari偽装ボット/設定探索スキャナー群
        or inet(ip) <<= inet '129.226.0.0/16'
        or inet(ip) <<= inet '119.28.0.0/16'
        or inet(ip) <<= inet '43.132.0.0/14'
        or inet(ip) <<= inet '170.106.0.0/16'
        -- 2026-09-12/13スパイク追加: DigitalOcean上のWordPress/設定探索スキャナー
        or inet(ip) <<= inet '146.190.32.0/24'
        or inet(ip) <<= inet '165.227.32.0/24'
        -- 2026-09-18/20スパイク追加: VidScope daily-detailで検出された設定/認証情報探索スキャナー群
        -- 9/18: 34.94.154.180 (364 hits), 35.205.88.64 (135 hits) — Google Cloud
        or inet(ip) <<= inet '34.94.0.0/16'
        or inet(ip) <<= inet '35.205.0.0/16'
        -- 9/18: 45.138.12.22 (137 hits) — ホスティング系
        or inet(ip) <<= inet '45.138.12.0/24'
        -- 9/20: 34.156.22.222 (138 hits), 34.38.113.44 (136 hits) — Google Cloud
        or inet(ip) <<= inet '34.156.0.0/16'
        or inet(ip) <<= inet '34.38.0.0/16'
        -- 9/20: 195.178.110.15 (241 hits) — ホスティング系
        or inet(ip) <<= inet '195.178.110.0/24'
      )
    )
    or
    -- 脆弱性スキャンで狙われる典型パス
    (
      path is not null and (
        lower(path) like '/wp-admin%' or lower(path) like '/wp-login.php%'
        or lower(path) like '/wp-content%' or lower(path) like '/wp-includes%'
        or lower(path) like '/wp-json%' or lower(path) like '/xmlrpc.php%'
        or lower(path) like '/.env%' or lower(path) like '/.git%'
        or lower(path) like '/phpmyadmin%' or lower(path) like '/pma%'
        or lower(path) like '/vendor/%' or lower(path) like '/.aws%'
        or lower(path) like '/.ssh%' or lower(path) like '/config.json%'
        or lower(path) like '/actuator%' or lower(path) like '/cgi-bin%'
        or lower(path) like '/.docker%' or lower(path) like '/.vscode%'
        or lower(path) like '/.idea%' or lower(path) like '/server-status%'
        or lower(path) like '/telescope%' or lower(path) like '/_profiler%'
        or lower(path) like '/debug/default/view%' or lower(path) like '/geoserver%'
        -- バックアップ探索系（プレフィックス）
        or lower(path) like '/backup%' or lower(path) like '/backups%'
        or lower(path) like '/dump%'
        -- 2026-09-12/13スパイク追加: 設定/認証情報探索系スキャン（プレフィックス）
        or lower(path) like '/system%' or lower(path) like '/storage%'
        or lower(path) like '/store/app/etc%' or lower(path) like '/src/prisma%'
        or lower(path) like '/_src%' or lower(path) like '/sphinxsearch%'
        or lower(path) like '/.svn%' or lower(path) like '/database_credentials%'
        or lower(path) like '/credentials%' or lower(path) like '/.credentials%'
        or lower(path) like '/.dbeaver%' or lower(path) like '/sftp%'
        or lower(path) like '/deployment-config%' or lower(path) like '/.config/sftp%'
        or lower(path) like '/recentservers%' or lower(path) like '/filezilla%'
        or lower(path) like '/ftpsync%' or lower(path) like '/secrets%'
        -- 2026-09-18/20スパイク追加: 設定/認証情報ファイル探索系（プレフィックス/完全一致）
        or lower(path) like '/env%' or lower(path) like '/config/aws.json%'
        or lower(path) like '/appsettings.json%' or lower(path) like '/appsettings.production.json%'
        or lower(path) like '/appsettings.development.json%' or lower(path) like '/settings.ini%'
        or lower(path) like '/terraform.tfvars%' or lower(path) like '/application_default_credentials.json%'
        or lower(path) like '/.config/gcloud/%' or lower(path) like '/phpinfo%'
        -- 2026-09-18/20スパイク追加: スキャナーが多用するディレクトリプレフィックス
        or lower(path) like '/var/www/%' or lower(path) like '/public_html/%'
        or lower(path) like '/web/%' or lower(path) like '/staging/%'
        or lower(path) like '/server/%' or lower(path) like '/test/%'
        or lower(path) like '/v1/%' or lower(path) like '/v2/%'
        or lower(path) like '/v3/%' or lower(path) like '/src/%'
        -- 2026-09-18/20スパイク追加: 任意ディレクトリ配下の .env ファイル
        or lower(path) like '%/.env'
        -- バックアップ/ダンプファイル拡張子（サフィックス）
        or lower(path) like '%.bak' or lower(path) like '%.sql'
        or lower(path) like '%.zip' or lower(path) like '%.tar.gz'
        -- 2026-09-09追加: VidScopeにPHPエンドポイントはないため、.phpで終わる全パスをスキャンとみなす
        or lower(path) like '%.php'
        -- 2026-09-12/13スパイク追加: 設定/認証情報ファイル拡張子（サフィックス）
        or lower(path) like '%.inc' or lower(path) like '%.yml'
        or lower(path) like '%.yaml' or lower(path) like '%.xml'
        or lower(path) like '%.conf' or lower(path) like '%.log'
        or lower(path) like '%.settings' or lower(path) like '%.key'
        or lower(path) like '%.db' or lower(path) like '%.sh'
        or lower(path) like '%.history'
        -- 2026-09-09追加(5): 先頭ダブルスラッシュ等でプレフィックス判定をすり抜けるWordPressスキャンを捕捉
        or lower(path) like '%/wp-admin/%'
        or lower(path) like '%/wp-login.php%'
        or lower(path) like '%/wp-content/%'
        or lower(path) like '%/wp-includes/%'
        or lower(path) like '%/wp-json/%'
        or lower(path) like '%wlwmanifest.xml%'
        -- 2026-09-12/13スパイク追加: WordPress関連の任意プレフィックススキャン
        or lower(path) like '%/wp/%'
        or lower(path) like '%/wordpress/%'
      )
    );
$$;
