#!/usr/bin/env python3
"""
Test script to validate the EC2 with EBS blueprint.
This does a quick verification that the blueprint components are properly configured
without actually deploying them.
"""

import pulumi
import unittest
from pulumi.runtime import mocks
import importlib.util
import sys
import os

# Path to the __main__.py file
MAIN_PATH = os.path.join(os.path.dirname(__file__), "__main__.py")

# Add the blueprint directory to the Python path
sys.path.append(os.path.dirname(__file__))

# Load the __main__.py module
spec = importlib.util.spec_from_file_location("main", MAIN_PATH)
main = importlib.util.module_from_spec(spec)
sys.modules["main"] = main

# Create mock for Pulumi
class TestingMocks(pulumi.runtime.Mocks):
    def __init__(self):
        self.resources = {}
        
    def new_resource(self, args):
        resource_id = f"{args.typ}::{args.name}"
        self.resources[resource_id] = args.inputs
        outputs = {k: v for k, v in args.inputs.items()}
        return [resource_id, outputs]
        
    def call(self, args):
        if args.token == 'aws:ec2/getAmi:getAmi':
            return {
                'id': 'ami-123456',
                'architecture': 'x86_64',
                'name': 'mock-ami',
                'rootDeviceName': '/dev/xvda',
                'rootDeviceType': 'ebs',
                'virtualizationType': 'hvm',
            }
        if args.token == 'aws:getAvailabilityZones:getAvailabilityZones':
            return {
                'names': ['us-west-2a', 'us-west-2b', 'us-west-2c'],
                'zoneIds': ['usw2-az1', 'usw2-az2', 'usw2-az3'],
            }
        return {}

# Pulumi test case
class TestBlueprint(unittest.TestCase):
    @pulumi.runtime.test
    def test_blueprint(self):
        # Override the creation of an AMI to ensure we can test without AWS credentials
        def get_ami_override(*args, **kwargs):
            return "ami-123456"
            
        def get_azs_override(*args, **kwargs):
            return ['us-west-2a', 'us-west-2b', 'us-west-2c']
            
        # Register mock
        pulumi.runtime.set_mocks(TestingMocks())
        
        # Patch the get_ubuntu_ami function to avoid AWS API calls
        import infrastructure.utils.ami
        infrastructure.utils.ami.get_ubuntu_ami = get_ami_override
        
        # Patch the get_local_public_ip function to avoid network calls
        import infrastructure.utils.ip
        infrastructure.utils.ip.get_local_public_ip = lambda: "192.168.1.100"
        
        # Patch the get_availability_zones function
        import infrastructure.networking.vpc
        infrastructure.networking.vpc.get_availability_zones = get_azs_override
        
        # Import the main module to trigger resource creation
        try:
            spec.loader.exec_module(main)
            
            # Verify VPC resource
            vpc = main.vpc
            self.assertIsNotNone(vpc)
            
            # Verify EC2 instance
            instance = main.instance
            self.assertIsNotNone(instance)
            
            # Verify EBS volume
            ebs_volume = main.ebs_volume
            self.assertIsNotNone(ebs_volume)
            
            # Verify attachment
            attachment = main.volume_attachment
            self.assertIsNotNone(attachment)
            
            # Verify security group
            security_group = main.security_group
            self.assertIsNotNone(security_group)
            
            print("✅ All blueprint resources configured correctly")
            
        except Exception as e:
            self.fail(f"Failed to test blueprint: {str(e)}")

if __name__ == "__main__":
    unittest.main() 