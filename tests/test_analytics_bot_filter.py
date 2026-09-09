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


def _sql_scan_path_suffixes() -> list[str]:
    """SQL内の lower(path) like '%.xxx' のサフィックス部分を全て抽出する。"""
    body = _extract_is_bot_page_view_sql()
    path_block_start = body.index("脆弱性スキャンで狙われる典型パス")
    path_block = body[path_block_start:]
    return re.findall(r"lower\(path\)\s+like\s+'(%\.[^'%]+)'", path_block)


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
    scan_suffixes = _sql_scan_path_suffixes()

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
        if any(path_lower.startswith(prefix) for prefix in scan_prefixes):
            path_match = True
        elif any(path_lower.endswith(suffix.lstrip("%")) for suffix in scan_suffixes):
            path_match = True

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


class NewBotFilterTests(unittest.TestCase):
    """2026-08-30スパイク対応で追加したフィルタのテスト。"""

    # ---- HeadlessChrome UA ----

    def test_headlesschrome_ua_is_bot(self):
        ua = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) HeadlessChrome/114.0.5735.90 Safari/537.36"
        self.assertTrue(analytics._is_bot_user_agent(ua))

    def test_headlesschromium_ua_is_bot(self):
        ua = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) HeadlessChromium/114.0.5735.90 Safari/537.36"
        self.assertTrue(analytics._is_bot_user_agent(ua))

    def test_regular_chrome_is_not_bot(self):
        # 通常のChromeは 'HeadlessChrome' を含まないため誤検知されない
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
        self.assertFalse(analytics._is_bot_user_agent(ua))

    # ---- Tencent Cloud 追加IPレンジ ----

    def test_tencent_beijing_1_12_is_bot(self):
        # 1.12.0.0/14 (1.12.0.0 〜 1.15.255.255)
        self.assertTrue(analytics._is_bot_ip("1.14.110.85"))

    def test_tencent_beijing_118_24_is_bot(self):
        # 118.24.0.0/16
        self.assertTrue(analytics._is_bot_ip("118.24.135.34"))

    def test_tencent_hk_101_32_is_bot(self):
        # 101.32.0.0/15 (101.32.0.0 〜 101.33.255.255)
        self.assertTrue(analytics._is_bot_ip("101.32.49.171"))

    def test_just_outside_1_12_range_is_not_bot(self):
        # 1.12.0.0/14 の直前(1.11.255.255)は範囲外
        self.assertFalse(analytics._is_bot_ip("1.11.255.255"))

    def test_just_outside_101_32_range_is_not_bot(self):
        # 101.32.0.0/15 の直後(101.34.0.0)は範囲外
        self.assertFalse(analytics._is_bot_ip("101.34.0.0"))

    # ---- バックアップ探索パス（プレフィックス） ----

    def test_backup_prefix_is_scan_path(self):
        self.assertTrue(analytics._is_scan_path("/backup/database.sql"))

    def test_backups_prefix_is_scan_path(self):
        self.assertTrue(analytics._is_scan_path("/backups/database.sql"))

    def test_dump_prefix_is_scan_path(self):
        self.assertTrue(analytics._is_scan_path("/dump/vidscope.sql"))

    # ---- バックアップファイル拡張子（サフィックス） ----

    def test_bak_suffix_is_scan_path(self):
        self.assertTrue(analytics._is_scan_path("/config/settings.bak"))

    def test_sql_suffix_is_scan_path(self):
        self.assertTrue(analytics._is_scan_path("/backups/database.sql"))

    def test_zip_suffix_is_scan_path(self):
        self.assertTrue(analytics._is_scan_path("/vidscope.zip"))

    def test_tar_gz_suffix_is_scan_path(self):
        self.assertTrue(analytics._is_scan_path("/vidscope.tar.gz"))

    def test_normal_path_with_sql_keyword_not_blocked(self):
        # /blog/sql-tutorial のような正当なパスが誤検知されないこと
        self.assertFalse(analytics._is_scan_path("/blog/sql-tutorial"))

    def test_case_insensitive_zip_suffix(self):
        self.assertTrue(analytics._is_scan_path("/Archive.ZIP"))


class NewPatternSqlEquivalenceTests(unittest.TestCase):
    """新パターン（HeadlessChrome UA / 追加IPレンジ / バックアップパス）のSQL/Python等価性テスト。"""

    NEW_CASES = [
        # (user_agent, ip, path, expected_is_bot)
        ("Mozilla/5.0 HeadlessChrome/114.0.5735.90 Safari/537.36", "1.2.3.4", "/", True),
        ("Mozilla/5.0 HeadlessChromium/114.0 Safari/537.36", "1.2.3.4", "/", True),
        ("Mozilla/5.0 (Windows NT 10.0) Chrome/125.0.0.0 Safari/537.36", "1.2.3.4", "/", False),
        (None, "1.14.110.85", "/", True),
        (None, "118.24.135.34", "/", True),
        (None, "101.32.49.171", "/", True),
        ("Mozilla/5.0 normal browser", "126.0.0.1", "/backups/database.sql", True),
        ("Mozilla/5.0 normal browser", "126.0.0.1", "/vidscope.zip", True),
        ("Mozilla/5.0 normal browser", "126.0.0.1", "/data.tar.gz", True),
        ("Mozilla/5.0 normal browser", "126.0.0.1", "/blog/sql-tutorial", False),
    ]

    def test_new_patterns_python_matches_sql(self):
        for user_agent, ip, path, expected in self.NEW_CASES:
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
                self.assertEqual(
                    python_result,
                    expected,
                    f"期待値={expected} Python判定={python_result}: "
                    f"ua={user_agent!r} ip={ip!r} path={path!r}",
                )

    def test_sql_scan_path_suffixes_match_python_suffixes(self):
        """SQLのサフィックスLIKEパターンがPython側 _SCAN_PATH_SUFFIXES と一致すること。"""
        sql_raw = _sql_scan_path_suffixes()
        # SQLでは '%.bak' のように格納されているため先頭の'%'を除去して比較
        sql_suffixes = {s.lstrip("%") for s in sql_raw}
        python_suffixes = set(analytics._SCAN_PATH_SUFFIXES)
        self.assertEqual(sql_suffixes, python_suffixes)

    def test_sql_ip_cidrs_include_new_tencent_ranges(self):
        sql_cidrs = set(_sql_ip_cidrs())
        for cidr in ("1.12.0.0/14", "118.24.0.0/16", "101.32.0.0/15"):
            with self.subTest(cidr=cidr):
                self.assertIn(cidr, sql_cidrs)


