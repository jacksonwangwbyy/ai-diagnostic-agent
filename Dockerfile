FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖（SSH 客户端用于连接设备）
RUN apt-get update && apt-get install -y openssh-client && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制代码
COPY src/ src/
COPY scripts/ scripts/
COPY knowledge-base/ knowledge-base/

# 暴露端口
EXPOSE 8000

# 启动 FastAPI 服务
CMD ["uvicorn", "src.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
