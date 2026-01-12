# VLESS 协议支持

本文档介绍如何在代理中转系统中使用 VLESS 协议。

## 概述

VLESS 是一种轻量级的代理协议，相比传统的 SOCKS5 和 HTTP 代理，VLESS 提供了更好的性能和更多的传输选项。

系统现在支持：
- ✅ VLESS 协议的上游代理
- ✅ 从 VLESS URL 导入配置
- ✅ 从 VLESS JSON 配置导入
- ✅ 多种传输协议（TCP、WebSocket、gRPC）
- ✅ TLS/XTLS 加密
- ✅ 自动健康监控

## VLESS 配置参数

### 必需参数

- `server`: 服务器地址
- `port`: 服务器端口
- `uuid`: VLESS 用户 ID（UUID 格式）
- `protocol`: 必须设置为 "vless"

### 可选参数

- `encryption`: 加密方式（默认: "none"）
- `network`: 传输协议（默认: "tcp"）
  - `tcp`: 原始 TCP
  - `ws`: WebSocket
  - `grpc`: gRPC
  - `http`: HTTP/2
- `flow`: 流控模式（如 "xtls-rprx-vision"）
- `tls`: 是否启用 TLS（默认: false）
- `sni`: TLS Server Name Indication
- `alpn`: Application-Layer Protocol Negotiation（列表）

### WebSocket 特定参数

- `ws_path`: WebSocket 路径（默认: "/"）
- `ws_host`: WebSocket Host 头

### gRPC 特定参数

- `grpc_service_name`: gRPC 服务名称

## 使用方法

### 方法 1: Web 界面导入（推荐）

通过 Web 管理界面可以快速导入 VLESS 代理配置：

#### 步骤：

1. **访问代理管理页面**
   - 打开浏览器访问 `http://your-server:8080/proxies`
   - 使用管理员账号登录

2. **点击"添加代理"按钮**

3. **填写基本信息**
   - 本地端口：输入要监听的端口（如 1080）
   - 名称：给代理起个名字（如 "My VLESS Proxy"）

4. **勾选"使用出口代理"**

5. **选择"链接导入"配置方式**

6. **粘贴 VLESS 链接**
   - 在输入框中粘贴完整的 VLESS URL
   - 支持格式：
     - VLESS URL: `vless://uuid@server:port?...`
     - JSON 配置: `{"server":"...","uuid":"..."}`

7. **点击"解析"按钮**
   - 系统会自动解析链接
   - 显示解析结果（服务器、端口、协议、传输方式等）
   - 自动填充所有配置字段

8. **（可选）启用监控**
   - 勾选"立即开启可用性监控"以启用自动健康检查

9. **点击"保存"**
   - 系统会自动应用配置并重启 sing-box

#### 界面截图说明：

```
┌─────────────────────────────────────────┐
│ 配置方式                                 │
│ ○ 手动输入  ● 链接导入  ○ 通过 API 获取 │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│ VLESS 链接 *                            │
│ ┌─────────────────────────────────────┐ │
│ │ vless://uuid@server:port?...        │ │
│ └─────────────────────────────────────┘ │
│ [解析] 按钮                              │
│                                         │
│ ✓ 解析成功                              │
│   服务器: example.com                   │
│   端口: 443                             │
│   协议: vless                           │
│   传输: ws [TLS]                        │
└─────────────────────────────────────────┘
```

### 方法 2: 从 VLESS URL 导入（命令行）

VLESS URL 格式：
```
vless://uuid@server:port?参数1=值1&参数2=值2#备注
```

#### 示例 1: 基本 TCP 连接

```bash
proxy-relay import-vless \
  "vless://550e8400-e29b-41d4-a716-446655440000@example.com:443" \
  1080
```

### 方法 3: 从 JSON 配置导入（命令行）

```bash
proxy-relay import-vless \
  "vless://550e8400-e29b-41d4-a716-446655440000@example.com:443?security=tls&sni=example.com" \
  1080 \
  --name "My VLESS Proxy"
```

#### 示例 3: WebSocket + TLS

```bash
proxy-relay import-vless \
  "vless://550e8400-e29b-41d4-a716-446655440000@example.com:443?type=ws&path=/ws&host=example.com&security=tls&sni=example.com" \
  1080 \
  --monitoring
```

#### 示例 4: gRPC + TLS

```bash
proxy-relay import-vless \
  "vless://550e8400-e29b-41d4-a716-446655440000@example.com:443?type=grpc&serviceName=myservice&security=tls&sni=example.com" \
  1080
```

#### 示例 5: 带 XTLS Vision

```bash
proxy-relay import-vless \
  "vless://550e8400-e29b-41d4-a716-446655440000@example.com:443?flow=xtls-rprx-vision&security=tls&sni=example.com" \
  1080
```

### 方法 3: 从 JSON 配置导入（命令行）

```bash
proxy-relay import-vless '{
  "server": "example.com",
  "port": 443,
  "uuid": "550e8400-e29b-41d4-a716-446655440000",
  "network": "ws",
  "tls": {
    "enabled": true,
    "sni": "example.com",
    "alpn": ["h2", "http/1.1"]
  },
  "ws": {
    "path": "/ws",
    "host": "example.com"
  }
}' 1080 --name "My Proxy"
```

### 方法 4: 手动配置文件

在 `config.yaml` 中添加 VLESS 代理：

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
      ws_host: "example.com"
    monitoring_enabled: true
