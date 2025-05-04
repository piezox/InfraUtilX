"""
AWS Profile Manager

This module provides utilities for managing AWS profiles using Pulumi's
AWS provider system. It helps with listing, validating, and switching
between different AWS profiles configured on the system.
"""

import os
import pulumi
import pulumi_aws as aws
import configparser
import subprocess
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

__all__ = [
    'list_profiles',
    'get_current_profile',
    'switch_profile',
    'validate_profile',
    'refresh_sso_credentials',
    'ProfileInfo'
]

class ProfileInfo:
    """Contains information about an AWS profile."""
    def __init__(self, name: str, region: Optional[str] = None, 
                 is_sso: bool = False, is_default: bool = False,
                 is_active: bool = False, account_id: Optional[str] = None,
                 auth_method: Optional[str] = None, user_identity: Optional[str] = None):
        self.name = name
        self.region = region
        self.is_sso = is_sso
        self.is_default = is_default
        self.is_active = is_active
        self.account_id = account_id
        self.auth_method = auth_method  # "api_key", "sso", "role", etc.
        self.user_identity = user_identity  # IAM user/role name
    
    def __str__(self) -> str:
        """Return string representation of the profile info."""
        status = []
        if self.is_active:
            status.append("ACTIVE")
        if self.is_default:
            status.append("DEFAULT")
        if self.is_sso:
            status.append("SSO")
        
        status_str = f" ({', '.join(status)})" if status else ""
        region_str = f" - {self.region}" if self.region else ""
        account_str = f" - Account: {self.account_id}" if self.account_id else ""
        
        identity_info = []
        if self.auth_method:
            identity_info.append(self.auth_method)
        if self.user_identity:
            identity_info.append(self.user_identity)
        
        identity_str = f" [{', '.join(identity_info)}]" if identity_info else ""
        
        return f"{self.name}{region_str}{account_str}{identity_str}{status_str}"

def _get_aws_config_path() -> Path:
    """Get the path to the AWS config file."""
    aws_dir = Path.home() / ".aws"
    return aws_dir / "config"

def _get_aws_credentials_path() -> Path:
    """Get the path to the AWS credentials file."""
    aws_dir = Path.home() / ".aws"
    return aws_dir / "credentials"

def _get_aws_sso_cache_dir() -> Path:
    """Get the path to the AWS SSO cache directory."""
    aws_dir = Path.home() / ".aws"
    return aws_dir / "sso" / "cache"

def _get_account_id_from_sts(profile_name: Optional[str] = None) -> Optional[str]:
    """
    Get AWS account ID from STS for a profile.
    
    Args:
        profile_name: AWS profile name or None for default
        
    Returns:
        AWS account ID or None if it can't be retrieved
    """
    try:
        cmd = ["aws", "sts", "get-caller-identity", "--output", "json"]
        if profile_name:
            cmd.extend(["--profile", profile_name])
            
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            identity = json.loads(result.stdout)
            return identity.get("Account")
    except (subprocess.SubprocessError, json.JSONDecodeError, Exception):
        pass
    
    return None

def _get_account_id_from_sso_cache(profile_name: str, config: configparser.ConfigParser) -> Optional[str]:
    """
    Get AWS account ID from SSO cache for a profile.
    
    Args:
        profile_name: AWS profile name
        config: Parsed AWS config
        
    Returns:
        AWS account ID or None if it can't be retrieved
    """
    # Get the SSO session name and account ID from the profile
    section = f"profile {profile_name}" if profile_name != "default" else "default"
    if section not in config:
        return None
    
    profile_section = config[section]
    
    # If the profile has a direct account ID, use that
    sso_account_id = profile_section.get("sso_account_id")
    if sso_account_id:
        return sso_account_id
    
    # Otherwise, try to find from SSO cache
    sso_session = profile_section.get("sso_session")
    if not sso_session:
        return None
    
    # Check SSO cache files for this session
    cache_dir = _get_aws_sso_cache_dir()
    if not cache_dir.exists():
        return None
    
    # Attempt to find account ID in cache files
    for cache_file in cache_dir.glob("*.json"):
        try:
            with open(cache_file, 'r') as f:
                cache_data = json.load(f)
                if 'accountId' in cache_data:
                    return cache_data['accountId']
        except (json.JSONDecodeError, IOError):
            continue
    
    return None

