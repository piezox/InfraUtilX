#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}VS Code Server Resource Cleanup${NC}"

# Configuration directory and file
CONFIG_DIR="$HOME/.vscode_server"
CONFIG_FILE="$CONFIG_DIR/config"
IP_CACHE_FILE="$CONFIG_DIR/last_ip"

# Check if AWS CLI is available
if ! command -v aws &> /dev/null; then
    echo -e "${RED}AWS CLI is not installed. Please install it first.${NC}"
    exit 1
fi

# Check if AWS credentials are configured
if ! aws sts get-caller-identity &>/dev/null; then
    echo -e "${RED}AWS credentials are not configured or have expired.${NC}"
    echo -e "${YELLOW}Please run 'aws configure' or 'aws sso login' to set up credentials.${NC}"
    exit 1
fi

# Get AWS region from AWS CLI config or use default
AWS_REGION=$(aws configure get region 2>/dev/null || echo "us-west-2")
echo -e "${BLUE}Using AWS region:${NC} ${GREEN}${AWS_REGION}${NC}"

# Check if configuration exists
if [ ! -f "$CONFIG_FILE" ]; then
    echo -e "${YELLOW}No existing configuration found at $CONFIG_FILE${NC}"
    echo -e "${YELLOW}Would you like to search for VS Code Server resources in your AWS account? (y/n)${NC}"
    read -p "" -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${RED}Exiting.${NC}"
        exit 1
    fi
    
    # Search for resources with the VSCodeServer tag
    echo -e "${BLUE}Searching for VS Code Server resources...${NC}"
    INSTANCE_ID=$(aws ec2 describe-instances --filters "Name=tag:Name,Values=VSCodeServer" --region $AWS_REGION --query "Reservations[*].Instances[*].InstanceId" --output text)
    
    if [ -z "$INSTANCE_ID" ]; then
        echo -e "${YELLOW}No VS Code Server instances found.${NC}"
    else
        echo -e "${BLUE}Found VS Code Server instance:${NC} ${GREEN}$INSTANCE_ID${NC}"
    fi
else
    echo -e "${BLUE}Loading existing configuration...${NC}"
    source "$CONFIG_FILE"
    
    # Display configuration
    echo -e "${BLUE}Instance ID:${NC} ${GREEN}$INSTANCE_ID${NC}"
    echo -e "${BLUE}Volume ID:${NC} ${GREEN}$VOLUME_ID${NC}"
    echo -e "${BLUE}Security Group:${NC} ${GREEN}$SECURITY_GROUP_ID${NC}"
    echo -e "${BLUE}Key Path:${NC} ${GREEN}$KEY_PATH${NC}"
fi

# Confirm deletion
echo -e "${RED}WARNING: This will permanently delete all VS Code Server resources.${NC}"
echo -e "${RED}This action cannot be undone.${NC}"
echo -e "${YELLOW}Are you sure you want to proceed? (y/n)${NC}"
read -p "" -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${BLUE}Operation cancelled.${NC}"
    exit 0
fi

# Terminate EC2 instance if it exists
if [ -n "$INSTANCE_ID" ]; then
    echo -e "${BLUE}Terminating EC2 instance ${INSTANCE_ID}...${NC}"
    aws ec2 terminate-instances --instance-ids $INSTANCE_ID --region $AWS_REGION
    
    echo -e "${BLUE}Waiting for instance to terminate...${NC}"
    aws ec2 wait instance-terminated --instance-ids $INSTANCE_ID --region $AWS_REGION
    
    echo -e "${GREEN}Instance terminated successfully.${NC}"
fi

# Delete EBS volume if it exists
if [ -n "$VOLUME_ID" ]; then
    echo -e "${BLUE}Deleting EBS volume ${VOLUME_ID}...${NC}"
    # Wait a bit to ensure the volume is detached
    sleep 10
    aws ec2 delete-volume --volume-id $VOLUME_ID --region $AWS_REGION
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}Volume deleted successfully.${NC}"
    else
        echo -e "${YELLOW}Failed to delete volume. It might still be attached to the instance.${NC}"
        echo -e "${YELLOW}You may need to delete it manually from the AWS console.${NC}"
    fi
fi

# Delete security group if it exists
if [ -n "$SECURITY_GROUP_ID" ]; then
    echo -e "${BLUE}Deleting security group ${SECURITY_GROUP_ID}...${NC}"
    # Wait a bit to ensure the instance is fully terminated
    sleep 10
    aws ec2 delete-security-group --group-id $SECURITY_GROUP_ID --region $AWS_REGION
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}Security group deleted successfully.${NC}"
    else
        echo -e "${YELLOW}Failed to delete security group. It might still be in use.${NC}"
        echo -e "${YELLOW}You may need to delete it manually from the AWS console.${NC}"
    fi
fi

# Delete key pair if it exists
if [ -n "$KEY_PATH" ]; then
    KEY_NAME=$(basename "$KEY_PATH" .pem)
    echo -e "${BLUE}Deleting key pair ${KEY_NAME}...${NC}"
    aws ec2 delete-key-pair --key-name $KEY_NAME --region $AWS_REGION
    
    echo -e "${YELLOW}Do you want to delete the local key file at ${KEY_PATH}? (y/n)${NC}"
    read -p "" -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -f "$KEY_PATH"
        echo -e "${GREEN}Local key file deleted.${NC}"
    else
        echo -e "${BLUE}Local key file preserved.${NC}"
    fi
fi

# Delete configuration files
echo -e "${YELLOW}Do you want to delete the VS Code Server configuration files? (y/n)${NC}"
read -p "" -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    rm -rf "$CONFIG_DIR"
    echo -e "${GREEN}Configuration files deleted.${NC}"
else
    echo -e "${BLUE}Configuration files preserved.${NC}"
fi

echo -e "${GREEN}Cleanup complete!${NC}"
echo -e "${BLUE}All VS Code Server resources have been removed.${NC}"
