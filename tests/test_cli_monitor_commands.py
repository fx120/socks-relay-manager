"""
CLI监控控制命令测试

测试monitor start、monitor stop、monitor status和switch命令。
"""

import pytest
import tempfile
import os
from pathlib import Path
from click.testing import CliRunner
from proxy_relay.cli import cli


class TestCLIMonitorCommands:
    """CLI监控控制命令测试"""
    
    def setup_method(self):
        """测试前准备"""
        self.runner = CliRunner()
        
        # 创建临时目录
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, 'config.yaml')
        self.db_file = os.path.join(self.temp_dir, 'data.db')
        
        # 写入测试配置
        config_content = f"""
system:
  web_port: 8080
  web_auth:
    enabled: true
    username: admin
    password_hash: "$2b$12$test"
  log_level: INFO
  log_file: {self.temp_dir}/app.log
  database: {self.db_file}

monitoring:
  check_interval: 30
  failure_threshold: 3
  check_timeout: 10
  check_url: "http://www.google.com"

api_providers:
  - id: "provider1"
    name: "Test Provider"
    enabled: true
    endpoint: "https://api.example.com/proxy"
    method: "GET"
    params:
      key: "value"
    timeout: 10
    retry_attempts: 3
    retry_backoff: 2
    response_format:
      type: "custom"
      success_field: "success"
      success_value: true
      data_path: "data"
      ip_field: "ip"
      port_field: "port"

proxies:
  - local_port: 1080
    name: "Test Proxy 1"
    api_provider_id: "provider1"
    upstream:
      server: "proxy1.example.com"
      port: 10000
      username: null
      password: null
      protocol: socks5
    monitoring_enabled: false
  - local_port: 1081
    name: "Test Proxy 2"
    api_provider_id: "provider1"
    upstream:
      server: "proxy2.example.com"
      port: 10001
      username: "user"
      password: "pass"
      protocol: socks5
    monitoring_enabled: true
"""
        with open(self.config_file, 'w') as f:
            f.write(config_content)
    
    def teardown_method(self):
        """测试后清理"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_monitor_status_no_monitoring(self):
        """测试monitor status命令在没有监控时"""
        result = self.runner.invoke(cli, ['--config', self.config_file, 'monitor', 'status'])
        assert result.exit_code == 0
        assert 'No monitoring status found' in result.output or 'Configured proxy ports' in result.output
    
    def test_monitor_start_invalid_port(self):
        """测试monitor start命令使用无效端口"""
        result = self.runner.invoke(cli, ['--config', self.config_file, 'monitor', 'start', '9999'])
        assert result.exit_code == 1
        assert 'Error' in result.output
    
    def test_monitor_stop_not_running(self):
        """测试monitor stop命令在监控未运行时"""
        result = self.runner.invoke(cli, ['--config', self.config_file, 'monitor', 'stop', '1080'])
        assert result.exit_code == 1
        assert 'Error' in result.output or 'not running' in result.output
    
    def test_switch_command_invalid_port(self):
        """测试switch命令使用无效端口"""
        result = self.runner.invoke(cli, ['--config', self.config_file, 'switch', '9999'])
        assert result.exit_code == 1
        assert 'Error' in result.output
        assert 'No proxy configuration found' in result.output
    
    def test_switch_command_help(self):
        """测试switch命令帮助信息"""
        result = self.runner.invoke(cli, ['switch', '--help'])
        assert result.exit_code == 0
        assert 'Manually trigger proxy replacement' in result.output
        assert '--api-provider' in result.output
    
    def test_monitor_start_help(self):
        """测试monitor start命令帮助信息"""
        result = self.runner.invoke(cli, ['monitor', 'start', '--help'])
        assert result.exit_code == 0
        assert 'Start monitoring' in result.output
    
    def test_monitor_stop_help(self):
        """测试monitor stop命令帮助信息"""
        result = self.runner.invoke(cli, ['monitor', 'stop', '--help'])
        assert result.exit_code == 0
        assert 'Stop monitoring' in result.output
    
    def test_monitor_status_help(self):
        """测试monitor status命令帮助信息"""
        result = self.runner.invoke(cli, ['monitor', 'status', '--help'])
        assert result.exit_code == 0
        assert 'Show monitoring status' in result.output


class TestCLIMonitorCommandsIntegration:
    """CLI监控控制命令集成测试（需要实际组件）"""
    
    def setup_method(self):
        """测试前准备"""
        self.runner = CliRunner()
        
        # 创建临时目录
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, 'config.yaml')
        self.db_file = os.path.join(self.temp_dir, 'data.db')
        
        # 写入测试配置
        config_content = f"""
