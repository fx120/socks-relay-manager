# 出口代理池架构设计 (v1.2.0)

## 概述

v1.2.0 引入了出口代理池（Upstream Proxy Pool）架构，将出口代理管理与本地代理配置解耦，提供更灵活和可维护的代理管理方式。

## 核心概念

### 1. 出口代理池 (Upstream Proxy Pool)

独立管理所有出口代理服务器的配置库。

**特性：**
- 每个出口代理有唯一 ID
- 支持多种添加方式（手动、链接导入、API 获取）
- 可以独立测试、编辑、删除
- 支持标签分类（地区、速度等）
- 显示使用统计

**数据结构：**
```python
@dataclass
class UpstreamProxyPool:
    id: str                          # 唯一标识符，如 "upstream-001"
    name: str                        # 显示名称，如 "美国节点1"
    proxy: UpstreamProxy            # 代理配置
    enabled: bool = True            # 是否启用
    description: Optional[str]      # 描述信息
    tags: Optional[List[str]]       # 标签列表
```

### 2. 本地代理 (Local Proxy)

监听本地端口的 SOCKS5 代理。

**特性：**
- 通过 `upstream_id` 引用出口代理池中的代理
- 支持直连模式（不使用出口代理）
- 可以随时切换使用的出口代理
- 保持向后兼容（支持直接配置 upstream）

**数据结构：**
```python
@dataclass
class ProxyConfig:
    local_port: int                 # 本地监听端口
    name: str                       # 代理名称
    upstream_id: Optional[str]      # 引用出口代理池 ID（新增）
    upstream: Optional[UpstreamProxy]  # 直接配置（向后兼容）
    api_provider_id: Optional[str]  # API 提供商 ID
    monitoring_enabled: bool        # 是否启用监控
    local_username: Optional[str]   # 本地认证用户名
    local_password: Optional[str]   # 本地认证密码
```

## 架构优势

### 1. 解耦管理
- 出口代理和本地代理分离
- 修改出口代理不影响本地代理配置
- 便于批量管理和维护

### 2. 复用性
- 一个出口代理可被多个本地代理使用
- 减少重复配置
- 统一管理相同的出口代理

### 3. 灵活性
- 本地代理可随时切换出口代理
- 支持动态调整
- 便于测试和比较不同出口代理

### 4. 可维护性
- 集中管理所有出口代理
- 统一测试和验证
- 清晰的使用关系

## 数据流

```
┌─────────────────────────────────────────────────────────┐
│                    配置文件 (config.yaml)                 │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  upstream_proxies:                                       │
│    - id: upstream-001                                    │
│      name: "美国节点1"                                    │
│      proxy:                                              │
│        server: us.example.com                            │
│        port: 443                                         │
│        protocol: vless                                   │
│        ...                                               │
│                                                          │
│  proxies:                                                │
│    - local_port: 1080                                    │
│      name: "代理1"                                        │
│      upstream_id: upstream-001  ← 引用                   │
│      monitoring_enabled: true                            │
│                                                          │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│                  ConfigManager 加载配置                   │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│              ProxyManager 解析引用关系                     │
│  - 根据 upstream_id 查找对应的出口代理                     │
│  - 生成 sing-box 配置                                     │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│                  sing-box 配置文件                        │
│  inbound: socks5://0.0.0.0:1080                         │
│  outbound: vless://us.example.com:443                   │
└─────────────────────────────────────────────────────────┘
```

## Web 界面设计

### 1. 导航栏更新

```
┌─────────────────────────────────────────────────────────┐
│  [仪表板] [本地代理] [出口代理池] [API提供商] [设置]      │
│                        ↑ 新增                            │
└─────────────────────────────────────────────────────────┘
```

### 2. 出口代理池页面

```
┌─────────────────────────────────────────────────────────┐
│  出口代理池                          [+ 添加出口代理]     │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  [手动输入] [链接导入] [从API获取]                        │
│                                                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │ 名称      │ 服务器          │ 协议  │ 状态 │ 使用  │ │
│  ├────────────────────────────────────────────────────┤ │
│  │ 美国节点1 │ us.example.com  │ VLESS │ ✓   │ 2个  │ │
│  │           │ :443            │       │     │      │ │
│  │           │ [测试] [编辑] [删除]                   │ │
│  ├────────────────────────────────────────────────────┤ │
│  │ 日本节点1 │ jp.example.com  │ VLESS │ ✓   │ 1个  │ │
│  │           │ :443            │       │     │      │ │
│  │           │ [测试] [编辑] [删除]                   │ │
│  └────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

### 3. 本地代理页面更新

```
┌─────────────────────────────────────────────────────────┐
│  添加代理                                    [×]          │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  基本配置                                                 │
│  ┌──────────────┐  ┌──────────────┐                    │
│  │ 本地端口: 1080│  │ 名称: 代理1   │                    │
│  └──────────────┘  └──────────────┘                    │
│                                                          │
│  出口代理配置                                             │
│  ○ 直连模式（不使用出口代理）                             │
│  ● 使用出口代理                                          │
│                                                          │
│  ┌─────────────────────────────────────────────────┐   │
│  │ 选择出口代理:                                     │   │
│  │ [下拉选择] 美国节点1 (us.example.com:443) ▼     │   │
│  │                                                  │   │
│  │ 或者                                             │   │
│  │ [+ 添加新的出口代理]                             │   │
│  └─────────────────────────────────────────────────┘   │
│                                                          │
│  □ 立即开启可用性监控                                    │
│                                                          │
│  [取消]  [保存]                                          │
└─────────────────────────────────────────────────────────┘
```

## API 设计

### 出口代理池 API

```
GET    /api/upstream-proxies           # 获取所有出口代理
POST   /api/upstream-proxies           # 添加出口代理
GET    /api/upstream-proxies/{id}      # 获取单个出口代理
PUT    /api/upstream-proxies/{id}      # 更新出口代理
DELETE /api/upstream-proxies/{id}      # 删除出口代理
POST   /api/upstream-proxies/{id}/test # 测试出口代理
GET    /api/upstream-proxies/{id}/usage # 获取使用统计
```

### 本地代理 API 更新

```
POST   /api/proxies                    # 创建本地代理
  Body: {
    "local_port": 1080,
    "name": "代理1",
    "upstream_id": "upstream-001",     # 引用出口代理
    "monitoring_enabled": true
  }

