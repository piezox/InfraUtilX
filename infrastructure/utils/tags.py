from typing import Dict, Optional

def get_default_tags(project: str, environment: str = "dev") -> Dict[str, str]:
    """
    Get default tags for AWS resources.
    
    Args:
        project: Name of the project
        environment: Environment name (dev, prod, etc.)
    
    Returns:
        Dict[str, str]: Dictionary of default tags
    """
    return {
        "Project": project,
        "Environment": environment,
        "ManagedBy": "InfraUtilX",
    }

def merge_tags(default_tags: Optional[Dict[str, str]] = None, custom_tags: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """
    Merge default tags with custom tags.
    
    Args:
        default_tags: Default tags dictionary
        custom_tags: Optional custom tags dictionary
    
    Returns:
        Dict[str, str]: Merged tags dictionary
    """
    result = {}
    
    # Add default tags if provided
    if default_tags:
        result.update(default_tags)
    
    # Add custom tags if provided
    if custom_tags:
        result.update(custom_tags)
    
    return result 