#!/bin/bash

# VS Code Server Setup Script
# This script sets up a new VS Code Server on AWS EC2
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

# Get AWS region from AWS CLI config
AWS_REGION=$(aws configure get region 2>/dev/null || echo "us-west-2")
echo -e "${BLUE}Using AWS region:${NC} ${GREEN}${AWS_REGION}${NC}"

# Configuration - Customizable variables
INSTANCE_TYPE="t2.micro"
KEY_NAME="vscode_server_key"
SECURITY_GROUP_NAME="vscode-server-sg"
INSTANCE_NAME="VSCodeServer"
VOLUME_SIZE=20  # Size in GB

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

# Check if AWS credentials are configured
if ! aws sts get-caller-identity &>/dev/null; then
    echo -e "${RED}AWS credentials are not configured or have expired.${NC}"
    echo -e "${YELLOW}Please run 'aws configure' or 'aws sso login' to set up credentials.${NC}"
    exit 1
fi

# Get latest Ubuntu AMI ID for the current region
echo -e "${BLUE}Getting latest Ubuntu AMI ID for region ${AWS_REGION}...${NC}"
AMI_ID=$(aws ec2 describe-images --owners 099720109477 --filters "Name=name,Values=ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*" "Name=state,Values=available" --query "sort_by(Images, &CreationDate)[-1].ImageId" --region $AWS_REGION --output text)

if [ -z "$AMI_ID" ] || [ "$AMI_ID" == "None" ]; then
    echo -e "${RED}Failed to get Ubuntu AMI ID. Exiting.${NC}"
    exit 1
fi

echo -e "${BLUE}Using AMI:${NC} ${GREEN}$AMI_ID${NC}"

# Create key pair if it doesn't exist
KEY_PATH="$HOME/.ssh/${KEY_NAME}.pem"
if [ ! -f "$KEY_PATH" ]; then
    echo -e "${BLUE}Creating new key pair...${NC}"
    aws ec2 create-key-pair --key-name ${KEY_NAME} --query 'KeyMaterial' --output text --region ${AWS_REGION} > "$KEY_PATH"
    chmod 600 "$KEY_PATH"
    echo -e "${GREEN}Key pair created at $KEY_PATH${NC}"
else
    # Check if key exists in AWS
    KEY_EXISTS=$(aws ec2 describe-key-pairs --key-names ${KEY_NAME} --region ${AWS_REGION} --query "KeyPairs[0].KeyName" --output text 2>/dev/null || echo "NOT_FOUND")
    
    if [ "$KEY_EXISTS" == "NOT_FOUND" ]; then
        echo -e "${YELLOW}Key pair exists locally but not in AWS. Creating new key pair...${NC}"
        # Backup the old key
        mv "$KEY_PATH" "${KEY_PATH}.bak"
        echo -e "${YELLOW}Old key backed up to ${KEY_PATH}.bak${NC}"
        # Create new key pair
        aws ec2 create-key-pair --key-name ${KEY_NAME} --query 'KeyMaterial' --output text --region ${AWS_REGION} > "$KEY_PATH"
        chmod 600 "$KEY_PATH"
        echo -e "${GREEN}New key pair created at $KEY_PATH${NC}"
    else
        echo -e "${YELLOW}Key pair already exists at $KEY_PATH${NC}"
    fi
fi

# Create security group
echo -e "${BLUE}Creating security group...${NC}"
# First check if it already exists
SG_ID=$(aws ec2 describe-security-groups --filters "Name=group-name,Values=${SECURITY_GROUP_NAME}" --region ${AWS_REGION} --query "SecurityGroups[0].GroupId" --output text 2>/dev/null || echo "")

