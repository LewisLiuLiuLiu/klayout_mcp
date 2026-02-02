# GitHub 公开化检查清单

## 🎯 决策总结

### 关于文档保留的决定

**✅ 推荐：保留所有文档（data/ 和 klayout-doc/）**

| 问题 | 答案 |
|------|------|
| html/markdown 文档需要保留吗？ | **是的**，因为 `search_klayout_docs` 工具依赖它们 |
| uv 安装时会安装这些文档吗？ | **不会**，`packages=["src"]` 配置只安装 Python 代码 |
| 但 uv 安装时会下载整个仓库吗？ | **是的**，克隆时会下载（40MB），但运行时只占用 Python 代码 |
| 建议怎么做？ | **保留所有文件**，功能完整，用户体验好 |

---

## ✅ 公开前必须完成的步骤

### 1. 替换占位符（必须）

编辑 `pyproject.toml`：
```toml
[project.urls]
Homepage = "https://github.com/YOUR_USERNAME/klayout_mcp"        # ← 替换
Repository = "https://github.com/YOUR_USERNAME/klayout_mcp"      # ← 替换
Documentation = "https://github.com/YOUR_USERNAME/klayout_mcp/blob/main/README.md"  # ← 替换
```

编辑 `README.md`：
```markdown
uv pip install git+https://github.com/YOUR_USERNAME/klayout_mcp  # ← 替换所有 YOUR_USERNAME
```

### 2. 提交更改

```bash
git add .
git commit -m "chore: prepare for public release

- Add pyproject.toml for modern Python packaging
- Remove requirements.txt (migrated to pyproject.toml)
- Add async/await support with Context integration
- Add structured output for all tools
- Add evaluation.xml with 10 test questions
- Add verification scripts
- Update documentation"
```

### 3. 检查敏感信息

```bash
# 运行检查
grep -r "api_key\|apikey\|token\|password\|secret\|private_key" \
  --include="*.py" --include="*.json" --include="*.toml" --include="*.sh" .

# 检查是否有个人路径
grep -r "/home/`whoami`/\|/Users/`whoami`/" --include="*.py" --include="*.md" .
```

### 4. GitHub 公开化操作

1. 登录 GitHub 网页
2. 进入仓库 `Settings` → `General`
3. 滚动到最下方 `Danger Zone`
4. 点击 `Change repository visibility`
5. 选择 `Make public`
6. 输入仓库名确认
7. 点击 `I understand, make this repository public`

### 5. 创建 Release（推荐）

```bash
# 创建标签
git tag -a v1.0.0 -m "First public release - Full MCP server with async support"

# 推送标签
git push origin v1.0.0
```

然后在 GitHub 网页：
1. 进入 `Releases` → `Draft a new release`
2. 选择 `v1.0.0`
3. 填写发布说明
4. 点击 `Publish release`

---

## 🧪 公开后测试

### 测试 uv 安装

```bash
# 创建测试目录
mkdir -p /tmp/test-klayout-mcp
cd /tmp/test-klayout-mcp

# 使用 uv 安装
uv venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 从 GitHub 安装（替换 YOUR_USERNAME）
uv pip install git+https://github.com/YOUR_USERNAME/klayout_mcp

# 验证安装
python -c "from src.server import mcp; print('✅ Install successful')"

# 运行验证
python -m src.scripts.verify_mcp

# 清理
cd ~
rm -rf /tmp/test-klayout-mcp
```

---

## 📋 文件变更总结

### 新增文件
- `pyproject.toml` - Python 项目配置
- `evaluation.xml` - 评估问题
- `GITHUB_PUBLISH_GUIDE.md` - 公开指南
- `VERIFICATION_PLAN.md` - 验证计划
- `VERIFICATION_REPORT.md` - 验证报告
- `scripts/quick_verify.sh` - 快速验证脚本
- `scripts/verify_mcp.py` - 完整验证脚本

### 修改文件
- `src/server.py` - 完全异步化 + Context 支持
- `README.md` - 添加 uv 安装说明
- `AGENTS.md` - 添加评估文档

### 删除文件
- `requirements.txt` - 已迁移到 pyproject.toml

---

## 🎉 完成后

你的 KLayout MCP Server 将可以通过以下方式安装：

```bash
# 用户使用 uv
uv pip install git+https://github.com/YOUR_USERNAME/klayout_mcp

# 用户使用 pip
pip install git+https://github.com/YOUR_USERNAME/klayout_mcp

# 开发者安装
git clone https://github.com/YOUR_USERNAME/klayout_mcp.git
cd klayout_mcp
uv pip install -e ".[all]"
```

---

## ⚠️ 重要提醒

1. **不要**删除 `data/` 或 `klayout-doc/`，否则功能会缺失
2. **必须**替换 `YOUR_USERNAME` 占位符
3. **建议**先在私人仓库测试所有步骤
4. **可选**添加 Git LFS 管理大文件（非必需）

**一切准备就绪后，你的 MCP 服务器就可以公开给所有人使用了！** 🚀
