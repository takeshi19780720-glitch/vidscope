"""アクセス監視モジュール - Supabase(PostgreSQL)ベースのアナリティクス"""

import ipaddress
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from user_agents import parse as parse_ua

from app import supabase_client as sb

logger = logging.getLogger("vidscope")

# アクティブセッション追跡
_active_sessions: dict[str, float] = {}  # {session_id: last_seen_timestamp}
_sessions_lock = threading.Lock()
SESSION_TIMEOUT = 300  # 5分

# ページビュー計測(GeoIP解決 + Supabase insert)を実行するための専用executor。
#
# 以前はリクエストごとに threading.Thread(daemon=True).start() していたため、
# bot判定をすり抜けた高頻度アクセス時にスレッドが無制限に積み上がるリスクがあった
# （1スレッドの最悪生存時間は GeoIPタイムアウト5s + 429リトライ1.5s + 5s +
# Supabase insertタイムアウト10s ≒ 20秒程度）。
# ThreadPoolExecutor で同時実行数の上限を持たせ、キューが溢れた場合は
# 「計測1件を捨ててWARNINGログを出す」方針にする。計測データの欠損は
# サービス安定性より優先度が低いため許容する。
_ANALYTICS_MAX_WORKERS = 6
_ANALYTICS_QUEUE_MAXSIZE = 200  # ワーカー数 + キュー待ちの上限（超過分は投入を諦める）
_analytics_executor = ThreadPoolExecutor(
    max_workers=_ANALYTICS_MAX_WORKERS, thread_name_prefix="analytics-io"
)
_analytics_pending_lock = threading.Lock()
_analytics_pending_count = 0


def _submit_analytics_task(fn, *args) -> None:
    """バックグラウンドI/Oタスク(GeoIP解決+Supabase insert)をexecutorに投入する。

    投入待ち件数が _ANALYTICS_QUEUE_MAXSIZE を超えている場合は、
    プロセスの安定性を優先してこの1件の計測を諦め、WARNINGログのみ残す。
    """
    global _analytics_pending_count
    with _analytics_pending_lock:
        if _analytics_pending_count >= _ANALYTICS_QUEUE_MAXSIZE:
            logger.warning(
                "Analytics task queue full (>= %d pending), dropping one measurement",
                _ANALYTICS_QUEUE_MAXSIZE,
            )
            return
        _analytics_pending_count += 1

    def _run():
        global _analytics_pending_count
        try:
            fn(*args)
        finally:
            with _analytics_pending_lock:
                _analytics_pending_count -= 1

    try:
        _analytics_executor.submit(_run)
    except RuntimeError:
        # executor が既に shutdown 済み（プロセス終了処理中等）。計測を諦める。
        with _analytics_pending_lock:
            _analytics_pending_count -= 1
        logger.warning("Analytics executor already shut down, dropping one measurement")


def shutdown_analytics_executor(wait_timeout: float = 5.0) -> None:
    """プロセス終了時にexecutorをgraceful shutdownする。

    実行中のinsertを可能な限り完了させるが、シャットダウンを長時間ブロック
    しないよう待機時間には上限を設ける（デフォルト5秒）。
    """

    def _wait():
        _analytics_executor.shutdown(wait=True)

    waiter = threading.Thread(target=_wait, daemon=True)
    waiter.start()
    waiter.join(timeout=wait_timeout)
    if waiter.is_alive():
        logger.warning(
            "Analytics executor shutdown did not finish within %.1fs, proceeding anyway",
            wait_timeout,
        )


# 管理者自身のアクセスをアナリティクスから除外するためのCookie
# （管理画面ログイン成功時にセットし、以後のページビュー/検索記録を除外する）
EXCLUDE_COOKIE_NAME = "vidscope_exclude_analytics"
EXCLUDE_COOKIE_MAX_AGE = 60 * 60 * 24 * 365  # 1年（秒）

# IP→国キャッシュ
_geo_cache: dict[str, str] = {}
_geo_cache_lock = threading.Lock()