if [ -z "$SG_ID" ] || [ "$SG_ID" == "None" ]; then
    # Try to create it
    echo -e "${BLUE}Security group does not exist. Creating new one...${NC}"
    # Create a VPC ID first if needed
    VPC_ID=$(aws ec2 describe-vpcs --region ${AWS_REGION} --query "Vpcs[0].VpcId" --output text 2>/dev/null || echo "")
    
    if [ -z "$VPC_ID" ] || [ "$VPC_ID" == "None" ]; then
        echo -e "${RED}No VPC found. Cannot create security group. Exiting.${NC}"
        exit 1
    fi
    
    echo -e "${BLUE}Using VPC: ${VPC_ID}${NC}"
    SG_ID=$(aws ec2 create-security-group --group-name ${SECURITY_GROUP_NAME} --description "Security group for VS Code Server" --vpc-id ${VPC_ID} --region ${AWS_REGION} --output json 2>/dev/null | jq -r '.GroupId' 2>/dev/null || echo "")
    
    if [ -z "$SG_ID" ] || [ "$SG_ID" == "null" ]; then
        echo -e "${RED}Failed to create security group. Exiting.${NC}"
        exit 1
    else
        echo -e "${GREEN}Security group created: ${SG_ID}${NC}"
        
        # Add SSH rule for current IP
        CURRENT_IP=$(curl -s https://checkip.amazonaws.com)
        echo -e "${BLUE}Adding SSH access for current IP${NC} ${GREEN}$CURRENT_IP/32${NC}"
        aws ec2 authorize-security-group-ingress --group-id ${SG_ID} --protocol tcp --port 22 --cidr "${CURRENT_IP}/32" --region ${AWS_REGION}
    fi
else
    echo -e "${YELLOW}Using existing security group: ${SG_ID}${NC}"
fi

# Create persistent EBS volume for development data
echo -e "${BLUE}Creating persistent EBS volume for development data...${NC}"

# First find a subnet in the VPC associated with the security group
VPC_ID=$(aws ec2 describe-security-groups --group-ids ${SG_ID} --region ${AWS_REGION} --query "SecurityGroups[0].VpcId" --output text)
echo -e "${BLUE}Security group is in VPC: ${VPC_ID}${NC}"

# Get a subnet in this VPC
SUBNET_ID=$(aws ec2 describe-subnets --filters "Name=vpc-id,Values=${VPC_ID}" --region ${AWS_REGION} --query "Subnets[0].SubnetId" --output text)
if [ -z "$SUBNET_ID" ] || [ "$SUBNET_ID" == "None" ]; then
    echo -e "${RED}No subnet found in VPC ${VPC_ID}. Exiting.${NC}"
    exit 1
fi

# Get the availability zone of this subnet
AVAILABILITY_ZONE=$(aws ec2 describe-subnets --subnet-ids ${SUBNET_ID} --region ${AWS_REGION} --query "Subnets[0].AvailabilityZone" --output text)
echo -e "${BLUE}Using subnet ${SUBNET_ID} in availability zone ${AVAILABILITY_ZONE}${NC}"

# Create the volume in the same availability zone as the subnet
VOLUME_ID=$(aws ec2 create-volume \
  --availability-zone ${AVAILABILITY_ZONE} \
  --size ${VOLUME_SIZE} \
  --volume-type gp3 \
  --tag-specifications "ResourceType=volume,Tags=[{Key=Name,Value=${INSTANCE_NAME}-Data}]" \
  --region ${AWS_REGION} \
  --output json | jq -r '.VolumeId')

if [ -z "$VOLUME_ID" ]; then
    echo -e "${RED}Failed to create EBS volume. Exiting.${NC}"
    exit 1
fi

echo -e "${GREEN}EBS volume created: ${VOLUME_ID}${NC}"

# Launch EC2 instance in the same availability zone as the volume
echo -e "${BLUE}Launching EC2 instance...${NC}"
echo -e "${BLUE}Using subnet: ${SUBNET_ID} in availability zone ${AVAILABILITY_ZONE}${NC}"

# Ensure the subnet is configured to auto-assign public IPs
SUBNET_MAP_PUBLIC_IP=$(aws ec2 describe-subnets --subnet-ids ${SUBNET_ID} --region ${AWS_REGION} --query "Subnets[0].MapPublicIpOnLaunch" --output text)
if [ "$SUBNET_MAP_PUBLIC_IP" != "True" ]; then
    echo -e "${YELLOW}Warning: Subnet ${SUBNET_ID} is not configured to auto-assign public IPs.${NC}"
    echo -e "${YELLOW}Temporarily enabling auto-assign public IP for this instance launch...${NC}"
    # We'll use the associate-public-ip-address flag in the run-instances command
fi

INSTANCE_ID=$(aws ec2 run-instances \
  --image-id ${AMI_ID} \
  --count 1 \
  --instance-type ${INSTANCE_TYPE} \
  --key-name ${KEY_NAME} \
  --security-group-ids ${SG_ID} \
  --subnet-id ${SUBNET_ID} \
  --associate-public-ip-address \
  --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=${INSTANCE_NAME}}]" \
  --region ${AWS_REGION} \
  --output json | jq -r '.Instances[0].InstanceId')

