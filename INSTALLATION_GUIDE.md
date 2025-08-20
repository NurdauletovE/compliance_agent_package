# Compliance Agent Installation Guide

This guide provides step-by-step instructions for installing and deploying the Compliance Agent on remote systems.

## Prerequisites

### System Requirements
- Linux-based operating system (Ubuntu 20.04+, Debian 11+, RHEL 8+, CentOS 8+)
- Docker Engine 20.10+ or Docker Desktop
- Docker Compose v2.0+ (optional but recommended)
- Minimum 2GB RAM
- Minimum 4GB disk space
- Network connectivity to compliance API server

### Network Requirements
- Outbound HTTPS/HTTP access to compliance API server
- Port 8080 available for health check endpoint (configurable)
- Docker registry access for base images (if building from source)

## Installation Methods

### Method 1: Quick Installation (Recommended)

1. **Download and Extract Package**
   ```bash
   # Download the package (replace with actual download link)
   wget https://github.com/your-org/compliance-agent/releases/latest/compliance-agent.tar.gz
   
   # Extract
   tar -xzf compliance-agent.tar.gz
   cd compliance_agent_package
   ```

2. **Configure Environment**
   ```bash
   # Set your compliance API server URL
   export COMPLIANCE_API_URL="http://your-compliance-server:8002"
   
   # Optional: Set authentication token
   export COMPLIANCE_API_TOKEN="your-token"
   
   # Optional: Configure scan interval (default: 1 hour)
   export SCAN_INTERVAL="3600"
   ```

3. **Deploy**
   ```bash
   # Make deployment script executable
   chmod +x deploy.sh
   
   # Build and deploy the agent
   ./deploy.sh deploy
   ```

4. **Verify Installation**
   ```bash
   # Check status
   ./deploy.sh status
   
   # View logs
   ./deploy.sh logs
   ```

### Method 2: Docker Compose Installation

1. **Prepare Environment File**
   ```bash
   cat > .env << EOF
   COMPLIANCE_API_URL=http://your-compliance-server:8002
   COMPLIANCE_API_TOKEN=your-optional-token
   SCAN_INTERVAL=3600
   DEFAULT_PROFILE=xccdf_org.ssgproject.content_profile_cis
   AGENT_PORT=8080
   LOG_LEVEL=INFO
   EOF
   ```

2. **Deploy with Docker Compose**
   ```bash
   docker-compose up -d
   ```

3. **Verify Deployment**
   ```bash
   # Check container status
   docker-compose ps
   
   # Check logs
   docker-compose logs -f
   
   # Test health endpoint
   curl http://localhost:8080/health
   ```

### Method 3: Manual Docker Installation

1. **Build Image**
   ```bash
   docker build -t compliance-agent:latest .
   ```

2. **Run Container**
   ```bash
   docker run -d \
     --name compliance-agent \
     --restart unless-stopped \
     -p 8080:8080 \
     -e COMPLIANCE_API_URL="http://your-server:8002" \
     -e SCAN_INTERVAL="3600" \
     -v compliance-agent-logs:/app/logs \
     -v compliance-agent-results:/app/results \
     --privileged \
     compliance-agent:latest
   ```

## Configuration Options

### Environment Variables

Create a `.env` file or set environment variables:

```bash
# Required
COMPLIANCE_API_URL=http://your-compliance-server:8002

# Optional
COMPLIANCE_API_TOKEN=your-authentication-token
SCAN_INTERVAL=3600
DEFAULT_PROFILE=xccdf_org.ssgproject.content_profile_cis
AGENT_PORT=8080
LOG_LEVEL=INFO
```

### Configuration File

Edit `config/agent.yaml` for advanced configuration:

```yaml
# API Configuration
api_base_url: "http://your-compliance-server:8002"
api_token: ""

# Scanning Configuration
scan_interval: 3600
default_profile: "xccdf_org.ssgproject.content_profile_cis"

# Available Profiles
available_profiles:
  - "xccdf_org.ssgproject.content_profile_cis"
  - "xccdf_org.ssgproject.content_profile_cis_level1_server"
  - "xccdf_org.ssgproject.content_profile_cis_level2_server"
  - "xccdf_org.ssgproject.content_profile_standard"

# Agent Configuration
agent_port: 8080
log_level: "INFO"
max_scan_history: 100
```

## Post-Installation Steps

### 1. Verify Agent Registration

```bash
# Check agent health
curl http://localhost:8080/health

# Expected response
{
    "status": "healthy",
    "timestamp": "2025-08-17T02:00:00Z",
    "version": "1.0.0"
}
```

### 2. Test Scan Functionality

```bash
# Trigger a manual scan
curl -X POST http://localhost:8080/scan

# Check scan results in logs
./deploy.sh logs
```

### 3. Verify API Communication

```bash
# Check agent logs for API communication
docker-compose logs | grep -i "submitted\|api\|error"

# Should see successful submission messages
```

