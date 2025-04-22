"""
Client implementation for Kevo key-value store.

This module provides the main client interface for connecting to and
interacting with a Kevo server.
"""

import grpc
from typing import List, Optional, Tuple, Iterator

from .connection import Connection
from .errors import handle_grpc_error, ConnectionError, ValidationError
from .models import KeyValue, Stats, BatchOperation
from .options import ClientOptions, ScanOptions
from .proto.kevo import service_pb2
from .scanner import Scanner, ScanIterator
from .transaction import Transaction


class Client:
    """Client for connecting to and interacting with a Kevo server."""

    def __init__(self, options: Optional[ClientOptions] = None):
        """
        Initialize a Kevo client.

        Args:
            options: Client configuration options
        """
        self._options = options or ClientOptions()
        self._connection = Connection(self._options)

    def connect(self) -> None:
        """
        Connect to the server.

        Raises:
            ConnectionError: If the connection fails
        """
        self._connection.connect()

    def close(self) -> None:
        """Close the connection to the server."""
        self._connection.close()

    def is_connected(self) -> bool:
        """Check if the client is connected to the server."""
        return self._connection.is_connected()

    def get(self, key: bytes) -> Tuple[Optional[bytes], bool]:
        """
        Get a value by key.

        Args:
            key: The key to get

        Returns:
            A tuple of (value, found) where found is True if the key exists

        Raises:
            ConnectionError: If the client is not connected or the request fails
            ValidationError: If the key is invalid
        """
        # Input validation
        if not isinstance(key, bytes):
            raise ValidationError("Key must be bytes")
        if not key:
            raise ValidationError("Key cannot be empty")

        request = service_pb2.GetRequest(key=key)

        try:
            stub = self._connection.get_stub()
            response = stub.Get(request, timeout=self._connection.get_timeout())
            return (response.value, response.found)
        except grpc.RpcError as e:
            raise handle_grpc_error(e, "getting key")

    def put(self, key: bytes, value: bytes, sync: bool = False) -> bool:
        """
        Put a key-value pair.

        Args:
            key: The key to put
            value: The value to put
            sync: Whether to sync to disk before returning

        Returns:
            True if the operation succeeded

        Raises:
            ConnectionError: If the client is not connected or the request fails
            ValidationError: If the key or value is invalid
        """
        # Input validation
        if not isinstance(key, bytes):
            raise ValidationError("Key must be bytes")
        if not key:
            raise ValidationError("Key cannot be empty")
        if not isinstance(value, bytes):
            raise ValidationError("Value must be bytes")

        request = service_pb2.PutRequest(key=key, value=value, sync=sync)

        try:
            stub = self._connection.get_stub()
            response = stub.Put(request, timeout=self._connection.get_timeout())
            return response.success
        except grpc.RpcError as e:
            raise handle_grpc_error(e, "putting key-value")

    def delete(self, key: bytes, sync: bool = False) -> bool:
        """
        Delete a key-value pair.

        Args:
            key: The key to delete
            sync: Whether to sync to disk before returning

        Returns:
            True if the operation succeeded

        Raises:
            ConnectionError: If the client is not connected or the request fails
            ValidationError: If the key is invalid
        """
        # Input validation
        if not isinstance(key, bytes):
            raise ValidationError("Key must be bytes")
        if not key:
            raise ValidationError("Key cannot be empty")

        request = service_pb2.DeleteRequest(key=key, sync=sync)

        try:
            stub = self._connection.get_stub()
            response = stub.Delete(request, timeout=self._connection.get_timeout())
            return response.success
        except grpc.RpcError as e:
            raise handle_grpc_error(e, "deleting key")

    def batch_write(self, operations: List[BatchOperation], sync: bool = False) -> bool:
        """
        Perform multiple operations in a single atomic batch.

        Args:
            operations: List of operations to perform
            sync: Whether to sync to disk before returning

        Returns:
            True if all operations succeeded

        Raises:
            ConnectionError: If the client is not connected or the request fails
            ValidationError: If any operation is invalid
        """
        # Input validation
        if not operations:
            return True  # Empty batch succeeds trivially

        # Convert our batch operations to protobuf operations
        pb_operations = []
        for op in operations:
            pb_op = service_pb2.Operation(key=op.key, value=op.value or b"")

            if op.type == BatchOperation.Type.PUT:
                pb_op.type = service_pb2.Operation.PUT
            elif op.type == BatchOperation.Type.DELETE:
                pb_op.type = service_pb2.Operation.DELETE
            else:
                raise ValidationError(f"Unknown operation type: {op.type}")

            pb_operations.append(pb_op)

        request = service_pb2.BatchWriteRequest(operations=pb_operations, sync=sync)

        try:
            stub = self._connection.get_stub()
            response = stub.BatchWrite(
                request, timeout=self._connection.get_timeout()
            )
            return response.success
        except grpc.RpcError as e:
            raise handle_grpc_error(e, "performing batch write")

    def scan(self, options: Optional[ScanOptions] = None) -> Scanner:
        """
        Scan keys in the database.

        Args:
            options: Options for the scan operation

        Returns:
            A scanner for iterating through the results

        Raises:
            ConnectionError: If the client is not connected
        """
        if options is None:
            options = ScanOptions()

        return ScanIterator(self._connection, options)

    def begin_transaction(self, read_only: bool = False) -> Transaction:
        """
        Begin a new transaction.

        Args:
            read_only: Whether this is a read-only transaction

        Returns:
            A new transaction object

        Raises:
            ConnectionError: If the client is not connected or the request fails
        """
        request = service_pb2.BeginTransactionRequest(read_only=read_only)

        try:
            stub = self._connection.get_stub()
            response = stub.BeginTransaction(
                request, timeout=self._connection.get_timeout()
            )
            return Transaction(self._connection, response.transaction_id, read_only)
        except grpc.RpcError as e:
            raise handle_grpc_error(e, "beginning transaction")

    def get_stats(self) -> Stats:
        """
        Get database statistics.

        Returns:
            Statistics about the database

        Raises:
            ConnectionError: If the client is not connected or the request fails
        """
        request = service_pb2.GetStatsRequest()

        try:
            stub = self._connection.get_stub()
            response = stub.GetStats(
                request, timeout=self._connection.get_timeout()
            )
            return Stats(
                key_count=response.key_count,
                storage_size=response.storage_size,
                memtable_count=response.memtable_count,
                sstable_count=response.sstable_count,
                write_amplification=response.write_amplification,
                read_amplification=response.read_amplification,
            )
        except grpc.RpcError as e:
            raise handle_grpc_error(e, "getting stats")

    def compact(self, force: bool = False) -> bool:
        """
        Trigger database compaction.

        Args:
            force: Whether to force compaction even if not needed

        Returns:
            True if compaction succeeded

        Raises:
            ConnectionError: If the client is not connected or the request fails
        """
        request = service_pb2.CompactRequest(force=force)

        try:
            stub = self._connection.get_stub()
            response = stub.Compact(
                request, timeout=self._connection.get_timeout()
            )
            return response.success
        except grpc.RpcError as e:
            raise handle_grpc_error(e, "compacting database")
