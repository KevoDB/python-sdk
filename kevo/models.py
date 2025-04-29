"""
Data models for the Kevo client.

This module defines data models used throughout the Kevo client,
including KeyValue pairs, batch operations, statistics, and replication info.
"""

import enum
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict, Any


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


class NodeRole(Enum):
    """Role of a node in the replication topology."""

    STANDALONE = "standalone"
    PRIMARY = "primary"
    REPLICA = "replica"


@dataclass
class ReplicaInfo:
    """Information about a replica node."""

    address: str
    last_sequence: int
    available: bool
    region: Optional[str] = None
    meta: Dict[str, str] = field(default_factory=dict)

    def __str__(self) -> str:
        """Return a string representation of the replica info."""
        return (
            f"ReplicaInfo(address={self.address}, "
            f"last_sequence={self.last_sequence}, "
            f"available={self.available}, "
            f"region={self.region})"
        )


@dataclass
class NodeInfo:
    """Information about a node in the replication topology."""

    node_role: NodeRole
    primary_address: str = ""
    replicas: List[ReplicaInfo] = field(default_factory=list)
    last_sequence: int = 0
    read_only: bool = False

    def __str__(self) -> str:
        """Return a string representation of the node info."""
        return (
            f"NodeInfo(node_role={self.node_role.value}, "
            f"primary_address={self.primary_address}, "
            f"replicas_count={len(self.replicas)}, "
            f"last_sequence={self.last_sequence}, "
            f"read_only={self.read_only})"
        )