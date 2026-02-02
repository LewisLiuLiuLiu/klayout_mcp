# GitHub 公开化与 uv 安装指南

## 📋 公开前检查清单

### 1. 敏感信息检查
```bash
# 搜索可能的敏感信息
grep -r "api_key\|apikey\|token\|password\|secret" --include="*.py" --include="*.json" --include="*.toml" .

# 检查是否有个人路径
grep -r "/home/\|/Users/" --include="*.py" --include="*.md" .
```

### 2. 确认 LICENSE
- [x] BSD-3-Clause 许可证已添加
- [x] LICENSE 文件存在

### 3. 作者信息
- [x] 已移除示例邮箱（可选：添加你的真实邮箱）

---

## 🚀 步骤 1: GitHub 仓库设置

### 1.1 在 GitHub 网页操作

1. 登录 GitHub，进入你的仓库
2. 点击 **Settings** → **General** → **Danger Zone**
3. 找到 **Change repository visibility**
4. 点击 **Change visibility** → **Make public**
5. 确认仓库名，输入 `yourusername/klayout_mcp`
6. 点击 **I understand, make this repository public**

### 1.2 更新仓库 URL（替换为真实用户名）

```bash
# 编辑 pyproject.toml，替换 YOUR_USERNAME
git add pyproject.toml
git commit -m "chore: update project URLs for public release"
```

---

## 📦 步骤 2: uv 安装支持

### 用户安装方式

创建 `INSTALL.md` 让用户了解如何安装：

```markdown
## Installation

### Using uv (Recommended)

```bash
# Install from GitHub
uv pip install git+https://github.com/YOUR_USERNAME/klayout_mcp

# Or with standalone KLayout support
uv pip install "git+https://github.com/YOUR_USERNAME/klayout_mcp[standalone]"

# Development install
uv pip install "git+https://github.com/YOUR_USERNAME/klayout_mcp[dev]"

# All features
uv pip install "git+https://github.com/YOUR_USERNAME/klayout_mcp[all]"
```

### Using pip

```bash
pip install git+https://github.com/YOUR_USERNAME/klayout_mcp
```
```

---

## 🔒 步骤 3: 保护主分支（推荐）

1. Settings → **Branches**
2. 点击 **Add rule**
3. 分支名模式：`main` 或 `master`
4. 勾选：
   - [ ] **Require a pull request before merging**
   - [ ] **Require status checks to pass**
   - [ ] **Require branches to be up to date before merging**

---

## 🏷️ 步骤 4: 创建 Release（可选但推荐）

### 4.1 创建 Git Tag

```bash
# 确保所有更改已提交
git add .
git commit -m "chore: prepare for public release"

# 创建版本标签
git tag -a v1.0.0 -m "First public release"

# 推送标签
git push origin v1.0.0
```

### 4.2 在 GitHub 创建 Release

1. 进入仓库 → **Releases** → **Draft a new release**
2. 选择标签 `v1.0.0`
3. 标题：`v1.0.0 - Initial Public Release`
4. 描述：复制 README 的 Features 部分
5. 点击 **Publish release**

---

## ✅ 公开后验证

### 测试 uv 安装

```bash
# 创建一个干净的测试环境
mkdir -p /tmp/test-klayout-mcp
cd /tmp/test-klayout-mcp

# 使用 uv 安装
uv venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 从 GitHub 安装
uv pip install git+https://github.com/YOUR_USERNAME/klayout_mcp

# 验证安装
which klayout-mcp
klayout-mcp --help  # 如果有 --help 选项

# 验证功能
python3 -c "
from src.server import mcp
print('✅ Import successful')
"

# 清理
cd ~
rm -rf /tmp/test-klayout-mcp
```

---

## 📊 文档保留说明

### 为什么保留 data/ 和 klayout-doc/

| 目录 | 大小 | 保留原因 |
|------|------|----------|
| `data/api_index.json` | 39MB | API 搜索功能必需 |
| `klayout-doc/markdown_docs/` | ~5MB | `search_klayout_docs` 工具必需 |

### uv 安装时会发生什么

```
用户执行: uv pip install git+https://...
           ↓
    git clone 整个仓库（包含所有文件）
           ↓
    构建 wheel（仅 src/ 被打包）
           ↓
    安装到 site-packages/
           ↓
    运行时从相对路径读取 data/ 和 klayout-doc/
```

**结果：✅ 功能完整，文档可用**

---

## 🎯 最佳实践建议

### 1. 大文件管理（可选）

如果仓库变得过大，可以考虑：

```bash
# 使用 Git LFS 管理大文件
git lfs track "data/api_index.json"
git add .gitattributes
git commit -m "chore: use LFS for large files"
```

### 2. 分开发布文档（高级）

如果希望减小仓库体积：

```bash
# 1. 创建文档分支
git checkout -b docs

# 2. 在主分支删除文档
git checkout main
git rm -r klayout-doc/
git commit -m "chore: move docs to separate branch"

# 3. 修改代码从 GitHub API 获取文档（复杂，不推荐）
```

**不推荐**，因为会增加复杂性。

### 3. 保留当前方案（推荐）

✅ **当前方案（保留所有文件）是最佳选择**，因为：
- 功能完整
- 用户体验好
- 维护简单
- 40MB 在现代网络下可接受

---

## 📝 README 更新

更新 `README.md` 的安装部分：

```markdown
## Installation

### Using uv (Recommended)

```bash
uv pip install git+https://github.com/YOUR_USERNAME/klayout_mcp
```

### Using pip

```bash
pip install git+https://github.com/YOUR_USERNAME/klayout_mcp
```

### Development Install

```bash
git clone https://github.com/YOUR_USERNAME/klayout_mcp.git
cd klayout_mcp
uv pip install -e ".[all]"
```
```

---

## ✅ 最终检查清单

公开前确认：

- [ ] 敏感信息已清除
- [ ] LICENSE 文件存在
- [ ] pyproject.toml 中的 URL 已更新
- [ ] README.md 安装说明已更新
- [ ] 创建 Release Tag
- [ ] 分支保护已设置（可选）
- [ ] 测试 uv 安装成功

**完成后，你的仓库就准备好公开了！** 🎉