## Security Setup

### 1. Network Security

```bash
# Configure firewall (example for UFW)
sudo ufw allow from YOUR_COMPLIANCE_SERVER_IP to any port 8080
sudo ufw deny 8080

# Or use iptables
sudo iptables -A INPUT -s YOUR_COMPLIANCE_SERVER_IP -p tcp --dport 8080 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 8080 -j DROP
```

### 2. User and File Permissions

```bash
# Create dedicated user (optional)
sudo useradd -r -s /bin/false compliance-agent

# Set proper file permissions
chmod 600 .env
chmod 755 deploy.sh
```

### 3. Secure Configuration

```bash
# Use environment files instead of command line
cat > .env << EOF
COMPLIANCE_API_URL=https://your-secure-server:8443
COMPLIANCE_API_TOKEN=your-secure-token
EOF

# Protect environment file
chmod 600 .env
```

## Troubleshooting

### Common Installation Issues

1. **Docker not found**
   ```bash
   # Install Docker (Ubuntu/Debian)
   curl -fsSL https://get.docker.com -o get-docker.sh
   sudo sh get-docker.sh
   sudo usermod -aG docker $USER
   # Log out and back in
   ```

2. **Permission denied**
   ```bash
   # Fix Docker permissions
   sudo chmod 666 /var/run/docker.sock
   # Or add user to docker group
   sudo usermod -aG docker $USER
   ```

3. **Port already in use**
   ```bash
   # Change agent port
   export AGENT_PORT=8081
   ./deploy.sh deploy
   ```

4. **Build failures**
   ```bash
   # Clean Docker build cache
   docker system prune -f
   
   # Rebuild with no cache
   docker build --no-cache -t compliance-agent:latest .
   ```

### Connectivity Issues

1. **Cannot reach API server**
   ```bash
   # Test connectivity
   curl -I http://your-compliance-server:8002/health
   
   # Check DNS resolution
   nslookup your-compliance-server
   
   # Test from container
   docker exec compliance-agent curl -I $COMPLIANCE_API_URL/health
   ```

2. **API authentication failures**
   ```bash
   # Verify token
   curl -H "Authorization: Bearer $COMPLIANCE_API_TOKEN" \
        http://your-compliance-server:8002/health
   
   # Check agent logs
   ./deploy.sh logs | grep -i auth
   ```

### Scanning Issues

1. **OpenSCAP not found**
   ```bash
   # Check OpenSCAP installation in container
   docker exec compliance-agent oscap --version
   
   # Check SCAP content
   docker exec compliance-agent ls -la /app/content/
   ```

2. **Scan failures**
   ```bash
   # Check available profiles
   docker exec compliance-agent \
     oscap info /app/content/ssg-ubuntu2204-ds.xml
   
   # Test manual scan
   ./deploy.sh scan
   ```

## Maintenance

### Regular Updates

```bash
# Update the agent
./deploy.sh stop
git pull  # Or download new package
./deploy.sh deploy

# Check new version
./deploy.sh status
```

### Log Management

```bash
# View recent logs
./deploy.sh logs | tail -100

# Clear old logs
docker exec compliance-agent find /app/logs -name "*.log" -mtime +7 -delete

# Rotate logs (setup logrotate)
sudo cat > /etc/logrotate.d/compliance-agent << EOF
/var/lib/docker/volumes/compliance-agent-logs/_data/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
}
EOF
```

### Performance Monitoring

```bash
# Monitor resource usage
docker stats compliance-agent

# Monitor disk usage
df -h
docker system df

# Clean up old images
docker image prune -f
```

## Uninstallation

### Complete Removal

```bash
# Stop and remove agent
./deploy.sh cleanup

# Remove package
cd ..
rm -rf compliance_agent_package

# Clean Docker resources
docker system prune -a -f
```

### Partial Cleanup

```bash
# Stop agent only
./deploy.sh stop

# Remove container but keep images
docker-compose down
```

## Support

### Getting Help

1. **Check Documentation**: Review README.md and this installation guide
2. **Check Logs**: Use `./deploy.sh logs` to see detailed error messages
3. **Test Connectivity**: Verify network connectivity to API server
4. **Community Support**: Check project repository for issues and discussions

### Reporting Issues

When reporting issues, include:

1. Operating system and version
2. Docker version (`docker --version`)
3. Agent version and configuration
4. Complete error logs
5. Steps to reproduce the issue

### Debug Information

```bash
# Collect debug information
echo "=== System Info ===" > debug.log
uname -a >> debug.log
docker --version >> debug.log
docker-compose --version >> debug.log

echo "=== Agent Status ===" >> debug.log
./deploy.sh status >> debug.log

echo "=== Agent Logs ===" >> debug.log
./deploy.sh logs >> debug.log

echo "=== Container Info ===" >> debug.log
docker inspect compliance-agent >> debug.log
```

This installation guide should help you successfully deploy the Compliance Agent in your environment.
