# ── USVISA-CA — Server mode Docker image ─────────────────────────────────────
# 适用于 Railway / VPS / 任意 Linux 容器平台
# Works on Railway / VPS / any Linux container platform
#
# Build:   docker build -t usvisa-ca .
# Run:     docker run --env-file .env usvisa-ca
# ─────────────────────────────────────────────────────────────────────────────

FROM python:3.11-slim

# ── 安装 Chromium 和 chromedriver ─────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    chromium \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ── 安装 Python 依赖 ──────────────────────────────────────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── 复制项目文件 ──────────────────────────────────────────────────────────
COPY . .

# ── 运行模式固定为 server ─────────────────────────────────────────────────
ENV RUN_MODE=server
ENV PYTHONUNBUFFERED=1

CMD ["python", "reschedule.py"]
