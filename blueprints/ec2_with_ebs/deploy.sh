#!/bin/bash

# EC2 with EBS Blueprint Deployment Script
# This script deploys the EC2 with EBS blueprint infrastructure

set -e

# Process command line arguments
DESTROY=false
CREATE_KEY=false
REGION="us-west-2"

show_help() {
  echo "InfraUtilX - EC2 with EBS Blueprint"
  echo ""
  echo "Usage: ./deploy.sh [options]"
  echo ""
  echo "Options:"
  echo "  --destroy       Destroy the deployed resources"
  echo "  --create-key    [Deprecated] Key pair is now managed automatically through Pulumi"
  echo "  --region        AWS region to deploy to (default: us-west-2)"
  echo "  --help          Show this help message"
  echo ""
  exit 0
}

while [[ "$#" -gt 0 ]]; do
  case $1 in
    --destroy) DESTROY=true; shift ;;
    --create-key) CREATE_KEY=true; shift ;;
    --region) REGION="$2"; shift 2 ;;
    --help) show_help ;;
    *) echo "Unknown parameter: $1"; exit 1 ;;
  esac
done

# Check for required tools
command -v pulumi >/dev/null 2>&1 || { echo "Pulumi is required but not installed. Aborting."; exit 1; }
command -v aws >/dev/null 2>&1 || { echo "AWS CLI is required but not installed. Aborting."; exit 1; }

# Check AWS credentials
if ! aws sts get-caller-identity >/dev/null 2>&1; then
  echo "AWS credentials not configured or invalid. Please run 'aws configure'."
  exit 1
fi

# Go to the blueprint directory
THIS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$THIS_DIR"

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
if ! pulumi stack ls 2>/dev/null | grep -q "dev"; then
  echo "Initializing Pulumi stack..."
  pulumi stack init dev
fi

# Set AWS region
echo "Setting AWS region to $REGION..."
pulumi config set aws:region "$REGION"

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
  echo "You can access your instance with the following IP:"
  pulumi stack output public_ip

  echo ""
  echo "Your instance can be accessed using the SSH key:"
  echo "ssh -i ~/.ssh/$(pulumi stack output key_name).pem ubuntu@$(pulumi stack output public_ip)"
  
  echo ""
  echo "To clean up all resources when done, run:"
  echo "./deploy.sh --destroy"
fi 