if [ -z "$INSTANCE_ID" ]; then
    echo -e "${RED}Failed to launch EC2 instance. Exiting.${NC}"
    exit 1
fi

echo -e "${GREEN}EC2 instance launched: ${INSTANCE_ID}${NC}"

# Store instance and volume IDs for future reference
mkdir -p ${CONFIG_DIR}
cat > ${CONFIG_FILE} << EOF
INSTANCE_ID=${INSTANCE_ID}
VOLUME_ID=${VOLUME_ID}
SECURITY_GROUP_ID=${SG_ID}
REGION=${AWS_REGION}
KEY_PATH=${KEY_PATH}
INSTANCE_TYPE=${INSTANCE_TYPE}
INSTANCE_NAME=${INSTANCE_NAME}
EOF

# Wait for instance to be running
echo -e "${BLUE}Waiting for instance to be running...${NC}"
aws ec2 wait instance-running --instance-ids ${INSTANCE_ID} --region ${AWS_REGION}

# Attach EBS volume to instance
echo -e "${BLUE}Attaching EBS volume to instance...${NC}"
aws ec2 attach-volume --volume-id ${VOLUME_ID} --instance-id ${INSTANCE_ID} --device /dev/sdf --region ${AWS_REGION}

# Wait for network interfaces to be ready and public IP to be assigned
echo -e "${BLUE}Waiting for network interfaces to be ready (this may take a minute)...${NC}"
MAX_RETRIES=12
RETRY_COUNT=0
INSTANCE_DNS=""

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    # Try to get public DNS first
    INSTANCE_DNS=$(aws ec2 describe-instances --instance-ids ${INSTANCE_ID} --region ${AWS_REGION} --query "Reservations[0].Instances[0].PublicDnsName" --output text)
    
    # If public DNS is empty or None, try to get public IP address instead
    if [ -z "$INSTANCE_DNS" ] || [ "$INSTANCE_DNS" == "None" ]; then
        echo -e "${YELLOW}No public DNS name found. Trying public IP address...${NC}"
        INSTANCE_DNS=$(aws ec2 describe-instances --instance-ids ${INSTANCE_ID} --region ${AWS_REGION} --query "Reservations[0].Instances[0].PublicIpAddress" --output text)
    fi
    
    # If we have a valid address, break out of the loop
    if [ -n "$INSTANCE_DNS" ] && [ "$INSTANCE_DNS" != "None" ]; then
        break
    fi
    
    # Otherwise, increment retry count and wait
    RETRY_COUNT=$((RETRY_COUNT+1))
    echo -e "${YELLOW}Attempt $RETRY_COUNT/$MAX_RETRIES: No public address found yet. Waiting 15 seconds...${NC}"
    sleep 15
done

# Check if we got a valid address
if [ -z "$INSTANCE_DNS" ] || [ "$INSTANCE_DNS" == "None" ]; then
    echo -e "${RED}Failed to get EC2 instance public address after multiple attempts.${NC}"
    echo -e "${YELLOW}This could be due to VPC configuration or networking issues.${NC}"
    echo -e "${YELLOW}Please check your VPC settings to ensure instances receive public IPs.${NC}"
    echo -e "${YELLOW}You can try one of the following:${NC}"
    echo -e "${YELLOW}1. Modify your VPC subnet to auto-assign public IPs${NC}"
    echo -e "${YELLOW}2. Manually assign a public IP through the AWS console${NC}"
    echo -e "${YELLOW}3. Restart the script to try again${NC}"
    
    # Get the instance ID for manual troubleshooting
    echo -e "${BLUE}Instance ID for manual troubleshooting: ${INSTANCE_ID}${NC}"
    exit 1
