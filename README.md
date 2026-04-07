# USVISA-CA (Canada US Visa Rescheduler)

[English](#english) | [中文](#中文)

---

<a name="english"></a>
## English

### 1. Overview
A Python-based tool for automatically checking and rescheduling US visa interview appointments at consulates in Canada (Calgary, Halifax, Montreal, Ottawa, Quebec, Toronto, Vancouver).

### 2. Core Logic
- **Scraping/Automation**: Uses `Selenium` with Chrome (via `webdriver_manager`) to navigate the `ais.usvisa-info.com` portal.
- **Monitoring**: Periodically checks for available dates within a user-defined range (`EARLIEST_ACCEPTABLE_DATE` to `LATEST_ACCEPTABLE_DATE`).
- **Notification**: Sends alerts via Gmail (SMTP) when a suitable slot is found.
- **Safety**: Includes a `TEST_MODE` to simulate finding slots without actual booking, and `SHOW_GUI` toggle for headless operation.

### 3. How to Run
1. **Setup Environment**:
   ```bash
   pip install -r requirements.txt
   ```
2. **Configure**: Create a `.env` file based on `.env.example`.
3. **Execute**:
   ```bash
   python reschedule.py
   ```

---

<a name="中文"></a>
## 中文

### 1. 项目简介
基于 Python 的自动化工具，用于自动查询并改约加拿大境内美国领事馆（卡尔加里、哈利法克斯、蒙特利尔、渥太华、魁北克、多伦多、温哥华）的签证面试预约。

### 2. 核心逻辑
- **爬虫/自动化**: 使用 `Selenium` 配合 Chrome (通过 `webdriver_manager`) 模拟浏览器操作 `ais.usvisa-info.com` 门户。
- **监控**: 定期检查用户定义的日期范围内的可用名额 (`EARLIEST_ACCEPTABLE_DATE` 到 `LATEST_ACCEPTABLE_DATE`)。
- **通知**: 发现合适的名额时，通过 Gmail (SMTP) 发送即时提醒。
- **安全**: 包含 `TEST_MODE`（测试模式）用于模拟查询而不实际执行改约，以及 `SHOW_GUI` 开关用于切换是否显示浏览器窗口。

### 3. 如何运行
1. **环境配置**:
   ```bash
   pip install -r requirements.txt
   ```
2. **配置变量**: 根据 `.env.example` 创建 `.env` 文件并填写相关账号和日期信息。
3. **执行脚本**:
   ```bash
   python reschedule.py
   ```

---

## Project Structure / 项目结构
- `reschedule.py`: Main entry point / 主程序入口
- `settings.py`: Configuration & Constants / 配置与常量
- `requirements.txt`: Dependencies / 依赖库
- `request_tracker.py`: Frequency Control / 访问频率管理
