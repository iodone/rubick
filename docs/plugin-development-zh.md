# Rub 插件开发指南

本文档帮助你从零开始构建一个 Rub 协议适配器插件（`rub-xxx`）。读完后，你将拥有一个可被 Rub 自动发现和加载的独立 Python 包。

---

## 目录

- [Rub 概述](#rub-概述)
- [插件架构](#插件架构)
- [快速开始：创建插件](#快速开始创建插件)
  - [1. 目录结构](#1-目录结构)
  - [2. 配置 pyproject.toml](#2-配置-pyprojecttoml)
  - [3. 实现 Adapter](#3-实现-adapter)
  - [4. 导出适配器类](#4-导出适配器类)
- [数据模型参考](#数据模型参考)
- [Hook 生命周期](#hook-生命周期)
- [独立 CLI 模式](#独立-cli-模式)
- [测试指南](#测试指南)
- [开发工作流](#开发工作流)
- [发布](#发布)
- [发布检查清单](#发布检查清单)
- [使用 AI Agent Skills 辅助开发](#使用-ai-agent-skills-辅助开发)
- [常见问题与排错](#常见问题与排错)

---

## Rub 概述

Rub 是一个通用 API 命令行工具，通过统一的交互模式操作任意协议的 API：

```
rub <url> -h                # 发现：列出所有可用操作
rub <url> <operation> -h    # 检视：查看操作的参数说明
rub <url> <op> key=value    # 调用：执行操作并返回结果
```

Rub 核心不内置任何协议支持——所有协议（OpenAPI、GraphQL、gRPC、MCP 等）均通过 **插件包**（satellite package）提供。安装插件后，Rub 在运行时自动发现并加载，无需任何配置。

---

## 插件架构

Rub 的插件系统基于两个机制：

### 1. Python Entry Points（适配器发现）

插件在 `pyproject.toml` 中声明一个 entry point，Rub 通过 `importlib.metadata.entry_points(group="rub.adapters")` 在运行时扫描所有已安装的适配器：

```toml
[project.entry-points.'rub.adapters']
myprotocol = "rub_myprotocol:MyAdapter"
```

用户执行 `pip install rub-myprotocol` 后，Rub 就能自动发现你的适配器。

### 2. pluggy Hooks（生命周期扩展）

Rub 定义了 6 个生命周期钩子，插件可以在 pipeline 的关键节点注入自定义行为（如日志、监控、鉴权覆盖等）。

### 3. 优先级级联检测

每个适配器声明一个优先级数值（默认 100），数值越高越先被尝试。当用户执行 `rub <url>` 时，Rub 按优先级从高到低依次调用每个适配器的 `can_handle(url)`，第一个返回 `True` 的适配器胜出。

```
优先级 200: OpenAPIAdapter  → can_handle() → False
优先级 100: GraphQLAdapter   → can_handle() → True  ← 命中，使用此适配器
优先级  50: EchoAdapter      → （不再尝试）
```

---

## 快速开始：创建插件

以创建一个名为 `rub-myprotocol` 的插件为例。

### 1. 目录结构

```
rub-myprotocol/
├── pyproject.toml
├── src/
│   └── rub_myprotocol/
│       ├── __init__.py
│       └── adapter.py
└── tests/
    └── test_adapter.py
```

创建目录：

```bash
mkdir -p rub-myprotocol/src/rub_myprotocol rub-myprotocol/tests
cd rub-myprotocol
```

### 2. 配置 pyproject.toml

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "rub-myprotocol"
version = "0.1.0"
description = "MyProtocol adapter for Rub"
requires-python = ">= 3.12"
license = "MIT"
dependencies = [
    "rub>=0.1.0",
]

# ┌──────────────────────────────────────────────────┐
# │  关键配置：entry point                            │
# │                                                    │
# │  group:  rub.adapters  — Rub 扫描此分组            │
# │  name:   myprotocol    — 适配器唯一标识            │
# │  value:  module:Class  — 模块路径和类名            │
# └──────────────────────────────────────────────────┘
[project.entry-points.'rub.adapters']
myprotocol = "rub_myprotocol:MyProtocolAdapter"

[dependency-groups]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
]

[tool.hatch.build.targets.wheel]
sources = ["src"]
only-include = ["src/rub_myprotocol"]

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
```

**重点说明：**

- `[project.entry-points.'rub.adapters']` 是 Rub 发现插件的唯一入口
- `name`（等号左侧）是适配器的唯一标识符，不同插件不能重复
- `value`（等号右侧）格式为 `模块路径:类名`，指向一个 `Adapter` 子类

### 3. 实现 Adapter

每个插件必须继承 `rub.adapter.Adapter` 并实现 **6 个异步抽象方法**。

创建 `src/rub_myprotocol/adapter.py`：

```python
"""MyProtocol adapter for Rub."""

from __future__ import annotations

from typing import Any

from rub.adapter import Adapter, ExecutionResult
from rub.schema import Operation, OperationDetail, Parameter


class MyProtocolAdapter(Adapter):
    """处理 myprotocol:// URL 的适配器。"""

    # 同步优先级属性，供 AdapterRegistry 排序时使用
    _priority = 100

    # ── 身份与优先级 ──

    async def protocol_name(self) -> str:
        """返回协议标识符。"""
        return "myprotocol"

    async def priority(self) -> int:
        """返回检测优先级，数值越高越先被尝试。"""
        return 100

    # ── 协议检测 ──

    async def can_handle(self, url: str) -> bool:
        """判断此适配器能否处理给定 URL。

        此方法会在每次 rub 调用时被执行，应保持快速且无副作用。
        """
        return url.startswith("myprotocol://")

    # ── 操作发现 ──

    async def list_operations(self, url: str) -> list[Operation]:
        """返回此端点支持的所有操作列表。

        对应 CLI 命令：rub <url> -h
        """
        return [
            Operation(
                operation_id="hello",
                display_name="Hello",
                description="发送问候",
                parameters=[
                    Parameter(
                        name="name",
                        param_type="string",
                        required=True,
                        description="问候对象的名称",
                    ),
                ],
            ),
        ]

    # ── 操作检视 ──

    async def describe_operation(self, url: str, op_id: str) -> OperationDetail:
        """返回某个操作的详细信息。

        对应 CLI 命令：rub <url> <op> -h
        """
        return OperationDetail(
            operation_id="hello",
            display_name="Hello",
            description="发送问候",
            parameters=[
                Parameter(
                    name="name",
                    param_type="string",
                    required=True,
                    description="问候对象的名称",
                ),
            ],
            return_type="object",
            input_schema={
                "type": "object",
                "properties": {"name": {"type": "string"}},
                "required": ["name"],
            },
        )

    # ── 操作执行 ──

    async def execute(
        self,
        url: str,
        op_id: str,
        args: dict[str, Any],
        *,
        auth_headers: dict[str, str] | None = None,
    ) -> ExecutionResult:
        """执行操作并返回结果。

        对应 CLI 命令：rub <url> <op> key=value

        Args:
            url: 目标 URL。
            op_id: 操作标识符。
            args: 调用参数。
            auth_headers: Rub 自动注入的认证头，适配器在发起
                          HTTP 请求时应将其传入。
        """
        name = args.get("name", "World")
        return ExecutionResult(
            data={"message": f"Hello, {name}!"},
            status_code=200,
        )
```

#### 6 个抽象方法一览

| 方法 | 调用时机 | 返回值 |
|---|---|---|
| `protocol_name()` | 元数据/日志 | 协议名称字符串，如 `"openapi"` |
| `priority()` | 检测排序 | 整数，越大越先尝试（默认 100） |
| `can_handle(url)` | 协议检测级联 | `True` 表示可处理该 URL |
| `list_operations(url)` | `rub <url> -h` | `list[Operation]` |
| `describe_operation(url, op_id)` | `rub <url> <op> -h` | `OperationDetail` |
| `execute(url, op_id, args)` | `rub <url> <op> k=v` | `ExecutionResult` |

**注意事项：**
- `can_handle()` 在每次调用时都会执行，必须快速返回且无副作用
- `_priority` 类属性是必要的——`AdapterRegistry` 在排序时需要同步访问优先级
- `execute()` 的 `auth_headers` 参数由 Rub 框架自动注入，你的适配器在发 HTTP 请求时应将其传递给客户端

### 4. 导出适配器类

创建 `src/rub_myprotocol/__init__.py`，确保 entry point 能找到你的类：

```python
"""Rub adapter for MyProtocol."""

from rub_myprotocol.adapter import MyProtocolAdapter

__all__ = ["MyProtocolAdapter"]
```

---

## 数据模型参考

Rub 使用 Pydantic 模型定义操作和结果的数据结构。

### Parameter

描述操作的单个参数。

```python
from rub.schema import Parameter

Parameter(
    name="user_id",          # 参数名
    param_type="string",     # 参数类型（默认 "string"）
    required=True,           # 是否必填（默认 False）
    description="用户 ID",   # 参数说明
)
```

### Operation

操作摘要，用于发现阶段（`list_operations` 返回值）。

```python
from rub.schema import Operation

Operation(
    operation_id="getUser",          # 操作标识符（唯一）
    display_name="Get User",         # 显示名称
    description="获取用户信息",       # 操作说明
    parameters=[...],                # Parameter 列表
)
```

### OperationDetail

操作详情，继承自 `Operation`，用于检视阶段（`describe_operation` 返回值）。

```python
from rub.schema import OperationDetail

OperationDetail(
    operation_id="getUser",
    display_name="Get User",
    description="获取用户信息",
    parameters=[...],
    return_type="application/json",        # 返回类型
    input_schema={"type": "object", ...},  # JSON Schema
    invocation_examples=[                  # 调用示例
        'rub myprotocol://api getUser id=123',
    ],
)
```

### ExecutionResult

操作执行结果（`execute` 返回值）。

```python
from rub.adapter import ExecutionResult

ExecutionResult(
    data={"id": "123", "name": "Alice"},  # 返回数据（任意类型）
    status_code=200,                       # HTTP 状态码（可选）
    headers={"content-type": "json"},      # 响应头（可选）
)
```

---

## Hook 生命周期

Rub 基于 [pluggy](https://pluggy.readthedocs.io/) 定义了 6 个生命周期钩子。插件可以实现这些钩子来扩展 Rub 的行为，而无需修改核心代码。

### 钩子一览

| 钩子 | 触发时机 | 参数 | 返回值 |
|---|---|---|---|
| `on_before_discover` | 适配器检测开始前 | `url` | `None` |
| `on_after_discover` | 适配器选定后 | `url, adapter` | `None` |
| `on_before_execute` | 操作执行前 | `url, operation_id, args` | `None` |
| `on_after_execute` | 操作执行后 | `url, operation_id, result` | `None` |
| `on_before_auth` | 认证头注入前 | `url, profile` | `dict[str, str] \| None` |
| `on_error` | 任何阶段出错时 | `error` | `None` |

- **通知型钩子**（`on_before_discover` 等）：所有注册的实现都会被调用，返回值被忽略
- **首结果钩子**（`on_before_auth`）：第一个返回非 `None` 的实现胜出，其返回的 headers 将替换默认认证头

### 执行顺序

对于一次完整的操作调用（`rub <url> <op> k=v`），钩子按如下顺序触发：

```
1. on_before_discover(url)           ← 开始探测适配器
2.   adapter.can_handle(url)         ← 检测级联（非钩子）
3. on_after_discover(url, adapter)   ← 适配器选定
4. on_before_auth(url, profile)      ← 即将注入认证
5. on_before_execute(url, op, args)  ← 即将调用 execute()
6.   adapter.execute(...)            ← 实际执行（非钩子）
7. on_after_execute(url, op, result) ← 执行完成
```

出错时触发：`on_error(error)`

### 实现示例

```python
# src/rub_myprotocol/hooks.py
from __future__ import annotations

from typing import Any

from loguru import logger
from rub.hooks import hookimpl


class MyProtocolHooks:
    """MyProtocol 生命周期钩子。"""

    @hookimpl
    def on_before_execute(
        self, url: str, operation_id: str, args: dict[str, Any]
    ) -> None:
        """在操作执行前打印日志。"""
        logger.info("即将调用 {} on {}", operation_id, url)

    @hookimpl
    def on_error(self, error: Exception) -> None:
        """错误发生时记录日志。"""
        logger.error("MyProtocol 插件捕获错误: {}", error)
```

在 `__init__.py` 中导出，供 Rub 注册：

```python
from rub_myprotocol.adapter import MyProtocolAdapter
from rub_myprotocol.hooks import MyProtocolHooks

__all__ = ["MyProtocolAdapter", "MyProtocolHooks"]
```

---

## 独立 CLI 模式

Rub 提供了 `standalone_cli()` 工具，可以为任意适配器生成一个独立的命令行程序，跳过协议检测层，直接使用适配器。

创建 `src/rub_myprotocol/__main__.py`：

```python
"""独立 CLI 入口。"""

from rub.standalone import standalone_cli
from rub_myprotocol.adapter import MyProtocolAdapter

app = standalone_cli(
    MyProtocolAdapter(),
    name="myprotocol",
    default_url="myprotocol://default",
)

if __name__ == "__main__":
    app()
```

在 `pyproject.toml` 中注册 script 入口：

```toml
[project.scripts]
myprotocol = "rub_myprotocol.__main__:app"
```

安装后即可使用：

```bash
myprotocol -h                      # 发现操作
myprotocol hello -h                # 检视操作
myprotocol hello name=Alice        # 执行操作
```

---

## 测试指南

推荐使用 `pytest` + `pytest-asyncio` 编写测试。按功能划分测试类：

```python
# tests/test_adapter.py
from __future__ import annotations

import pytest
from rub_myprotocol.adapter import MyProtocolAdapter


@pytest.fixture
def adapter() -> MyProtocolAdapter:
    return MyProtocolAdapter()


class TestCanHandle:
    """协议检测测试。"""

    @pytest.mark.asyncio
    async def test_handles_own_scheme(self, adapter: MyProtocolAdapter) -> None:
        assert await adapter.can_handle("myprotocol://example") is True

    @pytest.mark.asyncio
    async def test_rejects_other_scheme(self, adapter: MyProtocolAdapter) -> None:
        assert await adapter.can_handle("https://example.com") is False


class TestListOperations:
    """操作发现测试。"""

    @pytest.mark.asyncio
    async def test_returns_operations(self, adapter: MyProtocolAdapter) -> None:
        ops = await adapter.list_operations("myprotocol://example")
        assert len(ops) >= 1
        assert ops[0].operation_id == "hello"


class TestDescribeOperation:
    """操作检视测试。"""

    @pytest.mark.asyncio
    async def test_describe_hello(self, adapter: MyProtocolAdapter) -> None:
        detail = await adapter.describe_operation("myprotocol://example", "hello")
        assert detail.operation_id == "hello"
        assert detail.input_schema is not None


class TestExecute:
    """操作执行测试。"""

    @pytest.mark.asyncio
    async def test_hello_with_name(self, adapter: MyProtocolAdapter) -> None:
        result = await adapter.execute(
            "myprotocol://example", "hello", {"name": "Alice"}
        )
        assert result.status_code == 200
        assert "Alice" in str(result.data)


class TestProtocolMeta:
    """协议元信息测试。"""

    @pytest.mark.asyncio
    async def test_protocol_name(self, adapter: MyProtocolAdapter) -> None:
        assert await adapter.protocol_name() == "myprotocol"

    @pytest.mark.asyncio
    async def test_priority(self, adapter: MyProtocolAdapter) -> None:
        assert await adapter.priority() == 100
```

运行测试：

```bash
uv run pytest -v
```

### 涉及 HTTP 请求的适配器

对于需要发起网络请求的适配器，使用 `unittest.mock` 模拟 `AsyncHTTPClient`：

```python
from unittest.mock import AsyncMock, patch

async def test_can_handle_remote(self, adapter):
    mock_response = AsyncMock()
    mock_response.is_success = True
    mock_response.json_body = {"myprotocol": "1.0"}

    with patch("rub_myprotocol.adapter.AsyncHTTPClient") as MockClient:
        instance = MockClient.return_value.__aenter__.return_value
        instance.get = AsyncMock(return_value=mock_response)
        assert await adapter.can_handle("https://example.com/api") is True
```

---

## 开发工作流

### 安装到开发环境

```bash
cd rub-myprotocol

# 使用 uv（推荐）
uv pip install -e ".[dev]"

# 或使用 pip
pip install -e ".[dev]"
```

`-e`（editable）模式下，代码修改立即生效，无需重新安装。

### 验证 Entry Point 注册

```bash
python -c "
import importlib.metadata
eps = importlib.metadata.entry_points(group='rub.adapters')
for ep in eps:
    print(f'{ep.name} = {ep.value}')
"
```

期望输出：

```
myprotocol = rub_myprotocol:MyProtocolAdapter
```

### 使用 Rub 测试

```bash
# 发现操作
rub myprotocol://test -h

# 检视操作
rub myprotocol://test hello -h

# 执行操作
rub myprotocol://test hello name=Alice
```

### 调试

增加日志级别查看检测过程：

```bash
rub myprotocol://test -h -vv
```

### 使用 AsyncHTTPClient 发起请求

Rub 提供了带连接池和重试机制的 HTTP 客户端：

```python
from rub.client import AsyncHTTPClient

async with AsyncHTTPClient(auth_headers=auth_headers) as client:
    resp = await client.get("https://api.example.com/data")
    if resp.is_success:
        data = resp.json_body
```

`AsyncHTTPClient` 的主要特性：
- 基于 httpx 的连接池
- 可配置超时（默认 30 秒）
- 自动重试（默认 3 次，针对连接和超时错误）
- 支持通过 `auth_headers` 注入认证头

---

## 发布

### 准备

1. 更新 `pyproject.toml` 中的 `version`
2. 添加 `README.md` 描述你的适配器
3. 添加 `LICENSE` 文件

### 构建与上传

```bash
# 构建分发包
uv build

# 上传到 PyPI
uv publish
```

### 用户安装

```bash
uv add rub-myprotocol
# 或
pip install rub-myprotocol
```

安装后，`rub` 自动发现并使用你的适配器——无需编辑配置文件，无需手动注册。

---

## 发布检查清单

- [ ] `pyproject.toml` 包含 `[project.entry-points.'rub.adapters']` 配置
- [ ] entry point 指向一个 `rub.adapter.Adapter` 的子类
- [ ] 6 个抽象方法全部实现（`protocol_name`、`priority`、`can_handle`、`list_operations`、`describe_operation`、`execute`）
- [ ] 类上定义了 `_priority` 属性（与 `priority()` 返回值一致）
- [ ] `can_handle()` 快速返回且无副作用
- [ ] `execute()` 接收并使用 `auth_headers` 参数
- [ ] 测试覆盖检测、发现、检视、执行四个阶段
- [ ] `pip install -e .` 安装成功
- [ ] entry point 可通过 `importlib.metadata.entry_points(group="rub.adapters")` 查到
- [ ] `rub <url> -h` 能正确发现你的适配器

---

## 常见问题与排错

### 适配器未被发现

```
No adapter could handle URL: ...
Attempted adapters: (none installed)
```

排查步骤：
1. 检查 entry point 是否注册：`python -c "import importlib.metadata; print(list(importlib.metadata.entry_points(group='rub.adapters')))"`
2. 确认包已安装：`pip list | grep rub-`
3. 检查 entry point 的值是否正确（`模块:类名` 格式）
4. 确认 `__init__.py` 中导出了适配器类

### 检测失败

- 增加日志级别：`rub <url> -h -vv` 查看调试输出
- 确认 `can_handle()` 不会抛出异常（异常会被捕获并跳过）
- 检查 URL 格式是否匹配你的检测逻辑

### 导入错误

- 确保 `rub` 核心包已在依赖中声明
- 检查 `__init__.py` 是否正确导出适配器类
- 验证 `[tool.hatch.build.targets.wheel]` 包含了你的源码目录

### 错误层次结构

Rub 使用以下错误类型（均继承自 `RubError`）：

| 错误类 | 含义 |
|---|---|
| `ProtocolDetectionError` | 没有适配器匹配该 URL |
| `SchemaRetrievalError` | 无法获取或解析远端 schema |
| `OperationNotFoundError` | 请求的操作不存在 |
| `InvalidArgumentsError` | 参数不匹配操作的 schema |
| `ExecutionError` | 操作执行过程中出错 |
| `AuthError` | 认证/授权失败 |

在适配器中抛出合适的错误类型，Rub 会自动将其转换为结构化的错误输出。

```python
from rub.errors import OperationNotFoundError

async def describe_operation(self, url: str, op_id: str) -> OperationDetail:
    if op_id not in self._operations:
        raise OperationNotFoundError(f"操作 '{op_id}' 不存在")
    ...
```

---

## 使用 AI Agent Skills 辅助开发

Rub 安装时会自动将两个 AI agent skill 安装到 `~/.agents/skills/` 目录。这些 skill 为 AI 编程助手（Claude Code、Copilot 等）提供结构化的工作流指导，帮助你更高效地使用 Rub 和开发插件。

如果 skill 未自动安装，可手动执行：

```bash
rub-install-skills
```

### rub skill — 执行流程规范

**路径：** `~/.agents/skills/rub/`

`rub` skill 定义了使用 Rub CLI 的标准执行流程，是所有 Rub 相关操作的基础规范。它指导 AI 助手按照正确的模式与 Rub 交互：

- **核心工作流**：discover → inspect → invoke 三步操作模式
- **认证配置**：Bearer Token、API Key、Custom Headers、OAuth2 的设置方式
- **输出契约**：JSON envelope 格式（`ok`、`kind`、`data`、`error`、`meta`），确保输出可预测、可解析
- **复用规则**：其他 skill 需要调用远端 API 时，应复用 `rub` skill 而非自行嵌入协议调用逻辑

当你让 AI 助手帮你调用 API、调试 Rub 命令或排查认证问题时，`rub` skill 会自动提供正确的操作步骤。

### rub-skill-creator skill — 插件生成指南

**路径：** `~/.agents/skills/rub-skill-creator/`

`rub-skill-creator` skill 专门指导 AI 助手生成 Rub 协议适配器插件。它提供了一套完整的插件开发工作流：

**核心工作流（9 步）：**

1. **明确协议** — 记录协议名称（如 `"graphql"`、`"grpc"`），确定 URL 检测策略
2. **探索协议行为** — 查阅官方文档，手动测试请求/响应格式
3. **确认认证需求** — 探测端点，记录所需的认证模型
4. **固定接口设计** — 确定 `protocol_name`、`priority`、`can_handle` 策略、操作发现方式
5. **实现适配器方法** — `can_handle`、`list_operations`、`describe_operation`、`execute`
6. **编写测试** — 协议检测、操作发现、执行、认证注入的完整测试
7. **注册 entry point** — 在 `pyproject.toml` 中配置
8. **编写 README** — 含使用示例
9. **验证安装** — 确认 `rub <url> -h` 正常工作

**硬性规则：**
- 协议名称必须唯一
- `can_handle()` 必须确定性且快速
- `execute()` 必须注入 `auth_headers`
- 测试覆盖率不低于 80%
- 不硬编码凭证，使用 `auth_headers` 参数

**内置模板（`references/templates.md`）：**

该 skill 附带三种即用模板：

- **最小适配器模板** — scheme 检测 + 硬编码操作，适合快速验证
- **REST API 适配器模板** — 固定操作目录 + 路径参数替换，适合包装已知 API
- **测试模板** — 检测、发现、执行三类测试的标准结构

### 使用示例

在支持 skill 的 AI 编程环境（如 Claude Code）中，你可以直接使用这些 skill：

```
# 让 AI 助手帮你创建一个 GraphQL 适配器
/rub-skill-creator 我需要创建一个 rub-graphql 插件，目标端点是 https://api.example.com/graphql

# 让 AI 助手帮你调用 API
/rub 帮我查看 https://petstore3.swagger.io/api/v3 有哪些操作
```

AI 助手会自动遵循 skill 中定义的工作流和硬性规则，产出结构规范的代码和配置。

---

## 参考项目

- **rub-echo**（`packages/rub-echo/`）— 最简示例插件，无网络请求，适合理解插件结构
- **OpenAPI Adapter**（`src/rub/adapters/openapi/`）— 内置适配器，展示了带 HTTP 请求的完整实现
