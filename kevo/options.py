"""
Configuration options for the Kevo client.

This module defines configuration options for the Kevo client, including
connection settings, security settings, and performance tuning.
"""

import enum
from dataclasses import dataclass
from typing import Optional


class CompressionType(enum.IntEnum):
    """Compression options for client-server communication."""

    NONE = 0
    GZIP = 1
    SNAPPY = 2


@dataclass
class ClientOptions:
    """Options for configuring a Kevo client."""

    # Connection options
    endpoint: str = "localhost:50051"
    connect_timeout: float = 5.0  # seconds
    request_timeout: float = 10.0  # seconds

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

    # Performance options
    compression: CompressionType = CompressionType.NONE
    max_message_size: int = 16 * 1024 * 1024  # 16MB


class ScanOptions:
    """Options for configuring a scan operation."""

    def __init__(
        self,
        prefix: Optional[bytes] = None,
        suffix: Optional[bytes] = None,
        start_key: Optional[bytes] = None,
        end_key: Optional[bytes] = None,
        limit: int = 0,
    ):
        """
        Initialize scan options.

        Args:
            prefix: Only return keys with this prefix
            suffix: Only return keys with this suffix
            start_key: Start scanning from this key (inclusive)
            end_key: End scanning at this key (exclusive)
            limit: Maximum number of results to return (0 means no limit)
        """
        self.prefix = prefix
        self.suffix = suffix
        self.start_key = start_key
        self.end_key = end_key
        self.limit = limit
        
        # Validate conflicting options
        if prefix is not None and (start_key is not None or end_key is not None):
            raise ValueError("Cannot specify both prefix and start_key/end_key")