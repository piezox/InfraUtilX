import pytest
import pulumi
import pulumi_aws as aws
from typing import Any
from infrastructure.ec2.instances import create_instance, get_instance_public_ip, get_instance_private_ip

@pytest.fixture
def mock_vpc():
    """Create a mock VPC for testing."""
    return aws.ec2.Vpc(
        "test-vpc",
        cidr_block="10.0.0.0/16",
        tags={"Name": "test-vpc"}
    )

@pytest.fixture
def mock_security_group(mock_vpc):
    """Create a mock security group for testing."""
    return aws.ec2.SecurityGroup(
        "test-sg",
        vpc_id=mock_vpc.id,
        description="Test security group",
        tags={"Name": "test-sg"}
    )

def test_create_instance(mock_vpc, mock_security_group):
    """Test EC2 instance creation with default settings."""
    # Create instance
    instance = create_instance(
        name="test-instance",
        instance_type="t2.micro",
        vpc=mock_vpc,
        security_group_ids=[mock_security_group.id],
        tags={"Name": "test-instance"}
    )
    
    # Verify instance properties are Output objects
    assert isinstance(instance.instance_type, pulumi.Output)
    assert isinstance(instance.associate_public_ip_address, pulumi.Output)
    assert isinstance(instance.root_block_device.volume_size, pulumi.Output)
    assert isinstance(instance.root_block_device.volume_type, pulumi.Output)
    assert isinstance(instance.root_block_device.delete_on_termination, pulumi.Output)

    # Verify expected values using apply
    def check_instance_values(values):
        instance_type, public_ip, volume_size, volume_type, delete_on_term = values
        assert instance_type == "t2.micro"
        assert public_ip is True
        assert volume_size == 20
        assert volume_type == "gp3"
        assert delete_on_term is True
        return True

    pulumi.Output.all(
        instance.instance_type,
        instance.associate_public_ip_address,
        instance.root_block_device.volume_size,
        instance.root_block_device.volume_type,
        instance.root_block_device.delete_on_termination
    ).apply(check_instance_values)

def test_create_instance_with_custom_ami(mock_vpc, mock_security_group):
    """Test EC2 instance creation with custom AMI."""
    custom_ami = "ami-0c55b159cbfafe1f0"
    
    # Create instance with custom AMI
    instance = create_instance(
        name="test-instance-custom-ami",
        instance_type="t2.micro",
        vpc=mock_vpc,
        security_group_ids=[mock_security_group.id],
        ami_id=custom_ami,
        tags={"Name": "test-instance-custom-ami"}
    )
    
    # Verify AMI is an Output and has expected value
    assert isinstance(instance.ami, pulumi.Output)
    instance.ami.apply(lambda ami: assert_equal(ami, custom_ami))

def test_create_instance_with_user_data(mock_vpc, mock_security_group):
    """Test EC2 instance creation with user data."""
    user_data = """#!/bin/bash
    echo "Hello, World!"
    """
    
    # Create instance with user data
    instance = create_instance(
        name="test-instance-userdata",
        instance_type="t2.micro",
        vpc=mock_vpc,
        security_group_ids=[mock_security_group.id],
        user_data=user_data,
        tags={"Name": "test-instance-userdata"}
    )
    
    # Verify user data is an Output and has expected value
    assert isinstance(instance.user_data, pulumi.Output)
    instance.user_data.apply(lambda data: assert_equal(data, user_data))

def test_get_instance_ips(mock_vpc, mock_security_group):
    """Test getting instance IP addresses."""
    # Create instance
    instance = create_instance(
        name="test-instance-ips",
        instance_type="t2.micro",
        vpc=mock_vpc,
        security_group_ids=[mock_security_group.id],
        tags={"Name": "test-instance-ips"}
    )
    
    # Get IPs
    public_ip = get_instance_public_ip(instance)
    private_ip = get_instance_private_ip(instance)
    
    # Verify IPs are Output objects
    assert isinstance(public_ip, pulumi.Output)
    assert isinstance(private_ip, pulumi.Output)

def assert_equal(actual, expected):
    assert actual == expected, f"Expected {expected}, but got {actual}" 