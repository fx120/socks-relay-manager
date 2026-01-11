"""
基本CLI功能测试

测试CLI命令的基本功能，包括help、version和命令结构。
"""

import pytest
from click.testing import CliRunner
from proxy_relay.cli import cli


class TestCLIBasic:
    """CLI基本功能测试"""
    
    def setup_method(self):
        """测试前准备"""
        self.runner = CliRunner()
    
    def test_cli_help(self):
        """测试CLI帮助信息"""
        result = self.runner.invoke(cli, ['--help'])
        assert result.exit_code == 0
        assert 'Proxy Relay System' in result.output
        assert 'start' in result.output
        assert 'stop' in result.output
        assert 'status' in result.output
        assert 'list' in result.output
    
    def test_cli_version(self):
        """测试版本信息"""
        result = self.runner.invoke(cli, ['--version'])
        assert result.exit_code == 0
        assert '0.1.0' in result.output
    
    def test_start_command_help(self):
        """测试start命令帮助"""
        result = self.runner.invoke(cli, ['start', '--help'])
        assert result.exit_code == 0
        assert 'Start the proxy relay service' in result.output
    
    def test_stop_command_help(self):
        """测试stop命令帮助"""
        result = self.runner.invoke(cli, ['stop', '--help'])
        assert result.exit_code == 0
        assert 'Stop the proxy relay service' in result.output
    
    def test_status_command_help(self):
        """测试status命令帮助"""
        result = self.runner.invoke(cli, ['status', '--help'])
        assert result.exit_code == 0
        assert 'Show the status' in result.output
    
    def test_list_command_help(self):
        """测试list命令帮助"""
        result = self.runner.invoke(cli, ['list', '--help'])
        assert result.exit_code == 0
        assert 'List all configured proxy ports' in result.output
    
    def test_list_with_nonexistent_config(self):
        """测试使用不存在的配置文件"""
        result = self.runner.invoke(cli, ['--config', '/nonexistent/config.yaml', 'list'])
        assert result.exit_code == 1
        assert 'Configuration file not found' in result.output
    
    def test_status_with_nonexistent_config(self):
        """测试status命令使用不存在的配置文件"""
        result = self.runner.invoke(cli, ['--config', '/nonexistent/config.yaml', 'status'])
        assert result.exit_code == 0  # status命令即使配置不存在也应该返回状态
        assert 'Configuration file not found' in result.output or 'Not running' in result.output
