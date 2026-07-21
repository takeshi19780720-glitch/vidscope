import hashlib
import json
import os
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Body, Header
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.config import settings
from app.models import SearchResponse, VideoItem, ChannelInfo, ChannelVideoItem
from app.youtube_client import YouTubeClient, YouTubeClientError, get_quota_status
from app import analytics
from app import supabase_client

ENV_PATH = Path(__file__).resolve().parent.parent / ".env"


# --- キャッシュ ---
_cache: dict = {}  # {cache_key: {"data": [...], "expires": timestamp}}
CACHE_TTL = 30 * 60  # 30分


def _cache_key(q, max_results, duration_filter, published_after, category_id, language, region) -> str:
    raw = json.dumps([q, max_results, duration_filter, published_after, category_id, language, region], sort_keys=True)
    return hashlib.md5(raw.encode()).hexdigest()


def _cache_get(key: str):
    entry = _cache.get(key)
    if entry and entry["expires"] > time.time():
        return entry["data"]
    if entry:
        del _cache[key]
    return None


def _cache_set(key: str, data):
    # 古いキャッシュを削除（最大100エントリ）
    if len(_cache) > 100:
        now = time.time()
        expired = [k for k, v in _cache.items() if v["expires"] <= now]
        for k in expired:
            del _cache[k]
    _cache[key] = {"data": data, "expires": time.time() + CACHE_TTL}


app = FastAPI(title="YouTube Data API v3 Search App")

# --- アナリティクス初期化 ---
analytics.init_db()


def _get_client_ip(request: Request) -> str:
    """リバースプロキシ(Render)経由の実クライアントIPを取得する。

    前提: Renderのロードバランサ/プロキシは一般的なリバースプロキシと同様に
    `X-Forwarded-For` ヘッダーへ「元クライアントIP, プロキシ1, プロキシ2, ...」の順で
    カンマ区切りリストを設定して転送すると想定し、先頭の値を採用する。
    `X-Forwarded-For` が無い場合は `X-Real-IP` を次点として参照し、
    どちらも無ければ従来通り `request.client.host`（プロキシのIP）にフォールバックする。

    注意: Renderが実際にどのヘッダーでクライアントIPを渡しているかはドキュメント上
    明確でないため、本番デプロイ後に /api/admin/analytics/recent の ip / country カラムを
    確認し、想定通りに実IP・国が取得できているか検証すること。
    """
    xff = request.headers.get("x-forwarded-for", "")
    if xff:
        first_ip = xff.split(",")[0].strip()
        if first_ip:
            return first_ip
    x_real_ip = request.headers.get("x-real-ip", "")
    if x_real_ip.strip():
        return x_real_ip.strip()
    return request.client.host if request.client else ""


# --- アクセス監視ミドルウェア ---
class AnalyticsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        try:
            ip = _get_client_ip(request)
            ua = request.headers.get("user-agent", "")
            lang = request.headers.get("accept-language", "").split(",")[0] if request.headers.get("accept-language") else ""
            referer = request.headers.get("referer", "")
            analytics.log_page_view(request.url.path, ip, ua, lang, referer)
        except Exception:
            pass
        return response

# --- レート制限 ---
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response


app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(AnalyticsMiddleware)
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
def root() -> FileResponse:
    return FileResponse("static/landing.html")


@app.get("/app")
def app_page() -> FileResponse:
    return FileResponse("static/index.html")


@app.get("/privacy")
def privacy_page() -> FileResponse:
    return FileResponse("static/privacy.html")


@app.get("/terms")
def terms_page() -> FileResponse:
    return FileResponse("static/terms.html")


@app.get("/contact")
def contact_page() -> FileResponse:
    return FileResponse("static/contact.html")


@app.get("/blog/vidscope-vs-tubebuddy-vidiq-socialblade")
def blog_vidscope_vs_competitors_page() -> FileResponse:
    return FileResponse("static/blog/vidscope-vs-tubebuddy-vidiq-socialblade.html")


