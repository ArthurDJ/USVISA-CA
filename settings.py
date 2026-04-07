"""
settings.py — 全局配置文件，所有参数均从 .env 读取
settings.py — Global configuration; all values are loaded from .env

使用方法 / Usage:
  复制 .env.example 为 .env，填入对应值后运行程序。
  Copy .env.example to .env, fill in your values, then run the program.
"""

from dotenv import load_dotenv
import os
from datetime import datetime

# 从 .env 文件加载环境变量 / Load environment variables from .env
load_dotenv()

# ===========================================================================
# 账户信息 / Account credentials
# ===========================================================================
USER_EMAIL       = os.getenv("USER_EMAIL")      # AIS 登录邮箱 / AIS login email
USER_PASSWORD    = os.getenv("USER_PASSWORD")   # AIS 登录密码 / AIS login password
NUM_PARTICIPANTS = int(os.getenv("NUM_PARTICIPANTS", "1"))  # 预约人数 / Number of applicants

# ===========================================================================
# 可接受的预约日期范围 / Acceptable appointment date window (YYYY-MM-DD)
# ===========================================================================
EARLIEST_ACCEPTABLE_DATE = os.getenv("EARLIEST_ACCEPTABLE_DATE")
LATEST_ACCEPTABLE_DATE   = os.getenv("LATEST_ACCEPTABLE_DATE")

# ===========================================================================
# 排除日期区间 / Exclusion date ranges
# 在可接受范围内但不希望预约的日期段（最多支持 9 段）
# Date sub-ranges within the acceptable window that should be skipped (up to 9)
# ===========================================================================
EXCLUSION_DATE_RANGES = []
if EARLIEST_ACCEPTABLE_DATE and LATEST_ACCEPTABLE_DATE:
    try:
        earliest_acceptable_date = datetime.strptime(EARLIEST_ACCEPTABLE_DATE, "%Y-%m-%d").date()
        latest_acceptable_date   = datetime.strptime(LATEST_ACCEPTABLE_DATE,   "%Y-%m-%d").date()

        for i in range(1, 10):  # 支持最多 9 段排除区间 / Support up to 9 exclusion ranges
            start = os.getenv(f"EXCLUSION_START_DATE_{i}")
            end   = os.getenv(f"EXCLUSION_END_DATE_{i}")
            if start and end:
                try:
                    exclusion_start_date = datetime.strptime(start, "%Y-%m-%d").date()
                    exclusion_end_date   = datetime.strptime(end,   "%Y-%m-%d").date()
                    # 仅在区间完全落在可接受范围内时才加入列表
                    # Only add if the exclusion range falls entirely within the acceptable window
                    if earliest_acceptable_date < exclusion_start_date < exclusion_end_date < latest_acceptable_date:
                        EXCLUSION_DATE_RANGES.append((start, end))
                except ValueError:
                    print(f"排除区间日期格式无效 / Invalid date format in exclusion range {start} to {end}")
    except ValueError:
        print("EARLIEST_ACCEPTABLE_DATE 或 LATEST_ACCEPTABLE_DATE 格式无效 / "
              "Invalid date format in EARLIEST_ACCEPTABLE_DATE or LATEST_ACCEPTABLE_DATE")

# ===========================================================================
# 领事馆配置 / Consulate configuration
# 仅 Toronto 和 Vancouver 经过验证 / Only Toronto and Vancouver are verified
# ===========================================================================
CONSULATES = {
    "Calgary":   89,
    "Halifax":   90,
    "Montreal":  91,
    "Ottawa":    92,
    "Quebec":    93,
    "Toronto":   94,
    "Vancouver": 95,
}
USER_CONSULATE = os.getenv("USER_CONSULATE")  # 从上方列表中选择城市 / Choose a city from the list above

