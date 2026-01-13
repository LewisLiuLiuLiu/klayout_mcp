# 阶段 1：编译 KLayout
FROM ubuntu:22.04 AS builder

# 设置环境变量避免交互式提示
ENV DEBIAN_FRONTEND=noninteractive

# 更新软件包列表并安装所有构建依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    ccache \
    wget \
    curl \
    python3 \
    python3-dev \
    python3-pip \
    libz-dev \
    libpng-dev \
    libtiff5-dev \
    libboost-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# 设置平台相关的构建参数
ARG TARGETPLATFORM
ARG BUILDPLATFORM
ARG TARGETOS
ARG TARGETARCH

# 克隆 KLayout 源码（使用 0.30.5 版本对应的 commit）
RUN git clone https://github.com/KLayout/klayout.git /tmp/klayout

# 编译 KLayout（无 Qt 绑定，只生成 Python 模块）
WORKDIR /tmp/klayout
RUN git checkout 6ad326e80

# 根据目标平台调整构建配置
RUN if [ "$TARGETARCH" = "arm64" ]; then \
    export CFLAGS="-O3 -march=armv8-a"; \
    export CXXFLAGS="-O3 -march=armv8-a"; \
    fi && \
    if [ "$TARGETARCH" = "amd64" ]; then \
    export CFLAGS="-O3 -march=x86-64"; \
    export CXXFLAGS="-O3 -march=x86-64"; \
    fi

RUN ./build.sh -bin /usr/local/klayout -without-qtbinding -j$(nproc)

# 阶段 2：运行环境
FROM ubuntu:22.04

# 设置环境变量避免交互式提示
ENV DEBIAN_FRONTEND=noninteractive

# 设置 Python 模块路径
ENV PYTHONPATH=/usr/local/klayout/pymod:/app/src:$PYTHONPATH
ENV LD_LIBRARY_PATH=/usr/local/klayout:$LD_LIBRARY_PATH
ENV PATH=/usr/local/klayout/bin:$PATH

# 安装运行时依赖和开发工具
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-venv \
    libz1 \
    zlib1g \
    git \
    curl \
    wget \
    vim \
    less \
    && rm -rf /var/lib/apt/lists/*

# 从构建阶段复制编译结果
COPY --from=builder /usr/local/klayout /usr/local/klayout

# 设置工作目录
WORKDIR /app

# 复制项目文件
COPY requirements.txt /app/

# 安装 Python 依赖
RUN pip3 install --no-cache-dir --upgrade pip && \
    pip3 install --no-cache-dir -r requirements.txt

# 添加非 root 用户
RUN useradd -m -s /bin/bash appuser && \
    chown -R appuser:appuser /app && \
    # 给予 appuser 执行权限
    chmod +x /usr/local/klayout/bin/*
USER appuser

# 暴露端口（如果使用 HTTP 传输）
EXPOSE 8000

# 添加健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python3 -c "import sys; sys.path.append('/app/src'); from server import test_klayout_import; print(test_klayout_import())" || exit 1

# 启动 MCP 服务器
CMD ["python3", "/app/src/server.py"]