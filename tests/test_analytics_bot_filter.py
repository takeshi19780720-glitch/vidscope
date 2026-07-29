"""app/analytics.py のボット判定ロジックのユニットテスト。

対象: _is_bot_user_agent / _is_bot_ip / _is_scan_path
（判定パターン自体 _BOT_UA_PATTERNS / _BOT_IP_RANGES / _SCAN_PATH_PREFIXES は
 検証済みのため変更しない。このテストは「現状のロジックが期待通り動くこと」
 と「SQL側 is_bot_page_view() と等価であること」を保証するために追加した。）

実行方法:
    cd <リポジトリルート>
    python3 -m unittest tests.test_analytics_bot_filter -v
"""

import re
import sys
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app import analytics  # noqa: E402

SCHEMA_SQL_PATH = REPO_ROOT / "supabase_schema.sql"


def _extract_is_bot_page_view_sql() -> str:
    """supabase_schema.sql から is_bot_page_view() 関数本体（$$...$$の中身）を抽出する。"""
    sql = SCHEMA_SQL_PATH.read_text(encoding="utf-8")
    match = re.search(
        r"create or replace function is_bot_page_view\([^)]*\)\s*"
        r"returns boolean language sql immutable as \$\$(.*?)\$\$;",
        sql,
        re.DOTALL,
    )
    if not match:
        raise AssertionError("is_bot_page_view() 関数本体が supabase_schema.sql に見つからない")
    return match.group(1)


def _sql_ua_regex_pattern() -> str:
    """SQL内の lower(user_agent) ~ '...' の正規表現部分を抽出する。"""
    body = _extract_is_bot_page_view_sql()
    match = re.search(r"lower\(user_agent\)\s*~\s*'([^']+)'", body)
    if not match:
        raise AssertionError("UAの正規表現パターンが抽出できない")
    return match.group(1)


def _sql_ua_like_keywords() -> list[str]:
    """SQL内の lower(user_agent) like '%xxx%' のxxx部分を全て抽出する。"""
    body = _extract_is_bot_page_view_sql()
    # UAブロックのみ（IPブロック開始より前）に限定する
    ua_block_end = body.index("既知のbot/クローラーIPレンジ")
    ua_block = body[:ua_block_end]
    return re.findall(r"lower\(user_agent\)\s+like\s+'%([^%']+)%'", ua_block)


def _sql_ip_cidrs() -> list[str]:
    """SQL内の inet(ip) <<= inet '...' のCIDRを全て抽出する。"""
    body = _extract_is_bot_page_view_sql()
    return re.findall(r"inet\(ip\)\s*<<=\s*inet\s*'([^']+)'", body)


def _sql_scan_path_prefixes() -> list[str]:
    """SQL内の lower(path) like '/xxx%' のプレフィックスを全て抽出する。"""
    body = _extract_is_bot_page_view_sql()
    path_block_start = body.index("脆弱性スキャンで狙われる典型パス")
    path_block = body[path_block_start:]
    return re.findall(r"lower\(path\)\s+like\s+'([^%']+)%'", path_block)


def _sql_is_bot_page_view(user_agent: str | None, ip: str | None, path: str | None) -> bool:
    """is_bot_page_view() のSQLロジックをPythonで再現した参照実装。

    実際にPostgreSQLへ接続してテストするのが理想だが、ローカルにSupabase接続情報が
    ないため、SQLファイルから動的に抽出したパターンでロジックを再現し、
    Python側実装(_is_bot_user_agent等)との出力を突き合わせる形で等価性を確認する。
    """
    import ipaddress as _ipaddress

    ua_regex = _sql_ua_regex_pattern()
    ua_like_keywords = _sql_ua_like_keywords()
    ip_cidrs = _sql_ip_cidrs()
    scan_prefixes = _sql_scan_path_prefixes()

    ua_match = False
    if user_agent:
        ua_lower = user_agent.lower()
        if re.search(ua_regex, ua_lower):
            ua_match = True
        elif any(kw in ua_lower for kw in ua_like_keywords):
            ua_match = True

    ip_match = False
    if ip and re.match(r"^[0-9.]+$", ip):
        try:
            addr = _ipaddress.ip_address(ip)
            ip_match = any(addr in _ipaddress.ip_network(cidr) for cidr in ip_cidrs)
        except ValueError:
            ip_match = False

    path_match = False
    if path:
        path_lower = path.lower()
        path_match = any(path_lower.startswith(prefix) for prefix in scan_prefixes)

    return ua_match or ip_match or path_match


