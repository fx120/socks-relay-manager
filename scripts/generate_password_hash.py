#!/usr/bin/env python3
"""
生成密码哈希工具

用于生成Web认证的bcrypt密码哈希。
"""

import sys
import getpass
from pathlib import Path

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from proxy_relay.auth import hash_password


def main():
    """主函数"""
    print("代理中转系统 - 密码哈希生成工具")
    print("=" * 50)
    print()
    
    # 获取密码
    while True:
        password = getpass.getpass("请输入密码: ")
        if not password:
            print("错误: 密码不能为空")
            continue
        
        password_confirm = getpass.getpass("请再次输入密码: ")
        
        if password != password_confirm:
            print("错误: 两次输入的密码不一致，请重试")
            print()
            continue
        
        break
    
    # 生成哈希
    print()
    print("正在生成密码哈希...")
    password_hash = hash_password(password)
    
    print()
    print("密码哈希生成成功！")
    print("=" * 50)
    print()
    print("请将以下哈希值复制到配置文件中：")
    print()
    print(password_hash)
    print()
    print("配置示例：")
    print()
    print("system:")
    print("  web_auth:")
    print("    enabled: true")
    print("    username: admin")
    print(f"    password_hash: {password_hash}")
    print()


if __name__ == "__main__":
    main()