class ExtendedBotFilterTests2026Sep(unittest.TestCase):
    """2026-09-05追加フィルタのテスト（DigitalOcean/AWS/GCP IPレンジ + リファラースパム）。"""

    # ---- DigitalOcean Netherlands 167.71.6.0/24 ----

    def test_digitalocean_167_71_6_is_bot(self):
        # 167.71.6.0/24 (167.71.6.0 〜 167.71.6.255)
        self.assertTrue(analytics._is_bot_ip("167.71.6.60"))

    def test_digitalocean_167_71_6_last_addr_is_bot(self):
        self.assertTrue(analytics._is_bot_ip("167.71.6.255"))

    def test_just_below_167_71_6_is_not_bot(self):
        # 167.71.6.0/24 の直前(167.71.5.255)は範囲外
        self.assertFalse(analytics._is_bot_ip("167.71.5.255"))

    def test_just_above_167_71_6_is_not_bot(self):
        # 167.71.6.0/24 の直後(167.71.7.0)は範囲外
        self.assertFalse(analytics._is_bot_ip("167.71.7.0"))

    # ---- AWS EC2 3.151.194.0/24 (us-east-2) ----

    def test_aws_ec2_us_east2_is_bot(self):
        # 3.151.194.0/24
        self.assertTrue(analytics._is_bot_ip("3.151.194.164"))

    def test_just_outside_aws_us_east2_is_not_bot(self):
        # 3.151.194.0/24 の直後(3.151.195.0)は範囲外
        self.assertFalse(analytics._is_bot_ip("3.151.195.0"))

    # ---- AWS EC2 54.77.166.0/24 (eu-west-1) ----

    def test_aws_ec2_eu_west1_is_bot(self):
        # 54.77.166.0/24
        self.assertTrue(analytics._is_bot_ip("54.77.166.182"))

    def test_just_outside_aws_eu_west1_is_not_bot(self):
        # 54.77.166.0/24 の直後(54.77.167.0)は範囲外
        self.assertFalse(analytics._is_bot_ip("54.77.167.0"))

    # ---- Google Cloud 35.254.67.0/24 (us-central1) ----

    def test_google_cloud_us_central1_is_bot(self):
        # 35.254.67.0/24
        self.assertTrue(analytics._is_bot_ip("35.254.67.46"))

    def test_just_outside_gcp_range_is_not_bot(self):
        # 35.254.67.0/24 の直後(35.254.68.0)は範囲外
        self.assertFalse(analytics._is_bot_ip("35.254.68.0"))

    # ---- リファラースパム ----

    def test_spam_referer_streetfoodies_is_spam(self):
        self.assertTrue(analytics._is_spam_referer("https://streetfoodies.dk/some/path"))

    def test_spam_referer_arapidprototype_is_spam(self):
        self.assertTrue(analytics._is_spam_referer("https://arapidprototype.com/"))

    def test_spam_referer_airbase_cloud_is_spam(self):
        self.assertTrue(analytics._is_spam_referer("https://airbase.cloud/"))

    def test_spam_referer_with_www_is_spam(self):
        self.assertTrue(analytics._is_spam_referer("https://www.streetfoodies.dk/"))

    def test_spam_referer_http_no_path_is_spam(self):
        self.assertTrue(analytics._is_spam_referer("http://arapidprototype.com"))

    def test_empty_referer_is_not_spam(self):
        self.assertFalse(analytics._is_spam_referer(""))

    def test_none_referer_is_not_spam(self):
        self.assertFalse(analytics._is_spam_referer(None))

    def test_google_referer_is_not_spam(self):
        self.assertFalse(analytics._is_spam_referer("https://www.google.com/search?q=vidscope"))

    def test_twitter_referer_is_not_spam(self):
        self.assertFalse(analytics._is_spam_referer("https://twitter.com/"))

    def test_partial_domain_match_is_not_spam(self):
        # 'streetfoodies.dk' をパスに含むだけのURLは誤検知されない
        self.assertFalse(analytics._is_spam_referer("https://example.com/streetfoodies.dk/foo"))