@app.post("/api/contact")
async def submit_contact(request: Request):
    from datetime import datetime
    data = await request.json()
    entry = {
        "timestamp": datetime.now().isoformat(),
        "name": data.get("name", ""),
        "email": data.get("email", ""),
        "category": data.get("category", ""),
        "message": data.get("message", ""),
    }

    # Supabaseへ保存（バックグラウンド）
    import threading
    threading.Thread(
        target=supabase_client.insert,
        args=("contacts", {
            "name": entry["name"],
            "email": entry["email"],
            "category": entry["category"],
            "message": entry["message"],
        }),
        daemon=True,
    ).start()

    # メール通知（バックグラウンド）
    threading.Thread(target=_send_contact_email, args=(entry,), daemon=True).start()

    return {"status": "ok"}


def _send_contact_email(entry: dict):
    """お問い合わせ内容をResend API経由で通知"""
    import requests as req
    import logging

    logger = logging.getLogger("vidscope")

    resend_key = os.getenv("RESEND_API_KEY", "")
    notify_to = os.getenv("NOTIFY_EMAIL", "")

    if not resend_key or not notify_to:
        logger.error("Resend credentials not set: RESEND_API_KEY=%s, NOTIFY_EMAIL=%s", bool(resend_key), bool(notify_to))
        return

    body = f"""VidScopeにお問い合わせがありました。

━━━━━━━━━━━━━━━━━━━━━━━━━━
■ 日時: {entry.get('timestamp', '')}
■ お名前: {entry.get('name', '')}
■ メール: {entry.get('email', '')}
■ カテゴリ: {entry.get('category', '')}
━━━━━━━━━━━━━━━━━━━━━━━━━━

{entry.get('message', '')}

━━━━━━━━━━━━━━━━━━━━━━━━━━
このメールはVidScope (https://vidscope.app) から自動送信されています。
"""

    try:
        resp = req.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {resend_key}"},
            json={
                # send.vidscope.app はResendでドメイン認証済みの送信元
                "from": "VidScope <reply@send.vidscope.app>",
                "to": [notify_to],
                "reply_to": entry.get('email'),
                "subject": f"【VidScope】お問い合わせ: {entry.get('category', '一般')}",
                "text": body,
            },
            timeout=10,
        )
        if resp.status_code == 200:
            logger.info("Contact email sent successfully to %s", notify_to)
        else:
            logger.error("Failed to send contact email: %s %s", resp.status_code, resp.text)
    except Exception as e:
        logger.error("Failed to send contact email: %s", str(e))


@app.get("/robots.txt", include_in_schema=False)
def robots_txt():
    return FileResponse("static/robots.txt", media_type="text/plain")


@app.get("/sitemap.xml", include_in_schema=False)
def sitemap_xml():
    return FileResponse("static/sitemap.xml", media_type="application/xml")


# --- APIキー管理 ---

def _require_admin(x_admin_password: str = Header(None)):
    """管理者パスワードによる認証チェック"""
    if not settings.admin_password:
        raise HTTPException(status_code=500, detail="ADMIN_PASSWORD is not configured.")
    if x_admin_password != settings.admin_password:
        raise HTTPException(status_code=401, detail="認証に失敗しました。管理者パスワードが正しくありません。")


def _save_keys_to_env(keys: list[str]):
    """APIキーを.envファイルに保存し、settingsをリロード"""
    lines = []
    for i, key in enumerate(keys):
        suffix = "" if i == 0 else f"_{i + 1}"
        lines.append(f"YOUTUBE_API_KEY{suffix}={key}")
    ENV_PATH.write_text("\n".join(lines) + "\n")
    # settingsをリロード
    settings.youtube_api_keys = keys


@app.get("/api/quota")
def get_quota():
    """現在のAPIクォータ使用状況を返す"""
    return get_quota_status()


@app.get("/api/keys")
def list_keys():
    """APIキー一覧（マスキング表示）"""
    masked = []
    for i, key in enumerate(settings.youtube_api_keys):
        masked.append({
            "index": i,
            "masked": key[:8] + "..." + key[-4:] if len(key) > 12 else "****",
        })
    return {"keys": masked, "count": len(masked)}


