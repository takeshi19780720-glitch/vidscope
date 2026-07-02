"""Supabase (PostgREST) への薄いHTTPラッパー。requestsで直接REST APIを叩く。"""

import logging
import os
from urllib.parse import quote

import requests

logger = logging.getLogger("vidscope")

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

_TIMEOUT = 10


def is_configured() -> bool:
    return bool(SUPABASE_URL and SUPABASE_KEY)


def _headers(extra: dict | None = None) -> dict:
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }
    if extra:
        headers.update(extra)
    return headers


def _rest_url(path: str) -> str:
    return f"{SUPABASE_URL}/rest/v1/{path}"


def select(table: str, select: str = "*", filters: dict | None = None,
           order: str | None = None, limit: int | None = None) -> list[dict]:
    """SELECT。filtersはPostgREST演算子込みの値（例: {"query": "not.eq."}）をそのまま渡す。"""
    if not is_configured():
        return []
    params = {"select": select}
    if filters:
        params.update(filters)
    if order:
        params["order"] = order
    if limit is not None:
        params["limit"] = str(limit)
    try:
        resp = requests.get(_rest_url(table), headers=_headers(), params=params, timeout=_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.error("Supabase select failed (%s): %s", table, e)
        return []


def insert(table: str, data: dict) -> dict | None:
    """INSERT。成功した行を返す。"""
    if not is_configured():
        logger.error("Supabase not configured, skip insert to %s", table)
        return None
    try:
        resp = requests.post(
            _rest_url(table),
            headers=_headers({"Prefer": "return=representation"}),
            json=data,
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        rows = resp.json()
        return rows[0] if rows else None
    except Exception as e:
        logger.error("Supabase insert failed (%s): %s", table, e)
        return None


def delete(table: str, filters: dict) -> bool:
    """DELETE。filtersはPostgREST演算子込み（例: {"timestamp": "lt.2024-01-01"}）"""
    if not is_configured():
        return False
    try:
        resp = requests.delete(_rest_url(table), headers=_headers(), params=filters, timeout=_TIMEOUT)
        resp.raise_for_status()
        return True
    except Exception as e:
        logger.error("Supabase delete failed (%s): %s", table, e)
        return False


def rpc(fn_name: str, params: dict | None = None):
    """Postgres関数をRPC経由で呼び出す。"""
    if not is_configured():
        return None
    try:
        resp = requests.post(
            f"{SUPABASE_URL}/rest/v1/rpc/{quote(fn_name)}",
            headers=_headers(),
            json=params or {},
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.error("Supabase rpc failed (%s): %s", fn_name, e)
        return None
