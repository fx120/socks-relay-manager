#!/bin/bash
#
# Proxy Relay System - Configuration Wizard
#
# Interactive configuration generator for the Proxy Relay System.
# This wizard helps users create a valid configuration file by
# asking questions and validating inputs.
#
# Usage: ./config_wizard.sh [output_file]
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Default output file
OUTPUT_FILE="${1:-config.yaml}"

# Configuration variables
WEB_PORT=8080
WEB_AUTH_ENABLED="true"
WEB_USERNAME="admin"
WEB_PASSWORD=""
LOG_LEVEL="INFO"
LOG_FILE="/var/log/proxy-relay/app.log"
DATABASE="/var/lib/proxy-relay/data.db"

MONITOR_CHECK_INTERVAL=30
MONITOR_FAILURE_THRESHOLD=3
MONITOR_CHECK_TIMEOUT=10
MONITOR_CHECK_URL="http://www.google.com"

API_PROVIDERS=()
PROXIES=()

# Function to print colored messages
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_question() {
    echo -e "${CYAN}[?]${NC} $1"
}

print_section() {
    echo
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo
}

# Function to read input with default value
read_with_default() {
    local prompt="$1"
    local default="$2"
    local var_name="$3"
    
    if [ -n "$default" ]; then
        read -p "$(echo -e ${CYAN}[?]${NC}) $prompt [$default]: " input
        eval "$var_name=\"${input:-$default}\""
    else
        read -p "$(echo -e ${CYAN}[?]${NC}) $prompt: " input
        eval "$var_name=\"$input\""
    fi
}

# Function to read password
read_password() {
    local prompt="$1"
    local var_name="$2"
    
    read -s -p "$(echo -e ${CYAN}[?]${NC}) $prompt: " password
    echo
    read -s -p "$(echo -e ${CYAN}[?]${NC}) Confirm password: " password_confirm
    echo
    
    if [ "$password" != "$password_confirm" ]; then
        print_error "Passwords do not match"
        return 1
    fi
    
    eval "$var_name=\"$password\""
    return 0
}

# Function to validate port number
validate_port() {
    local port="$1"
    
    if ! [[ "$port" =~ ^[0-9]+$ ]]; then
        return 1
    fi
    
    if [ "$port" -lt 1 ] || [ "$port" -gt 65535 ]; then
        return 1
    fi
    
    return 0
}

