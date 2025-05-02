"""
Shared test fixtures and configuration.
"""

import pytest
import pulumi
import os
import sys

# Add the parent directory to the path so we can import the infrastructure package
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock Pulumi engine
class MockPulumiEngine:
    """Mock Pulumi engine for testing."""
    
    def __init__(self):
        self.outputs = {}
    
    def mock_output(self, name, value):
        """Mock a Pulumi output."""
        self.outputs[name] = pulumi.Output.from_input(value)
        
    def get_output(self, name):
        """Get a mocked Pulumi output."""
        return self.outputs.get(name)

@pytest.fixture
def mock_pulumi():
    """Fixture to mock Pulumi engine."""
    return MockPulumiEngine()