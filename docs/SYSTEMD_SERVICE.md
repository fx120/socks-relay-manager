# Systemd Service Integration

This document describes how to install, configure, and manage the Proxy Relay System as a systemd service on Debian/Ubuntu systems.

## Overview

The Proxy Relay System can be installed as a systemd service, which provides:

- Automatic startup on system boot
- Process management and monitoring
- Graceful shutdown handling
- Resource limits and security hardening
- Centralized logging via journald

## Prerequisites

- Debian 11/12 or Ubuntu 20.04/22.04
- Python 3.11 or higher
- systemd (installed by default on modern Debian/Ubuntu)
- sing-box (must be installed separately)
- Root or sudo access

## Installation

### Automated Installation

The easiest way to install the service is using the provided installation script:

```bash
# Clone or download the repository
cd /path/to/proxy-relay

# Run the installation script
sudo ./scripts/install_service.sh
```

The installation script will:

1. Check system requirements
2. Create a dedicated `proxy-relay` user and group
3. Create necessary directories:
   - `/opt/proxy-relay` - Application files
   - `/etc/proxy-relay` - Configuration files
   - `/var/lib/proxy-relay` - Database and state files
   - `/var/log/proxy-relay` - Log files
4. Set appropriate file permissions
5. Install Python dependencies in a virtual environment
6. Copy the example configuration
7. Install and enable the systemd service

### Manual Installation

If you prefer to install manually:

1. **Create user and group:**

```bash
sudo groupadd --system proxy-relay
sudo useradd --system --gid proxy-relay --home-dir /opt/proxy-relay \
    --no-create-home --shell /usr/sbin/nologin proxy-relay
```

2. **Create directories:**

```bash
sudo mkdir -p /opt/proxy-relay
sudo mkdir -p /etc/proxy-relay
sudo mkdir -p /var/lib/proxy-relay
sudo mkdir -p /var/log/proxy-relay
```

3. **Copy application files:**

```bash
sudo cp -r src /opt/proxy-relay/
sudo cp requirements.txt /opt/proxy-relay/
sudo cp config.yaml.example /etc/proxy-relay/config.yaml
```

4. **Install Python dependencies:**

```bash
cd /opt/proxy-relay
sudo python3 -m venv venv
sudo venv/bin/pip install -r requirements.txt
```

5. **Set permissions:**

```bash
sudo chown -R proxy-relay:proxy-relay /opt/proxy-relay
sudo chown -R proxy-relay:proxy-relay /etc/proxy-relay
sudo chown -R proxy-relay:proxy-relay /var/lib/proxy-relay
sudo chown -R proxy-relay:proxy-relay /var/log/proxy-relay
sudo chmod 750 /etc/proxy-relay
sudo chmod 640 /etc/proxy-relay/config.yaml
```

6. **Install systemd service:**

```bash
sudo cp proxy-relay.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable proxy-relay
```

## Configuration

### Service Configuration

The systemd service is configured in `/etc/systemd/system/proxy-relay.service`:

```ini
[Unit]
Description=Proxy Relay System
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=proxy-relay
Group=proxy-relay
WorkingDirectory=/opt/proxy-relay
ExecStart=/opt/proxy-relay/venv/bin/python -m uvicorn proxy_relay.web_api:app --host 0.0.0.0 --port 8080
ExecReload=/bin/kill -HUP $MAINPID
Restart=on-failure
RestartSec=5s
Environment="PROXY_RELAY_CONFIG=/etc/proxy-relay/config.yaml"

# Security hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/lib/proxy-relay /var/log/proxy-relay /etc/proxy-relay

[Install]
WantedBy=multi-user.target
```

### Application Configuration

Edit the application configuration file:

```bash
sudo nano /etc/proxy-relay/config.yaml
```

See [QUICKSTART.md](QUICKSTART.md) for configuration details.

## Service Management

### Starting the Service

```bash
sudo systemctl start proxy-relay
```

### Stopping the Service

```bash
sudo systemctl stop proxy-relay
```

The service will perform a graceful shutdown:
1. Stop all monitoring tasks
2. Save current configuration
3. Close database connections
4. Exit cleanly

### Restarting the Service

```bash
sudo systemctl restart proxy-relay
```

### Reloading Configuration

To reload the configuration without restarting:

```bash
sudo systemctl reload proxy-relay
```

This sends a SIGHUP signal to the process, which triggers a configuration reload.

### Checking Service Status

```bash
sudo systemctl status proxy-relay
```

Example output:

```
● proxy-relay.service - Proxy Relay System
     Loaded: loaded (/etc/systemd/system/proxy-relay.service; enabled; vendor preset: enabled)
     Active: active (running) since Mon 2024-01-15 10:30:00 UTC; 1h 23min ago
   Main PID: 12345 (python)
      Tasks: 8 (limit: 4915)
     Memory: 45.2M
        CPU: 2.345s
     CGroup: /system.slice/proxy-relay.service
             └─12345 /opt/proxy-relay/venv/bin/python -m uvicorn proxy_relay.web_api:app...
```

### Enabling Auto-Start on Boot

```bash
sudo systemctl enable proxy-relay
```

### Disabling Auto-Start

```bash
sudo systemctl disable proxy-relay
```

## Logging

### Viewing Logs

The service logs to systemd's journal. View logs with:

```bash
# View all logs
sudo journalctl -u proxy-relay

# Follow logs in real-time
sudo journalctl -u proxy-relay -f

# View logs from the last hour
sudo journalctl -u proxy-relay --since "1 hour ago"

# View logs with specific priority
sudo journalctl -u proxy-relay -p err

# View logs in reverse order (newest first)
sudo journalctl -u proxy-relay -r
```

### Application Logs

In addition to systemd journal, the application writes logs to:

