#!/bin/bash

# VS Code Server Launcher
# This script either connects to an existing VS Code Server or triggers setup if needed
# Created: $(date)

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Configuration directory and file
CONFIG_DIR="$HOME/.vscode_server"
CONFIG_FILE="$CONFIG_DIR/config"
IP_CACHE_FILE="$CONFIG_DIR/last_ip"

# Default values
LOCAL_PORT=8080
REMOTE_PORT=8080
SSH_PORT=22
EC2_USER="ubuntu"

# Get AWS region from AWS CLI config
AWS_REGION=$(aws configure get region 2>/dev/null || echo "us-west-2")

echo -e "${BLUE}VS Code Server Launcher${NC}"
echo -e "${BLUE}Using AWS region:${NC} ${GREEN}${AWS_REGION}${NC}"

# Check if AWS CLI is available
if ! command -v aws &> /dev/null; then
    echo -e "${RED}AWS CLI is not installed. Please install it first.${NC}"
    exit 1
fi

# Check if jq is available
if ! command -v jq &> /dev/null; then
    echo -e "${RED}jq is not installed. Please install it first.${NC}"
    exit 1
fi

# Check if AWS credentials are configured
if ! aws sts get-caller-identity &>/dev/null; then
    echo -e "${RED}AWS credentials are not configured or have expired.${NC}"
    echo -e "${YELLOW}Please run 'aws configure' or 'aws sso login' to set up credentials.${NC}"
    exit 1
fi