class ExtendedSqlEquivalenceTests2026Sep(unittest.TestCase):
    """2026-09-05追加IPレンジのSQL/Python等価性テスト。"""

    NEW_IP_CASES = [
        # (user_agent, ip, path, expected_is_bot)
        ("Mozilla/5.0 normal browser", "167.71.6.60", "/", True),
        ("Mozilla/5.0 normal browser", "167.71.6.255", "/", True),
        ("Mozilla/5.0 normal browser", "167.71.5.255", "/", False),
        ("Mozilla/5.0 normal browser", "167.71.7.0", "/", False),
        ("Mozilla/5.0 normal browser", "3.151.194.164", "/", True),
        ("Mozilla/5.0 normal browser", "3.151.195.0", "/", False),
        ("Mozilla/5.0 normal browser", "54.77.166.182", "/", True),
        ("Mozilla/5.0 normal browser", "54.77.167.0", "/", False),
        ("Mozilla/5.0 normal browser", "35.254.67.46", "/", True),
        ("Mozilla/5.0 normal browser", "35.254.68.0", "/", False),
    ]

    def test_new_ip_ranges_python_matches_sql(self):
        for user_agent, ip, path, expected in self.NEW_IP_CASES:
            with self.subTest(ip=ip):
                python_result = (
                    analytics._is_bot_user_agent(user_agent or "")
                    or analytics._is_bot_ip(ip or "")
                    or analytics._is_scan_path(path or "")
                )
                sql_result = _sql_is_bot_page_view(user_agent, ip, path)
                self.assertEqual(
                    python_result,
                    sql_result,
                    f"Python/SQL不一致: ua={user_agent!r} ip={ip!r} path={path!r}",
                )
                self.assertEqual(
                    python_result,
                    expected,
                    f"期待値={expected} Python判定={python_result}: ip={ip!r}",
                )

    def test_sql_ip_cidrs_include_new_cloud_ranges(self):
        sql_cidrs = set(_sql_ip_cidrs())
        for cidr in ("167.71.6.0/24", "3.151.194.0/24", "54.77.166.0/24", "35.254.67.0/24"):
            with self.subTest(cidr=cidr):
                self.assertIn(cidr, sql_cidrs)

    def test_sql_ip_cidrs_match_python_bot_ip_ranges_extended(self):
        """SQL側CIDRセットとPython側 _BOT_IP_RANGES が完全一致すること（拡張後も）。"""
        sql_cidrs = set(_sql_ip_cidrs())
        python_cidrs = {cidr for cidr, _comment in analytics._BOT_IP_RANGES}
        self.assertEqual(sql_cidrs, python_cidrs)


class ResidualCloudScraperFilterTests2026Sep(unittest.TestCase):
    """2026-09-05追加(2): 8/30スパイク残存主要クラウドスクレイパー /24 x5 のテスト。"""

    # ---- Google Cloud 35.185.159.0/24 ----

    def test_gcp_35_185_159_is_bot(self):
        # 35.185.159.0/24 (35.185.159.0 〜 35.185.159.255)
        self.assertTrue(analytics._is_bot_ip("35.185.159.90"))

    def test_gcp_35_185_159_last_addr_is_bot(self):
        self.assertTrue(analytics._is_bot_ip("35.185.159.255"))

    def test_just_below_35_185_159_is_not_bot(self):
        self.assertFalse(analytics._is_bot_ip("35.185.158.255"))

    def test_just_above_35_185_159_is_not_bot(self):
        self.assertFalse(analytics._is_bot_ip("35.185.160.0"))

    # ---- Google Cloud 34.78.15.0/24 ----

    def test_gcp_34_78_15_is_bot(self):
        # 34.78.15.0/24 (34.78.15.0 〜 34.78.15.255)
        self.assertTrue(analytics._is_bot_ip("34.78.15.240"))

    def test_gcp_34_78_15_last_addr_is_bot(self):
        self.assertTrue(analytics._is_bot_ip("34.78.15.255"))

    def test_just_below_34_78_15_is_not_bot(self):
        self.assertFalse(analytics._is_bot_ip("34.78.14.255"))

    def test_just_above_34_78_15_is_not_bot(self):
        self.assertFalse(analytics._is_bot_ip("34.78.16.0"))

    # ---- Microsoft Azure 20.104.81.0/24 ----

    def test_azure_20_104_81_is_bot(self):
        # 20.104.81.0/24 (20.104.81.0 〜 20.104.81.255)
        self.assertTrue(analytics._is_bot_ip("20.104.81.161"))

    def test_azure_20_104_81_last_addr_is_bot(self):
        self.assertTrue(analytics._is_bot_ip("20.104.81.255"))

    def test_just_below_20_104_81_is_not_bot(self):
        self.assertFalse(analytics._is_bot_ip("20.104.80.255"))

    def test_just_above_20_104_81_is_not_bot(self):
        self.assertFalse(analytics._is_bot_ip("20.104.82.0"))

    # ---- Vultr 170.64.159.0/24 ----

    def test_vultr_170_64_159_is_bot(self):
        # 170.64.159.0/24 (170.64.159.0 〜 170.64.159.255)
        self.assertTrue(analytics._is_bot_ip("170.64.159.93"))

    def test_vultr_170_64_159_last_addr_is_bot(self):
        self.assertTrue(analytics._is_bot_ip("170.64.159.255"))

    def test_just_below_170_64_159_is_not_bot(self):
        self.assertFalse(analytics._is_bot_ip("170.64.158.255"))

    def test_just_above_170_64_159_is_not_bot(self):
        self.assertFalse(analytics._is_bot_ip("170.64.160.0"))

    # ---- OVHcloud 158.69.55.0/24 ----

    def test_ovh_158_69_55_is_bot(self):
        # 158.69.55.0/24 (158.69.55.0 〜 158.69.55.255)
        self.assertTrue(analytics._is_bot_ip("158.69.55.82"))

    def test_ovh_158_69_55_last_addr_is_bot(self):
        self.assertTrue(analytics._is_bot_ip("158.69.55.255"))

    def test_just_below_158_69_55_is_not_bot(self):
        self.assertFalse(analytics._is_bot_ip("158.69.54.255"))

    def test_just_above_158_69_55_is_not_bot(self):
        self.assertFalse(analytics._is_bot_ip("158.69.56.0"))


