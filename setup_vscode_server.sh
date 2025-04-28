#!/bin/bash

# Script to set up a VS Code Server on an EC2 instance
# Created: $(date)

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Configuration
AWS_REGION="us-east-1"
INSTANCE_TYPE="t2.micro"
KEY_NAME="VSCodeServerKey"
SECURITY_GROUP_NAME="vscode-server-sg"
INSTANCE_NAME="VSCodeServer"
AMI_ID="ami-0c7217cdde317cfec"  # Ubuntu 22.04 LTS in us-east-1

echo -e "${BLUE}Setting up VS Code Server on AWS EC2...${NC}"

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo -e "${RED}AWS CLI is not installed. Please install it first.${NC}"
    exit 1
fi

# Check if jq is installed
if ! command -v jq &> /dev/null; then
    echo -e "${RED}jq is not installed. Please install it first.${NC}"
    exit 1
fi

# Create key pair if it doesn't exist
if [ ! -f ~/.ssh/${KEY_NAME}.pem ]; then
    echo -e "${BLUE}Creating new key pair...${NC}"
    aws ec2 create-key-pair --key-name ${KEY_NAME} --query 'KeyMaterial' --output text > ~/.ssh/${KEY_NAME}.pem
    chmod 600 ~/.ssh/${KEY_NAME}.pem
    echo -e "${GREEN}Key pair created at ~/.ssh/${KEY_NAME}.pem${NC}"
else
    echo -e "${YELLOW}Key pair already exists at ~/.ssh/${KEY_NAME}.pem${NC}"
fi

# Create security group
echo -e "${BLUE}Creating security group...${NC}"
SG_ID=$(aws ec2 create-security-group --group-name ${SECURITY_GROUP_NAME} --description "Security group for VS Code Server" --output json | jq -r '.GroupId')

if [ -z "$SG_ID" ]; then
    echo -e "${RED}Failed to create security group. Checking if it already exists...${NC}"
    SG_ID=$(aws ec2 describe-security-groups --filters "Name=group-name,Values=${SECURITY_GROUP_NAME}" --query "SecurityGroups[0].GroupId" --output text)
    
    if [ -z "$SG_ID" ] || [ "$SG_ID" == "None" ]; then
        echo -e "${RED}Could not find or create security group. Exiting.${NC}"
        exit 1
    else
        echo -e "${YELLOW}Using existing security group: ${SG_ID}${NC}"
    fi
else
    echo -e "${GREEN}Security group created: ${SG_ID}${NC}"
    
    # Add SSH rule for current IP
    CURRENT_IP=$(curl -s https://checkip.amazonaws.com)
    echo -e "${BLUE}Adding SSH access for current IP${NC} ${GREEN}$CURRENT_IP/32${NC}"
    aws ec2 authorize-security-group-ingress --group-id ${SG_ID} --protocol tcp --port 22 --cidr "${CURRENT_IP}/32"
fi

# Create persistent EBS volume for development data
echo -e "${BLUE}Creating persistent EBS volume for development data...${NC}"
AVAILABILITY_ZONE=$(aws ec2 describe-availability-zones --region ${AWS_REGION} --query "AvailabilityZones[0].ZoneName" --output text)
VOLUME_ID=$(aws ec2 create-volume \
  --availability-zone ${AVAILABILITY_ZONE} \
  --size 20 \
  --volume-type gp3 \
  --tag-specifications "ResourceType=volume,Tags=[{Key=Name,Value=${INSTANCE_NAME}-Data}]" \
  --output json | jq -r '.VolumeId')

if [ -z "$VOLUME_ID" ]; then
    echo -e "${RED}Failed to create EBS volume. Exiting.${NC}"
    exit 1
fi

echo -e "${GREEN}EBS volume created: ${VOLUME_ID}${NC}"

# Launch EC2 instance in the same availability zone as the volume
echo -e "${BLUE}Launching EC2 instance...${NC}"
INSTANCE_ID=$(aws ec2 run-instances \
  --image-id ${AMI_ID} \
  --count 1 \
  --instance-type ${INSTANCE_TYPE} \
  --key-name ${KEY_NAME} \
  --security-group-ids ${SG_ID} \
  --placement "AvailabilityZone=${AVAILABILITY_ZONE}" \
  --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=${INSTANCE_NAME}}]" \
  --output json | jq -r '.Instances[0].InstanceId')

