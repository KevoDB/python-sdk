"""
Scanner implementation for the Kevo client.

This module provides iterator classes for scanning keys in the Kevo database,
both directly and within transactions.
"""

import grpc
from typing import Iterator, Optional

from .connection import Connection
from .errors import handle_grpc_error, ScanError
from .models import KeyValue
from .options import ScanOptions
from .proto.kevo import service_pb2


class Scanner:
    """Base interface for iterating through keys and values."""

    def __iter__(self) -> Iterator[KeyValue]:
        """Make the scanner iterable."""
        return self

    def __next__(self) -> KeyValue:
        """Get the next key-value pair."""
        if not self.next():
            raise StopIteration
        return KeyValue(self.key(), self.value())

    def next(self) -> bool:
        """Advance to the next key-value pair."""
        raise NotImplementedError

    def key(self) -> bytes:
        """Get the current key."""
        raise NotImplementedError

    def value(self) -> bytes:
        """Get the current value."""
        raise NotImplementedError

    def error(self) -> Optional[Exception]:
        """Get any error that occurred during scanning."""
        raise NotImplementedError

    def close(self) -> None:
        """Close the scanner and release resources."""
        raise NotImplementedError


class ScanIterator(Scanner):
    """Iterator for scanning keys in the database."""

    def __init__(self, connection: Connection, options: ScanOptions):
        """
        Initialize a scan iterator.

        Args:
            connection: The connection to use
            options: Scan options
        """
        self._connection = connection
        self._options = options
        self._current = None
        self._error = None
        self._closed = False
        self._iterator = None

        # Create the request
        request = service_pb2.ScanRequest(
            prefix=options.prefix or b"",
            suffix=options.suffix or b"",
            start_key=options.start_key or b"",
            end_key=options.end_key or b"",
            limit=options.limit,
        )

        try:
            # Get the response stream
            self._iterator = self._connection.get_stub().Scan(request)
        except grpc.RpcError as e:
            self._error = handle_grpc_error(e, "starting scan")

    def next(self) -> bool:
        """Advance to the next key-value pair."""
        if self._closed or self._error is not None or self._iterator is None:
            return False

        try:
            response = next(self._iterator)
            self._current = KeyValue(response.key, response.value)
            return True
        except StopIteration:
            return False
        except grpc.RpcError as e:
            self._error = handle_grpc_error(e, "scanning")
            return False

    def key(self) -> bytes:
        """Get the current key."""
        if self._current is None:
            return b""
        return self._current.key

    def value(self) -> bytes:
        """Get the current value."""
        if self._current is None:
            return b""
        return self._current.value

    def error(self) -> Optional[Exception]:
        """Get any error that occurred during scanning."""
        return self._error

    def close(self) -> None:
        """Close the scanner and release resources."""
        self._closed = True
        # The gRPC iterator doesn't need explicit closing


class TransactionScanIterator(Scanner):
    """Iterator for scanning keys in a transaction."""

    def __init__(self, tx_id: str, connection: Connection, options: ScanOptions):
        """
        Initialize a transaction scan iterator.

        Args:
            tx_id: Transaction ID
            connection: The connection to use
            options: Scan options
        """
        self._tx_id = tx_id
        self._connection = connection
        self._options = options
        self._current = None
        self._error = None
        self._closed = False
        self._iterator = None

        # Create the request
        request = service_pb2.TxScanRequest(
            transaction_id=tx_id,
            prefix=options.prefix or b"",
            suffix=options.suffix or b"",
            start_key=options.start_key or b"",
            end_key=options.end_key or b"",
            limit=options.limit,
        )

        try:
            # Get the response stream
            stub = self._connection.get_stub()
            self._iterator = stub.TxScan(request)
        except grpc.RpcError as e:
            self._error = handle_grpc_error(e, "starting transaction scan")

    def next(self) -> bool:
        """Advance to the next key-value pair."""
        if self._closed or self._error is not None or self._iterator is None:
            return False

        try:
            response = next(self._iterator)
            self._current = KeyValue(response.key, response.value)
            return True
        except StopIteration:
            return False
        except grpc.RpcError as e:
            self._error = handle_grpc_error(e, "scanning in transaction")
            return False

    def key(self) -> bytes:
        """Get the current key."""
        if self._current is None:
            return b""
        return self._current.key

    def value(self) -> bytes:
        """Get the current value."""
        if self._current is None:
            return b""
        return self._current.value

    def error(self) -> Optional[Exception]:
        """Get any error that occurred during scanning."""
        return self._error

    def close(self) -> None:
        """Close the scanner and release resources."""
        self._closed = True
        # The gRPC iterator doesn't need explicit closing