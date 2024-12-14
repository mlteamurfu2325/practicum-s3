#!/bin/bash

# Store the full script path
SCRIPT_PATH=$(readlink -f "$0")

# Set up logging
exec 1> >(tee "deployment.log") 2>&1
echo "Deployment started at $(date)"
echo "----------------------------------------"

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
    python3 -c "import sys; exit(0) if sys.version_info >= (3, 8) else exit(1)" 2>/dev/null
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
        sudo apt-get update
        sudo apt-get install -y ca-certificates curl gnupg
        sudo install -m 0755 -d /etc/apt/keyrings
        curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
        sudo chmod a+r /etc/apt/keyrings/docker.gpg

        # Add the repository to Apt sources
        echo \
          "deb [arch="$(dpkg --print-architecture)" signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
          "$(. /etc/os-release && echo "$VERSION_CODENAME")" stable" | \
          sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

        # Install Docker packages
        sudo apt-get update
        sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
        check_status "Docker installation"
    else
        echo "✓ Docker is already installed"
    fi

    # Add current user to docker group if not already added
    if ! groups | grep -q docker; then
        sudo usermod -aG docker $USER
        echo "✓ Added user to docker group. Please log out and back in for this to take effect."
        # Create a new shell with the docker group added to avoid requiring logout
        exec sg docker -c "$SCRIPT_PATH"
    fi
}

# Function to check and install Docker Compose
setup_docker_compose() {
    if ! command -v docker compose &> /dev/null; then
        echo "Docker Compose not found. Installing Docker Compose..."
        sudo apt-get update
        sudo apt-get install -y docker-compose-plugin
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

print_header "Setting up data directory"
mkdir -p data
chmod 750 data
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

sudo apt install "./megacmd-xUbuntu_${ubuntu_version}_amd64.deb"
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
    mega-get "https://mega.nz/file/WVB3gIDT#NDUcZMcCCEla7mtpvAdk2ecMkQ0oOgtDMoSBa1dglDA" "data/geo-reviews-enriched.parquet"
    check_status "Embeddings download"
else
    print_header "Processing raw dataset"
    echo "Starting data processing pipeline..."
    
    # Check if raw TSKV file exists with correct md5sum
    if ! check_md5sum "data/geo-reviews-dataset-2023.tskv" "857fe8ae8af5f5165da3e1674e6f588a"; then
        echo "Downloading geo-reviews dataset..."
        mkdir -p data
        wget -O data/geo-reviews-dataset-2023.tskv https://github.com/yandex/geo-reviews-dataset-2023/raw/refs/heads/master/geo-reviews-dataset-2023.tskv
        
        if ! check_md5sum "data/geo-reviews-dataset-2023.tskv" "857fe8ae8af5f5165da3e1674e6f588a"; then
            echo "✗ Error: Downloaded file has incorrect md5sum"
            exit 1
        fi
    fi

    # Step 1: Convert TSKV to Parquet
    echo "Converting TSKV to Parquet format..."
    python src/reviews-processing/export_to_parquet.py
    check_status "TSKV to Parquet conversion"
    
    # Step 2: Check token limits
    echo "Checking and processing token limits..."
    python src/reviews-processing/check_token_limit.py
    check_status "Token limit processing"
    
    # Step 3: Generate embeddings
    echo "Generating embeddings (this may take a while)..."
    python src/reviews-processing/enrich_with_embeddings.py
    check_status "Embeddings generation"
fi

print_header "Checking system requirements"
check_python_version

print_header "Setting up Docker environment"
setup_docker
setup_docker_compose
start_docker_containers

print_header "Setting up development environment"

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m virtualenv .venv
    check_status "Virtual environment creation"
fi

# Activate virtual environment
source .venv/bin/activate
check_status "Virtual environment activation"

print_header "Upgrading pip and installing dependencies"
python -m pip install --upgrade pip
check_status "Pip upgrade"

# Install requirements
echo "Installing dependencies..."
pip install -r requirements.txt
check_status "Dependencies installation"

print_header "Setting up security configuration"

# Create logs directory
echo "Creating logs directory..."
mkdir -p logs
chmod 750 logs
check_status "Logs directory setup"

# Create secrets directory
echo "Setting up secrets directory..."
mkdir -p secrets
chmod 700 secrets
check_status "Secrets directory setup"

# Generate random password for database if not exists
if [ ! -f "secrets/db_password.txt" ]; then
    echo "Generating secure database password..."
    openssl rand -base64 32 > secrets/db_password.txt
    chmod 600 secrets/db_password.txt
    check_status "Database password generation"
fi

print_header "Environment setup"
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
    
    # Get database password
    DB_PASSWORD=$(cat secrets/db_password.txt)
    
    # Create .env file with fixed database configuration
    cat > .env << EOL
# OpenRouter API Configuration
OPENROUTER_API_KEY=${OPENROUTER_KEY}

# Database Configuration (using TimescaleDB defaults)
DB_HOST=localhost
DB_PORT=5432
DB_NAME=postgres
DB_USER=postgres
DB_PASSWORD=${DB_PASSWORD}

# Security Settings
MAX_REQUESTS_PER_HOUR=${MAX_REQUESTS}
EOL
    chmod 600 .env
    check_status ".env file creation"
    
    echo -e "\nDatabase Configuration Notes:"
    echo "- Using default TimescaleDB user 'postgres' as recommended"
    echo "- Database password auto-generated in secrets/db_password.txt"
    echo "- Database runs in Docker container on localhost:5432"
fi

print_header "Database Import"
echo "Importing reviews into PostgreSQL database..."
python src/db-importer/pg-reviews-importer.py
check_status "Database import"

print_header "Verifying project structure"
# Check if required directories exist
required_dirs=(
    "src/llm"
    "src/reviews-processing"
    "docs"
    "data"
    "logs"
    "secrets"
    "docker"
)

for dir in "${required_dirs[@]}"; do
    if [ ! -d "$dir" ]; then
        echo -e "✗ Error: Required directory $dir is missing\n"
        exit 1
    fi
done
echo -e "✓ Project structure verification passed\n"

print_header "Security Checklist"
echo "Please verify the following:"
echo "1. .env file exists and has correct permissions (600)"
echo "2. secrets/db_password.txt exists and has correct permissions (600)"
echo "3. secrets/ directory has correct permissions (700)"
echo "4. logs/ directory has correct permissions (750)"
echo -e "\nFile permissions:"
ls -la .env 2>/dev/null || echo "❌ .env file missing"
ls -la secrets/db_password.txt 2>/dev/null || echo "❌ db_password.txt missing"
ls -ld secrets/ 2>/dev/null || echo "❌ secrets directory missing"
ls -ld logs/ 2>/dev/null || echo "❌ logs directory missing"
echo -e "\n"

print_header "Setup complete!"
echo -e "To complete the setup:\n"
echo "1. Review your .env file and secrets/db_password.txt"
echo "2. Ensure all security permissions are correct (see above)"
echo -e "3. Run: streamlit run app.py\n"

echo -e "\nDeployment finished at $(date)"
echo "----------------------------------------"
echo "Full deployment log has been saved to deployment.log"
