"""
reschedule.py — 美国签证预约自动改期主程序
reschedule.py — Main driver for automated US visa appointment rescheduling.

流程概述 / Flow overview:
  1. 启动 Chrome，登录 AIS 预约系统，读取当前预约日期
     Launch Chrome, log in to AIS, read current appointment date
  2. 轮询可用预约日期，判断是否落在可接受范围内
     Poll available dates and check if they fall within the acceptable window
  3. 若开关允许，自动提交改期；改期成功后重新登录验证新日期，强制发送对比邮件
     If toggles allow, submit reschedule; on success re-login to verify, then send mandatory confirmation email
"""

import logging
import os
import re
import traceback
from datetime import datetime
import random
from time import sleep
from typing import Union, List

import requests
from selenium import webdriver
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from legacy.gmail import GMail, Message
from legacy_rescheduler import legacy_reschedule
from request_tracker import RequestTracker
from settings import *

# ---------------------------------------------------------------------------
# 日志配置 / Logging setup
# 同时输出到控制台和文件，文件按日期命名
# Output to both console and a date-stamped log file
# ---------------------------------------------------------------------------
os.makedirs("log", exist_ok=True)
_log_filename = f"log/reschedule_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.DEBUG,
    format="[%(asctime)s] %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(_log_filename, encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


def log_message(message: str) -> None:
    """向后兼容的日志包装。/ Backward-compatible wrapper."""
    logger.info(message)


# ---------------------------------------------------------------------------
# 浏览器初始化 / Browser initialisation
# ---------------------------------------------------------------------------

def get_chrome_driver() -> WebDriver:
    """创建并返回配置好的 Chrome WebDriver 实例。
    Create and return a configured Chrome WebDriver instance."""
    logger.debug("初始化 Chrome WebDriver / Initialising Chrome WebDriver")
    options = webdriver.ChromeOptions()

    if not SHOW_GUI:
        options.add_argument("headless")
        options.add_argument("window-size=1920x1080")
        options.add_argument("disable-gpu")
        options.add_argument(
            'user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
            'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36'
        )

    options.add_experimental_option("detach", DETACH)
    options.add_argument('--incognito')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument(f'--user-data-dir=/tmp/chrome-{datetime.now().strftime("%Y%m%d-%H%M%S")}')

    driver = webdriver.Chrome(options=options)
    logger.debug("Chrome WebDriver 启动成功 / Chrome WebDriver started")
    return driver


# ---------------------------------------------------------------------------
# 登录 / Login
# ---------------------------------------------------------------------------

def login(driver: WebDriver) -> None:
    """登录 AIS 签证预约系统。/ Log in to the AIS visa portal."""
    logger.info(f"正在登录账户 / Logging in: {USER_EMAIL}")
    driver.get(LOGIN_URL)
    timeout = TIMEOUT

    email_input = WebDriverWait(driver, timeout).until(
        EC.visibility_of_element_located((By.ID, "user_email"))
    )
    email_input.send_keys(USER_EMAIL)

    password_input = WebDriverWait(driver, timeout).until(
        EC.visibility_of_element_located((By.ID, "user_password"))
    )
    password_input.send_keys(USER_PASSWORD)

    policy_checkbox = WebDriverWait(driver, timeout).until(
        EC.element_to_be_clickable((By.CLASS_NAME, "icheckbox"))
    )
    policy_checkbox.click()

    login_button = WebDriverWait(driver, timeout).until(
        EC.element_to_be_clickable((By.NAME, "commit"))
    )
    login_button.click()
    logger.info("登录请求已提交 / Login submitted")


# ---------------------------------------------------------------------------
# 跳转预约页面 / Navigate to appointment page
# ---------------------------------------------------------------------------

def get_appointment_page(driver: WebDriver) -> None:
    """点击 Continue 并跳转预约管理页。
    Click Continue and navigate to the appointment management page."""
    logger.debug("等待 Continue 按钮 / Waiting for Continue button")
    timeout = TIMEOUT

    continue_button = WebDriverWait(driver, timeout).until(
        EC.element_to_be_clickable((By.LINK_TEXT, "Continue"))
    )
    continue_button.click()
    sleep(2)

    current_url = driver.current_url
    url_id = re.search(r"/(\d+)", current_url).group(1)
    appointment_url = APPOINTMENT_PAGE_URL.format(id=url_id)

    logger.info(f"跳转预约页面 / Navigating to: {appointment_url}")
    driver.get(appointment_url)


