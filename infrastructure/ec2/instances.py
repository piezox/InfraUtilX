import pulumi
import pulumi_aws as aws
from typing import List, Optional, Dict, Any

def create_instance(
    name: str,
    instance_type: str,
    vpc: aws.ec2.Vpc,
    security_group_ids: List[str],
    user_data: Optional[str] = None,
    tags: Optional[Dict[str, str]] = None,
    key_name: Optional[str] = None,
    subnet_id: Optional[str] = None,
    ami_id: Optional[str] = None,
) -> aws.ec2.Instance:
    """
    Create an EC2 instance with the specified configuration.
    
    Args:
        name: Name of the instance
        instance_type: EC2 instance type (e.g., t2.micro)
        vpc: VPC to launch the instance in
        security_group_ids: List of security group IDs to attach
        user_data: Optional user data script
        tags: Optional dictionary of tags
        key_name: Optional key pair name for SSH access
        subnet_id: Optional subnet ID to launch in
        ami_id: Optional AMI ID (defaults to latest Ubuntu 22.04)
    
    Returns:
        aws.ec2.Instance: The created EC2 instance
    """
    # Get the latest Ubuntu 22.04 AMI if not specified
    if not ami_id:
        ami = aws.ec2.get_ami(
            most_recent=True,
            owners=["099720109477"],  # Canonical
            filters=[{
                "name": "name",
                "values": ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
            }]
        )
        ami_id = ami.id

    # Create the instance
    instance = aws.ec2.Instance(
        name,
        instance_type=instance_type,
        ami=ami_id,
        vpc_security_group_ids=security_group_ids,
        user_data=user_data,
        tags=tags,
        key_name=key_name,
        subnet_id=subnet_id,
        associate_public_ip_address=True,  # Enable public IP for remote access
        root_block_device=aws.ec2.InstanceRootBlockDeviceArgs(
            volume_size=20,  # 20GB root volume
            volume_type="gp3",
            delete_on_termination=True,
        ),
    )

    return instance

def get_instance_public_ip(instance: aws.ec2.Instance) -> pulumi.Output[str]:
    """
    Get the public IP address of an EC2 instance.
    
    Args:
        instance: The EC2 instance
    
    Returns:
        pulumi.Output[str]: The public IP address
    """
    return instance.public_ip

def get_instance_private_ip(instance: aws.ec2.Instance) -> pulumi.Output[str]:
    """
    Get the private IP address of an EC2 instance.
    
    Args:
        instance: The EC2 instance
    
    Returns:
        pulumi.Output[str]: The private IP address
    """
    return instance.private_ip 