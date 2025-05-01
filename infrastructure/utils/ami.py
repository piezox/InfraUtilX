import pulumi_aws as aws
from typing import Optional, List, Dict, Any

def get_ubuntu_ami(
    version: str = "22.04",
    architecture: str = "amd64",
    virtualization_type: str = "hvm",
    root_device_type: str = "ebs",
) -> str:
    """
    Get the latest Ubuntu AMI ID.
    
    Args:
        version: Ubuntu version (e.g., "22.04")
        architecture: CPU architecture (amd64, arm64)
        virtualization_type: Virtualization type (hvm, paravirtual)
        root_device_type: Root device type (ebs, instance-store)
    
    Returns:
        str: AMI ID
    """
    ami = aws.ec2.get_ami(
        most_recent=True,
        owners=["099720109477"],  # Canonical
        filters=[
            {
                "name": "name",
                "values": [f"ubuntu/images/{virtualization_type}-{root_device_type}/ubuntu-jammy-{version}-{architecture}-server-*"]
            },
            {
                "name": "virtualization-type",
                "values": [virtualization_type]
            },
            {
                "name": "root-device-type",
                "values": [root_device_type]
            }
        ]
    )
    return ami.id

def get_amazon_linux_ami(
    version: int = 2,
    architecture: str = "x86_64",
    virtualization_type: str = "hvm",
) -> str:
    """
    Get the latest Amazon Linux AMI ID.
    
    Args:
        version: Amazon Linux version (1 or 2)
        architecture: CPU architecture (x86_64, arm64)
        virtualization_type: Virtualization type (hvm, paravirtual)
    
    Returns:
        str: AMI ID
    """
    owners = ["137112412989"]  # Amazon
    name_filter = f"amzn2-ami-*-{architecture}-gp2" if version == 2 else f"amzn-ami-*-{architecture}-gp2"
    
    ami = aws.ec2.get_ami(
        most_recent=True,
        owners=owners,
        filters=[
            {
                "name": "name",
                "values": [name_filter]
            },
            {
                "name": "virtualization-type",
                "values": [virtualization_type]
            }
        ]
    )
    return ami.id 