@app.post("/api/keys")
def add_key(body: dict = Body(...), x_admin_password: str = Header(None)):
    """APIキーを追加（認証必須）"""
    _require_admin(x_admin_password)
    new_key = body.get("key", "").strip()
    if not new_key:
        raise HTTPException(status_code=400, detail="APIキーを入力してください")
    if not new_key.startswith("AIza"):
        raise HTTPException(status_code=400, detail="無効なAPIキー形式です")
    if new_key in settings.youtube_api_keys:
        raise HTTPException(status_code=400, detail="このAPIキーは既に登録されています")
    keys = settings.youtube_api_keys + [new_key]
    _save_keys_to_env(keys)
    return {"message": "APIキーを追加しました", "count": len(keys)}


@app.delete("/api/keys/{index}")
def delete_key(index: int, x_admin_password: str = Header(None)):
    """APIキーを削除（認証必須）"""
    _require_admin(x_admin_password)
    if index < 0 or index >= len(settings.youtube_api_keys):
        raise HTTPException(status_code=404, detail="無効なインデックスです")
    if len(settings.youtube_api_keys) <= 1:
        raise HTTPException(status_code=400, detail="最低1つのAPIキーが必要です")
    keys = settings.youtube_api_keys.copy()
    removed = keys.pop(index)
    _save_keys_to_env(keys)
    return {"message": "APIキーを削除しました", "count": len(keys)}


@app.get("/api/search", response_model=SearchResponse)
@limiter.limit("30/minute")
def search(
    request: Request,
    q: str = Query("", description="Search keyword"),
    max_results: int = Query(10, ge=1, le=200),
    duration_filter: str = Query("all", pattern="^(all|short|normal)$"),
    published_after: str = Query("all", pattern="^(all|24h|1w|2w|1m|2m|3m|6m|1y)$"),
    category_id: str = Query("all"),
    language: str = Query("all"),
    region: str = Query("all"),
) -> SearchResponse:
    if not settings.youtube_api_keys:
        raise HTTPException(
            status_code=500,
            detail="YOUTUBE_API_KEY is not set. Please configure your .env file.",
        )

    client = YouTubeClient(settings.youtube_api_keys)
    published_after_iso = _resolve_published_after(published_after)
    resolved_category = None if category_id == "all" else category_id
    resolved_language = None if language == "all" else language
    resolved_region = None if region == "all" else region

    # 検索クエリを記録
    try:
        ip = _get_client_ip(request)
        analytics.log_search_query(q, max_results, duration_filter, published_after, category_id, language, region, ip)
    except Exception:
        pass

    # キーワードが空の場合はそのまま空文字を渡す
    search_q = q

    # キャッシュチェック
    ck = _cache_key(q, max_results, duration_filter, published_after, category_id, language, region)
    cached = _cache_get(ck)
    if cached:
        return SearchResponse(q=q, max_results=max_results, total=len(cached), items=cached)

    # 言語フィルターが指定されている場合、多めに取得してサーバー側でフィルタリング
    fetch_count = max_results
    if resolved_language:
        # キーワード空の場合はAPIのrelevanceLanguageがほぼ機能しないので大量取得
        multiplier = 10 if not search_q.strip() or search_q.strip() == "*" else 5
        fetch_count = min(200, max_results * multiplier)

    try:
        video_ids = client.search_videos(
            q=search_q,
            max_results=fetch_count,
            duration_filter=duration_filter,
            published_after=published_after_iso,
            category_id=resolved_category,
            language=resolved_language,
            region=resolved_region,
        )
        details = client.get_video_details(video_ids)
    except YouTubeClientError as exc:
        raise HTTPException(status_code=502, detail=f"YouTube API request failed: {exc}") from exc

    # サーバー側言語フィルタリング
    if resolved_language:
        details = _filter_by_language(details, resolved_language)

    # 再生回数の降順で明示的にソート（YouTube search APIのviewCount順は概算のため）
    details.sort(key=lambda x: int(x.get('view_count', 0)), reverse=True)

    items = [VideoItem(**item) for item in details[:max_results]]

    # キャッシュに保存
    _cache_set(ck, items)

    return SearchResponse(q=q, max_results=max_results, total=len(items), items=items)


