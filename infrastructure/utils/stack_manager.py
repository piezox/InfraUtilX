"""
Stack Manager Utility

This module provides utilities for managing Pulumi stacks created with InfraUtilX,
including listing stacks, checking access, and updating security group rules.
"""

import os
import json
import subprocess
import shutil
from typing import List, Dict, Optional, Any, Tuple
from ..utils.ip import get_local_public_ip, format_cidr_from_ip

class StackManager:
    """
    Manages Pulumi stacks created with InfraUtilX.
    """
    
    def __init__(self, project_filter: Optional[str] = None):
        """
        Initialize the stack manager.
        
        Args:
            project_filter: Optional filter to only include stacks from a specific project
        """
        self.project_filter = project_filter
    
    def _check_pulumi_installed(self) -> bool:
        """
        Check if Pulumi CLI is installed and available.
        
        Returns:
            bool: True if Pulumi is installed, False otherwise
        """
        return shutil.which("pulumi") is not None
    
    def list_stacks(self) -> List[Dict[str, Any]]:
        """
        List all Pulumi stacks created with InfraUtilX.
        
        Returns:
            List[Dict[str, Any]]: List of stack information
        """
        # Check if Pulumi is installed
        if not self._check_pulumi_installed():
            print("Error: Pulumi CLI is not installed or not in PATH")
            print("Please install Pulumi CLI: https://www.pulumi.com/docs/install/")
            return []
            
        try:
            # Run pulumi stack ls command with --all flag to list all stacks regardless of current directory
            cmd = ["pulumi", "stack", "ls", "--all", "--json"]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"Error running Pulumi command: {result.stderr}")
                print("Make sure you're logged in to Pulumi: run 'pulumi login'")
                return []
                
            stacks = json.loads(result.stdout)
            
            # Filter stacks if project_filter is specified
            if self.project_filter:
                stacks = [s for s in stacks if s.get("projectName", "").startswith(self.project_filter)]
            
            # Get more details for each stack
            detailed_stacks = []
            for stack in stacks:
                stack_name = stack.get("name")
                project_name = stack.get("projectName")
                if not stack_name or not project_name:
                    continue
                    
                # Format the full stack name as project/stack
                full_stack_name = f"{project_name}/{stack_name}"
                stack_info = self._get_stack_outputs(full_stack_name)
                
                if stack_info:
                    detailed_stacks.append({
                        "name": full_stack_name,
                        "project": project_name,
                        "last_update": stack.get("lastUpdate"),
                        "resources": stack.get("resourceCount"),
                        "outputs": stack_info
                    })
            
            return detailed_stacks
        except json.JSONDecodeError:
            print("Error: Could not parse Pulumi output. Make sure you're logged in to Pulumi.")
            return []
        except Exception as e:
            print(f"Error listing stacks: {str(e)}")
            return []
    
    def _get_stack_outputs(self, stack_name: str) -> Dict[str, Any]:
        """
        Get the outputs for a specific stack.
        
        Args:
            stack_name: Name of the stack (format: project/stack)
            
        Returns:
            Dict[str, Any]: Stack outputs
        """
        if not self._check_pulumi_installed():
            return {}
            
        try:
            # Split the stack name to get project and stack
            parts = stack_name.split('/')
            if len(parts) < 2:
                print(f"Invalid stack name format: {stack_name}. Expected format: project/stack")
                return {}
                
            project_name = parts[0]
            stack_name_only = parts[1]
            
            # Use the --show-secrets flag to ensure we get all outputs
            cmd = ["pulumi", "stack", "output", "--json", "--stack", stack_name_only, "--cwd", "/tmp", "--show-secrets"]
            
            # Set PULUMI_SKIP_UPDATE_CHECK to avoid update checks that might cause errors
            env = os.environ.copy()
            env["PULUMI_SKIP_UPDATE_CHECK"] = "true"
            
            # Try to get outputs directly
            result = subprocess.run(cmd, capture_output=True, text=True, env=env)
            
            # If that fails, try with the full stack name
            if result.returncode != 0:
                cmd = ["pulumi", "stack", "output", "--json", "--stack", stack_name, "--cwd", "/tmp", "--show-secrets"]
                result = subprocess.run(cmd, capture_output=True, text=True, env=env)
            
            if result.returncode == 0:
                return json.loads(result.stdout)
                
            # If we still can't get outputs, try using a Pulumi program to get information
            print(f"Could not get outputs for stack {stack_name}, trying alternative method...")
            return self._get_stack_info_with_pulumi(stack_name)
            
        except json.JSONDecodeError:
            return {}
        except Exception as e:
            print(f"Error getting stack outputs: {str(e)}")
            return {}
    
    def _get_stack_info_with_pulumi(self, stack_name: str) -> Dict[str, Any]:
        """
        Get information about a stack using a Pulumi program.
        This is a fallback method when direct stack output fails.
        
        Args:
            stack_name: Name of the stack
            
        Returns:
            Dict[str, Any]: Stack information
        """
        try:
            # Create a temporary directory for a Pulumi program
            temp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp_stack_info")
            os.makedirs(temp_dir, exist_ok=True)
            
            # Create a temporary Pulumi program to query the stack
            with open(os.path.join(temp_dir, "__main__.py"), "w") as f:
                f.write(f"""
import pulumi
import pulumi_aws as aws

# Query resources in the stack
def get_resources():
    # We'll use tags to find resources associated with this stack
    stack_name = "{stack_name}"
    project_name = stack_name.split('/')[0] if '/' in stack_name else stack_name
    
    # Try to find security groups with the project tag
    try:
        sgs = aws.ec2.SecurityGroup.get_all()
        for sg in sgs:
            if sg.tags and sg.tags.get("Project") == project_name:
                pulumi.export("security_group_id", sg.id)
                break
    except:
        pass
    
    # Try to find EC2 instances with the project tag
    try:
        instances = aws.ec2.Instance.get_all()
        for instance in instances:
            if instance.tags and instance.tags.get("Project") == project_name:
                pulumi.export("instance_id", instance.id)
                pulumi.export("public_ip", instance.public_ip)
                break
    except:
        pass

# Call the function to get resources
get_resources()
""")
            
            # Create Pulumi.yaml
            with open(os.path.join(temp_dir, "Pulumi.yaml"), "w") as f:
                f.write(f"""
name: stack-info
runtime: python
description: Temporary project to get stack information
""")
            
            # Create requirements.txt
            with open(os.path.join(temp_dir, "requirements.txt"), "w") as f:
                f.write("pulumi>=3.0.0\npulumi-aws>=6.0.0\n")
            
            # Install dependencies
            subprocess.run(["pip", "install", "-q", "-r", os.path.join(temp_dir, "requirements.txt")], 
                          capture_output=True, text=True)
            
            # Initialize a new stack
            stack_init_cmd = ["pulumi", "stack", "init", "dev", "--cwd", temp_dir]
            subprocess.run(stack_init_cmd, capture_output=True, text=True)
            
            # Run the program
            up_cmd = ["pulumi", "up", "--yes", "--cwd", temp_dir]
            subprocess.run(up_cmd, capture_output=True, text=True)
            
            # Get the outputs
            output_cmd = ["pulumi", "stack", "output", "--json", "--cwd", temp_dir]
            output_result = subprocess.run(output_cmd, capture_output=True, text=True)
            
            if output_result.returncode == 0:
                return json.loads(output_result.stdout)
            
            return {}
            
        except Exception as e:
            print(f"Error getting stack information with Pulumi: {str(e)}")
            return {}
    
    def check_access(self, stack_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Check if the current IP has access to security groups in the stacks.
        
        Args:
            stack_name: Optional stack name to check (checks all stacks if not specified)
            
        Returns:
            List[Dict[str, Any]]: List of access status for each stack
        """
        # Get current IP
        current_ip = get_local_public_ip()
        if not current_ip:
            print("Could not determine current IP address")
            return []
        
        current_cidr = format_cidr_from_ip(current_ip)
        
        # Get stacks to check
        stacks = self.list_stacks()
        if stack_name:
            stacks = [s for s in stacks if s["name"] == stack_name]
        
        access_status = []
        for stack in stacks:
            # Check if this stack has security group information
            sg_id = stack.get("outputs", {}).get("security_group_id")
            if not sg_id:
                continue
            
            # Get security group rules
            sg_rules = self._get_security_group_rules(stack["name"], sg_id)
            
            # Check if current IP is in the rules
            has_access = False
            authorized_ips = []
            for rule in sg_rules:
                if rule.get("port") == 22:  # SSH port
                    cidr_blocks = rule.get("cidr_blocks", [])
                    authorized_ips.extend(cidr_blocks)
                    if current_cidr in cidr_blocks:
                        has_access = True
            
            access_status.append({
                "stack_name": stack["name"],
                "security_group_id": sg_id,
                "has_access": has_access,
                "current_ip": current_cidr,
                "authorized_ips": authorized_ips
            })
        
        return access_status
    
    def _get_security_group_rules(self, stack_name: str, sg_id: str) -> List[Dict[str, Any]]:
        """
        Get the rules for a security group using Pulumi.
        
        Args:
            stack_name: Name of the stack
            sg_id: Security group ID
            
        Returns:
            List[Dict[str, Any]]: List of security group rules
        """
        # Check if required tools are installed
        if not self._check_pulumi_installed():
            print("Error: Pulumi CLI is not installed or not in PATH")
            return []
            
        try:
            # Create a temporary directory for a Pulumi program to query the security group
            temp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp_sg_query")
            os.makedirs(temp_dir, exist_ok=True)
            
            # Create a temporary Pulumi program to query the security group
            with open(os.path.join(temp_dir, "__main__.py"), "w") as f:
                f.write(f"""
import pulumi
import pulumi_aws as aws
import json

# Use the AWS provider to query the security group
provider = aws.Provider("aws-provider")

# Query the security group
sg_data = aws.ec2.get_security_group(id="{sg_id}", provider=provider)

# Export the security group rules
ingress_rules = []
for rule in sg_data.ingress:
    ingress_rules.append({{
        "protocol": rule.protocol,
        "from_port": rule.from_port,
        "to_port": rule.to_port,
        "cidr_blocks": rule.cidr_blocks
    }})

pulumi.export("ingress_rules", ingress_rules)
""")
            
            # Create Pulumi.yaml
            with open(os.path.join(temp_dir, "Pulumi.yaml"), "w") as f:
                f.write(f"""
name: sg-query
runtime: python
description: Temporary project to query security group
""")
            
            # Create requirements.txt
            with open(os.path.join(temp_dir, "requirements.txt"), "w") as f:
                f.write("pulumi>=3.0.0\npulumi-aws>=6.0.0\n")
            
            # Install dependencies
            subprocess.run(["pip", "install", "-q", "-r", os.path.join(temp_dir, "requirements.txt")], 
                          capture_output=True, text=True)
            
            # Initialize a new stack
            stack_init_cmd = ["pulumi", "stack", "init", "dev", "--cwd", temp_dir]
            subprocess.run(stack_init_cmd, capture_output=True, text=True)
            
            # Run the program
            up_cmd = ["pulumi", "up", "--yes", "--cwd", temp_dir]
            subprocess.run(up_cmd, capture_output=True, text=True)
            
            # Get the outputs
            output_cmd = ["pulumi", "stack", "output", "--json", "--cwd", temp_dir]
            output_result = subprocess.run(output_cmd, capture_output=True, text=True)
            
            if output_result.returncode == 0:
                output_data = json.loads(output_result.stdout)
                ingress_rules = output_data.get("ingress_rules", [])
                
                rules = []
                for rule in ingress_rules:
                    rules.append({
                        "protocol": rule.get("protocol"),
                        "port": rule.get("from_port"),
                        "cidr_blocks": rule.get("cidr_blocks", [])
                    })
                
                return rules
            
            return []
                
        except Exception as e:
            print(f"Error getting security group rules: {str(e)}")
            return []
    
    def update_ip_access(self, stack_name: str) -> bool:
        """
        Update security group rules to allow access from the current IP.
        
        Args:
            stack_name: Name of the stack to update
            
        Returns:
            bool: True if successful, False otherwise
        """
        # Check if required tools are installed
        if not self._check_pulumi_installed():
            print("Error: Pulumi CLI is not installed or not in PATH")
            print("Please install Pulumi CLI: https://www.pulumi.com/docs/install/")
            return False
            
        try:
            # Get current IP
            current_ip = get_local_public_ip()
            if not current_ip:
                print("Could not determine current IP address")
                print("Please check your internet connection")
                return False
            
            current_cidr = format_cidr_from_ip(current_ip)
            
            # Get stack information
            stacks = self.list_stacks()
            if not stacks:
                print("No stacks found or could not access Pulumi stacks")
                print("Make sure you're logged in to Pulumi: run 'pulumi login'")
                return False
                
            target_stack = next((s for s in stacks if s["name"] == stack_name), None)
            if not target_stack:
                print(f"Stack {stack_name} not found")
                if stacks:
                    print(f"Available stacks: {', '.join(s['name'] for s in stacks)}")
                return False
            
            # Get security group ID
            sg_id = target_stack.get("outputs", {}).get("security_group_id")
            if not sg_id:
                print(f"No security group found in stack {stack_name}")
                print("Make sure your stack exports a 'security_group_id' output")
                return False
            
            # Check current access
            access_info = self.check_access(stack_name)
            if not access_info:
                print("Could not check current access status")
                print("Proceeding with update anyway...")
            elif access_info[0].get("has_access"):
                print(f"Current IP {current_cidr} already has access to stack {stack_name}")
                return True
            
            # Create a temporary directory for the Pulumi project
            temp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp_sg_update")
            os.makedirs(temp_dir, exist_ok=True)
            
            # Create a temporary Pulumi program
            with open(os.path.join(temp_dir, "__main__.py"), "w") as f:
                f.write(f"""
import pulumi
import pulumi_aws as aws

# Use the AWS provider to get the security group
provider = aws.Provider("aws-provider")

# Get the existing security group
sg = aws.ec2.SecurityGroup.get("existing-sg", "{sg_id}", provider=provider)

# Add a new ingress rule for the current IP
new_rule = aws.ec2.SecurityGroupRule("new-ssh-rule",
    type="ingress",
    from_port=22,
    to_port=22,
    protocol="tcp",
    cidr_blocks=["{current_cidr}"],
    security_group_id=sg.id,
    description="SSH access from updated IP {current_cidr}",
    provider=provider
)

pulumi.export("updated_sg_id", sg.id)
pulumi.export("new_rule_id", new_rule.id)
""")
            
            # Create Pulumi.yaml
            with open(os.path.join(temp_dir, "Pulumi.yaml"), "w") as f:
                f.write(f"""
name: sg-update
runtime: python
description: Temporary project to update security group
""")
            
            # Create requirements.txt
            with open(os.path.join(temp_dir, "requirements.txt"), "w") as f:
                f.write("pulumi>=3.0.0\npulumi-aws>=6.0.0\n")
            
            # Install dependencies
            print("Installing required Pulumi packages...")
            subprocess.run(["pip", "install", "-q", "-r", os.path.join(temp_dir, "requirements.txt")], 
                          capture_output=True, text=True)
            
            # Initialize a new stack
            print("Initializing Pulumi project...")
            stack_init_cmd = ["pulumi", "stack", "init", "dev", "--cwd", temp_dir]
            init_result = subprocess.run(stack_init_cmd, capture_output=True, text=True)
            
            if init_result.returncode != 0:
                print(f"Failed to initialize Pulumi stack: {init_result.stderr}")
                return False
            
            # Run the update
            print(f"Updating security group {sg_id} to allow access from {current_cidr}...")
            up_cmd = ["pulumi", "up", "--yes", "--cwd", temp_dir]
            up_result = subprocess.run(up_cmd, capture_output=True, text=True)
            
            if up_result.returncode == 0:
                print(f"Successfully updated security group in stack {stack_name} to allow access from {current_cidr}")
                return True
            else:
                print(f"Failed to update security group: {up_result.stderr}")
                print("Make sure you have the necessary permissions to update security groups")
                return False
                
        except Exception as e:
            print(f"Error updating IP access: {str(e)}")
            return False


def list_stacks(project_filter: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    List all Pulumi stacks created with InfraUtilX.
    
    Args:
        project_filter: Optional filter to only include stacks from a specific project
        
    Returns:
        List[Dict[str, Any]]: List of stack information
    """
    manager = StackManager(project_filter)
    return manager.list_stacks()


def check_access(stack_name: Optional[str] = None, project_filter: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Check if the current IP has access to security groups in the stacks.
    
    Args:
        stack_name: Optional stack name to check (checks all stacks if not specified)
        project_filter: Optional filter to only include stacks from a specific project
        
    Returns:
        List[Dict[str, Any]]: List of access status for each stack
    """
    manager = StackManager(project_filter)
    return manager.check_access(stack_name)


def update_ip_access(stack_name: str) -> bool:
    """
    Update security group rules to allow access from the current IP.
    
    Args:
        stack_name: Name of the stack to update
        
    Returns:
        bool: True if successful, False otherwise
    """
    manager = StackManager()
    return manager.update_ip_access(stack_name)