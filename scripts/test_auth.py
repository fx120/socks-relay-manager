#!/usr/bin/env python3
"""
测试认证功能的脚本
用于验证密码哈希是否正确
"""

import sys
import bcrypt

def test_password():
    """测试默认密码"""
    # 默认密码
    password = "admin123"
    
    # 配置文件中的哈希（需要去掉转义符）
    password_hash = "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYIq.Ejm2W2"
    
    print(f"测试密码: {password}")
    print(f"密码哈希: {password_hash}")
    print()
    
    # 验证密码
    try:
        result = bcrypt.checkpw(
            password.encode('utf-8'),
            password_hash.encode('utf-8')
        )
        
        if result:
            print("✓ 密码验证成功！")
            return 0
        else:
            print("✗ 密码验证失败！")
            return 1
            
    except Exception as e:
        print(f"✗ 验证过程出错: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(test_password())