class ResidualCloudScraperSqlEquivalenceTests2026Sep(unittest.TestCase):
    """2026-09-05追加(2)の5レンジについてSQL/Python等価性テスト。"""

    RESIDUAL_IP_CASES = [
        # (user_agent, ip, path, expected_is_bot)
        ("Mozilla/5.0 normal browser", "35.185.159.90", "/", True),
        ("Mozilla/5.0 normal browser", "35.185.159.255", "/", True),
        ("Mozilla/5.0 normal browser", "35.185.158.255", "/", False),
        ("Mozilla/5.0 normal browser", "35.185.160.0", "/", False),
        ("Mozilla/5.0 normal browser", "34.78.15.240", "/", True),
        ("Mozilla/5.0 normal browser", "34.78.15.255", "/", True),
        ("Mozilla/5.0 normal browser", "34.78.14.255", "/", False),
        ("Mozilla/5.0 normal browser", "34.78.16.0", "/", False),
        ("Mozilla/5.0 normal browser", "20.104.81.161", "/", True),
        ("Mozilla/5.0 normal browser", "20.104.81.255", "/", True),
        ("Mozilla/5.0 normal browser", "20.104.80.255", "/", False),
        ("Mozilla/5.0 normal browser", "20.104.82.0", "/", False),
        ("Mozilla/5.0 normal browser", "170.64.159.93", "/", True),
        ("Mozilla/5.0 normal browser", "170.64.159.255", "/", True),
        ("Mozilla/5.0 normal browser", "170.64.158.255", "/", False),
        ("Mozilla/5.0 normal browser", "170.64.160.0", "/", False),
        ("Mozilla/5.0 normal browser", "158.69.55.82", "/", True),
        ("Mozilla/5.0 normal browser", "158.69.55.255", "/", True),
        ("Mozilla/5.0 normal browser", "158.69.54.255", "/", False),
        ("Mozilla/5.0 normal browser", "158.69.56.0", "/", False),
    ]

    def test_residual_ip_ranges_python_matches_sql(self):
        for user_agent, ip, path, expected in self.RESIDUAL_IP_CASES:
            with self.subTest(ip=ip):
                python_result = (
                    analytics._is_bot_user_agent(user_agent or "")
                    or analytics._is_bot_ip(ip or "")
                    or analytics._is_scan_path(path or "")
                )
                sql_result = _sql_is_bot_page_view(user_agent, ip, path)
                self.assertEqual(
                    python_result,
                    sql_result,
                    f"Python/SQL不一致: ua={user_agent!r} ip={ip!r} path={path!r}",
                )
                self.assertEqual(
                    python_result,
                    expected,
                    f"期待値={expected} Python判定={python_result}: ip={ip!r}",
                )

    def test_sql_ip_cidrs_include_residual_cloud_ranges(self):
        sql_cidrs = set(_sql_ip_cidrs())
        for cidr in (
            "35.185.159.0/24",
            "34.78.15.0/24",
            "20.104.81.0/24",
            "170.64.159.0/24",
            "158.69.55.0/24",
        ):
            with self.subTest(cidr=cidr):
                self.assertIn(cidr, sql_cidrs)

    def test_sql_ip_cidrs_match_python_bot_ip_ranges_residual(self):
        """SQL側CIDRセットとPython側 _BOT_IP_RANGES が完全一致すること（残存5レンジ追加後も）。"""
        sql_cidrs = set(_sql_ip_cidrs())
        python_cidrs = {cidr for cidr, _comment in analytics._BOT_IP_RANGES}
        self.assertEqual(sql_cidrs, python_cidrs)