# 明らかなbot/スクリプト系User-Agentのパターン（大文字小文字無視、部分一致）
# 'bot' / 'spider' / 'crawler' の部分一致だけでは拾えない主要クローラーを個別に列挙している。
#
# !!! 二重管理注意 !!!
# このパターンは supabase_schema.sql の is_bot_page_view() 内の正規表現/LIKE条件と
# 意味的に等価になるよう保守されている（保存済み過去データを集計時に判定するため、
# SQL側にも同じロジックが別実装として存在する）。どちらか一方だけを変更すると
# 「新規データはPython側でブロックされるが、過去データの集計ではSQL側の古い
# パターンのまま」というズレが発生する。変更する場合は両方を同時に更新し、
# tests/test_analytics_bot_filter.py の等価性テストを通すこと。
_BOT_UA_PATTERNS = (
    "bot", "spider", "crawler", "curl", "wget", "go-http-client",
    "python-requests", "python-urllib", "libwww-perl", "scrapy",
    "httpclient", "java/", "okhttp", "postmanruntime", "axios",
    "node-fetch", "masscan", "nmap", "nikto", "sqlmap", "zgrab",
    # --- Google系（'bot'を含まない/含んでいても明示しておきたいもの） ---
    "google-inspectiontool",   # Search Consoleのインデックス登録リクエスト・URL検査ツール
    "googleother",             # Google全般クロール（検索インデックス以外の用途）
    "google-extended",         # Bard/Gemini/Vertex AI学習用クローラー
    "feedfetcher-google",      # Googleのフィード取得
    "google favicon",          # favicon取得
    "apis-google",             # Google APIsからのプッシュ通知系フェッチ
    "storebot-google",         # ショッピング関連クローラー
    "google-cloudvertexbot",   # Vertex AI関連クローラー
    "mediapartners-google",    # AdSenseクローラー
    "adsbot-google",           # Google Ads品質チェック
    # --- SEOツール/リンク調査系 ---
    "ahrefsbot", "semrushbot", "dotbot", "mj12bot", "rogerbot",
    "blexbot", "seznambot",
    # --- 商用クロール/スクレイパー系 ---
    "petalbot", "bytespider", "gptbot", "chatgpt-user", "claudebot",
    "ccbot", "amazonbot", "meta-externalagent", "meta-externalfetcher",
    "yandexbot", "applebot", "bingpreview",
)

# 脆弱性スキャン等でよく狙われるパス（プレフィックス/完全一致）
_SCAN_PATH_PREFIXES = (
    "/wp-admin", "/wp-login.php", "/wp-content", "/wp-includes", "/wp-json",
    "/xmlrpc.php", "/.env", "/.git", "/phpmyadmin", "/pma", "/vendor/",
    "/.aws", "/.ssh", "/config.json", "/actuator", "/cgi-bin",
    "/.docker", "/.vscode", "/.idea", "/server-status", "/telescope",
    "/_profiler", "/debug/default/view", "/geoserver",
)

# ボット/クローラーが利用することが判明しているIPレンジ（CIDR）。
# UAを詐称して人間のブラウザを装うケースがあるため、UA判定と独立してIPでも除外する。
# 各エントリは (network, 出自コメント) のタプル。
_BOT_IP_RANGES: tuple[tuple[str, str], ...] = (
    # Tencent Cloud（中国）。国別TOP10のUS/HK等に大量に混入していたボット群のIP帯。
    # UAを "Mobile Safari 13.0.3 / iOS 13.2.3" 等に偽装していたため、UA判定では検出不可。
    ("43.128.0.0/10", "Tencent Cloud"),
    # Googlebot共通クロール帯。UA判定（'googlebot'等）と二重になるが、
    # UA偽装や新規UA追加漏れに備えた保険として保持する。
    ("66.249.64.0/19", "Googlebot common crawl range"),
)

_BOT_NETWORKS: tuple[ipaddress.IPv4Network | ipaddress.IPv6Network, ...] = tuple(
    ipaddress.ip_network(cidr) for cidr, _comment in _BOT_IP_RANGES
)


def _is_bot_user_agent(user_agent: str) -> bool:
    """UAが既知のbot/スクリプト系パターンに一致するか判定する"""
    if not user_agent:
        return False
    ua_lower = user_agent.lower()
    return any(pattern in ua_lower for pattern in _BOT_UA_PATTERNS)


def _is_bot_ip(ip: str) -> bool:
    """既知のbot/クローラーIPレンジ（例: Tencent Cloud, Googlebot）に該当するか判定する。

    UAを詐称しているボット（例: iOS Safariを名乗るTencent Cloud上のスキャナ）を
    UA判定をすり抜けても捕捉できるようにするための機構。
    """
    if not ip:
        return False
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return any(addr in network for network in _BOT_NETWORKS)


def _is_scan_path(path: str) -> bool:
    """脆弱性スキャンでよく狙われるパスかどうか判定する"""
    path_lower = path.lower()
    return any(path_lower.startswith(prefix) for prefix in _SCAN_PATH_PREFIXES)


def init_db():
    """テーブルはSupabase側でSQL Editorにより作成済み。起動時チェックのみ行う。"""
    if not sb.is_configured():
        logger.error(
            "SUPABASE_URL / SUPABASE_KEY が設定されていません。アナリティクス機能は無効化されます。"
        )


