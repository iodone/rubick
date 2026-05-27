# Rub 使用模式

## 核心工作流示例

### Discover → Inspect → Execute 流程

```bash
# 1. Discover — 发现所有操作
rub https://petstore3.swagger.io/api/v3 -h

# 2. Inspect — 检查目标操作的参数
rub https://petstore3.swagger.io/api/v3 getPetById -h

# 3. Execute — 执行调用
rub https://petstore3.swagger.io/api/v3 getPetById petId=1
```

### 认证配置流程

```bash
# 1. 创建凭证
rub auth set prod-key --type bearer --secret "sk-xxxxxxxxxxxx"

# 2. 绑定别名
rub auth bind https://api.production.example.com prod-key --alias prod

# 3. 验证
rub auth bindings | grep prod

# 4. 使用
rub myapi://prod listUsers
```

### 多环境模式

```bash
# 配置凭证
rub auth set dev-key --secret "dev-token"
rub auth set staging-key --secret "staging-token"
rub auth set prod-key --secret "prod-token"

# 绑定别名
rub auth bind https://api-dev.example.com dev-key --alias dev
rub auth bind https://api-staging.example.com staging-key --alias staging
rub auth bind https://api-prod.example.com prod-key --alias prod

# 环境切换
rub myapi://dev getStatus
rub myapi://staging getStatus
rub myapi://prod getStatus
```

## 输入模式

### 简单参数

```bash
rub <url> createUser name=alice              # 字符串
rub <url> getPage limit=10 offset=20         # 数字
rub <url> updateSettings enabled=true        # 布尔
rub <url> searchUsers name=alice age=30      # 多参数
```

### 嵌套对象

```bash
# 点号路径
rub <url> updateProfile user.name=alice user.email=alice@example.com

# 等价 JSON
rub <url> updateProfile '{"user":{"name":"alice","email":"alice@example.com"}}'
```

### 数组

```bash
rub <url> getTags tags=alpha,beta,gamma
rub <url> getTags '{"tags":["alpha","beta","gamma"]}'
```

### 复杂负载

```bash
# 从文件读取
rub <url> createResource "$(cat payload.json)"

# 管道组合 jq
rub <url> createResource "$(echo '{}' | jq '.name="test" | .type="demo"')"
```

## 输出解析

```bash
# 提取数据
rub <url> <operation> | jq '.data'
rub <url> getUser id=123 | jq '.data.name'

# 错误处理
if rub <url> <operation> | jq -e '.ok'; then
  echo "成功"
else
  rub <url> <operation> | jq -r '.error.message'
fi

# 链式调用
USER_ID=$(rub <url> listUsers | jq -r '.data.users[0].id')
rub <url> getUser id=$USER_ID
```

## 最佳实践

| 类别 | 建议 |
|------|------|
| 安全 | 用 `rub auth set` 管理凭证，不要硬编码；用 `$API_TOKEN` 环境变量 |
| 命名 | 使用语义化别名如 `prod`、`staging`；避免泛用名如 `api`、`test` |
| 性能 | 读操作利用缓存，写操作加 `--no-cache`；善用别名减少 URL 解析开销 |
| 调试 | 认证失败先查 `rub auth bindings`；用 `jq '.error'` 提取错误详情 |
