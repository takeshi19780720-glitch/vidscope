"""BotShieldMiddleware の統合テスト。

対象: app/main.py の BotShieldMiddleware
実行方法:
    cd <リポジトリルート>
    python3 -m unittest tests.test_bot_shield -v
"""

import sys
import time
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from fastapi.testclient import TestClient

from app import analytics, main  # noqa: E402


class BotShieldMiddlewareTests(unittest.TestCase):
    """ミドルウェア層でのスキャンパス遮断・IP自動ブロック・通常リクエスト通過を検証。"""

    def setUp(self):
        # 各テスト間でプロセス内ブロックリスト/ヒストリをリセット
        main.BotShieldMiddleware._blocked_ips = {}
        main.BotShieldMiddleware._scan_hits = {}
        main.BotShieldMiddleware._scan_rate_hits = {}
        self.client = TestClient(main.app)

    def test_shell_php_returns_403_and_blocked_header(self):
        resp = self.client.get("/shell.php")
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.headers.get("X-VidScope-Bot-Shield"), "blocked")

    def test_double_slash_wp_includes_wlwmanifest_returns_403(self):
        resp = self.client.get("//test/wp-includes/wlwmanifest.xml")
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.headers.get("X-VidScope-Bot-Shield"), "blocked")

    def test_scan_path_is_not_logged_to_analytics(self):
        with mock.patch.object(analytics, "log_page_view") as mock_log:
            resp = self.client.get("/wp-json/wp/v2/users")
            self.assertEqual(resp.status_code, 403)
            self.assertEqual(resp.headers.get("X-VidScope-Bot-Shield"), "blocked")
            mock_log.assert_not_called()

    def test_three_scan_hits_block_fourth_with_ip_blocked(self):
        # 同一IPから3回スキャンパスにアクセス
        for _ in range(3):
            resp = self.client.get("/wp-login.php")
            self.assertEqual(resp.status_code, 403)
            self.assertEqual(resp.headers.get("X-VidScope-Bot-Shield"), "blocked")

        # 4回目はIPブロック済みになる
        resp = self.client.get("/wp-login.php")
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.headers.get("X-VidScope-Bot-Shield"), "ip-blocked")

    def test_ip_block_expires_after_duration(self):
        # 3回ヒットでブロック
        for _ in range(3):
            self.client.get("/wp-login.php")

        # ブロックされていることを確認
        resp = self.client.get("/wp-login.php")
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.headers.get("X-VidScope-Bot-Shield"), "ip-blocked")

        # 24時間経過させてブロック解除
        now = time.time()
        main.BotShieldMiddleware._blocked_ips["testclient"] = now - 1

        # 再度スキャンパスへアクセスすると通常の blocked ヘッダーに戻る
        resp = self.client.get("/wp-login.php")
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.headers.get("X-VidScope-Bot-Shield"), "blocked")

    def test_normal_root_request_is_not_blocked(self):
        with mock.patch.object(analytics, "log_page_view"):
            resp = self.client.get("/")
            # 静的ファイルが存在すれば200、存在しなければ404だが403でないことを確認
            self.assertNotEqual(resp.status_code, 403)
            self.assertNotEqual(resp.headers.get("X-VidScope-Bot-Shield"), "blocked")

    def test_normal_api_search_request_is_not_blocked(self):
        with mock.patch.object(analytics, "log_search_query"):
            resp = self.client.get("/api/search?q=test")
            self.assertNotEqual(resp.status_code, 403)
            self.assertNotIn(resp.headers.get("X-VidScope-Bot-Shield", ""), ("blocked", "ip-blocked"))

    def test_scan_path_rate_limit_429(self):
        # 自動ブロックがすぐに発動するとレート制限到達前に ip-blocked になるため、
        # このテストでは閾値を一時的に高くしてレート制限ロジックだけを検証する。
        with mock.patch.object(main.BotShieldMiddleware, "_SCAN_THRESHOLD", 100):
            # 同一IPから10回スキャンパスにアクセス
            for _ in range(10):
                resp = self.client.get("/.env")
                self.assertEqual(resp.status_code, 403)
                self.assertEqual(resp.headers.get("X-VidScope-Bot-Shield"), "blocked")

            # 11回目はレート制限
            resp = self.client.get("/.env")
            self.assertEqual(resp.status_code, 429)
            self.assertEqual(resp.headers.get("X-VidScope-Bot-Shield"), "rate-limited")


if __name__ == "__main__":
    unittest.main()
