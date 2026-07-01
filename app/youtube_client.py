from datetime import datetime
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

import requests


YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"

# --- クォータカウンター（インメモリ、日付変化でリセット） ---
_quota_used: int = 0
_quota_date: str = ""  # YYYY-MM-DD

QUOTA_LIMIT = 10000

# エンドポイントごとのユニットコスト
_QUOTA_COST: Dict[str, int] = {
    "search": 100,
    "videos": 1,
    "channels": 1,
    "playlistItems": 1,
}


def _get_today() -> str:
    # YouTube APIクォータは太平洋時間(America/Los_Angeles)の0時にリセット
    return datetime.now(ZoneInfo('America/Los_Angeles')).strftime('%Y-%m-%d')


def _add_quota(endpoint: str) -> None:
    """エンドポイント名（URLの末尾パス）に応じてクォータを加算する。"""
    global _quota_used, _quota_date
    today = _get_today()
    if _quota_date != today:
        _quota_used = 0
        _quota_date = today
    cost = _QUOTA_COST.get(endpoint, 1)
    _quota_used += cost


def get_quota_status() -> Dict[str, Any]:
    """現在のクォータ使用状況を返す。"""
    global _quota_used, _quota_date
    today = _get_today()
    if _quota_date != today:
        _quota_used = 0
        _quota_date = today
    return {"used": _quota_used, "limit": QUOTA_LIMIT, "date": today}


class YouTubeClientError(Exception):
    """Raised when YouTube API request fails."""


