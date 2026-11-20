
#!/usr/bin/env bash
set -Eeuo pipefail

IMAGE="kgpro/echome:latest"

DEPLOY_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="$DEPLOY_DIR/docker-compose.yml"
ENV_FILE="$DEPLOY_DIR/.env"
REDIS_ENV="$DEPLOY_DIR/redis.env"

REDIS_PORT="6379"

log() {
    echo
    echo "========== $1 =========="
}

die() {
    echo "ERROR: $1" >&2
    exit 1
}

# Basic checks
[[ "$EUID" -ne 0 ]] || die "Run without sudo."
command -v sudo >/dev/null || die "sudo is required."
command -v apt-get >/dev/null || die "Ubuntu/Debian is required."
command -v curl >/dev/null || die "curl is required."

[[ -f "$COMPOSE_FILE" ]] || die "docker-compose.yml not found."

# Install Docker if missing
log "Checking Docker"

if ! command -v docker >/dev/null 2>&1; then
    sudo apt-get update
    sudo apt-get install -y ca-certificates curl

    curl -fsSL https://get.docker.com -o /tmp/install-docker.sh
    sudo sh /tmp/install-docker.sh
    rm -f /tmp/install-docker.sh
fi

sudo systemctl enable --now docker

docker compose version >/dev/null 2>&1 ||
    die "Docker Compose plugin is unavailable."

# Detect EC2 public IP
log "Detecting EC2 public IP"

REDIS_PUBLIC_HOST="$(
    curl -4 -fsS --retry 3 https://checkip.amazonaws.com |
    tr -d '[:space:]'
)"

[[ -n "$REDIS_PUBLIC_HOST" ]] ||
    die "Could not detect EC2 public IP."

echo "Detected public IP: $REDIS_PUBLIC_HOST"

# Prepare deployment directory
log "Preparing deployment files"

chmod 700 "$DEPLOY_DIR"

touch "$ENV_FILE" "$REDIS_ENV"
chmod 600 "$ENV_FILE" "$REDIS_ENV"

# Add or update environment variables without overwriting others.
set_env() {
    local file="$1"
    local key="$2"
    local value="$3"
    local temp_file

    temp_file="$(mktemp)"

    grep -v "^${key}=" "$file" > "$temp_file" || true
    printf '%s=%s\n' "$key" "$value" >> "$temp_file"

    cat "$temp_file" > "$file"
    rm -f "$temp_file"
}

# Redis public connection details for Render
set_env "$ENV_FILE" "REDIS_HOST" "$REDIS_PUBLIC_HOST"
set_env "$ENV_FILE" "REDIS_PORT" "$REDIS_PORT"

# Allow user to configure remaining environment variables
log "Configure environment variables"

nano "$ENV_FILE"
nano "$REDIS_ENV"

chmod 600 "$ENV_FILE" "$REDIS_ENV"

# Validate Compose configuration
log "Validating Docker Compose"

sudo docker compose \
    --project-directory "$DEPLOY_DIR" \
    -f "$COMPOSE_FILE" config >/dev/null

# Pull images
log "Pulling Docker images"

sudo docker compose \
    --project-directory "$DEPLOY_DIR" \
    -f "$COMPOSE_FILE" pull

# Start containers
log "Starting ECHOME services"

sudo docker compose \
    --project-directory "$DEPLOY_DIR" \
    -f "$COMPOSE_FILE" up -d

# Display status
log "Deployment status"

sudo docker compose \
    --project-directory "$DEPLOY_DIR" \
    -f "$COMPOSE_FILE" ps

echo
echo "ECHOME deployment completed."
echo "Redis public host: $REDIS_PUBLIC_HOST"
echo "Redis port: $REDIS_PORT"
echo
echo "Useful commands:"
echo "  sudo docker compose -f $COMPOSE_FILE logs -f"
echo "  sudo docker compose -f $COMPOSE_FILE ps"
echo "  sudo docker compose -f $COMPOSE_FILE pull"
echo "  sudo docker compose -f $COMPOSE_FILE up -d"