PUT    /api/proxies/{port}             # 更新本地代理
  Body: {
    "upstream_id": "upstream-002"      # 切换出口代理
  }
```

## 配置文件格式

### 新格式 (v1.2.0)

```yaml
system:
  web_port: 8080
  log_level: INFO

monitoring:
  check_interval: 30
  failure_threshold: 3

# 出口代理池（新增）
upstream_proxies:
  - id: upstream-001
    name: "美国节点1"
    enabled: true
    description: "高速美国节点"
    tags: ["美国", "高速", "稳定"]
    proxy:
      server: us.example.com
      port: 443
      protocol: vless
      uuid: "550e8400-e29b-41d4-a716-446655440000"
      network: ws
      tls: true
      sni: us.example.com
  
  - id: upstream-002
    name: "日本节点1"
    enabled: true
    proxy:
      server: jp.example.com
      port: 443
      protocol: vless
      uuid: "660e8400-e29b-41d4-a716-446655440001"

# 本地代理
proxies:
  - local_port: 1080
    name: "代理1"
    upstream_id: upstream-001  # 引用出口代理池
    monitoring_enabled: true
  
  - local_port: 1081
    name: "代理2"
    upstream_id: upstream-002
    monitoring_enabled: false
  
  - local_port: 1082
    name: "直连代理"
    # 不指定 upstream_id，使用直连模式
    monitoring_enabled: false
```

### 向后兼容 (v1.1.0 格式)

```yaml
# 旧格式仍然支持
proxies:
  - local_port: 1080
    name: "代理1"
    upstream:  # 直接配置（向后兼容）
      server: us.example.com
      port: 443
      protocol: vless
      uuid: "..."
    monitoring_enabled: true
```

## 数据迁移

### 自动迁移策略

系统启动时自动检测配置格式：

1. **检测旧格式**：如果 `proxies` 中有 `upstream` 字段
2. **自动转换**：
   - 为每个 `upstream` 生成唯一 ID
   - 创建对应的 `upstream_proxies` 条目
   - 更新 `proxies` 使用 `upstream_id` 引用
3. **保存新格式**：备份旧配置，保存新格式
4. **日志记录**：记录迁移过程

### 迁移示例

**迁移前：**
```yaml
proxies:
  - local_port: 1080
    upstream:
      server: us.example.com
      port: 443
```

**迁移后：**
```yaml
upstream_proxies:
  - id: migrated-001  # 自动生成
    name: "us.example.com:443"  # 自动命名
    proxy:
      server: us.example.com
      port: 443

proxies:
  - local_port: 1080
    upstream_id: migrated-001  # 自动引用
```

## 实施计划

### Phase 1: 核心功能 ✅
- [x] 数据模型扩展
- [ ] 配置管理器更新
- [ ] 代理管理器更新

### Phase 2: 数据库支持
- [ ] 添加 upstream_proxies 表
- [ ] 更新查询和统计
- [ ] 数据迁移脚本

### Phase 3: Web API
- [ ] 出口代理池 CRUD API
- [ ] 本地代理 API 更新
- [ ] 测试和验证接口

### Phase 4: Web 界面
- [ ] 出口代理池管理页面
- [ ] 本地代理页面更新
- [ ] 导航栏更新

### Phase 5: 测试和文档
- [ ] 单元测试
- [ ] 集成测试
- [ ] 用户文档
- [ ] API 文档

## 兼容性

### 向后兼容

- ✅ 支持旧配置格式
- ✅ 自动迁移到新格式
- ✅ 保留旧配置备份
- ✅ API 保持兼容

### 升级路径

1. **v1.1.0 → v1.2.0**
   - 自动检测并迁移配置
   - 无需手动操作
   - 保留所有现有功能

2. **回滚支持**
   - 保留旧配置备份
   - 可以回退到 v1.1.0
   - 数据不丢失

## 性能考虑

### 优化点

1. **配置加载**
   - 缓存出口代理池
   - 延迟加载未使用的代理

2. **引用解析**
   - 构建 ID 索引
   - O(1) 查找复杂度

3. **Web 界面**
   - 分页显示
   - 按需加载详情

## 安全考虑

### 访问控制

- 出口代理池需要认证
- 敏感信息加密存储
- 操作日志记录

### 数据保护

- 配置文件权限控制
- 密码和 UUID 不明文显示
- 备份加密

## 总结

v1.2.0 的出口代理池架构提供了：

1. **更好的组织**：清晰的代理管理结构
2. **更高的灵活性**：轻松切换和复用代理
3. **更强的可维护性**：集中管理和测试
4. **完全兼容**：无缝升级，不影响现有功能

这个架构为未来的功能扩展（如代理池负载均衡、自动故障转移等）奠定了基础。