```
/var/log/proxy-relay/app.log
```

View application logs:

```bash
sudo tail -f /var/log/proxy-relay/app.log
```

## Security Features

The systemd service includes several security hardening options:

### Process Isolation

- **NoNewPrivileges**: Prevents privilege escalation
- **PrivateTmp**: Provides private /tmp directory
- **PrivateDevices**: Restricts access to devices

### Filesystem Protection

- **ProtectSystem=strict**: Makes most of the filesystem read-only
- **ProtectHome=true**: Prevents access to user home directories
- **ReadWritePaths**: Only allows writes to specific directories

### Kernel Protection

- **ProtectKernelTunables**: Prevents modification of kernel parameters
- **ProtectKernelModules**: Prevents loading kernel modules
- **ProtectKernelLogs**: Prevents access to kernel logs

### Network Restrictions

- **RestrictAddressFamilies**: Limits to IPv4, IPv6, and Unix sockets

### Resource Limits

- **LimitNOFILE=65536**: Maximum open files
- **LimitNPROC=512**: Maximum processes

## Troubleshooting

### Service Won't Start

1. Check service status:
   ```bash
   sudo systemctl status proxy-relay
   ```

2. View detailed logs:
   ```bash
   sudo journalctl -u proxy-relay -n 50
   ```

3. Check configuration:
   ```bash
   sudo /opt/proxy-relay/venv/bin/python -m proxy_relay.cli --config /etc/proxy-relay/config.yaml status
   ```

4. Verify permissions:
   ```bash
   ls -la /etc/proxy-relay/
   ls -la /var/lib/proxy-relay/
   ls -la /var/log/proxy-relay/
   ```

### Permission Denied Errors

If you see permission errors:

```bash
sudo chown -R proxy-relay:proxy-relay /opt/proxy-relay
sudo chown -R proxy-relay:proxy-relay /etc/proxy-relay
sudo chown -R proxy-relay:proxy-relay /var/lib/proxy-relay
sudo chown -R proxy-relay:proxy-relay /var/log/proxy-relay
```

### Service Crashes on Startup

1. Check Python version:
   ```bash
   /opt/proxy-relay/venv/bin/python --version
   ```

2. Verify dependencies:
   ```bash
   /opt/proxy-relay/venv/bin/pip list
   ```

3. Test configuration:
   ```bash
   sudo -u proxy-relay /opt/proxy-relay/venv/bin/python -c "from proxy_relay.config_manager import ConfigManager; ConfigManager('/etc/proxy-relay/config.yaml').load_config()"
   ```

### sing-box Not Found

If the service can't find sing-box:

1. Install sing-box:
   ```bash
   # Download from https://github.com/SagerNet/sing-box/releases
   sudo wget -O /usr/local/bin/sing-box https://github.com/SagerNet/sing-box/releases/download/v1.x.x/sing-box-linux-amd64
   sudo chmod +x /usr/local/bin/sing-box
   ```

2. Verify installation:
   ```bash
   which sing-box
   sing-box version
   ```

## Uninstallation

### Automated Uninstallation

Use the provided uninstallation script:

```bash
# Uninstall and remove all data
sudo ./scripts/uninstall_service.sh

# Uninstall but keep data
sudo ./scripts/uninstall_service.sh --keep-data
```

### Manual Uninstallation

1. Stop and disable service:
   ```bash
   sudo systemctl stop proxy-relay
   sudo systemctl disable proxy-relay
   ```

2. Remove service file:
   ```bash
   sudo rm /etc/systemd/system/proxy-relay.service
   sudo systemctl daemon-reload
   ```

3. Remove directories (optional):
   ```bash
   sudo rm -rf /opt/proxy-relay
   sudo rm -rf /etc/proxy-relay
   sudo rm -rf /var/lib/proxy-relay
   sudo rm -rf /var/log/proxy-relay
   ```

4. Remove user and group:
   ```bash
   sudo userdel proxy-relay
   sudo groupdel proxy-relay
   ```

## Advanced Configuration

### Custom Port

To change the web interface port, edit the service file:

```bash
sudo nano /etc/systemd/system/proxy-relay.service
```

Change the `--port` parameter in `ExecStart`:

```ini
ExecStart=/opt/proxy-relay/venv/bin/python -m uvicorn proxy_relay.web_api:app --host 0.0.0.0 --port 9090
```

Then reload and restart:

```bash
sudo systemctl daemon-reload
sudo systemctl restart proxy-relay
```

### Environment Variables

Add custom environment variables in the service file:

```ini
[Service]
Environment="PROXY_RELAY_CONFIG=/etc/proxy-relay/config.yaml"
Environment="CUSTOM_VAR=value"
```

### Resource Limits

Adjust resource limits in the service file:

```ini
[Service]
LimitNOFILE=100000
LimitNPROC=1024
MemoryLimit=512M
CPUQuota=200%
```

## Integration with Other Services

### Nginx Reverse Proxy

To put the service behind Nginx:

```nginx
server {
    listen 80;
    server_name proxy-relay.example.com;

    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # SSE support
    location /api/events/ {
        proxy_pass http://localhost:8080;
        proxy_set_header Connection '';
        proxy_http_version 1.1;
        chunked_transfer_encoding off;
        proxy_buffering off;
        proxy_cache off;
    }
}
```

### Monitoring with Prometheus

The service can be monitored using systemd metrics:

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'proxy-relay'
    static_configs:
      - targets: ['localhost:8080']
```

## See Also

- [DEPLOYMENT.md](DEPLOYMENT.md) - Full deployment guide
- [QUICKSTART.md](QUICKSTART.md) - Quick start guide
- [PRODUCTION_CHECKLIST.md](PRODUCTION_CHECKLIST.md) - Production deployment checklist
