#!/bin/bash

# VS Code Server Blueprint Destruction Script
# This script destroys the VS Code Server blueprint infrastructure

set -e

# Process command line arguments
ENV_FILE=".env"
SSO_LOGIN=false

show_help() {
  echo "InfraUtilX - VS Code Server Blueprint Destruction"
  echo ""
  echo "Usage: ./destroy.sh [options]"
  echo ""
  echo "Options:"
  echo "  --env-file      Path to environment file (default: .env)"
  echo "  --sso-login     Force AWS SSO login before destruction"
  echo "  --help          Show this help message"
  echo ""
  exit 0
}

while [[ "$#" -gt 0 ]]; do
  case $1 in
    --env-file) ENV_FILE="$2"; shift 2 ;;
    --sso-login) SSO_LOGIN=true; shift ;;
    --help) show_help ;;
    *) echo "Unknown parameter: $1"; exit 1 ;;
  esac
done

# Go to the blueprint directory
THIS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$THIS_DIR"

# Check if .env file exists
if [ ! -f "$ENV_FILE" ]; then
  echo "Environment file $ENV_FILE not found. Please run ./deploy.sh first to create it."
  exit 1
fi

# Load environment variables from .env file
echo "Loading environment variables from $ENV_FILE..."
export $(grep -v '^#' "$ENV_FILE" | xargs)

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

# Activate virtual environment if it exists
if [ -d "venv" ]; then
  echo "Activating virtual environment..."
  source venv/bin/activate
fi

# Select the stack
STACK_NAME=${PULUMI_STACK:-dev}
echo "Selecting stack $STACK_NAME..."
pulumi stack select "$STACK_NAME"

# Set AWS profile if using SSO
if [[ -n "$AWS_SSO_PROFILE" ]]; then
  echo "Setting AWS profile to $AWS_SSO_PROFILE..."
  pulumi config set aws:profile "$AWS_SSO_PROFILE"
fi

# Destroy resources
echo "Destroying all resources..."
pulumi destroy --yes

echo "Cleanup completed successfully!"
echo ""
echo "If you want to completely remove the stack, run:"
echo "pulumi stack rm $STACK_NAME"