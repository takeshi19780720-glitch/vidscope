"""アクセス監視モジュール - Supabase(PostgreSQL)ベースのアナリティクス"""

import threading
import time
from datetime import datetime, timedelta, timezone
from user_agents import parse as parse_ua

from app import supabase_client as sb

# アクティブセッション追跡
_active_sessions: dict[str, float] = {}  # {session_id: last_seen_timestamp}
_sessions_lock = threading.Lock()
SESSION_TIMEOUT = 300  # 5分

# IP→国キャッシュ
_geo_cache: dict[str, str] = {}
_geo_cache_lock = threading.Lock()


def init_db():
    """テーブルはSupabase側でSQL Editorにより作成済み。起動時チェックのみ行う。"""
    if not sb.is_configured():
        import logging
        logging.getLogger("vidscope").error(
            "SUPABASE_URL / SUPABASE_KEY が設定されていません。アナリティクス機能は無効化されます。"
        )


def log_page_view(path: str, ip: str, user_agent: str, language: str, referer: str):
    """ページビューを記録（バックグラウンドスレッドでSupabaseへ送信）"""
    # 静的ファイル・APIリクエスト・管理ページは除外
    if path.startswith("/static/") or path.startswith("/api/") or path.startswith("/admin/"):
        return
    if path in ("/robots.txt", "/sitemap.xml", "/favicon.ico"):
        return

    ua = parse_ua(user_agent) if user_agent else None
    browser = f"{ua.browser.family} {ua.browser.version_string}" if ua else ""
    os_name = f"{ua.os.family} {ua.os.version_string}" if ua else ""
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
    threading.Thread(target=sb.insert, args=("page_views", row), daemon=True).start()

    # アクティブセッション更新
    session_id = f"{ip}:{user_agent[:50] if user_agent else ''}"
    with _sessions_lock:
        _active_sessions[session_id] = time.time()


def log_search_query(query: str, max_results: int, duration_filter: str,
                     published_after: str, category_id: str, language: str, region: str, ip: str):
    """検索クエリを記録（バックグラウンドスレッドでSupabaseへ送信）"""
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
    threading.Thread(target=sb.insert, args=("search_queries", row), daemon=True).start()


def get_active_sessions() -> int:
    """アクティブセッション数を返す"""
    now = time.time()
    with _sessions_lock:
        # タイムアウトしたセッションを削除
        expired = [k for k, v in _active_sessions.items() if now - v > SESSION_TIMEOUT]
        for k in expired:
            del _active_sessions[k]
        return len(_active_sessions)


def _get_country(ip: str) -> str:
    """IPアドレスから国を推定（キャッシュ付き）"""
    if not ip or ip in ("127.0.0.1", "localhost", "::1"):
        return "Local"

    with _geo_cache_lock:
        if ip in _geo_cache:
            return _geo_cache[ip]

    try:
        import requests
        resp = requests.get(f"http://ip-api.com/json/{ip}?fields=country", timeout=2)
        if resp.status_code == 200:
            country = resp.json().get("country", "Unknown")
        else:
            country = "Unknown"
    except Exception:
        country = "Unknown"

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
