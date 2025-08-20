#!/bin/bash

# Compliance Agent Setup Script
# This script helps set up the environment for running the compliance agent

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Log functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
check_root() {
    if [ "$EUID" -eq 0 ]; then
        log_warning "Running as root. Some operations may be skipped for security."
        return 0
    fi
    return 1
}

# Check system requirements
check_system_requirements() {
    log_info "Checking system requirements..."
    
    # Check OS
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        log_info "Detected OS: $NAME $VERSION"
        
        case "$ID" in
            ubuntu|debian)
                if [ "$VERSION_ID" \< "20.04" ] && [ "$ID" = "ubuntu" ]; then
                    log_warning "Ubuntu version may be too old. Recommended: 20.04+"
                fi
                ;;
            rhel|centos|fedora)
                log_info "Red Hat family OS detected"
                ;;
            *)
                log_warning "Untested OS. Proceed with caution."
                ;;
        esac
    else
        log_warning "Cannot detect OS version"
    fi
    
    # Check architecture
    ARCH=$(uname -m)
    log_info "Architecture: $ARCH"
    if [ "$ARCH" != "x86_64" ] && [ "$ARCH" != "amd64" ]; then
        log_warning "Untested architecture: $ARCH"
    fi
    
    # Check memory
    MEMORY_GB=$(free -g | awk '/^Mem:/{print $2}')
    log_info "Available memory: ${MEMORY_GB}GB"
    if [ "$MEMORY_GB" -lt 2 ]; then
        log_warning "Less than 2GB memory detected. Agent may not perform optimally."
    fi
    
    # Check disk space
    DISK_GB=$(df -BG "$SCRIPT_DIR" | awk 'NR==2 {print $4}' | sed 's/G//')
    log_info "Available disk space: ${DISK_GB}GB"
    if [ "$DISK_GB" -lt 4 ]; then
        log_warning "Less than 4GB disk space available. May not be sufficient."
    fi
}

# Check if Docker is installed
check_docker() {
    log_info "Checking Docker installation..."
    
    if command -v docker >/dev/null 2>&1; then
        DOCKER_VERSION=$(docker --version | cut -d' ' -f3 | cut -d',' -f1)
        log_success "Docker found: $DOCKER_VERSION"
        
        # Check if Docker daemon is running
        if docker info >/dev/null 2>&1; then
            log_success "Docker daemon is running"
        else
            log_error "Docker daemon is not running"
            return 1
        fi
        
        # Check if user can run Docker
        if docker ps >/dev/null 2>&1; then
            log_success "User can run Docker commands"
        else
            log_warning "User cannot run Docker commands. You may need to:"
            log_warning "  1. Add user to docker group: sudo usermod -aG docker \$USER"
            log_warning "  2. Log out and back in"
            log_warning "  3. Or run commands with sudo"
        fi
        
        return 0
    else
        log_error "Docker not found"
        return 1
    fi
}

# Install Docker
install_docker() {
    log_info "Installing Docker..."
    
    if check_root; then
        log_error "Cannot install Docker as root for security reasons"
        log_info "Please install Docker manually or run as non-root user"
        return 1
    fi
    
    # Check if we can use apt
    if command -v apt >/dev/null 2>&1; then
        log_info "Installing Docker using apt..."
        
        # Update package index
        sudo apt update
        
        # Install prerequisites
        sudo apt install -y \
            ca-certificates \
            curl \
            gnupg \
            lsb-release
        
        # Add Docker's official GPG key
        sudo mkdir -p /etc/apt/keyrings
        curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
        
        # Set up repository
        echo \
          "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
          $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
        
        # Install Docker Engine
        sudo apt update
        sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
        
        # Add user to docker group
        sudo usermod -aG docker "$USER"
        
        log_success "Docker installed successfully"
        log_warning "Please log out and back in to use Docker without sudo"
        
    elif command -v yum >/dev/null 2>&1; then
        log_info "Installing Docker using yum..."
        
        # Install yum-utils
        sudo yum install -y yum-utils
        
        # Set up repository
        sudo yum-config-manager \
            --add-repo \
            https://download.docker.com/linux/centos/docker-ce.repo
        
        # Install Docker
        sudo yum install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
        
        # Start Docker
        sudo systemctl start docker
        sudo systemctl enable docker
        
        # Add user to docker group
        sudo usermod -aG docker "$USER"
        
        log_success "Docker installed successfully"
        
    else
        log_error "Cannot determine package manager. Please install Docker manually."
        log_info "Visit: https://docs.docker.com/get-docker/"
        return 1
    fi
}

