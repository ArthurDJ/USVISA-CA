"""
test.py — 项目功能测试与诊断工具
test.py — Project functional tests and diagnostics.

运行方式 / Usage:
  python test.py                  # 运行全部测试 / Run all tests
  python test.py EmailTest        # 只运行邮件测试 / Run email tests only
  python test.py SettingsTest     # 只运行配置校验 / Run settings validation only
  python test.py RequestTrackerTest
"""

import sys
# Windows 控制台强制 UTF-8 输出，避免中文乱码
# Force UTF-8 output on Windows to handle Chinese characters
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8")

import smtplib
import sys
import time
import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# 预先 mock 重型依赖（selenium / requests），使测试可在未安装完整依赖时运行
# Pre-mock heavy dependencies so tests run without the full install
# ---------------------------------------------------------------------------
for _mod in [
    "selenium", "selenium.webdriver", "selenium.webdriver.chrome",
    "selenium.webdriver.chrome.webdriver", "selenium.webdriver.common",
    "selenium.webdriver.common.by", "selenium.webdriver.support",
    "selenium.webdriver.support.expected_conditions",
    "selenium.webdriver.support.ui",
    "requests",
]:
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()


# ---------------------------------------------------------------------------
# 辅助：带颜色的控制台输出 / Helper: coloured console output
# ---------------------------------------------------------------------------
class _C:
    OK   = "\033[92m"
    WARN = "\033[93m"
    ERR  = "\033[91m"
    BOLD = "\033[1m"
    END  = "\033[0m"

def _ok(msg):   print(f"  {_C.OK}✔  {msg}{_C.END}")
def _warn(msg): print(f"  {_C.WARN}⚠  {msg}{_C.END}")
def _err(msg):  print(f"  {_C.ERR}✘  {msg}{_C.END}")


