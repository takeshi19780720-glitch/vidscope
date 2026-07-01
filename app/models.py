from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, HttpUrl


class VideoItem(BaseModel):
    video_id: str
    title: str
    description: str
    tags: List[str]
    view_count: int
    like_count: int
    comment_count: int
    duration_seconds: int
    published_at: datetime
    channel_title: str
    channel_id: str = ""
    subscriber_count: int
    engagement_rate: float
    category_id: str = ""
    default_language: str = ""
    default_audio_language: str = ""
    thumbnail_url: HttpUrl
    video_url: HttpUrl


class SearchResponse(BaseModel):
    q: str
    max_results: int
    total: int
    items: List[VideoItem]


class ChannelInfo(BaseModel):
    channel_id: str
    title: str
    description: str
    thumbnail_url: str
    subscriber_count: int
    view_count: int
    video_count: int
    published_at: str
    custom_url: str = ""
    channel_url: str
    uploads_playlist_id: str = ""


class ChannelVideoItem(BaseModel):
    video_id: str
    title: str
    thumbnail_url: str
    published_at: str
    view_count: int
    video_url: str