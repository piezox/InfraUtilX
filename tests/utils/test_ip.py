import pytest
from unittest.mock import patch, MagicMock
from infrastructure.utils.ip import get_local_public_ip, format_cidr_from_ip

def test_format_cidr_from_ip():
    """Test formatting IP address as CIDR block."""
    # Test with default suffix
    assert format_cidr_from_ip("192.168.1.1") == "192.168.1.1/32"
    
    # Test with custom suffix
    assert format_cidr_from_ip("192.168.1.0", "/24") == "192.168.1.0/24"
    assert format_cidr_from_ip("10.0.0.0", "/16") == "10.0.0.0/16"

@patch('infrastructure.utils.ip.requests.get')
def test_get_local_public_ip_success(mock_get):
    """Test getting local public IP successfully."""
    # Mock successful response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = "203.0.113.10"
    mock_get.return_value = mock_response
    
    # Test function
    ip = get_local_public_ip()
    
    # Assertions
    assert ip == "203.0.113.10"
    mock_get.assert_called_once_with('https://api.ipify.org')

@patch('infrastructure.utils.ip.requests.get')
def test_get_local_public_ip_primary_failure_backup_success(mock_get):
    """Test falling back to backup IP service."""
    # Mock responses
    def side_effect(url):
        if url == 'https://api.ipify.org':
            # Primary service fails
            raise Exception("Connection error")
        elif url == 'https://ifconfig.me':
            # Backup service succeeds
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = "203.0.113.10"
            return mock_response
    
    mock_get.side_effect = side_effect
    
    # Test function
    ip = get_local_public_ip()
    
    # Assertions
    assert ip == "203.0.113.10"
    assert mock_get.call_count == 2

@patch('infrastructure.utils.ip.requests.get')
def test_get_local_public_ip_all_failures(mock_get):
    """Test when all IP services fail."""
    # Mock failures for all services
    mock_get.side_effect = Exception("Connection error")
    
    # Test function
    ip = get_local_public_ip()
    
    # Assertions
    assert ip is None
    assert mock_get.call_count == 2 