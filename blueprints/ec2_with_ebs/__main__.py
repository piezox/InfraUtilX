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
vpc = create_vpc(
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
    tags=merge_tags(tags, {"Name": f"{CONFIG['project']}-subnet"})
)

# Get the public IP of the local machine for secure SSH access
local_ip = get_local_public_ip()
if not local_ip:
    raise Exception("Failed to determine local IP address")

local_cidr = format_cidr_from_ip(local_ip)
pulumi.export("authorized_ip", local_cidr)

# Create a security group with SSH access from local IP
ingress_rules = [
    IngressRule(
        protocol="tcp",
        from_port=22,
        to_port=22,
        cidr_blocks=[local_cidr],
        description="SSH access from local machine"
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
    )
]

security_group = create_security_group(
    name=f"{CONFIG['project']}-sg",
    vpc_id=vpc.id,
    description=f"Security group for {CONFIG['project']}",
    ingress_rules=ingress_rules,
    tags=tags
)

# Create an EC2 instance
ami_id = get_ubuntu_ami()
instance = create_instance(
    name=f"{CONFIG['project']}-instance",
    instance_type=CONFIG["instance_type"],
    vpc=vpc,
    security_group_ids=[security_group.id],
    key_name=key_name,
    subnet_id=subnet.id,
    tags=merge_tags(tags, {"Name": f"{CONFIG['project']}-instance"}),
    ami_id=ami_id,
    user_data="""#!/bin/bash
echo "Hello from InfraUtilX Example!"
sudo apt-get update -y
sudo apt-get install -y nginx
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