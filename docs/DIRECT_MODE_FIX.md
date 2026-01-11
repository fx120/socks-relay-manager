# 直连模式修复说明

## 问题描述

用户在创建直连模式代理（不勾选"使用出口代理"）时遇到验证错误：
```
proxies[0].api_provider_id 'None' not found in api_providers
```

## 根本原因

1. **验证逻辑缺陷**：`models.py` 和 `config_manager.py` 中的验证逻辑没有正确处理 `api_provider_id` 为 `None` 的情况
2. **空值检查缺失**：`web_api.py` 中的多个函数在访问 `proxy.upstream` 属性前没有检查是否为 `None`

## 修复内容

### 1. models.py
- 修改 `Config.__post_init__` 中的验证逻辑，使用 `is not None` 而不是 `if proxy.api_provider_id`
- 确保只在 `api_provider_id` 不为 `None` 时才验证其存在性

### 2. config_manager.py
- 修改 `validate_config` 方法，添加 `proxy.api_provider_id is not None` 检查
- 修改上游代理验证逻辑，允许 `upstream` 为 `None`（直连模式）

### 3. web_api.py
- 修改 `get_proxies` 函数，使用条件表达式处理 `upstream` 可能为 `None` 的情况
- 修改 `get_proxy` 函数，同样处理 `None` upstream
- 修改 `update_proxy` 函数，返回值中正确处理 `None` upstream
- 所有返回的代理配置中添加 `local_username` 和 `local_password` 字段

## 支持的三种模式

修复后系统支持以下三种代理模式：

### 1. 直连模式
- `use_upstream`: false
- `api_provider_id`: null
- `upstream`: null
- 使用本机网络直接连接
- 不支持监控

### 2. 手动上游代理模式
- `use_upstream`: true
- `upstream_mode`: "manual"
- `api_provider_id`: null
- `upstream`: { server, port, username, password, protocol }
- 手动配置上游代理信息
- 支持监控

### 3. API 上游代理模式
- `use_upstream`: true
- `upstream_mode`: "api"
- `api_provider_id`: "provider-id"
- `upstream`: null（初始为空，从 API 获取）
- 从 API 提供商自动获取代理
- 支持监控

## 测试

创建了 `tests/test_direct_mode.py` 测试文件，包含：
- 直连模式代理配置创建测试
- 直连模式不能启用监控的验证测试
- 包含直连模式代理的完整配置测试

所有测试通过。

## 部署

使用以下命令重新打包：
```bash
export COPYFILE_DISABLE=1 && tar -czf proxy-relay-deploy.tar.gz \
  --exclude='._*' --exclude='.DS_Store' --exclude='*.pyc' \
  --exclude='__pycache__' --exclude='.git' --exclude='.pytest_cache' \
  --exclude='venv' --exclude='.venv' --exclude='dev' --exclude='*.tar.gz' \
  src/ scripts/ config.yaml.example requirements.txt pyproject.toml \
  proxy-relay.service README.md .gitignore docs/
```

包大小：约 128KB

## 使用示例

### 创建直连模式代理
```json
{
  "local_port": 10810,
  "name": "Direct Proxy",
  "local_username": "qidian",
  "local_password": "password",
  "api_provider_id": null,
  "upstream": null,
  "monitoring_enabled": false
}
```

### 创建手动上游代理
```json
{
  "local_port": 10811,
  "name": "Manual Proxy",
  "local_username": "user",
  "local_password": "pass",
  "api_provider_id": null,
  "upstream": {
    "server": "proxy.example.com",
    "port": 1080,
    "username": "upstream_user",
    "password": "upstream_pass",
    "protocol": "socks5"
  },
  "monitoring_enabled": true
}
```

### 创建 API 上游代理
```json
{
  "local_port": 10812,
  "name": "API Proxy",
  "local_username": "user",
  "local_password": "pass",
  "api_provider_id": "my-provider",
  "upstream": null,
  "monitoring_enabled": true
}
```
