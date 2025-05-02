#!/usr/bin/env python3
"""
Manage Access Script

This script provides a command-line interface for managing access to InfraUtilX stacks,
including listing stacks, checking access, and updating security group rules.
"""

import argparse
import sys
import os
import json
from typing import Optional, List, Dict, Any

# Add the parent directory to the path so we can import the infrastructure package
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from infrastructure.utils.stack_manager import list_stacks, check_access, update_ip_access
from infrastructure.utils.ip import get_local_public_ip, format_cidr_from_ip

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Manage access to InfraUtilX stacks"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # List stacks command
    list_parser = subparsers.add_parser("list", help="List all stacks")
    list_parser.add_argument("--project", help="Filter stacks by project name")
    list_parser.add_argument("--json", action="store_true", help="Output in JSON format")
    
    # Check access command
    check_parser = subparsers.add_parser("check", help="Check if current IP has access to stacks")
    check_parser.add_argument("--stack", help="Check specific stack")
    check_parser.add_argument("--project", help="Filter stacks by project name")
    check_parser.add_argument("--json", action="store_true", help="Output in JSON format")
    
    # Update access command
    update_parser = subparsers.add_parser("update", help="Update security group to allow access from current IP")
    update_parser.add_argument("stack", help="Stack to update")
    
    return parser.parse_args()

def display_stacks(stacks: List[Dict[str, Any]], json_output: bool = False):
    """Display stack information."""
    if json_output:
        print(json.dumps(stacks, indent=2))
        return
    
    if not stacks:
        print("No stacks found.")
        return
    
    print(f"Found {len(stacks)} stacks:")
    for i, stack in enumerate(stacks, 1):
        print(f"\n{i}. {stack['name']} ({stack['project']})")
        print(f"   Last updated: {stack['last_update']}")
        print(f"   Resources: {stack['resources']}")
        
        # Display key outputs
        outputs = stack.get("outputs", {})
        if "public_ip" in outputs:
            print(f"   Public IP: {outputs['public_ip']}")
        if "vpc_id" in outputs:
            print(f"   VPC ID: {outputs['vpc_id']}")
        if "security_group_id" in outputs:
            print(f"   Security Group ID: {outputs['security_group_id']}")

def display_access_status(access_info: List[Dict[str, Any]], json_output: bool = False):
    """Display access status information."""
    if json_output:
        print(json.dumps(access_info, indent=2))
        return
    
    if not access_info:
        print("No access information available.")
        return
    
    current_ip = get_local_public_ip()
    current_cidr = format_cidr_from_ip(current_ip) if current_ip else "Unknown"
    
    print(f"Current IP: {current_cidr}")
    print(f"\nAccess status for {len(access_info)} stacks:")
    
    for i, info in enumerate(access_info, 1):
        status = "✅ ALLOWED" if info["has_access"] else "❌ DENIED"
        print(f"\n{i}. {info['stack_name']} - {status}")
        print(f"   Security Group: {info['security_group_id']}")
        print(f"   Authorized IPs for SSH:")
        for ip in info["authorized_ips"]:
            if ip == current_cidr:
                print(f"     - {ip} (current)")
            else:
                print(f"     - {ip}")

def main():
    """Main function."""
    args = parse_args()
    
    if args.command == "list":
        stacks = list_stacks(args.project)
        display_stacks(stacks, args.json)
    
    elif args.command == "check":
        access_info = check_access(args.stack, args.project)
        display_access_status(access_info, args.json)
    
    elif args.command == "update":
        success = update_ip_access(args.stack)
        if success:
            print(f"Successfully updated security group in stack {args.stack} to allow access from your current IP.")
        else:
            print(f"Failed to update security group in stack {args.stack}.")
            sys.exit(1)
    
    else:
        print("Please specify a command. Use --help for more information.")
        sys.exit(1)

if __name__ == "__main__":
    main()