# ===========================================================================
# 1. 配置项校验 / Settings validation
# ===========================================================================
class SettingsTest(unittest.TestCase):
    """校验 .env 中所有必填项均已正确加载。
    Validate that all required .env values are loaded correctly."""

    @classmethod
    def setUpClass(cls):
        print(f"\n{_C.BOLD}=== SettingsTest — .env 配置校验 ==={_C.END}")
        try:
            import settings as s
            cls.s = s
        except ModuleNotFoundError as e:
            raise unittest.SkipTest(
                f"缺少依赖，跳过 / Missing dependency, skipping: {e}\n"
                "  请运行 / Run: pip install python-dotenv"
            )

    def test_account_credentials_present(self):
        """账户邮箱和密码必须存在。/ USER_EMAIL and USER_PASSWORD must be set."""
        self.assertTrue(self.s.USER_EMAIL,    "USER_EMAIL 未设置 / USER_EMAIL is not set")
        self.assertTrue(self.s.USER_PASSWORD, "USER_PASSWORD 未设置 / USER_PASSWORD is not set")
        _ok(f"USER_EMAIL: {self.s.USER_EMAIL}")

    def test_date_range_format(self):
        """日期格式必须为 YYYY-MM-DD。/ Dates must follow YYYY-MM-DD format."""
        for var, val in [
            ("EARLIEST_ACCEPTABLE_DATE", self.s.EARLIEST_ACCEPTABLE_DATE),
            ("LATEST_ACCEPTABLE_DATE",   self.s.LATEST_ACCEPTABLE_DATE),
        ]:
            self.assertIsNotNone(val, f"{var} 未设置 / {var} is not set")
            try:
                datetime.strptime(val, "%Y-%m-%d")
                _ok(f"{var}: {val}")
            except ValueError:
                self.fail(f"{var} 格式错误 / Invalid format: {val!r} (expected YYYY-MM-DD)")

    def test_date_range_order(self):
        """最早日期必须早于最晚日期。/ Earliest date must be before latest date."""
        earliest = datetime.strptime(self.s.EARLIEST_ACCEPTABLE_DATE, "%Y-%m-%d").date()
        latest   = datetime.strptime(self.s.LATEST_ACCEPTABLE_DATE,   "%Y-%m-%d").date()
        self.assertLess(earliest, latest,
            f"EARLIEST ({earliest}) 必须早于 LATEST ({latest}) / EARLIEST must be before LATEST")
        _ok(f"日期范围有效 / Date range valid: {earliest} ~ {latest}")

    def test_consulate_valid(self):
        """领事馆必须是支持的城市。/ Consulate must be a supported city."""
        self.assertIn(self.s.USER_CONSULATE, self.s.CONSULATES,
            f"USER_CONSULATE={self.s.USER_CONSULATE!r} 不在支持列表中 / not in supported list: {list(self.s.CONSULATES)}")
        _ok(f"USER_CONSULATE: {self.s.USER_CONSULATE} (ID={self.s.CONSULATES[self.s.USER_CONSULATE]})")

    def test_email_config_present(self):
        """邮件配置必须完整。/ Email configuration must be complete."""
        fields = {
            "GMAIL_EMAIL":           self.s.GMAIL_EMAIL,
            "GMAIL_APPLICATION_PWD": self.s.GMAIL_APPLICATION_PWD,
            "RECEIVER_EMAIL":        self.s.RECEIVER_EMAIL,
        }
        for name, val in fields.items():
            self.assertTrue(val, f"{name} 未设置 / {name} is not set")
            _ok(f"{name}: {val[:4]}{'*' * max(0, len(val) - 4)}")

    def test_feature_toggles_type(self):
        """功能开关必须是布尔值。/ Feature toggles must be booleans."""
        for name, val in [
            ("ENABLE_DATE_QUERY",        self.s.ENABLE_DATE_QUERY),
            ("ENABLE_EMAIL_NOTIFICATION",self.s.ENABLE_EMAIL_NOTIFICATION),
            ("ENABLE_AUTO_RESCHEDULE",   self.s.ENABLE_AUTO_RESCHEDULE),
        ]:
            self.assertIsInstance(val, bool, f"{name} 不是布尔值 / {name} is not bool: {val!r}")
            _ok(f"{name}: {val}")

    def test_numeric_params_positive(self):
        """数值型运行参数必须为正整数。/ Numeric runtime params must be positive integers."""
        params = {
            "TIMEOUT":                   self.s.TIMEOUT,
            "FAIL_RETRY_DELAY":          self.s.FAIL_RETRY_DELAY,
            "DATE_REQUEST_DELAY":        self.s.DATE_REQUEST_DELAY,
            "DATE_REQUEST_MAX_RETRY":    self.s.DATE_REQUEST_MAX_RETRY,
            "DATE_REQUEST_MAX_TIME":     self.s.DATE_REQUEST_MAX_TIME,
            "NEW_SESSION_AFTER_FAILURES":self.s.NEW_SESSION_AFTER_FAILURES,
            "NEW_SESSION_DELAY":         self.s.NEW_SESSION_DELAY,
        }
        for name, val in params.items():
            self.assertIsInstance(val, int, f"{name} 不是整数 / {name} is not int: {val!r}")
            self.assertGreater(val, 0,      f"{name} 必须大于 0 / {name} must be > 0: {val}")
            _ok(f"{name}: {val}")