```

## 命令行选项

### import-vless 命令

```bash
proxy-relay import-vless [OPTIONS] VLESS_INPUT PORT
```

**参数：**
- `VLESS_INPUT`: VLESS URL 或 JSON 配置（必需）
- `PORT`: 本地监听端口（必需）

**选项：**
- `--name, -n`: 代理名称（可选，默认自动生成）
- `--monitoring/--no-monitoring`: 启用/禁用自动监控（默认: 禁用）
- `--config, -c`: 配置文件路径（默认: /etc/proxy-relay/config.yaml）

## 配置示例

### 完整的 VLESS 配置示例

```yaml
system:
  web_port: 8080
  log_level: INFO
  database: /var/lib/proxy-relay/data.db

monitoring:
  check_interval: 30
  failure_threshold: 3
  check_timeout: 10
  check_url: "http://www.google.com"

proxies:
  # VLESS + WebSocket + TLS
  - local_port: 1080
    name: "VLESS WS"
    upstream:
      server: "example.com"
      port: 443
      protocol: "vless"
      uuid: "550e8400-e29b-41d4-a716-446655440000"
      network: "ws"
      tls: true
      sni: "example.com"
      alpn: ["h2", "http/1.1"]
      ws_path: "/ws"
      ws_host: "example.com"
    monitoring_enabled: true
  
  # VLESS + gRPC + TLS
  - local_port: 1081
    name: "VLESS gRPC"
    upstream:
      server: "example.com"
      port: 443
      protocol: "vless"
      uuid: "550e8400-e29b-41d4-a716-446655440000"
      network: "grpc"
      tls: true
      sni: "example.com"
      grpc_service_name: "myservice"
    monitoring_enabled: true
  
  # VLESS + TCP + XTLS
  - local_port: 1082
    name: "VLESS XTLS"
    upstream:
      server: "example.com"
      port: 443
      protocol: "vless"
      uuid: "550e8400-e29b-41d4-a716-446655440000"
      network: "tcp"
      flow: "xtls-rprx-vision"
      tls: true
      sni: "example.com"
    monitoring_enabled: true
```

## API 支持

如果你的代理提供商 API 返回 VLESS 配置，系统会自动识别并解析。

API 响应示例：

```json
{
  "code": 0,
  "data": {
    "proxy_list": [
      {
        "ip": "example.com",
        "port": 443,
        "protocol": "vless",
        "uuid": "550e8400-e29b-41d4-a716-446655440000",
        "network": "ws",
        "tls": true,
        "sni": "example.com",
        "ws_path": "/ws"
      }
    ]
  }
}
```

## 验证和测试

### 1. 验证配置

导入后，系统会自动验证配置并应用到 sing-box：

```bash
proxy-relay import-vless "vless://..." 1080
```

### 2. 检查状态

```bash
proxy-relay status
```

### 3. 测试连接

```bash
# 使用 curl 测试
curl -x socks5://127.0.0.1:1080 https://www.google.com

# 或使用 wget
wget -e use_proxy=yes -e socks_proxy=127.0.0.1:1080 https://www.google.com
```

### 4. 查看日志

```bash
# 查看应用日志
tail -f /var/log/proxy-relay/app.log

# 查看 sing-box 日志
sudo journalctl -u sing-box -f
```

## 故障排除

### 问题 1: 导入失败

**错误信息：** "Failed to parse VLESS configuration"

**解决方法：**
1. 检查 VLESS URL 格式是否正确
2. 确保 UUID 格式有效
3. 验证所有必需参数都已提供

### 问题 2: 连接失败

**错误信息：** "Connection refused" 或 "Timeout"

**解决方法：**
1. 验证服务器地址和端口是否正确
2. 检查 TLS 配置（SNI、ALPN）
3. 确认服务器支持指定的传输协议
4. 检查防火墙设置

### 问题 3: TLS 握手失败

**错误信息：** "TLS handshake failed"

**解决方法：**
1. 确认 SNI 设置正确
2. 检查 ALPN 配置
3. 验证服务器证书有效

### 问题 4: WebSocket 连接失败

**错误信息：** "WebSocket upgrade failed"

**解决方法：**
1. 检查 `ws_path` 是否正确
2. 验证 `ws_host` 设置
3. 确认服务器支持 WebSocket

## 性能优化

### 1. 选择合适的传输协议

- **TCP**: 最低延迟，适合直连
- **WebSocket**: 适合穿透防火墙
- **gRPC**: 适合多路复用场景
- **HTTP/2**: 适合 CDN 场景

### 2. 启用 XTLS

对于支持的服务器，使用 XTLS Vision 可以获得更好的性能：

```yaml
flow: "xtls-rprx-vision"
```

### 3. 配置 ALPN

根据服务器支持情况配置 ALPN：

```yaml
alpn: ["h2", "http/1.1"]
```

## 安全建议

1. **保护 UUID**: UUID 相当于密码，不要泄露
2. **使用 TLS**: 生产环境务必启用 TLS
3. **验证证书**: 确保 SNI 设置正确
4. **定期更换**: 定期更换 UUID 和服务器
5. **监控日志**: 定期检查异常连接

## 相关文档

- [快速开始](QUICKSTART.md)
- [配置说明](INSTALLATION.md)
- [故障排除](TROUBLESHOOTING.md)
- [API 文档](API.md)

## 技术支持

如有问题，请查看：
1. 系统日志：`/var/log/proxy-relay/app.log`
2. sing-box 日志：`sudo journalctl -u sing-box`
3. 配置文件：`/etc/proxy-relay/config.yaml`