class BotUserAgentTests(unittest.TestCase):
    """Google系クローラーUA除外 + 一般的な日本の読者UAが誤検知されないことの確認。"""

    def test_googlebot_smartphone_is_bot(self):
        ua = (
            "Mozilla/5.0 (Linux; Android 6.0.1; Nexus 5X Build/MMB29P) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/W.X.Y.Z Mobile "
            "Safari/537.36 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
        )
        self.assertTrue(analytics._is_bot_user_agent(ua))

    def test_google_inspectiontool_is_bot(self):
        ua = "Mozilla/5.0 (compatible; Google-InspectionTool/1.0)"
        self.assertTrue(analytics._is_bot_user_agent(ua))

    def test_googleother_is_bot(self):
        ua = "GoogleOther"
        self.assertTrue(analytics._is_bot_user_agent(ua))

    def test_google_extended_is_bot(self):
        ua = "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko); Google-Extended"
        self.assertTrue(analytics._is_bot_user_agent(ua))

    def test_adsbot_google_is_bot(self):
        ua = "AdsBot-Google (+http://www.google.com/adsbot.html)"
        self.assertTrue(analytics._is_bot_user_agent(ua))

    def test_ahrefsbot_is_bot(self):
        ua = "Mozilla/5.0 (compatible; AhrefsBot/7.0; +http://ahrefs.com/robot/)"
        self.assertTrue(analytics._is_bot_user_agent(ua))

    def test_semrushbot_is_bot(self):
        ua = "Mozilla/5.0 (compatible; SemrushBot/7~bl; +http://www.semrush.com/bot.html)"
        self.assertTrue(analytics._is_bot_user_agent(ua))

    def test_gptbot_is_bot(self):
        ua = "Mozilla/5.0 (compatible; GPTBot/1.2; +https://openai.com/gptbot)"
        self.assertTrue(analytics._is_bot_user_agent(ua))

    def test_curl_is_bot(self):
        self.assertTrue(analytics._is_bot_user_agent("curl/8.7.1"))

    def test_python_requests_is_bot(self):
        self.assertTrue(analytics._is_bot_user_agent("python-requests/2.31.0"))

    # --- 日本の一般的な読者UA（誤検知されないこと） ---

    def test_japanese_iphone_safari_is_not_bot(self):
        ua = (
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 "
            "Mobile/15E148 Safari/604.1"
        )
        self.assertFalse(analytics._is_bot_user_agent(ua))

    def test_japanese_android_chrome_is_not_bot(self):
        ua = (
            "Mozilla/5.0 (Linux; Android 14; SC-51D) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/125.0.0.0 Mobile Safari/537.36"
        )
        self.assertFalse(analytics._is_bot_user_agent(ua))

    def test_windows_edge_is_not_bot(self):
        ua = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36 Edg/125.0.0.0"
        )
        self.assertFalse(analytics._is_bot_user_agent(ua))

    def test_mac_safari_is_not_bot(self):
        ua = (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15"
        )
        self.assertFalse(analytics._is_bot_user_agent(ua))


