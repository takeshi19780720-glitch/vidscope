import os
from typing import List

from dotenv import load_dotenv


load_dotenv()


class Settings:
    def __init__(self) -> None:
        self.youtube_api_keys: List[str] = []
        # 全てのYOUTUBE_API_KEY環境変数を収集
        base_key = os.getenv("YOUTUBE_API_KEY", "").strip()
        if base_key:
            self.youtube_api_keys.append(base_key)
        i = 2
        while True:
            key = os.getenv(f"YOUTUBE_API_KEY_{i}", "").strip()
            if not key:
                break
            self.youtube_api_keys.append(key)
            i += 1
        # 管理者パスワード
        self.admin_password: str = os.getenv("ADMIN_PASSWORD", "").strip()

    @property
    def youtube_api_key(self) -> str:
        """後方互換: 最初のキーを返す"""
        return self.youtube_api_keys[0] if self.youtube_api_keys else ""


settings = Settings()