# Check Docker Compose
check_docker_compose() {
    log_info "Checking Docker Compose..."
    
    # Check for Docker Compose v2 (plugin)
    if docker compose version >/dev/null 2>&1; then
        COMPOSE_VERSION=$(docker compose version | cut -d' ' -f4)
        log_success "Docker Compose found: $COMPOSE_VERSION"
        return 0
    # Check for Docker Compose v1 (standalone)
    elif command -v docker-compose >/dev/null 2>&1; then
        COMPOSE_VERSION=$(docker-compose --version | cut -d' ' -f3 | cut -d',' -f1)
        log_success "Docker Compose found: $COMPOSE_VERSION"
        log_warning "Using legacy docker-compose. Consider upgrading to Docker Compose v2"
        return 0
    else
        log_error "Docker Compose not found"
        return 1
    fi
}

# Install Docker Compose
install_docker_compose() {
    log_info "Installing Docker Compose..."
    
    if command -v docker >/dev/null 2>&1; then
        # Docker Compose should be included with modern Docker installations
        log_info "Docker Compose should be included with Docker installation"
        log_info "If not available, please update Docker to the latest version"
    else
        log_error "Docker must be installed first"
        return 1
    fi
}

# Create environment file
create_environment_file() {
    log_info "Creating environment configuration..."
    
    ENV_FILE="$SCRIPT_DIR/.env"
    
    if [ -f "$ENV_FILE" ]; then
        log_warning "Environment file already exists: $ENV_FILE"
        read -p "Do you want to overwrite it? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "Skipping environment file creation"
            return 0
        fi
    fi
    
    # Get API URL from user
    echo
    log_info "Please provide the compliance API server information:"
    
    while true; do
        read -p "API Server URL (e.g., http://server:8002): " API_URL
        if [ -n "$API_URL" ]; then
            break
        else
            log_error "API URL is required"
        fi
    done
    
    read -p "API Token (optional, press Enter to skip): " API_TOKEN
    read -p "Scan interval in seconds (default: 3600): " SCAN_INTERVAL
    SCAN_INTERVAL=${SCAN_INTERVAL:-3600}
    
    read -p "Agent port (default: 8080): " AGENT_PORT
    AGENT_PORT=${AGENT_PORT:-8080}
    
    # Create environment file
    cat > "$ENV_FILE" << EOF
# Compliance Agent Configuration
# Generated by setup script on $(date)

# Required: Compliance API server URL
COMPLIANCE_API_URL=$API_URL

# Optional: Authentication token
COMPLIANCE_API_TOKEN=$API_TOKEN

# Optional: Scan interval in seconds (default: 1 hour)
SCAN_INTERVAL=$SCAN_INTERVAL

# Optional: Default SCAP profile
DEFAULT_PROFILE=xccdf_org.ssgproject.content_profile_cis

# Optional: Agent health check port
AGENT_PORT=$AGENT_PORT

# Optional: Log level (DEBUG, INFO, WARNING, ERROR)
LOG_LEVEL=INFO
EOF
    
    chmod 600 "$ENV_FILE"
    log_success "Environment file created: $ENV_FILE"
}

