#!/bin/bash

# Check if script is run with sudo
if [ "$EUID" -ne 0 ]; then 
    echo "Please run this script with sudo"
    exit 1
fi

# Capture the original user who invoked sudo
ORIGINAL_USER=$(logname)
ORIGINAL_HOME=$(eval echo ~$ORIGINAL_USER)

# Store the full script path
SCRIPT_PATH=$(readlink -f "$0")

# Set up logging
exec 1> >(tee "deployment.log") 2>&1
echo "Deployment started at $(date)"
echo "----------------------------------------"

# Function to run commands as the original user
run_as_user() {
    sudo -u $ORIGINAL_USER "$@"
}

# Function to print section headers
print_header() {
    echo -e "\n===================================="
    echo "$1"
    echo "===================================="
}

# Function to check command status
check_status() {
    if [ $? -eq 0 ]; then
        echo -e "✓ $1 completed successfully\n"
    else
        echo -e "✗ Error: $1 failed\n"
        exit 1
    fi
}

# Function to check Python version
check_python_version() {
    run_as_user python3 -c "import sys; exit(0) if sys.version_info >= (3, 8) else exit(1)" 2>/dev/null
    if [ $? -ne 0 ]; then
        echo -e "✗ Error: Python 3.8 or higher is required\n"
        exit 1
    fi
    echo -e "✓ Python version check passed\n"
}

# Function to check and install Docker
setup_docker() {
    if ! command -v docker &> /dev/null; then
        echo "Docker not found. Installing Docker..."
        # Add Docker's official GPG key
        apt-get update
        apt-get install -y ca-certificates curl gnupg
        install -m 0755 -d /etc/apt/keyrings
        curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
        chmod a+r /etc/apt/keyrings/docker.gpg

        # Add the repository to Apt sources
        echo \
          "deb [arch="$(dpkg --print-architecture)" signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
          "$(. /etc/os-release && echo "$VERSION_CODENAME")" stable" | \
          tee /etc/apt/sources.list.d/docker.list > /dev/null

        # Install Docker packages
        apt-get update
        apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
        check_status "Docker installation"
    else
        echo "✓ Docker is already installed"
    fi
}

# Function to check and install Docker Compose
setup_docker_compose() {
    if ! command -v docker compose &> /dev/null; then
        echo "Docker Compose not found. Installing Docker Compose..."
        apt-get update
        apt-get install -y docker-compose-plugin
        check_status "Docker Compose installation"
    else
        echo "✓ Docker Compose is already installed"
    fi
}

# Function to start Docker containers
start_docker_containers() {
    echo "Starting Docker containers..."
    cd docker/
    docker compose up -d
    check_status "Starting Docker containers"
    cd ..
    
    # Wait for the database to be ready
    echo "Waiting for database to be ready..."
    sleep 10  # Initial wait
    max_attempts=30
    attempt=1
    while ! docker exec $(docker ps -qf "name=timescaledb") pg_isready -U postgres > /dev/null 2>&1; do
        if [ $attempt -eq $max_attempts ]; then
            echo "✗ Error: Database failed to start after $max_attempts attempts"
            exit 1
        fi
        echo "Waiting for database to be ready... (attempt $attempt/$max_attempts)"
        sleep 2
        ((attempt++))
    done
    echo "✓ Database is ready"
}

# Function to check file md5sum
check_md5sum() {
    local file=$1
    local expected_md5=$2
    if [ ! -f "$file" ]; then
        return 1
    fi
    local actual_md5=$(md5sum "$file" | cut -d' ' -f1)
    if [ "$actual_md5" != "$expected_md5" ]; then
        return 1
    fi
    return 0
}

# Function to setup UFW and configure security rules
setup_ufw() {
    print_header "Setting up UFW firewall"
    
    # Check if UFW is installed
    if ! command -v ufw &> /dev/null; then
        echo "UFW not found. Installing UFW..."
        apt-get update
        apt-get install -y ufw
        check_status "UFW installation"
    else
        echo "✓ UFW is already installed"
    fi

    echo "Resetting UFW to default configuration..."
    ufw --force reset
    check_status "UFW reset"

    echo "Configuring UFW rules..."
    
    # Default policies
    ufw default deny incoming
    ufw default allow outgoing
    
    # Allow SSH (essential to prevent lockout)
    echo "Allowing SSH connections..."
    ufw allow ssh
    
    # Configure PostgreSQL UFW rules
    echo "Configuring PostgreSQL rules..."
    
    # Allow internal networks to PostgreSQL
    ufw allow from 10.0.0.0/8 to any port 5432
    ufw allow from 172.16.0.0/12 to any port 5432
    ufw allow from 192.168.0.0/16 to any port 5432
    ufw allow from 127.0.0.0/8 to any port 5432
    
    # Deny all other incoming connections to PostgreSQL
    ufw deny to any port 5432
    
    # Enable UFW
    echo "Enabling UFW..."
    ufw --force enable
    
    check_status "UFW configuration"
}