system:
  web_port: 8080
  web_auth:
    enabled: true
    username: admin
    password_hash: "$2b$12$test"
  log_level: INFO
  log_file: {self.temp_dir}/app.log
  database: {self.db_file}

monitoring:
  check_interval: 5
  failure_threshold: 2
  check_timeout: 5
  check_url: "http://www.google.com"

api_providers:
  - id: "provider1"
    name: "Test Provider"
    enabled: true
    endpoint: "https://api.example.com/proxy"
    method: "GET"
    params:
      key: "value"
    timeout: 10
    retry_attempts: 3
    retry_backoff: 2
    response_format:
      type: "custom"
      success_field: "success"
      success_value: true
      data_path: "data"
      ip_field: "ip"
      port_field: "port"

proxies:
  - local_port: 1080
    name: "Test Proxy 1"
    api_provider_id: "provider1"
    upstream:
      server: "proxy1.example.com"
      port: 10000
      username: null
      password: null
      protocol: socks5
    monitoring_enabled: false
"""
        with open(self.config_file, 'w') as f:
            f.write(config_content)
    
    def teardown_method(self):
        """测试后清理"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_monitor_commands_basic_flow(self):
        """测试监控命令基本流程"""
        # 1. 检查初始状态
        result = self.runner.invoke(cli, ['--config', self.config_file, 'monitor', 'status'])
        assert result.exit_code == 0
        
        # 注意：由于监控需要后台线程，这里只测试命令是否能正确执行
        # 实际的监控功能测试应该在单元测试中进行
    
    def test_switch_command_with_missing_api_provider(self):
        """测试switch命令在缺少API提供商时"""
        # 创建一个没有api_provider_id的配置
        config_content = f"""
system:
  web_port: 8080
  web_auth:
    enabled: true
    username: admin
    password_hash: "$2b$12$test"
  log_level: INFO
  log_file: {self.temp_dir}/app.log
  database: {self.db_file}

monitoring:
  check_interval: 30
  failure_threshold: 3
  check_timeout: 10
  check_url: "http://www.google.com"

api_providers:
  - id: "provider1"
    name: "Test Provider"
    enabled: true
    endpoint: "https://api.example.com/proxy"
    method: "GET"
    params:
      key: "value"
    timeout: 10
    retry_attempts: 3
    retry_backoff: 2
    response_format:
      type: "custom"
      success_field: "success"
      success_value: true
      data_path: "data"
      ip_field: "ip"
      port_field: "port"

proxies:
  - local_port: 1080
    name: "Test Proxy 1"
    api_provider_id: null
    upstream:
      server: "proxy1.example.com"
      port: 10000
      username: null
      password: null
      protocol: socks5
    monitoring_enabled: false
"""
        config_file2 = os.path.join(self.temp_dir, 'config2.yaml')
        with open(config_file2, 'w') as f:
            f.write(config_content)
        
        result = self.runner.invoke(cli, ['--config', config_file2, 'switch', '1080'])
        assert result.exit_code == 1
        # 配置验证会在加载时失败，或者在switch命令中检测到缺少API提供商
        assert 'Error' in result.output
        assert ('api_provider_id cannot be empty' in result.output or 
                'No API provider specified' in result.output)
