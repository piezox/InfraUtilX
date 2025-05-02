#!/usr/bin/env python3
"""
Test script to validate the EC2 with EBS blueprint.
This does a comprehensive verification that the blueprint components are properly configured
without actually deploying them.
"""

import pulumi
import unittest
import sys
import os
from unittest import mock

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from infrastructure.utils import get_default_tags, merge_tags
from infrastructure.networking.vpc import create_vpc, create_subnet

class TestBlueprint(unittest.TestCase):
    """Test cases for the EC2 with EBS blueprint."""
    
    def test_vpc_creation(self):
        """Test VPC creation with proper settings."""
        # Create a VPC
        vpc, route_table = create_vpc(
            name="test-vpc",
            cidr_block="10.0.0.0/16",
            enable_dns_hostnames=True,
            tags={"Name": "test-vpc"}
        )
        
        # Verify VPC properties
        self.assertIsNotNone(vpc)
        self.assertIsNotNone(route_table)
        
        # Check that the VPC has the expected attributes
        def check_vpc_attributes(vpc_id):
            self.assertIsNotNone(vpc_id)
            return True
        
        vpc.id.apply(check_vpc_attributes)
        
        print("✅ VPC creation test passed")
    
    def test_subnet_creation(self):
        """Test subnet creation with proper settings."""
        # Create a VPC first
        vpc, route_table = create_vpc(
            name="test-vpc-for-subnet",
            cidr_block="10.0.0.0/16",
            enable_dns_hostnames=True,
            tags={"Name": "test-vpc-for-subnet"}
        )
        
        # Create a subnet
        subnet = create_subnet(
            name="test-subnet",
            vpc_id=vpc.id,
            cidr_block="10.0.1.0/24",
            availability_zone="us-west-2a",
            map_public_ip_on_launch=True,
            tags={"Name": "test-subnet"},
            public_route_table_id=route_table.id
        )
        
        # Verify subnet properties
        self.assertIsNotNone(subnet)
        
        # Check that the subnet has the expected attributes
        def check_subnet_attributes(subnet_id):
            self.assertIsNotNone(subnet_id)
            return True
        
        subnet.id.apply(check_subnet_attributes)
        
        print("✅ Subnet creation test passed")
    
    def test_security_group_creation(self):
        """Test security group creation with proper rules."""
        # Create a VPC first
        vpc, _ = create_vpc(
            name="test-vpc-for-sg",
            cidr_block="10.0.0.0/16",
            enable_dns_hostnames=True,
            tags={"Name": "test-vpc-for-sg"}
        )
        
        # Import here to avoid circular imports
        from infrastructure.ec2.security_groups import create_security_group, IngressRule
        
        # Define ingress rules
        ingress_rules = [
            IngressRule(
                protocol="tcp",
                from_port=22,
                to_port=22,
                cidr_blocks=["192.168.1.100/32"],
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
        
        # Create a security group
        security_group = create_security_group(
            name="test-sg",
            vpc_id=vpc.id,
            description="Test security group",
            ingress_rules=ingress_rules,
            tags={"Name": "test-sg"}
        )
        
        # Verify security group properties
        self.assertIsNotNone(security_group)
        
        # Check that the security group has the expected attributes
        def check_sg_attributes(sg_id):
            self.assertIsNotNone(sg_id)
            return True
        
        security_group.id.apply(check_sg_attributes)
        
        print("✅ Security group creation test passed")
    
    @mock.patch('infrastructure.ec2.instances.aws.ec2.get_ami')
    def test_instance_creation(self, mock_get_ami):
        """Test EC2 instance creation with proper settings."""
        # Mock the AMI lookup
        mock_ami = mock.MagicMock()
        mock_ami.id = "ami-12345678"
        mock_get_ami.return_value = mock_ami
        
        # Create a VPC first
        vpc, _ = create_vpc(
            name="test-vpc-for-instance",
            cidr_block="10.0.0.0/16",
            enable_dns_hostnames=True,
            tags={"Name": "test-vpc-for-instance"}
        )
        
        # Create a subnet
        subnet = create_subnet(
            name="test-subnet-for-instance",
            vpc_id=vpc.id,
            cidr_block="10.0.1.0/24",
            availability_zone="us-west-2a",
            map_public_ip_on_launch=True,
            tags={"Name": "test-subnet-for-instance"}
        )
        
        # Import here to avoid circular imports
        from infrastructure.ec2.security_groups import create_security_group, IngressRule
        
        # Create a security group
        security_group = create_security_group(
            name="test-sg-for-instance",
            vpc_id=vpc.id,
            description="Test security group for instance",
            ingress_rules=[
                IngressRule(
                    protocol="tcp",
                    from_port=22,
                    to_port=22,
                    cidr_blocks=["0.0.0.0/0"],
                    description="SSH access"
                )
            ],
            tags={"Name": "test-sg-for-instance"}
        )
        
        # Import the instance creation function
        from infrastructure.ec2.instances import create_instance
        
        # Create an EC2 instance with a specific AMI ID to avoid AWS API calls
        instance = create_instance(
            name="test-instance",
            instance_type="t2.micro",
            vpc=vpc,
            security_group_ids=[security_group.id],
            subnet_id=subnet.id,
            tags={"Name": "test-instance"},
            ami_id="ami-12345678",  # Use a specific AMI ID
            user_data="""#!/bin/bash
echo "Hello from test instance"
"""
        )
        
        # Verify instance properties
        self.assertIsNotNone(instance)
        
        # Check that the instance has the expected attributes
        def check_instance_attributes(instance_type):
            self.assertEqual(instance_type, "t2.micro")
            return True
        
        instance.instance_type.apply(check_instance_attributes)
        
        print("✅ Instance creation test passed")
    
    @mock.patch('infrastructure.ec2.instances.aws.ec2.get_ami')
    def test_ebs_volume_creation(self, mock_get_ami):
        """Test EBS volume creation and attachment."""
        # Mock the AMI lookup
        mock_ami = mock.MagicMock()
        mock_ami.id = "ami-12345678"
        mock_get_ami.return_value = mock_ami
        
        # Create a VPC first
        vpc, _ = create_vpc(
            name="test-vpc-for-ebs",
            cidr_block="10.0.0.0/16",
            enable_dns_hostnames=True,
            tags={"Name": "test-vpc-for-ebs"}
        )
        
        # Create a subnet
        subnet = create_subnet(
            name="test-subnet-for-ebs",
            vpc_id=vpc.id,
            cidr_block="10.0.1.0/24",
            availability_zone="us-west-2a",
            map_public_ip_on_launch=True,
            tags={"Name": "test-subnet-for-ebs"}
        )
        
        # Import here to avoid circular imports
        from infrastructure.ec2.security_groups import create_security_group, IngressRule
        from infrastructure.ec2.instances import create_instance
        from infrastructure.storage.ebs import create_ebs_volume, attach_volume
        
        # Create a security group
        security_group = create_security_group(
            name="test-sg-for-ebs",
            vpc_id=vpc.id,
            description="Test security group for EBS",
            ingress_rules=[
                IngressRule(
                    protocol="tcp",
                    from_port=22,
                    to_port=22,
                    cidr_blocks=["0.0.0.0/0"],
                    description="SSH access"
                )
            ],
            tags={"Name": "test-sg-for-ebs"}
        )
        
        # Create an EC2 instance with a specific AMI ID to avoid AWS API calls
        instance = create_instance(
            name="test-instance-for-ebs",
            instance_type="t2.micro",
            vpc=vpc,
            security_group_ids=[security_group.id],
            subnet_id=subnet.id,
            tags={"Name": "test-instance-for-ebs"},
            ami_id="ami-12345678"  # Use a specific AMI ID
        )
        
        # Create an EBS volume
        volume = create_ebs_volume(
            name="test-volume",
            availability_zone="us-west-2a",
            size=20,
            volume_type="gp3",
            encrypted=True,
            tags={"Name": "test-volume"}
        )
        
        # Verify volume properties
        self.assertIsNotNone(volume)
        
        # Check that the volume has the expected attributes
        def check_volume_attributes(volume_type):
            self.assertEqual(volume_type, "gp3")
            return True
        
        volume.type.apply(check_volume_attributes)
        
        # Attach the volume to the instance
        attachment = attach_volume(
            name="test-attachment",
            volume_id=volume.id,
            instance_id=instance.id,
            device_name="/dev/sdf"
        )
        
        # Verify attachment properties
        self.assertIsNotNone(attachment)
        
        # Check that the attachment has the expected attributes
        def check_attachment_attributes(device_name):
            self.assertEqual(device_name, "/dev/sdf")
            return True
        
        attachment.device_name.apply(check_attachment_attributes)
        
        print("✅ EBS volume creation and attachment test passed")
    
    def test_tagging(self):
        """Test tag generation and merging."""
        # Test default tags
        default_tags = get_default_tags("test-project", "dev")
        
        # Verify default tags
        self.assertIn("Project", default_tags)
        self.assertIn("Environment", default_tags)
        self.assertIn("ManagedBy", default_tags)
        self.assertEqual(default_tags["Project"], "test-project")
        self.assertEqual(default_tags["Environment"], "dev")
        self.assertEqual(default_tags["ManagedBy"], "InfraUtilX")
        
        # Test tag merging
        custom_tags = {"Name": "test-resource", "Owner": "test-user"}
        merged_tags = merge_tags(default_tags, custom_tags)
        
        # Verify merged tags
        self.assertIn("Project", merged_tags)
        self.assertIn("Environment", merged_tags)
        self.assertIn("ManagedBy", merged_tags)
        self.assertIn("Name", merged_tags)
        self.assertIn("Owner", merged_tags)
        self.assertEqual(merged_tags["Project"], "test-project")
        self.assertEqual(merged_tags["Environment"], "dev")
        self.assertEqual(merged_tags["ManagedBy"], "InfraUtilX")
        self.assertEqual(merged_tags["Name"], "test-resource")
        self.assertEqual(merged_tags["Owner"], "test-user")
        
        print("✅ Tagging test passed")
    
    def test_blueprint_config(self):
        """Test the blueprint configuration values."""
        # Test the configuration values directly
        import os
        
        # Path to the __main__.py file
        main_path = os.path.join(os.path.dirname(__file__), "__main__.py")
        
        # Read the file content
        with open(main_path, 'r') as f:
            content = f.read()
        
        # Check for expected configuration values
        self.assertIn('"project": "infrautilx-example"', content)
        self.assertIn('"environment": "dev"', content)
        self.assertIn('"instance_type": "t2.micro"', content)
        self.assertIn('"key_name": "demo-key"', content)
        self.assertIn('"ebs_size": 20', content)
        self.assertIn('"ebs_device_name": "/dev/sdf"', content)
        
        print("✅ Blueprint configuration test passed")

if __name__ == "__main__":
    unittest.main()
