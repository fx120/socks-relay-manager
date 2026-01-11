"""
认证模块

提供Web API的认证功能，包括密码哈希和HTTP Basic Auth验证。
"""

import logging
import secrets
from typing import Optional
import bcrypt
from fastapi import HTTPException, Security, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from .models import WebAuthConfig

logger = logging.getLogger(__name__)

# HTTP Basic Auth 安全方案 (auto_error=False 允许在认证禁用时不强制要求凭据)
security = HTTPBasic(auto_error=False)


def hash_password(password: str) -> str:
    """
    使用bcrypt哈希密码
    
    Args:
        password: 明文密码
        
    Returns:
        str: bcrypt哈希后的密码
    """
    # 生成salt并哈希密码
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    验证密码是否匹配
    
    Args:
        plain_password: 明文密码
        hashed_password: bcrypt哈希后的密码
        
    Returns:
        bool: 密码是否匹配
    """
    try:
        return bcrypt.checkpw(
            plain_password.encode('utf-8'),
            hashed_password.encode('utf-8')
        )
    except Exception as e:
        logger.error(f"Password verification error: {e}")
        return False


class AuthMiddleware:
    """认证中间件"""
    
    def __init__(self, auth_config: WebAuthConfig):
        """
        初始化认证中间件
        
        Args:
            auth_config: Web认证配置
        """
        self.auth_config = auth_config
        logger.info(f"Auth middleware initialized (enabled={auth_config.enabled})")
    
    def verify_credentials(
        self,
        credentials: Optional[HTTPBasicCredentials] = Security(security)
    ) -> str:
        """
        验证HTTP Basic Auth凭据
        
        Args:
            credentials: HTTP Basic Auth凭据（可选）
            
        Returns:
            str: 验证通过的用户名
            
        Raises:
            HTTPException: 认证失败时抛出401错误
        """
        # 如果认证未启用，直接返回
        if not self.auth_config.enabled:
            return "anonymous"
        
        # 如果认证启用但未提供凭据，返回401错误
        if credentials is None:
            logger.warning("Authentication required but no credentials provided")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
                headers={"WWW-Authenticate": "Basic"},
            )
        
        # 验证用户名
        correct_username = secrets.compare_digest(
            credentials.username.encode('utf-8'),
            self.auth_config.username.encode('utf-8')
        )
        
        # 验证密码
        correct_password = False
        if self.auth_config.password_hash:
            correct_password = verify_password(
                credentials.password,
                self.auth_config.password_hash
            )
        
        # 如果用户名或密码不正确，返回401错误
        if not (correct_username and correct_password):
            logger.warning(f"Authentication failed for user: {credentials.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Basic"},
            )
        
        logger.debug(f"Authentication successful for user: {credentials.username}")
        return credentials.username


def create_auth_dependency(auth_config: WebAuthConfig):
    """
    创建认证依赖函数
    
    Args:
        auth_config: Web认证配置
        
    Returns:
        callable: 认证依赖函数
    """
    middleware = AuthMiddleware(auth_config)
    
    def auth_dependency(
        credentials: Optional[HTTPBasicCredentials] = Security(security)
    ) -> str:
        """认证依赖函数"""
        return middleware.verify_credentials(credentials)
    
    return auth_dependency
