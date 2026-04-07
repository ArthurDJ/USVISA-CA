"""
request_tracker.py — 请求次数与时间追踪器
request_tracker.py — Tracks retry count and elapsed time for a polling session.

用于控制轮询循环的退出条件：超过最大重试次数或超过最长允许时间时停止。
Controls the exit condition of a polling loop: stops when max retries or max time is exceeded.
"""

import logging
import time
from datetime import datetime

logger = logging.getLogger(__name__)


class RequestTracker:
    """追踪单次轮询 session 的请求次数和已耗时间。
    Tracks request count and elapsed time for a single polling session.

    Attributes:
        retries     (int):   当前已重试次数 / Current retry count
        max_retries (int):   允许的最大重试次数 / Maximum allowed retries
        max_time    (float): 允许的最长运行时间（秒）/ Maximum allowed run time in seconds
        start_time  (float): session 开始的时间戳 / Timestamp when the session started
    """

    def __init__(self, max_retries: int, max_time: float) -> None:
        """初始化追踪器，记录起始时间。
        Initialise the tracker and record the start time.

        Args:
            max_retries: 最大重试次数 / Maximum number of retries allowed
            max_time:    最长运行时间（秒）/ Maximum allowed run time in seconds
        """
        self.retries = 0
        self.max_retries = max_retries
        self.max_time = max_time
        self.start_time = time.time()
        logger.debug(
            f"RequestTracker 初始化 / RequestTracker initialised: "
            f"max_retries={max_retries}, max_time={max_time}s"
        )

    def retry(self) -> None:
        """将重试计数加一。/ Increment the retry counter by one."""
        self.retries += 1
        logger.debug(f"重试计数更新 / Retry count updated: {self.retries}/{self.max_retries}")

    def should_retry(self) -> bool:
        """判断是否应继续重试。
        Determine whether the polling loop should continue.

        Returns:
            False — 已超过最大重试次数或已超过最长时间 / Retry or time limit exceeded
            True  — 仍在限制范围内，可以继续 / Still within limits, continue
        """
        # 检查重试次数上限 / Check retry count limit
        if self.retries > self.max_retries:
            logger.warning(
                f"已达最大重试次数 / Max retries reached: "
                f"{self.retries}/{self.max_retries}，停止轮询 / stopping poll"
            )
            return False

        # 检查运行时间上限 / Check elapsed time limit
        elapsed_time = time.time() - self.start_time
        if elapsed_time > self.max_time:
            logger.warning(
                f"已超过最长运行时间 / Max time exceeded: "
                f"{elapsed_time:.1f}s / {self.max_time}s，停止轮询 / stopping poll"
            )
            return False

        logger.debug(
            f"继续轮询 / Continuing poll: "
            f"retries={self.retries}/{self.max_retries}, "
            f"elapsed={elapsed_time:.1f}s/{self.max_time}s"
        )
        return True

    def log_retry(self) -> None:
        """打印当前重试信息（兼容旧调用方式）。
        Log current retry info (kept for backward compatibility with call sites).
        """
        elapsed = time.time() - self.start_time
        logger.info(
            f"日期查询第 {self.retries + 1} 次 / Date query attempt #{self.retries + 1} "
            f"(已耗时 / elapsed: {elapsed:.1f}s)"
        )
