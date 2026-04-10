# USVISA-CA — US Visa Appointment Rescheduler (Canada)

[English](#english) | [中文](#中文)

---

<a name="english"></a>
## English

### 1. Overview
A Python + Selenium tool that automatically monitors and reschedules US visa interview appointments at Canadian consulates (Calgary, Halifax, Montreal, Ottawa, Quebec, Toronto, Vancouver).

Supports two run modes:
- **Local mode** — macOS / Windows, optional browser GUI, ChromeDriver auto-downloaded
- **Server mode** — Linux server / Docker / Railway, always headless, uses system Chromium

### 2. Core Logic
- **Automation**: Uses Selenium with Chrome to navigate the `ais.usvisa-info.com` portal.
- **Monitoring**: Periodically checks for dates within the user-defined window (`EARLIEST_ACCEPTABLE_DATE` → `LATEST_ACCEPTABLE_DATE`).
- **Notification**: Sends email via Gmail (SMTP) when a suitable slot is found.
- **Auto-reschedule**: Optional — submit the new booking automatically (requires double confirmation flag).
- **Hub integration**: Pushes status events (startup, heartbeat, found, booked, error, exited) to a jackdeng-hub backend.

### 3. Local Mode (macOS / Windows)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure
cp .env.example .env
# Edit .env — set RUN_MODE=local, credentials, date range, etc.

# 3. Run
python reschedule.py
```

ChromeDriver is downloaded automatically by `webdriver_manager`. Set `SHOW_GUI=true` in `.env` to watch the browser.

### 4. Server Mode (Docker)

```bash
# 1. Build image
docker build -t usvisa-ca .

# 2. Run with env file
docker run --env-file .env usvisa-ca

# Or pass env vars directly
docker run \
  -e RUN_MODE=server \
  -e USER_EMAIL=your@email.com \
  -e USER_PASSWORD=secret \
  -e USER_CONSULATE=Vancouver \
  -e EARLIEST_ACCEPTABLE_DATE=2024-05-01 \
  -e LATEST_ACCEPTABLE_DATE=2024-12-31 \
  usvisa-ca
```

> **Note**: The Docker image installs `chromium` and `chromium-driver` via `apt`. No `.env` file is needed if you pass all env vars through `-e` flags or your platform's secret manager.

### 5. Server Mode (Railway)

1. Push this repo to GitHub.
2. Create a new project on [Railway](https://railway.app) → Deploy from GitHub.
3. Set environment variables in the Railway dashboard (same as `.env.example`), including `RUN_MODE=server`.
4. Railway auto-detects the `Dockerfile` and builds/deploys the container.

### 6. Environment Variables

See [`.env.example`](.env.example) for the full list. Key variables:

| Variable | Default | Description |
|---|---|---|
| `RUN_MODE` | `local` | `local` or `server` |
| `USER_EMAIL` | — | AIS portal login email |
| `USER_PASSWORD` | — | AIS portal password |
| `USER_CONSULATE` | — | Target city (e.g. `Vancouver`) |
| `EARLIEST_ACCEPTABLE_DATE` | — | Earliest acceptable date (YYYY-MM-DD) |
| `LATEST_ACCEPTABLE_DATE` | — | Latest acceptable date (YYYY-MM-DD) |
| `SHOW_GUI` | `false` | Show browser (local mode only) |
| `TEST_MODE` | `false` | Simulate without real booking |
| `ENABLE_AUTO_RESCHEDULE` | `false` | Enable auto booking (also set `AUTO_RESCHEDULE_CONFIRM=CONFIRM`) |
| `HUB_URL` | — | jackdeng-hub base URL (optional) |
| `CRON_SECRET` | — | jackdeng-hub auth secret (optional) |

---

<a name="中文"></a>
## 中文

### 1. 项目简介
基于 Python + Selenium 的自动化工具，用于监控并改约加拿大境内美国领事馆的签证面试预约。支持两种运行模式：
- **本地模式**：macOS / Windows，可选显示浏览器窗口，ChromeDriver 自动下载
- **服务器模式**：Linux 服务器 / Docker / Railway，强制无头，使用系统 Chromium

### 2. 核心逻辑
- **自动化**：使用 Selenium + Chrome 操作 `ais.usvisa-info.com` 门户。
- **监控**：定期检查可接受日期范围内的可用名额。
- **通知**：找到名额时通过 Gmail SMTP 发送邮件。
- **自动改签**：可选功能，需额外确认标志。
- **Hub 集成**：将运行状态事件推送到 jackdeng-hub 后台。

### 3. 本地模式（macOS / Windows）

```bash
# 安装依赖
pip install -r requirements.txt

# 配置
cp .env.example .env
# 编辑 .env，设置 RUN_MODE=local、账号信息、日期范围等

# 运行
python reschedule.py
```

ChromeDriver 由 `webdriver_manager` 自动下载。将 `.env` 中的 `SHOW_GUI=true` 可观察浏览器操作过程。

### 4. 服务器模式（Docker）

```bash
# 构建镜像
docker build -t usvisa-ca .

# 使用 env 文件运行
docker run --env-file .env usvisa-ca
```

Docker 镜像通过 `apt` 安装 `chromium` 和 `chromium-driver`，无需手动下载驱动。

### 5. 服务器模式（Railway 一键部署）

1. 将本仓库推送到 GitHub。
2. 在 [Railway](https://railway.app) 创建项目 → 从 GitHub 部署。
3. 在 Railway 控制台配置环境变量（参考 `.env.example`），设置 `RUN_MODE=server`。
4. Railway 自动识别 `Dockerfile` 并完成构建和部署。

### 6. 项目结构

| 文件 | 说明 |
|---|---|
| `reschedule.py` | 主程序入口 |
| `settings.py` | 全局配置，所有参数从环境变量读取 |
| `hub_notifier.py` | jackdeng-hub 状态推送模块 |
| `legacy_rescheduler.py` | 改签操作核心逻辑 |
| `request_tracker.py` | 访问频率管理 |
| `Dockerfile` | 服务器模式容器镜像 |
| `requirements.txt` | Python 依赖 |
| `.env.example` | 环境变量模板 |
