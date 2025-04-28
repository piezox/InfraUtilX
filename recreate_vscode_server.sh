#!/bin/bash

# Script to recreate VS Code Server instance using existing persistent volume
# Created: $(date)

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}Recreating VS Code Server on AWS EC2...${NC}"

# Check if configuration file exists
CONFIG_FILE=~/.vscode_server/config
if [ ! -f "$CONFIG_FILE" ]; then
    echo -e "${RED}Configuration file not found. Please run setup_vscode_server.sh first.${NC}"
    exit 1
fi

# Load configuration
source $CONFIG_FILE
echo -e "${BLUE}Loaded configuration:${NC}"
echo -e "  Instance ID: ${YELLOW}$INSTANCE_ID${NC}"
echo -e "  Volume ID: ${YELLOW}$VOLUME_ID${NC}"
echo -e "  Security Group ID: ${YELLOW}$SECURITY_GROUP_ID${NC}"
echo -e "  Region: ${YELLOW}$REGION${NC}"

# Check if volume exists
VOLUME_EXISTS=$(aws ec2 describe-volumes --volume-ids $VOLUME_ID --region $REGION --query "Volumes[0].State" --output text 2>/dev/null)
if [ "$VOLUME_EXISTS" != "available" ] && [ "$VOLUME_EXISTS" != "in-use" ]; then
    echo -e "${RED}Volume $VOLUME_ID not found or not available. Exiting.${NC}"
    exit 1
fi

echo -e "${GREEN}Found existing volume: $VOLUME_ID${NC}"

# Get volume availability zone
AVAILABILITY_ZONE=$(aws ec2 describe-volumes --volume-ids $VOLUME_ID --region $REGION --query "Volumes[0].AvailabilityZone" --output text)
echo -e "${BLUE}Volume is in availability zone: ${YELLOW}$AVAILABILITY_ZONE${NC}"

# Check if instance exists and terminate if it does
INSTANCE_STATE=$(aws ec2 describe-instances --instance-ids $INSTANCE_ID --region $REGION --query "Reservations[0].Instances[0].State.Name" --output text 2>/dev/null)
if [ "$INSTANCE_STATE" != "None" ] && [ -n "$INSTANCE_STATE" ]; then
    echo -e "${YELLOW}Instance $INSTANCE_ID exists in state: $INSTANCE_STATE${NC}"
    
    # Detach volume if attached to the old instance
    ATTACHMENT_STATE=$(aws ec2 describe-volumes --volume-ids $VOLUME_ID --region $REGION --query "Volumes[0].Attachments[0].State" --output text)
    if [ "$ATTACHMENT_STATE" == "attached" ]; then
        echo -e "${BLUE}Detaching volume from existing instance...${NC}"
        aws ec2 detach-volume --volume-id $VOLUME_ID --region $REGION
        
        # Wait for volume to be available
        echo -e "${BLUE}Waiting for volume to become available...${NC}"
        aws ec2 wait volume-available --volume-ids $VOLUME_ID --region $REGION
    fi
    
    # Terminate old instance
    echo -e "${BLUE}Terminating old instance...${NC}"
    aws ec2 terminate-instances --instance-ids $INSTANCE_ID --region $REGION
    
    # Wait for instance to be terminated
    echo -e "${BLUE}Waiting for instance to be terminated...${NC}"
    aws ec2 wait instance-terminated --instance-ids $INSTANCE_ID --region $REGION
fi

# Get latest Ubuntu AMI ID
echo -e "${BLUE}Getting latest Ubuntu AMI ID...${NC}"
AMI_ID=$(aws ec2 describe-images --owners 099720109477 --filters "Name=name,Values=ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*" "Name=state,Values=available" --query "sort_by(Images, &CreationDate)[-1].ImageId" --region $REGION --output text)

if [ -z "$AMI_ID" ]; then
    echo -e "${RED}Failed to get AMI ID. Using default Ubuntu 22.04 AMI.${NC}"
    AMI_ID="ami-0c7217cdde317cfec"  # Default Ubuntu 22.04 LTS in us-east-1
fi

echo -e "${BLUE}Using AMI: ${YELLOW}$AMI_ID${NC}"

# Get key name from existing instance or use default
KEY_NAME=$(aws ec2 describe-instances --instance-ids $INSTANCE_ID --region $REGION --query "Reservations[0].Instances[0].KeyName" --output text 2>/dev/null)
if [ -z "$KEY_NAME" ] || [ "$KEY_NAME" == "None" ]; then
    KEY_NAME="VSCodeServerKey"
    echo -e "${YELLOW}Using default key name: $KEY_NAME${NC}"
else
    echo -e "${BLUE}Using existing key name: ${YELLOW}$KEY_NAME${NC}"
fi

