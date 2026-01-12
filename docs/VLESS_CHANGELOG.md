# VLESS 协议支持 - 更新日志

## 版本信息

**更新日期**: 2026-01-12  
**功能**: VLESS 协议支持和连接导入

## 新增功能

### 1. VLESS 协议支持

系统现在完全支持 VLESS 协议作为上游代理，包括：

- ✅ VLESS 基本协议支持
- ✅ 多种传输协议（TCP、WebSocket、gRPC、HTTP/2）
- ✅ TLS/XTLS 加密支持
- ✅ 流控模式（如 xtls-rprx-vision）
- ✅ 自定义 SNI 和 ALPN 配置

### 2. VLESS 连接导入

新增 `import-vless` 命令，支持快速导入 VLESS 配置：

```bash
# 从 VLESS URL 导入
proxy-relay import-vless "vless://uuid@server:port?..." 1080

# 从 JSON 配置导入
proxy-relay import-vless '{"server":"...","uuid":"..."}' 1081
```

### 3. 自动配置解析

- 自动识别 VLESS URL 和 JSON 格式
- 智能解析传输层配置（WebSocket、gRPC 等）
- 自动提取 TLS 配置参数

## 文件变更

### 新增文件

1. **src/proxy_relay/vless_parser.py**
   - VLESS URL 解析器
   - VLESS JSON 配置解析器
   - VLESS URL 生成器
   - 支持往返转换（URL ↔ Proxy ↔ URL）

2. **tests/test_vless_parser.py**
   - 完整的 VLESS 解析器测试套件
   - 20 个测试用例，覆盖所有功能
   - 测试通过率: 100%

3. **docs/VLESS_SUPPORT.md**
   - 完整的 VLESS 使用文档
   - 配置示例和最佳实践
   - 故障排除指南

### 修改文件

1. **src/proxy_relay/models.py**
   - 扩展 `UpstreamProxy` 模型，添加 VLESS 特定字段：
     - `uuid`: VLESS 用户 ID
     - `flow`: 流控模式
     - `encryption`: 加密方式
     - `network`: 传输协议
     - `tls`: TLS 启用标志
     - `sni`: TLS Server Name
     - `alpn`: ALPN 配置
     - `ws_path`, `ws_host`: WebSocket 配置
     - `grpc_service_name`: gRPC 配置
   - 添加 VLESS 协议验证逻辑

2. **src/proxy_relay/api_client.py**
   - 更新 API 响应解析器，支持 VLESS 协议
   - 自动识别并解析 VLESS 配置字段
   - 兼容现有的 SOCKS5/HTTP 协议

3. **src/proxy_relay/proxy_manager.py**
   - 更新 sing-box 配置生成器
   - 添加 VLESS outbound 配置生成
   - 支持 WebSocket、gRPC 传输层配置
   - 支持 TLS/XTLS 配置

4. **src/proxy_relay/cli.py**
   - 新增 `import-vless` 命令
   - 支持命令行参数：
     - `--name`: 自定义代理名称
     - `--monitoring`: 启用自动监控

5. **config.yaml.example**
   - 添加 VLESS 配置示例
   - 包含 WebSocket + TLS 示例
   - 包含 gRPC + TLS 示例

6. **README.md**
   - 更新功能特性列表
   - 添加 VLESS 导入示例
   - 添加文档链接

7. **docs/QUICK_REFERENCE.md**
   - 添加 VLESS 导入命令
   - 添加 VLESS 文档链接

## 技术细节

### VLESS URL 格式

```
vless://uuid@server:port?param1=value1&param2=value2#name
```

**支持的参数**:
- `encryption`: 加密方式（默认: none）
- `security`: 安全层（none, tls, reality）
- `type`: 传输协议（tcp, ws, grpc, http）
- `flow`: 流控模式（如 xtls-rprx-vision）
- `sni`: TLS Server Name
- `alpn`: ALPN（逗号分隔）
- `path`: WebSocket 路径
- `host`: WebSocket Host
- `serviceName`: gRPC 服务名

### sing-box 配置映射

VLESS 代理会生成如下 sing-box outbound 配置：

```json
{
  "type": "vless",
  "tag": "upstream-1080",
  "server": "example.com",
  "server_port": 443,
  "uuid": "550e8400-e29b-41d4-a716-446655440000",
  "flow": "xtls-rprx-vision",
  "tls": {
    "enabled": true,
    "server_name": "example.com",
    "alpn": ["h2", "http/1.1"]
  },
  "transport": {
    "type": "ws",
    "path": "/ws",
    "headers": {
      "Host": "example.com"
    }
  }
}
```

## 兼容性

### 向后兼容

