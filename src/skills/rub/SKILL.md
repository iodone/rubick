---
name: rub
description: 通过 Rub 通用 CLI 发现和调用 API。当需要列出操作、查看参数 schema、执行 OpenAPI（或自定义协议）调用时使用此技能。
metadata:
  short-description: 基于适配器架构的通用 API CLI
---

# Rub 技能

当任务需要调用远程 API，且该 API 通过 Rub 适配器系统暴露操作时，使用此技能。

## 适用场景

- 需要调用其他技能中的 API，且希望统一 CLI 工作流
- 接口为 OpenAPI 3.x / Swagger 2.x，或已安装自定义 Rub 适配器
- 需要确定性的机器可读输出（`ok`、`kind`、`data`、`error`）

不适用于纯本地文件操作且无远程接口的场景。

## 核心工作流：Discover → Inspect → Execute

### 1. Discover（发现）— 列出所有可用操作

```bash
rub <url> -h
```

返回该 API 的完整操作列表及简要说明。这是探索任何新 API 的第一步。

### 2. Inspect（检查）— 查看操作的参数 schema

```bash
rub <url> <operation> -h
```

返回该操作的详细参数定义，包括类型、是否必填、默认值等。在构造请求前务必先 inspect。

### 3. Execute（执行）— 发送请求并解析结果

```bash
# key/value 形式（推荐）
rub <url> <operation> key=value

# JSON 形式
rub <url> <operation> '<payload-json>'
```

**结果解析：**

- 成功：`.ok == true`，读取 `.data`
- 失败：`.ok == false`，检查 `.error.code` 和 `.error.message`

### 完整示例

```bash
# 1. 发现操作
rub https://petstore3.swagger.io/api/v3 -h

# 2. 检查参数
rub https://petstore3.swagger.io/api/v3 getPetById -h

# 3. 执行调用
rub https://petstore3.swagger.io/api/v3 getPetById petId=1
```

## 输入方式

- **key/value（推荐）**：`rub <url> <operation> field=value`
- **带类型 JSON 值**：`rub <url> <operation> 'count:=42'`（`:=` 后面的值会解析为 JSON 类型）
- **JSON positional**：`rub <url> <operation> '{"field":"value"}'`
- **JSON body（`--data/-d`）**：`rub <url> <operation> -d '{"field":"value"}'`，也支持 stdin `-d -`

不要通过 `--args` 传 JSON；始终用 positional 或 `--data` 形式。

### 复杂输入

```bash
# 嵌套对象 — 点号路径
rub <url> updateProfile user.name=alice user.email=alice@example.com

# 数组 — 逗号分隔
rub <url> getTags tags=alpha,beta,gamma

# 从文件读取
rub <url> createResource "$(cat payload.json)"

# 带类型值（数字和布尔不会被当作字符串）
rub <url> updateConfig 'limit:=100' 'enabled:=true'
```

## 认证配置

支持的认证类型：`bearer`、`api_key`、`basic`、`oauth2`、`custom`。

### Bearer Token

```bash
rub auth set my-token --type bearer --secret "your-secret-token"
rub auth bind https://api.example.com my-token
# 之后自动注入认证头
rub https://api.example.com getUser id=123
```

### API Key（Header 或 Query）

```bash
# Header 方式
rub auth set my-key --type api_key \
  --secret "your-key" \
  --location header \
  --param-name "X-API-Key"

# Query 方式
rub auth set my-key --type api_key \
  --secret "your-key" \
  --location query \
  --param-name "api_key"

rub auth bind https://api.example.com my-key
```

### 自定义 Headers（非标准认证）

```bash
rub auth set my-custom --type custom \
  --header "X-Custom-Token=abc123" \
  --header "X-Workspace-ID=456"

rub auth bind https://api.example.com my-custom
```

### 显式指定凭证

```bash
# 绑定多个凭证时，用 -c 指定使用哪个
rub -c my-token https://api.example.com getUser id=123
```

### Binding Meta 注入

绑定时可通过 `--meta` 向 adapter 注入额外参数：

```bash
rub auth bind https://api.example.com my-token --meta region=chnbj
# 执行时 region=chnbj 会自动注入到 args 中
```

### URL 别名

```bash
rub auth bind https://api-prod.example.com my-token --alias prod
rub myapi://prod getUser id=123
```

### 凭证管理

```bash
rub auth list         # 列出所有凭证
rub auth bindings     # 列出所有绑定
rub auth remove name  # 删除凭证
rub auth unbind url   # 解除绑定
```

## 输出契约（供其他技能复用）

其他技能应将此技能作为 API 执行层，仅消费稳定的 JSON 信封：

- 成功字段：`ok`、`kind`、`protocol`、`endpoint`、`operation`、`data`、`meta`
- 失败字段：`ok`、`error.code`、`error.message`、`meta`

默认输出为 JSON。可通过 `--format/-f` 切换：`json`（默认）、`table`（Rich 表格）、`text`。自动化场景不要使用 `table` 或 `text`。

## 协议检测

Rub 根据以下信息自动检测协议：

1. URL scheme（如 `https://`、自定义 scheme）
2. 内容探测（如获取 OpenAPI spec）
3. 适配器优先级（优先级越高越先尝试）

- **内置适配器**：OpenAPI（OpenAPI 3.x / Swagger 2.x）
- **外部适配器**：通过 Python entry points 安装的自定义协议适配器

## 缓存管理

```bash
rub cache stats       # 查看缓存状态
rub cache clear       # 清除缓存
rub <url> <op> --no-cache  # 禁用单次缓存
```

## 常见问题

| 问题 | 解决方案 |
|------|---------|
| "No credential matched for URL" | `rub auth list` + `rub auth bindings` 确认绑定是否存在 |
| "No adapter can handle this URL" | 确认 URL 返回有效的 OpenAPI spec，或安装对应适配器 |
| URL 别名无法解析 | `rub auth bindings \| grep <alias>` 检查配置 |

## 相关资源

- 使用模式示例：`references/usage-patterns.md`