# Launch new EC2 instance in the same availability zone as the volume
echo -e "${BLUE}Launching new EC2 instance...${NC}"
NEW_INSTANCE_ID=$(aws ec2 run-instances \
  --image-id $AMI_ID \
  --count 1 \
  --instance-type t2.micro \
  --key-name $KEY_NAME \
  --security-group-ids $SECURITY_GROUP_ID \
  --placement "AvailabilityZone=$AVAILABILITY_ZONE" \
  --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=VSCodeServer}]" \
  --region $REGION \
  --output json | jq -r '.Instances[0].InstanceId')

if [ -z "$NEW_INSTANCE_ID" ]; then
    echo -e "${RED}Failed to launch EC2 instance. Exiting.${NC}"
    exit 1
fi

echo -e "${GREEN}New EC2 instance launched: ${NEW_INSTANCE_ID}${NC}"

# Update instance ID in config
sed -i.bak "s/INSTANCE_ID=.*/INSTANCE_ID=${NEW_INSTANCE_ID}/" $CONFIG_FILE

# Wait for instance to be running
echo -e "${BLUE}Waiting for instance to be running...${NC}"
aws ec2 wait instance-running --instance-ids $NEW_INSTANCE_ID --region $REGION

# Attach EBS volume to instance
echo -e "${BLUE}Attaching EBS volume to instance...${NC}"
aws ec2 attach-volume --volume-id $VOLUME_ID --instance-id $NEW_INSTANCE_ID --device /dev/sdf --region $REGION

# Get instance public DNS
INSTANCE_DNS=$(aws ec2 describe-instances --instance-ids $NEW_INSTANCE_ID --region $REGION --query "Reservations[0].Instances[0].PublicDnsName" --output text)

echo -e "${GREEN}Instance is now running at: ${INSTANCE_DNS}${NC}"
echo -e "${YELLOW}Waiting 30 seconds for instance to initialize...${NC}"
sleep 30

# Create setup script for the instance
cat > /tmp/setup_code_server.sh << 'EOF'
#!/bin/bash

# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y curl wget gpg apt-transport-https

# Format and mount persistent volume if not already mounted
if [ ! -d "/data" ]; then
    echo "Setting up persistent storage volume..."
    # Check if the device exists
    if [ -e "/dev/nvme1n1" ]; then
        DEVICE="/dev/nvme1n1"
    elif [ -e "/dev/xvdf" ]; then
        DEVICE="/dev/xvdf"
    else
        echo "Could not find attached EBS volume device"
        exit 1
    fi
    
    # Create mount point and mount (don't format as it contains data)
    sudo mkdir -p /data
    sudo mount $DEVICE /data
    sudo chown ubuntu:ubuntu /data
    
    # Add to fstab for persistence across reboots
    echo "$DEVICE /data ext4 defaults,nofail 0 2" | sudo tee -a /etc/fstab
fi

# Install code-server
curl -fsSL https://code-server.dev/install.sh | sh

# Configure code-server to use persistent storage
mkdir -p ~/.config/code-server
cat > ~/.config/code-server/config.yaml << INNEREOF
bind-addr: 127.0.0.1:8080
auth: password
password: vscode123  # This should be the same as your previous password
cert: false
user-data-dir: /data/user-data
extensions-dir: /data/extensions
INNEREOF

# Create symbolic link for projects
ln -sf /data/projects ~/projects

# Enable and start the service
sudo systemctl enable --now code-server@$USER

# Install common development tools
sudo apt install -y git build-essential python3-pip nodejs npm

echo "VS Code Server setup complete!"
echo "Your projects are stored in the persistent volume at /data/projects"
echo "Access this directory via the ~/projects symlink"
EOF

# Copy setup script to instance
echo -e "${BLUE}Copying setup script to instance...${NC}"
scp -o StrictHostKeyChecking=no -i ~/.ssh/${KEY_NAME}.pem /tmp/setup_code_server.sh ubuntu@${INSTANCE_DNS}:~/setup_code_server.sh

# Execute setup script
echo -e "${BLUE}Setting up VS Code Server on the instance...${NC}"
ssh -o StrictHostKeyChecking=no -i ~/.ssh/${KEY_NAME}.pem ubuntu@${INSTANCE_DNS} "chmod +x ~/setup_code_server.sh && ~/setup_code_server.sh"

# Update client connection script
echo -e "${BLUE}Updating client connection script...${NC}"
cat > ./connect_vscode_server.sh << EOF
#!/bin/bash

# Script to connect to VS Code Server on EC2
# Created: $(date)

# Configuration
INSTANCE_ID="${NEW_INSTANCE_ID}"
EC2_USER="ubuntu"
KEY_PATH="\$HOME/.ssh/${KEY_NAME}.pem"
LOCAL_PORT=8080
REMOTE_PORT=8080
SECURITY_GROUP_ID="${SECURITY_GROUP_ID}"
AWS_REGION="${REGION}"
SSH_PORT=22
IP_CACHE_FILE="\$HOME/.ec2_last_ip"

