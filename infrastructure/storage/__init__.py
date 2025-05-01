"""
Storage infrastructure components.
"""

from .ebs import create_ebs_volume, attach_volume, create_snapshot

__all__ = [
    'create_ebs_volume',
    'attach_volume',
    'create_snapshot',
] 