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
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.config import settings
from app.models import SearchResponse, VideoItem, ChannelInfo, ChannelVideoItem
from app.youtube_client import YouTubeClient, YouTubeClientError, get_quota_status

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


@app.post("/api/contact")
async def submit_contact(request: Request):
    import json, os
    from datetime import datetime
    data = await request.json()
    entry = {
        "timestamp": datetime.now().isoformat(),
        "name": data.get("name", ""),
        "email": data.get("email", ""),
        "category": data.get("category", ""),
        "message": data.get("message", ""),
    }
    contact_file = "data/contact_submissions.json"
    os.makedirs("data", exist_ok=True)
    submissions = []
    if os.path.exists(contact_file):
        with open(contact_file, "r") as f:
            submissions = json.load(f)
    submissions.append(entry)
    with open(contact_file, "w") as f:
        json.dump(submissions, f, ensure_ascii=False, indent=2)
    return {"status": "ok"}


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


@app.get("/{full_path:path}", include_in_schema=False)
def catch_all(full_path: str):
    return FileResponse("static/404.html", status_code=404)