class YouTubeClient:
    def __init__(self, api_keys) -> None:
        if isinstance(api_keys, str):
            self.api_keys = [api_keys]
        else:
            self.api_keys = list(api_keys)
        self.current_key_index = 0
        self.session = requests.Session()
        self.timeout = 15

    @property
    def api_key(self) -> str:
        return self.api_keys[self.current_key_index]

    def _rotate_key(self) -> bool:
        """次のキーに切り替える。全て試した場合はFalseを返す。"""
        next_index = self.current_key_index + 1
        if next_index < len(self.api_keys):
            self.current_key_index = next_index
            return True
        return False

    def search_videos(
        self,
        q: str,
        max_results: int = 10,
        duration_filter: str = "all",
        published_after: Optional[str] = None,
        category_id: Optional[str] = None,
        language: Optional[str] = None,
        region: Optional[str] = None,
    ) -> List[str]:
        url = f"{YOUTUBE_API_BASE}/search"
        base_params = {
            "part": "snippet",
            "type": "video",
            "key": self.api_key,
        }
        if region:
            base_params["regionCode"] = region
        elif language:
            # 言語に対応する国コードを設定（relevanceLanguageだけでは不十分）
            lang_to_region = {"ja": "JP", "ko": "KR", "zh": "CN", "en": "US", "hi": "IN", "ar": "SA"}
            base_params["regionCode"] = lang_to_region.get(language, "JP")
        else:
            # 地域・言語未指定時: US指定でグローバルに人気な結果を取得
            base_params["regionCode"] = "US"
        if q and q.strip():
            base_params["q"] = q
        else:
            # キーワード空: 言語指定があればその言語の助詞で検索精度を上げる
            lang_queries = {"ja": "の", "ko": "의", "zh": "的", "en": "the", "hi": "का", "ar": "في"}
            if language and language in lang_queries:
                base_params["q"] = lang_queries[language]
            else:
                # 言語未指定: スペースで全体検索（YouTube APIはq必須）
                base_params["q"] = " "
        # 常に再生回数の多い順で並べる
        base_params["order"] = "viewCount"
        if published_after:
            base_params["publishedAfter"] = published_after
        if category_id:
            base_params["videoCategoryId"] = category_id
        if language:
            base_params["relevanceLanguage"] = language

        if duration_filter == "short":
            return self._paginated_search(url, base_params, max_results, "short")

        if duration_filter == "normal":
            # normal(4分以上)は medium(4-20分) + long(20分超) を結合
            combined_ids: List[str] = []
            for dur in ("medium", "long"):
                ids = self._paginated_search(url, base_params, max_results - len(combined_ids), dur)
                for video_id in ids:
                    if video_id not in combined_ids:
                        combined_ids.append(video_id)
                    if len(combined_ids) >= max_results:
                        return combined_ids
            return combined_ids

        return self._paginated_search(url, base_params, max_results, None)

    def _paginated_search(self, url: str, base_params: dict, max_results: int, video_duration: Optional[str]) -> List[str]:
        all_ids: List[str] = []
        next_page_token = None
        while len(all_ids) < max_results:
            per_page = min(50, max_results - len(all_ids))
            params = {**base_params, "maxResults": per_page}
            if video_duration:
                params["videoDuration"] = video_duration
            if next_page_token:
                params["pageToken"] = next_page_token
            data = self._get(url, params)
            ids = self._extract_video_ids(data.get("items", []))
            all_ids.extend(ids)
            next_page_token = data.get("nextPageToken")
            if not next_page_token or not ids:
                break
        return all_ids[:max_results]

    def get_video_details(self, video_ids: List[str]) -> List[Dict[str, Any]]:
        if not video_ids:
            return []
        url = f"{YOUTUBE_API_BASE}/videos"
        # videos.list APIは1回最大50件まで
        items = []
        for i in range(0, len(video_ids), 50):
            batch = video_ids[i:i+50]
            params = {
                "part": "snippet,statistics,contentDetails",
                "id": ",".join(batch),
                "key": self.api_key,
                "maxResults": len(batch),
            }
            data = self._get(url, params)
            items.extend(data.get("items", []))
        # videos.listはID順で返すため、search.listの再生回数順を復元
        id_order = {vid: idx for idx, vid in enumerate(video_ids)}
        items.sort(key=lambda x: id_order.get(x.get("id", ""), len(video_ids)))
        subscriber_counts = self._get_channel_subscriber_counts(
            [item.get("snippet", {}).get("channelId", "") for item in items]
        )
        results: List[Dict[str, Any]] = []
        for item in items:
            snippet = item.get("snippet", {})
            statistics = item.get("statistics", {})
            content_details = item.get("contentDetails", {})
            video_id = item.get("id", "")
            channel_id = snippet.get("channelId", "")
            subscriber_count = int(subscriber_counts.get(channel_id, 0))
            view_count = int(statistics.get("viewCount", 0))
            duration_seconds = self._parse_iso8601_duration_to_seconds(
                content_details.get("duration", "")
            )
            engagement_rate = (view_count / subscriber_count) if subscriber_count > 0 else 0.0
            thumbs = snippet.get("thumbnails", {})
            thumbnail_url = (
                thumbs.get("high", {}).get("url")
                or thumbs.get("medium", {}).get("url")
                or thumbs.get("default", {}).get("url")
                or ""
            )
            results.append(
                {
                    "video_id": video_id,
                    "title": snippet.get("title", ""),
                    "description": snippet.get("description", ""),
                    "tags": snippet.get("tags", []),
                    "view_count": view_count,
                    "like_count": int(statistics.get("likeCount", 0)),
                    "comment_count": int(statistics.get("commentCount", 0)),
                    "duration_seconds": duration_seconds,
                    "published_at": snippet.get("publishedAt"),
                    "channel_title": snippet.get("channelTitle", ""),
                    "channel_id": channel_id,
                    "subscriber_count": subscriber_count,
                    "engagement_rate": engagement_rate,
                    "category_id": snippet.get("categoryId", ""),
                    "default_language": snippet.get("defaultLanguage", ""),
                    "default_audio_language": snippet.get("defaultAudioLanguage", ""),
                    "thumbnail_url": thumbnail_url,
                    "video_url": f"https://www.youtube.com/watch?v={video_id}",
                }
            )
        return results

    def _extract_video_ids(self, items: List[Dict[str, Any]]) -> List[str]:
        return [
            item.get("id", {}).get("videoId")
            for item in items
            if item.get("id", {}).get("videoId")
        ]

    def _get_channel_subscriber_counts(self, channel_ids: List[str]) -> Dict[str, int]:
        unique_ids = [channel_id for channel_id in dict.fromkeys(channel_ids) if channel_id]
        if not unique_ids:
            return {}
        url = f"{YOUTUBE_API_BASE}/channels"
        result: Dict[str, int] = {}
        # channels.list APIも1回最大50件まで
        for i in range(0, len(unique_ids), 50):
            batch = unique_ids[i:i+50]
            params = {
                "part": "statistics",
                "id": ",".join(batch),
                "key": self.api_key,
                "maxResults": len(batch),
            }
            data = self._get(url, params)
            for item in data.get("items", []):
                channel_id = item.get("id", "")
                stats = item.get("statistics", {})
                result[channel_id] = int(stats.get("subscriberCount", 0))
        return result

    def get_channel_info(self, channel_id: str) -> Dict[str, Any]:
        """チャンネル詳細情報を取得する。channels.list 3単位消費。"""
        url = f"{YOUTUBE_API_BASE}/channels"
        params = {
            "part": "snippet,statistics,contentDetails",
            "id": channel_id,
            "key": self.api_key,
        }
        data = self._get(url, params)
        items = data.get("items", [])
        if not items:
            raise YouTubeClientError(f"Channel not found: {channel_id}")
        item = items[0]
        snippet = item.get("snippet", {})
        statistics = item.get("statistics", {})
        content_details = item.get("contentDetails", {})

        thumbs = snippet.get("thumbnails", {})
        thumbnail_url = (
            thumbs.get("high", {}).get("url")
            or thumbs.get("medium", {}).get("url")
            or thumbs.get("default", {}).get("url")
            or ""
        )
        uploads_playlist_id = content_details.get("relatedPlaylists", {}).get("uploads", "")

        return {
            "channel_id": channel_id,
            "title": snippet.get("title", ""),
            "description": snippet.get("description", ""),
            "thumbnail_url": thumbnail_url,
            "subscriber_count": int(statistics.get("subscriberCount", 0)),
            "view_count": int(statistics.get("viewCount", 0)),
            "video_count": int(statistics.get("videoCount", 0)),
            "published_at": snippet.get("publishedAt", ""),
            "custom_url": snippet.get("customUrl", ""),
            "channel_url": f"https://www.youtube.com/channel/{channel_id}",
            "uploads_playlist_id": uploads_playlist_id,
        }

    def get_channel_videos(self, uploads_playlist_id: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """チャンネルの最新動画を取得する。playlistItems.list 1単位 + videos.list 1単位消費。"""
        if not uploads_playlist_id:
            return []

        # playlistItems.list で最新動画IDを取得（クォータ1単位）
        url = f"{YOUTUBE_API_BASE}/playlistItems"
        params = {
            "part": "snippet",
            "playlistId": uploads_playlist_id,
            "maxResults": max_results,
            "key": self.api_key,
        }
        data = self._get(url, params)
        items = data.get("items", [])
        if not items:
            return []

        video_ids = []
        snippets_map: Dict[str, Any] = {}
        for item in items:
            snippet = item.get("snippet", {})
            resource = snippet.get("resourceId", {})
            vid = resource.get("videoId", "")
            if vid:
                video_ids.append(vid)
                snippets_map[vid] = snippet

        if not video_ids:
            return []

        # videos.list で再生回数を取得（クォータ1単位）
        videos_url = f"{YOUTUBE_API_BASE}/videos"
        videos_params = {
            "part": "statistics",
            "id": ",".join(video_ids),
            "key": self.api_key,
        }
        videos_data = self._get(videos_url, videos_params)
        stats_map: Dict[str, int] = {}
        for v in videos_data.get("items", []):
            stats_map[v.get("id", "")] = int(v.get("statistics", {}).get("viewCount", 0))

        results = []
        for vid in video_ids:
            snippet = snippets_map.get(vid, {})
            thumbs = snippet.get("thumbnails", {})
            thumbnail_url = (
                thumbs.get("high", {}).get("url")
                or thumbs.get("medium", {}).get("url")
                or thumbs.get("default", {}).get("url")
                or ""
            )
            results.append({
                "video_id": vid,
                "title": snippet.get("title", ""),
                "thumbnail_url": thumbnail_url,
                "published_at": snippet.get("publishedAt", ""),
                "view_count": stats_map.get(vid, 0),
                "video_url": f"https://www.youtube.com/watch?v={vid}",
            })
        return results

    def _parse_iso8601_duration_to_seconds(self, duration: str) -> int:
        if not duration or not duration.startswith("P"):
            return 0
        hours = 0
        minutes = 0
        seconds = 0
        time_part = duration.split("T", 1)[1] if "T" in duration else ""
        number = ""
        for ch in time_part:
            if ch.isdigit():
                number += ch
                continue
            if not number:
                continue
            if ch == "H":
                hours = int(number)
            elif ch == "M":
                minutes = int(number)
            elif ch == "S":
                seconds = int(number)
            number = ""
        return hours * 3600 + minutes * 60 + seconds

    def _get(self, url: str, params: Dict[str, Any]) -> Dict[str, Any]:
        # URLの末尾パス（例: "search", "videos", "channels", "playlistItems"）を取得
        endpoint = url.rstrip("/").split("/")[-1]
        while True:
            try:
                params["key"] = self.api_key
                response = self.session.get(url, params=params, timeout=self.timeout)
                if response.status_code == 403:
                    if self._rotate_key():
                        continue  # 次のキーで再試行
                response.raise_for_status()
                _add_quota(endpoint)
                return response.json()
            except requests.RequestException as exc:
                raise YouTubeClientError(str(exc)) from exc