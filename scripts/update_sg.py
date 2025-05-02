#!/usr/bin/env python3
"""
Pulumi Security Group Update Script

This script provides a way to update security groups with your current IP address
using Pulumi's Python SDK directly, without requiring a full Pulumi project setup.
"""

import argparse
import sys
import os
import json
import subprocess
from typing import Optional, List, Dict, Any

# Add the parent directory to the path so we can import the infrastructure package
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from infrastructure.utils.ip import get_local_public_ip, format_cidr_from_ip

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Update security groups with your current IP address using Pulumi"
    )
    
    parser.add_argument("--sg-id", help="Security group ID to update")
    parser.add_argument("--stack", help="Pulumi stack name")
    parser.add_argument("--port", type=int, default=22, help="Port to allow access to (default: 22)")
    parser.add_argument("--protocol", default="tcp", help="Protocol to allow (default: tcp)")
    
    return parser.parse_args()

def create_pulumi_program(sg_id: str, cidr: str, port: int = 22, protocol: str = "tcp") -> str:
    """
    Create a Pulumi program to update a security group.
    
    Args:
        sg_id: Security group ID
        cidr: CIDR block to add
        port: Port to allow access to
        protocol: Protocol to allow
        
    Returns:
        str: Pulumi program code
    """
    return f"""
import pulumi
import pulumi_aws as aws

# Get the existing security group
sg = aws.ec2.SecurityGroup.get("existing-sg", "{sg_id}")

# Add a new ingress rule for the current IP
new_rule = aws.ec2.SecurityGroupRule("new-ssh-rule",
    type="ingress",
    from_port={port},
    to_port={port},
    protocol="{protocol}",
    cidr_blocks=["{cidr}"],
    security_group_id=sg.id,
    description="Access from {cidr} on port {port}/{protocol}"
)

pulumi.export("updated_sg_id", sg.id)
pulumi.export("new_rule_id", new_rule.id)
"""

def setup_pulumi_project(temp_dir: str, program_code: str, project_name: str = "sg-update") -> bool:
    """
    Set up a temporary Pulumi project.
    
    Args:
        temp_dir: Directory to create the project in
        program_code: Pulumi program code
        project_name: Name for the Pulumi project
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Create directory if it doesn't exist
        os.makedirs(temp_dir, exist_ok=True)
        
        # Create __main__.py
        with open(os.path.join(temp_dir, "__main__.py"), "w") as f:
            f.write(program_code)
        
        # Create Pulumi.yaml
        with open(os.path.join(temp_dir, "Pulumi.yaml"), "w") as f:
            f.write(f"""
name: {project_name}
runtime: python
description: Temporary project to update security group
""")
        
        # Create requirements.txt
        with open(os.path.join(temp_dir, "requirements.txt"), "w") as f:
            f.write("pulumi>=3.0.0\npulumi-aws>=6.0.0\n")
        
        # Install dependencies
        print("Installing Pulumi dependencies...")
        cmd = ["pip", "install", "-r", os.path.join(temp_dir, "requirements.txt")]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"Failed to install dependencies: {result.stderr}")
            return False
            
        return True
        
    except Exception as e:
        print(f"Error setting up Pulumi project: {str(e)}")
        return False

def run_pulumi_update(temp_dir: str, stack_name: str = "dev") -> bool:
    """
    Run Pulumi update on a temporary project.
    
    Args:
        temp_dir: Directory containing the Pulumi project
        stack_name: Name for the Pulumi stack
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Initialize a new stack
        print(f"Initializing Pulumi stack '{stack_name}'...")
        cmd = ["pulumi", "stack", "init", stack_name, "--cwd", temp_dir]
        init_result = subprocess.run(cmd, capture_output=True, text=True)
        
        if init_result.returncode != 0:
            print(f"Failed to initialize stack: {init_result.stderr}")
            return False
        
        # Run the update
        print("Updating security group...")
        cmd = ["pulumi", "up", "--yes", "--cwd", temp_dir]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"Failed to update security group: {result.stderr}")
            return False
            
        print("Security group updated successfully")
        return True
        
    except Exception as e:
        print(f"Error running Pulumi update: {str(e)}")
        return False

def get_sg_id_from_stack(stack_name: str) -> Optional[str]:
    """
    Get security group ID from a Pulumi stack.
    
    Args:
        stack_name: Name of the Pulumi stack
        
    Returns:
        Optional[str]: Security group ID or None if not found
    """
    try:
        cmd = ["pulumi", "stack", "output", "--json", "--stack", stack_name]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"Failed to get stack outputs: {result.stderr}")
            return None
            
        outputs = json.loads(result.stdout)
        
        # Look for security_group_id in outputs
        sg_id = outputs.get("security_group_id")
        if sg_id:
            return sg_id
            
        # If not found, look for other possible output names
        for key, value in outputs.items():
            if "sg" in key.lower() or "security" in key.lower():
                if isinstance(value, str) and value.startswith("sg-"):
                    return value
                    
        print(f"No security group ID found in stack outputs: {list(outputs.keys())}")
        return None
        
    except Exception as e:
        print(f"Error getting security group ID from stack: {str(e)}")
        return None

def main():
    """Main function."""
    args = parse_args()
    
    # Get current IP
    current_ip = get_local_public_ip()
    if not current_ip:
        print("Error: Could not determine current IP address")
        print("Please check your internet connection")
        sys.exit(1)
    
    current_cidr = format_cidr_from_ip(current_ip)
    print(f"Current IP: {current_cidr}")
    
    # Get security group ID
    sg_id = args.sg_id
    
    # If security group ID is not provided directly, try to get it from stack
    if not sg_id and args.stack:
        print(f"Getting security group ID from stack '{args.stack}'...")
        sg_id = get_sg_id_from_stack(args.stack)
        
        if not sg_id:
            print(f"Could not find security group ID in stack '{args.stack}'")
            sys.exit(1)
    
    # If we still don't have a security group ID, exit
    if not sg_id:
        print("Error: Either --sg-id or --stack must be specified")
        sys.exit(1)
    
    # Create a temporary directory for the Pulumi project
    temp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp_sg_update")
    
    # Create Pulumi program
    program_code = create_pulumi_program(sg_id, current_cidr, args.port, args.protocol)
    
    # Set up Pulumi project
    if not setup_pulumi_project(temp_dir, program_code):
        print("Failed to set up Pulumi project")
        sys.exit(1)
    
    # Run Pulumi update
    if not run_pulumi_update(temp_dir):
        print("Failed to update security group")
        sys.exit(1)
    
    print(f"Successfully updated security group {sg_id} to allow access from {current_cidr}")

if __name__ == "__main__":
    main()