class ResidualBotFilterTests2026SepRound3(unittest.TestCase):
    """2026-09-05追加(3): 8/30スパイク残存266の内訳から特定したAI/SNSクローラーと/24ブロックのテスト。"""

    # ---- AI/SNSクローラーUA ----

    def test_perplexity_user_ua_is_bot(self):
        ua = "Mozilla/5.0 (compatible; Perplexity-User/1.0; +https://www.perplexity.ai/)"
        self.assertTrue(analytics._is_bot_user_agent(ua))

    def test_claude_user_ua_is_bot(self):
        ua = "Mozilla/5.0 (compatible; Claude-User/1.0; +https://www.anthropic.com/)"
        self.assertTrue(analytics._is_bot_user_agent(ua))

    def test_facebook_external_hit_ua_is_bot(self):
        ua = "facebookexternalhit/1.1 (+http://www.facebook.com/externalhit_uatext.php)"
        self.assertTrue(analytics._is_bot_user_agent(ua))

    def test_whatsapp_crawler_ua_is_bot(self):
        ua = "WhatsApp/10.0.2.1"
        self.assertTrue(analytics._is_bot_user_agent(ua))

    def test_wordpress_checker_ua_is_bot(self):
        ua = "WordPressChecker/1.0"
        self.assertTrue(analytics._is_bot_user_agent(ua))

    # ---- 実ユーザー可能性のあるUAはブロックしない ----

    def test_iphone_ios_17_5_safari_is_not_bot(self):
        ua = (
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 "
            "Mobile/15E148 Safari/604.1"
        )
        self.assertFalse(analytics._is_bot_user_agent(ua))

    def test_mac_safari_17_2_is_not_bot(self):
        ua = (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_2_1) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 "
            "Safari/605.1.15"
        )
        self.assertFalse(analytics._is_bot_user_agent(ua))

    # ---- 45.148.10.0/24: 複数UAローテーションボット ----

    def test_rotator_45_148_10_first_addr_is_bot(self):
        self.assertTrue(analytics._is_bot_ip("45.148.10.0"))

    def test_rotator_45_148_10_middle_addr_is_bot(self):
        self.assertTrue(analytics._is_bot_ip("45.148.10.62"))

    def test_rotator_45_148_10_last_addr_is_bot(self):
        self.assertTrue(analytics._is_bot_ip("45.148.10.255"))

    def test_just_below_45_148_10_is_not_bot(self):
        self.assertFalse(analytics._is_bot_ip("45.148.9.255"))

    def test_just_above_45_148_10_is_not_bot(self):
        self.assertFalse(analytics._is_bot_ip("45.148.11.0"))

    # ---- 37.66.170.0/24: 複数UAローテーションボット ----

    def test_rotator_37_66_170_first_addr_is_bot(self):
        self.assertTrue(analytics._is_bot_ip("37.66.170.0"))

    def test_rotator_37_66_170_middle_addr_is_bot(self):
        self.assertTrue(analytics._is_bot_ip("37.66.170.56"))

    def test_rotator_37_66_170_last_addr_is_bot(self):
        self.assertTrue(analytics._is_bot_ip("37.66.170.255"))

    def test_just_below_37_66_170_is_not_bot(self):
        self.assertFalse(analytics._is_bot_ip("37.66.169.255"))

    def test_just_above_37_66_170_is_not_bot(self):
        self.assertFalse(analytics._is_bot_ip("37.66.171.0"))

    # ---- 150.109.119.0/24: Tencent Mobile Safari偽装ボットの別IP ----

    def test_tencent_150_109_119_first_addr_is_bot(self):
        self.assertTrue(analytics._is_bot_ip("150.109.119.0"))

    def test_tencent_150_109_119_middle_addr_is_bot(self):
        self.assertTrue(analytics._is_bot_ip("150.109.119.38"))

    def test_tencent_150_109_119_last_addr_is_bot(self):
        self.assertTrue(analytics._is_bot_ip("150.109.119.255"))

    def test_just_below_150_109_119_is_not_bot(self):
        self.assertFalse(analytics._is_bot_ip("150.109.118.255"))

    def test_just_above_150_109_119_is_not_bot(self):
        self.assertFalse(analytics._is_bot_ip("150.109.120.0"))

    # ---- 組み合わせ：UA偽装 + 新規bot IP ----

    def test_spoofed_ios_ua_from_150_109_119_is_bot(self):
        spoofed_ua = (
            "Mozilla/5.0 (iPhone; CPU iPhone OS 13_2_3 like Mac OS X) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 Safari/13.0.3"
        )
        self.assertFalse(analytics._is_bot_user_agent(spoofed_ua))
        self.assertTrue(analytics._is_bot_ip("150.109.119.38"))

    def test_spoofed_mac_chrome_from_45_148_10_is_bot(self):
        spoofed_ua = (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36"
        )
        self.assertFalse(analytics._is_bot_user_agent(spoofed_ua))
        self.assertTrue(analytics._is_bot_ip("45.148.10.62"))


class ResidualBotFilterSqlEquivalenceTests2026SepRound3(unittest.TestCase):
    """2026-09-05追加(3)のUA/IPについてSQL/Python等価性テスト。"""

    NEW_CASES = [
        # AI/SNSクローラーUA
        ("Mozilla/5.0 (compatible; Perplexity-User/1.0)", "1.2.3.4", "/", True),
        ("Mozilla/5.0 (compatible; Claude-User/1.0)", "1.2.3.4", "/", True),
        ("facebookexternalhit/1.1", "1.2.3.4", "/", True),
        ("WhatsApp/10.0.2.1", "1.2.3.4", "/", True),
        ("WordPressChecker/1.0", "1.2.3.4", "/", True),
        # 実ユーザー可能性のあるUAはブロックしない
        (
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 "
            "Mobile/15E148 Safari/604.1",
            "126.0.0.1",
            "/",
            False,
        ),
        (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_2_1) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 "
            "Safari/605.1.15",
            "126.0.0.1",
            "/",
            False,
        ),
        # 新規/24 IPレンジ
        ("Mozilla/5.0 normal browser", "45.148.10.62", "/", True),
        ("Mozilla/5.0 normal browser", "45.148.10.255", "/", True),
        ("Mozilla/5.0 normal browser", "45.148.9.255", "/", False),
        ("Mozilla/5.0 normal browser", "45.148.11.0", "/", False),
        ("Mozilla/5.0 normal browser", "37.66.170.56", "/", True),
        ("Mozilla/5.0 normal browser", "37.66.170.255", "/", True),
        ("Mozilla/5.0 normal browser", "37.66.169.255", "/", False),
        ("Mozilla/5.0 normal browser", "37.66.171.0", "/", False),
        ("Mozilla/5.0 normal browser", "150.109.119.38", "/", True),
        ("Mozilla/5.0 normal browser", "150.109.119.255", "/", True),
        ("Mozilla/5.0 normal browser", "150.109.118.255", "/", False),
        ("Mozilla/5.0 normal browser", "150.109.120.0", "/", False),
        # 組み合わせ
        (
            "Mozilla/5.0 (iPhone; CPU iPhone OS 13_2_3 like Mac OS X) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 Safari/13.0.3",
            "150.109.119.38",
            "/",
            True,
        ),
    ]

    def test_new_residual_patterns_python_matches_sql(self):
        for user_agent, ip, path, expected in self.NEW_CASES:
            with self.subTest(ua=user_agent, ip=ip, path=path):
                python_result = (
                    analytics._is_bot_user_agent(user_agent or "")
                    or analytics._is_bot_ip(ip or "")
                    or analytics._is_scan_path(path or "")
                )
                sql_result = _sql_is_bot_page_view(user_agent, ip, path)
                self.assertEqual(
                    python_result,
                    sql_result,
                    f"Python/SQL不一致: ua={user_agent!r} ip={ip!r} path={path!r}",
                )
                self.assertEqual(
                    python_result,
                    expected,
                    f"期待値={expected} Python判定={python_result}: "
                    f"ua={user_agent!r} ip={ip!r} path={path!r}",
                )

    def test_sql_ip_cidrs_include_new_residual_ranges(self):
        sql_cidrs = set(_sql_ip_cidrs())
        for cidr in ("45.148.10.0/24", "37.66.170.0/24", "150.109.119.0/24"):
            with self.subTest(cidr=cidr):
                self.assertIn(cidr, sql_cidrs)

    def test_sql_ip_cidrs_match_python_bot_ip_ranges_round3(self):
        """SQL側CIDRセットとPython側 _BOT_IP_RANGES が完全一致すること（追加3レンジ後も）。"""
        sql_cidrs = set(_sql_ip_cidrs())
        python_cidrs = {cidr for cidr, _comment in analytics._BOT_IP_RANGES}
        self.assertEqual(sql_cidrs, python_cidrs)


