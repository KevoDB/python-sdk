"""
Data models for the Kevo client.

This module defines data models used throughout the Kevo client,
including KeyValue pairs, batch operations, and statistics.
"""

import enum
from dataclasses import dataclass
from enum import Enum
from typing import Optional


@dataclass
class KeyValue:
    """A key-value pair returned from a scan operation."""
    
    key: bytes
    value: bytes


@dataclass
class Stats:
    """Database statistics."""

    key_count: int
    storage_size: int
    memtable_count: int
    sstable_count: int
    write_amplification: float
    read_amplification: float
    
    def __str__(self) -> str:
        """Return a string representation of the stats."""
        return (
            f"Stats(key_count={self.key_count}, "
            f"storage_size={self.storage_size}, "
            f"memtable_count={self.memtable_count}, "
            f"sstable_count={self.sstable_count}, "
            f"write_amplification={self.write_amplification:.2f}, "
            f"read_amplification={self.read_amplification:.2f})"
        )


class BatchOperation:
    """Represents a single operation in a batch write."""

    class Type(Enum):
        """Type of batch operation."""

        PUT = "put"
        DELETE = "delete"

    def __init__(self, op_type: Type, key: bytes, value: Optional[bytes] = None):
        """
        Initialize a batch operation.

        Args:
            op_type: Type of operation (PUT or DELETE)
            key: The key to operate on
            value: The value to store (only for PUT operations)
        """
        self.type = op_type
        self.key = key
        self.value = value

        # Validate
        if op_type == BatchOperation.Type.PUT and value is None:
            raise ValueError("Value must be provided for PUT operations")