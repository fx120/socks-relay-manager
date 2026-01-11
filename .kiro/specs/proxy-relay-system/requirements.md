# 需求文档

## 简介

代理中转系统是一个运行在Debian服务器上的SOCKS代理中转服务，用于为指纹浏览器提供稳定的代理连接。系统通过在本地提供多个SOCKS代理端口，每个端口连接到不同的上游代理服务器，实现代理服务器的无感切换，避免指纹浏览器重启。

## 术语表

- **Proxy_Relay_System**: 代理中转系统，本文档描述的整个系统
- **Local_SOCKS_Proxy**: 本地SOCKS代理，运行在中转服务器上的代理端口
- **Upstream_Proxy**: 上游代理服务器，实际提供代理服务的外部服务器
- **Health_Monitor**: 健康监控器，负责检测上游代理服务器的可用性
- **Proxy_Manager**: 代理管理器，负责管理代理配置和切换
- **Fingerprint_Browser**: 指纹浏览器，使用代理服务的客户端应用
- **API_Client**: API客户端，用于从供应商获取新的代理服务器信息

## 需求

### 需求 1: 本地SOCKS代理服务

**用户故事:** 作为指纹浏览器用户，我希望在中转服务器上有多个可用的SOCKS代理端口，以便不同的浏览器窗口可以使用不同的代理。

#### 验收标准

1. THE Proxy_Relay_System SHALL provide multiple local SOCKS5 proxy ports on the relay server
2. WHEN a Fingerprint_Browser connects to a Local_SOCKS_Proxy port, THE Proxy_Relay_System SHALL forward traffic to the configured Upstream_Proxy
3. WHERE a specific port is configured, THE Local_SOCKS_Proxy SHALL bind to that port and accept connections
4. WHEN an Upstream_Proxy is changed for a port, THE Local_SOCKS_Proxy SHALL maintain existing connections while routing new connections to the new upstream
5. THE Proxy_Relay_System SHALL support at least 10 concurrent Local_SOCKS_Proxy ports

### 需求 2: 上游代理配置管理

**用户故事:** 作为系统管理员，我希望能够为每个本地代理端口配置不同的上游代理服务器，以便实现灵活的代理分配。

#### 验收标准

1. WHEN configuring a Local_SOCKS_Proxy port, THE Proxy_Manager SHALL accept upstream proxy server address, port, and authentication credentials
2. THE Proxy_Manager SHALL store proxy configurations persistently
3. WHEN updating an upstream proxy configuration, THE Proxy_Manager SHALL apply changes without requiring system restart
4. THE Proxy_Manager SHALL validate upstream proxy configuration format before applying
5. WHERE authentication is required, THE Proxy_Manager SHALL support username and password authentication for upstream proxies

### 需求 3: 上游代理健康监控

**用户故事:** 作为系统管理员，我希望系统能够自动监控上游代理服务器的健康状态，以便及时发现失效的代理。

#### 验收标准

1. WHEN monitoring is started, THE Health_Monitor SHALL periodically check each configured Upstream_Proxy availability
2. THE Health_Monitor SHALL perform health checks at configurable intervals (default 30 seconds)
3. WHEN an Upstream_Proxy fails health check, THE Health_Monitor SHALL mark it as unhealthy
4. THE Health_Monitor SHALL use HTTP/HTTPS requests through the proxy to verify connectivity
5. WHEN an Upstream_Proxy fails consecutive health checks (configurable threshold, default 3), THE Health_Monitor SHALL trigger proxy replacement

### 需求 4: 自动代理切换

**用户故事:** 作为系统管理员，我希望当上游代理失效时系统能够自动获取新的代理并切换，以便保持业务连续性。

#### 验收标准

1. WHEN an Upstream_Proxy is marked as unhealthy, THE Proxy_Manager SHALL call the API_Client to obtain a new proxy
2. WHEN a new proxy is obtained, THE Proxy_Manager SHALL update the configuration for the affected Local_SOCKS_Proxy port
3. THE Proxy_Manager SHALL validate the new proxy before applying the configuration
4. WHEN proxy switching occurs, THE Proxy_Manager SHALL log the event with timestamp and proxy details
5. IF the API_Client fails to obtain a new proxy, THEN THE Proxy_Manager SHALL retry with exponential backoff (max 3 attempts)

### 需求 5: 监控任务控制

**用户故事:** 作为系统管理员，我希望能够手动启动和停止监控任务，以便在需要时才进行监控和切换，避免浪费上游IP资源。

#### 验收标准

