#!/bin/bash

# Integrated script to update security group and launch SSH tunnel to VS Code Server
# Created: $(date)

# Configuration
INSTANCE_ID="..."  # Fixed instance ID that won't change on reboot
EC2_USER="ubuntu"
KEY_PATH="$HOME/.ssh/..."
LOCAL_PORT=8080
REMOTE_PORT=8080
SECURITY_GROUP_ID="..."
AWS_REGION="..."
SSH_PORT=22
IP_CACHE_FILE="$HOME/.ec2_last_ip"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}Preparing connection to VS Code Server...${NC}"

# Get current EC2 instance public DNS name
echo -e "${BLUE}Getting current EC2 instance public DNS name...${NC}"
EC2_HOST=$(aws ec2 describe-instances --instance-ids $INSTANCE_ID --region $AWS_REGION --query "Reservations[0].Instances[0].PublicDnsName" --output text)

if [ -z "$EC2_HOST" ] || [ "$EC2_HOST" == "None" ]; then
    echo -e "${RED}Failed to get EC2 instance public DNS name. Is the instance running?${NC}"
    exit 1
fi

echo -e "${BLUE}EC2 instance public DNS name:${NC} ${GREEN}$EC2_HOST${NC}"

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
    
    # Revoke all existing SSH rules
    echo -e "${BLUE}Revoking existing SSH rules...${NC}"
    aws ec2 describe-security-groups --group-ids $SECURITY_GROUP_ID --region $AWS_REGION --query "SecurityGroups[0].IpPermissions[?FromPort==${SSH_PORT}]" --output json | \
    jq -c '.[]' 2>/dev/null | \
    while read -r rule; do
        if [ -n "$rule" ]; then
            cidr=$(echo $rule | jq -r '.IpRanges[0].CidrIp')
            echo -e "${BLUE}Revoking SSH access from${NC} ${RED}$cidr${NC}"
            aws ec2 revoke-security-group-ingress --group-id $SECURITY_GROUP_ID --protocol tcp --port $SSH_PORT --cidr $cidr --region $AWS_REGION
        fi
    done
    
    # Add new rule with current IP
    echo -e "${BLUE}Adding SSH access for current IP${NC} ${GREEN}$CURRENT_IP/32${NC}"
    aws ec2 authorize-security-group-ingress --group-id $SECURITY_GROUP_ID --protocol tcp --port $SSH_PORT --cidr "$CURRENT_IP/32" --region $AWS_REGION
    
    # Save current IP for future reference
    echo "$CURRENT_IP" > "$IP_CACHE_FILE"
    
    echo -e "${GREEN}Security group updated successfully!${NC}"
else
    echo -e "${GREEN}Security group already configured for current IP.${NC}"
fi

# Start the SSH tunnel
echo -e "${BLUE}Starting SSH tunnel to VS Code Server...${NC}"
echo -e "${BLUE}VS Code Server will be available at:${NC} ${GREEN}http://localhost:${LOCAL_PORT}/login${NC}"
echo -e "${BLUE}Press Ctrl+C to stop the tunnel${NC}"
echo ""

# Start the SSH tunnel
ssh -i "$KEY_PATH" -L ${LOCAL_PORT}:localhost:${REMOTE_PORT} ${EC2_USER}@${EC2_HOST}

# This part will execute when SSH connection ends
echo -e "${BLUE}SSH tunnel closed${NC}"
