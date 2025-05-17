"""
Configuration options for the Kevo client.

This module defines configuration options for the Kevo client, including
connection settings, security settings, performance tuning, and replication.
"""

import enum
import random
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Union


class CompressionType(enum.IntEnum):
    """Compression options for client-server communication."""

    NONE = 0
    GZIP = 1
    SNAPPY = 2


@dataclass
class ReplicationOptions:
    """Options for configuring replication behavior."""
    
    # Topology discovery
    discover_topology: bool = True
    
    # Read/write routing
    auto_route_writes: bool = True
    auto_route_reads: bool = True
    
    # Read preferences
    read_from_replicas: bool = True
    
    # Replica selection strategy: "random", "sequential", "round_robin"
    replica_selection_strategy: str = "random"
    
    # Connection management
    auto_connect_to_replicas: bool = True
    auto_connect_to_primary: bool = True
    
    # Retry settings for replication operations
    replica_retry_count: int = 2


@dataclass
class ReadOptions:
    """Options for read operations."""
    
    # Whether to use replica for this read
    read_from_replicas: bool = True
    
    # Consistency requirements
    require_max_staleness_ms: Optional[int] = None
    
    # Timeout specific to this read
    timeout: Optional[float] = None


@dataclass
class WriteOptions:
    """Options for write operations."""
    
    # Whether to sync to disk
    sync: bool = False
    
    # Timeout specific to this write
    timeout: Optional[float] = None


@dataclass
class ClientOptions:
    """Options for configuring a Kevo client."""

    # Connection options
    endpoint: str = "localhost:50051"
    connect_timeout: float = 10.0  # seconds
    request_timeout: float = 30.0  # seconds

    # Security options
    tls_enabled: bool = False
    cert_file: Optional[str] = None
    key_file: Optional[str] = None
    ca_file: Optional[str] = None

    # Retry options
    max_retries: int = 3
    initial_backoff: float = 0.1  # seconds
    max_backoff: float = 2.0  # seconds
    backoff_factor: float = 1.5
    retry_jitter: float = 0.2
    
    # Auto-reconnection options
    auto_reconnect: bool = True
    reconnect_max_attempts: int = 5
    reconnect_backoff_factor: float = 2.0
    reconnect_initial_delay: float = 1.0  # seconds
    reconnect_max_delay: float = 30.0  # seconds

    # Performance options
    compression: CompressionType = CompressionType.NONE
    max_message_size: int = 16 * 1024 * 1024  # 16MB
    
    # Replication options
    replication: ReplicationOptions = field(default_factory=ReplicationOptions)


class ScanOptions:
    """Options for configuring a scan operation."""

    def __init__(
        self,
        prefix: Optional[bytes] = None,
        suffix: Optional[bytes] = None,
        start_key: Optional[bytes] = None,
        end_key: Optional[bytes] = None,
        limit: int = 0,
        read_from_replicas: bool = True,
    ):
        """
        Initialize scan options.

        Args:
            prefix: Only return keys with this prefix
            suffix: Only return keys with this suffix
            start_key: Start scanning from this key (inclusive)
            end_key: End scanning at this key (exclusive)
            limit: Maximum number of results to return (0 means no limit)
            read_from_replicas: Whether to read from replicas for this scan operation
        """
        self.prefix = prefix
        self.suffix = suffix
        self.start_key = start_key
        self.end_key = end_key
        self.limit = limit
        self.read_from_replicas = read_from_replicas
        
        # Validate conflicting options
        if prefix is not None and (start_key is not None or end_key is not None):
            raise ValueError("Cannot specify both prefix and start_key/end_key")