# ===========================================================================
# 2. 邮件功能测试 / Email tests
# ===========================================================================
class EmailTest(unittest.TestCase):
    """诊断并测试 Gmail SMTP 邮件发送。
    Diagnose and test Gmail SMTP sending."""

    @classmethod
    def setUpClass(cls):
        print(f"\n{_C.BOLD}=== EmailTest — Gmail SMTP 诊断 ==={_C.END}")
        try:
            import settings as s
        except ModuleNotFoundError as e:
            raise unittest.SkipTest(
                f"缺少依赖，跳过 / Missing dependency, skipping: {e}\n"
                "  请运行 / Run: pip install python-dotenv"
            )
        cls.s = s
        cls.sender   = s.GMAIL_EMAIL
        cls.password = s.GMAIL_APPLICATION_PWD
        cls.receiver = f"{s.RECEIVER_NAME} <{s.RECEIVER_EMAIL}>"

    def test_01_credentials_not_empty(self):
        """邮件凭据不能为空。/ Email credentials must not be empty."""
        self.assertTrue(self.s.GMAIL_EMAIL,           "GMAIL_EMAIL 未设置 / not set")
        self.assertTrue(self.s.GMAIL_APPLICATION_PWD, "GMAIL_APPLICATION_PWD 未设置 / not set")
        _ok(f"Gmail 账户 / account: {self.s.GMAIL_EMAIL}")

    def test_02_app_password_format(self):
        """应用专用密码格式校验（通常为 16 位，可含空格）。
        App Password format check (typically 16 chars, may contain spaces)."""
        pwd_clean = self.s.GMAIL_APPLICATION_PWD.replace(" ", "")
        if len(pwd_clean) != 16:
            _warn(
                f"应用专用密码长度为 {len(pwd_clean)} 位（通常应为 16 位）/ "
                f"App Password length is {len(pwd_clean)} (expected 16). "
                f"请在 https://myaccount.google.com/apppasswords 重新生成 / "
                f"Regenerate at https://myaccount.google.com/apppasswords"
            )
        else:
            _ok(f"应用专用密码格式正确（16 位）/ App Password format OK (16 chars)")
        # 格式错误只警告，不断言失败，让后续连接测试给出准确错误
        # Only warn on format mismatch; let the connection test give the definitive verdict

    def test_03_smtp_connection(self):
        """测试 SMTP 服务器连接（不发送邮件）。
        Test SMTP server connection only — no email is sent."""
        print("  正在连接 smtp.gmail.com:587 / Connecting to smtp.gmail.com:587 ...")
        try:
            session = smtplib.SMTP("smtp.gmail.com", 587, timeout=10)
            session.ehlo()
            session.starttls()
            session.ehlo()
            session.quit()
            _ok("SMTP 连接成功 / SMTP connection OK")
        except Exception as e:
            self.fail(
                f"SMTP 连接失败 / SMTP connection failed: {e}\n"
                "  请检查网络或防火墙设置 / Check network or firewall settings"
            )

    def test_04_smtp_login(self):
        """测试 SMTP 登录（不发送邮件）。
        Test SMTP login only — no email is sent.

        常见失败原因 / Common failure reasons:
          535 5.7.8 — 应用专用密码错误或已过期，请在 Google 账户重新生成
                      App Password is wrong or expired — regenerate at Google Account settings
          534 5.7.9 — 需要应用专用密码，不能使用账户密码
                      An App Password is required; account password is not accepted
        """
        print("  正在验证 SMTP 凭据 / Authenticating SMTP credentials ...")
        try:
            session = smtplib.SMTP("smtp.gmail.com", 587, timeout=10)
            session.ehlo()
            session.starttls()
            session.ehlo()
            session.login(self.s.GMAIL_EMAIL, self.s.GMAIL_APPLICATION_PWD)
            session.quit()
            _ok("SMTP 登录成功 / SMTP login OK — credentials are valid")
        except smtplib.SMTPAuthenticationError as e:
            code = e.smtp_code
            hints = {
                535: (
                    "应用专用密码错误或已过期 / App Password is wrong or expired.\n"
                    "  → 访问 https://myaccount.google.com/apppasswords 重新生成\n"
                    "  → Visit https://myaccount.google.com/apppasswords to regenerate"
                ),
                534: (
                    "需要应用专用密码，不能使用账户密码 / App Password required, not account password.\n"
                    "  → 确保已开启两步验证并生成应用专用密码\n"
                    "  → Enable 2-Step Verification and create an App Password"
                ),
            }
            hint = hints.get(code, f"认证错误 / Auth error: {e}")
            self.fail(f"SMTP 登录失败 (code={code}) / SMTP login failed:\n  {hint}")
        except Exception as e:
            self.fail(f"SMTP 登录时发生意外错误 / Unexpected error during SMTP login: {e}")

    def test_05_send_real_email(self):
        """发送真实测试邮件（需要凭据有效）。
        Send a real test email — requires valid credentials.

        注意：此测试会真实发送邮件 / Note: this test actually sends an email.
        """
        from legacy.gmail import GMail, Message
        print(f"  发送测试邮件至 / Sending test email to: {self.receiver}")
        try:
            gmail = GMail(self.sender, self.password)
            msg = Message(
                subject=f"[测试] Gmail 邮件发送测试 / Email Send Test — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                to=self.receiver,
                text=(
                    f"这是一封测试邮件，用于验证 Gmail SMTP 配置是否正确。\n"
                    f"This is a test email to verify Gmail SMTP configuration.\n\n"
                    f"  发件账户  / Sender   : {self.s.GMAIL_EMAIL}\n"
                    f"  收件人    / Receiver : {self.s.RECEIVER_EMAIL}\n"
                    f"  发送时间  / Sent at  : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                ),
            )
            gmail.send(msg)
            gmail.close()
            _ok(f"测试邮件已发送 / Test email sent to {self.s.RECEIVER_EMAIL}")
        except smtplib.SMTPAuthenticationError as e:
            self.fail(
                f"邮件发送失败（认证错误）/ Send failed (auth error, code={e.smtp_code}).\n"
                "  请先确保 test_04_smtp_login 通过 / Ensure test_04_smtp_login passes first."
            )
        except Exception as e:
            self.fail(f"邮件发送失败 / Send failed: {e}")


# ===========================================================================
# 3. RequestTracker 单元测试 / RequestTracker unit tests
# ===========================================================================
class RequestTrackerTest(unittest.TestCase):
    """RequestTracker 类的单元测试。/ Unit tests for the RequestTracker class."""

    @classmethod
    def setUpClass(cls):
        print(f"\n{_C.BOLD}=== RequestTrackerTest — RequestTracker 单元测试 ==={_C.END}")
        from request_tracker import RequestTracker
        cls.RequestTracker = RequestTracker

    def test_initial_state(self):
        """初始状态：retries=0，should_retry=True。/ Initial state: retries=0, should_retry=True."""
        tracker = self.RequestTracker(max_retries=3, max_time=60)
        self.assertEqual(tracker.retries, 0)
        self.assertTrue(tracker.should_retry())
        _ok("初始状态正确 / Initial state correct")

    def test_retry_increments(self):
        """retry() 应使计数器加一。/ retry() should increment counter by one."""
        tracker = self.RequestTracker(max_retries=5, max_time=60)
        tracker.retry()
        tracker.retry()
        self.assertEqual(tracker.retries, 2)
        _ok("retry() 计数正确 / retry() count correct")

    def test_stops_after_max_retries(self):
        """超过最大重试次数后 should_retry 返回 False。
        should_retry returns False after max retries exceeded."""
        tracker = self.RequestTracker(max_retries=2, max_time=60)
        for _ in range(3):   # 超过 max_retries=2 / exceed max_retries=2
            tracker.retry()
        self.assertFalse(tracker.should_retry())
        _ok("超出最大重试次数后正确停止 / Correctly stops after max retries")

    def test_stops_after_max_time(self):
        """超过最长时间后 should_retry 返回 False。
        should_retry returns False after max time exceeded."""
        tracker = self.RequestTracker(max_retries=100, max_time=0.01)
        time.sleep(0.05)   # 等待超时 / Wait for timeout
        self.assertFalse(tracker.should_retry())
        _ok("超出最长时间后正确停止 / Correctly stops after max time")

    def test_within_limits_returns_true(self):
        """在限制范围内 should_retry 返回 True。/ Returns True while within limits."""
        tracker = self.RequestTracker(max_retries=10, max_time=60)
        tracker.retry()
        self.assertTrue(tracker.should_retry())
        _ok("限制范围内正确继续 / Correctly continues within limits")

    def test_log_retry_does_not_raise(self):
        """log_retry() 不应抛出异常。/ log_retry() must not raise."""
        tracker = self.RequestTracker(max_retries=5, max_time=60)
        try:
            tracker.log_retry()
            _ok("log_retry() 无异常 / log_retry() raised no exception")
        except Exception as e:
            self.fail(f"log_retry() 抛出异常 / log_retry() raised: {e}")


# ===========================================================================
# 4. _send_email 单元测试（Mock GMail）/ _send_email unit tests with mocked GMail
# ===========================================================================
class SendEmailTest(unittest.TestCase):
    """用 Mock 测试 _send_email 的开关控制逻辑（不实际发邮件）。
    Test _send_email toggle logic using mocks — no real email is sent."""

    @classmethod
    def setUpClass(cls):
        print(f"\n{_C.BOLD}=== SendEmailTest — _send_email 开关逻辑测试 ==={_C.END}")
        try:
            import settings  # noqa: F401 — ensure settings loads before reschedule
        except ModuleNotFoundError as e:
            raise unittest.SkipTest(
                f"缺少依赖，跳过 / Missing dependency, skipping: {e}\n"
                "  请运行 / Run: pip install python-dotenv"
            )

    def _run_send_email(self, enable_notification: bool, mandatory: bool):
        """执行 _send_email 并返回 GMail.send 被调用的次数。
        Run _send_email and return how many times GMail.send was called."""
        with patch("reschedule.ENABLE_EMAIL_NOTIFICATION", enable_notification), \
             patch("reschedule.GMail") as mock_gmail_cls, \
             patch("reschedule.Message"):
            mock_gmail_inst = MagicMock()
            mock_gmail_cls.return_value = mock_gmail_inst
            import reschedule
            reschedule._send_email("Test Subject", "Test Body", mandatory=mandatory)
            return mock_gmail_inst.send.call_count

    def test_notification_on_sends_when_enabled(self):
        """ENABLE_EMAIL_NOTIFICATION=True, mandatory=False → 应发送。/ Should send."""
        count = self._run_send_email(enable_notification=True, mandatory=False)
        self.assertEqual(count, 1)
        _ok("邮件开关=True, mandatory=False → 已发送 / Sent as expected")

    def test_notification_off_skips_when_not_mandatory(self):
        """ENABLE_EMAIL_NOTIFICATION=False, mandatory=False → 跳过。/ Should skip."""
        count = self._run_send_email(enable_notification=False, mandatory=False)
        self.assertEqual(count, 0)
        _ok("邮件开关=False, mandatory=False → 已跳过 / Skipped as expected")

    def test_mandatory_always_sends_regardless_of_toggle(self):
        """mandatory=True 时无论开关状态均发送。/ mandatory=True always sends."""
        count_off = self._run_send_email(enable_notification=False, mandatory=True)
        count_on  = self._run_send_email(enable_notification=True,  mandatory=True)
        self.assertEqual(count_off, 1, "邮件开关=False, mandatory=True → 应强制发送 / Should send")
        self.assertEqual(count_on,  1, "邮件开关=True,  mandatory=True → 应发送 / Should send")
        _ok("mandatory=True 时强制发送，不受开关控制 / mandatory=True always sends")


# ===========================================================================
# 入口 / Entry point
# ===========================================================================
if __name__ == "__main__":
    print(f"{_C.BOLD}{'=' * 60}")
    print("美国签证改期工具 — 功能测试与诊断")
    print("US Visa Rescheduler  — Functional Tests & Diagnostics")
    print(f"{'=' * 60}{_C.END}")

    # 按顺序运行：settings → email → tracker → send_email mock
    # Run in order: settings → email → tracker → send_email mock
    loader = unittest.TestLoader()
    suite  = unittest.TestSuite()
    for cls in [SettingsTest, EmailTest, RequestTrackerTest, SendEmailTest]:
        suite.addTests(loader.loadTestsFromTestCase(cls))

    runner = unittest.TextTestRunner(verbosity=0, failfast=False)
    result = runner.run(suite)

    print(f"\n{_C.BOLD}{'=' * 60}{_C.END}")
    total   = result.testsRun
    failures = len(result.failures) + len(result.errors)
    passed   = total - failures
    status   = _C.OK if failures == 0 else _C.ERR
    print(f"{status}{_C.BOLD}结果 / Result: {passed}/{total} 通过 passed{_C.END}")
    if failures:
        print(f"{_C.ERR}  {failures} 个测试失败，请查看上方错误详情 / {failures} test(s) failed — see details above{_C.END}")
    print(f"{_C.BOLD}{'=' * 60}{_C.END}\n")