fi

echo -e "${GREEN}Instance is now running at: ${INSTANCE_DNS}${NC}"
echo -e "${YELLOW}Waiting 30 seconds for instance to initialize...${NC}"
sleep 30

# Create update security script for the instance
cat > /tmp/update_security.sh << 'EOF'
#!/bin/bash

# This script updates the security group to allow access from the current IP address
# It's designed to be run on the EC2 instance

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Get instance ID and security group ID
INSTANCE_ID=$(curl -s http://169.254.169.254/latest/meta-data/instance-id)
SECURITY_GROUP_ID=$(aws ec2 describe-instances --instance-ids $INSTANCE_ID --query "Reservations[0].Instances[0].SecurityGroups[0].GroupId" --output text)
AWS_REGION=$(curl -s http://169.254.169.254/latest/meta-data/placement/region)

# Get current public IP address
CURRENT_IP=$(curl -s https://checkip.amazonaws.com)

if [ -z "$CURRENT_IP" ]; then
    echo -e "${RED}Failed to get current IP address. Exiting.${NC}"
    exit 1
fi

echo -e "${BLUE}Current IP address:${NC} ${GREEN}$CURRENT_IP${NC}"
echo -e "${BLUE}Updating EC2 security group with current IP address...${NC}"

# Check if rule for current IP already exists using jq
RULE_EXISTS=$(aws ec2 describe-security-groups --group-ids $SECURITY_GROUP_ID --region $AWS_REGION --output json | 
              jq -r --arg ip "${CURRENT_IP}/32" '.SecurityGroups[0].IpPermissions[] | select(.FromPort==22) | .IpRanges[] | select(.CidrIp==$ip) | .CidrIp' | 
              grep -c "${CURRENT_IP}/32" || echo "0")

if [ "$RULE_EXISTS" != "0" ]; then
    echo -e "${YELLOW}Rule for IP ${CURRENT_IP}/32 already exists${NC}"
else
    echo -e "${BLUE}Adding SSH access for current IP ${CURRENT_IP}/32${NC}"
    aws ec2 authorize-security-group-ingress --group-id $SECURITY_GROUP_ID --protocol tcp --port 22 --cidr "${CURRENT_IP}/32" --region $AWS_REGION
fi

echo -e "${GREEN}Security group updated successfully!${NC}"
EOF

# Create setup script for the instance
cat > /tmp/setup_code_server.sh << 'EOF'
#!/bin/bash

# This script updates the security group to allow access from the current IP address
# It's designed to be run on the EC2 instance

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Get instance ID and security group ID
INSTANCE_ID=$(curl -s http://169.254.169.254/latest/meta-data/instance-id)
SECURITY_GROUP_ID=$(aws ec2 describe-instances --instance-ids $INSTANCE_ID --query "Reservations[0].Instances[0].SecurityGroups[0].GroupId" --output text)
AWS_REGION=$(curl -s http://169.254.169.254/latest/meta-data/placement/region)

# Get current public IP address
CURRENT_IP=$(curl -s https://checkip.amazonaws.com)

if [ -z "$CURRENT_IP" ]; then
    echo -e "${RED}Failed to get current IP address. Exiting.${NC}"
    exit 1
fi

echo -e "${BLUE}Current IP address:${NC} ${GREEN}$CURRENT_IP${NC}"
echo -e "${BLUE}Updating EC2 security group with current IP address...${NC}"

# Check if rule for current IP already exists using jq
RULE_EXISTS=$(aws ec2 describe-security-groups --group-ids $SECURITY_GROUP_ID --region $AWS_REGION --output json | 
              jq -r --arg ip "${CURRENT_IP}/32" '.SecurityGroups[0].IpPermissions[] | select(.FromPort==22) | .IpRanges[] | select(.CidrIp==$ip) | .CidrIp' | 
              grep -c "${CURRENT_IP}/32" || echo "0")

if [ "$RULE_EXISTS" != "0" ]; then
    echo -e "${YELLOW}Rule for IP ${CURRENT_IP}/32 already exists${NC}"
else
    echo -e "${BLUE}Adding SSH access for current IP ${CURRENT_IP}/32${NC}"
    aws ec2 authorize-security-group-ingress --group-id $SECURITY_GROUP_ID --protocol tcp --port 22 --cidr "${CURRENT_IP}/32" --region $AWS_REGION
fi

echo -e "${GREEN}Security group updated successfully!${NC}"
EOF
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

# Copy setup scripts to instance
echo -e "${BLUE}Copying setup scripts to instance...${NC}"
scp -o StrictHostKeyChecking=no -i "$KEY_PATH" /tmp/setup_code_server.sh ubuntu@${INSTANCE_DNS}:~/setup_code_server.sh
scp -o StrictHostKeyChecking=no -i "$KEY_PATH" /tmp/update_security.sh ubuntu@${INSTANCE_DNS}:~/update_security.sh

# Check if the copy was successful
if [ $? -ne 0 ]; then
    echo -e "${RED}Failed to copy setup scripts to instance. Retrying after 30 seconds...${NC}"
    sleep 30
    scp -o StrictHostKeyChecking=no -i "$KEY_PATH" /tmp/setup_code_server.sh ubuntu@${INSTANCE_DNS}:~/setup_code_server.sh
    scp -o StrictHostKeyChecking=no -i "$KEY_PATH" /tmp/update_security.sh ubuntu@${INSTANCE_DNS}:~/update_security.sh
    
    if [ $? -ne 0 ]; then
        echo -e "${RED}Failed to copy setup scripts again. Please check your network connection and security group rules.${NC}"
        echo -e "${YELLOW}Your instance is running at ${INSTANCE_DNS}. You can try to connect manually:${NC}"
        echo -e "ssh -i \"$KEY_PATH\" ubuntu@${INSTANCE_DNS}"
        exit 1
    fi
fi

# Execute setup scripts
echo -e "${BLUE}Setting up VS Code Server on the instance...${NC}"
ssh -o StrictHostKeyChecking=no -i "$KEY_PATH" ubuntu@${INSTANCE_DNS} "chmod +x ~/setup_code_server.sh ~/update_security.sh && ~/setup_code_server.sh"

# Check if the setup was successful
if [ $? -ne 0 ]; then
    echo -e "${RED}Failed to execute setup script on the instance. Retrying...${NC}"
    ssh -o StrictHostKeyChecking=no -i "$KEY_PATH" ubuntu@${INSTANCE_DNS} "chmod +x ~/setup_code_server.sh && ~/setup_code_server.sh"
    
    if [ $? -ne 0 ]; then
        echo -e "${RED}Failed to execute setup script again. Please check the instance manually.${NC}"
        echo -e "${YELLOW}You can connect to the instance and run the setup script manually:${NC}"
        echo -e "ssh -i \"$KEY_PATH\" ubuntu@${INSTANCE_DNS}"
        echo -e "chmod +x ~/setup_code_server.sh && ~/setup_code_server.sh"
        exit 1
    fi
fi

echo -e "${GREEN}Setup complete!${NC}"
echo -e "${BLUE}Your VS Code Server instance ID:${NC} ${GREEN}${INSTANCE_ID}${NC}"
echo -e "${BLUE}Your persistent data is stored in EBS volume:${NC} ${GREEN}${VOLUME_ID}${NC}"
echo -e "${YELLOW}Note: The default password is 'vscode123'. Please change it after first login.${NC}"

# Launch the connection script
echo -e "${BLUE}Connecting to your new VS Code Server...${NC}"
./launch_vscode_server.sh
