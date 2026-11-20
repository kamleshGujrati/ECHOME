
#!/usr/bin/env bash
set -Eeuo pipefail

# ECHOME production bootstrap

REPO_URL="https://raw.githubusercontent.com/kamleshGujrati/ECHOME/main/deployment"

DEPLOY_DIR="$HOME/ECHOME/deployment"

log() {
    echo
    echo "========== $1 =========="
}

die() {
    echo "ERROR: $1" >&2
    exit 1
}

# Check dependencies
command -v curl >/dev/null 2>&1 || die "curl is required."

# Create deployment directory
log "Preparing deployment directory"

mkdir -p "$DEPLOY_DIR"

# Download deployment files
download_file() {
    local filename="$1"
    local temporary_file="$DEPLOY_DIR/.${filename}.tmp"

    log "Downloading $filename"

    curl -fLsS --retry 3 \
        "$REPO_URL/$filename" \
        -o "$temporary_file" || {
            rm -f "$temporary_file"
            die "Failed to download $filename"
        }

    mv "$temporary_file" "$DEPLOY_DIR/$filename"
}

download_file "docker-compose.yml"
download_file "deployment.sh"

# Make deployment script executable
chmod +x "$DEPLOY_DIR/deployment.sh"

# Execute actual deployment
log "Starting ECHOME production deployment"

exec bash "$DEPLOY_DIR/deployment.sh"
