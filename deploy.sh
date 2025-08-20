#!/bin/bash
# Simple Compliance Agent Deployment Script

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Configuration
IMAGE_NAME="${IMAGE_NAME:-compliance-agent}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
CONTAINER_NAME="${CONTAINER_NAME:-compliance-agent}"
AGENT_PORT="${AGENT_PORT:-8080}"

# Default environment variables
COMPLIANCE_API_URL="${COMPLIANCE_API_URL:-http://host.docker.internal:8002}"
SCAN_INTERVAL="${SCAN_INTERVAL:-3600}"
DEFAULT_PROFILE="${DEFAULT_PROFILE:-xccdf_org.ssgproject.content_profile_cis}"

echo "=================================="
echo "Compliance Agent Deployment"
echo "=================================="
echo "Image: $IMAGE_NAME:$IMAGE_TAG"
echo "Container: $CONTAINER_NAME"
echo "API URL: $COMPLIANCE_API_URL"
echo "Scan Interval: $SCAN_INTERVAL seconds"
echo "=================================="

# Function to build the image
build() {
    echo "Building compliance agent image..."
    docker build -t "$IMAGE_NAME:$IMAGE_TAG" .
    echo "✓ Image built successfully"
}

# Function to run with docker compose
run() {
    echo "Starting compliance agent with docker compose..."
    
    # Create .env file
    cat > .env << EOF
COMPLIANCE_API_URL=$COMPLIANCE_API_URL
COMPLIANCE_API_TOKEN=$COMPLIANCE_API_TOKEN
SCAN_INTERVAL=$SCAN_INTERVAL
DEFAULT_PROFILE=$DEFAULT_PROFILE
AGENT_PORT=$AGENT_PORT
LOG_LEVEL=${LOG_LEVEL:-INFO}
EOF
    
    docker compose up -d
    echo "✓ Agent started successfully"
    echo "Container: $(docker compose ps -q)"
}

# Function to show logs
logs() {
    echo "Showing agent logs..."
    docker compose logs -f
}

# Function to check status
status() {
    echo "Checking agent status..."
    
    if docker compose ps | grep -q "Up"; then
        echo "✓ Container is running"
        
        # Check health endpoint
        sleep 3
        if curl -s "http://localhost:$AGENT_PORT/health" >/dev/null 2>&1; then
            echo "✓ Health endpoint responding"
            curl -s "http://localhost:$AGENT_PORT/health" | python3 -m json.tool 2>/dev/null || echo "Health check passed"
        else
            echo "⚠ Health endpoint not responding"
        fi
    else
        echo "❌ Container is not running"
        return 1
    fi
}

# Function to trigger a manual scan
scan() {
    echo "Triggering manual scan..."
    
    PROFILE="${1:-$DEFAULT_PROFILE}"
    
    if curl -s -X POST "http://localhost:$AGENT_PORT/scan?profile=$PROFILE" >/dev/null 2>&1; then
        echo "✓ Scan triggered successfully"
        curl -s -X POST "http://localhost:$AGENT_PORT/scan?profile=$PROFILE" | python3 -m json.tool 2>/dev/null || echo "Scan initiated"
    else
        echo "❌ Failed to trigger scan"
        return 1
    fi
}

# Function to stop
stop() {
    echo "Stopping compliance agent..."
    docker compose down
    echo "✓ Agent stopped"
}

# Function to cleanup
cleanup() {
    echo "Cleaning up compliance agent..."
    docker compose down -v --rmi all
    echo "✓ Cleanup completed"
}

# Function aliases for verification script compatibility
deploy_agent() {
    build
    run
}

stop_agent() {
    stop
}

check_status() {
    status
}

show_logs() {
    logs
}

# Main command handling
case "${1:-help}" in
    build)
        build
        ;;
    run)
        run
        ;;
    deploy)
        build
        run
        ;;
    logs)
        logs
        ;;
    status)
        status
        ;;
    scan)
        scan "$2"
        ;;
    stop)
        stop
        ;;
    cleanup)
        cleanup
        ;;
    help|*)
        echo "Usage: $0 {build|run|deploy|logs|status|scan|stop|cleanup}"
        echo ""
        echo "Commands:"
        echo "  build     - Build the compliance agent Docker image"
        echo "  run       - Run the compliance agent with docker compose"
        echo "  deploy    - Build and run the compliance agent"
        echo "  logs      - Show container logs"
        echo "  status    - Check agent status and health"
        echo "  scan      - Trigger a manual scan (optional: scan [profile])"
        echo "  stop      - Stop the agent"
        echo "  cleanup   - Remove all agent resources"
        echo ""
        echo "Environment Variables:"
        echo "  COMPLIANCE_API_URL    - URL of the compliance API server"
        echo "  COMPLIANCE_API_TOKEN  - API authentication token"
        echo "  SCAN_INTERVAL         - Scan interval in seconds (default: 3600)"
        echo "  DEFAULT_PROFILE       - Default compliance profile"
        echo "  AGENT_PORT           - Agent health check port (default: 8080)"
        ;;
esac
