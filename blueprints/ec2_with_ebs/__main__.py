"""
Example EC2 Deployment with EBS and Security Group Configuration

This example demonstrates how to:
1. Launch an EC2 instance with all the proper supporting infrastructure
2. Attach an EBS volume for additional storage
3. Configure a security group using the local machine's IP address
"""

import pulumi
import pulumi_aws as aws
from infrastructure.utils import (
    get_default_tags,
    merge_tags,
    get_ubuntu_ami,
    get_local_public_ip,
    format_cidr_from_ip,
)
from infrastructure.networking.vpc import create_vpc, create_subnet, get_availability_zones
from infrastructure.ec2.instances import create_instance
from infrastructure.ec2.security_groups import create_security_group, IngressRule
from infrastructure.ec2.keypairs import ensure_keypair
from infrastructure.storage.ebs import create_ebs_volume, attach_volume

# Configuration
CONFIG = {
    "project": "infrautilx-example",
    "environment": "dev",
    "instance_type": "t2.micro",
    "key_name": "demo-key",  # Must exist in AWS account
    "ebs_size": 20,  # GB
    "ebs_device_name": "/dev/sdf",
    # Use a known working AMI ID
    "ami_id": "ami-075686beab831bb7f",  # Known working Ubuntu AMI
}

# Get default tags
tags = get_default_tags(CONFIG["project"], CONFIG["environment"])

# Ensure the key pair exists in the correct region
key_name, key_path = ensure_keypair(
    name=CONFIG["key_name"],
    tags=merge_tags(tags, {"Name": f"{CONFIG['project']}-key"})
)

# Create a VPC with necessary networking components
# The create_vpc function already creates internet gateway and route tables
vpc, public_route_table = create_vpc(
    name=f"{CONFIG['project']}-vpc",
    cidr_block="10.0.0.0/16",
    enable_dns_hostnames=True,
    tags=tags
)

# Get the first availability zone in the region
availability_zones = get_availability_zones()
first_az = availability_zones[0]

# Create a subnet in the VPC
subnet = create_subnet(
    name=f"{CONFIG['project']}-subnet",
    vpc_id=vpc.id,
    cidr_block="10.0.1.0/24",
    availability_zone=first_az,
    map_public_ip_on_launch=True,
    tags=merge_tags(tags, {"Name": f"{CONFIG['project']}-subnet"}),
    public_route_table_id=public_route_table.id
)

# Get the public IP of the local machine for secure SSH access
local_ip = get_local_public_ip()
if not local_ip:
    raise Exception("Failed to determine local IP address")

local_cidr = format_cidr_from_ip(local_ip)
pulumi.export("authorized_ip", local_cidr)
print(f"Detected local IP address: {local_ip} (CIDR: {local_cidr})")

# Create a security group with SSH access from local IP and a wider range for troubleshooting
ingress_rules = [
    IngressRule(
        protocol="tcp",
        from_port=22,
        to_port=22,
        cidr_blocks=[local_cidr, "0.0.0.0/0"],  # Allow SSH from anywhere for initial troubleshooting
        description="SSH access (includes wider access for troubleshooting)"
    ),
    IngressRule(
        protocol="tcp",
        from_port=80,
        to_port=80,
        cidr_blocks=["0.0.0.0/0"],
        description="HTTP access"
    ),
    IngressRule(
        protocol="tcp",
        from_port=443,
        to_port=443,
        cidr_blocks=["0.0.0.0/0"],
        description="HTTPS access"
    ),
    # Add ICMP for ping tests
    IngressRule(
        protocol="icmp",
        from_port=-1,
        to_port=-1,
        cidr_blocks=["0.0.0.0/0"],
        description="ICMP (ping) access"
    )
]

security_group = create_security_group(
    name=f"{CONFIG['project']}-sg",
    vpc_id=vpc.id,
    description=f"Security group for {CONFIG['project']}",
    ingress_rules=ingress_rules,
    tags=tags
)

