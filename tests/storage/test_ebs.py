import pytest
import pulumi
import pulumi_aws as aws
from infrastructure.storage.ebs import create_ebs_volume, attach_volume, create_snapshot

@pytest.fixture
def mock_instance():
    """Create a mock EC2 instance for testing."""
    return aws.ec2.Instance(
        "test-instance",
        instance_type="t2.micro",
        ami="ami-0c55b159cbfafe1f0",  # Amazon Linux 2 AMI
        tags={"Name": "test-instance"}
    )

def test_create_ebs_volume():
    """Test EBS volume creation with default settings."""
    # Create volume
    volume = create_ebs_volume(
        name="test-volume",
        availability_zone="us-west-2a",
        size=20,
        tags={"Name": "test-volume"}
    )
    
    # Verify volume properties are Output objects
    assert isinstance(volume.size, pulumi.Output)
    assert isinstance(volume.type, pulumi.Output)
    assert isinstance(volume.encrypted, pulumi.Output)
    assert isinstance(volume.availability_zone, pulumi.Output)

    # Verify expected values using apply
    def check_volume_values(values):
        size, volume_type, encrypted, az = values
        assert size == 20
        assert volume_type == "gp3"
        assert encrypted is True
        assert az == "us-west-2a"
        return True

    pulumi.Output.all(
        volume.size,
        volume.type,
        volume.encrypted,
        volume.availability_zone
    ).apply(check_volume_values)

def test_create_ebs_volume_with_custom_settings():
    """Test EBS volume creation with custom settings."""
    # Create volume with custom settings
    volume = create_ebs_volume(
        name="test-volume-custom",
        availability_zone="us-west-2a",
        size=50,
        volume_type="io1",
        encrypted=False,
        tags={"Name": "test-volume-custom"}
    )
    
    # Verify volume properties are Output objects
    assert isinstance(volume.size, pulumi.Output)
    assert isinstance(volume.type, pulumi.Output)
    assert isinstance(volume.encrypted, pulumi.Output)

    # Verify expected values using apply
    def check_custom_volume_values(values):
        size, volume_type, encrypted = values
        assert size == 50
        assert volume_type == "io1"
        assert encrypted is False
        return True

    pulumi.Output.all(
        volume.size,
        volume.type,
        volume.encrypted
    ).apply(check_custom_volume_values)

def test_attach_volume(mock_instance):
    """Test attaching an EBS volume to an instance."""
    # Create volume
    volume = create_ebs_volume(
        name="test-volume-attach",
        availability_zone="us-west-2a",
        size=20,
        tags={"Name": "test-volume-attach"}
    )
    
    # Attach volume
    attachment = attach_volume(
        name="test-attachment",
        volume_id=volume.id,
        instance_id=mock_instance.id,
        device_name="/dev/sdf"
    )
    
    # Verify attachment properties are Output objects
    assert isinstance(attachment.volume_id, pulumi.Output)
    assert isinstance(attachment.instance_id, pulumi.Output)
    assert isinstance(attachment.device_name, pulumi.Output)

    # Verify expected values using apply
    def check_attachment_values(values):
        volume_id, instance_id, device_name = values
        assert volume_id == volume.id
        assert instance_id == mock_instance.id
        assert device_name == "/dev/sdf"
        return True

    pulumi.Output.all(
        attachment.volume_id,
        attachment.instance_id,
        attachment.device_name
    ).apply(check_attachment_values)

def test_create_snapshot():
    """Test creating an EBS snapshot."""
    # Create volume
    volume = create_ebs_volume(
        name="test-volume-snapshot",
        availability_zone="us-west-2a",
        size=20,
        tags={"Name": "test-volume-snapshot"}
    )
    
    # Create snapshot
    snapshot = create_snapshot(
        name="test-snapshot",
        volume_id=volume.id,
        description="Test snapshot",
        tags={"Name": "test-snapshot"}
    )
    
    # Verify snapshot properties are Output objects
    assert isinstance(snapshot.volume_id, pulumi.Output)
    assert isinstance(snapshot.description, pulumi.Output)

    # Verify expected values using apply
    def check_snapshot_values(values):
        volume_id, description = values
        assert volume_id == volume.id
        assert description == "Test snapshot"
        return True

    pulumi.Output.all(
        snapshot.volume_id,
        snapshot.description
    ).apply(check_snapshot_values) 