def _filter_by_language(details: list, language: str) -> list:
    """サーバー側で言語フィルタリングを行う。

    判定優先順位:
    1. default_audio_language が設定されている → それで判定
    2. default_language が設定されている → それで判定
    3. どちらも未設定 → タイトル+説明の文字種比率で判定（厳密）
    """
    filtered = []
    for item in details:
        audio_lang = (item.get("default_audio_language") or "").lower()
        def_lang = (item.get("default_language") or "").lower()

        # どちらかが対象言語に一致すればOK
        if audio_lang.startswith(language) or def_lang.startswith(language):
            filtered.append(item)
            continue

        # 明確に他言語が設定されている場合は除外
        if audio_lang or def_lang:
            continue

        # メタデータなし → 文字種比率で判定
        if _matches_language_by_text(item, language):
            filtered.append(item)

    return filtered


def _matches_language_by_text(item: dict, language: str) -> bool:
    """タイトルとチャンネル名の文字種比率で言語を判定する。"""
    text = (item.get("title") or "") + (item.get("channel_title") or "")
    if not text:
        return False

    if language == "ja":
        # 日本語文字（ひらがな、カタカナ、漢字）の割合が20%以上
        ja_chars = len(re.findall(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF\u3000-\u303F]', text))
        # 空白と記号を除いた文字数
        meaningful = len(re.findall(r'[^\s\u0020-\u002F\u003A-\u0040\u005B-\u0060\u007B-\u007E]', text))
        if meaningful == 0:
            return False
        return (ja_chars / meaningful) >= 0.2
    elif language == "ko":
        ko_chars = len(re.findall(r'[\uAC00-\uD7AF]', text))
        meaningful = len(re.findall(r'[^\s]', text))
        return meaningful > 0 and (ko_chars / meaningful) >= 0.2
    elif language == "zh":
        zh_chars = len(re.findall(r'[\u4E00-\u9FFF]', text))
        ja_chars = len(re.findall(r'[\u3040-\u309F\u30A0-\u30FF]', text))
        if ja_chars > 0:
            return False  # ひらがな/カタカナがあれば日本語
        meaningful = len(re.findall(r'[^\s]', text))
        return meaningful > 0 and (zh_chars / meaningful) >= 0.2
    elif language == "en":
        en_chars = len(re.findall(r'[a-zA-Z]', text))
        meaningful = len(re.findall(r'[^\s]', text))
        return meaningful > 0 and (en_chars / meaningful) >= 0.6
    # その他の言語はパス
    return True


def _resolve_published_after(value: str) -> str | None:
    if value == "all":
        return None
    now = datetime.now(timezone.utc)
    delta_map = {
        "24h": timedelta(hours=24),
        "1w": timedelta(weeks=1),
        "2w": timedelta(weeks=2),
        "1m": timedelta(days=30),
        "2m": timedelta(days=60),
        "3m": timedelta(days=90),
        "6m": timedelta(days=180),
        "1y": timedelta(days=365),
    }
    delta = delta_map.get(value)
    if not delta:
        return None
    dt = now - delta
    return dt.isoformat().replace("+00:00", "Z")


# --- チャンネルキャッシュ ---
_channel_cache: dict = {}  # {channel_id: {"data": ..., "expires": timestamp}}


def _channel_cache_get(key: str):
    entry = _channel_cache.get(key)
    if entry and entry["expires"] > time.time():
        return entry["data"]
    if entry:
        del _channel_cache[key]
    return None


def _channel_cache_set(key: str, data):
    if len(_channel_cache) > 200:
        now = time.time()
        expired = [k for k, v in _channel_cache.items() if v["expires"] <= now]
        for k in expired:
            del _channel_cache[k]
    _channel_cache[key] = {"data": data, "expires": time.time() + CACHE_TTL}


@app.get("/api/channel/{channel_id}", response_model=ChannelInfo)
def get_channel(channel_id: str):
    """チャンネル情報を取得する"""
    if not settings.youtube_api_keys:
        raise HTTPException(status_code=500, detail="YOUTUBE_API_KEY is not set.")

    cached = _channel_cache_get(channel_id)
    if cached:
        return cached

    client = YouTubeClient(settings.youtube_api_keys)
    try:
        info = client.get_channel_info(channel_id)
    except YouTubeClientError as exc:
        msg = str(exc)
        if "not found" in msg.lower():
            raise HTTPException(status_code=404, detail="チャンネルが見つかりません") from exc
        raise HTTPException(status_code=502, detail=f"YouTube API request failed: {exc}") from exc

    channel_info = ChannelInfo(**info)
    _channel_cache_set(channel_id, channel_info)
    return channel_info


@app.get("/api/channel/{channel_id}/videos", response_model=list[ChannelVideoItem])
def get_channel_videos(channel_id: str):
    """チャンネルの最新動画5件を取得する"""
    if not settings.youtube_api_keys:
        raise HTTPException(status_code=500, detail="YOUTUBE_API_KEY is not set.")

    videos_cache_key = f"{channel_id}:videos"
    cached_videos = _channel_cache_get(videos_cache_key)
    if cached_videos:
        return cached_videos

    client = YouTubeClient(settings.youtube_api_keys)
    try:
        # チャンネル情報からuploads playlist IDを取得（キャッシュ優先）
        channel_info_cached = _channel_cache_get(channel_id)
        if channel_info_cached:
            uploads_playlist_id = channel_info_cached.uploads_playlist_id
        else:
            info = client.get_channel_info(channel_id)
            channel_info = ChannelInfo(**info)
            _channel_cache_set(channel_id, channel_info)
            uploads_playlist_id = channel_info.uploads_playlist_id

        videos = client.get_channel_videos(uploads_playlist_id, max_results=5)
    except YouTubeClientError as exc:
        msg = str(exc)
        if "not found" in msg.lower():
            raise HTTPException(status_code=404, detail="チャンネルが見つかりません") from exc
        raise HTTPException(status_code=502, detail=f"YouTube API request failed: {exc}") from exc

    video_items = [ChannelVideoItem(**v) for v in videos]
    _channel_cache_set(videos_cache_key, video_items)
    return video_items


# --- アナリティクス ダッシュボード ---

@app.get("/admin/analytics")
def analytics_page() -> FileResponse:
    return FileResponse("static/admin/analytics.html")


@app.get("/api/admin/analytics/summary")
def analytics_summary(x_admin_password: str = Header(None)):
    _require_admin(x_admin_password)
    return analytics.get_summary()


@app.get("/api/admin/analytics/pageviews")
def analytics_pageviews(
    days: int = Query(7, ge=1, le=90),
    offset_days: int = Query(0, ge=0, le=365),
    x_admin_password: str = Header(None),
):
    _require_admin(x_admin_password)
    return analytics.get_pageviews(days, offset_days)


@app.get("/api/admin/analytics/top-pages")
def analytics_top_pages(x_admin_password: str = Header(None)):
    _require_admin(x_admin_password)
    return analytics.get_top_pages()


@app.get("/api/admin/analytics/top-searches")
def analytics_top_searches(x_admin_password: str = Header(None)):
    _require_admin(x_admin_password)
    return analytics.get_top_searches()


@app.get("/api/admin/analytics/top-countries")
def analytics_top_countries(x_admin_password: str = Header(None)):
    _require_admin(x_admin_password)
    return analytics.get_top_countries()


@app.get("/api/admin/analytics/top-referrers")
def analytics_top_referrers(
    days: int | None = Query(None, ge=1, le=365),
    x_admin_password: str = Header(None),
):
    _require_admin(x_admin_password)
    return analytics.get_top_referrers(days=days)


@app.get("/api/admin/analytics/browsers")
def analytics_browsers(x_admin_password: str = Header(None)):
    _require_admin(x_admin_password)
    return analytics.get_browsers()


@app.get("/api/admin/analytics/recent")
def analytics_recent(x_admin_password: str = Header(None)):
    _require_admin(x_admin_password)
    return analytics.get_recent()


@app.get("/api/admin/contacts")
def admin_contacts(x_admin_password: str = Header(None)):
    """お問い合わせ一覧を返す（新しい順）"""
    _require_admin(x_admin_password)
    rows = supabase_client.select(
        "contacts",
        select="id,name,email,category,message,created_at",
        order="created_at.desc",
    )
    return [
        {
            "id": r.get("id"),
            "timestamp": r.get("created_at", ""),
            "name": r.get("name", ""),
            "email": r.get("email", ""),
            "category": r.get("category", ""),
            "message": r.get("message", ""),
        }
        for r in rows
    ]


@app.delete("/api/admin/contacts/{contact_id}")
def delete_contact(contact_id: int, x_admin_password: str = Header(None)):
    """お問い合わせを削除（認証必須）"""
    _require_admin(x_admin_password)
    ok = supabase_client.delete("contacts", {"id": f"eq.{contact_id}"})
    if not ok:
        raise HTTPException(status_code=502, detail="削除に失敗しました")
    return {"status": "ok"}


@app.get("/api/admin/contacts/{contact_id}/replies")
def admin_contact_replies(contact_id: int, x_admin_password: str = Header(None)):
    """指定した問い合わせへの返信履歴を返す（新しい順）"""
    _require_admin(x_admin_password)
    rows = supabase_client.select(
        "contact_replies",
        select="id,subject,body,status,error,created_at",
        filters={"contact_id": f"eq.{contact_id}"},
        order="created_at.desc",
    )
    return rows


class ReplyRequest(BaseModel):
    subject: str
    body: str


def _send_reply_email(to_email: str, subject: str, body: str) -> tuple[bool, str | None]:
    """お問い合わせ者への返信をResend API経由で送信する。(成功可否, エラーメッセージ)を返す"""
    import requests as req
    import logging

    logger = logging.getLogger("vidscope")

    resend_key = os.getenv("RESEND_API_KEY", "")
    if not resend_key:
        logger.error("Resend credentials not set: RESEND_API_KEY is empty")
        return False, "メール送信設定が未構成です"

    try:
        resp = req.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {resend_key}"},
            json={
                # send.vidscope.app はResendでドメイン認証済みの送信元
                "from": "VidScope <reply@send.vidscope.app>",
                "to": [to_email],
                "subject": subject,
                "text": body,
            },
            timeout=10,
        )
        if resp.status_code == 200:
            logger.info("Reply email sent successfully to %s", to_email)
            return True, None
        logger.error("Failed to send reply email: %s %s", resp.status_code, resp.text)
        return False, f"メール送信に失敗しました（ステータス: {resp.status_code}）"
    except Exception as e:
        logger.error("Failed to send reply email: %s", str(e))
        return False, "メール送信中にエラーが発生しました"


