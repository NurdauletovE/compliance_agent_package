# Compliance Agent Package

A containerized OpenSCAP compliance scanning agent that runs on remote systems and sends results to a central compliance API server.

## Package Contents

```
compliance_agent_package/
├── Dockerfile                  # Docker image definition
├── docker-compose.yml         # Docker Compose configuration
├── deploy.sh                  # Simple deployment script
├── README.md                  # This file
├── requirements.txt           # Python dependencies
├── src/
│   └── agent.py               # Main agent application
├── config/
│   └── agent.yaml            # Agent configuration
├── scripts/
│   └── deploy-agent.sh       # Advanced deployment script
└── docker/
    ├── entrypoint.sh         # Container entrypoint
    └── supervisord.conf      # Supervisor configuration
```

## Quick Start

### 1. Set Environment Variables

```bash
export COMPLIANCE_API_URL="http://your-compliance-server:8002"
export COMPLIANCE_API_TOKEN="your-optional-token"
export SCAN_INTERVAL="3600"  # 1 hour
```

### 2. Deploy with Simple Script

```bash
# Build and deploy
./deploy.sh deploy

# Check status
./deploy.sh status

# View logs
./deploy.sh logs

# Trigger manual scan
./deploy.sh scan
```

### 3. Deploy with Docker Compose

```bash
# Create environment file
cat > .env << EOF
COMPLIANCE_API_URL=http://your-server:8002
SCAN_INTERVAL=3600
DEFAULT_PROFILE=xccdf_org.ssgproject.content_profile_cis
AGENT_PORT=8080
EOF

# Start the agent
docker-compose up -d

# Check logs
docker-compose logs -f
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `COMPLIANCE_API_URL` | `http://host.docker.internal:8002` | Compliance API server URL |
| `COMPLIANCE_API_TOKEN` | - | API authentication token (optional) |
| `SCAN_INTERVAL` | `3600` | Scan interval in seconds (0 to disable) |
| `DEFAULT_PROFILE` | `xccdf_org.ssgproject.content_profile_cis` | Default compliance profile |
| `AGENT_PORT` | `8080` | Health check endpoint port |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |

### Available Compliance Profiles

- `xccdf_org.ssgproject.content_profile_cis` - General CIS Benchmark
- `xccdf_org.ssgproject.content_profile_cis_level1_server` - CIS Level 1 Server
- `xccdf_org.ssgproject.content_profile_cis_level2_server` - CIS Level 2 Server
- `xccdf_org.ssgproject.content_profile_standard` - Standard Security Profile
- `xccdf_org.ssgproject.content_profile_stig` - STIG Compliance Profile

## Usage Examples

### Basic Deployment

```bash
# Deploy with defaults
./deploy.sh deploy
```

### Custom Configuration

```bash
# Set custom configuration
export COMPLIANCE_API_URL="https://compliance.company.com/api"
export SCAN_INTERVAL="7200"  # 2 hours
export DEFAULT_PROFILE="xccdf_org.ssgproject.content_profile_cis_level2_server"

# Deploy
./deploy.sh deploy
```

### Manual Operations

```bash
# Build image only
./deploy.sh build

# Start agent
./deploy.sh run

# Check status
./deploy.sh status

# Trigger immediate scan
./deploy.sh scan

# Trigger scan with specific profile
./deploy.sh scan xccdf_org.ssgproject.content_profile_cis_level1_server

# View logs
./deploy.sh logs

# Stop agent
./deploy.sh stop

# Complete cleanup
./deploy.sh cleanup
```

## API Endpoints

The agent exposes a REST API on port 8080 (configurable):

### Health Check
```bash
curl http://localhost:8080/health
```

Response:
```json
{
    "status": "healthy",
    "timestamp": "2025-08-17T02:00:00Z",
    "version": "1.0.0"
}
```

### Manual Scan Trigger
```bash
# Default profile
curl -X POST http://localhost:8080/scan

# Specific profile
curl -X POST "http://localhost:8080/scan?profile=xccdf_org.ssgproject.content_profile_cis_level1_server"
```

## Deployment on Remote Systems

### 1. Copy Package to Remote System

```bash
# Create package archive
tar -czf compliance-agent.tar.gz compliance_agent_package/

# Copy to remote system
scp compliance-agent.tar.gz user@remote-system:/tmp/

# On remote system
cd /tmp
tar -xzf compliance-agent.tar.gz
cd compliance_agent_package
```

### 2. Configure for Remote Deployment

```bash
# Set API server URL (accessible from remote system)
export COMPLIANCE_API_URL="http://your-compliance-server-ip:8002"

# Deploy
./deploy.sh deploy
```

### 3. Verify Deployment

```bash
# Check agent status
./deploy.sh status

# Trigger test scan
./deploy.sh scan

# Monitor logs
./deploy.sh logs
```

## Security Considerations

### Privileged Mode
The agent runs in privileged mode for comprehensive system scanning. For production:

1. **Network Security**: Restrict network access to only the compliance API
2. **Monitoring**: Monitor agent logs for suspicious activity
3. **Updates**: Keep the agent image updated with security patches
4. **Access Control**: Limit who can deploy and manage agents

## Support and Maintenance

### Log Files
- Agent logs: `/app/logs/agent.log`
- Supervisor logs: `/app/logs/supervisord.log`
- Scan results: `/app/results/`

### Monitoring
- Health endpoint: `http://localhost:8080/health`
- Container health: `docker-compose ps`
- Resource usage: `docker stats compliance-agent`

### Updates
```bash
# Pull latest version
git pull

# Rebuild and redeploy
./deploy.sh cleanup
./deploy.sh deploy
```

## License

This compliance agent is part of the security compliance automation system.