class BotFilterTests2026Sep09(unittest.TestCase):
    """2026-09-09追加フィルタのテスト（PHPスキャンパス / Agency UA / 新規IPレンジ）。"""

    # ---- Agency UA ----

    def test_agency_ua_is_bot(self):
        ua = "Agency 93.8.2357"
        self.assertTrue(analytics._is_bot_user_agent(ua))

    def test_agency_ua_case_insensitive_is_bot(self):
        ua = "Mozilla/5.0 (compatible; AGENCY/1.0)"
        self.assertTrue(analytics._is_bot_user_agent(ua))

    def test_regular_browser_without_agency_is_not_bot(self):
        ua = (
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 "
            "Mobile/15E148 Safari/604.1"
        )
        self.assertFalse(analytics._is_bot_user_agent(ua))

    # ---- .php スキャンパス ----

    def test_shell_php_is_scan_path(self):
        self.assertTrue(analytics._is_scan_path("/shell.php"))

    def test_admin_php_is_scan_path(self):
        self.assertTrue(analytics._is_scan_path("/admin.php"))

    def test_storage_index_php_is_scan_path(self):
        self.assertTrue(analytics._is_scan_path("/storage/index.php"))

    def test_php_case_insensitive_is_scan_path(self):
        self.assertTrue(analytics._is_scan_path("/shell.PHP"))

    def test_normal_path_containing_php_not_blocked(self):
        # .php で終わらなければ誤検知しない
        self.assertFalse(analytics._is_scan_path("/blog/php-tutorial"))

    def test_normal_blog_path_not_blocked(self):
        self.assertFalse(analytics._is_scan_path("/blog/youtube-cpm-rpm-calculation-guide"))

    # ---- Vultr Japan 167.179.69.0/24 ----

    def test_vultr_japan_scanner_ip_is_bot(self):
        self.assertTrue(analytics._is_bot_ip("167.179.69.76"))

    def test_vultr_japan_network_first_is_bot(self):
        self.assertTrue(analytics._is_bot_ip("167.179.69.0"))

    def test_vultr_japan_network_last_is_bot(self):
        self.assertTrue(analytics._is_bot_ip("167.179.69.255"))

    def test_just_below_vultr_japan_is_not_bot(self):
        self.assertFalse(analytics._is_bot_ip("167.179.68.255"))

    def test_just_above_vultr_japan_is_not_bot(self):
        self.assertFalse(analytics._is_bot_ip("167.179.70.0"))

    # ---- Tencent Cloud 82.156.0.0/15 ----

    def test_tencent_82_156_spoofed_ip_is_bot(self):
        self.assertTrue(analytics._is_bot_ip("82.156.88.97"))

    def test_tencent_82_156_first_is_bot(self):
        self.assertTrue(analytics._is_bot_ip("82.156.0.0"))

    def test_tencent_82_157_last_is_bot(self):
        # 82.156.0.0/15 = 82.156.0.0 〜 82.157.255.255
        self.assertTrue(analytics._is_bot_ip("82.157.255.255"))

    def test_just_below_tencent_82_156_is_not_bot(self):
        self.assertFalse(analytics._is_bot_ip("82.155.255.255"))

    def test_just_above_tencent_82_157_is_not_bot(self):
        self.assertFalse(analytics._is_bot_ip("82.158.0.0"))

    # ---- Tencent Cloud 119.45.0.0/16 ----

    def test_tencent_119_45_spoofed_ip_is_bot(self):
        self.assertTrue(analytics._is_bot_ip("119.45.7.86"))

    def test_tencent_119_45_first_is_bot(self):
        self.assertTrue(analytics._is_bot_ip("119.45.0.0"))

    def test_tencent_119_45_last_is_bot(self):
        self.assertTrue(analytics._is_bot_ip("119.45.255.255"))

    def test_just_below_tencent_119_45_is_not_bot(self):
        self.assertFalse(analytics._is_bot_ip("119.44.255.255"))

    def test_just_above_tencent_119_45_is_not_bot(self):
        self.assertFalse(analytics._is_bot_ip("119.46.0.0"))

    # ---- Google Cloud 34.26.102.0/24 ----

    def test_google_cloud_34_26_102_is_bot(self):
        self.assertTrue(analytics._is_bot_ip("34.26.102.1"))

    def test_google_cloud_34_26_102_last_is_bot(self):
        self.assertTrue(analytics._is_bot_ip("34.26.102.255"))

    def test_just_outside_google_cloud_34_26_102_is_not_bot(self):
        self.assertFalse(analytics._is_bot_ip("34.26.103.0"))

    # ---- DigitalOcean 137.184.227.0/24 ----

    def test_digitalocean_137_184_227_is_bot(self):
        self.assertTrue(analytics._is_bot_ip("137.184.227.1"))

    def test_digitalocean_137_184_227_last_is_bot(self):
        self.assertTrue(analytics._is_bot_ip("137.184.227.255"))

    def test_just_outside_digitalocean_137_184_227_is_not_bot(self):
        self.assertFalse(analytics._is_bot_ip("137.184.228.0"))

    # ---- DigitalOcean Netherlands 188.166.67.0/24 ----

    def test_digitalocean_188_166_67_is_bot(self):
        self.assertTrue(analytics._is_bot_ip("188.166.67.1"))

    def test_digitalocean_188_166_67_last_is_bot(self):
        self.assertTrue(analytics._is_bot_ip("188.166.67.255"))

    def test_just_outside_digitalocean_188_166_67_is_not_bot(self):
        self.assertFalse(analytics._is_bot_ip("188.166.68.0"))

    # ---- Microsoft Azure 20.172.36.0/24 ----

    def test_azure_20_172_36_is_bot(self):
        self.assertTrue(analytics._is_bot_ip("20.172.36.1"))

    def test_azure_20_172_36_last_is_bot(self):
        self.assertTrue(analytics._is_bot_ip("20.172.36.255"))

    def test_just_outside_azure_20_172_36_is_not_bot(self):
        self.assertFalse(analytics._is_bot_ip("20.172.37.0"))

    # ---- Scaleway? France 51.15.215.0/24 ----

    def test_scaleway_france_51_15_215_is_bot(self):
        self.assertTrue(analytics._is_bot_ip("51.15.215.1"))

    def test_scaleway_france_51_15_215_last_is_bot(self):
        self.assertTrue(analytics._is_bot_ip("51.15.215.255"))

    def test_just_outside_scaleway_france_51_15_215_is_not_bot(self):
        self.assertFalse(analytics._is_bot_ip("51.15.216.0"))

    # ---- US Other/Other 66.132.186.0/24 ----

    def test_us_66_132_186_is_bot(self):
        self.assertTrue(analytics._is_bot_ip("66.132.186.1"))

    def test_us_66_132_186_last_is_bot(self):
        self.assertTrue(analytics._is_bot_ip("66.132.186.255"))

    def test_just_outside_us_66_132_186_is_not_bot(self):
        self.assertFalse(analytics._is_bot_ip("66.132.187.0"))

    # ---- Hong Kong Other/Other 199.45.155.0/24 ----

    def test_hong_kong_199_45_155_is_bot(self):
        self.assertTrue(analytics._is_bot_ip("199.45.155.1"))

    def test_hong_kong_199_45_155_last_is_bot(self):
        self.assertTrue(analytics._is_bot_ip("199.45.155.255"))

    def test_just_outside_hong_kong_199_45_155_is_not_bot(self):
        self.assertFalse(analytics._is_bot_ip("199.45.156.0"))

    # ---- 組み合わせ：PHPスキャン + Vultr IP ----

    def test_php_scan_from_vultr_japan_is_bot(self):
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        self.assertFalse(analytics._is_bot_user_agent(ua))
        self.assertTrue(analytics._is_scan_path("/ws83.php"))
        self.assertTrue(analytics._is_bot_ip("167.179.69.76"))

    # ---- 組み合わせ：Tencent偽装UA + 新規Tencent IP ----

    def test_spoofed_mobile_safari_from_tencent_82_156_is_bot(self):
        spoofed_ua = (
            "Mozilla/5.0 (iPhone; CPU iPhone OS 13_2_3 like Mac OS X) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 Safari/13.0.3"
        )
        self.assertFalse(analytics._is_bot_user_agent(spoofed_ua))
        self.assertTrue(analytics._is_bot_ip("82.156.88.97"))

    def test_spoofed_mobile_safari_from_tencent_119_45_is_bot(self):
        spoofed_ua = (
            "Mozilla/5.0 (iPhone; CPU iPhone OS 13_2_3 like Mac OS X) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 Safari/13.0.3"
        )
        self.assertFalse(analytics._is_bot_user_agent(spoofed_ua))
        self.assertTrue(analytics._is_bot_ip("119.45.7.86"))


