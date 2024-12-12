#!/bin/bash

# Function to print section headers
print_header() {
    echo "===================================="
    echo "$1"
    echo "===================================="
}

# Function to check command status
check_status() {
    if [ $? -eq 0 ]; then
        echo "✓ $1 completed successfully"
    else
        echo "✗ Error: $1 failed"
        exit 1
    fi
}

# Function to check Python version
check_python_version() {
    python3 -c "import sys; exit(0) if sys.version_info >= (3, 8) else exit(1)" 2>/dev/null
    if [ $? -ne 0 ]; then
        echo "✗ Error: Python 3.8 or higher is required"
        exit 1
    fi
    echo "✓ Python version check passed"
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
    python3 -m venv .venv
    check_status "Virtual environment creation"
fi

# Activate virtual environment
source .venv/bin/activate
check_status "Virtual environment activation"

# Install/upgrade pip
print_header "Upgrading pip and installing dependencies"
python -m pip install --upgrade pip
check_status "Pip upgrade"

# Install requirements
echo "Installing dependencies..."
pip install -r requirements.txt
check_status "Dependencies installation"

# Create .env file if it doesn't exist
print_header "Environment setup"
if [ ! -f ".env" ]; then
    echo "Creating .env file..."
    cat > .env << EOL
# OpenRouter API Configuration
OPENROUTER_API_KEY=your_api_key_here
EOL
    chmod 600 .env
    echo "Please update .env with your actual OpenRouter API key"
    check_status ".env file creation"
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
        echo "✗ Error: Required directory $dir is missing"
        exit 1
    fi
done
echo "✓ Project structure verification passed"

print_header "Checking data files"

# Check enriched parquet file
if ! check_md5sum "data/geo-reviews-enriched.parquet" "85fa8d4819131e645b72f5361c004ce3"; then
    echo "Need to generate Parquet files for Reviews and Enrich it with embeddings for review texts"
    
    # Check if raw TSKV file exists with correct md5sum
    if ! check_md5sum "data/geo-reviews-dataset-2023.tskv" "857fe8ae8af5f5165da3e1674e6f588a"; then
        echo "Downloading geo-reviews dataset..."
        mkdir -p data
        wget -O data/geo-reviews-dataset-2023.tskv https://raw.githubusercontent.com/yandex/geo-reviews-dataset-2023/master/geo-reviews-dataset-2023.tskv
        
        if ! check_md5sum "data/geo-reviews-dataset-2023.tskv" "857fe8ae8af5f5165da3e1674e6f588a"; then
            echo "✗ Error: Downloaded file has incorrect md5sum"
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
    
    if ! check_md5sum "data/geo-reviews-enriched.parquet" "85fa8d4819131e645b72f5361c004ce3"; then
        echo "✗ Error: Generated enriched parquet file has incorrect md5sum"
        exit 1
    fi
fi

print_header "Setup complete!"
echo "To complete the setup:"
echo "1. Update .env with your OpenRouter API key from https://openrouter.ai/"
echo "2. Run: streamlit run app.py"
echo ""
echo "Development workflow:"
echo "1. Create issue on GitHub"
echo "2. Create branch: issue-<number>/<category>/<description>"
echo "3. Make changes following conventional commits"
echo "4. Create pull request"
echo "5. Get code review"
echo "6. Merge to main"
echo ""
echo "Commit message format:"
echo "<type>[area]: <description>"
echo ""
echo "Types: feat, fix, docs, style, refactor, test, chore, perf, ci, build, revert"
echo ""
echo "LLM Integration Notes:"
echo "- Model: google/gemini-flash-1.5 via OpenRouter API"
echo "- Review generation workflow: validation → generation → quality check"
echo "- Automatic retries on failure (max 3 attempts)"
echo "- 15-second timeout per generation attempt"
