# VLESS Reality 调试指南

## 错误：unknown version: 72

这个错误表示 VLESS 协议握手失败，通常是 TLS/Reality 配置问题。

### 常见原因

1. **Reality Server Name 不匹配**
   - Reality Server Name 必须与 SNI 一致
   - 必须是真实存在的域名

2. **Public Key 错误**
   - Reality Public Key 必须是 43 个字符的 base64 字符串
   - 必须与服务器端配置完全一致

3. **Short ID 格式错误**
   - Short ID 必须是 1-16 个十六进制字符
   - 不能包含非十六进制字符

4. **缺少必要字段**
   - VLESS Reality 必须启用 TLS
   - 必须设置 server_name (SNI)

### 检查步骤

#### 1. 查看 sing-box 配置

```bash
sudo cat /etc/sing-box/config.json | python3 -m json.tool
```

#### 2. 检查 VLESS outbound 配置

正确的 Reality 配置应该包含：

```json
{
  "type": "vless",
  "tag": "upstream-10808",
  "server": "23.106.140.228",
  "server_port": 29517,
  "uuid": "23f46d47-ee18-4a8a-8567-c7373da9ed09",
  "tls": {
    "enabled": true,
    "server_name": "yahoo.com",
    "reality": {
      "enabled": true,
      "public_key": "zom-Pma-d81VT_WBhWx-IxzsymCZZ1mJrspT98wLT24",
      "short_id": "cdf169fff46a80"
    },
    "utls": {
      "enabled": true,
      "fingerprint": "chrome"
    }
  }
}
```

#### 3. 验证配置字段

**必须检查：**
- ✅ `tls.enabled` = true
- ✅ `tls.server_name` 已设置（与 Reality Server Name 一致）
- ✅ `tls.reality.enabled` = true
- ✅ `tls.reality.public_key` 长度为 43 字符
- ✅ `tls.reality.short_id` 是十六进制字符串
- ✅ `tls.utls.enabled` = true
- ✅ `tls.utls.fingerprint` 已设置

#### 4. 查看 sing-box 日志

```bash
sudo journalctl -u sing-box -n 100 --no-pager | grep -i error
```

### 常见错误模式

#### 错误 1: "unknown version: 72"
- **原因**: TLS 握手失败
- **解决**: 检查 server_name 是否正确，Reality 参数是否完整

#### 错误 2: "connection closed"
- **原因**: Reality 验证失败
- **解决**: 检查 public_key 和 short_id 是否与服务器端一致

#### 错误 3: "dial tcp: lookup xxx: no such host"
- **原因**: 服务器地址无法解析
- **解决**: 检查 server 字段是否正确

### 修复步骤

#### 方法 1: 重新导入链接

1. 访问 Web 界面 → 出口代理池
2. 编辑 VLESS 代理
3. 切换到"链接导入"
4. 重新粘贴 VLESS Reality 链接
5. 点击"解析链接"
6. 保存

#### 方法 2: 手动检查配置

1. 访问 Web 界面 → 出口代理池
2. 编辑 VLESS 代理
3. 确认以下字段：
   - 协议 = VLESS
   - 启用 TLS = ✓
   - SNI = yahoo.com (或其他真实域名)
   - 启用 Reality = ✓
   - Public Key = 完整的 43 字符
   - Short ID = 十六进制字符串
   - Server Name = 与 SNI 相同
   - uTLS Fingerprint = chrome (或其他)

#### 方法 3: 查看数据库配置

```bash
sudo sqlite3 /var/lib/proxy-relay/proxy_relay.db "SELECT * FROM upstream_proxies;"
```

### 测试连接

#### 使用 curl 测试

```bash
# 通过本地代理测试
curl -x socks5://127.0.0.1:10808 https://www.google.com -v
```

#### 查看实时日志

```bash
# 终端 1: 查看 sing-box 日志
sudo journalctl -u sing-box -f

# 终端 2: 发送测试请求
curl -x socks5://127.0.0.1:10808 https://www.google.com
```

### 获取帮助

如果问题仍然存在，请提供：

1. sing-box 配置文件内容
2. sing-box 错误日志
3. VLESS 链接（隐藏敏感信息）
4. 出口代理池配置截图

```bash
# 收集诊断信息
sudo cat /etc/sing-box/config.json > singbox-config.txt
sudo journalctl -u sing-box -n 200 --no-pager > singbox-logs.txt
sudo sqlite3 /var/lib/proxy-relay/proxy_relay.db "SELECT id, name, enabled FROM upstream_proxies;" > upstream-list.txt
```