def log_page_view(path: str, ip: str, user_agent: str, language: str, referer: str):
    """ページビューを記録（バックグラウンドexecutorでSupabaseへ送信）"""
    # 静的ファイル・APIリクエスト・管理ページは除外
    if path.startswith("/static/") or path.startswith("/api/") or path.startswith("/admin/"):
        return
    if path in ("/robots.txt", "/sitemap.xml", "/favicon.ico"):
        return

    # 明らかなbot/スクリプトのUser-Agentは記録しない
    if _is_bot_user_agent(user_agent):
        return

    # UAを偽装しているボット（既知のクローラー/データセンターIPレンジ）は記録しない
    if _is_bot_ip(ip):
        return

    # 脆弱性スキャン対象の典型的なパスは記録しない
    if _is_scan_path(path):
        return

    ua = parse_ua(user_agent) if user_agent else None
    browser = f"{ua.browser.family} {ua.browser.version_string}" if ua else ""
    os_name = f"{ua.os.family} {ua.os.version_string}" if ua else ""

    # 注意: _get_country() は外部GeoIP APIへのブロッキングHTTPリクエストを伴う。
    # log_page_view() 自体は非同期ミドルウェア(AnalyticsMiddleware)から同期的に
    # 呼び出されるため、ここで待ってしまうとイベントループを塞ぎ、全リクエストの
    # レスポンスが遅延する（アクセス集中時ほど悪化し、GeoIP側のレート制限にも
    # 到達しやすくなる悪循環を生む）。そのため国解決とinsertを丸ごとバックグラウンドの
    # 専用executor(_analytics_executor)に委譲し、リクエスト処理をブロックしないように
    # しつつ、同時実行数の上限を管理する（無制限スレッド生成を防ぐ）。
    def _resolve_and_insert():
        # この関数はexecutorのワーカースレッド上で実行される。ここで例外を
        # 外に漏らすと threading.excepthook 経由でstderrにしか出ず、
        # logging に残らないため、関数全体を必ずtry/exceptで囲む。
        # 計測処理の失敗がリクエスト処理に影響することは絶対にない
        # （呼び出し元は既にレスポンスを返した後、fire-and-forgetで実行される）。
        try:
            country = _get_country(ip)
            row = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "path": path,
                "ip": ip,
                "user_agent": user_agent,
                "browser": browser,
                "os": os_name,
                "language": language,
                "referer": referer,
                "country": country,
            }
            sb.insert("page_views", row)
        except Exception as exc:
            logger.warning("log_page_view background task failed for path=%s: %r", path, exc)

    _submit_analytics_task(_resolve_and_insert)

    # アクティブセッション更新
    session_id = f"{ip}:{user_agent[:50] if user_agent else ''}"
    with _sessions_lock:
        _active_sessions[session_id] = time.time()


def log_search_query(query: str, max_results: int, duration_filter: str,
                     published_after: str, category_id: str, language: str, region: str, ip: str):
    """検索クエリを記録（バックグラウンドexecutorでSupabaseへ送信）"""
    row = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "query": query,
        "max_results": max_results,
        "duration_filter": duration_filter,
        "published_after": published_after,
        "category_id": category_id,
        "language": language,
        "region": region,
        "ip": ip,
    }

    def _insert():
        try:
            sb.insert("search_queries", row)
        except Exception as exc:
            logger.warning("log_search_query background task failed: %r", exc)

    _submit_analytics_task(_insert)


def get_active_sessions() -> int:
    """アクティブセッション数を返す"""
    now = time.time()
    with _sessions_lock:
        # タイムアウトしたセッションを削除
        expired = [k for k, v in _active_sessions.items() if now - v > SESSION_TIMEOUT]
        for k in expired:
            del _active_sessions[k]
        return len(_active_sessions)


# ip-api.com 無料プランのレート制限（45リクエスト/分）に対する自前スロットリング。
# 上限に達している間はHTTPリクエスト自体を送らず、即座に "Unknown" とすることで
# タイムアウト待ちによる遅延と、無駄な429連発を避ける。
#
# --- ip-api.com 依存に関する既知のリスク（将来GeoIPを差し替える際の判断材料） ---
# 1. 無料プランは45req/分という厳しいレート制限があり、アクセスが集中すると
#    容易に枯渇する（現にUnknown比率が高騰した一因）。
# 2. 無料プランはHTTPSに非対応（http://ip-api.comのみ）。IPアドレスという
#    個人情報になり得る値を平文でサードパーティに送信している点は要考慮。
# 3. 利用規約上、無料プランは非商用利用が前提。VidScopeが商用サービスと
#    見なされる場合はライセンス違反のリスクがあるため、商用化する場合は
#    有料プランへの切り替えまたは別サービス（ipinfo.io, MaxMind GeoLite2の
#    自前ホスティング等）への移行を検討する必要がある。
# 今回のタスクではGeoIPサービスの差し替えは行わない（判定ロジック変更は対象外）。
_GEO_RATE_LIMIT = 45
_GEO_RATE_WINDOW_SEC = 60.0
_geo_request_times: list[float] = []
_geo_rate_lock = threading.Lock()

