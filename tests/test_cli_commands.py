"""
CLI命令功能测试

测试CLI命令的实际功能，包括list、status等命令。
"""

import pytest
import tempfile
import os
from pathlib import Path
from click.testing import CliRunner
from proxy_relay.cli import cli


class TestCLICommands:
    """CLI命令功能测试"""
    
    def setup_method(self):
        """测试前准备"""
        self.runner = CliRunner()
        
        # 创建临时配置文件
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, 'config.yaml')
        
        # 写入测试配置
        config_content = """
system:
  web_port: 8080
  web_auth:
    enabled: true
    username: admin
    password_hash: "$2b$12$test"
  log_level: INFO
  log_file: /var/log/proxy-relay/app.log
  database: /var/lib/proxy-relay/data.db

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
    monitoring_enabled: false
  - local_port: 1081
    name: "Test Proxy 2"
    api_provider_id: "provider1"
    upstream:
      server: "proxy2.example.com"
      port: 10001
      username: "user"
      password: "pass"
    monitoring_enabled: true
"""
        with open(self.config_file, 'w') as f:
            f.write(config_content)
    
    def teardown_method(self):
        """测试后清理"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_list_command_with_valid_config(self):
        """测试list命令使用有效配置"""
        result = self.runner.invoke(cli, ['--config', self.config_file, 'list'])
        assert result.exit_code == 0
        assert 'Test Proxy 1' in result.output
        assert 'Test Proxy 2' in result.output
        assert '1080' in result.output
        assert '1081' in result.output
        assert 'proxy1.example.com' in result.output
        assert 'proxy2.example.com' in result.output
    
    def test_list_command_verbose(self):
        """测试list命令详细模式"""
        result = self.runner.invoke(cli, ['--config', self.config_file, 'list', '--verbose'])
        assert result.exit_code == 0
        assert 'Test Proxy 1' in result.output
        assert 'Test Proxy 2' in result.output
        assert 'Protocol: socks5' in result.output
    
    def test_list_shows_authentication_status(self):
        """测试list命令显示认证状态"""
        result = self.runner.invoke(cli, ['--config', self.config_file, 'list'])
        assert result.exit_code == 0
        # Test Proxy 1 没有认证
        assert 'Authentication: No' in result.output
        # Test Proxy 2 有认证
        assert 'Authentication: Yes' in result.output
        assert 'username: user' in result.output
    
    def test_list_shows_monitoring_status(self):
        """测试list命令显示监控状态"""
        result = self.runner.invoke(cli, ['--config', self.config_file, 'list'])
        assert result.exit_code == 0
        assert 'Monitoring: Disabled' in result.output
        assert 'Monitoring: Enabled' in result.output
    
    def test_status_command_with_valid_config(self):
        """测试status命令使用有效配置"""
        result = self.runner.invoke(cli, ['--config', self.config_file, 'status'])
        assert result.exit_code == 0
        assert 'Proxy Relay System Status' in result.output
        assert 'Service Status:' in result.output
        assert 'Configured Proxies: 2' in result.output
        assert 'Web Port: 8080' in result.output
        assert 'Log Level: INFO' in result.output
    
    def test_status_shows_not_running(self):
        """测试status命令显示未运行状态"""
        result = self.runner.invoke(cli, ['--config', self.config_file, 'status'])
        assert result.exit_code == 0
        assert 'Not running' in result.output
    
    def test_stop_without_running_service(self):
        """测试stop命令在服务未运行时"""
        result = self.runner.invoke(cli, ['stop'])
        assert result.exit_code == 1
        assert 'not running' in result.output or 'PID file not found' in result.output
