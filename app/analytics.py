"""アクセス監視モジュール - SQLiteベースのアナリティクス"""

import sqlite3
import threading
import time
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from collections import Counter
from user_agents import parse as parse_ua

DB_PATH = Path("data/analytics.db")
_local = threading.local()

# アクティブセッション追跡
_active_sessions: dict[str, float] = {}  # {session_id: last_seen_timestamp}
_sessions_lock = threading.Lock()
SESSION_TIMEOUT = 300  # 5分

# IP→国キャッシュ
_geo_cache: dict[str, str] = {}
_geo_cache_lock = threading.Lock()


def _get_db() -> sqlite3.Connection:
    """スレッドローカルなDB接続を返す"""
    if not hasattr(_local, "conn") or _local.conn is None:
        os.makedirs("data", exist_ok=True)
        _local.conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        _local.conn.row_factory = sqlite3.Row
        _local.conn.execute("PRAGMA journal_mode=WAL")
    return _local.conn


def init_db():
    """テーブル作成"""
    conn = _get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS page_views (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            path TEXT NOT NULL,
            ip TEXT,
            user_agent TEXT,
            browser TEXT,
            os TEXT,
            language TEXT,
            referer TEXT,
            country TEXT
        );
        CREATE TABLE IF NOT EXISTS search_queries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            query TEXT,
            max_results INTEGER,
            duration_filter TEXT,
            published_after TEXT,
            category_id TEXT,
            language TEXT,
            region TEXT,
            ip TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_pv_timestamp ON page_views(timestamp);
        CREATE INDEX IF NOT EXISTS idx_pv_path ON page_views(path);
        CREATE INDEX IF NOT EXISTS idx_sq_timestamp ON search_queries(timestamp);
    """)
    conn.commit()


def log_page_view(path: str, ip: str, user_agent: str, language: str, referer: str):
    """ページビューを記録"""
    # 静的ファイル・APIリクエスト・管理ページは除外
    if path.startswith("/static/") or path.startswith("/api/") or path.startswith("/admin/"):
        return
    if path in ("/robots.txt", "/sitemap.xml", "/favicon.ico"):
        return

    ua = parse_ua(user_agent) if user_agent else None
    browser = f"{ua.browser.family} {ua.browser.version_string}" if ua else ""
    os_name = f"{ua.os.family} {ua.os.version_string}" if ua else ""
    country = _get_country(ip)

    conn = _get_db()
    conn.execute(
        "INSERT INTO page_views (timestamp, path, ip, user_agent, browser, os, language, referer, country) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (datetime.now(timezone.utc).isoformat(), path, ip, user_agent, browser, os_name, language, referer, country),
    )
    conn.commit()

    # アクティブセッション更新
    session_id = f"{ip}:{user_agent[:50] if user_agent else ''}"
    with _sessions_lock:
        _active_sessions[session_id] = time.time()


def log_search_query(query: str, max_results: int, duration_filter: str,
                     published_after: str, category_id: str, language: str, region: str, ip: str):
    """検索クエリを記録"""
    conn = _get_db()
    conn.execute(
        "INSERT INTO search_queries (timestamp, query, max_results, duration_filter, published_after, category_id, language, region, ip) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (datetime.now(timezone.utc).isoformat(), query, max_results, duration_filter, published_after, category_id, language, region, ip),
    )
    conn.commit()


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
    conn = _get_db()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    pv_today = conn.execute(
        "SELECT COUNT(*) FROM page_views WHERE timestamp LIKE ?", (f"{today}%",)
    ).fetchone()[0]

    uv_today = conn.execute(
        "SELECT COUNT(DISTINCT ip) FROM page_views WHERE timestamp LIKE ?", (f"{today}%",)
    ).fetchone()[0]

    searches_today = conn.execute(
        "SELECT COUNT(*) FROM search_queries WHERE timestamp LIKE ?", (f"{today}%",)
    ).fetchone()[0]

    pv_total = conn.execute("SELECT COUNT(*) FROM page_views").fetchone()[0]

    return {
        "pv_today": pv_today,
        "uv_today": uv_today,
        "searches_today": searches_today,
        "active_sessions": get_active_sessions(),
        "pv_total": pv_total,
    }


def get_pageviews(days: int = 7) -> list[dict]:
    """日別PV推移"""
    conn = _get_db()
    since = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    rows = conn.execute(
        "SELECT DATE(timestamp) as date, COUNT(*) as count FROM page_views "
        "WHERE timestamp >= ? GROUP BY DATE(timestamp) ORDER BY date",
        (since,),
    ).fetchall()
    return [{"date": r["date"], "count": r["count"]} for r in rows]


def get_top_pages(limit: int = 10) -> list[dict]:
    """人気ページTOP"""
    conn = _get_db()
    rows = conn.execute(
        "SELECT path, COUNT(*) as count FROM page_views GROUP BY path ORDER BY count DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return [{"path": r["path"], "count": r["count"]} for r in rows]


def get_top_searches(limit: int = 10) -> list[dict]:
    """検索キーワードTOP"""
    conn = _get_db()
    rows = conn.execute(
        "SELECT query, COUNT(*) as count FROM search_queries WHERE query != '' GROUP BY query ORDER BY count DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return [{"query": r["query"], "count": r["count"]} for r in rows]


def get_top_countries(limit: int = 10) -> list[dict]:
    """アクセス元国TOP"""
    conn = _get_db()
    rows = conn.execute(
        "SELECT country, COUNT(*) as count FROM page_views WHERE country != '' GROUP BY country ORDER BY count DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return [{"country": r["country"], "count": r["count"]} for r in rows]


def get_browsers() -> dict:
    """ブラウザ・OS分布"""
    conn = _get_db()
    browser_rows = conn.execute(
        "SELECT browser, COUNT(*) as count FROM page_views WHERE browser != '' GROUP BY browser ORDER BY count DESC LIMIT 10"
    ).fetchall()
    os_rows = conn.execute(
        "SELECT os, COUNT(*) as count FROM page_views WHERE os != '' GROUP BY os ORDER BY count DESC LIMIT 10"
    ).fetchall()
    return {
        "browsers": [{"name": r["browser"], "count": r["count"]} for r in browser_rows],
        "os": [{"name": r["os"], "count": r["count"]} for r in os_rows],
    }


def get_recent(limit: int = 50) -> list[dict]:
    """直近のアクセスログ"""
    conn = _get_db()
    rows = conn.execute(
        "SELECT timestamp, path, ip, browser, os, country, referer FROM page_views ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return [dict(r) for r in rows]


def cleanup_old_data(days: int = 90):
    """古いデータを削除"""
    conn = _get_db()
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    conn.execute("DELETE FROM page_views WHERE timestamp < ?", (cutoff,))
    conn.execute("DELETE FROM search_queries WHERE timestamp < ?", (cutoff,))
    conn.commit()