class BotFilterSqlEquivalenceTests2026Sep09(unittest.TestCase):
    """2026-09-09追加パターンのSQL/Python等価性テスト。"""

    NEW_CASES = [
        # Agency UA
        ("Agency 93.8.2357", "1.2.3.4", "/", True),
        ("Mozilla/5.0 (compatible; AGENCY/1.0)", "1.2.3.4", "/", True),
        # .php パス
        ("Mozilla/5.0 normal browser", "126.0.0.1", "/shell.php", True),
        ("Mozilla/5.0 normal browser", "126.0.0.1", "/admin.php", True),
        ("Mozilla/5.0 normal browser", "126.0.0.1", "/storage/index.php", True),
        ("Mozilla/5.0 normal browser", "126.0.0.1", "/shell.PHP", True),
        ("Mozilla/5.0 normal browser", "126.0.0.1", "/blog/php-tutorial", False),
        # 新規IPレンジ
        ("Mozilla/5.0 normal browser", "167.179.69.76", "/", True),
        ("Mozilla/5.0 normal browser", "167.179.69.0", "/", True),
        ("Mozilla/5.0 normal browser", "167.179.69.255", "/", True),
        ("Mozilla/5.0 normal browser", "167.179.68.255", "/", False),
        ("Mozilla/5.0 normal browser", "167.179.70.0", "/", False),
        ("Mozilla/5.0 normal browser", "82.156.88.97", "/", True),
        ("Mozilla/5.0 normal browser", "82.156.0.0", "/", True),
        ("Mozilla/5.0 normal browser", "82.157.255.255", "/", True),
        ("Mozilla/5.0 normal browser", "82.155.255.255", "/", False),
        ("Mozilla/5.0 normal browser", "82.158.0.0", "/", False),
        ("Mozilla/5.0 normal browser", "119.45.7.86", "/", True),
        ("Mozilla/5.0 normal browser", "119.45.0.0", "/", True),
        ("Mozilla/5.0 normal browser", "119.45.255.255", "/", True),
        ("Mozilla/5.0 normal browser", "119.44.255.255", "/", False),
        ("Mozilla/5.0 normal browser", "119.46.0.0", "/", False),
        ("Mozilla/5.0 normal browser", "34.26.102.1", "/", True),
        ("Mozilla/5.0 normal browser", "34.26.102.255", "/", True),
        ("Mozilla/5.0 normal browser", "34.26.103.0", "/", False),
        ("Mozilla/5.0 normal browser", "137.184.227.1", "/", True),
        ("Mozilla/5.0 normal browser", "137.184.227.255", "/", True),
        ("Mozilla/5.0 normal browser", "137.184.228.0", "/", False),
        ("Mozilla/5.0 normal browser", "188.166.67.1", "/", True),
        ("Mozilla/5.0 normal browser", "188.166.67.255", "/", True),
        ("Mozilla/5.0 normal browser", "188.166.68.0", "/", False),
        ("Mozilla/5.0 normal browser", "20.172.36.1", "/", True),
        ("Mozilla/5.0 normal browser", "20.172.36.255", "/", True),
        ("Mozilla/5.0 normal browser", "20.172.37.0", "/", False),
        ("Mozilla/5.0 normal browser", "51.15.215.1", "/", True),
        ("Mozilla/5.0 normal browser", "51.15.215.255", "/", True),
        ("Mozilla/5.0 normal browser", "51.15.216.0", "/", False),
        ("Mozilla/5.0 normal browser", "66.132.186.1", "/", True),
        ("Mozilla/5.0 normal browser", "66.132.186.255", "/", True),
        ("Mozilla/5.0 normal browser", "66.132.187.0", "/", False),
        ("Mozilla/5.0 normal browser", "199.45.155.1", "/", True),
        ("Mozilla/5.0 normal browser", "199.45.155.255", "/", True),
        ("Mozilla/5.0 normal browser", "199.45.156.0", "/", False),
    ]

    def test_new_patterns_python_matches_sql(self):
        for user_agent, ip, path, expected in self.NEW_CASES:
            with self.subTest(ua=user_agent, ip=ip, path=path):
                python_result = (
                    analytics._is_bot_user_agent(user_agent or "")
                    or analytics._is_bot_ip(ip or "")
                    or analytics._is_scan_path(path or "")
                )
                sql_result = _sql_is_bot_page_view(user_agent, ip, path)
                self.assertEqual(
                    python_result,
                    sql_result,
                    f"Python/SQL不一致: ua={user_agent!r} ip={ip!r} path={path!r}",
                )
                self.assertEqual(
                    python_result,
                    expected,
                    f"期待値={expected} Python判定={python_result}: "
                    f"ua={user_agent!r} ip={ip!r} path={path!r}",
                )

    def test_sql_scan_path_suffixes_include_php(self):
        sql_raw = _sql_scan_path_suffixes()
        sql_suffixes = {s.lstrip("%") for s in sql_raw}
        self.assertIn(".php", sql_suffixes)

    def test_sql_ip_cidrs_include_new_ranges(self):
        sql_cidrs = set(_sql_ip_cidrs())
        for cidr in (
            "167.179.69.0/24",
            "82.156.0.0/15",
            "119.45.0.0/16",
            "34.26.102.0/24",
            "137.184.227.0/24",
            "188.166.67.0/24",
            "20.172.36.0/24",
            "51.15.215.0/24",
            "66.132.186.0/24",
            "199.45.155.0/24",
        ):
            with self.subTest(cidr=cidr):
                self.assertIn(cidr, sql_cidrs)

    def test_sql_ip_cidrs_match_python_bot_ip_ranges_sep09(self):
        """SQL側CIDRセットとPython側 _BOT_IP_RANGES が完全一致すること（2026-09-09追加後も）。"""
        sql_cidrs = set(_sql_ip_cidrs())
        python_cidrs = {cidr for cidr, _comment in analytics._BOT_IP_RANGES}
        self.assertEqual(sql_cidrs, python_cidrs)


if __name__ == "__main__":
    unittest.main()
