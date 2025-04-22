"""
Error definitions for the Kevo client.

This module contains all custom exceptions used by the Kevo client.
"""

import grpc
from typing import Optional


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


def handle_grpc_error(e: grpc.RpcError, operation: str) -> Exception:
    """Convert a gRPC error to an appropriate Kevo exception.
    
    Args:
        e: The gRPC error
        operation: Description of the operation being performed
        
    Returns:
        An appropriate Kevo exception
    """
    status_code = e.code()
    
    if status_code == grpc.StatusCode.UNAVAILABLE:
        return ConnectionError(f"Server unavailable during {operation}: {e.details()}")
    elif status_code == grpc.StatusCode.NOT_FOUND:
        return KeyNotFoundError(f"Key not found during {operation}")
    elif status_code == grpc.StatusCode.INVALID_ARGUMENT:
        return ValidationError(f"Invalid argument during {operation}: {e.details()}")
    elif status_code == grpc.StatusCode.FAILED_PRECONDITION:
        return TransactionError(f"Transaction error during {operation}: {e.details()}")
    else:
        return KevoError(f"Error during {operation}: {status_code.name} - {e.details()}")