# Create an EC2 instance with enhanced user data for SSH troubleshooting
# Use the specified AMI ID instead of the dynamic lookup
ami_id = CONFIG["ami_id"]
instance = create_instance(
    name=f"{CONFIG['project']}-instance",
    instance_type=CONFIG["instance_type"],
    vpc=vpc,
    security_group_ids=[security_group.id],
    key_name=key_name,
    subnet_id=subnet.id,
    tags=merge_tags(tags, {"Name": f"{CONFIG['project']}-instance"}),
    ami_id=ami_id,
    user_data=f"""#!/bin/bash
# Create a log file for troubleshooting
LOGFILE="/var/log/infrautilx-startup.log"
exec > >(tee -a $LOGFILE) 2>&1

# Ensure HOME environment variable is set
export HOME="/home/ubuntu"

echo "===== InfraUtilX Startup Script - $(date) ====="
echo "Starting instance configuration..."

# Ensure SSH is properly configured and running
echo "Configuring SSH service..."
sudo sed -i 's/#PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
sudo sed -i 's/#PubkeyAuthentication yes/PubkeyAuthentication yes/' /etc/ssh/sshd_config
sudo systemctl restart ssh
sudo systemctl status ssh

# Check SSH service status
echo "SSH service status:"
sudo systemctl status ssh | grep Active

# Update packages
echo "Updating packages..."
sudo apt-get update -y
sudo apt-get install -y nginx
sudo systemctl start nginx

# Check network configuration
echo "Network configuration:"
ip addr show
echo "Default route:"
ip route show
echo "DNS configuration:"
cat /etc/resolv.conf

# Wait for devices to settle
echo "Waiting for devices to settle..."
sleep 10

# Get the EBS device name (in case of device name mapping differences)
DEVICE_NAME="{CONFIG['ebs_device_name']}"
echo "Looking for EBS volume at $DEVICE_NAME..."
lsblk

# Find EBS volume - improved method that avoids the root volume
ACTUAL_DEVICE=$(lsblk | grep -v loop | grep disk | grep -v nvme0n1 | awk '{{print $1}}' | head -1)
if [ -z "$ACTUAL_DEVICE" ]; then
    echo "Could not find the EBS volume. Using default: $DEVICE_NAME"
    ACTUAL_DEVICE="xvdf"
else
    echo "Detected EBS volume as /dev/$ACTUAL_DEVICE"
fi
ACTUAL_DEVICE="/dev/$ACTUAL_DEVICE"

# Create mount point
MOUNT_POINT="/data"
sudo mkdir -p $MOUNT_POINT
echo "Created mount point at $MOUNT_POINT"

# Check if the device is already mounted or formatted
if mount | grep -q "$ACTUAL_DEVICE"; then
    echo "Device $ACTUAL_DEVICE is already mounted. Skipping formatting."
else
    # Check if the device has a filesystem
    if sudo file -s $ACTUAL_DEVICE | grep -q "data"; then
        echo "Device $ACTUAL_DEVICE already has a filesystem. Skipping formatting."
    else
        # Format the volume
        echo "Formatting the EBS volume as ext4..."
        sudo mkfs -t ext4 $ACTUAL_DEVICE
    fi
    
    # Mount the volume
    echo "Mounting the EBS volume to $MOUNT_POINT"
    sudo mount $ACTUAL_DEVICE $MOUNT_POINT
    
    # Update fstab to mount on reboot
    EBS_UUID=$(sudo blkid -s UUID -o value $ACTUAL_DEVICE)
    if ! grep -q "$EBS_UUID" /etc/fstab; then
        echo "Adding entry to /etc/fstab for persistent mounting"
        echo "UUID=$EBS_UUID $MOUNT_POINT ext4 defaults,nofail 0 2" | sudo tee -a /etc/fstab
    fi
fi

# Set proper permissions
sudo chown -R ubuntu:ubuntu $MOUNT_POINT
echo "Set permissions on $MOUNT_POINT"

# Create a file to verify setup completed
sudo touch /tmp/startup_complete
echo "EBS volume setup completed successfully" > $MOUNT_POINT/setup_complete.txt

# Create a welcome page with instance info
cat > /var/www/html/index.html << EOF
<!DOCTYPE html>
<html>
<head>
    <title>InfraUtilX Instance</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }}
        h1 {{ color: #333; }}
        .info {{ background-color: #f4f4f4; padding: 20px; border-radius: 5px; }}
    </style>
</head>
<body>
    <h1>InfraUtilX Instance</h1>
    <div class="info">
        <p><strong>Instance ID:</strong> $(curl -s http://169.254.169.254/latest/meta-data/instance-id)</p>
        <p><strong>Instance Type:</strong> $(curl -s http://169.254.169.254/latest/meta-data/instance-type)</p>
        <p><strong>Availability Zone:</strong> $(curl -s http://169.254.169.254/latest/meta-data/placement/availability-zone)</p>
        <p><strong>Public IP:</strong> $(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)</p>
        <p><strong>Setup Completed:</strong> $(date)</p>
    </div>
</body>
</html>
EOF

echo "===== InfraUtilX Startup Script Completed - $(date) ====="
"""
)

# Create EBS volume and attach it to the instance
ebs_volume = create_ebs_volume(
    name=f"{CONFIG['project']}-ebs",
    availability_zone=instance.availability_zone,
    size=CONFIG["ebs_size"],
    volume_type="gp3",
    tags=merge_tags(tags, {"Name": f"{CONFIG['project']}-ebs"})
)

volume_attachment = attach_volume(
    name=f"{CONFIG['project']}-volume-attachment",
    volume_id=ebs_volume.id,
    instance_id=instance.id,
    device_name=CONFIG["ebs_device_name"]
)

# Export important information
pulumi.export("vpc_id", vpc.id)
pulumi.export("subnet_id", subnet.id)
pulumi.export("security_group_id", security_group.id)
pulumi.export("instance_id", instance.id)
pulumi.export("public_ip", instance.public_ip)
pulumi.export("ebs_volume_id", ebs_volume.id)
pulumi.export("key_name", key_name)
pulumi.export("key_path", key_path)