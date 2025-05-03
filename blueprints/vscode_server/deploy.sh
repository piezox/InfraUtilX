#!/bin/bash

# VS Code Server Blueprint Deployment Script
# This script deploys the VS Code Server blueprint infrastructure

set -e

# Process command line arguments
DESTROY=false
CREATE_KEY=false
REGION=""
PROFILE=""
ENV_FILE=".env"
SSO_LOGIN=false
SKIP_PROMPTS=false
TEST_SSH=true

show_help() {
  echo "InfraUtilX - VS Code Server Blueprint"
  echo ""
  echo "Usage: ./deploy.sh [options]"
  echo ""
  echo "Options:"
  echo "  --destroy       Destroy the deployed resources"
  echo "  --region        AWS region to deploy to (overrides .env setting)"
  echo "  --profile       AWS profile to use (overrides .env setting)"
  echo "  --env-file      Path to environment file (default: .env)"
  echo "  --sso-login     Force AWS SSO login before deployment"
  echo "  --skip-prompts  Skip interactive prompts and use defaults"
  echo "  --no-test-ssh   Skip SSH connectivity test after deployment"
  echo "  --help          Show this help message"
  echo ""
  exit 0
}

while [[ "$#" -gt 0 ]]; do
  case $1 in
    --destroy) DESTROY=true; shift ;;
    --region) REGION="$2"; shift 2 ;;
    --profile) PROFILE="$2"; shift 2 ;;
    --env-file) ENV_FILE="$2"; shift 2 ;;
    --sso-login) SSO_LOGIN=true; shift ;;
    --skip-prompts) SKIP_PROMPTS=true; shift ;;
    --no-test-ssh) TEST_SSH=false; shift ;;
    --help) show_help ;;
    *) echo "Unknown parameter: $1"; exit 1 ;;
  esac
done

# Go to the blueprint directory
THIS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$THIS_DIR"

