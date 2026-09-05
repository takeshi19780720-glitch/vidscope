-- ① is_bot_page_view（ボット判定関数）
create or replace function is_bot_page_view(user_agent text, ip text, path text)
returns boolean language sql immutable as $$
  select
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
        or lower(user_agent) like '%headlesschrom%'
      )
    )
    or
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
      )
    )
    or
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
        or lower(path) like '/backup%' or lower(path) like '/backups%'
        or lower(path) like '/dump%'
        or lower(path) like '%.bak' or lower(path) like '%.sql'
        or lower(path) like '%.zip' or lower(path) like '%.tar.gz'
      )
    );
$$;

-- ② get_daily_pageviews（日別PVグラフ、ボット除外付き）
create or replace function get_daily_pageviews(days_back integer, offset_days integer default 0)
returns table(date text, count bigint) language sql stable as $$
  select to_char("timestamp", 'YYYY-MM-DD'), count(*)::bigint
  from page_views
  where "timestamp" >= now() - ((days_back + offset_days) || ' days')::interval
    and "timestamp" < now() - (offset_days || ' days')::interval
    and not is_bot_page_view(user_agent, ip, path)
  group by 1 order by 1;
$$;
