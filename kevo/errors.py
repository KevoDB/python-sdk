"""
Error definitions for the Kevo client.

This module contains all custom exceptions used by the Kevo client.
"""

import re
import grpc
from typing import Optional, Tuple


class KevoError(Exception):
    """Base exception class for all Kevo client errors."""
    pass


class ConnectionError(KevoError):
    """Error when connecting to the Kevo server."""
    pass


class TransactionError(KevoError):
    """Error during transaction operations."""
    pass


class KeyNotFoundError(KevoError):
    """Error when a key doesn't exist."""
    pass


class ScanError(KevoError):
    """Error during a scan operation."""
    pass


class ValidationError(KevoError):
    """Error when input validation fails."""
    pass


class ReplicaReadError(KevoError):
    """Error when reading from a replica."""
    pass


class ReplicationError(KevoError):
    """General error related to replication operations."""
    pass


class ReadOnlyError(KevoError):
    """Error when trying to write to a read-only node."""
    
    def __init__(self, message: str, primary_address: Optional[str] = None):
        """
        Initialize a read-only error.
        
        Args:
            message: The error message
            primary_address: The address of the primary node to redirect to
        """
        super().__init__(message)
        self.primary_address = primary_address


# Regular expression to extract primary address from read-only error message
PRIMARY_ADDRESS_PATTERN = re.compile(r'primary node at (\S+)')


def parse_primary_address(error_message: str) -> Optional[str]:
    """
    Extract primary address from an error message.
    
    Args:
        error_message: The error message to parse
        
    Returns:
        The primary address if found, None otherwise
    """
    match = PRIMARY_ADDRESS_PATTERN.search(error_message)
    if match:
        return match.group(1)
    return None


def handle_grpc_error(e: grpc.RpcError, operation: str) -> Exception:
    """Convert a gRPC error to an appropriate Kevo exception.
    
    Args:
        e: The gRPC error
        operation: Description of the operation being performed
        
    Returns:
        An appropriate Kevo exception
    """
    status_code = e.code()
    details = e.details()
    
    if status_code == grpc.StatusCode.UNAVAILABLE:
        return ConnectionError(f"Server unavailable during {operation}: {details}")
    elif status_code == grpc.StatusCode.NOT_FOUND:
        return KeyNotFoundError(f"Key not found during {operation}")
    elif status_code == grpc.StatusCode.INVALID_ARGUMENT:
        return ValidationError(f"Invalid argument during {operation}: {details}")
    elif status_code == grpc.StatusCode.FAILED_PRECONDITION:
        # Check if this is a read-only error (replica node)
        if "replica" in details and "primary node at" in details:
            primary_address = parse_primary_address(details)
            return ReadOnlyError(
                f"Read-only error during {operation}: {details}", 
                primary_address=primary_address
            )
        else:
            return TransactionError(f"Transaction error during {operation}: {details}")
    else:
        return KevoError(f"Error during {operation}: {status_code.name} - {details}")