1. THE Proxy_Relay_System SHALL provide a command to start monitoring for specific Local_SOCKS_Proxy ports
2. THE Proxy_Relay_System SHALL provide a command to stop monitoring for specific Local_SOCKS_Proxy ports
3. WHEN monitoring is stopped, THE Health_Monitor SHALL cease health checks and proxy switching for the specified ports
4. THE Proxy_Relay_System SHALL maintain monitoring state across system restarts
5. THE Proxy_Relay_System SHALL provide a command to query current monitoring status for all ports

### 需求 6: API集成

**用户故事:** 作为系统管理员，我希望系统能够调用代理供应商的API获取新的代理信息，以便自动补充失效的代理。

#### 验收标准

1. THE API_Client SHALL support configurable API endpoint for proxy provider
2. WHEN requesting a new proxy, THE API_Client SHALL send HTTP requests with required authentication
3. THE API_Client SHALL parse the API response and extract proxy server address, port, and credentials
4. IF the API request fails, THEN THE API_Client SHALL return an error with descriptive message
5. THE API_Client SHALL support configurable timeout for API requests (default 10 seconds)

### 需求 7: 配置管理

**用户故事:** 作为系统管理员，我希望通过配置文件管理系统设置，以便轻松调整系统行为。

#### 验收标准

1. THE Proxy_Relay_System SHALL read configuration from a JSON or YAML file at startup
2. THE configuration file SHALL specify local proxy ports, initial upstream proxies, monitoring intervals, and API settings
3. WHEN the configuration file is modified, THE Proxy_Relay_System SHALL support reloading configuration without full restart
4. IF the configuration file contains errors, THEN THE Proxy_Relay_System SHALL report validation errors and use previous valid configuration
5. THE Proxy_Relay_System SHALL provide example configuration file templates

### 需求 8: 日志和监控

**用户故事:** 作为系统管理员，我希望系统记录详细的操作日志，以便排查问题和监控系统运行状态。

#### 验收标准

1. THE Proxy_Relay_System SHALL log all proxy switching events with timestamp, port, old proxy, and new proxy
2. THE Proxy_Relay_System SHALL log health check failures with timestamp and failure reason
3. THE Proxy_Relay_System SHALL log API calls with timestamp, request, and response status
4. THE Proxy_Relay_System SHALL support configurable log levels (DEBUG, INFO, WARN, ERROR)
5. THE Proxy_Relay_System SHALL rotate log files when they exceed configurable size (default 100MB)

### 需求 9: 命令行界面

**用户故事:** 作为系统管理员，我希望通过命令行工具管理代理中转系统，以便方便地执行各种操作。

#### 验收标准

1. THE Proxy_Relay_System SHALL provide a CLI command to start the proxy relay service
2. THE Proxy_Relay_System SHALL provide a CLI command to stop the proxy relay service
3. THE Proxy_Relay_System SHALL provide a CLI command to list all configured proxy ports and their status
4. THE Proxy_Relay_System SHALL provide a CLI command to start/stop monitoring for specific ports
5. THE Proxy_Relay_System SHALL provide a CLI command to manually trigger proxy replacement for a specific port

### 需求 10: Web管理面板

**用户故事:** 作为系统管理员，我希望通过Web界面管理代理配置和监控状态，以便更直观地操作系统。

#### 验收标准

1. THE Proxy_Relay_System SHALL provide a web-based management interface accessible via HTTP
2. WHEN accessing the web panel, THE Proxy_Relay_System SHALL display all configured Local_SOCKS_Proxy ports with their status
3. THE web panel SHALL allow adding, editing, and deleting Local_SOCKS_Proxy port configurations
4. THE web panel SHALL allow configuring Upstream_Proxy settings for each port including address, port, and credentials
5. THE web panel SHALL provide controls to start and stop monitoring for each port
6. THE web panel SHALL display real-time health status for each Upstream_Proxy
7. THE web panel SHALL show proxy switching history with timestamps
8. THE web panel SHALL support authentication to prevent unauthorized access
9. THE web panel SHALL be responsive and usable on mobile devices
10. THE web panel SHALL provide a dashboard view showing overall system status

### 需求 11: 系统服务集成

**用户故事:** 作为系统管理员，我希望代理中转系统能够作为系统服务运行，以便开机自启动和后台运行。

#### 验收标准

1. THE Proxy_Relay_System SHALL provide a systemd service unit file for Debian systems
2. WHEN installed as a service, THE Proxy_Relay_System SHALL start automatically on system boot
3. THE Proxy_Relay_System SHALL support graceful shutdown when receiving SIGTERM signal
4. THE Proxy_Relay_System SHALL support service status checking through systemd
5. THE Proxy_Relay_System SHALL run as a non-root user with appropriate permissions