# ===========================================================================
# Gmail 邮件通知配置 / Gmail notification configuration
# ===========================================================================
GMAIL_SENDER_NAME     = os.getenv("GMAIL_SENDER_NAME")      # 发件人显示名称 / Sender display name
GMAIL_EMAIL           = os.getenv("GMAIL_EMAIL")            # Gmail 地址 / Gmail address
GMAIL_APPLICATION_PWD = os.getenv("GMAIL_APPLICATION_PWD")  # Gmail 应用专用密码 / Gmail App Password
RECEIVER_NAME         = os.getenv("RECEIVER_NAME")          # 收件人名称 / Recipient name
RECEIVER_EMAIL        = os.getenv("RECEIVER_EMAIL")         # 收件人邮箱 / Recipient email

# ===========================================================================
# 界面与测试开关 / UI and test switches
# ===========================================================================
# 是否显示浏览器窗口（true=显示，false=无头模式）
# Whether to show the browser window (true=visible, false=headless)
SHOW_GUI  = os.getenv("SHOW_GUI",  "false").lower() == "true"

# 测试模式：程序正常运行但不点击最终确认按钮
# Test mode: program runs normally but does NOT click the final confirm button
TEST_MODE = os.getenv("TEST_MODE", "false").lower() == "true"

# ===========================================================================
# 功能开关 / Feature toggles
# ===========================================================================

# 开关 1：日期查询 / Toggle 1: Date query
ENABLE_DATE_QUERY = os.getenv("ENABLE_DATE_QUERY", "true").lower() == "true"

# 开关 2：邮件通知 / Toggle 2: Email notification
ENABLE_EMAIL_NOTIFICATION = os.getenv("ENABLE_EMAIL_NOTIFICATION", "true").lower() == "true"

# 开关 3：自动改期（双重确认，严格控制）/ Toggle 3: Auto-reschedule (strict double-confirmation)
# 必须同时满足：ENABLE_AUTO_RESCHEDULE=true 且 AUTO_RESCHEDULE_CONFIRM=CONFIRM
# Both must be set: ENABLE_AUTO_RESCHEDULE=true AND AUTO_RESCHEDULE_CONFIRM=CONFIRM
ENABLE_AUTO_RESCHEDULE = (
    os.getenv("ENABLE_AUTO_RESCHEDULE", "false").lower() == "true"
    and os.getenv("AUTO_RESCHEDULE_CONFIRM", "") == "CONFIRM"
)

# ===========================================================================
# 内部运行参数（非必要请勿修改）/ Internal runtime parameters (do not change unless you know what you are doing)
# ===========================================================================
DETACH                   = os.getenv("DETACH",                   "true").lower() == "true"
NEW_SESSION_AFTER_FAILURES = int(os.getenv("NEW_SESSION_AFTER_FAILURES", "5"))
NEW_SESSION_DELAY        = int(os.getenv("NEW_SESSION_DELAY",        "3000"))
TIMEOUT                  = int(os.getenv("TIMEOUT",                  "10"))
FAIL_RETRY_DELAY         = int(os.getenv("FAIL_RETRY_DELAY",         "180"))
DATE_REQUEST_DELAY       = int(os.getenv("DATE_REQUEST_DELAY",       "180"))
DATE_REQUEST_MAX_RETRY   = int(os.getenv("DATE_REQUEST_MAX_RETRY",   "5"))
DATE_REQUEST_MAX_TIME    = int(os.getenv("DATE_REQUEST_MAX_TIME",    "900"))

LOGIN_URL = "https://ais.usvisa-info.com/en-ca/niv/users/sign_in"
AVAILABLE_DATE_REQUEST_SUFFIX = f"/days/{CONSULATES[USER_CONSULATE]}.json?appointments[expedite]=false"
APPOINTMENT_PAGE_URL = "https://ais.usvisa-info.com/en-ca/niv/schedule/{id}/appointment"
PAYMENT_PAGE_URL     = "https://ais.usvisa-info.com/en-ca/niv/schedule/{id}/payment"

# API 请求头（标识为 AJAX 请求，避免被服务器拦截）
# Request headers (marks request as AJAX to avoid server-side blocking)
REQUEST_HEADERS = {
    "X-Requested-With": "XMLHttpRequest",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "en-US,en;q=0.9",
}
