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

create or replace function get_daily_pageviews(days_back integer)
returns table(date text, count bigint) language sql stable as $$
  select to_char("timestamp", 'YYYY-MM-DD'), count(*)::bigint
  from page_views where "timestamp" >= now() - (days_back || ' days')::interval
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
-- Row Level Security
-- バックエンドは service_role キーを使用するためRLSは常にバイパスされる。
-- ここではRLSを有効化した上でポリシーを一切追加しないことで、
-- anon/authenticatedキー経由のアクセスをデフォルト拒否にする（セキュリティ推奨設定）。
-- ============================================

alter table page_views enable row level security;
alter table search_queries enable row level security;
alter table contacts enable row level security;
alter table contact_replies enable row level security;