# Verify package integrity
verify_package() {
    log_info "Verifying package integrity..."
    
    VERIFY_SCRIPT="$SCRIPT_DIR/verify_package.py"
    
    if [ -f "$VERIFY_SCRIPT" ]; then
        if command -v python3 >/dev/null 2>&1; then
            python3 "$VERIFY_SCRIPT" --package-dir "$SCRIPT_DIR"
        else
            log_warning "Python3 not found. Skipping package verification."
            log_info "Install Python3 to run package verification"
        fi
    else
        log_warning "Package verification script not found"
    fi
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check Python
    if command -v python3 >/dev/null 2>&1; then
        PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
        log_success "Python3 found: $PYTHON_VERSION"
    else
        log_warning "Python3 not found. Required for package verification."
    fi
    
    # Check curl
    if command -v curl >/dev/null 2>&1; then
        log_success "curl found"
    else
        log_warning "curl not found. Required for API communication testing."
    fi
    
    # Check basic network connectivity
    if ping -c 1 google.com >/dev/null 2>&1; then
        log_success "Network connectivity verified"
    else
        log_warning "Network connectivity check failed"
    fi
}

# Test deployment
test_deployment() {
    log_info "Testing deployment configuration..."
    
    # Check if deploy.sh exists and is executable
    DEPLOY_SCRIPT="$SCRIPT_DIR/deploy.sh"
    if [ -f "$DEPLOY_SCRIPT" ] && [ -x "$DEPLOY_SCRIPT" ]; then
        log_success "Deployment script found and executable"
        
        # Test Docker build (dry run)
        log_info "Testing Docker build..."
        if docker build --help >/dev/null 2>&1; then
            log_success "Docker build command available"
        else
            log_error "Docker build not available"
        fi
    else
        log_error "Deployment script not found or not executable"
    fi
}

# Print summary and next steps
print_summary() {
    echo
    log_info "=============================================="
    log_info "              SETUP SUMMARY"
    log_info "=============================================="
    echo
    
    if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
        log_success "✅ Docker is ready"
    else
        log_error "❌ Docker needs attention"
    fi
    
    if [ -f "$SCRIPT_DIR/.env" ]; then
        log_success "✅ Environment configured"
    else
        log_warning "⚠️  Environment file missing"
    fi
    
    echo
    log_info "Next steps:"
    log_info "1. Review the configuration in .env file"
    log_info "2. Run: ./deploy.sh deploy"
    log_info "3. Check status: ./deploy.sh status"
    log_info "4. View logs: ./deploy.sh logs"
    echo
    log_info "For detailed instructions, see:"
    log_info "- README.md"
    log_info "- INSTALLATION_GUIDE.md"
    echo
}

# Main setup function
main() {
    echo
    log_info "=============================================="
    log_info "        Compliance Agent Setup Script"
    log_info "=============================================="
    echo
    
    # Check system requirements
    check_system_requirements
    echo
    
    # Check prerequisites
    check_prerequisites
    echo
    
    # Check Docker
    if ! check_docker; then
        echo
        read -p "Docker not found. Do you want to install it? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            install_docker
        else
            log_warning "Docker installation skipped. Please install Docker manually."
        fi
    fi
    echo
    
    # Check Docker Compose
    if ! check_docker_compose; then
        echo
        read -p "Docker Compose not found. Do you want to install it? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            install_docker_compose
        fi
    fi
    echo
    
    # Create environment file
    read -p "Do you want to configure the environment now? (Y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        create_environment_file
    fi
    echo
    
    # Verify package
    read -p "Do you want to verify the package integrity? (Y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        verify_package
    fi
    echo
    
    # Test deployment configuration
    test_deployment
    
    # Print summary
    print_summary
}

# Handle command line arguments
case "${1:-}" in
    "check")
        check_system_requirements
        check_prerequisites
        check_docker
        check_docker_compose
        ;;
    "install-docker")
        install_docker
        ;;
    "configure")
        create_environment_file
        ;;
    "verify")
        verify_package
        ;;
    "test")
        test_deployment
        ;;
    "help"|"-h"|"--help")
        echo "Usage: $0 [command]"
        echo
        echo "Commands:"
        echo "  check          - Check system requirements and prerequisites"
        echo "  install-docker - Install Docker"
        echo "  configure      - Create environment configuration"
        echo "  verify         - Verify package integrity"
        echo "  test          - Test deployment configuration"
        echo "  help          - Show this help message"
        echo
        echo "If no command is provided, interactive setup will run."
        ;;
    "")
        main
        ;;
    *)
        log_error "Unknown command: $1"
        log_info "Run '$0 help' for usage information"
        exit 1
        ;;
esac