# ---------------------------------------------------------------------------
# 读取当前已预约信息 / Read current booked appointment info
# ---------------------------------------------------------------------------

def get_current_appointment_info(driver: WebDriver) -> dict:
    """从当前页面的 .consular-appt 区块读取预约信息（主页或预约页均可）。
    Read appointment info from the .consular-appt block on the current page
    (works on both the main dashboard and the appointment page).

    Returns:
        dict 包含 'date'、'time'、'location'、'delivery'，无法读取时值为 'N/A'。
        dict with 'date', 'time', 'location', 'delivery'; values are 'N/A' if unreadable.
    """
    info = {"date": "N/A", "time": "N/A", "location": "N/A", "delivery": "N/A"}
    try:
        # 尝试通过多种选择器定位预约区块 / Try multiple selectors for the appt section
        appt_section = None
        selectors = [
            (By.CLASS_NAME, "consular-appt"),
            (By.XPATH, "//h5[contains(text(), 'Consular Appointment')]/following-sibling::div"),
            (By.XPATH, "//p[contains(@class, 'consular-appt')]"),
            (By.XPATH, "//div[contains(@class, 'consular-appt')]")
        ]
        
        for by, val in selectors:
            try:
                appt_section = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((by, val))
                )
                if appt_section:
                    logger.debug(f"成功使用选择器定位到预约区块: {val}")
                    break
            except:
                continue

        if not appt_section:
            # 兜底：尝试获取整个页面的文本并解析 / Fallback: Parse whole page text
            page_text = driver.find_element(By.TAG_NAME, "body").text
            logger.debug("尝试从全页文本中提取预约信息...")
            # 匹配类似 "May 20, 2026, 08:30 Vancouver local time at Vancouver"
            full_match = re.search(r"(\w+\s+\d{1,2},\s+\d{4}),\s+(\d{1,2}:\d{2})\s+.*?at\s+(.*)", page_text)
            if full_match:
                info["date"] = full_match.group(1).strip()
                info["time"] = full_match.group(2).strip()
                info["location"] = full_match.group(3).splitlines()[0].strip()
                logger.info(f"成功从全页文本提取信息: {info}")
                return info
            raise Exception("未能定位到预约信息区块或匹配到文本")

        paragraphs = appt_section.find_elements(By.TAG_NAME, "p")
        if not paragraphs:
            # 某些页面结构可能直接在 div 内或使用其他标签 / Try direct text extraction
            section_text = appt_section.text.strip()
            logger.debug(f"区块原始内容 / Section raw text: {section_text}")
            paragraphs = [appt_section] # Treat the section itself as the carrier

        # ── 解析逻辑 ────────────────────
        for p in paragraphs:
            text = p.text.strip()
            if not text: continue
            logger.debug(f"正在解析段落文本: {text[:50]}...")

            # 匹配日期 / Match Date (e.g., 20 May, 2026 or May 20, 2026)
            date_match = re.search(r"\d{1,2}\s+\w+,\s+\d{4}|\w+\s+\d{1,2},\s+\d{4}", text)
            if date_match and info["date"] == "N/A":
                info["date"] = date_match.group(0)

            # 匹配时间 / Match Time (e.g., 08:30)
            time_match = re.search(r"\d{1,2}:\d{2}", text)
            if time_match and info["time"] == "N/A":
                info["time"] = time_match.group(0)

            # 匹配地点 / Match Location
            if " at " in text and info["location"] == "N/A":
                loc_match = re.search(r"\bat\s+(.+)$", text, re.IGNORECASE)
                if loc_match:
                    # 去除多余的 "— get directions" 等后缀
                    raw_loc = loc_match.group(1).splitlines()[0].strip()
                    info["location"] = raw_loc.split(" — ")[0].strip()

            # 匹配取件地址 / Match Delivery
            if ("Delivery" in text or "Location" in text) and info["delivery"] == "N/A" and "at" not in text.lower():
                lines = [ln.strip() for ln in text.splitlines() if ln.strip() and "Delivery Location" not in ln]
                if lines:
                    info["delivery"] = " | ".join(lines)

    except Exception as e:
        logger.warning(f"无法读取当前预约信息 / Could not read current appointment info: {e}")
        # 调试用：保存当前页面快照 / For debugging: save page source
        try:
            with open("log/failed_parsing_page.html", "w") as f:
                f.write(driver.page_source)
            logger.debug("已保存解析失败时的页面源码至 log/failed_parsing_page.html")
        except: pass

    logger.info(
        f"当前预约 / Current appointment: "
        f"日期={info['date']}, 时间={info['time']}, "
        f"地点={info['location']}, 取件={info['delivery']}"
    )
    return info


