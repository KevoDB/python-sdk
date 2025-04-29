"""
Kevo Python SDK - Client for the Kevo key-value store

This package provides a Pythonic interface to interact with a Kevo server,
including support for replication.
"""

__version__ = "0.3.0"
__author__ = "Kevo Team"
__email__ = "info@example.com"

from .client import Client
from .models import KeyValue, Stats, BatchOperation, NodeInfo, ReplicaInfo, NodeRole
from .options import (
    ClientOptions, 
    ScanOptions, 
    CompressionType, 
    ReplicationOptions,
    ReadOptions,
    WriteOptions
)
from .scanner import Scanner
from .transaction import Transaction
from .errors import (
    KevoError,
    ConnectionError, 
    TransactionError,
    KeyNotFoundError,
    ScanError,
    ValidationError,
    ReplicationError,
    ReadOnlyError,
    ReplicaReadError,
)

__all__ = [
    # Core client
    "Client",
    
    # Configuration
    "ClientOptions",
    "ScanOptions",
    "CompressionType",
    "ReplicationOptions",
    "ReadOptions",
    "WriteOptions",
    
    # Data models
    "KeyValue",
    "Stats",
    "BatchOperation",
    "NodeInfo",
    "ReplicaInfo",
    "NodeRole",
    
    # Iterators
    "Scanner",
    
    # Transactions
    "Transaction",
    
    # Error types
    "KevoError",
    "ConnectionError",
    "TransactionError",
    "KeyNotFoundError",
    "ScanError",
    "ValidationError",
    "ReplicationError",
    "ReadOnlyError",
    "ReplicaReadError",
]