class BotIpRangeTests(unittest.TestCase):
    """43.128.0.0/10 (Tencent Cloud) の境界値テスト + 一般的な日本の読者IPの非検知確認。"""

    def test_network_address_is_bot(self):
        self.assertTrue(analytics._is_bot_ip("43.128.0.0"))

    def test_broadcast_address_is_bot(self):
        self.assertTrue(analytics._is_bot_ip("43.191.255.255"))

    def test_middle_of_range_is_bot(self):
        self.assertTrue(analytics._is_bot_ip("43.160.1.1"))

    def test_just_below_network_is_not_bot(self):
        # 43.128.0.0/10 の直前(43.127.255.255)は範囲外
        self.assertFalse(analytics._is_bot_ip("43.127.255.255"))

    def test_just_above_broadcast_is_not_bot(self):
        # 43.191.255.255 の直後(43.192.0.0)は範囲外
        self.assertFalse(analytics._is_bot_ip("43.192.0.0"))

    def test_googlebot_range_is_bot(self):
        self.assertTrue(analytics._is_bot_ip("66.249.64.1"))

    def test_typical_japanese_isp_ip_is_not_bot(self):
        # NTTドコモ/OCN等の典型的な日本国内ISPレンジのサンプル（bot範囲外）
        for ip in ("126.0.0.1", "133.1.1.1", "153.240.0.1", "202.32.0.1"):
            with self.subTest(ip=ip):
                self.assertFalse(analytics._is_bot_ip(ip))

    def test_empty_or_none_ip_is_not_bot(self):
        self.assertFalse(analytics._is_bot_ip(""))
        self.assertFalse(analytics._is_bot_ip(None))

    def test_invalid_ip_is_not_bot(self):
        self.assertFalse(analytics._is_bot_ip("not-an-ip"))


class SpoofedUaWithBotIpTests(unittest.TestCase):
    """UA偽装 + bot IPの組み合わせ（UAだけ見ると通常ブラウザに見えるがIPで捕捉されるケース）。"""

    def test_spoofed_ios_ua_from_tencent_cloud_is_bot(self):
        spoofed_ua = (
            "Mozilla/5.0 (iPhone; CPU iPhone OS 13_2_3 like Mac OS X) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 Safari/13.0.3"
        )
        tencent_ip = "43.135.20.5"
        # UAだけでは検知できない（偽装が成功している）ことを確認
        self.assertFalse(analytics._is_bot_user_agent(spoofed_ua))
        # だがIP判定側で捕捉できる
        self.assertTrue(analytics._is_bot_ip(tencent_ip))

    def test_spoofed_android_ua_from_tencent_cloud_is_bot(self):
        spoofed_ua = (
            "Mozilla/5.0 (Linux; Android 10; Pixel 3) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/90.0.4430.91 Mobile Safari/537.36"
        )
        tencent_ip = "43.150.10.10"
        self.assertFalse(analytics._is_bot_user_agent(spoofed_ua))
        self.assertTrue(analytics._is_bot_ip(tencent_ip))

    def test_normal_ua_from_normal_ip_is_not_bot(self):
        normal_ua = (
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 "
            "Mobile/15E148 Safari/604.1"
        )
        normal_ip = "126.0.0.1"
        self.assertFalse(analytics._is_bot_user_agent(normal_ua))
        self.assertFalse(analytics._is_bot_ip(normal_ip))


class ScanPathTests(unittest.TestCase):
    """/wp-json 系を含む脆弱性スキャンパスの除外確認。"""

    def test_wp_json_is_scan_path(self):
        self.assertTrue(analytics._is_scan_path("/wp-json"))

    def test_wp_json_with_subpath_is_scan_path(self):
        self.assertTrue(analytics._is_scan_path("/wp-json/wp/v2/users"))

    def test_wp_admin_is_scan_path(self):
        self.assertTrue(analytics._is_scan_path("/wp-admin/install.php"))

    def test_wp_login_is_scan_path(self):
        self.assertTrue(analytics._is_scan_path("/wp-login.php"))

    def test_env_is_scan_path(self):
        self.assertTrue(analytics._is_scan_path("/.env"))

    def test_git_is_scan_path(self):
        self.assertTrue(analytics._is_scan_path("/.git/config"))

    def test_normal_blog_path_is_not_scan_path(self):
        self.assertFalse(analytics._is_scan_path("/blog/youtube-cpm-rpm-calculation-guide"))

    def test_root_path_is_not_scan_path(self):
        self.assertFalse(analytics._is_scan_path("/"))

    def test_app_path_is_not_scan_path(self):
        self.assertFalse(analytics._is_scan_path("/app"))

    def test_case_insensitive(self):
        self.assertTrue(analytics._is_scan_path("/WP-JSON/foo"))


