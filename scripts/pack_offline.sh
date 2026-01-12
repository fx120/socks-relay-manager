#!/bin/bash

# 离线部署包打包脚本
# 用于创建包含 sing-box 的离线部署包

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"

SINGBOX_VERSION="${SINGBOX_VERSION:-1.12.15}"
OUTPUT_DIR="${OUTPUT_DIR:-$PROJECT_DIR}"
PACKAGE_NAME="proxy-relay-offline"

show_help() {
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  -v, --version VERSION   sing-box 版本 (默认: $SINGBOX_VERSION)"
    echo "  -o, --output DIR        输出目录 (默认: 项目根目录)"
    echo "  -a, --arch ARCH         架构: amd64, arm64, all (默认: all)"
    echo "  -h, --help              显示帮助"
    echo ""
    echo "示例:"
    echo "  $0                      # 打包所有架构"
    echo "  $0 -a amd64             # 只打包 amd64"
    echo "  $0 -v 1.12.15 -a arm64  # 指定版本和架构"
}

ARCH="all"

while [[ $# -gt 0 ]]; do
    case $1 in
        -v|--version)
            SINGBOX_VERSION="$2"
            shift 2
            ;;
        -o|--output)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        -a|--arch)
            ARCH="$2"
            shift 2
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            log_error "未知选项: $1"
            show_help
            exit 1
            ;;
    esac
done

download_singbox() {
    local arch=$1
    local url="https://github.com/SagerNet/sing-box/releases/download/v${SINGBOX_VERSION}/sing-box-${SINGBOX_VERSION}-linux-${arch}.tar.gz"
    local output_file="$TEMP_DIR/bin/sing-box-${SINGBOX_VERSION}-linux-${arch}.tar.gz"
    
    log_info "下载 sing-box ${SINGBOX_VERSION} (${arch})..."
    log_info "URL: $url"
    
    if curl -L --fail --progress-bar "$url" -o "$output_file"; then
        log_info "✓ 下载完成: $output_file"
        return 0
    else
        log_error "✗ 下载失败: $url"
        return 1
    fi
}

main() {
    log_info "开始创建离线部署包..."
    log_info "sing-box 版本: $SINGBOX_VERSION"
    log_info "目标架构: $ARCH"
    
    # 创建临时目录
    TEMP_DIR=$(mktemp -d)
    trap "rm -rf $TEMP_DIR" EXIT
    
    log_info "临时目录: $TEMP_DIR"
    
    # 创建目录结构
    mkdir -p "$TEMP_DIR/bin"
    mkdir -p "$TEMP_DIR/src"
    mkdir -p "$TEMP_DIR/scripts"
    mkdir -p "$TEMP_DIR/docs"
    
    # 复制项目文件
    log_info "复制项目文件..."
    cp -r "$PROJECT_DIR/src/proxy_relay" "$TEMP_DIR/src/"
    cp -r "$PROJECT_DIR/scripts/"* "$TEMP_DIR/scripts/"
    [ -d "$PROJECT_DIR/docs" ] && cp -r "$PROJECT_DIR/docs/"* "$TEMP_DIR/docs/"
    cp "$PROJECT_DIR/requirements.txt" "$TEMP_DIR/"
    cp "$PROJECT_DIR/pyproject.toml" "$TEMP_DIR/"
    [ -f "$PROJECT_DIR/README.md" ] && cp "$PROJECT_DIR/README.md" "$TEMP_DIR/"
    [ -f "$PROJECT_DIR/config.yaml.example" ] && cp "$PROJECT_DIR/config.yaml.example" "$TEMP_DIR/"
    
    # 下载 sing-box
    log_info "下载 sing-box 二进制文件..."
    
    if [ "$ARCH" = "all" ]; then
        download_singbox "amd64" || log_warn "amd64 下载失败"
        download_singbox "arm64" || log_warn "arm64 下载失败"
    else
        download_singbox "$ARCH" || {
            log_error "sing-box 下载失败"
            exit 1
        }
    fi
    
    # 检查是否有下载成功的文件
    if [ -z "$(ls -A $TEMP_DIR/bin 2>/dev/null)" ]; then
        log_error "没有成功下载任何 sing-box 文件"
        exit 1
    fi
    
    # 创建安装说明
    cat > "$TEMP_DIR/INSTALL.md" << 'EOF'
# 离线部署说明

## 快速安装

```bash
# 解压部署包
tar -xzf proxy-relay-offline.tar.gz
cd proxy-relay-offline

# 运行离线部署脚本 (需要 root 权限)
sudo bash scripts/deploy_offline.sh
```

## 包含内容

- `src/` - 应用源代码
- `scripts/` - 部署和管理脚本
- `docs/` - 文档
- `bin/` - sing-box 二进制文件
- `requirements.txt` - Python 依赖
- `pyproject.toml` - 项目配置

## 系统要求

- Debian 11+ 或 Ubuntu 20.04+
- Python 3.11+
- root 权限

## 部署后

访问 Web 管理界面:
- URL: http://<服务器IP>:8080
- 用户名: admin
- 密码: admin123

首次登录后请立即修改密码！
EOF

    # 打包
    TIMESTAMP=$(date +%Y%m%d)
    PACKAGE_FILE="${PACKAGE_NAME}-${TIMESTAMP}.tar.gz"
    
    log_info "创建部署包: $PACKAGE_FILE"
    
    cd "$TEMP_DIR"
    tar -czf "$OUTPUT_DIR/$PACKAGE_FILE" .
    
    # 显示结果
    PACKAGE_SIZE=$(du -h "$OUTPUT_DIR/$PACKAGE_FILE" | cut -f1)
    
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║           ✅ 离线部署包创建完成！                          ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    echo "📦 部署包: $OUTPUT_DIR/$PACKAGE_FILE"
    echo "📊 大小: $PACKAGE_SIZE"
    echo ""
    echo "📋 包含的 sing-box 版本:"
    ls -la "$TEMP_DIR/bin/" | grep sing-box
    echo ""
    echo "🚀 部署方法:"
    echo ""
    echo "   1. 上传到目标服务器:"
    echo "      scp $PACKAGE_FILE user@server:/tmp/"
    echo ""
    echo "   2. 在服务器上解压并部署:"
    echo "      cd /tmp"
    echo "      tar -xzf $PACKAGE_FILE"
    echo "      cd ${PACKAGE_NAME}-${TIMESTAMP}"
    echo "      sudo bash scripts/deploy_offline.sh"
    echo ""
}

main
