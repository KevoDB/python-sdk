"""
Kevo Python SDK - Client for the Kevo key-value store

This package provides a Pythonic interface to interact with a Kevo server.
"""

__version__ = "0.2.0"
__author__ = "Kevo Team"
__email__ = "info@example.com"

from .client import Client
from .models import KeyValue, Stats, BatchOperation
from .options import ClientOptions, ScanOptions, CompressionType
from .scanner import Scanner
from .transaction import Transaction
from .errors import (
    KevoError,
    ConnectionError, 
    TransactionError,
    KeyNotFoundError,
    ScanError,
    ValidationError,
)

__all__ = [
    # Core client
    "Client",
    
    # Configuration
    "ClientOptions",
    "ScanOptions",
    "CompressionType",
    
    # Data models
    "KeyValue",
    "Stats",
    "BatchOperation",
    
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
]
