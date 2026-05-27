# AGENTS.md — Rub 项目开发协议

> **结构先于实现，美即低熵。**
> 
> 这是 rub 项目的工作协议。所有开发工作应遵循本协议定义的流程和规范。

---

## 1. 项目概述

**Rub** 是一个 Universal API CLI 框架，通过单一接口发现、检查和调用任何协议。

- **仓库**: https://github.com/iodone/rubick.gitiodone
- **语言**: Python 3.12+
- **包管理**: uv
- **构建工具**: setuptools

---

## 2. 开发流程

### 2.1 分支命名规范

| Type | 场景 | 示例 |
|------|------|------|
| `feat/` | 新功能 | `feat/user-auth-jwt` |
| `fix/` | Bug 修复 | `fix/config-show-workspaces-null` |
| `docs/` | 文档变更 | `docs/update-readme` |
| `refactor/` | 重构 | `refactor/simplify-auth-flow` |
| `chore/` | 构建/工具变更 | `chore/add-ci-cd` |
| `style/` | 代码风格 | `style/fix-lint-errors` |

### 2.2 Commit Message 格式

```
<type>(<scope>): <subject> (#issue)

[optional body]
```

**示例**:
```
fix(auth): support secret_source for custom auth type (#2)

- make_auth_headers(): support both custom_headers and secret_source
- resolve_secret(): only raise error when custom type has no secret_source
```

---

## 3. 开发命令

### 3.1 基础命令

```bash
# 安装依赖
just install
# 或
uv sync

# 格式化代码
just format
# 或
uv run black src/ tests/

# 运行 lint 检查
just check
# 或
uv run ruff check src/
uv run mypy src/

# 运行测试
just test
# 或
uv run pytest

# 构建包
just build
# 或
uv build
```

### 3.2 完整开发流程

```bash
# 1. 同步最新代码
git checkout main && git pull

# 2. 创建功能分支
git checkout -b feat/my-feature

# 3. 开发 & 测试
# ... 编辑代码 ...

# 4. 格式化 & 检查
just format
just check
just test

# 5. 提交
git add <files>
git commit -m "feat(scope): description (#issue)"

# 6. 推送 & 创建 MR
git push -u origin feat/my-feature
gh mr create ...
```

---

## 4. 代码规范

### 4.1 风格指南

- **行长度**: 88 字符（Black 默认）
- **格式化工具**: Black
- **Lint 工具**: Ruff（规则: E, F, I, UP）
- **类型检查**: mypy（strict 模式）

### 4.2 Ruff 配置

```toml
[tool.ruff]
target-version = "py312"
src = ["src"]

[tool.ruff.lint]
select = ["E", "F", "I", "UP"]

[tool.ruff.lint.per-file-ignores]
"__init__.py" = ["E402"]
```

### 4.3 字符串折行规则

Black/Ruff format **不会自动折行字符串**。以下情况需手动拆分：

- 长 SQL 查询
- 长 f-string
- 长 docstring

**示例**:
```python
# ✅ 正确：手动拆分长字符串
query = (
    "SELECT key, schema_json, protocol, "
    "fetched_at, expires_at "
    "FROM schema_cache WHERE key = ?"
)

# ❌ 错误：超过 88 字符
query = "SELECT key, schema_json, protocol, fetched_at, expires_at FROM schema_cache WHERE key = ?"
```

---

## 5. 测试规范

### 5.1 测试文件命名

```
tests/
├── test_adapter.py        # Adapter 协议测试
├── test_auth_bindings.py  # Auth binding 测试
├── test_auth_profiles.py  # Auth profile 测试
├── test_cache.py          # 缓存功能测试
├── test_cli.py            # CLI 命令测试
├── test_client.py         # HTTP 客户端测试
├── test_config.py         # 配置测试
├── test_discovery.py      # 适配器发现测试
└── test_openapi_adapter.py # OpenAPI 适配器测试
```

### 5.2 测试覆盖率

```bash
# 运行测试并生成覆盖率报告
uv run pytest --cov=rub --cov-report=term-missing --cov-report=xml
```

### 5.3 测试标记

```python
import pytest

@pytest.mark.asyncio
async def test_my_async_function():
    """异步测试示例"""
    result = await my_async_function()
    assert result.ok
```

