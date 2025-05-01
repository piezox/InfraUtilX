import requests
from typing import Optional

def get_local_public_ip() -> Optional[str]:
    """
    Get the public IP address of the local machine.
    
    Returns:
        Optional[str]: The public IP address or None if it can't be determined
    """
    try:
        response = requests.get('https://api.ipify.org')
        return response.text if response.status_code == 200 else None
    except Exception:
        # Try a backup service if the first one fails
        try:
            response = requests.get('https://ifconfig.me')
            return response.text if response.status_code == 200 else None
        except Exception:
            return None

def format_cidr_from_ip(ip: str, suffix: str = "/32") -> str:
    """
    Format an IP address as a CIDR block.
    
    Args:
        ip: The IP address
        suffix: The CIDR suffix (default: /32 for single IP)
        
    Returns:
        str: The formatted CIDR block
    """
    return f"{ip}{suffix}" 