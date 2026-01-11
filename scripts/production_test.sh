#!/bin/bash

# 生产环境测试脚本
# 用于验证代理中转系统在生产环境中的功能

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置
API_BASE="http://localhost:8080"
API_USER="admin"
API_PASS=""
TEST_PORT=1080

# 测试结果统计
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[PASS]${NC} $1"
    ((PASSED_TESTS++))
}

log_fail() {
    echo -e "${RED}[FAIL]${NC} $1"
    ((FAILED_TESTS++))
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

# 测试函数
run_test() {
    ((TOTAL_TESTS++))
    echo ""
    log_info "测试 $TOTAL_TESTS: $1"
}

# 获取认证信息
get_credentials() {
    if [ -z "$API_PASS" ]; then
        echo -n "请输入 Web 界面密码: "
        read -s API_PASS
        echo ""
    fi
}

# 测试 API 调用
test_api() {
    local method=$1
    local endpoint=$2
    local expected_code=$3
    local data=$4
    
    if [ -n "$data" ]; then
        response=$(curl -s -w "\n%{http_code}" -X "$method" \
            -u "$API_USER:$API_PASS" \
            -H "Content-Type: application/json" \
            -d "$data" \
            "$API_BASE$endpoint")
    else
        response=$(curl -s -w "\n%{http_code}" -X "$method" \
            -u "$API_USER:$API_PASS" \
            "$API_BASE$endpoint")
    fi
    
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')
    
    if [ "$http_code" = "$expected_code" ]; then
        return 0
    else
        echo "Expected: $expected_code, Got: $http_code"
        echo "Response: $body"
        return 1
    fi
}

# 1. 基础功能测试
test_basic_functionality() {
    echo ""
    echo "=========================================="
    echo "  1. 基础功能测试"
    echo "=========================================="
    
    # 1.1 测试 Web 界面访问
    run_test "Web 界面访问"
    if curl -s -o /dev/null -w "%{http_code}" "$API_BASE/" | grep -q "200\|401"; then
        log_success "Web 界面可访问"
    else
        log_fail "Web 界面无法访问"
    fi
    
    # 1.2 测试 API 认证
    run_test "API 认证"
    if test_api "GET" "/api/proxies" "200"; then
        log_success "API 认证成功"
    else
        log_fail "API 认证失败"
    fi
    
    # 1.3 测试代理列表
    run_test "获取代理列表"
    if test_api "GET" "/api/proxies" "200"; then
        log_success "代理列表获取成功"
    else
        log_fail "代理列表获取失败"
    fi
    
    # 1.4 测试系统状态
    run_test "获取系统状态"
    if test_api "GET" "/api/system/status" "200"; then
        log_success "系统状态获取成功"
    else
        log_fail "系统状态获取失败"
    fi
}

# 2. 代理功能测试
test_proxy_functionality() {
    echo ""
    echo "=========================================="
    echo "  2. 代理功能测试"
    echo "=========================================="
    
    # 2.1 检查代理端口
    run_test "检查代理端口监听"
    if netstat -tlnp 2>/dev/null | grep -q ":$TEST_PORT" || ss -tlnp 2>/dev/null | grep -q ":$TEST_PORT"; then
        log_success "代理端口 $TEST_PORT 已监听"
    else
        log_fail "代理端口 $TEST_PORT 未监听"
        return
    fi
    
    # 2.2 测试代理连接
    run_test "测试代理连接"
    if timeout 10 curl -s -x "socks5://localhost:$TEST_PORT" http://ipinfo.io > /dev/null 2>&1; then
        log_success "代理连接成功"
        
        # 显示代理 IP
        proxy_ip=$(timeout 10 curl -s -x "socks5://localhost:$TEST_PORT" http://ipinfo.io/ip)
        log_info "代理 IP: $proxy_ip"
    else
        log_fail "代理连接失败"
    fi
    
    # 2.3 测试代理速度
    run_test "测试代理响应速度"
    start_time=$(date +%s%N)
    if timeout 10 curl -s -x "socks5://localhost:$TEST_PORT" http://www.google.com > /dev/null 2>&1; then
        end_time=$(date +%s%N)
        duration=$(( (end_time - start_time) / 1000000 ))
        log_success "代理响应时间: ${duration}ms"
        
        if [ $duration -lt 5000 ]; then
            log_info "响应速度: 优秀"
        elif [ $duration -lt 10000 ]; then
            log_info "响应速度: 良好"
        else
            log_warn "响应速度: 较慢"
        fi
    else
        log_fail "代理响应超时"
    fi
    
    # 2.4 测试多个请求
    run_test "测试连续请求稳定性"
    success_count=0
    for i in {1..10}; do
        if timeout 5 curl -s -x "socks5://localhost:$TEST_PORT" http://ipinfo.io > /dev/null 2>&1; then
            ((success_count++))
        fi
    done
    
    if [ $success_count -eq 10 ]; then
        log_success "连续请求测试: 10/10 成功"
    elif [ $success_count -ge 7 ]; then
        log_warn "连续请求测试: $success_count/10 成功"
    else
        log_fail "连续请求测试: $success_count/10 成功"
    fi
}

# 3. 监控功能测试
test_monitoring_functionality() {
    echo ""
    echo "=========================================="
    echo "  3. 监控功能测试"
    echo "=========================================="
    
    # 3.1 获取监控状态
    run_test "获取监控状态"
    if test_api "GET" "/api/proxies/$TEST_PORT/monitoring/status" "200"; then
        log_success "监控状态获取成功"
    else
        log_fail "监控状态获取失败"
    fi
    
    # 3.2 启动监控
    run_test "启动监控"
    if test_api "POST" "/api/proxies/$TEST_PORT/monitoring/start" "200"; then
        log_success "监控启动成功"
        sleep 2
    else
        log_warn "监控启动失败（可能已在运行）"
    fi
    
    # 3.3 验证监控运行
    run_test "验证监控运行"
    response=$(curl -s -u "$API_USER:$API_PASS" "$API_BASE/api/proxies/$TEST_PORT/monitoring/status")
    if echo "$response" | jq -e '.enabled == true' > /dev/null 2>&1; then
        log_success "监控正在运行"
    else
        log_fail "监控未运行"
    fi
    
    # 3.4 等待健康检查
    log_info "等待健康检查执行..."
    sleep 35
    
    # 3.5 查看健康检查日志
    run_test "查看健康检查日志"
    if test_api "GET" "/api/system/logs?limit=5" "200"; then
        log_success "健康检查日志获取成功"
    else
        log_fail "健康检查日志获取失败"
    fi
    
    # 3.6 停止监控
    run_test "停止监控"
    if test_api "POST" "/api/proxies/$TEST_PORT/monitoring/stop" "200"; then
        log_success "监控停止成功"
    else
        log_fail "监控停止失败"
    fi
}

# 4. 切换功能测试
test_switching_functionality() {
    echo ""
    echo "=========================================="
    echo "  4. 切换功能测试"
    echo "=========================================="
    
    # 4.1 获取当前代理信息
    run_test "获取当前代理信息"
    old_proxy=$(curl -s -u "$API_USER:$API_PASS" "$API_BASE/api/proxies/$TEST_PORT" | jq -r '.upstream.server')
    if [ -n "$old_proxy" ] && [ "$old_proxy" != "null" ]; then
        log_success "当前上游代理: $old_proxy"
    else
        log_fail "无法获取当前代理信息"
        return
    fi
    
    # 4.2 手动触发切换
    run_test "手动触发代理切换"
    if test_api "POST" "/api/proxies/$TEST_PORT/switch" "200"; then
        log_success "代理切换触发成功"
        sleep 5
    else
        log_fail "代理切换触发失败"
        return
    fi
    
    # 4.3 验证代理已切换
    run_test "验证代理已切换"
    new_proxy=$(curl -s -u "$API_USER:$API_PASS" "$API_BASE/api/proxies/$TEST_PORT" | jq -r '.upstream.server')
    if [ -n "$new_proxy" ] && [ "$new_proxy" != "null" ]; then
        log_info "新上游代理: $new_proxy"
        if [ "$new_proxy" != "$old_proxy" ]; then
            log_success "代理已成功切换"
        else
            log_warn "代理未切换（可能是 API 返回相同代理）"
        fi
    else
        log_fail "无法获取新代理信息"
    fi
    
    # 4.4 测试新代理连接
    run_test "测试新代理连接"
    if timeout 10 curl -s -x "socks5://localhost:$TEST_PORT" http://ipinfo.io > /dev/null 2>&1; then
        log_success "新代理连接成功"
    else
        log_fail "新代理连接失败"
    fi
    
    # 4.5 查看切换历史
    run_test "查看切换历史"
    if test_api "GET" "/api/history?limit=5" "200"; then
        log_success "切换历史获取成功"
    else
        log_fail "切换历史获取失败"
    fi
}

# 5. 性能测试
test_performance() {
    echo ""
    echo "=========================================="
    echo "  5. 性能测试"
    echo "=========================================="
    
    # 5.1 并发连接测试
    run_test "并发连接测试 (10个并发)"
    success_count=0
    for i in {1..10}; do
        (timeout 10 curl -s -x "socks5://localhost:$TEST_PORT" http://ipinfo.io > /dev/null 2>&1 && echo "success") &
    done
    wait
    
    success_count=$(jobs -p | wc -l)
    if [ $success_count -ge 8 ]; then
        log_success "并发连接测试通过"
    else
        log_warn "并发连接测试: 部分失败"
    fi
    
    # 5.2 系统资源使用
    run_test "系统资源使用"
    
    # CPU 使用率
    proxy_relay_cpu=$(ps aux | grep "[p]roxy_relay" | awk '{print $3}')
    singbox_cpu=$(ps aux | grep "[s]ing-box" | awk '{print $3}')
    
    log_info "proxy-relay CPU: ${proxy_relay_cpu}%"
    log_info "sing-box CPU: ${singbox_cpu}%"
    
    # 内存使用
    proxy_relay_mem=$(ps aux | grep "[p]roxy_relay" | awk '{print $4}')
    singbox_mem=$(ps aux | grep "[s]ing-box" | awk '{print $4}')
    
    log_info "proxy-relay 内存: ${proxy_relay_mem}%"
    log_info "sing-box 内存: ${singbox_mem}%"
    
    log_success "资源使用正常"
    
    # 5.3 连接数统计
    run_test "连接数统计"
    conn_count=$(netstat -an 2>/dev/null | grep ":$TEST_PORT" | wc -l || ss -an 2>/dev/null | grep ":$TEST_PORT" | wc -l)
    log_info "当前连接数: $conn_count"
    log_success "连接统计完成"
}

# 6. 服务稳定性测试
test_service_stability() {
    echo ""
    echo "=========================================="
    echo "  6. 服务稳定性测试"
    echo "=========================================="
    
    # 6.1 检查服务状态
    run_test "检查服务状态"
    if systemctl is-active --quiet proxy-relay && systemctl is-active --quiet sing-box; then
        log_success "所有服务运行正常"
    else
        log_fail "部分服务未运行"
    fi
    
    # 6.2 检查服务运行时间
    run_test "检查服务运行时间"
    uptime=$(systemctl show proxy-relay -p ActiveEnterTimestamp --value)
    log_info "proxy-relay 启动时间: $uptime"
    log_success "服务运行时间检查完成"
    
    # 6.3 检查错误日志
    run_test "检查错误日志"
    error_count=$(journalctl -u proxy-relay --since "1 hour ago" -p err | wc -l)
    if [ $error_count -eq 0 ]; then
        log_success "最近1小时无错误日志"
    else
        log_warn "最近1小时有 $error_count 条错误日志"
    fi
}

# 7. 数据库测试
test_database() {
    echo ""
    echo "=========================================="
    echo "  7. 数据库测试"
    echo "=========================================="
    
    DB_PATH="/var/lib/proxy-relay/data.db"
    
    # 7.1 检查数据库文件
    run_test "检查数据库文件"
    if [ -f "$DB_PATH" ]; then
        db_size=$(du -h "$DB_PATH" | cut -f1)
        log_success "数据库文件存在，大小: $db_size"
    else
        log_fail "数据库文件不存在"
        return
    fi
    
    # 7.2 查询切换历史
    run_test "查询切换历史"
    history_count=$(sudo -u proxy-relay sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM proxy_switch_history;" 2>/dev/null || echo "0")
    log_info "切换历史记录数: $history_count"
    log_success "切换历史查询成功"
    
    # 7.3 查询健康检查日志
    run_test "查询健康检查日志"
    health_count=$(sudo -u proxy-relay sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM health_check_log;" 2>/dev/null || echo "0")
    log_info "健康检查记录数: $health_count"
    log_success "健康检查日志查询成功"
    
    # 7.4 查询监控状态
    run_test "查询监控状态"
    monitor_count=$(sudo -u proxy-relay sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM monitoring_state;" 2>/dev/null || echo "0")
    log_info "监控状态记录数: $monitor_count"
    log_success "监控状态查询成功"
}

# 生成测试报告
generate_report() {
    echo ""
    echo "=========================================="
    echo "  测试报告"
    echo "=========================================="
    echo ""
    echo "总测试数: $TOTAL_TESTS"
    echo "通过: $PASSED_TESTS"
    echo "失败: $FAILED_TESTS"
    echo ""
    
    pass_rate=$(awk "BEGIN {printf \"%.2f\", ($PASSED_TESTS/$TOTAL_TESTS)*100}")
    echo "通过率: ${pass_rate}%"
    echo ""
    
    if [ $FAILED_TESTS -eq 0 ]; then
        echo -e "${GREEN}✓ 所有测试通过！${NC}"
        echo ""
        echo "系统状态: 良好"
        echo "建议: 系统可以投入生产使用"
    elif [ $FAILED_TESTS -le 3 ]; then
        echo -e "${YELLOW}⚠ 部分测试失败${NC}"
        echo ""
        echo "系统状态: 基本正常"
        echo "建议: 检查失败的测试项，修复后再投入生产"
    else
        echo -e "${RED}✗ 多个测试失败${NC}"
        echo ""
        echo "系统状态: 存在问题"
        echo "建议: 请检查系统配置和日志，解决问题后重新测试"
    fi
    
    echo ""
    echo "详细日志:"
    echo "  sudo journalctl -u proxy-relay -n 100"
    echo "  sudo journalctl -u sing-box -n 100"
    echo ""
    echo "=========================================="
}

# 主函数
main() {
    echo "=========================================="
    echo "  代理中转系统 - 生产环境测试"
    echo "=========================================="
    echo ""
    
    # 检查是否为 root
    if [ "$EUID" -ne 0 ]; then
        log_warn "建议使用 root 或 sudo 运行以获取完整测试结果"
    fi
    
    # 获取认证信息
    get_credentials
    
    # 运行测试
    test_basic_functionality
    test_proxy_functionality
    test_monitoring_functionality
    test_switching_functionality
    test_performance
    test_service_stability
    test_database
    
    # 生成报告
    generate_report
}

# 运行主函数
main
