import pytest
import pulumi
import pulumi_aws as aws
from typing import Any
from infrastructure.ec2.security_groups import create_security_group, IngressRule

@pytest.fixture
def mock_vpc():
    """Create a mock VPC for testing."""
    return aws.ec2.Vpc(
        "test-vpc",
        cidr_block="10.0.0.0/16",
        tags={"Name": "test-vpc"}
    )

def test_create_security_group_with_ingress_rules(mock_vpc):
    """Test security group creation with ingress rules."""
    # Define ingress rules
    ingress_rules = [
        IngressRule(
            protocol="tcp",
            from_port=22,
            to_port=22,
            cidr_blocks=["0.0.0.0/0"],
            description="Allow SSH"
        ),
        IngressRule(
            protocol="tcp",
            from_port=80,
            to_port=80,
            cidr_blocks=["0.0.0.0/0"],
            description="Allow HTTP"
        )
    ]
    
    # Create security group
    sg = create_security_group(
        name="test-sg",
        vpc_id=mock_vpc.id,
        description="Test security group",
        ingress_rules=ingress_rules,
        tags={"Name": "test-sg"}
    )
    
    # Verify security group properties are Output objects
    assert isinstance(sg.vpc_id, pulumi.Output)
    assert isinstance(sg.description, pulumi.Output)
    assert isinstance(sg.ingress, pulumi.Output)

    # Verify expected values using apply
    def check_sg_values(values):
        vpc_id, description, ingress = values
        assert vpc_id == mock_vpc.id
        assert description == "Test security group"
        assert len(ingress) == 2  # Two ingress rules
        return True

    pulumi.Output.all(
        sg.vpc_id,
        sg.description,
        sg.ingress
    ).apply(check_sg_values)

def test_create_security_group_with_dict_rules(mock_vpc):
    """Test security group creation with dictionary rules."""
    # Define rules as dictionaries
    ingress_rules = [
        {
            "protocol": "tcp",
            "from_port": 22,
            "to_port": 22,
            "cidr_blocks": ["0.0.0.0/0"],
            "description": "Allow SSH"
        }
    ]
    
    egress_rules = [
        {
            "protocol": "-1",
            "from_port": 0,
            "to_port": 0,
            "cidr_blocks": ["0.0.0.0/0"],
            "description": "Allow all outbound"
        }
    ]
    
    # Create security group
    sg = create_security_group(
        name="test-sg-dict",
        vpc_id=mock_vpc.id,
        description="Test security group with dict rules",
        ingress_rules=ingress_rules,
        egress_rules=egress_rules,
        tags={"Name": "test-sg-dict"}
    )
    
    # Verify security group properties are Output objects
    assert isinstance(sg.vpc_id, pulumi.Output)
    assert isinstance(sg.ingress, pulumi.Output)
    assert isinstance(sg.egress, pulumi.Output)

    # Verify expected values using apply
    def check_sg_dict_values(values):
        vpc_id, ingress, egress = values
        assert vpc_id == mock_vpc.id
        assert len(ingress) == 1  # One ingress rule
        assert len(egress) == 1  # One egress rule
        return True

    pulumi.Output.all(
        sg.vpc_id,
        sg.ingress,
        sg.egress
    ).apply(check_sg_dict_values)

def test_create_security_group_with_default_egress(mock_vpc):
    """Test security group creation with default egress rules."""
    # Define only ingress rules
    ingress_rules = [
        IngressRule(
            protocol="tcp",
            from_port=22,
            to_port=22,
            cidr_blocks=["0.0.0.0/0"],
            description="Allow SSH"
        )
    ]
    
    # Create security group
    sg = create_security_group(
        name="test-sg-default-egress",
        vpc_id=mock_vpc.id,
        description="Test security group with default egress",
        ingress_rules=ingress_rules,
        tags={"Name": "test-sg-default-egress"}
    )
    
    # Verify security group properties are Output objects
    assert isinstance(sg.vpc_id, pulumi.Output)
    assert isinstance(sg.ingress, pulumi.Output)
    assert isinstance(sg.egress, pulumi.Output)

    # Verify expected values using apply
    def check_sg_default_egress_values(values):
        vpc_id, ingress, egress = values
        assert vpc_id == mock_vpc.id
        assert len(ingress) == 1  # One ingress rule
        assert len(egress) == 1  # Default egress rule
        return True

    pulumi.Output.all(
        sg.vpc_id,
        sg.ingress,
        sg.egress
    ).apply(check_sg_default_egress_values) 