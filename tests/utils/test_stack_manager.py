"""
Tests for the stack manager utility.
"""

import pytest
import json
from unittest.mock import patch, MagicMock, mock_open
from infrastructure.utils.stack_manager import (
    StackManager, 
    list_stacks, 
    check_access, 
    update_ip_access
)

# Sample data for tests
SAMPLE_STACKS_OUTPUT = """
[
  {
    "name": "dev/test-stack",
    "projectName": "infrautilx-example",
    "lastUpdate": "2023-05-15T10:30:00Z",
    "resourceCount": 10
  },
  {
    "name": "dev/another-stack",
    "projectName": "another-project",
    "lastUpdate": "2023-05-16T11:45:00Z",
    "resourceCount": 5
  }
]
"""

SAMPLE_STACK_OUTPUTS = """
{
  "vpc_id": "vpc-12345",
  "subnet_id": "subnet-12345",
  "security_group_id": "sg-12345",
  "instance_id": "i-12345",
  "public_ip": "203.0.113.10"
}
"""

SAMPLE_SG_RULES = """
{
  "SecurityGroups": [
    {
      "GroupId": "sg-12345",
      "GroupName": "test-sg",
      "IpPermissions": [
        {
          "FromPort": 22,
          "ToPort": 22,
          "IpProtocol": "tcp",
          "IpRanges": [
            {
              "CidrIp": "198.51.100.0/32",
              "Description": "SSH access from old IP"
            }
          ]
        },
        {
          "FromPort": 80,
          "ToPort": 80,
          "IpProtocol": "tcp",
          "IpRanges": [
            {
              "CidrIp": "0.0.0.0/0",
              "Description": "HTTP access"
            }
          ]
        }
      ]
    }
  ]
}
"""

@pytest.fixture
def mock_subprocess():
    """Mock subprocess.run for testing."""
    with patch('subprocess.run') as mock_run:
        # Configure the mock to return appropriate values
        def side_effect(*args, **kwargs):
            cmd = args[0] if args else kwargs.get('cmd', [])
            
            # Mock stack list command
            if 'stack' in cmd and 'ls' in cmd:
                mock_result = MagicMock()
                mock_result.stdout = SAMPLE_STACKS_OUTPUT
                mock_result.returncode = 0
                return mock_result
                
            # Mock stack output command
            elif 'stack' in cmd and 'output' in cmd:
                mock_result = MagicMock()
                mock_result.stdout = SAMPLE_STACK_OUTPUTS
                mock_result.returncode = 0
                return mock_result
                
            # Mock security group describe command
            elif 'describe-security-groups' in cmd:
                mock_result = MagicMock()
                mock_result.stdout = SAMPLE_SG_RULES
                mock_result.returncode = 0
                return mock_result
                
            # Mock pulumi up command
            elif 'up' in cmd:
                mock_result = MagicMock()
                mock_result.returncode = 0
                return mock_result
                
            # Default mock response
            mock_result = MagicMock()
            mock_result.returncode = 0
            return mock_result
            
        mock_run.side_effect = side_effect
        yield mock_run

@pytest.fixture
def mock_get_ip():
    """Mock get_local_public_ip function."""
    with patch('infrastructure.utils.ip.get_local_public_ip') as mock_ip:
        mock_ip.return_value = "203.0.113.42"
        yield mock_ip

@pytest.fixture
def mock_os_makedirs():
    """Mock os.makedirs function."""
    with patch('os.makedirs') as mock_makedirs:
        yield mock_makedirs

@pytest.fixture
def mock_open_file():
    """Mock open function for file operations."""
    with patch('builtins.open', mock_open()) as mock_file:
        yield mock_file

def test_list_stacks(mock_subprocess):
    """Test listing stacks."""
    # Call the function
    stacks = list_stacks()
    
    # Verify results
    assert len(stacks) == 2
    assert stacks[0]["name"] == "dev/test-stack"
    assert stacks[0]["project"] == "infrautilx-example"
    assert stacks[1]["name"] == "dev/another-stack"
    assert stacks[1]["project"] == "another-project"
    
    # Verify subprocess was called correctly
    mock_subprocess.assert_any_call(
        ["pulumi", "stack", "ls", "--json"], 
        capture_output=True, 
        text=True, 
        check=True
    )

def test_list_stacks_with_filter(mock_subprocess):
    """Test listing stacks with project filter."""
    # Call the function with filter
    stacks = list_stacks("infrautilx")
    
    # Verify results
    assert len(stacks) == 1
    assert stacks[0]["name"] == "dev/test-stack"
    assert stacks[0]["project"] == "infrautilx-example"

def test_check_access(mock_subprocess, mock_get_ip):
    """Test checking access status."""
    # Call the function
    access_info = check_access()
    
    # Verify results
    assert len(access_info) == 2
    assert access_info[0]["stack_name"] == "dev/test-stack"
    assert access_info[0]["security_group_id"] == "sg-12345"
    assert access_info[0]["has_access"] is False
    assert access_info[0]["current_ip"] == "203.0.113.42/32"
    
    # Verify IP function was called
    mock_get_ip.assert_called_once()

def test_check_access_specific_stack(mock_subprocess, mock_get_ip):
    """Test checking access for a specific stack."""
    # Call the function with stack name
    access_info = check_access("dev/test-stack")
    
    # Verify results
    assert len(access_info) == 1
    assert access_info[0]["stack_name"] == "dev/test-stack"

def test_update_ip_access(mock_subprocess, mock_get_ip, mock_os_makedirs, mock_open_file):
    """Test updating IP access."""
    # Call the function
    result = update_ip_access("dev/test-stack")
    
    # Verify results
    assert result is True
    
    # Verify subprocess calls
    mock_subprocess.assert_any_call(
        ["pulumi", "up", "--yes", "--cwd"], 
        capture_output=True, 
        text=True
    )
    
    # Verify file operations
    mock_open_file.assert_called()
    
    # Verify IP function was called
    mock_get_ip.assert_called()

def test_stack_manager_init():
    """Test StackManager initialization."""
    # Create manager with filter
    manager = StackManager("test-filter")
    
    # Verify attributes
    assert manager.project_filter == "test-filter"
    
    # Create manager without filter
    manager = StackManager()
    
    # Verify attributes
    assert manager.project_filter is None

def test_get_security_group_rules(mock_subprocess):
    """Test getting security group rules."""
    # Create manager
    manager = StackManager()
    
    # Call the method
    rules = manager._get_security_group_rules("dev/test-stack", "sg-12345")
    
    # Verify results
    assert len(rules) == 2
    assert rules[0]["port"] == 22
    assert rules[0]["protocol"] == "tcp"
    assert rules[0]["cidr_blocks"] == ["198.51.100.0/32"]
    assert rules[1]["port"] == 80