class SqlPythonEquivalenceTests(unittest.TestCase):
    """SQL側 is_bot_page_view() の正規表現/LIKE条件とPython側判定の等価性テスト。

    ローカルにSupabase(PostgreSQL)接続情報がないため実DBには接続できない。
    そのため supabase_schema.sql から正規表現/LIKEパターンを動的に抽出し、
    Pythonでそのロジックを再現した _sql_is_bot_page_view() を作り、
    実装(_is_bot_user_agent/_is_bot_ip/_is_scan_path)の組み合わせ結果と突き合わせる。
    """

    CASES = [
        # (user_agent, ip, path)
        ("Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)", "8.8.8.8", "/"),
        ("Mozilla/5.0 (compatible; AhrefsBot/7.0)", "1.2.3.4", "/blog/foo"),
        ("curl/8.7.1", "1.2.3.4", "/"),
        ("GPTBot/1.0", "1.2.3.4", "/"),
        (
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 "
            "(KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1",
            "126.0.0.1",
            "/",
        ),
        (
            "Mozilla/5.0 (Linux; Android 14; SC-51D) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/125.0.0.0 Mobile Safari/537.36",
            "133.1.1.1",
            "/blog/vidscope-vs-tubebuddy-vidiq-socialblade",
        ),
        (
            "Mozilla/5.0 (iPhone; CPU iPhone OS 13_2_3 like Mac OS X) AppleWebKit/605.1.15 "
            "(KHTML, like Gecko) Mobile/15E148 Safari/13.0.3",
            "43.135.20.5",
            "/",
        ),
        ("Mozilla/5.0 (Windows NT 10.0; Win64; x64)", "153.240.0.1", "/wp-json/wp/v2/users"),
        ("Mozilla/5.0 (Windows NT 10.0; Win64; x64)", "153.240.0.1", "/"),
        (None, "43.128.0.0", "/"),
        ("Mozilla/5.0 normal browser", None, "/.env"),
        ("Mozilla/5.0 normal browser", "202.32.0.1", "/wp-admin/install.php"),
    ]

    def test_python_impl_matches_sql_reference_for_each_case(self):
        for user_agent, ip, path in self.CASES:
            with self.subTest(user_agent=user_agent, ip=ip, path=path):
                python_result = (
                    analytics._is_bot_user_agent(user_agent or "")
                    or analytics._is_bot_ip(ip or "")
                    or analytics._is_scan_path(path or "")
                )
                sql_result = _sql_is_bot_page_view(user_agent, ip, path)
                self.assertEqual(
                    python_result,
                    sql_result,
                    f"Python判定={python_result} SQL判定={sql_result} が不一致: "
                    f"ua={user_agent!r} ip={ip!r} path={path!r}",
                )

    def test_sql_ua_regex_covers_same_keywords_as_python_first_group(self):
        """SQLの正規表現(bot|spider|...)がPython側 _BOT_UA_PATTERNS の対応する先頭グループと一致すること。"""
        sql_pattern = _sql_ua_regex_pattern()
        sql_keywords = re.findall(r"[a-z0-9./\-]+", sql_pattern)
        # Python側 _BOT_UA_PATTERNS のうち、SQLの正規表現グループに対応する先頭部分
        # (件数はSQL側の抽出結果に合わせて動的に決定し、ハードコードしない)
        python_first_group = list(analytics._BOT_UA_PATTERNS[: len(sql_keywords)])
        self.assertEqual(sql_keywords, python_first_group)

    def test_sql_ua_like_keywords_are_subset_of_python_patterns(self):
        """SQLのLIKE列挙キーワードが全てPython側 _BOT_UA_PATTERNS に含まれること。"""
        sql_like_keywords = _sql_ua_like_keywords()
        for kw in sql_like_keywords:
            with self.subTest(keyword=kw):
                self.assertIn(kw, analytics._BOT_UA_PATTERNS)

    def test_sql_ip_cidrs_match_python_bot_ip_ranges(self):
        sql_cidrs = set(_sql_ip_cidrs())
        python_cidrs = {cidr for cidr, _comment in analytics._BOT_IP_RANGES}
        self.assertEqual(sql_cidrs, python_cidrs)

    def test_sql_scan_path_prefixes_match_python_prefixes(self):
        sql_prefixes = set(_sql_scan_path_prefixes())
        python_prefixes = set(analytics._SCAN_PATH_PREFIXES)
        self.assertEqual(sql_prefixes, python_prefixes)


