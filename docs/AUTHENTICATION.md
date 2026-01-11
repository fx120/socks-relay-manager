# Web认证配置指南

代理中转系统的Web管理界面支持HTTP Basic Auth认证，使用bcrypt算法对密码进行安全哈希。

## 认证配置

在配置文件 `config.yaml` 中配置Web认证：

```yaml
system:
  web_auth:
    enabled: true              # 是否启用认证
    username: admin            # 管理员用户名
    password_hash: <bcrypt_hash>  # bcrypt密码哈希
```

## 生成密码哈希

### 方法1: 使用提供的脚本（推荐）

运行密码哈希生成工具：

```bash
python scripts/generate_password_hash.py
```

脚本会提示你输入密码，并生成对应的bcrypt哈希值。

### 方法2: 使用Python命令

```bash
python -c "import bcrypt; print(bcrypt.hashpw(b'your_password', bcrypt.gensalt()).decode())"
```

将 `your_password` 替换为你想要的密码。

### 方法3: 使用Python交互式环境

```python
import bcrypt

# 生成密码哈希
password = "your_password"
hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
print(hashed.decode('utf-8'))
```

## 启用/禁用认证

### 启用认证

1. 生成密码哈希（见上文）
2. 在配置文件中设置：
   ```yaml
   system:
     web_auth:
       enabled: true
       username: admin
       password_hash: $2b$12$...  # 你生成的哈希值
   ```
3. 重启服务或重新加载配置

### 禁用认证

在配置文件中设置：

```yaml
system:
  web_auth:
    enabled: false
```

**注意**: 禁用认证后，任何人都可以访问Web管理界面，请谨慎使用。

## 使用认证

### 通过浏览器访问

1. 访问Web管理界面（如 `http://localhost:8080`）
2. 浏览器会弹出认证对话框
3. 输入配置的用户名和密码
4. 认证成功后即可访问管理界面

### 通过API访问

使用HTTP Basic Auth进行API调用：

```bash
# 使用curl
curl -u admin:your_password http://localhost:8080/api/proxies

# 使用Python requests
import requests
from requests.auth import HTTPBasicAuth

response = requests.get(
    'http://localhost:8080/api/proxies',
    auth=HTTPBasicAuth('admin', 'your_password')
)
```

## 安全建议

1. **修改默认密码**: 不要使用示例配置中的默认密码
2. **使用强密码**: 密码应包含大小写字母、数字和特殊字符，长度至少12位
3. **限制访问**: 使用防火墙限制Web界面只能从特定IP访问
4. **使用HTTPS**: 在生产环境中，建议在Web界面前配置反向代理（如Nginx）并启用HTTPS
5. **定期更换密码**: 定期更新管理员密码
6. **保护配置文件**: 确保配置文件权限正确，只有授权用户可以读取

## 配置文件权限

建议设置配置文件权限，防止未授权访问：

```bash
# 设置配置文件所有者
sudo chown proxy-relay:proxy-relay /etc/proxy-relay/config.yaml

# 设置配置文件权限（只有所有者可读写）
sudo chmod 600 /etc/proxy-relay/config.yaml
```

## 故障排查

### 认证失败

如果无法登录，检查以下几点：

1. **用户名是否正确**: 确认配置文件中的用户名与输入的用户名一致
2. **密码哈希是否正确**: 确认密码哈希是使用bcrypt生成的
3. **配置是否生效**: 重启服务或重新加载配置
4. **查看日志**: 检查日志文件中的认证相关错误信息

### 忘记密码

如果忘记密码：

1. 生成新的密码哈希
2. 编辑配置文件，更新 `password_hash` 字段
3. 重启服务或重新加载配置

### 临时禁用认证

如果需要临时禁用认证进行调试：

1. 编辑配置文件，设置 `enabled: false`
2. 重启服务
3. 完成调试后，记得重新启用认证

## 示例配置

### 开发环境（禁用认证）

```yaml
system:
  web_auth:
    enabled: false
    username: admin
    password_hash: null
```

### 生产环境（启用认证）

```yaml
system:
  web_auth:
    enabled: true
    username: admin
    password_hash: $2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYIeWeCrm4u
```

## 技术细节

### bcrypt算法

- **算法**: bcrypt
- **工作因子**: 12（默认）
- **盐值**: 自动生成
- **哈希长度**: 60字符

### HTTP Basic Auth

- **认证方案**: HTTP Basic Authentication
- **编码**: Base64
- **传输**: 建议使用HTTPS加密传输

### 安全特性

1. **密码哈希**: 使用bcrypt单向哈希，无法反向解密
2. **盐值**: 每个密码使用唯一的随机盐值
3. **慢速哈希**: bcrypt设计为计算密集型，防止暴力破解
4. **时间恒定比较**: 使用 `secrets.compare_digest` 防止时序攻击
