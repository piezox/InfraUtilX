"""
VS Code Server Blueprint

This blueprint extends the EC2 with EBS blueprint to deploy a VS Code Server
for remote development. It configures an EC2 instance with:
1. VS Code Server installed and accessible via browser
2. An EBS volume for persistent storage of code and settings
3. Proper security groups allowing access only from authorized IPs
"""

import os
import pulumi
import pulumi_aws as aws
import secrets
import string
from pathlib import Path
import sys

# Add parent directory to path to allow importing from ec2_with_ebs blueprint
sys.path.append(str(Path(__file__).parent.parent))

# Import utilities from infrastructure
from infrastructure.utils import (
    get_default_tags,
    merge_tags,
    get_local_public_ip,
    format_cidr_from_ip,
)
from infrastructure.networking.vpc import create_vpc, create_subnet, get_availability_zones
from infrastructure.ec2.instances import create_instance
from infrastructure.ec2.security_groups import create_security_group, IngressRule
from infrastructure.ec2.keypairs import ensure_keypair
from infrastructure.storage.ebs import create_ebs_volume, attach_volume

# Configuration for VS Code Server blueprint, overriding defaults from EC2 with EBS
CONFIG = {
    "project": "vscode-server",
    "environment": "dev",
    "instance_type": "t3.medium",  # Better performance for development
    "key_name": "vscode-key",
    "ebs_size": 40,  # GB - more space for code, packages, and dependencies
    "ebs_device_name": "/dev/sdf",
    "ami_id": "ami-075686beab831bb7f",  # Known working Ubuntu AMI
    "vscode_port": 8080,  # Port for VS Code Server
}

# Generate a secure random password for VS Code Server
def generate_password(length=12):
    """Generate a secure random password for VS Code Server access"""
    alphabet = string.ascii_letters + string.digits
    password = ''.join(secrets.choice(alphabet) for _ in range(length))
    return password

vscode_password = generate_password(16)

# Get default tags
tags = get_default_tags(CONFIG["project"], CONFIG["environment"])

# Ensure the key pair exists in the correct region
key_name, key_path = ensure_keypair(
    name=CONFIG["key_name"],
    tags=merge_tags(tags, {"Name": f"{CONFIG['project']}-key"})
)

# Create a VPC with necessary networking components
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

# Get the public IP of the local machine for secure access
local_ip = get_local_public_ip()
if not local_ip:
    raise Exception("Failed to determine local IP address")

local_cidr = format_cidr_from_ip(local_ip)
pulumi.export("authorized_ip", local_cidr)
print(f"Detected local IP address: {local_ip} (CIDR: {local_cidr})")

# Create a security group with SSH and VS Code Server access from local IP
ingress_rules = [
    # SSH access
    IngressRule(
        protocol="tcp",
        from_port=22,
        to_port=22,
        cidr_blocks=[local_cidr],
        description="SSH access from local IP"
    ),
    # VS Code Server access
    IngressRule(
        protocol="tcp",
        from_port=CONFIG["vscode_port"],
        to_port=CONFIG["vscode_port"],
        cidr_blocks=[local_cidr],
        description="VS Code Server access from local IP"
    ),
    # HTTP access for web interface
    IngressRule(
        protocol="tcp",
        from_port=80,
        to_port=80,
        cidr_blocks=[local_cidr],
        description="HTTP access from local IP"
    ),
    # HTTPS access for secure web interface
    IngressRule(
        protocol="tcp",
        from_port=443,
        to_port=443,
        cidr_blocks=[local_cidr],
        description="HTTPS access from local IP"
    ),
    # ICMP for ping tests
    IngressRule(
        protocol="icmp",
        from_port=-1,
        to_port=-1,
        cidr_blocks=[local_cidr],
        description="ICMP (ping) access from local IP"
    )
]

security_group = create_security_group(
    name=f"{CONFIG['project']}-sg",
    vpc_id=vpc.id,
    description=f"Security group for {CONFIG['project']}",
    ingress_rules=ingress_rules,
    tags=tags
)

# Read the user data template
user_data_template_path = os.path.join(os.path.dirname(__file__), "user_data.sh.tpl")
with open(user_data_template_path, "r") as f:
    user_data_template = f.read()

# Replace template variables
user_data = user_data_template.replace("${vscode_password}", vscode_password)
user_data = user_data.replace("${vscode_port}", str(CONFIG["vscode_port"]))
user_data = user_data.replace("${ebs_device_name}", CONFIG["ebs_device_name"])

# Create an EC2 instance with VS Code Server
instance = create_instance(
    name=f"{CONFIG['project']}-instance",
    instance_type=CONFIG["instance_type"],
    vpc=vpc,
    security_group_ids=[security_group.id],
    key_name=key_name,
    subnet_id=subnet.id,
    tags=merge_tags(tags, {"Name": f"{CONFIG['project']}-instance"}),
    ami_id=CONFIG["ami_id"],
    user_data=user_data
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

# Export VS Code Server specific information
pulumi.export("vscode_server_url", pulumi.Output.concat("http://", instance.public_ip))
pulumi.export("vscode_server_port", CONFIG["vscode_port"])
pulumi.export("vscode_server_password", vscode_password)
pulumi.export("ssh_command", pulumi.Output.concat("ssh -i ", key_path, " ubuntu@", instance.public_ip))

# Print instructions for accessing VS Code Server
@pulumi.runtime.register_stack_transformation
def print_vscode_info(args):
    if args.is_preview:
        print("\nAfter deployment, you will be able to access VS Code Server at:")
        print("http://<instance-public-ip>")
        print(f"Login with the generated password (will be shown in outputs)")
    return None