# Function to print UFW status
print_ufw_status() {
    print_header "Current UFW Rules"
    echo "IMPORTANT: Please review these rules carefully to ensure you haven't lost access!"
    echo "Particularly, verify that SSH (port 22) is allowed."
    echo "----------------------------------------"
    ufw status verbose
    echo "----------------------------------------"
}

# Function to get external IP address
get_external_ip() {
    # Try different IP services until we get a valid response
    local ip=""
    
    # Array of IP services to try
    local services=(
        "https://api.ipify.org"
        "https://icanhazip.com"
        "https://ifconfig.me"
        "https://ipecho.net/plain"
    )
    
    for service in "${services[@]}"; do
        ip=$(curl -s --connect-timeout 5 "$service" 2>/dev/null)
        
        # Check if we got a valid IPv4 address
        if [[ $ip =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
            echo "$ip"
            return 0
        fi
    done
    
    # If all services fail
    echo "Error: Could not determine external IP" >&2
    return 1
}

# Function to setup domain with myaddr.tools
setup_domain() {
    # Check if curl is installed
    if ! command -v curl &> /dev/null; then
        echo "Installing curl..."
        apt-get update
        apt-get install -y curl
        check_status "curl installation"
    fi

    # Get external IP
    EXTERNAL_IP=$(get_external_ip)
    if [ $? -ne 0 ]; then
        echo "Failed to get external IP"
        return 1
    fi
    echo "External IP detected: $EXTERNAL_IP"

    echo "Enter your myaddr.tools domain key:"
    read -r DOMAIN_KEY
    
    echo "Enter your full domain name (e.g., myapp.myaddr.tools):"
    read -r DOMAIN_NAME

    # Update domain
    echo "Updating domain with IP address..."
    RESPONSE=$(curl -s -w "%{http_code}" -d "key=${DOMAIN_KEY}" -d "ip=${EXTERNAL_IP}" https://myaddr.tools/update)
    HTTP_CODE=${RESPONSE: -3}
    RESPONSE_BODY=${RESPONSE%???}  # Remove last 3 characters (status code)
    
    if [ "$HTTP_CODE" = "200" ]; then
        echo "✓ Domain successfully configured"
        return 0
    else
        echo "✗ Failed to configure domain. HTTP Code: $HTTP_CODE"
        [ ! -z "$RESPONSE_BODY" ] && echo "Response: $RESPONSE_BODY"
        return 1
    fi
}

# Function to setup Caddy
setup_caddy() {
    print_header "Setting up Caddy"
    
    # Install Caddy
    apt-get update
    apt-get install -y debian-keyring debian-archive-keyring apt-transport-https
    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | tee /etc/apt/sources.list.d/caddy-stable.list
    apt-get update
    apt-get install -y caddy
    
    # Configure Caddyfile
    echo "$DOMAIN_NAME {
    reverse_proxy localhost:8501
}" > /etc/caddy/Caddyfile
    
    # Allow HTTPS in UFW
    ufw allow 80/tcp
    ufw allow 443/tcp
    
    # Start Caddy
    systemctl enable caddy
    systemctl restart caddy
    
    check_status "Caddy setup"
}

print_header "Setting up data directory"
run_as_user mkdir -p data
run_as_user chmod 750 data
check_status "Data directory setup"

print_header "Checking Ubuntu version"
# Get Ubuntu version in XX.YY format
ubuntu_version=$(lsb_release -rs)
if [ -z "$ubuntu_version" ]; then
    echo -e "✗ Error: Could not detect Ubuntu version\n"
    exit 1
fi

# Extract major version number (XX) and compare with 22
ubuntu_major=$(echo "$ubuntu_version" | cut -d. -f1)
if [ "$ubuntu_major" -lt 22 ]; then
    echo -e "✗ Error: This script requires Ubuntu 22.04 or newer. Your version: $ubuntu_version\n"
    exit 1
fi
echo -e "✓ Ubuntu version check passed (version $ubuntu_version)\n"

print_header "Installing MEGA CMD"
# Download and install megacmd for detected Ubuntu version
wget "https://mega.nz/linux/repo/xUbuntu_${ubuntu_version}/amd64/megacmd-xUbuntu_${ubuntu_version}_amd64.deb"
check_status "MEGA CMD package download"

apt install -y "./megacmd-xUbuntu_${ubuntu_version}_amd64.deb"
check_status "MEGA CMD installation"

# Clean up the downloaded package
rm "megacmd-xUbuntu_${ubuntu_version}_amd64.deb"

print_header "Data Processing Setup"
echo "You have two options for review data:"
echo "1. Download pre-generated embeddings (recommended)"
echo "2. Process the raw dataset and generate embeddings (requires high-end GPU)"
echo -n "Download pre-generated embeddings? [Y/n]: "
read -r download_choice

if [[ $download_choice =~ ^[Yy]$ ]] || [[ -z $download_choice ]]; then
    print_header "Downloading pre-generated embeddings"
    if [ -f "data/geo-reviews-enriched.parquet" ]; then
        echo "✓ Pre-generated embeddings file already exists, skipping download"
    else
        run_as_user mega-get "https://mega.nz/file/WVB3gIDT#NDUcZMcCCEla7mtpvAdk2ecMkQ0oOgtDMoSBa1dglDA" "data/geo-reviews-enriched.parquet"
        check_status "Embeddings download"
    fi
else
    print_header "Processing raw dataset"
    echo "Starting data processing pipeline..."
    
    # Check if raw TSKV file exists with correct md5sum
    if ! check_md5sum "data/geo-reviews-dataset-2023.tskv" "857fe8ae8af5f5165da3e1674e6f588a"; then
        echo "Downloading geo-reviews dataset..."
        run_as_user mkdir -p data
        wget -O data/geo-reviews-dataset-2023.tskv https://github.com/yandex/geo-reviews-dataset-2023/raw/refs/heads/master/geo-reviews-dataset-2023.tskv
        
        if ! check_md5sum "data/geo-reviews-dataset-2023.tskv" "857fe8ae8af5f5165da3e1674e6f588a"; then
            echo "✗ Error: Downloaded file has incorrect md5sum"
            exit 1
        fi
    fi

    # Step 1: Convert TSKV to Parquet
    echo "Converting TSKV to Parquet format..."
    run_as_user python src/reviews-processing/export_to_parquet.py
    check_status "TSKV to Parquet conversion"
    
    # Step 2: Check token limits
    echo "Checking and processing token limits..."
    run_as_user python src/reviews-processing/check_token_limit.py
    check_status "Token limit processing"
    
    # Step 3: Generate embeddings
    echo "Generating embeddings (this may take a while)..."
    run_as_user python src/reviews-processing/enrich_with_embeddings.py
    check_status "Embeddings generation"
fi

print_header "Checking system requirements"
check_python_version

print_header "Creating logs directory"
run_as_user mkdir -p logs
run_as_user chmod 750 logs
check_status "Logs directory setup"

print_header "Setting up Docker environment"
setup_docker
setup_docker_compose

print_header "Setting up environment variables"
if [ ! -f ".env" ]; then
    echo "Setting up environment variables..."
    echo -e "Please provide the following configuration values:\n"
    
    # Prompt for OpenRouter API key (sensitive)
    echo -e "\nOpenRouter API Key"
    echo -n "[required]: "
    read -s OPENROUTER_KEY
    echo  # New line after hidden input
    
    if [ -z "$OPENROUTER_KEY" ]; then
        echo -e "✗ Error: OpenRouter API Key is required\n"
        exit 1
    fi
    
    # Prompt for max requests (not sensitive)
    echo -e "\nMax Requests per Hour"
    echo -n "[default: 100]: "
    read MAX_REQUESTS
    MAX_REQUESTS=${MAX_REQUESTS:-100}
    
    # Generate database password
    DB_PASSWORD=$(openssl rand -base64 32)
    
    # Create .env file with configuration
    run_as_user bash -c "cat > .env << EOL
# OpenRouter API Configuration
OPENROUTER_API_KEY=${OPENROUTER_KEY}

# Database Configuration
DB_HOST=localhost  # Changed back to localhost since we're using host networking
DB_PORT=5432
DB_NAME=postgres
DB_USER=postgres
DB_PASSWORD=${DB_PASSWORD}
POSTGRES_PASSWORD=${DB_PASSWORD}  # Required by Docker

# Security Settings
MAX_REQUESTS_PER_HOUR=${MAX_REQUESTS}
EOL"
    run_as_user chmod 600 .env
    check_status ".env file creation"
    
    echo -e "\nDatabase Configuration Notes:"
    echo "- Using default TimescaleDB user 'postgres'"
    echo "- Database password auto-generated and stored in .env"
    echo "- Database accessible via localhost"
fi

print_header "Starting Docker containers"
start_docker_containers

print_header "Setting up development environment"
# Install virtualenv if not present
if ! command -v virtualenv &> /dev/null; then
    echo "Installing python3-virtualenv..."
    apt-get update
    apt-get install -y python3-virtualenv
    check_status "virtualenv installation"
fi

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    run_as_user python3 -m virtualenv .venv
    check_status "Virtual environment creation"
fi

print_header "Upgrading pip and installing dependencies"
# Use the full path to pip within the virtual environment
run_as_user .venv/bin/pip install --upgrade pip
check_status "Pip upgrade"

# Install requirements
echo "Installing dependencies..."
run_as_user .venv/bin/pip install -r requirements.txt
check_status "Dependencies installation"

print_header "Database Import"
echo "Importing reviews into PostgreSQL database..."
run_as_user .venv/bin/python src/db-importer/pg-reviews-importer.py
check_status "Database import"

print_header "Setting up UFW and PostgreSQL rules"
setup_ufw

print_header "Streamlit Deployment Configuration"
echo "How would you like to run the Streamlit app?"
echo "1. By IP address (no HTTPS)"
echo "2. With a free domain name (HTTPS enabled)"
read -p "Enter your choice (1 or 2): " STREAMLIT_CHOICE

if [ "$STREAMLIT_CHOICE" = "2" ]; then
    echo "Do you already have a myaddr.tools domain?"
    echo "1. Yes, I have a domain and key"
    echo "2. No, I need to claim one"
    read -p "Enter your choice (1 or 2): " DOMAIN_CHOICE
    
    if [ "$DOMAIN_CHOICE" = "2" ]; then
        echo "Please visit https://myaddr.tools/claim to claim your domain"
        echo "After claiming your domain, press Enter to continue"
        read
    fi
    
    if setup_domain; then
        setup_caddy
        echo "Starting Streamlit with Caddy..."
        run_as_user .venv/bin/streamlit run app.py --server.address 127.0.0.1 --server.port 8501
        echo "✓ Streamlit is now accessible at https://$DOMAIN_NAME"
    else
        echo "Failed to set up domain. Falling back to IP-based access..."
        ufw allow 8501/tcp
        run_as_user .venv/bin/streamlit run app.py --server.address 0.0.0.0 --server.port 8501
        echo "✓ Streamlit is now accessible at http://$EXTERNAL_IP:8501"
    fi
else
    echo "Setting up IP-based access..."
    ufw allow 8501/tcp
    run_as_user .venv/bin/streamlit run app.py --server.address 0.0.0.0 --server.port 8501
    echo "✓ Streamlit is now accessible at http://$EXTERNAL_IP:8501"
fi

print_header "Setup complete!"
echo -e "To complete the setup:\n"
echo "1. Review your .env file"
echo "2. Ensure all security permissions are correct"
if [ "$STREAMLIT_CHOICE" = "2" ] && [ "$HTTP_CODE" = "200" ]; then
    echo "3. Access your app at https://$DOMAIN_NAME"
else
    echo "3. Access your app at http://$EXTERNAL_IP:8501"
fi

print_header "Final Security Check"
print_ufw_status
echo "⚠️  IMPORTANT: Make sure SSH access (port 22) is allowed before disconnecting!"
echo "If you get locked out, you'll need physical access or console access to fix it."

echo -e "\nDeployment finished at $(date)"
echo "----------------------------------------"
echo "Full deployment log has been saved to deployment.log"
