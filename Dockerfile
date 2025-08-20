# Compliance Agent Dockerfile for Remote Scanning
FROM ubuntu:22.04

# Avoid interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies including OpenSCAP
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-venv \
    curl \
    wget \
    xmlstarlet \
    unzip \
    supervisor \
    git \
    netcat-openbsd \
    libopenscap8 \
    libopenscap-dev \
    python3-openscap \
    && rm -rf /var/lib/apt/lists/*

# Install OpenSCAP CLI tools manually since openscap-scanner package is not available
RUN cd /tmp && \
    wget -q https://github.com/OpenSCAP/openscap/releases/download/1.3.7/openscap-1.3.7.tar.gz && \
    tar xzf openscap-1.3.7.tar.gz && \
    cd openscap-1.3.7 && \
    apt-get update && apt-get install -y \
        build-essential cmake pkg-config \
        libxml2-dev libxslt1-dev libcurl4-openssl-dev \
        libpcre3-dev libdbus-1-dev libbz2-dev \
        libgcrypt20-dev libblkid-dev libxmlsec1-dev \
        libxmlsec1-openssl && \
    mkdir build && cd build && \
    cmake .. && make && make install && \
    ldconfig && \
    cd / && rm -rf /tmp/openscap-* && \
    apt-get remove -y build-essential cmake pkg-config && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*

# Download SCAP Security Guide content
RUN mkdir -p /usr/share/xml/scap/ssg/content && \
    cd /usr/share/xml/scap/ssg/content && \
    wget -q https://github.com/ComplianceAsCode/content/releases/download/v0.1.72/scap-security-guide-0.1.72.zip && \
    unzip -q scap-security-guide-0.1.72.zip && \
    mv scap-security-guide-0.1.72/* . && \
    rm -rf scap-security-guide-0.1.72.zip scap-security-guide-0.1.72 && \
    chown -R root:root /usr/share/xml/scap

# Create application directory
WORKDIR /app

# Create compliance user
RUN groupadd -r compliance && useradd -r -g compliance -d /app -s /bin/bash compliance

# Copy requirements for agent
COPY requirements.txt /app/requirements.txt

# Create virtual environment and install Python dependencies
RUN python3 -m venv /app/venv && \
    /app/venv/bin/pip install --upgrade pip && \
    /app/venv/bin/pip install --no-cache-dir -r requirements.txt

# Copy agent source code
COPY src/ /app/src/
COPY config/ /app/config/
COPY scripts/ /app/scripts/

# Create necessary directories
RUN mkdir -p /app/logs /app/results /app/content && \
    chown -R compliance:compliance /app

# Create content directory (SCAP content will be downloaded if available, otherwise mock scans)
RUN mkdir -p /app/content && \
    chown -R compliance:compliance /app/content

# Copy entrypoint and supervisor configuration
COPY docker/entrypoint.sh /entrypoint.sh
COPY docker/supervisord.conf /etc/supervisor/conf.d/supervisord.conf
RUN chmod +x /entrypoint.sh

# Expose health check port
EXPOSE 8080

# Set user
USER compliance

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Start supervisor to manage services
ENTRYPOINT ["/entrypoint.sh"]
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