# ---------------------------------------------------------------------------
# 改期后重新登录验证 / Re-login to verify rescheduled appointment
# ---------------------------------------------------------------------------

def verify_rescheduled_appointment() -> dict:
    """改期成功后新建 session，重新登录并读取最新预约信息以验证结果。
    After a successful reschedule, open a fresh session, log in, and read the new appointment to verify.

    Returns:
        dict 包含 'date' 和 'time'，无法读取时值为 'N/A'。
        dict with 'date' and 'time'; values are 'N/A' if unreadable.
    """
    logger.info("重新登录以验证改期结果 / Re-logging in to verify reschedule result")
    driver = get_chrome_driver()
    verified_info = {"date": "N/A", "time": "N/A", "location": "N/A", "delivery": "N/A"}
    try:
        login(driver)
        # 主页面的 .consular-appt 已包含完整预约信息，无需跳转预约页面
        # Main page .consular-appt contains full info — no need to navigate to appointment page
        verified_info = get_current_appointment_info(driver)
        logger.info(
            f"验证结果 / Verified appointment: 日期={verified_info['date']}, 时间={verified_info['time']}, "
            f"地点={verified_info['location']}"
        )
    except Exception as e:
        logger.error(f"验证改期结果时出错 / Error during verification: {e}")
    finally:
        driver.quit()
    return verified_info


# ---------------------------------------------------------------------------
# 邮件发送辅助函数 / Email sending helper
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# 全局监控变量 / Global monitoring variables
# ---------------------------------------------------------------------------
MONITOR_STATE = {
    "start_time": datetime.now(),
    "last_email_time": None,
    "last_status": "Starting...",
    "email_history": []
}

def update_monitor(status: str = None, email_sent: bool = False, subject: str = None):
    """更新全局监控状态。"""
    if status:
        MONITOR_STATE["last_status"] = status
    if email_sent:
        now = datetime.now()
        MONITOR_STATE["last_email_time"] = now
        MONITOR_STATE["email_history"].append({
            "time": now.strftime("%Y-%m-%d %H:%M:%S"),
            "subject": subject
        })
        # 保持历史记录在最近 10 条
        if len(MONITOR_STATE["email_history"]) > 10:
            MONITOR_STATE["email_history"].pop(0)

def _send_email(subject: str, body: str, mandatory: bool = False) -> None:
    """发送 Gmail 通知邮件。
    Send a Gmail notification email.

    Args:
        subject:   邮件主题 / Email subject
        body:      邮件正文 / Email body
        mandatory: True 表示强制发送，忽略 ENABLE_EMAIL_NOTIFICATION 开关
                   True = always send regardless of ENABLE_EMAIL_NOTIFICATION toggle
    """
    if not mandatory and not ENABLE_EMAIL_NOTIFICATION:
        logger.debug(f"邮件通知已禁用，跳过 / Email notification disabled, skipping: {subject}")
        return

    logger.info(f"{'[强制]' if mandatory else ''} 发送邮件 / Sending email: {subject}")
    try:
        gmail = GMail(GMAIL_EMAIL, GMAIL_APPLICATION_PWD)
        # 支持多收件人 / Support multiple recipients
        recipients = [r.strip() for r in RECEIVER_EMAIL.split(',')]
        for recipient in recipients:
            msg = Message(subject, to=recipient, text=body)
            gmail.send(msg)
        gmail.close()
        logger.info("邮件发送成功 / Email sent successfully")
        update_monitor(email_sent=True, subject=subject)
    except Exception as e:
        logger.error(f"邮件发送失败 / Failed to send email: {e}")