@app.post("/api/admin/contacts/{contact_id}/reply")
@limiter.limit("10/minute")
def reply_to_contact(request: Request, contact_id: int, payload: ReplyRequest, x_admin_password: str = Header(None)):
    """お問い合わせへの返信メールを送信し、履歴をSupabaseに記録する（認証必須）"""
    _require_admin(x_admin_password)

    contacts = supabase_client.select("contacts", select="id,email,name", filters={"id": f"eq.{contact_id}"})
    if not contacts:
        raise HTTPException(status_code=404, detail="お問い合わせが見つかりません")
    contact = contacts[0]

    if not payload.subject.strip() or not payload.body.strip():
        raise HTTPException(status_code=400, detail="件名と本文を入力してください")

    reply_row = supabase_client.insert("contact_replies", {
        "contact_id": contact_id,
        "subject": payload.subject,
        "body": payload.body,
        "status": "pending",
    })
    if not reply_row:
        return {"success": False, "error": "返信履歴の保存に失敗しました"}

    reply_id = reply_row["id"]
    ok, err = _send_reply_email(contact["email"], payload.subject, payload.body)

    supabase_client.update(
        "contact_replies",
        {"id": f"eq.{reply_id}"},
        {"status": "sent"} if ok else {"status": "failed", "error": err},
    )

    if not ok:
        return {"success": False, "error": err}
    return {"success": True, "reply_id": reply_id}


@app.get("/{full_path:path}", include_in_schema=False)
def catch_all(full_path: str):
    return FileResponse("static/404.html", status_code=404)