- ✅ 完全兼容现有的 SOCKS5/HTTP 代理配置
- ✅ 现有配置文件无需修改
- ✅ 现有 API 响应格式继续支持
- ✅ 所有现有功能保持不变

### 协议支持

| 协议 | 状态 | 说明 |
|------|------|------|
| SOCKS5 | ✅ 支持 | 原有功能 |
| HTTP | ✅ 支持 | 原有功能 |
| HTTPS | ✅ 支持 | 原有功能 |
| VLESS | ✅ 新增 | 本次更新 |

### 传输层支持

| 传输层 | 状态 | 说明 |
|--------|------|------|
| TCP | ✅ 支持 | 默认传输 |
| WebSocket | ✅ 支持 | 支持自定义路径和 Host |
| gRPC | ✅ 支持 | 支持自定义服务名 |
| HTTP/2 | ✅ 支持 | 标准 HTTP/2 传输 |

## 测试覆盖

### 单元测试

- **test_vless_parser.py**: 20 个测试用例
  - URL 解析测试: 8 个
  - JSON 解析测试: 3 个
  - 自动检测测试: 3 个
  - URL 生成测试: 5 个
  - 往返转换测试: 1 个

### 测试结果

```
tests/test_vless_parser.py::TestVLESSParser::test_parse_basic_vless_url PASSED
tests/test_vless_parser.py::TestVLESSParser::test_parse_vless_url_with_tls PASSED
tests/test_vless_parser.py::TestVLESSParser::test_parse_vless_url_with_websocket PASSED
tests/test_vless_parser.py::TestVLESSParser::test_parse_vless_url_with_grpc PASSED
tests/test_vless_parser.py::TestVLESSParser::test_parse_vless_url_with_flow PASSED
... (共 20 个测试，全部通过)

================================================== 20 passed in 0.21s ===================================================
```

## 使用示例

### 示例 1: 导入基本 VLESS 代理

```bash
proxy-relay import-vless \
  "vless://550e8400-e29b-41d4-a716-446655440000@example.com:443" \
  1080
```

### 示例 2: 导入 WebSocket + TLS 代理

```bash
proxy-relay import-vless \
  "vless://550e8400-e29b-41d4-a716-446655440000@example.com:443?type=ws&path=/ws&security=tls&sni=example.com" \
  1080 \
  --name "My VLESS Proxy" \
  --monitoring
```

### 示例 3: 从 JSON 导入

```bash
proxy-relay import-vless '{
  "server": "example.com",
  "port": 443,
  "uuid": "550e8400-e29b-41d4-a716-446655440000",
  "network": "ws",
  "tls": {"enabled": true, "sni": "example.com"}
}' 1081
```

### 示例 4: 手动配置文件

```yaml
proxies:
  - local_port: 1080
    name: "VLESS Proxy"
    upstream:
      server: "example.com"
      port: 443
      protocol: "vless"
      uuid: "550e8400-e29b-41d4-a716-446655440000"
      network: "ws"
      tls: true
      sni: "example.com"
      ws_path: "/ws"
    monitoring_enabled: true
```

## 安全注意事项

1. **保护 UUID**: UUID 相当于密码，不要泄露或提交到版本控制
2. **使用 TLS**: 生产环境务必启用 TLS 加密
3. **验证证书**: 确保 SNI 设置正确，避免中间人攻击
4. **定期更换**: 定期更换 UUID 和服务器配置
5. **监控日志**: 定期检查异常连接和访问模式

## 性能建议

1. **选择合适的传输协议**:
   - TCP: 最低延迟，适合直连
   - WebSocket: 适合穿透防火墙
   - gRPC: 适合多路复用场景

2. **启用 XTLS**: 对于支持的服务器，使用 XTLS Vision 可以获得更好的性能

3. **配置 ALPN**: 根据服务器支持情况配置 ALPN，提高连接效率

## 已知限制

1. **Reality 协议**: 当前版本暂不支持 Reality 协议，计划在未来版本中添加
2. **多跳代理**: 暂不支持 VLESS 多跳配置
3. **自定义加密**: 仅支持标准的 VLESS 加密方式

## 未来计划

- [ ] 支持 Reality 协议
- [ ] 支持 VLESS 多跳配置
- [ ] Web 界面支持 VLESS 导入
- [ ] 批量导入 VLESS 配置
- [ ] VLESS 配置导出功能

## 相关文档

- [VLESS 支持文档](VLESS_SUPPORT.md)
- [快速开始](QUICKSTART.md)
- [配置说明](INSTALLATION.md)
- [故障排除](TROUBLESHOOTING.md)

## 贡献者

感谢所有为此功能做出贡献的开发者！

## 反馈

如有问题或建议，请通过以下方式反馈：
- GitHub Issues: https://github.com/fx120/socks-relay-manager/issues
- 邮件: support@example.com