# Function to validate URL
validate_url() {
    local url="$1"
    
    if [[ "$url" =~ ^https?:// ]]; then
        return 0
    fi
    
    return 1
}

# Function to generate password hash
generate_password_hash() {
    local password="$1"
    
    # Check if Python is available
    if command -v python3 &> /dev/null; then
        python3 -c "import bcrypt; print(bcrypt.hashpw('$password'.encode(), bcrypt.gensalt()).decode())"
    else
        # Fallback: just return the password (not secure, but wizard will warn)
        echo "$password"
    fi
}

# Welcome message
show_welcome() {
    clear
    echo "=========================================="
    echo "  Proxy Relay System"
    echo "  Configuration Wizard"
    echo "=========================================="
    echo
    echo "This wizard will help you create a configuration"
    echo "file for the Proxy Relay System."
    echo
    echo "Press Enter to continue..."
    read
}

# Configure system settings
configure_system() {
    print_section "System Settings"
    
    # Web interface port
    while true; do
        read_with_default "Web interface port" "$WEB_PORT" WEB_PORT
        if validate_port "$WEB_PORT"; then
            break
        else
            print_error "Invalid port number (must be 1-65535)"
        fi
    done
    
    # Web authentication
    read_with_default "Enable web authentication? (true/false)" "$WEB_AUTH_ENABLED" WEB_AUTH_ENABLED
    
    if [ "$WEB_AUTH_ENABLED" = "true" ]; then
        read_with_default "Web username" "$WEB_USERNAME" WEB_USERNAME
        
        while true; do
            if read_password "Web password" WEB_PASSWORD; then
                if [ -z "$WEB_PASSWORD" ]; then
                    print_error "Password cannot be empty"
                else
                    break
                fi
            fi
        done
    fi
    
    # Log level
    print_question "Log level (DEBUG/INFO/WARN/ERROR)"
    echo "  DEBUG - Detailed debugging information"
    echo "  INFO  - General informational messages (recommended)"
    echo "  WARN  - Warning messages only"
    echo "  ERROR - Error messages only"
    read_with_default "Log level" "$LOG_LEVEL" LOG_LEVEL
    
    # Log file
    read_with_default "Log file path" "$LOG_FILE" LOG_FILE
    
    # Database
    read_with_default "Database file path" "$DATABASE" DATABASE
    
    print_info "✓ System settings configured"
}

# Configure monitoring settings
configure_monitoring() {
    print_section "Monitoring Settings"
    
    # Check interval
    read_with_default "Health check interval (seconds)" "$MONITOR_CHECK_INTERVAL" MONITOR_CHECK_INTERVAL
    
    # Failure threshold
    read_with_default "Failure threshold (consecutive failures)" "$MONITOR_FAILURE_THRESHOLD" MONITOR_FAILURE_THRESHOLD
    
    # Check timeout
    read_with_default "Check timeout (seconds)" "$MONITOR_CHECK_TIMEOUT" MONITOR_CHECK_TIMEOUT
    
    # Check URL
    while true; do
        read_with_default "Health check URL" "$MONITOR_CHECK_URL" MONITOR_CHECK_URL
        if validate_url "$MONITOR_CHECK_URL"; then
            break
        else
            print_error "Invalid URL (must start with http:// or https://)"
        fi
    done
    
    print_info "✓ Monitoring settings configured"
}

# Configure API provider
configure_api_provider() {
    local provider_id="$1"
    local provider_name
    local provider_enabled
    local provider_endpoint
    local provider_method
    local provider_timeout
    local provider_retry_attempts
    local provider_retry_backoff
    
    print_section "API Provider Configuration"
    
    if [ -z "$provider_id" ]; then
        read_with_default "Provider ID (e.g., provider1)" "provider1" provider_id
    fi
    
    read_with_default "Provider name" "API Provider" provider_name
    read_with_default "Enabled? (true/false)" "true" provider_enabled
    
    while true; do
        read_with_default "API endpoint URL" "" provider_endpoint
        if validate_url "$provider_endpoint"; then
            break
        else
            print_error "Invalid URL (must start with http:// or https://)"
        fi
    done
    
    read_with_default "HTTP method (GET/POST)" "GET" provider_method
    read_with_default "Timeout (seconds)" "10" provider_timeout
    read_with_default "Retry attempts" "3" provider_retry_attempts
    read_with_default "Retry backoff (seconds)" "2" provider_retry_backoff
    
    # API parameters
    print_info "Configure API parameters (key=value, empty to finish)"
    local params=()
    while true; do
        read -p "$(echo -e ${CYAN}[?]${NC}) Parameter (or press Enter to finish): " param
        if [ -z "$param" ]; then
            break
        fi
        params+=("$param")
    done
    
    # Response format
    print_question "Response format type"
    echo "  1. 91HTTP format (code, data.proxy_list)"
    echo "  2. Custom format"
    read_with_default "Select format (1/2)" "1" format_choice
    
    local response_type
    local success_field
    local success_value
    local data_path
    local ip_field
    local port_field
    
    if [ "$format_choice" = "1" ]; then
        response_type="91http"
        success_field="code"
        success_value="0"
        data_path="data.proxy_list"
        ip_field="ip"
        port_field="port"
    else
        response_type="custom"
        read_with_default "Success field name" "success" success_field
        read_with_default "Success value" "true" success_value
        read_with_default "Data path (e.g., data.proxies)" "data" data_path
        read_with_default "IP field name" "ip" ip_field
        read_with_default "Port field name" "port" port_field
    fi
    
    # Store provider configuration
    local provider_config="id: \"$provider_id\"
    name: \"$provider_name\"
    enabled: $provider_enabled
    endpoint: \"$provider_endpoint\"
    method: \"$provider_method\"
    timeout: $provider_timeout
    retry_attempts: $provider_retry_attempts
    retry_backoff: $provider_retry_backoff"
    
    if [ ${#params[@]} -gt 0 ]; then
        provider_config="$provider_config
    params:"
        for param in "${params[@]}"; do
            local key="${param%%=*}"
            local value="${param#*=}"
            provider_config="$provider_config
      $key: \"$value\""
        done
    fi
    
    provider_config="$provider_config
    response_format:
      type: \"$response_type\"
      success_field: \"$success_field\"
      success_value: $success_value
      data_path: \"$data_path\"
      ip_field: \"$ip_field\"
      port_field: \"$port_field\""
    
    API_PROVIDERS+=("$provider_config")
    
    print_info "✓ API provider configured"
}

# Configure proxy
configure_proxy() {
    local local_port
    local proxy_name
    local api_provider_id
    local upstream_server
    local upstream_port
    local upstream_username
    local upstream_password
    local monitoring_enabled
    
    print_section "Proxy Configuration"
    
    while true; do
        read_with_default "Local SOCKS5 port" "1080" local_port
        if validate_port "$local_port"; then
            break
        else
            print_error "Invalid port number (must be 1-65535)"
        fi
    done
    
    read_with_default "Proxy name" "Proxy $local_port" proxy_name
    
    # API provider selection
    if [ ${#API_PROVIDERS[@]} -gt 0 ]; then
        print_question "Select API provider for this proxy:"
        for i in "${!API_PROVIDERS[@]}"; do
            local provider_id=$(echo "${API_PROVIDERS[$i]}" | grep "id:" | cut -d'"' -f2)
            echo "  $((i+1)). $provider_id"
        done
        read_with_default "Provider number" "1" provider_num
        api_provider_id=$(echo "${API_PROVIDERS[$((provider_num-1))]}" | grep "id:" | cut -d'"' -f2)
    else
        read_with_default "API provider ID" "provider1" api_provider_id
    fi
    
    # Initial upstream proxy
    print_info "Configure initial upstream proxy (optional)"
    read_with_default "Upstream server (or leave empty)" "" upstream_server
    
    if [ -n "$upstream_server" ]; then
        while true; do
            read_with_default "Upstream port" "10000" upstream_port
            if validate_port "$upstream_port"; then
                break
            else
                print_error "Invalid port number"
            fi
        done
        
        read_with_default "Username (optional)" "" upstream_username
        if [ -n "$upstream_username" ]; then
            read_password "Password" upstream_password || upstream_password=""
        fi
    fi
    
    read_with_default "Enable monitoring? (true/false)" "false" monitoring_enabled
    
    # Store proxy configuration
    local proxy_config="- local_port: $local_port
    name: \"$proxy_name\"
    api_provider_id: \"$api_provider_id\""
    
    if [ -n "$upstream_server" ]; then
        proxy_config="$proxy_config
    upstream:
      server: \"$upstream_server\"
      port: $upstream_port"
        
        if [ -n "$upstream_username" ]; then
            proxy_config="$proxy_config
      username: \"$upstream_username\"
      password: \"$upstream_password\""
        else
            proxy_config="$proxy_config
      username: null
      password: null"
        fi
    else
        proxy_config="$proxy_config
    upstream:
      server: \"\"
      port: 0
      username: null
      password: null"
    fi
    
    proxy_config="$proxy_config
    monitoring_enabled: $monitoring_enabled"
    
    PROXIES+=("$proxy_config")
    
    print_info "✓ Proxy configured"
}

# Generate configuration file
generate_config() {
    print_section "Generating Configuration"
    
    print_info "Creating configuration file: $OUTPUT_FILE"
    
    # Generate password hash if needed
    local password_hash=""
    if [ "$WEB_AUTH_ENABLED" = "true" ]; then
        print_info "Generating password hash..."
        password_hash=$(generate_password_hash "$WEB_PASSWORD")
        
        if [ "$password_hash" = "$WEB_PASSWORD" ]; then
            print_warn "bcrypt not available, storing plain password (NOT SECURE)"
            print_warn "Please install bcrypt: pip install bcrypt"
        fi
    fi
    
    # Write configuration file
    cat > "$OUTPUT_FILE" <<EOF
# Proxy Relay System Configuration
# Generated by configuration wizard on $(date)

system:
  web_port: $WEB_PORT
  web_auth:
    enabled: $WEB_AUTH_ENABLED
EOF

    if [ "$WEB_AUTH_ENABLED" = "true" ]; then
        cat >> "$OUTPUT_FILE" <<EOF
    username: $WEB_USERNAME
    password_hash: $password_hash
EOF
    fi

    cat >> "$OUTPUT_FILE" <<EOF
  log_level: $LOG_LEVEL
  log_file: $LOG_FILE
  database: $DATABASE

monitoring:
  check_interval: $MONITOR_CHECK_INTERVAL
  failure_threshold: $MONITOR_FAILURE_THRESHOLD
  check_timeout: $MONITOR_CHECK_TIMEOUT
  check_url: "$MONITOR_CHECK_URL"

api_providers:
EOF

    # Write API providers
    for provider in "${API_PROVIDERS[@]}"; do
        echo "  - $provider" | sed 's/^/  /' >> "$OUTPUT_FILE"
    done

    cat >> "$OUTPUT_FILE" <<EOF

proxies:
EOF

    # Write proxies
    for proxy in "${PROXIES[@]}"; do
        echo "$proxy" >> "$OUTPUT_FILE"
    done

    print_info "✓ Configuration file created: $OUTPUT_FILE"
}

# Validate configuration
validate_config() {
    print_section "Validating Configuration"
    
    # Check if Python is available for validation
    if ! command -v python3 &> /dev/null; then
        print_warn "Python not available, skipping validation"
        return
    fi
    
    # Try to load and validate with Python
    print_info "Validating YAML syntax..."
    
    if python3 -c "import yaml; yaml.safe_load(open('$OUTPUT_FILE'))" 2>/dev/null; then
        print_info "✓ Configuration file is valid YAML"
    else
        print_error "Configuration file has YAML syntax errors"
        print_error "Please check the file manually"
        return 1
    fi
    
    # Basic validation checks
    print_info "Running validation checks..."
    
    local errors=0
    
    # Check if at least one API provider is configured
    if [ ${#API_PROVIDERS[@]} -eq 0 ]; then
        print_warn "No API providers configured"
        ((errors++))
    fi
    
    # Check if at least one proxy is configured
    if [ ${#PROXIES[@]} -eq 0 ]; then
        print_warn "No proxies configured"
        ((errors++))
    fi
    
    if [ $errors -eq 0 ]; then
        print_info "✓ Configuration validation passed"
    else
        print_warn "Configuration has $errors warning(s)"
    fi
}

# Show summary
show_summary() {
    print_section "Configuration Summary"
    
    echo "System Settings:"
    echo "  Web Port: $WEB_PORT"
    echo "  Web Auth: $WEB_AUTH_ENABLED"
    if [ "$WEB_AUTH_ENABLED" = "true" ]; then
        echo "  Username: $WEB_USERNAME"
    fi
    echo "  Log Level: $LOG_LEVEL"
    echo
    echo "Monitoring Settings:"
    echo "  Check Interval: ${MONITOR_CHECK_INTERVAL}s"
    echo "  Failure Threshold: $MONITOR_FAILURE_THRESHOLD"
    echo "  Check Timeout: ${MONITOR_CHECK_TIMEOUT}s"
    echo "  Check URL: $MONITOR_CHECK_URL"
    echo
    echo "API Providers: ${#API_PROVIDERS[@]}"
    echo "Proxies: ${#PROXIES[@]}"
    echo
    echo "Configuration file: $OUTPUT_FILE"
}

# Main wizard flow
main() {
    show_welcome
    
    # Configure system
    configure_system
    
    # Configure monitoring
    configure_monitoring
    
    # Configure API providers
    print_section "API Provider Setup"
    print_info "You need at least one API provider to fetch new proxies"
    
    while true; do
        configure_api_provider
        
        read -p "$(echo -e ${CYAN}[?]${NC}) Add another API provider? (y/n): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            break
        fi
    done
    
    # Configure proxies
    print_section "Proxy Setup"
    print_info "Configure local SOCKS5 proxy ports"
    
    while true; do
        configure_proxy
        
        read -p "$(echo -e ${CYAN}[?]${NC}) Add another proxy? (y/n): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            break
        fi
    done
    
    # Generate configuration
    generate_config
    
    # Validate configuration
    validate_config
    
    # Show summary
    show_summary
    
    # Final message
    echo
    print_info "Configuration wizard completed!"
    echo
    echo "Next steps:"
    echo "  1. Review the configuration file: $OUTPUT_FILE"
    echo "  2. Copy to /etc/proxy-relay/config.yaml (if installing system-wide)"
    echo "  3. Start the Proxy Relay System"
    echo
    print_warn "Remember to keep your configuration file secure!"
    print_warn "It contains sensitive information like passwords and API keys"
    echo
}

# Run main function
main
