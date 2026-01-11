"""
认证模块测试
"""

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPBasicCredentials

from src.proxy_relay.auth import (
    hash_password,
    verify_password,
    AuthMiddleware,
    create_auth_dependency,
)
from src.proxy_relay.models import WebAuthConfig


class TestPasswordHashing:
    """密码哈希测试"""
    
    def test_hash_password(self):
        """测试密码哈希"""
        password = "test_password_123"
        hashed = hash_password(password)
        
        # 验证哈希后的密码不等于原密码
        assert hashed != password
        
        # 验证哈希后的密码是bcrypt格式
        assert hashed.startswith("$2b$")
        
        # 验证可以验证密码
        assert verify_password(password, hashed)
    
    def test_verify_password_correct(self):
        """测试验证正确的密码"""
        password = "correct_password"
        hashed = hash_password(password)
        
        assert verify_password(password, hashed) is True
    
    def test_verify_password_incorrect(self):
        """测试验证错误的密码"""
        password = "correct_password"
        wrong_password = "wrong_password"
        hashed = hash_password(password)
        
        assert verify_password(wrong_password, hashed) is False
    
    def test_verify_password_invalid_hash(self):
        """测试验证无效的哈希"""
        password = "test_password"
        invalid_hash = "not_a_valid_hash"
        
        assert verify_password(password, invalid_hash) is False


class TestAuthMiddleware:
    """认证中间件测试"""
    
    def test_auth_disabled(self):
        """测试认证禁用时允许任何凭据"""
        auth_config = WebAuthConfig(
            enabled=False,
            username="admin",
            password_hash=hash_password("password")
        )
        middleware = AuthMiddleware(auth_config)
        
        # 没有凭据应该通过
        result = middleware.verify_credentials(None)
        assert result == "anonymous"
        
        # 任何凭据也应该通过
        credentials = HTTPBasicCredentials(username="any", password="any")
        result = middleware.verify_credentials(credentials)
        assert result == "anonymous"
    
    def test_auth_enabled_correct_credentials(self):
        """测试认证启用时正确的凭据"""
        password = "test_password_123"
        auth_config = WebAuthConfig(
            enabled=True,
            username="admin",
            password_hash=hash_password(password)
        )
        middleware = AuthMiddleware(auth_config)
        
        # 正确的凭据应该通过
        credentials = HTTPBasicCredentials(username="admin", password=password)
        result = middleware.verify_credentials(credentials)
        
        assert result == "admin"
    
    def test_auth_enabled_wrong_username(self):
        """测试认证启用时错误的用户名"""
        password = "test_password_123"
        auth_config = WebAuthConfig(
            enabled=True,
            username="admin",
            password_hash=hash_password(password)
        )
        middleware = AuthMiddleware(auth_config)
        
        # 错误的用户名应该失败
        credentials = HTTPBasicCredentials(username="wrong_user", password=password)
        
        with pytest.raises(HTTPException) as exc_info:
            middleware.verify_credentials(credentials)
        
        assert exc_info.value.status_code == 401
        assert "Incorrect username or password" in exc_info.value.detail
    
    def test_auth_enabled_wrong_password(self):
        """测试认证启用时错误的密码"""
        password = "test_password_123"
        auth_config = WebAuthConfig(
            enabled=True,
            username="admin",
            password_hash=hash_password(password)
        )
        middleware = AuthMiddleware(auth_config)
        
        # 错误的密码应该失败
        credentials = HTTPBasicCredentials(username="admin", password="wrong_password")
        
        with pytest.raises(HTTPException) as exc_info:
            middleware.verify_credentials(credentials)
        
        assert exc_info.value.status_code == 401
        assert "Incorrect username or password" in exc_info.value.detail
    
    def test_auth_enabled_both_wrong(self):
        """测试认证启用时用户名和密码都错误"""
        password = "test_password_123"
        auth_config = WebAuthConfig(
            enabled=True,
            username="admin",
            password_hash=hash_password(password)
        )
        middleware = AuthMiddleware(auth_config)
        
        # 用户名和密码都错误应该失败
        credentials = HTTPBasicCredentials(username="wrong_user", password="wrong_password")
        
        with pytest.raises(HTTPException) as exc_info:
            middleware.verify_credentials(credentials)
        
        assert exc_info.value.status_code == 401
        assert "Incorrect username or password" in exc_info.value.detail


class TestCreateAuthDependency:
    """创建认证依赖测试"""
    
    def test_create_auth_dependency(self):
        """测试创建认证依赖函数"""
        password = "test_password"
        auth_config = WebAuthConfig(
            enabled=True,
            username="admin",
            password_hash=hash_password(password)
        )
        
        auth_dependency = create_auth_dependency(auth_config)
        
        # 验证返回的是可调用函数
        assert callable(auth_dependency)
        
        # 测试正确的凭据
        credentials = HTTPBasicCredentials(username="admin", password=password)
        result = auth_dependency(credentials)
        assert result == "admin"
    
    def test_create_auth_dependency_disabled(self):
        """测试创建禁用认证的依赖函数"""
        auth_config = WebAuthConfig(
            enabled=False,
            username="admin",
            password_hash=hash_password("password")
        )
        
        auth_dependency = create_auth_dependency(auth_config)
        
        # 没有凭据应该通过
        result = auth_dependency(None)
        assert result == "anonymous"
        
        # 任何凭据也应该通过
        credentials = HTTPBasicCredentials(username="any", password="any")
        result = auth_dependency(credentials)
        assert result == "anonymous"