def list_profiles(fetch_all_account_ids: bool = True) -> List[ProfileInfo]:
    """
    List all AWS profiles configured on the system.
    
    Args:
        fetch_all_account_ids: Whether to fetch account IDs for all profiles (can be slow)
    
    Returns:
        List of ProfileInfo objects representing each AWS profile
    """
    profiles = []
    current_profile = get_current_profile()
    
    # Read from config file
    config_path = _get_aws_config_path()
    if config_path.exists():
        config = configparser.ConfigParser()
        config.read(config_path)
        
        for section in config.sections():
            # Process profile sections
            if section == "default":
                name = "default"
                is_default = True
            elif section.startswith("profile "):
                name = section[8:]  # Remove "profile " prefix
                is_default = False
            else:
                # Skip non-profile sections like sso-session
                if section.startswith("sso-session"):
                    continue
                name = section
                is_default = False
            
            # Get region and check if it's an SSO profile
            region = config.get(section, "region", fallback=None)
            is_sso = (config.has_option(section, "sso_start_url") or 
                      config.has_option(section, "sso_session"))
            
            # Check if profile is active
            is_active = (current_profile == name)
            
            # Try to get account ID from SSO config if it's an SSO profile
            account_id = None
            if is_sso:
                account_id = _get_account_id_from_sso_cache(name, config)
            
            # Get auth method and identity info from config
            auth_method = "sso" if is_sso else None
            user_identity = None
            
            # Try to get user identity from config for SSO profiles
            if is_sso and section in config:
                if config.has_option(section, "sso_role_name"):
                    user_identity = config.get(section, "sso_role_name")
            
            # If it's a role assumption profile, get the role info
            if section in config and config.has_option(section, "role_arn"):
                auth_method = "role"
                role_arn = config.get(section, "role_arn")
                parts = role_arn.split("/")
                if len(parts) >= 2:
                    user_identity = parts[1]
            
            # If we couldn't get the account ID and we should fetch all account IDs
            # or it's the active profile, try STS
            if account_id is None and (fetch_all_account_ids or is_active or name == current_profile):
                try:
                    account_id = _get_account_id_from_sts(name)
                    # Also get identity info if we're making the API call anyway
                    if auth_method is None or user_identity is None:
                        auth_method_sts, user_identity_sts = _get_identity_info(name)
                        if auth_method is None:
                            auth_method = auth_method_sts
                        if user_identity is None:
                            user_identity = user_identity_sts
                except Exception:
                    pass
            
            # For static credential profiles, check if they're in the credentials file
            if not auth_method and not is_sso:
                creds_path = _get_aws_credentials_path()
                if creds_path.exists():
                    creds = configparser.ConfigParser()
                    creds.read(creds_path)
                    if name in creds:
                        if creds.has_option(name, "aws_access_key_id"):
                            auth_method = "api_key"
                        elif creds.has_option(name, "credential_process"):
                            auth_method = "external"
            
            profiles.append(ProfileInfo(
                name=name,
                region=region,
                is_sso=is_sso,
                is_default=is_default,
                is_active=is_active,
                account_id=account_id,
                auth_method=auth_method,
                user_identity=user_identity
            ))
    
    # Also check credentials file for profiles not in config
    creds_path = _get_aws_credentials_path()
    if creds_path.exists():
        creds = configparser.ConfigParser()
        creds.read(creds_path)
        
        for section in creds.sections():
            # Skip profiles we already found in config file
            if any(p.name == section for p in profiles):
                continue
            
            is_default = (section == "default")
            is_active = (current_profile == section)
            
            # Determine auth method from the credentials file
            auth_method = None
            if creds.has_option(section, "aws_access_key_id"):
                auth_method = "api_key"
            elif creds.has_option(section, "credential_process"):
                auth_method = "external"
            
            # Try to get account ID and identity if we should fetch all account IDs or it's the active profile
            account_id = None
            user_identity = None
            if fetch_all_account_ids or is_active:
                try:
                    account_id = _get_account_id_from_sts(section)
                    # Also get identity info
                    auth_method_sts, user_identity = _get_identity_info(section)
                    if auth_method is None:
                        auth_method = auth_method_sts
                except Exception:
                    pass
            
            profiles.append(ProfileInfo(
                name=section,
                is_default=is_default,
                is_active=is_active,
                account_id=account_id,
                auth_method=auth_method,
                user_identity=user_identity
            ))
    
    return profiles

def get_current_profile() -> Optional[str]:
    """
    Get the name of the currently active AWS profile.
    
    Returns:
        Name of the active profile or None if using default credentials
    """
    # Check AWS_PROFILE environment variable
    profile = os.environ.get("AWS_PROFILE")
    if profile:
        return profile
    
    # Check if AWS_DEFAULT_PROFILE is set
    profile = os.environ.get("AWS_DEFAULT_PROFILE")
    if profile:
        return profile
    
    # If no profile is explicitly set, it's using the default
    return None

