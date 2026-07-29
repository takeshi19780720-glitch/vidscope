-- VidScope Supabase スキーマ
-- Supabaseダッシュボード > SQL Editor でこのファイルの内容をそのまま実行してください。

-- ============================================
-- テーブル
-- ============================================

create table if not exists page_views (
  id bigserial primary key,
  "timestamp" timestamptz not null default now(),
  path text not null,
  ip text,
  user_agent text,
  browser text,
  os text,
  language text,
  referer text,
  country text
);
create index if not exists idx_pv_timestamp on page_views("timestamp");
create index if not exists idx_pv_path on page_views(path);

create table if not exists search_queries (
  id bigserial primary key,
  "timestamp" timestamptz not null default now(),
  query text,
  max_results integer,
  duration_filter text,
  published_after text,
  category_id text,
  language text,
  region text,
  ip text
);
create index if not exists idx_sq_timestamp on search_queries("timestamp");

create table if not exists contacts (
  id bigserial primary key,
  name text,
  email text,
  category text,
  message text,
  created_at timestamptz not null default now()
);
create index if not exists idx_contacts_created_at on contacts(created_at);

-- お問い合わせへの管理者返信履歴（1件のcontactに対して複数回返信可能）
create extension if not exists pgcrypto;

create table if not exists contact_replies (
  id uuid primary key default gen_random_uuid(),
  contact_id bigint not null references contacts(id) on delete cascade,
  subject text not null,
  body text not null,
  status text not null default 'pending' check (status in ('pending', 'sent', 'failed')),
  error text,
  created_at timestamptz not null default now()
);
create index if not exists idx_contact_replies_contact_id on contact_replies(contact_id);
create index if not exists idx_contact_replies_created_at on contact_replies(created_at);

-- ============================================
-- ダッシュボード集計用 RPC関数
-- ============================================

create or replace function get_analytics_summary()
returns json language sql stable as $$
  select json_build_object(
    'pv_today', (select count(*) from page_views where "timestamp" >= date_trunc('day', now())),
    'uv_today', (select count(distinct ip) from page_views where "timestamp" >= date_trunc('day', now())),
    'searches_today', (select count(*) from search_queries where "timestamp" >= date_trunc('day', now())),
    'pv_total', (select count(*) from page_views),
    'pv_week', (select count(*) from page_views where "timestamp" >= now() - interval '7 days'),
    'pv_month', (select count(*) from page_views where "timestamp" >= now() - interval '30 days')
  );
$$;

-- offset_days: 0 = 直近N日間（従来通り）。7を指定すると「直近N日間の1つ前の期間」
-- （例: days_back=7, offset_days=7 → 8〜14日前の週）を取得できる。
create or replace function get_daily_pageviews(days_back integer, offset_days integer default 0)
returns table(date text, count bigint) language sql stable as $$
  select to_char("timestamp", 'YYYY-MM-DD'), count(*)::bigint
  from page_views
  where "timestamp" >= now() - ((days_back + offset_days) || ' days')::interval
    and "timestamp" < now() - (offset_days || ' days')::interval
  group by 1 order by 1;
$$;

create or replace function get_top_pages(limit_count integer)
returns table(path text, count bigint) language sql stable as $$
  select path, count(*)::bigint from page_views group by path order by count(*) desc limit limit_count;
$$;

create or replace function get_top_searches(limit_count integer)
returns table(query text, count bigint) language sql stable as $$
  select query, count(*)::bigint from search_queries
  where query is not null and query != '' group by query order by count(*) desc limit limit_count;
$$;

create or replace function get_top_countries(limit_count integer)
returns table(country text, count bigint) language sql stable as $$
  select country, count(*)::bigint from page_views
  where country is not null and country != '' group by country order by count(*) desc limit limit_count;
$$;

-- refererのURLからドメイン単位で集計する（例: https://www.reddit.com/r/microsaas/... -> reddit.com）。
-- referer が空/nullの場合は「Direct / (none)」として集計する。days_back を指定すると集計期間を絞れる（nullで全期間）。
create or replace function get_top_referrers(limit_count integer, days_back integer default null)
returns table(domain text, count bigint) language sql stable as $$
  select
    case
      when referer is null or referer = '' then 'Direct / (none)'
      else regexp_replace(
        regexp_replace(referer, '^https?://', '', 'i'),
        '^(www\.)?([^/]+).*$', '\2'
      )
    end as domain,
    count(*)::bigint
  from page_views
  where (days_back is null or "timestamp" >= now() - (days_back || ' days')::interval)
  group by 1
  order by count(*) desc
  limit limit_count;
