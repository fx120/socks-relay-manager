# Web 界面 VLESS 链接导入功能

## 功能概述

Web 管理界面现已支持通过链接导入 VLESS 代理配置，无需手动填写复杂的配置参数。

## 使用步骤

### 1. 访问代理管理页面

打开浏览器访问：`http://your-server:8080/proxies`

### 2. 添加新代理

点击页面右上角的"添加代理"按钮。

### 3. 填写基本信息

- **本地端口**：输入要监听的端口号（1024-65535）
- **名称**：为代理起一个便于识别的名称

### 4. 启用出口代理

勾选"使用出口代理"复选框。

### 5. 选择配置方式

在"配置方式"中选择"链接导入"选项。

### 6. 粘贴 VLESS 链接

在"VLESS 链接"输入框中粘贴完整的 VLESS 连接字符串。

支持的格式：
- **VLESS URL**: `vless://uuid@server:port?param1=value1&param2=value2`
- **JSON 配置**: `{"server":"...","port":443,"uuid":"..."}`

### 7. 解析链接

点击"解析"按钮，系统会自动：
- 验证链接格式
- 提取所有配置参数
- 显示解析结果
- 自动填充表单字段

### 8. 确认配置

解析成功后，会显示绿色的成功提示框，包含：
- 服务器地址
- 端口号
- 协议类型
- 传输方式
- TLS 状态

### 9. （可选）启用监控

如需自动健康检查，勾选"立即开启可用性监控"。

### 10. 保存配置

点击"保存"按钮，系统会：
- 验证配置
- 保存到配置文件
- 应用到 sing-box
- 重启代理服务

## 支持的协议

### VLESS 协议

完整支持 VLESS 协议的所有特性：

- ✅ 基本 TCP 传输
- ✅ WebSocket (ws)
- ✅ gRPC
- ✅ HTTP/2
- ✅ TLS/XTLS 加密
- ✅ 流控模式（flow）
- ✅ 自定义 SNI
- ✅ ALPN 配置

### 其他协议

同时支持传统代理协议：

- ✅ SOCKS5
- ✅ HTTP
- ✅ HTTPS

## 示例

### 示例 1: 基本 VLESS + WebSocket + TLS

**链接：**
```
vless://550e8400-e29b-41d4-a716-446655440000@example.com:443?type=ws&path=/ws&security=tls&sni=example.com
```

**解析结果：**
- 服务器: example.com
- 端口: 443
- 协议: vless
- 传输: ws [TLS]

### 示例 2: VLESS + gRPC + TLS

**链接：**
```
vless://550e8400-e29b-41d4-a716-446655440000@example.com:443?type=grpc&serviceName=myservice&security=tls&sni=example.com
```

**解析结果：**
- 服务器: example.com
- 端口: 443
- 协议: vless
- 传输: grpc [TLS]

### 示例 3: VLESS + XTLS Vision

**链接：**
```
vless://550e8400-e29b-41d4-a716-446655440000@example.com:443?flow=xtls-rprx-vision&security=tls&sni=example.com
```

**解析结果：**
- 服务器: example.com
- 端口: 443
- 协议: vless
- 传输: tcp [TLS]
- Flow: xtls-rprx-vision

## 界面说明

### 配置方式选项

```
┌─────────────────────────────────────────┐
│ 配置方式                                 │
│ ○ 手动输入                              │
│ ● 链接导入  ← 选择此项                  │
│ ○ 通过 API 获取                         │
└─────────────────────────────────────────┘
```

### 链接输入区域

```
┌─────────────────────────────────────────┐
│ VLESS 链接 *                            │
│ ┌─────────────────────────────────────┐ │
│ │ 粘贴 VLESS URL 或 JSON 配置         │ │
│ └─────────────────────────────────────┘ │
│                          [解析] 按钮    │
│                                         │
│ 支持 VLESS URL 或 JSON 配置格式         │
└─────────────────────────────────────────┘
```

### 解析成功提示

```
┌─────────────────────────────────────────┐
│ ✓ 解析成功                              │
│                                         │
│ 服务器: example.com                     │
│ 端口: 443                               │
│ 协议: vless                             │
│ 传输: ws [TLS]                          │
└─────────────────────────────────────────┘
```

## 常见问题

### Q1: 支持哪些 VLESS 链接格式？

**A:** 支持两种格式：
1. 标准 VLESS URL（以 `vless://` 开头）
2. JSON 配置对象

### Q2: 解析失败怎么办？

**A:** 检查以下几点：
1. 链接格式是否正确
2. 是否包含必需的参数（UUID、服务器、端口）
3. 特殊字符是否正确编码
4. JSON 格式是否有效

### Q3: 可以编辑已导入的配置吗？

**A:** 可以。点击代理列表中的"编辑"按钮，可以修改任何配置参数。

### Q4: 导入后可以切换到手动模式吗？

**A:** 可以。编辑代理时，选择"手动输入"模式，所有字段都可以手动修改。

### Q5: 支持批量导入吗？

**A:** 当前版本暂不支持批量导入，需要逐个添加。未来版本会考虑添加此功能。

## 技术细节

### API 端点

```
POST /api/proxies/parse-vless
```

**请求体：**
```json
{
  "link": "vless://uuid@server:port?..."
}
```

**响应：**
```json
{
  "server": "example.com",
  "port": 443,
  "protocol": "vless",
  "uuid": "550e8400-e29b-41d4-a716-446655440000",
  "network": "ws",
  "tls": true,
  "sni": "example.com",
  "ws_path": "/ws",
  "ws_host": "example.com"
}
```

### 前端实现

使用 Alpine.js 实现响应式界面：

```javascript
async parseVLESSLink() {
    const response = await fetch('/api/proxies/parse-vless', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ link: this.formData.vless_link })
    });
    
    if (response.ok) {
        const data = await response.json();
        // 自动填充表单
        this.formData.upstream = data;
    }
}
```

## 安全建议

1. **保护 UUID**: VLESS UUID 相当于密码，不要泄露
2. **使用 HTTPS**: 访问 Web 界面时使用 HTTPS
3. **强密码**: 为 Web 管理界面设置强密码
4. **限制访问**: 使用防火墙限制 Web 界面访问
5. **定期更换**: 定期更换 VLESS UUID 和服务器

## 相关文档

- [VLESS 完整支持文档](VLESS_SUPPORT.md)
- [快速开始指南](QUICKSTART.md)
- [Web API 文档](API.md)
- [故障排除](TROUBLESHOOTING.md)

## 更新日志

**v1.1.0** (2026-01-12)
- ✨ 新增 Web 界面链接导入功能
- ✨ 支持 VLESS URL 和 JSON 格式
- ✨ 自动解析和填充配置
- ✨ 实时显示解析结果
- 🐛 修复协议选择下拉框
- 📝 更新文档和示例

## 反馈

如有问题或建议，请通过以下方式反馈：
- GitHub Issues: https://github.com/fx120/socks-relay-manager/issues
- 文档: docs/TROUBLESHOOTING.md