if [ -z "$INSTANCE_ID" ]; then
    echo -e "${RED}Failed to launch EC2 instance. Exiting.${NC}"
    exit 1
fi

echo -e "${GREEN}EC2 instance launched: ${INSTANCE_ID}${NC}"

# Store instance and volume IDs for future reference
mkdir -p ~/.vscode_server
cat > ~/.vscode_server/config << EOF
INSTANCE_ID=${INSTANCE_ID}
VOLUME_ID=${VOLUME_ID}
SECURITY_GROUP_ID=${SG_ID}
REGION=${AWS_REGION}
EOF

# Wait for instance to be running
echo -e "${BLUE}Waiting for instance to be running...${NC}"
aws ec2 wait instance-running --instance-ids ${INSTANCE_ID}

# Attach EBS volume to instance
echo -e "${BLUE}Attaching EBS volume to instance...${NC}"
aws ec2 attach-volume --volume-id ${VOLUME_ID} --instance-id ${INSTANCE_ID} --device /dev/sdf

# Get instance public DNS
INSTANCE_DNS=$(aws ec2 describe-instances --instance-ids ${INSTANCE_ID} --query "Reservations[0].Instances[0].PublicDnsName" --output text)

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
    
    # Check if the device is already formatted
    if ! sudo file -s $DEVICE | grep -q ext4; then
        sudo mkfs -t ext4 $DEVICE
    fi
    
    # Create mount point and mount
    sudo mkdir -p /data
    sudo mount $DEVICE /data
    sudo chown ubuntu:ubuntu /data
    
    # Add to fstab for persistence across reboots
    echo "$DEVICE /data ext4 defaults,nofail 0 2" | sudo tee -a /etc/fstab
    
    # Create directories for VS Code data
    mkdir -p /data/projects
    mkdir -p /data/extensions
    mkdir -p /data/user-data
fi

# Install code-server
curl -fsSL https://code-server.dev/install.sh | sh

# Configure code-server to use persistent storage
mkdir -p ~/.config/code-server
cat > ~/.config/code-server/config.yaml << INNEREOF
bind-addr: 127.0.0.1:8080
auth: password
password: vscode123  # Change this to a secure password
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

# Create client connection script
echo -e "${BLUE}Creating client connection script...${NC}"
cat > ./connect_vscode_server.sh << EOF
#!/bin/bash

# Script to connect to VS Code Server on EC2
# Created: $(date)

# Configuration
INSTANCE_ID="${INSTANCE_ID}"
EC2_USER="ubuntu"
KEY_PATH="\$HOME/.ssh/${KEY_NAME}.pem"
LOCAL_PORT=8080
REMOTE_PORT=8080
SECURITY_GROUP_ID="${SG_ID}"
AWS_REGION="${AWS_REGION}"
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
echo -e "\${BLUE}Default password is:${NC} \${GREEN}vscode123${NC} \${YELLOW}(Change this in the VS Code Server settings)${NC}"
echo -e "\${BLUE}Press Ctrl+C to stop the tunnel${NC}"
echo ""

# Start the SSH tunnel
ssh -i "\$KEY_PATH" -L \${LOCAL_PORT}:localhost:\${REMOTE_PORT} \${EC2_USER}@\${EC2_HOST}

# This part will execute when SSH connection ends
echo -e "\${BLUE}SSH tunnel closed${NC}"
EOF

chmod +x ./connect_vscode_server.sh

echo -e "${GREEN}Setup complete!${NC}"
echo -e "${BLUE}Your VS Code Server instance ID:${NC} ${GREEN}${INSTANCE_ID}${NC}"
echo -e "${BLUE}To connect to your VS Code Server, run:${NC} ${GREEN}./connect_vscode_server.sh${NC}"
echo -e "${YELLOW}Note: The default password is 'vscode123'. Please change it after first login.${NC}"
echo -e "${BLUE}To stop the instance when not in use (to save costs):${NC} ${GREEN}aws ec2 stop-instances --instance-ids ${INSTANCE_ID}${NC}"
echo -e "${BLUE}To start the instance again:${NC} ${GREEN}aws ec2 start-instances --instance-ids ${INSTANCE_ID}${NC}"