class AnalyticsExecutorTests(unittest.TestCase):
    """スレッド無制限生成の解消(修正1) + 例外の取りこぼし対策(修正2)の確認。

    - リクエストごとに threading.Thread を無制限に生成せず、上限管理された
      ThreadPoolExecutor(_analytics_executor)にsubmitされること
    - キューが溢れた場合は例外を起こさず、1件を諦めてWARNINGログを出すこと
    - _resolve_and_insert 内(sb.insert相当)で例外が起きても logging に残り、
      呼び出し元(log_page_view)には伝播しないこと
    """

    def test_submit_analytics_task_runs_on_executor(self):
        done = threading.Event()
        result = {}

        def _task():
            result["thread_name"] = threading.current_thread().name
            done.set()

        analytics._submit_analytics_task(_task)
        self.assertTrue(done.wait(timeout=2), "タスクがexecutor上で実行されなかった")
        self.assertIn("analytics-io", result["thread_name"])

    def test_queue_full_drops_task_and_logs_warning(self):
        # pending件数を上限まで埋めた状態を作り、溢れた1件が例外なく捨てられ、
        # WARNINGログが出ることを確認する。
        with mock.patch.object(analytics, "_analytics_pending_count", analytics._ANALYTICS_QUEUE_MAXSIZE):
            with self.assertLogs("vidscope", level="WARNING") as cm:
                # 例外を投げずに正常終了することが重要（投入自体を諦めるだけ）
                analytics._submit_analytics_task(lambda: None)
            self.assertTrue(any("queue full" in msg.lower() for msg in cm.output))

    def test_resolve_and_insert_exception_is_logged_not_raised(self):
        """sb.insert が例外を投げても log_page_view 呼び出し側には伝播しないこと。"""

        def _boom(*_args, **_kwargs):
            raise RuntimeError("supabase insert failed (simulated)")

        done = threading.Event()
        orig_submit = analytics._analytics_executor.submit

        def _tracking_submit(fn, *args, **kwargs):
            fut = orig_submit(fn, *args, **kwargs)
            fut.add_done_callback(lambda _f: done.set())
            return fut

        with mock.patch.object(analytics.sb, "insert", side_effect=_boom), \
             mock.patch.object(analytics, "_get_country", return_value="Japan"), \
             mock.patch.object(analytics._analytics_executor, "submit", side_effect=_tracking_submit), \
             self.assertLogs("vidscope", level="WARNING") as cm:
            try:
                analytics.log_page_view(
                    path="/blog/some-article",
                    ip="126.0.0.1",
                    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Safari/605.1.15",
                    language="ja",
                    referer="",
                )
            except Exception as exc:  # log_page_view自体が例外を投げてはならない
                self.fail(f"log_page_view が例外を送出した: {exc!r}")

            self.assertTrue(done.wait(timeout=2), "バックグラウンドタスクが完了しなかった")
            self.assertTrue(any("background task failed" in msg for msg in cm.output))

    def test_shutdown_does_not_block_long(self):
        """shutdown_analytics_executor が指定タイムアウト程度で戻ること（長時間ブロックしない）。"""
        started = time.monotonic()
        # 実行中タスクがなくてもshutdownがすぐ戻ることを確認（極端に長い待ちにならない）
        analytics.shutdown_analytics_executor(wait_timeout=0.01)
        elapsed = time.monotonic() - started
        self.assertLess(elapsed, 3.0, "shutdownが長時間ブロックしている")
        # 後続テストのためexecutorを元に戻す
        analytics._analytics_executor = ThreadPoolExecutor(
            max_workers=analytics._ANALYTICS_MAX_WORKERS, thread_name_prefix="analytics-io"
        )


if __name__ == "__main__":
    unittest.main()