---

## 6. 发布流程

### 6.1 Dev 版本

```bash
# 1. 更新版本号
# 编辑 src/rub/__init__.py: __version__ = "0.2.1.dev1"

# 2. 提交并打 tag
git tag v0.2.1.dev1
git push origin v0.2.1.dev1
```

### 6.2 Official 版本

```bash
# 1. 创建 release 分支
git checkout main && git pull
git checkout -b release/v0.3.0

# 2. 更新版本号
# 编辑 src/rub/__init__.py: __version__ = "0.3.0"

# 3. 生成 release notes
# 参照 RELEASE_NOTES.md 格式

# 4. 创建 MR 合并到 main
gh mr create \
  --source-branch release/v0.3.0 \
  --target-branch main \
  --title "chore: release v0.3.0" \
  --description "Release version 0.3.0"
gh mr merge <mr-number> --repo iodone/rub

# 5. 创建 Git tag
git checkout main && git pull
git tag v0.3.0
git push origin v0.3.0

# 6. 创建 GitLab Release
NOTES=$(awk "/^## v0.3.0/{found=1} found && /^---$/{print; exit} found" RELEASE_NOTES.md)
gh release create v0.3.0 \
  --repo iodone/rub \
  --name "v0.3.0" \
  --notes "$NOTES"
```

---

## 7. CI/CD 流程

### 7.1 流程概览

```yaml
stages:
  - test    # MR 触发：ruff + pytest
  - build   # tag 触发：uv build
  - publish # tag 触发：发布到内部 PyPI
```

### 7.2 触发条件

| 阶段 | 触发条件 | 说明 |
|------|----------|------|
| test | MR → main | 自动运行 |
| build | tag `v*.*.*` | 自动构建 |
| publish_snapshot | tag `v*.*.*.dev*` | 自动发布到 snapshot |
| publish_release | tag `v*.*.*` | 手动确认后发布到 release |

---

## 8. 版本管理

### 8.1 版本号规范

遵循 [Semantic Versioning](https://semver.org/):

```
MAJOR.MINOR.PATCH[-prerelease][+build]

示例:
- 0.1.0      # 正式版
- 0.2.1.dev1 # 开发版
- 1.0.0      # 稳定版
```

### 8.2 版本来源

版本号定义在 `src/rub/__init__.py`，pyproject.toml 使用 dynamic version：

```toml
[project]
dynamic = ["version"]

[tool.setuptools.dynamic]
version = {attr = "rub.__version__"}
```

---

## 9. 依赖管理

### 9.1 依赖声明

```toml
# pyproject.toml
dependencies = [
    "typer>=0.9",
    "pydantic>=2.0",
    "httpx>=0.27",
    ...
]
```

### 9.2 开发依赖

```toml
[dependency-groups]
dev = [
    "pytest>=8.0",
    "ruff>=0.4",
    "mypy>=1.10",
    "black>=24.0",
]
```

### 9.3 依赖安装

```bash
# 安装所有依赖（包括开发依赖）
uv sync --dev

# 只安装生产依赖
uv sync
```

---

## 10. 文档规范

### 10.1 文件结构

```
rub/
├── README.md           # 项目说明和使用指南
├── RELEASE_NOTES.md    # 版本发布说明
├── AGENTS.md           # 本文件（开发协议）
├── docs/               # 详细文档
│   ├── plugin-development.md
│   └── plugin-development-zh.md
└── pyproject.toml      # 项目配置
```

### 10.2 Docstring 格式

```python
def my_function(arg1: str, arg2: int) -> bool:
    """Brief description of the function.

    Args:
        arg1: Description of arg1.
        arg2: Description of arg2.

    Returns:
        Description of return value.

    Raises:
        ValueError: When arg1 is empty.
    """
    ...
```

---

## 11. 工具生成，协议参考

本协议定义了 rub 项目的开发规范和流程。

**记住**：
- **结构先于实现** — 先设计，再编码
- **美即低熵** — 简洁、清晰、一致
- **工具生成** — 让工具处理格式化和检查
- **协议参考** — 遵循本协议保持一致性

---

*Last Updated: 2026-04-28*