# ---------------------------------------------------------------------------
# 查询可用日期 / Fetch available dates
# ---------------------------------------------------------------------------

def get_available_dates(
        driver: WebDriver, request_tracker: RequestTracker
) -> Union[List[datetime.date], None]:
    """向 AIS API 查询可用预约日期。
    Query the AIS API for available appointment dates."""
    if not ENABLE_DATE_QUERY:
        logger.warning(
            "日期查询已禁用，跳过 / Date query disabled (ENABLE_DATE_QUERY=false). Skipping."
        )
        return None

    request_tracker.log_retry()
    request_tracker.retry()

    schedule_base = driver.current_url.split("/appointment")[0]
    request_url = schedule_base + "/appointment" + AVAILABLE_DATE_REQUEST_SUFFIX
    logger.debug(f"日期查询 URL / Date query URL: {request_url}")

    request_header_cookie = "".join(
        [f"{cookie['name']}={cookie['value']};" for cookie in driver.get_cookies()]
    )
    request_headers = REQUEST_HEADERS.copy()
    request_headers["Cookie"] = request_header_cookie
    request_headers["User-Agent"] = driver.execute_script("return navigator.userAgent")

    try:
        response = requests.get(request_url, headers=request_headers)
    except Exception as e:
        logger.error(f"日期查询请求异常 / Date query exception: {e}")
        return None

    if response.status_code != 200:
        logger.error(f"日期查询失败，状态码 / Date query failed, status: {response.status_code}")
        logger.debug(f"响应内容 / Response: {response.text}")
        return None

    try:
        dates_json = response.json()
    except Exception:
        logger.error("JSON 解析失败 / Failed to decode JSON")
        logger.debug(f"原始响应 / Raw response: {response.text}")
        return None

    dates = [datetime.strptime(item["date"], "%Y-%m-%d").date() for item in dates_json]
    logger.info(
        f"查询到 {len(dates)} 个可用日期，最早 / Found {len(dates)} date(s), earliest: "
        f"{dates[0] if dates else 'N/A'}"
    )
    return dates


# ---------------------------------------------------------------------------
# 核心改期逻辑 / Core reschedule logic
# ---------------------------------------------------------------------------

