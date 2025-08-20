#!/bin/bash
set -e

echo "Starting Compliance Agent Container..."

# Environment variables with defaults
export COMPLIANCE_API_URL="${COMPLIANCE_API_URL:-http://host.docker.internal:8002}"
export COMPLIANCE_API_TOKEN="${COMPLIANCE_API_TOKEN:-}"
export SCAN_INTERVAL="${SCAN_INTERVAL:-3600}"
export DEFAULT_PROFILE="${DEFAULT_PROFILE:-xccdf_org.ssgproject.content_profile_cis}"
export AGENT_PORT="${AGENT_PORT:-8080}"

echo "Configuration:"
echo "  API URL: $COMPLIANCE_API_URL"
echo "  Scan Interval: $SCAN_INTERVAL seconds"
echo "  Default Profile: $DEFAULT_PROFILE"
echo "  Agent Port: $AGENT_PORT"

# Check if API server is reachable (optional)
if [[ -n "$COMPLIANCE_API_URL" ]]; then
    echo "Testing connectivity to compliance API..."
    API_HOST=$(echo "$COMPLIANCE_API_URL" | sed -E 's|^https?://([^:/]+).*|\1|')
    API_PORT=$(echo "$COMPLIANCE_API_URL" | sed -E 's|^https?://[^:]+:?([0-9]*).*|\1|')
    API_PORT=${API_PORT:-80}
    
    if command -v nc >/dev/null 2>&1; then
        for i in {1..5}; do
            if nc -z "$API_HOST" "$API_PORT" 2>/dev/null; then
                echo "✓ API server is reachable"
                break
            else
                echo "⚠ API server not reachable, attempt $i/5"
                sleep 5
            fi
        done
    fi
fi

# Ensure proper permissions
chown -R compliance:compliance /app/logs /app/results || true

# Check if OpenSCAP content is available
CONTENT_DIRS=("/usr/share/xml/scap/ssg/content" "/usr/share/xml/scap" "/app/content")
CONTENT_FOUND=false

for dir in "${CONTENT_DIRS[@]}"; do
    if [ -d "$dir" ] && [ "$(ls -A "$dir" 2>/dev/null)" ]; then
        echo "✓ SCAP content found in $dir"
        CONTENT_FOUND=true
        break
    fi
done

if [ "$CONTENT_FOUND" = false ]; then
    echo "⚠ Warning: No SCAP content found. Scans may fail."
    echo "  Make sure to mount SCAP content or install ssg-* packages"
fi

# Test OpenSCAP installation
if command -v oscap >/dev/null 2>&1; then
    echo "✓ OpenSCAP is installed: $(oscap --version 2>/dev/null | head -1 || echo 'version unknown')"
else
    echo "⚠ OpenSCAP not found! The agent will run and produce mock results."
fi

# Start the application
echo "Starting Compliance Agent..."
exec "$@"
