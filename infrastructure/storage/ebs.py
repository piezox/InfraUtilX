import pulumi
import pulumi_aws as aws
from typing import Optional, Dict, Any

def create_ebs_volume(
    name: str,
    availability_zone: str,
    size: int = 20,
    volume_type: str = "gp3",
    encrypted: bool = True,
    kms_key_id: Optional[str] = None,
    tags: Optional[Dict[str, str]] = None,
) -> aws.ebs.Volume:
    """
    Create an EBS volume.
    
    Args:
        name: Name of the volume
        availability_zone: Availability zone to create the volume in
        size: Size in GiB (default: 20)
        volume_type: Type of volume (gp3, gp2, io1, etc.)
        encrypted: Whether to encrypt the volume
        kms_key_id: Optional KMS key ID for encryption
        tags: Optional dictionary of tags
    
    Returns:
        aws.ebs.Volume: The created EBS volume
    """
    volume = aws.ebs.Volume(
        name,
        availability_zone=availability_zone,
        size=size,
        type=volume_type,
        encrypted=encrypted,
        kms_key_id=kms_key_id,
        tags=tags,
    )
    return volume

def attach_volume(
    name: str,
    volume_id: str,
    instance_id: str,
    device_name: str = "/dev/sdf",
) -> aws.ec2.VolumeAttachment:
    """
    Attach an EBS volume to an EC2 instance.
    
    Args:
        name: Name of the attachment
        volume_id: ID of the EBS volume
        instance_id: ID of the EC2 instance
        device_name: Device name on the instance
    
    Returns:
        aws.ec2.VolumeAttachment: The volume attachment
    """
    attachment = aws.ec2.VolumeAttachment(
        name,
        volume_id=volume_id,
        instance_id=instance_id,
        device_name=device_name,
    )
    return attachment

def create_snapshot(
    name: str,
    volume_id: str,
    description: Optional[str] = None,
    tags: Optional[Dict[str, str]] = None,
) -> aws.ebs.Snapshot:
    """
    Create a snapshot of an EBS volume.
    
    Args:
        name: Name of the snapshot
        volume_id: ID of the volume to snapshot
        description: Optional description
        tags: Optional dictionary of tags
    
    Returns:
        aws.ebs.Snapshot: The created snapshot
    """
    snapshot = aws.ebs.Snapshot(
        name,
        volume_id=volume_id,
        description=description,
        tags=tags,
    )
    return snapshot 