def switch_profile(profile_name: str) -> bool:
    """
    Switch to a different AWS profile.
    
    Args:
        profile_name: Name of the profile to switch to
        
    Returns:
        True if switch was successful, False otherwise
    """
    # Check if profile exists
    profiles = list_profiles()
    if not any(p.name == profile_name for p in profiles):
        return False
    
    # Set AWS_PROFILE for the current process
    os.environ["AWS_PROFILE"] = profile_name
    
    # Provide command to set AWS_PROFILE in the shell
    print(f"Profile switching command: export AWS_PROFILE={profile_name}")
    
    return True

def validate_profile(profile_name: Optional[str] = None) -> Tuple[bool, str]:
    """
    Validate AWS credentials for a profile.
    
    Args:
        profile_name: Name of the profile to validate (uses current if None)
        
    Returns:
        Tuple of (success, message)
    """
    original_profile = get_current_profile()
    
    # If profile is specified, temporarily switch to it
    if profile_name and profile_name != original_profile:
        if not switch_profile(profile_name):
            return False, f"Profile '{profile_name}' not found"
    
    # Validate credentials
    try:
        # Create a Pulumi AWS provider with the current credentials
        # This actually validates the credentials
        provider = aws.Provider("validator", profile=profile_name)
        
        # Reset to original profile if we switched
        if profile_name and profile_name != original_profile:
            switch_profile(original_profile)
            
        return True, "Credentials are valid"
    
    except Exception as e:
        # Reset to original profile if we switched
        if profile_name and profile_name != original_profile:
            switch_profile(original_profile)
            
        return False, f"Credential validation failed: {str(e)}"

def refresh_sso_credentials(profile_name: str) -> Tuple[bool, str]:
    """
    Refresh SSO credentials for a profile.
    
    Args:
        profile_name: Name of the SSO profile to refresh
        
    Returns:
        Tuple of (success, message)
    """
    # Check if profile exists and is an SSO profile
    profiles = list_profiles()
    profile = next((p for p in profiles if p.name == profile_name), None)
    
    if not profile:
        return False, f"Profile '{profile_name}' not found"
    
    if not profile.is_sso:
        return False, f"Profile '{profile_name}' is not an SSO profile"
    
    # Run AWS SSO login command
    try:
        cmd = ["aws", "sso", "login", "--profile", profile_name]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            return True, "SSO login successful"
        else:
            return False, f"SSO login failed: {result.stderr.strip()}"
    
    except Exception as e:
        return False, f"SSO login failed: {str(e)}"

def _get_identity_info(profile_name: Optional[str] = None) -> Tuple[Optional[str], Optional[str]]:
    """
    Get authentication method and identity info for a profile.
    
    Args:
        profile_name: AWS profile name or None for default
        
    Returns:
        Tuple of (auth_method, user_identity)
    """
    auth_method = None
    user_identity = None
    
    try:
        # Run AWS STS get-caller-identity to get user info
        cmd = ["aws", "sts", "get-caller-identity", "--output", "json"]
        if profile_name:
            cmd.extend(["--profile", profile_name])
            
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            identity = json.loads(result.stdout)
            
            # Extract the identity information
            arn = identity.get("Arn", "")
            if "assumed-role" in arn:
                auth_method = "role"
                # Format: arn:aws:sts::ACCOUNT:assumed-role/ROLE/SESSION
                parts = arn.split("/")
                if len(parts) >= 2:
                    user_identity = parts[1]
            elif ":user/" in arn:
                auth_method = "api_key"
                # Format: arn:aws:iam::ACCOUNT:user/USERNAME
                parts = arn.split("/")
                if len(parts) >= 2:
                    user_identity = parts[1]
            elif ":federated-user/" in arn:
                auth_method = "federated"
                parts = arn.split("/")
                if len(parts) >= 2:
                    user_identity = parts[1]
    except (subprocess.SubprocessError, json.JSONDecodeError, Exception):
        pass
    
    # If we still couldn't determine the auth method but it's an SSO profile
    if not auth_method and profile_name:
        # Check if it's an SSO profile in config
        config_path = _get_aws_config_path()
        if config_path.exists():
            config = configparser.ConfigParser()
            config.read(config_path)
            
            section = f"profile {profile_name}" if profile_name != "default" else "default"
            if section in config:
                if config.has_option(section, "sso_start_url") or config.has_option(section, "sso_session"):
                    auth_method = "sso"
                    
                    # Try to get the role name from the config
                    if config.has_option(section, "sso_role_name"):
                        user_identity = config.get(section, "sso_role_name")
                elif config.has_option(section, "role_arn"):
                    auth_method = "role"
                    # Format: arn:aws:iam::ACCOUNT:role/ROLE
                    role_arn = config.get(section, "role_arn")
                    parts = role_arn.split("/")
                    if len(parts) >= 2:
                        user_identity = parts[1]
    
    return auth_method, user_identity 