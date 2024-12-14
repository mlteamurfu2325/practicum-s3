#!/bin/bash

# Function to print section headers
print_header() {
    echo -e "\n\n===================================="
    echo "$1"
    echo "====================================\n"
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

# Function to prompt for secret
prompt_secret() {
    local secret_name=$1
    local default_value=$2
    local secret_value

    # Prompt for the secret
    echo -e "\n$secret_name"
    echo -n "[default: $default_value]: "
    read -s secret_value
    echo  # New line after hidden input
    
    # Use default if no input provided
    if [ -z "$secret_value" ]; then
        secret_value=$default_value
    fi
    
    echo $secret_value
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

print_header "Checking system requirements"
check_python_version

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
    
    # Prompt for OpenRouter API key
    OPENROUTER_KEY=$(prompt_secret "OpenRouter API Key" "your_api_key_here")
    
    # Security settings
    MAX_REQUESTS=$(prompt_secret "Max Requests per Hour" "100")
    
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

print_header "Verifying project structure"
# Check if required directories exist
required_dirs=(
    "src/llm"
    "src/reviews-processing"
    "docs"
)

for dir in "${required_dirs[@]}"; do
    if [ ! -d "$dir" ]; then
        echo -e "✗ Error: Required directory $dir is missing\n"
        exit 1
    fi
done
echo -e "✓ Project structure verification passed\n"

print_header "Checking data files"

# Check enriched parquet file
if [ ! -f "data/geo-reviews-enriched.parquet" ]; then
    echo -e "Need to generate Parquet files for Reviews and Enrich it with embeddings for review texts\n"
    
    # Check if raw TSKV file exists with correct md5sum
    if ! check_md5sum "data/geo-reviews-dataset-2023.tskv" "857fe8ae8af5f5165da3e1674e6f588a"; then
        echo "Downloading geo-reviews dataset..."
        mkdir -p data
        wget -O data/geo-reviews-dataset-2023.tskv https://github.com/yandex/geo-reviews-dataset-2023/raw/refs/heads/master/geo-reviews-dataset-2023.tskv
        
        if ! check_md5sum "data/geo-reviews-dataset-2023.tskv" "857fe8ae8af5f5165da3e1674e6f588a"; then
            echo -e "✗ Error: Downloaded file has incorrect md5sum\n"
            exit 1
        fi
    fi

    echo "Processing reviews data..."
    python src/reviews-processing/export_to_parquet.py
    check_status "Export to parquet"
    
    python src/reviews-processing/check_token_limit.py
    check_status "Token limit check"
    
    python src/reviews-processing/enrich_with_embeddings.py
    check_status "Embeddings enrichment"
fi

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

echo -e "Security Notes:\n"
echo "1. Keep your .env and secrets/ directory secure"
echo "2. Never commit secrets to version control"
echo "3. Regularly rotate passwords and API keys"
echo "4. Monitor logs/ directory for suspicious activity"
echo -e "5. Review rate limiting settings in .env\n"

echo -e "Development workflow:\n"
echo "1. Create issue on GitHub"
echo "2. Create branch: issue-<number>/<category>/<description>"
echo "3. Make changes following conventional commits"
echo "4. Create pull request"
echo "5. Get code review"
echo -e "6. Merge to main\n"

echo -e "Commit message format:\n"
echo "<type>[area]: <description>"
echo -e "\nTypes: feat, fix, docs, style, refactor, test, chore, perf, ci, build, revert\n"

echo -e "LLM Integration Notes:\n"
echo "- Model: google/gemini-flash-1.5 via OpenRouter API"
echo "- Review generation workflow: validation → generation → quality check"
echo "- Automatic retries on failure (max 3 attempts)"
echo -e "- 15-second timeout per generation attempt\n"