# Function to connect to VS Code Server
connect_to_server() {
    local instance_id=$1
    local key_path=$2
    local security_group_id=$3
    
    echo -e "${BLUE}Connecting to VS Code Server...${NC}"
    
    # Check if instance exists and is running
    INSTANCE_STATE=$(aws ec2 describe-instances --instance-ids $instance_id --region $AWS_REGION --query "Reservations[0].Instances[0].State.Name" --output text 2>/dev/null)
    
    if [ -z "$INSTANCE_STATE" ] || [ "$INSTANCE_STATE" == "None" ]; then
        echo -e "${RED}Instance $instance_id not found. It may have been terminated.${NC}"
        echo -e "${YELLOW}Would you like to set up a new VS Code Server? (y/n)${NC}"
        read -p "" -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            # Remove the config file if it exists
            if [ -f "$CONFIG_FILE" ]; then
                rm "$CONFIG_FILE"
            fi
            # Call setup script
            ./setup_vscode_server.sh
            exit 0
        else
            echo -e "${RED}Exiting.${NC}"
            exit 1
        fi
    fi
    
    if [ "$INSTANCE_STATE" != "running" ]; then
        echo -e "${YELLOW}Instance $instance_id is not running (current state: $INSTANCE_STATE).${NC}"
        
        if [ "$INSTANCE_STATE" == "stopped" ]; then
            echo -e "${BLUE}Starting the instance...${NC}"
            aws ec2 start-instances --instance-ids $instance_id --region $AWS_REGION
            
            echo -e "${BLUE}Waiting for instance to start...${NC}"
            aws ec2 wait instance-running --instance-ids $instance_id --region $AWS_REGION
            
            # Give some time for services to start
            echo -e "${YELLOW}Instance started. Waiting 20 seconds for services to initialize...${NC}"
            sleep 20
        else
            echo -e "${RED}Instance is in state '$INSTANCE_STATE' and cannot be started automatically.${NC}"
            echo -e "${YELLOW}Please check the AWS console or run:${NC}"
            echo -e "aws ec2 describe-instances --instance-ids $instance_id --region $AWS_REGION"
            exit 1
        fi
    fi
    
    # Get current EC2 instance public DNS name or public IP
    echo -e "${BLUE}Getting current EC2 instance connection information...${NC}"
    EC2_HOST=$(aws ec2 describe-instances --instance-ids $instance_id --region $AWS_REGION --query "Reservations[0].Instances[0].PublicDnsName" --output text)
    
    # If public DNS name is empty or None, try to get public IP address instead
    if [ -z "$EC2_HOST" ] || [ "$EC2_HOST" == "None" ]; then
        echo -e "${YELLOW}No public DNS name found. Trying public IP address...${NC}"
        EC2_HOST=$(aws ec2 describe-instances --instance-ids $instance_id --region $AWS_REGION --query "Reservations[0].Instances[0].PublicIpAddress" --output text)
        
        if [ -z "$EC2_HOST" ] || [ "$EC2_HOST" == "None" ]; then
            echo -e "${RED}Failed to get EC2 instance public IP address. Is the instance running?${NC}"
            exit 1
        fi
    fi
    
    echo -e "${BLUE}EC2 instance connection address:${NC} ${GREEN}$EC2_HOST${NC}"
    
    # Get current public IP address
    CURRENT_IP=$(curl -s https://checkip.amazonaws.com)
    
    if [ -z "$CURRENT_IP" ]; then
        echo -e "${RED}Failed to get current IP address. Exiting.${NC}"
        exit 1
    fi
    
    echo -e "${BLUE}Current IP address:${NC} ${GREEN}$CURRENT_IP${NC}"
    
    # Check if IP has changed since last run
    UPDATE_NEEDED=true
    if [ -f "$IP_CACHE_FILE" ]; then
        LAST_IP=$(cat "$IP_CACHE_FILE")
        if [ "$CURRENT_IP" == "$LAST_IP" ]; then
            echo -e "${YELLOW}IP address unchanged since last run. Skipping security group update.${NC}"
            UPDATE_NEEDED=false
        else
            echo -e "${YELLOW}IP address has changed since last run.${NC}"
        fi
    else
        echo -e "${YELLOW}First run detected. Will update security group.${NC}"
    fi
    
    # Update security group if needed
    if [ "$UPDATE_NEEDED" = true ]; then
        echo -e "${BLUE}Updating EC2 security group with current IP address...${NC}"
        
        # Check if rule for current IP already exists
        RULE_EXISTS=$(aws ec2 describe-security-groups --group-ids $security_group_id --region $AWS_REGION --query "SecurityGroups[0].IpPermissions[?FromPort==$SSH_PORT].IpRanges[?CidrIp=='$CURRENT_IP/32'].CidrIp" --output text)
        
        if [ -n "$RULE_EXISTS" ]; then
            echo -e "${YELLOW}Rule for current IP $CURRENT_IP/32 already exists. Skipping rule creation.${NC}"
        else
            # Add new rule with current IP
            echo -e "${BLUE}Adding SSH access for current IP${NC} ${GREEN}$CURRENT_IP/32${NC}"
            aws ec2 authorize-security-group-ingress --group-id $security_group_id --protocol tcp --port $SSH_PORT --cidr "$CURRENT_IP/32" --region $AWS_REGION
        fi
        
        # Save current IP for future reference
        mkdir -p "$(dirname "$IP_CACHE_FILE")"
        echo "$CURRENT_IP" > "$IP_CACHE_FILE"
        
        echo -e "${GREEN}Security group updated successfully!${NC}"
    else
        echo -e "${GREEN}Security group already configured for current IP.${NC}"
    fi
    
    # Start the SSH tunnel
    echo -e "${BLUE}Starting SSH tunnel to VS Code Server...${NC}"
    echo -e "${BLUE}VS Code Server will be available at:${NC} ${GREEN}http://localhost:${LOCAL_PORT}${NC}"
    echo -e "${BLUE}Default password is:${NC} ${GREEN}vscode123${NC} ${YELLOW}(Change this in the VS Code Server settings)${NC}"
    echo -e "${BLUE}Press Ctrl+C to stop the tunnel${NC}"
    echo ""
    
    # Start the SSH tunnel
    ssh -i "$key_path" -L ${LOCAL_PORT}:localhost:${REMOTE_PORT} ${EC2_USER}@${EC2_HOST}
    
    # This part will execute when SSH connection ends
    echo -e "${BLUE}SSH tunnel closed${NC}"
}

# Check if configuration exists
if [ -f "$CONFIG_FILE" ]; then
    echo -e "${BLUE}Loading existing configuration...${NC}"
    source "$CONFIG_FILE"
    
    # Display configuration
    echo -e "${BLUE}Instance ID:${NC} ${GREEN}$INSTANCE_ID${NC}"
    echo -e "${BLUE}Security Group:${NC} ${GREEN}$SECURITY_GROUP_ID${NC}"
    echo -e "${BLUE}SSH Key:${NC} ${GREEN}$KEY_PATH${NC}"
    
    # Check if key file exists
    if [ ! -f "$KEY_PATH" ]; then
        echo -e "${RED}SSH key not found at $KEY_PATH. Please check your configuration.${NC}"
        exit 1
    fi
    
    # Connect to the server
    connect_to_server "$INSTANCE_ID" "$KEY_PATH" "$SECURITY_GROUP_ID"
else
    echo -e "${YELLOW}No existing configuration found.${NC}"
    echo -e "${BLUE}Would you like to set up a new VS Code Server? (y/n)${NC}"
    read -p "" -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        # Call setup script
        ./setup_vscode_server.sh
    else
        echo -e "${RED}Exiting.${NC}"
        exit 1
    fi
fi