# Function to create or update .env file
setup_env_file() {
  local env_file="$1"
  local template_exists=false
  local temp_env_file="${env_file}.tmp"
  
  # Create a temporary file first
  if [ -f ".env.example" ]; then
    cp .env.example "$temp_env_file"
    template_exists=true
  else
    echo "# Environment variables for InfraUtilX VS Code Server Blueprint" > "$temp_env_file"
    echo "" >> "$temp_env_file"
    echo "# Pulumi configuration" >> "$temp_env_file"
    echo "PULUMI_CONFIG_PASSPHRASE=" >> "$temp_env_file"
    echo "# Force Pulumi to use the AWS SDK's credential chain" >> "$temp_env_file"
    echo "PULUMI_ACCESS_TOKEN=" >> "$temp_env_file"
    echo "" >> "$temp_env_file"
    echo "# AWS configuration" >> "$temp_env_file"
    echo "AWS_REGION=us-west-2" >> "$temp_env_file"
    echo "AWS_PROFILE=default" >> "$temp_env_file"
    echo "AWS_SSO_PROFILE=" >> "$temp_env_file"
    echo "" >> "$temp_env_file"
    echo "# Blueprint configuration" >> "$temp_env_file"
    echo "INSTANCE_TYPE=t3.medium" >> "$temp_env_file"
    echo "EBS_SIZE=40" >> "$temp_env_file"
    echo "PROJECT_NAME=vscode-server" >> "$temp_env_file"
    echo "ENVIRONMENT=dev" >> "$temp_env_file"
    echo "VSCODE_PORT=8080" >> "$temp_env_file"
    echo "" >> "$temp_env_file"
    echo "# Stack configuration" >> "$temp_env_file"
    echo "PULUMI_STACK=dev" >> "$temp_env_file"
  fi
  
  # Ask for configuration values if not skipping prompts
  if [ "$SKIP_PROMPTS" != "true" ]; then
    # Set up trap to remove temp file on interrupt
    trap 'echo "Setup interrupted. Cleaning up..."; rm -f "$temp_env_file"; exit 1' INT TERM
    
    # Ask for passphrase
    read -p "Enter a passphrase for Pulumi config encryption (leave empty for no passphrase): " PASSPHRASE
    sed -i.bak "s/PULUMI_CONFIG_PASSPHRASE=.*/PULUMI_CONFIG_PASSPHRASE=$PASSPHRASE/" "$temp_env_file" && rm -f "$temp_env_file.bak"
    
    # Ask for AWS region
    read -p "Enter AWS region [us-west-2]: " USER_REGION
    USER_REGION=${USER_REGION:-us-west-2}
    sed -i.bak "s/AWS_REGION=.*/AWS_REGION=$USER_REGION/" "$temp_env_file" && rm -f "$temp_env_file.bak"
    
    # Ask for AWS SSO profile
    read -p "Are you using AWS SSO? (y/n) [n]: " USE_SSO
    USE_SSO=${USE_SSO:-n}
    if [[ "$USE_SSO" == "y" || "$USE_SSO" == "Y" ]]; then
      read -p "Enter your AWS SSO profile name: " SSO_PROFILE
      sed -i.bak "s/AWS_SSO_PROFILE=.*/AWS_SSO_PROFILE=$SSO_PROFILE/" "$temp_env_file" && rm -f "$temp_env_file.bak"
      sed -i.bak "s/AWS_PROFILE=.*/AWS_PROFILE=$SSO_PROFILE/" "$temp_env_file" && rm -f "$temp_env_file.bak"
    else
      read -p "Enter AWS profile [default]: " USER_PROFILE
      USER_PROFILE=${USER_PROFILE:-default}
      sed -i.bak "s/AWS_PROFILE=.*/AWS_PROFILE=$USER_PROFILE/" "$temp_env_file" && rm -f "$temp_env_file.bak"
    fi
    
    # Ask for instance type
    read -p "Enter EC2 instance type [t3.medium]: " INSTANCE_TYPE
    INSTANCE_TYPE=${INSTANCE_TYPE:-t3.medium}
    sed -i.bak "s/INSTANCE_TYPE=.*/INSTANCE_TYPE=$INSTANCE_TYPE/" "$temp_env_file" && rm -f "$temp_env_file.bak"
    
    # Ask for EBS size
    read -p "Enter EBS volume size in GB [40]: " EBS_SIZE
    EBS_SIZE=${EBS_SIZE:-40}
    sed -i.bak "s/EBS_SIZE=.*/EBS_SIZE=$EBS_SIZE/" "$temp_env_file" && rm -f "$temp_env_file.bak"
    
    # Ask for project name
    read -p "Enter project name [vscode-server]: " PROJECT_NAME
    PROJECT_NAME=${PROJECT_NAME:-vscode-server}
    sed -i.bak "s/PROJECT_NAME=.*/PROJECT_NAME=$PROJECT_NAME/" "$temp_env_file" && rm -f "$temp_env_file.bak"
    
    # Ask for VS Code Server port
    read -p "Enter VS Code Server port [8080]: " VSCODE_PORT
    VSCODE_PORT=${VSCODE_PORT:-8080}
    sed -i.bak "s/VSCODE_PORT=.*/VSCODE_PORT=$VSCODE_PORT/" "$temp_env_file" && rm -f "$temp_env_file.bak"
    
    # Ask for environment
    read -p "Enter environment name [dev]: " ENVIRONMENT
    ENVIRONMENT=${ENVIRONMENT:-dev}
    sed -i.bak "s/ENVIRONMENT=.*/ENVIRONMENT=$ENVIRONMENT/" "$temp_env_file" && rm -f "$temp_env_file.bak"
    
    # Ask for stack name
    read -p "Enter Pulumi stack name [dev]: " STACK_NAME
    STACK_NAME=${STACK_NAME:-dev}
    sed -i.bak "s/PULUMI_STACK=.*/PULUMI_STACK=$STACK_NAME/" "$temp_env_file" && rm -f "$temp_env_file.bak"
    
    # Remove the trap now that we're done with the questions
    trap - INT TERM
  fi
  
  # Move the temporary file to the final location only after all questions are answered
  mv "$temp_env_file" "$env_file"
  echo "Environment file $env_file has been configured."
}

# Check if .env file exists, if not create it
if [ ! -f "$ENV_FILE" ]; then
  echo "Environment file $ENV_FILE not found. Setting up configuration..."
  setup_env_file "$ENV_FILE"
fi

# Load environment variables from .env file
echo "Loading environment variables from $ENV_FILE..."
export $(grep -v '^#' "$ENV_FILE" | xargs)

# Override with command line arguments if provided
if [ -n "$REGION" ]; then
  export AWS_REGION="$REGION"
fi

if [ -n "$PROFILE" ]; then
  export AWS_PROFILE="$PROFILE"
fi

# Check for required tools
command -v pulumi >/dev/null 2>&1 || { echo "Pulumi is required but not installed. Aborting."; exit 1; }
command -v aws >/dev/null 2>&1 || { echo "AWS CLI is required but not installed. Aborting."; exit 1; }

# Handle AWS SSO login if needed
AWS_SSO_PROFILE=${AWS_SSO_PROFILE:-$AWS_PROFILE}
if [[ -n "$AWS_SSO_PROFILE" ]]; then
  # Check if we need to login
  if [[ "$SSO_LOGIN" == "true" ]] || ! aws sts get-caller-identity --profile "$AWS_SSO_PROFILE" >/dev/null 2>&1; then
    echo "Logging in to AWS SSO with profile $AWS_SSO_PROFILE..."
    aws sso login --profile "$AWS_SSO_PROFILE"
    
    if [ $? -ne 0 ]; then
      echo "AWS SSO login failed. Please check your AWS SSO configuration."
      exit 1
    fi
  fi
  
  # Export AWS SSO credentials to environment variables
  echo "Using AWS SSO credentials from profile $AWS_SSO_PROFILE..."
  export AWS_PROFILE="$AWS_SSO_PROFILE"
  
  # Force Pulumi to use the AWS SDK's credential chain
  export PULUMI_ACCESS_TOKEN=""