_geo_logger = None


def _get_geo_logger():
    global _geo_logger
    if _geo_logger is None:
        import logging
        _geo_logger = logging.getLogger("vidscope.geoip")
    return _geo_logger


def _geo_rate_limit_ok() -> bool:
    """直近60秒以内のGeoIP問い合わせ回数が上限未満ならTrueを返し、カウントに加算する"""
    now = time.time()
    with _geo_rate_lock:
        cutoff = now - _GEO_RATE_WINDOW_SEC
        while _geo_request_times and _geo_request_times[0] < cutoff:
            _geo_request_times.pop(0)
        if len(_geo_request_times) >= _GEO_RATE_LIMIT:
            return False
        _geo_request_times.append(now)
        return True


def _get_country(ip: str) -> str:
    """IPアドレスから国を推定（キャッシュ付き）

    注意: 外部GeoIPサービス(ip-api.com)は無料プランで45req/分の制限があり、
    アクセスが集中すると429（レート制限）が返る。以前の実装はこれを含む全ての
    非200レスポンス・例外を無条件に "Unknown" へフォールバックし、かつログを
    一切出していなかったため、失敗の実態が見えず調査もできなかった。
    ここでは (1) 自前レートリミッタで無駄なリクエストを事前に抑制し、
    (2) 429時は一度だけ短い待機でリトライし、(3) 失敗時は理由をログに残す。
    """
    if not ip or ip in ("127.0.0.1", "localhost", "::1"):
        return "Local"

    with _geo_cache_lock:
        if ip in _geo_cache:
            return _geo_cache[ip]

    logger = _get_geo_logger()
    country = "Unknown"

    if not _geo_rate_limit_ok():
        logger.warning("GeoIP lookup skipped for %s: local rate limit (45/min) reached", ip)
        # レート制限中はキャッシュに書き込まない（後続の別リクエストで正常解決できる余地を残す）
        return country

    try:
        import requests
        resp = requests.get(
            f"http://ip-api.com/json/{ip}?fields=status,message,country",
            timeout=5,
        )
        if resp.status_code == 429:
            # ip-api.com のレート制限。1回だけ短く待って再試行する。
            logger.warning("GeoIP lookup rate-limited (429) for %s, retrying once", ip)
            time.sleep(1.5)
            resp = requests.get(
                f"http://ip-api.com/json/{ip}?fields=status,message,country",
                timeout=5,
            )

        if resp.status_code == 200:
            data = resp.json()
            if data.get("status") == "success":
                country = data.get("country") or "Unknown"
            else:
                logger.warning(
                    "GeoIP lookup failed for %s: status=%s message=%s",
                    ip, data.get("status"), data.get("message"),
                )
        else:
            logger.warning("GeoIP lookup HTTP error for %s: status_code=%s", ip, resp.status_code)
    except Exception as exc:
        logger.warning("GeoIP lookup exception for %s: %r", ip, exc)

    with _geo_cache_lock:
        if len(_geo_cache) > 10000:
            _geo_cache.clear()
        _geo_cache[ip] = country

    return country


# --- ダッシュボード用クエリ ---

def get_summary() -> dict:
    """今日の概要データ"""
    result = sb.rpc("get_analytics_summary") or {}
    return {
        "pv_today": result.get("pv_today", 0),
        "uv_today": result.get("uv_today", 0),
        "searches_today": result.get("searches_today", 0),
        "active_sessions": get_active_sessions(),
        "pv_total": result.get("pv_total", 0),
        "pv_week": result.get("pv_week", 0),
        "pv_month": result.get("pv_month", 0),
    }


