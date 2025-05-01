import pytest
from infrastructure.utils.tags import get_default_tags, merge_tags

def test_get_default_tags():
    """Test getting default tags."""
    # Get default tags
    tags = get_default_tags("test-project", "dev")
    
    # Verify default tags
    assert tags == {
        "Project": "test-project",
        "Environment": "dev",
        "ManagedBy": "InfraUtilX"
    }

def test_get_default_tags_with_different_environment():
    """Test getting default tags with different environment."""
    # Get default tags for production
    tags = get_default_tags("test-project", "prod")
    
    # Verify environment tag
    assert tags["Environment"] == "prod"

def test_merge_tags():
    """Test merging default tags with custom tags."""
    # Get default tags
    default_tags = get_default_tags("test-project", "dev")
    
    # Define custom tags
    custom_tags = {
        "Owner": "test-user",
        "Department": "engineering"
    }
    
    # Merge tags
    merged_tags = merge_tags(default_tags, custom_tags)
    
    # Verify merged tags
    assert merged_tags == {
        "Project": "test-project",
        "Environment": "dev",
        "ManagedBy": "InfraUtilX",
        "Owner": "test-user",
        "Department": "engineering"
    }

def test_merge_tags_with_none():
    """Test merging tags when custom tags is None."""
    # Get default tags
    default_tags = get_default_tags("test-project", "dev")
    
    # Merge with None
    merged_tags = merge_tags(default_tags, None)
    
    # Verify tags remain unchanged
    assert merged_tags == default_tags

def test_merge_tags_with_overlapping_keys():
    """Test merging tags with overlapping keys."""
    # Get default tags
    default_tags = get_default_tags("test-project", "dev")
    
    # Define custom tags with overlapping key
    custom_tags = {
        "Project": "custom-project",
        "Owner": "test-user"
    }
    
    # Merge tags
    merged_tags = merge_tags(default_tags, custom_tags)
    
    # Verify custom value takes precedence
    assert merged_tags["Project"] == "custom-project"
    assert merged_tags["Owner"] == "test-user" 