$$;

create or replace function get_browser_os_stats()
returns json language sql stable as $$
  select json_build_object(
    'browsers', (select coalesce(json_agg(row_to_json(t)), '[]'::json) from
      (select browser as name, count(*)::bigint as count from page_views
       where browser is not null and browser != '' group by browser order by count(*) desc limit 10) t),
    'os', (select coalesce(json_agg(row_to_json(t)), '[]'::json) from
      (select os as name, count(*)::bigint as count from page_views
       where os is not null and os != '' group by os order by count(*) desc limit 10) t)
  );
$$;

create or replace function cleanup_old_analytics(cutoff timestamptz)
returns void language sql as $$
  delete from page_views where "timestamp" < cutoff;
  delete from search_queries where "timestamp" < cutoff;
$$;

-- ============================================
-- ボット判定（集計時フィルタ）
-- ============================================
-- 過去データは遡及削除しない方針のため、bot除外はここでは「保存されたレコードを
-- 集計時に判定して弾く」形で実装する。判定ロジックは app/analytics.py の
-- _is_bot_user_agent / _is_bot_ip / _is_scan_path とできる限り一致させること。
-- UAパターンや IPレンジを追加/変更した場合は、Python側とこの関数の両方を
-- 同時に更新する必要がある点に注意。
create or replace function is_bot_page_view(user_agent text, ip text, path text)
returns boolean language sql immutable as $$
  select
    -- UAパターン一致（bot/spider/crawler等の部分一致 + Google系/SEOツール系/AI系クローラー個別列挙）
    (
      user_agent is not null and (
        lower(user_agent) ~ '(bot|spider|crawler|curl|wget|go-http-client|python-requests|python-urllib|libwww-perl|scrapy|httpclient|java/|okhttp|postmanruntime|axios|node-fetch|masscan|nmap|nikto|sqlmap|zgrab)'
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
      )
    )
    or
    -- 既知のbot/クローラーIPレンジ（UA偽装対策。43.128.0.0/10 = Tencent Cloud、66.249.64.0/19 = Googlebot）
    (
      ip is not null and ip != '' and ip ~ '^[0-9.]+$' and (
        inet(ip) <<= inet '43.128.0.0/10'
        or inet(ip) <<= inet '66.249.64.0/19'
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
      )
    );
$$;

-- 除外前(raw)/除外後(filtered)を並べて返すサマリー。
-- 管理画面で「フィルタがどれだけ効いているか」を可視化するために使う。
create or replace function get_analytics_summary_with_raw()
returns json language sql stable as $$
  select json_build_object(
    'pv_today_raw', (select count(*) from page_views where "timestamp" >= date_trunc('day', now())),
    'pv_today_filtered', (select count(*) from page_views where "timestamp" >= date_trunc('day', now()) and not is_bot_page_view(user_agent, ip, path)),
    'uv_today_raw', (select count(distinct ip) from page_views where "timestamp" >= date_trunc('day', now())),
    'uv_today_filtered', (select count(distinct ip) from page_views where "timestamp" >= date_trunc('day', now()) and not is_bot_page_view(user_agent, ip, path)),
    'pv_total_raw', (select count(*) from page_views),
    'pv_total_filtered', (select count(*) from page_views where not is_bot_page_view(user_agent, ip, path))
  );
$$;

-- 国別TOPの除外前/除外後を1回のクエリで返す。
-- raw_count: 全レコード数, filtered_count: bot除外後の件数（該当国がbotのみなら0行にはならず表示され得る）
create or replace function get_top_countries_with_raw(limit_count integer)
returns table(country text, raw_count bigint, filtered_count bigint) language sql stable as $$
  select
    country,
    count(*)::bigint as raw_count,
    count(*) filter (where not is_bot_page_view(user_agent, ip, path))::bigint as filtered_count
  from page_views
  where country is not null and country != ''
  group by country
  order by raw_count desc
  limit limit_count;
$$;

-- ============================================
-- Row Level Security
-- バックエンドは service_role キーを使用するためRLSは常にバイパスされる。
-- ここではRLSを有効化した上でポリシーを一切追加しないことで、
-- anon/authenticatedキー経由のアクセスをデフォルト拒否にする（セキュリティ推奨設定）。
-- ============================================

alter table page_views enable row level security;
alter table search_queries enable row level security;
alter table contacts enable row level security;
alter table contact_replies enable row level security;
