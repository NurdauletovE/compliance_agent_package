#!/bin/bash
# Compliance Agent Deployment Script

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

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
build_image() {
    echo "Building compliance agent image..."
    cd "$PROJECT_DIR"
    docker build -f Dockerfile -t "$IMAGE_NAME:$IMAGE_TAG" .
    echo "✓ Image built successfully"
}

# Function to run the container
run_container() {
    echo "Starting compliance agent container..."
    
    # Stop existing container if running
    if docker ps -q -f name="$CONTAINER_NAME" | grep -q .; then
        echo "Stopping existing container..."
        docker stop "$CONTAINER_NAME" >/dev/null 2>&1 || true
    fi
    
    # Remove existing container
    if docker ps -aq -f name="$CONTAINER_NAME" | grep -q .; then
        echo "Removing existing container..."
        docker rm "$CONTAINER_NAME" >/dev/null 2>&1 || true
    fi
    
    # Run new container
    docker run -d \
        --name "$CONTAINER_NAME" \
        --restart unless-stopped \
        -p "$AGENT_PORT:8080" \
        -e COMPLIANCE_API_URL="$COMPLIANCE_API_URL" \
        -e COMPLIANCE_API_TOKEN="$COMPLIANCE_API_TOKEN" \
        -e SCAN_INTERVAL="$SCAN_INTERVAL" \
        -e DEFAULT_PROFILE="$DEFAULT_PROFILE" \
        -v compliance_agent_logs:/app/logs \
        -v compliance_agent_results:/app/results \
        --privileged \
        "$IMAGE_NAME:$IMAGE_TAG"
    
    echo "✓ Container started successfully"
    echo "Container ID: $(docker ps -q -f name="$CONTAINER_NAME")"
}

# Function to show logs
show_logs() {
    echo "Showing container logs..."
    docker logs -f "$CONTAINER_NAME"
}

# Function to check status
check_status() {
    echo "Checking agent status..."
    
    if docker ps -q -f name="$CONTAINER_NAME" | grep -q .; then
        echo "✓ Container is running"
        
        # Check health endpoint
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
trigger_scan() {
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

# Function to stop the container
stop_container() {
    echo "Stopping compliance agent..."
    docker stop "$CONTAINER_NAME" >/dev/null 2>&1 || true
    echo "✓ Container stopped"
}

# Function to remove everything
cleanup() {
    echo "Cleaning up compliance agent..."
    docker stop "$CONTAINER_NAME" >/dev/null 2>&1 || true
    docker rm "$CONTAINER_NAME" >/dev/null 2>&1 || true
    docker rmi "$IMAGE_NAME:$IMAGE_TAG" >/dev/null 2>&1 || true
    docker volume rm compliance_agent_logs compliance_agent_results >/dev/null 2>&1 || true
    echo "✓ Cleanup completed"
}

# Main command handling
case "${1:-help}" in
    build)
        build_image
        ;;
    run)
        run_container
        ;;
    deploy)
        build_image
        run_container
        ;;
    logs)
        show_logs
        ;;
    status)
        check_status
        ;;
    scan)
        trigger_scan "$2"
        ;;
    stop)
        stop_container
        ;;
    cleanup)
        cleanup
        ;;
    help|*)
        echo "Usage: $0 {build|run|deploy|logs|status|scan|stop|cleanup}"
        echo ""
        echo "Commands:"
        echo "  build     - Build the compliance agent Docker image"
        echo "  run       - Run the compliance agent container"
        echo "  deploy    - Build and run the compliance agent"
        echo "  logs      - Show container logs"
        echo "  status    - Check agent status and health"
        echo "  scan      - Trigger a manual scan (optional: scan [profile])"
        echo "  stop      - Stop the agent container"
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