def get_summary_with_raw() -> dict:
    """ボット除外前(raw)/除外後(filtered)のPV・UUを並べて返す。

    既存の get_summary() はSupabase側で除外済みの値のみ返すため、
    「フィルタがどれだけ効いているか」を管理画面で可視化するために追加。
    """
    result = sb.rpc("get_analytics_summary_with_raw") or {}
    pv_today_raw = result.get("pv_today_raw", 0)
    pv_today_filtered = result.get("pv_today_filtered", 0)
    uv_today_raw = result.get("uv_today_raw", 0)
    uv_today_filtered = result.get("uv_today_filtered", 0)
    pv_total_raw = result.get("pv_total_raw", 0)
    pv_total_filtered = result.get("pv_total_filtered", 0)
    return {
        "pv_today_raw": pv_today_raw,
        "pv_today_filtered": pv_today_filtered,
        "pv_today_bot_ratio": _bot_ratio(pv_today_raw, pv_today_filtered),
        "uv_today_raw": uv_today_raw,
        "uv_today_filtered": uv_today_filtered,
        "uv_today_bot_ratio": _bot_ratio(uv_today_raw, uv_today_filtered),
        "pv_total_raw": pv_total_raw,
        "pv_total_filtered": pv_total_filtered,
        "pv_total_bot_ratio": _bot_ratio(pv_total_raw, pv_total_filtered),
    }


def _bot_ratio(raw: int, filtered: int) -> float:
    """除外率(%)を計算する。raw=0の場合は0を返す"""
    if not raw:
        return 0.0
    return round((raw - filtered) / raw * 100, 1)


def get_pageviews(days: int = 7, offset_days: int = 0) -> list[dict]:
    """日別PV推移。offset_daysを指定すると、直近days日間より前の期間を取得できる
    （例: days=7, offset_days=7 → 8〜14日前の週＝前週）。"""
    result = sb.rpc("get_daily_pageviews", {"days_back": days, "offset_days": offset_days})
    return result or []


def get_top_pages(limit: int = 10) -> list[dict]:
    """人気ページTOP"""
    result = sb.rpc("get_top_pages", {"limit_count": limit})
    return result or []


def get_top_searches(limit: int = 10) -> list[dict]:
    """検索キーワードTOP"""
    result = sb.rpc("get_top_searches", {"limit_count": limit})
    return result or []


def get_top_countries(limit: int = 10) -> list[dict]:
    """アクセス元国TOP"""
    result = sb.rpc("get_top_countries", {"limit_count": limit})
    return result or []


def get_top_countries_with_raw(limit: int = 10, days: int | None = None) -> list[dict]:
    """アクセス元国TOP（除外前raw_count/除外後filtered_countを併記）。

    days: 指定すると直近N日間のみ集計する（Noneなら全期間、従来通り）。
    2026-07-21のコミット8889018（プロキシ内部IPロギング修正）以降のデータに
    絞ってUnknown比率を確認したい場合に使う
    （docs/pv-diagnosis-2026-07.md の訂正メモを参照）。
    """
    params: dict = {"limit_count": limit}
    if days is not None:
        params["days_back"] = days
    result = sb.rpc("get_top_countries_with_raw", params)
    rows = result or []
    for row in rows:
        row["bot_ratio"] = _bot_ratio(row.get("raw_count", 0), row.get("filtered_count", 0))
    return rows


def get_unknown_country_ratio(days: int | None = None) -> dict:
    """country='Unknown'(またはnull/空)の比率を確認する。

    days: 指定すると直近N日間のみ、Noneなら全期間。
    2026-07-21以降のデータに絞ることで、8889018（プロキシ内部IPロギング修正）
    適用後もUnknownが多いかどうかを切り分けられる。
    """
    params: dict = {}
    if days is not None:
        params["days_back"] = days
    result = sb.rpc("get_unknown_country_ratio", params)
    return result or {"days_back": days, "total": 0, "unknown_or_null": 0, "unknown_ratio_pct": 0}


def get_top_referrers(limit: int = 10, days: int | None = None) -> list[dict]:
    """流入元（リファラー）ドメイン別集計TOP。daysを指定すると直近N日間、Noneなら全期間。"""
    params: dict = {"limit_count": limit}
    if days is not None:
        params["days_back"] = days
    result = sb.rpc("get_top_referrers", params)
    return result or []


def get_browsers() -> dict:
    """ブラウザ・OS分布"""
    result = sb.rpc("get_browser_os_stats")
    if not result:
        return {"browsers": [], "os": []}
    return result


def get_recent(limit: int = 50) -> list[dict]:
    """直近のアクセスログ"""
    rows = sb.select(
        "page_views",
        select="timestamp,path,ip,browser,os,country,referer",
        order="id.desc",
        limit=limit,
    )
    return rows


def cleanup_old_data(days: int = 90):
    """古いデータを削除"""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    sb.rpc("cleanup_old_analytics", {"cutoff": cutoff})
