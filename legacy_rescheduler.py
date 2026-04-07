"""
legacy_rescheduler.py — 基于 Selenium 的预约改期执行层
legacy_rescheduler.py — Selenium-based appointment rescheduling execution layer.

说明 / Note:
  本模块直接操作浏览器完成改期，待有测试账号后应用 requests 重写。
  This module drives the browser to complete rescheduling;
  it should be rewritten with requests once a test account is available.
"""

import logging
from time import sleep
from datetime import datetime, date
from typing import Optional

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.webdriver import WebDriver

from settings import TEST_MODE, NUM_PARTICIPANTS

logger = logging.getLogger(__name__)


def legacy_reschedule(driver: WebDriver, date_to_book: date) -> Optional[dict]:
    """用 Selenium 在预约页面完成改期操作。
    Use Selenium to complete the reschedule action on the appointment page.

    操作步骤 / Steps:
      1. 刷新页面，打开日期选择器 / Refresh and open the date picker
      2. 找到最近可用月份，选择最早可用日期 / Find nearest available month and select earliest date
      3. 读取并验证选中日期 / Read and validate selected date
      4. 选择最晚可用时间段 / Select the last available time slot
      5. 点击 Reschedule，确认弹窗 / Click Reschedule and confirm the dialog

    Args:
        driver:       已停留在预约页的 WebDriver / WebDriver on the appointment page
        date_to_book: 期望预约的目标日期 / Target date to book

    Returns:
        成功时返回 {'date': date, 'time': str}，失败或测试模式时返回 None。
        On success returns {'date': date, 'time': str}; returns None on failure or in TEST_MODE.
    """
    logger.info(f"开始执行改期，目标日期 / Starting reschedule, target date: {date_to_book}")
    driver.refresh()
    logger.debug("页面已刷新 / Page refreshed")

    # 多人预约时需先点击 Continue / For multiple participants, click Continue first
    if NUM_PARTICIPANTS > 1:
        logger.debug(f"多人预约 ({NUM_PARTICIPANTS} 人)，点击 Continue / Multiple participants, clicking Continue")
        continueBtn = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (By.XPATH, "//main[@id='main']/div[@class='mainContent']/form/div[2]/div/input")
            )
        )
        continueBtn.click()

    # 等待日期输入框并点击，唤起日期选择器
    # Wait for the date input field and click it to open the date picker
    logger.debug("等待日期选择框 / Waiting for date selection input")
    date_selection_box = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "appointments_consulate_appointment_date_input"))
    )
    sleep(2)
    date_selection_box.click()
    logger.debug("日期选择器已打开 / Date picker opened")

    # ── 内部辅助函数：日历翻页与月份可用性检查 ────────────────────────────────
    # Inner helpers: calendar navigation and month availability check

    def next_month() -> None:
        """点击日期选择器的「下一月」按钮。/ Click the date picker's next-month button."""
        driver.find_element(By.XPATH, "//div[@id='ui-datepicker-div']/div[2]/div/a").click()

    def cur_month_has_slot() -> bool:
        """检查当前显示月份是否有可用日期（class=" undefined" 表示可用）。
        Check if the currently displayed month has any available date (class=" undefined" means available)."""
        month_body = driver.find_element(
            By.XPATH, "//div[@id='ui-datepicker-div']/div[1]/table/tbody"
        )
        for td in month_body.find_elements(By.TAG_NAME, "td"):
            if td.get_attribute("class") == " undefined":
                return True
        return False

    def advance_to_nearest_available() -> int:
        """向后翻页直到找到有可用日期的月份，返回翻了几个月。
        Advance the calendar until a month with available dates is found; return months advanced."""
        months_advanced = 0
        while not cur_month_has_slot():
            next_month()
            months_advanced += 1
            logger.debug(f"当前月无可用日期，翻至下一月（+{months_advanced}）/ No slot this month, advanced +{months_advanced}")
        return months_advanced

    months_skipped = advance_to_nearest_available()
    logger.info(f"在 +{months_skipped} 个月后找到可用日期 / Found available dates after +{months_skipped} month(s)")

    # ── 选择最早可用日期 / Select the earliest available date ─────────────────
    month_body = driver.find_element(By.XPATH, "//div[@id='ui-datepicker-div']/div[1]/table/tbody")
    ava_date_btn = None
    for td in month_body.find_elements(By.TAG_NAME, "td"):
        if td.get_attribute("class") == " undefined":
            ava_date_btn = td.find_element(By.TAG_NAME, "a")
            break

    if ava_date_btn is None:
        # 理论上不会走到这里，但作为防御性处理 / Should not reach here, but defensive guard
        logger.error("未找到可点击的可用日期按钮 / No clickable available date button found")
        return None

    ava_date_btn.click()
    logger.debug("已点击可用日期 / Available date clicked")

    # ── 读取并验证选中日期 / Read and validate selected date ──────────────────
    sleep(2)
    date_box = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "appointments_consulate_appointment_date"))
    )
    date_selected = datetime.strptime(date_box.get_attribute("value"), "%Y-%m-%d").date()
    logger.info(f"日历选中日期 / Calendar selected date: {date_selected}")

    # 若选中日期晚于目标日期，说明目标槽位已被抢占
    # If selected date is later than the target, the slot was taken
    if not date_selected <= date_to_book:
        logger.warning(
            f"槽位已失效 / Slot no longer available: "
            f"selected={date_selected}, target={date_to_book}"
        )
        return None

    logger.info(f"槽位仍然有效，准备预约 / Slot still available, proceeding to book: {date_selected}")

    # ── 选择时间段（取最后一个可用选项）/ Select time slot (last available option) ──
    sleep(2)
    appointment_time = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.ID, "appointments_consulate_appointment_time"))
    )
    appointment_time.click()
    time_options = appointment_time.find_elements(By.TAG_NAME, "option")

    # 取最后一个非空时间选项 / Take the last non-empty time option
    selected_time_value = ""
    for opt in reversed(time_options):
        val = opt.get_attribute("value").strip()
        if val:
            opt.click()
            selected_time_value = val
            break

    logger.info(f"已选择时间段 / Selected time slot: {selected_time_value}")

    # ── 点击「Reschedule」提交按钮 / Click the Reschedule submit button ─────────
    driver.find_element(
        By.XPATH, "//form[@id='appointment-form']/div[2]/fieldset/ol/li/input"
    ).click()
    logger.debug("已点击 Reschedule 按钮 / Reschedule button clicked")
    sleep(2)

    # ── 等待并处理确认弹窗 / Wait for and handle the confirmation dialog ─────────
    try:
        confirm = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "/html/body/div[6]/div/div/a[2]"))
        )
        logger.debug("确认弹窗已出现 / Confirmation dialog appeared")
    finally:
        sleep(2)
        driver.implicitly_wait(0.1)

        if TEST_MODE:
            # 测试模式：不点击最终确认，返回 None
            # Test mode: do not click final confirm; return None
            logger.warning(
                "测试模式已启用，跳过最终确认点击 / "
                "TEST_MODE is ON — final confirm click skipped, returning None"
            )
            return None

        # 正式模式：点击确认，返回已预约的日期和时间
        # Production mode: click confirm and return the booked date and time
        confirm.click()
        logger.info(
            f"确认弹窗已点击，改期完成 / Confirm clicked, reschedule complete: "
            f"date={date_selected}, time={selected_time_value}"
        )
        return {"date": date_selected, "time": selected_time_value}