# Colors for output
GREEN='\\\033[0;32m'
BLUE='\\\033[0;34m'
YELLOW='\\\033[0;33m'
RED='\\\033[0;31m'
NC='\\\033[0m' # No Color

echo -e "\${BLUE}Preparing connection to VS Code Server...${NC}"

# Get current EC2 instance public DNS name
echo -e "\${BLUE}Getting current EC2 instance public DNS name...${NC}"
EC2_HOST=\$(aws ec2 describe-instances --instance-ids \$INSTANCE_ID --region \$AWS_REGION --query "Reservations[0].Instances[0].PublicDnsName" --output text)

if [ -z "\$EC2_HOST" ] || [ "\$EC2_HOST" == "None" ]; then
    echo -e "\${RED}Failed to get EC2 instance public DNS name. Is the instance running?${NC}"
    exit 1
fi

echo -e "\${BLUE}EC2 instance public DNS name:${NC} \${GREEN}\$EC2_HOST${NC}"

# Get current public IP address
CURRENT_IP=\$(curl -s https://checkip.amazonaws.com)

if [ -z "\$CURRENT_IP" ]; then
    echo -e "\${RED}Failed to get current IP address. Exiting.${NC}"
    exit 1
fi

echo -e "\${BLUE}Current IP address:${NC} \${GREEN}\$CURRENT_IP${NC}"

# Check if IP has changed since last run
UPDATE_NEEDED=true
if [ -f "\$IP_CACHE_FILE" ]; then
    LAST_IP=\$(cat "\$IP_CACHE_FILE")
    if [ "\$CURRENT_IP" == "\$LAST_IP" ]; then
        echo -e "\${YELLOW}IP address unchanged since last run. Skipping security group update.${NC}"
        UPDATE_NEEDED=false
    else
        echo -e "\${YELLOW}IP address has changed since last run.${NC}"
    fi
else
    echo -e "\${YELLOW}First run detected. Will update security group.${NC}"
fi

# Update security group if needed
if [ "\$UPDATE_NEEDED" = true ]; then
    echo -e "\${BLUE}Updating EC2 security group with current IP address...${NC}"
    
    # Revoke all existing SSH rules
    echo -e "\${BLUE}Revoking existing SSH rules...${NC}"
    aws ec2 describe-security-groups --group-ids \$SECURITY_GROUP_ID --region \$AWS_REGION --query "SecurityGroups[0].IpPermissions[?FromPort==\${SSH_PORT}]" --output json | \\
    jq -c '.[]' 2>/dev/null | \\
    while read -r rule; do
        if [ -n "\$rule" ]; then
            cidr=\$(echo \$rule | jq -r '.IpRanges[0].CidrIp')
            echo -e "\${BLUE}Revoking SSH access from${NC} \${RED}\$cidr${NC}"
            aws ec2 revoke-security-group-ingress --group-id \$SECURITY_GROUP_ID --protocol tcp --port \$SSH_PORT --cidr \$cidr --region \$AWS_REGION
        fi
    done
    
    # Add new rule with current IP
    echo -e "\${BLUE}Adding SSH access for current IP${NC} \${GREEN}\$CURRENT_IP/32${NC}"
    aws ec2 authorize-security-group-ingress --group-id \$SECURITY_GROUP_ID --protocol tcp --port \$SSH_PORT --cidr "\$CURRENT_IP/32" --region \$AWS_REGION
    
    # Save current IP for future reference
    echo "\$CURRENT_IP" > "\$IP_CACHE_FILE"
    
    echo -e "\${GREEN}Security group updated successfully!${NC}"
else
    echo -e "\${GREEN}Security group already configured for current IP.${NC}"
fi

# Start the SSH tunnel
echo -e "\${BLUE}Starting SSH tunnel to VS Code Server...${NC}"
echo -e "\${BLUE}VS Code Server will be available at:${NC} \${GREEN}http://localhost:\${LOCAL_PORT}${NC}"
echo -e "\${BLUE}Your projects are available in the ~/projects directory${NC}"
echo -e "\${BLUE}Press Ctrl+C to stop the tunnel${NC}"
echo ""

# Start the SSH tunnel
ssh -i "\$KEY_PATH" -L \${LOCAL_PORT}:localhost:\${REMOTE_PORT} \${EC2_USER}@\${EC2_HOST}

# This part will execute when SSH connection ends
echo -e "\${BLUE}SSH tunnel closed${NC}"
EOF

chmod +x ./connect_vscode_server.sh

echo -e "${GREEN}Recreation complete!${NC}"
echo -e "${BLUE}Your VS Code Server instance ID:${NC} ${GREEN}${NEW_INSTANCE_ID}${NC}"
echo -e "${BLUE}To connect to your VS Code Server, run:${NC} ${GREEN}./connect_vscode_server.sh${NC}"
echo -e "${BLUE}Your persistent data is preserved in the EBS volume:${NC} ${GREEN}${VOLUME_ID}${NC}"