def reschedule(driver: WebDriver, old_appointment: dict, retryCount: int = 0) -> bool:
    """轮询可用日期并在当前 session 内尝试改期。
    Poll available dates and attempt reschedule within the current session.

    Args:
        driver:          已登录并停留在预约页的 WebDriver
        old_appointment: 改期前从页面读到的当前预约信息 {'date': ..., 'time': ...}
        retryCount:      外部传入的重试上限（0 = 使用配置默认值）

    Returns:
        True — 改期成功 / False — 达到上限或失败
    """
    max_retries = retryCount if retryCount > 0 else DATE_REQUEST_MAX_RETRY
    max_time    = DATE_REQUEST_DELAY * retryCount if retryCount > 0 else DATE_REQUEST_MAX_TIME
    date_request_tracker = RequestTracker(max_retries, max_time)
    logger.info(
        f"开始轮询，max_retries={max_retries}, max_time={max_time}s / "
        f"Starting poll: max_retries={max_retries}, max_time={max_time}s"
    )

    earliest_acceptable_date = datetime.strptime(EARLIEST_ACCEPTABLE_DATE, "%Y-%m-%d").date()
    latest_acceptable_date   = datetime.strptime(LATEST_ACCEPTABLE_DATE,   "%Y-%m-%d").date()

    while date_request_tracker.should_retry():
        # ── 1. 获取可用日期 / Fetch available dates ──────────────────────────
        dates = get_available_dates(driver, date_request_tracker)
        available_dates = dates if dates is not None else []
        earliest_available_date = available_dates[0] if available_dates else "N/A (No slots found)"
        total_slots = len(available_dates)

        # 无论是否在期望区间内，都打印出官方最早可用日期
        if available_dates:
            logger.info(f"官方当前最早可用日期 (忽略区间限制): {earliest_available_date}")
            if earliest_available_date > datetime.strptime(LATEST_ACCEPTABLE_DATE, "%Y-%m-%d").date():
                logger.info(f"  注：该日期已晚于你的最晚接受日期 {LATEST_ACCEPTABLE_DATE}")

        # ── 启动成功通知 (含实时预约信息 + 首次查询结果) ──────────
        global startup_notified
        if 'startup_notified' not in globals() or not startup_notified:
            logger.info(f"发送启动成功汇报 / Sending startup success report: {earliest_available_date}")
            subject_prefix = "[STARTUP SUCCESS]" if not TEST_MODE else "[TEST STARTUP]"
            _send_email(
                subject=f"{subject_prefix} Rescheduler Active — {USER_CONSULATE}",
                body=(
                    f"抢位脚本已成功进入调度页，并完成初始数据抓取。\n"
                    f"Rescheduler is now active and monitoring slots.\n\n"
                    f"  ── 账户配置 / Config ───────────────────────────\n"
                    f"  账户邮箱 / Account     : {USER_EMAIL}\n"
                    f"  目标领事馆 / Consulate : {USER_CONSULATE}\n"
                    f"  期望区间 / Acceptable  : {EARLIEST_ACCEPTABLE_DATE} ~ {LATEST_ACCEPTABLE_DATE}\n"
                    f"  自动改期 / Auto-Resched: {'ENABLED' if ENABLE_AUTO_RESCHEDULE else 'DISABLED (Notification Only)'}\n\n"
                    f"  ── 首次查询结果 / First Query ───────────────────\n"
                    f"  最早可用日期 / Earliest Available: {earliest_available_date}\n"
                    f"  可用总数 / Total Slots Found    : {total_slots}\n\n"
                    f"  ── 当前个人预约 / Current Appt ───────────────────\n"
                    f"  预约日期 / Date    : {old_appointment['date']}\n"
                    f"  预约时间 / Time    : {old_appointment['time']}\n"
                    f"  预约地点 / Location: {old_appointment['location']}\n"
                    f"  取件地址 / Delivery: {old_appointment['delivery']}\n"
                    f"  ────────────────────────────────────────────────\n"
                    f"  启动时间 / Start Time  : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                ),
                mandatory=True
            )
            startup_notified = True

        if not dates:
            logger.warning(f"获取日期失败或暂无位子，{DATE_REQUEST_DELAY}s 后重试 / Failed or no slots, retrying in {DATE_REQUEST_DELAY}s")
            
            # ── 自动心跳检查 ──
            now = datetime.now()
            if MONITOR_STATE["last_email_time"]:
                hours_since_last = (now - MONITOR_STATE["last_email_time"]).total_seconds() / 3600
                if hours_since_last >= 4:
                    logger.info(f"距离上次发送已超过 {hours_since_last:.1f} 小时，强制发送心跳邮件")
                    _send_email(
                        subject=f"[AUTO HEARTBEAT] System Alive — {USER_CONSULATE}",
                        body=(
                            f"系统监控已持续运行，距上次邮件已超过 4 小时。\n\n"
                            f"  ── 运行快照 / Runtime Snapshot ─────────────────\n"
                            f"  启动时间 / Start Time  : {MONITOR_STATE['start_time'].strftime('%Y-%m-%d %H:%M:%S')}\n"
                            f"  当前状态 / Status      : Monitoring (No new slots)\n"
                            f"  最早可用 / Earliest    : {earliest_available_date}\n"
                            f"  可用总数 / Total Slots : {total_slots}\n"
                            f"  ── 当前个人预约 / Current Appt ───────────────────\n"
                            f"  预约日期 / Date    : {old_appointment['date']}\n"
                            f"  预约地点 / Location: {old_appointment['location']}\n"
                            f"  ────────────────────────────────────────────────\n"
                            f"  检查时间 / Check Time  : {now.strftime('%Y-%m-%d %H:%M:%S')}"
                        ),
                        mandatory=True
                    )
            
            sleep(DATE_REQUEST_DELAY + random.randint(0, 60))
            continue

        # ── 心跳预约汇报 (针对有槽位但不在期望区间内的情况) ────────
        now = datetime.now()
        if MONITOR_STATE["last_email_time"]:
            hours_since_last = (now - MONITOR_STATE["last_email_time"]).total_seconds() / 3600
            if hours_since_last >= 4:
                logger.info(f"发送系统心跳汇报 / Sending system heartbeat report: {earliest_available_date}")
                subject_prefix = "[AUTO HEARTBEAT]" if not TEST_MODE else "[TEST MODE HEARTBEAT]"
                _send_email(
                    subject=f"{subject_prefix} System Alive — {USER_CONSULATE} (Earliest: {earliest_available_date})",
                    body=(
                        f"系统监控已持续运行，距上次邮件已超过 4 小时。\n"
                        f"自动抢位功能：[{'已启动' if ENABLE_AUTO_RESCHEDULE else '已禁用'}]\n\n"
                        f"  ── 运行快照 / Runtime Snapshot ─────────────────\n"
                        f"  启动时间 / Start Time  : {MONITOR_STATE['start_time'].strftime('%Y-%m-%d %H:%M:%S')}\n"
                        f"  当前状态 / Status      : Monitoring (Slots available but out of range)\n"
                        f"  最早可用 / Earliest    : {earliest_available_date}\n"
                        f"  可用总数 / Total Slots : {total_slots}\n"
                        f"  期望区间 / Acceptable  : {EARLIEST_ACCEPTABLE_DATE} ~ {LATEST_ACCEPTABLE_DATE}\n"
                        f"  ── 当前个人预约 / Current Appt ───────────────────\n"
                        f"  预约日期 / Date    : {old_appointment['date']} {old_appointment['time']}\n"
                        f"  预约地点 / Location: {old_appointment['location']}\n"
                        f"  ────────────────────────────────────────────────\n"
                        f"  检查时间 / Check Time  : {now.strftime('%Y-%m-%d %H:%M:%S')}"
                    ),
                    mandatory=True
                )

        # ── 2. 检查是否在可接受范围内 / Check acceptable window ──────────────
        if not (earliest_acceptable_date <= earliest_available_date <= latest_acceptable_date):
            logger.info(
                f"不在接受范围内 / Out of acceptable range: {earliest_available_date} "
                f"(range: {earliest_acceptable_date} ~ {latest_acceptable_date})"
            )
            sleep(DATE_REQUEST_DELAY + random.randint(0, 60))
            continue

        # ── 3. 检查排除区间 / Check exclusion ranges ─────────────────────────
        excluded = False
        for i, (start, end) in enumerate(EXCLUSION_DATE_RANGES, 1):
            excl_start = datetime.strptime(start, "%Y-%m-%d").date()
            excl_end   = datetime.strptime(end,   "%Y-%m-%d").date()
            if excl_start <= earliest_available_date <= excl_end:
                logger.warning(
                    f"日期落在排除区间 {i} / Date in exclusion range {i}: {start} ~ {end}, skipping"
                )
                excluded = True
                break
        if excluded:
            sleep(DATE_REQUEST_DELAY + random.randint(0, 60))
            continue

        # ── 4. 找到合适日期 / Suitable date found ────────────────────────────
        logger.info(f"[!!!] 找到可用日期 / FOUND SLOT: {earliest_available_date}")

        # ── 5. 自动改期开关检查 / Auto-reschedule toggle check ────────────────
        if not ENABLE_AUTO_RESCHEDULE:
            logger.warning(
                "自动改期已禁用 / Auto-reschedule disabled. "
                "Set ENABLE_AUTO_RESCHEDULE=true and AUTO_RESCHEDULE_CONFIRM=CONFIRM to enable."
            )
            _send_email(
                subject=f"Visa Slot Found: {earliest_available_date} (not rescheduled / 未改期)",
                body=(
                    f"发现可用预约日期，但自动改期已禁用，请手动操作。\n"
                    f"A visa slot was found but auto-reschedule is disabled — please reschedule manually.\n\n"
                    f"  领事馆 / Consulate : {USER_CONSULATE}\n"
                    f"  可用日期 / Available: {earliest_available_date}\n"
                    f"  当前预约 / Current  : {old_appointment['date']} {old_appointment['time']} @ {old_appointment['location']}\n"
                    f"  取件地址 / Delivery : {old_appointment['delivery']}"
                ),
            )
            sleep(DATE_REQUEST_DELAY + random.randint(0, 60))
            continue

        # ── 6. 执行改期 / Execute reschedule ─────────────────────────────────
        logger.info(f"提交改期至 / Submitting reschedule to: {earliest_available_date}")
        try:
            # legacy_reschedule 成功时返回 {'date': date, 'time': str}，失败或测试模式返回 None
            # Returns {'date': date, 'time': str} on success, None on failure or TEST_MODE
            booked_info = legacy_reschedule(driver, earliest_available_date)
            if not booked_info:
                logger.error("改期操作返回 None（失败或测试模式）/ Reschedule returned None (failed or TEST_MODE)")
                return False

            logger.info(
                f"改期提交成功，已预约 / Reschedule submitted: "
                f"date={booked_info['date']}, time={booked_info['time']}"
            )

            # ── 7. 重新登录验证新预约，与提交结果交叉核对 ───────────────────
            # Re-login to verify the new appointment and cross-check with submitted result
            logger.info("重新登录验证改期结果 / Re-logging in to verify reschedule result")
            verified = verify_rescheduled_appointment()

            # 交叉核对：提交日期 vs 验证日期 / Cross-check: booked date vs verified date
            booked_date_str  = str(booked_info["date"])
            verified_date_str = str(verified["date"])
            if booked_date_str != "N/A" and verified_date_str != "N/A" and booked_date_str != verified_date_str:
                logger.warning(
                    f"日期不一致！提交={booked_date_str}，验证={verified_date_str} / "
                    f"Date mismatch! booked={booked_date_str}, verified={verified_date_str}"
                )
            else:
                logger.info(f"日期核对一致 / Date cross-check passed: {verified_date_str}")

            # ── 8. 强制发送改期确认邮件（mandatory=True）────────────────────
            # 不受 ENABLE_EMAIL_NOTIFICATION 控制，改期成功必须通知
            # Mandatory — not gated by ENABLE_EMAIL_NOTIFICATION; always notify on success
            _send_email(
                subject=f"[改期成功] Visa Appointment Rescheduled — {verified['date']}",
                body=(
                    f"您的签证预约已成功改期，详情如下：\n"
                    f"Your visa appointment has been successfully rescheduled.\n\n"
                    f"  领事馆 / Consulate          : {USER_CONSULATE}\n"
                    f"  ── 改期前 / Before ─────────────────────────────\n"
                    f"  原预约日期 / Old date        : {old_appointment['date']}\n"
                    f"  原预约时间 / Old time        : {old_appointment['time']}\n"
                    f"  原预约地点 / Old location    : {old_appointment['location']}\n"
                    f"  取件地址   / Delivery addr   : {old_appointment['delivery']}\n"
                    f"  ── 改期后（提交）/ Booked ──────────────────────\n"
                    f"  预约日期   / Booked date     : {booked_info['date']}\n"
                    f"  预约时间   / Booked time     : {booked_info['time']}\n"
                    f"  ── 改期后（验证）/ Verified ─────────────────────\n"
                    f"  验证日期   / Verified date   : {verified['date']}\n"
                    f"  验证时间   / Verified time   : {verified['time']}\n"
                    f"  验证地点   / Verified loc    : {verified['location']}\n"
                    f"  取件地址   / Delivery addr   : {verified['delivery']}\n"
                    f"  ────────────────────────────────────────────────\n"
                    f"  目标日期   / Target date     : {earliest_available_date}\n"
                    f"  验证时间戳 / Verified at     : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                ),
                mandatory=True,  # 改期成功强制发送，不受邮件开关控制 / Always send on success
            )
            logger.info("改期成功！/ Successfully rescheduled!")
            return True

        except Exception as e:
            logger.error(f"改期过程抛出异常 / Exception during reschedule: {e}")
            traceback.print_exc()
            continue

    logger.warning("超出重试限制，本 session 结束 / Retry limit exhausted for this session")
    return False


# ---------------------------------------------------------------------------
# 带新 session 的改期入口 / Reschedule with a fresh session
# ---------------------------------------------------------------------------

def reschedule_with_new_session(retryCount: int = DATE_REQUEST_MAX_RETRY) -> bool:
    """新建 session，登录，读取当前预约，然后执行改期流程。
    Open a fresh session, log in, read current appointment, then run the reschedule flow."""
    logger.info("新建浏览器 session / Starting new browser session")
    driver = get_chrome_driver()
    session_failures = 0
    timeout = TIMEOUT

    while session_failures < NEW_SESSION_AFTER_FAILURES:
        try:
            login(driver)

            # ── 在主页面读取当前预约（改期前）/ Read current appointment from main page ──
            old_appointment = get_current_appointment_info(driver)

            get_appointment_page(driver)

            policy_checkbox_limit = WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable((By.CLASS_NAME, "icheckbox"))
            )
            policy_checkbox_limit.click()

            continue_button = WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable((By.NAME, "commit"))
            )
            continue_button.click()
            logger.info(
                f"进入日期选择页，当前预约为 / Reached date selection, current appointment: "
                f"{old_appointment['date']} {old_appointment['time']}"
            )
            break
        except Exception as e:
            session_failures += 1
            logger.error(
                f"导航失败 ({session_failures}/{NEW_SESSION_AFTER_FAILURES}) / "
                f"Navigation failed ({session_failures}/{NEW_SESSION_AFTER_FAILURES}): {e}"
            )
            sleep(FAIL_RETRY_DELAY)

    if session_failures >= NEW_SESSION_AFTER_FAILURES:
        logger.error("超出最大 session 失败次数 / Max session failures exceeded")
        driver.quit()
        return False

    rescheduled = reschedule(driver, old_appointment, retryCount)
    logger.info(f"本 session 结果: {'成功 / success' if rescheduled else '失败 / failed'}")
    driver.quit()
    return rescheduled