fi

# Check AWS credentials
if ! aws sts get-caller-identity >/dev/null 2>&1; then
  echo "AWS credentials not configured or invalid. Please check your AWS configuration."
  exit 1
fi

# Display AWS identity information
echo "Using AWS credentials for:"
aws sts get-caller-identity

# Check if Python virtual environment exists
if [ ! -d "venv" ]; then
  echo "Creating Python virtual environment..."
  python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -e ../../  # Install the InfraUtilX package
pip install -r requirements.txt

# Initialize Pulumi if needed
STACK_NAME=${PULUMI_STACK:-dev}
if ! pulumi stack ls 2>/dev/null | grep -q "$STACK_NAME"; then
  echo "Initializing Pulumi stack $STACK_NAME..."
  pulumi stack init "$STACK_NAME"
fi

# Select the stack
echo "Selecting stack $STACK_NAME..."
pulumi stack select "$STACK_NAME"

# Set AWS region
echo "Setting AWS region to $AWS_REGION..."
pulumi config set aws:region "$AWS_REGION"

# Set AWS profile if using SSO
if [[ -n "$AWS_SSO_PROFILE" ]]; then
  echo "Setting AWS profile to $AWS_SSO_PROFILE..."
  pulumi config set aws:profile "$AWS_SSO_PROFILE"
fi

# Set blueprint configuration if provided in .env
if [ -n "$INSTANCE_TYPE" ]; then
  echo "Setting instance type to $INSTANCE_TYPE..."
  pulumi config set instance_type "$INSTANCE_TYPE"
fi

if [ -n "$EBS_SIZE" ]; then
  echo "Setting EBS size to $EBS_SIZE..."
  pulumi config set ebs_size "$EBS_SIZE"
fi

if [ -n "$PROJECT_NAME" ]; then
  echo "Setting project name to $PROJECT_NAME..."
  pulumi config set project "$PROJECT_NAME"
fi

if [ -n "$ENVIRONMENT" ]; then
  echo "Setting environment to $ENVIRONMENT..."
  pulumi config set environment "$ENVIRONMENT"
fi

if [ -n "$VSCODE_PORT" ]; then
  echo "Setting VS Code Server port to $VSCODE_PORT..."
  pulumi config set vscode_port "$VSCODE_PORT"
fi

if [ "$DESTROY" = true ]; then
  # Destroy resources
  echo "Destroying all resources..."
  pulumi destroy --yes
  echo "Cleanup completed successfully!"
else
  # Run deployment
  echo "Starting deployment..."
  pulumi up --yes

  # Show outputs
  echo "Deployment completed successfully!"
  
  # Get deployment outputs
  PUBLIC_IP=$(pulumi stack output public_ip)
  KEY_NAME=$(pulumi stack output key_name)
  KEY_PATH=$(pulumi stack output key_path)
  VSCODE_URL=$(pulumi stack output vscode_server_url)
  VSCODE_PASSWORD=$(pulumi stack output vscode_server_password)
  
  # Display VS Code Server information
  echo ""
  echo "VS Code Server Information:"
  echo "===================================================================================="
  echo "VS Code Server URL:      $VSCODE_URL"
  echo "VS Code Server Password: $VSCODE_PASSWORD"
  echo "===================================================================================="
  echo ""
  echo "Note: It may take a few minutes for the VS Code Server to finish installing and start."
  echo ""
  
  # Display SSH information
  echo "SSH Command to Connect to Instance:"
  echo "ssh -i \"$KEY_PATH\" ubuntu@$PUBLIC_IP"
  
  # Make the test_ssh.sh script executable if it exists
  if [ -f "test_ssh.sh" ]; then
    chmod +x test_ssh.sh
  fi
  
  # Test SSH connectivity if enabled
  if [ "$TEST_SSH" = true ] && [ -f "test_ssh.sh" ]; then
    echo ""
    echo "Testing SSH connectivity..."
    echo "This may take a few minutes as the instance initializes..."
    echo ""
    
    # Wait a bit for the instance to initialize
    echo "Waiting 60 seconds for the instance to initialize..."
    sleep 60
    
    # Run the SSH test script
    ./test_ssh.sh
  else
    echo ""
    echo "To test SSH connectivity, run:"
    echo "./test_ssh.sh"
  fi
  
  echo ""
  echo "To clean up all resources when done, run:"
  echo "./deploy.sh --destroy"
fi