# ---------------------------------------------------------------------------
# 程序入口 / Program entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    session_count = 0

    logger.info("=" * 60)
    logger.info("美国签证自动改期程序启动 / US Visa Auto-Rescheduler Starting")
    logger.info("=" * 60)
    logger.info(f"账户邮箱      / Account     : {USER_EMAIL}")
    logger.info(f"目标领事馆    / Consulate   : {USER_CONSULATE}")
    logger.info(f"最早可接受日期 / Earliest    : {EARLIEST_ACCEPTABLE_DATE}")
    logger.info(f"最晚可接受日期 / Latest      : {LATEST_ACCEPTABLE_DATE}")
    logger.info("-" * 60)
    logger.info(f"[开关] 日期查询    / DATE_QUERY       : {ENABLE_DATE_QUERY}")
    logger.info(f"[开关] 邮件通知    / EMAIL_NOTIF      : {ENABLE_EMAIL_NOTIFICATION}")
    logger.info(f"[开关] 自动改期    / AUTO_RESCHEDULE  : {ENABLE_AUTO_RESCHEDULE}")
    logger.info("  注：改期成功后无论邮件开关如何均强制发送确认邮件")
    logger.info("  Note: confirmation email is ALWAYS sent on successful reschedule")
    if not ENABLE_AUTO_RESCHEDULE:
        logger.warning(
            "自动改期未启用，发现合适日期时仅发邮件通知 / "
            "Auto-reschedule is OFF — only notifications will be sent when a slot is found."
        )
    logger.info("-" * 60)

    if EXCLUSION_DATE_RANGES:
        logger.info(f"排除区间 ({len(EXCLUSION_DATE_RANGES)} 个) / Exclusion ranges:")
        for i, (start, end) in enumerate(EXCLUSION_DATE_RANGES, 1):
            logger.info(f"  区间 {i} / Range {i}: {start} ~ {end}")
    else:
        logger.info("无排除日期区间 / No exclusion ranges")
    logger.info("=" * 60)

    while True:
        session_count += 1
        logger.info(f"启动第 {session_count} 个 session / Starting session #{session_count}")
        rescheduled = reschedule_with_new_session()

        if rescheduled:
            logger.info(f"改期成功，共用 {session_count} 个 session / Success after {session_count} session(s)")
            break

        logger.info(
            f"Session #{session_count} 未成功，等待 {NEW_SESSION_DELAY}s / "
            f"Session #{session_count} failed, waiting {NEW_SESSION_DELAY}s"
        )
        sleep(NEW_SESSION_DELAY + random.randint(0, 60))

    # 程序退出通知（受邮件开关控制）/ Exit notification (gated by email toggle)
    _send_email(
        subject="Rescheduler Program Exited / 改期程序已退出",
        body=(
            f"改期程序已于 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} 正常退出。\n"
            f"The rescheduler program exited at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}."
        ),
    )
