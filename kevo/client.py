"""
Client implementation for Kevo key-value store.

This module provides the main client interface for connecting to and
interacting with a Kevo server, including replication support.
"""

import logging
import grpc
from typing import List, Optional, Tuple, Iterator, Dict, Callable, Any, TypeVar

from .connection import Connection
from .errors import handle_grpc_error, ConnectionError, ValidationError, ReadOnlyError
from .models import KeyValue, Stats, BatchOperation, NodeInfo, ReplicaInfo, NodeRole
from .options import ClientOptions, ScanOptions, ReadOptions, WriteOptions
from .proto.kevo import service_pb2, service_pb2_grpc
from .scanner import Scanner, ScanIterator
from .transaction import Transaction

# Configure module logger
logger = logging.getLogger(__name__)

# Type variables for generic functions
T = TypeVar('T')


class Client:
    """Client for connecting to and interacting with a Kevo server."""

    def __init__(self, options: Optional[ClientOptions] = None, read_from_replicas: Optional[bool] = None):
        """
        Initialize a Kevo client.

        Args:
            options: Client configuration options
            read_from_replicas: Whether to prefer reading from replicas when available. 
                If not specified, uses the value from ClientOptions.replication.read_from_replicas
        """
        self._options = options or ClientOptions()
        
        # Set read_from_replicas on client options if specified
        if read_from_replicas is not None:
            self._options.replication.read_from_replicas = read_from_replicas
            
        self._connection = Connection(self._options)

    def connect(self) -> None:
        """
        Connect to the server and discover topology if replication is enabled.

        Raises:
            ConnectionError: If the connection fails
        """
        self._connection.connect()

    def close(self) -> None:
        """Close all connections to the server."""
        self._connection.close()

    def is_connected(self) -> bool:
        """Check if the client is connected to the server."""
        return self._connection.is_connected()

    def get_node_info(self) -> Optional[NodeInfo]:
        """
        Get information about the connected node's role and topology.

        Returns:
            Node information including role, replication status, and topology

        Raises:
            ConnectionError: If the client is not connected
        """
        if not self.is_connected():
            raise ConnectionError("Not connected to server")

        # Return cached node info if available
        node_info = self._connection.get_node_info()
        if node_info:
            return node_info

        # Otherwise, query the server for node info
        request = service_pb2.GetNodeInfoRequest()

        try:
            stub = self._connection.get_stub()
            response = stub.GetNodeInfo(
                request, timeout=self._connection.get_timeout()
            )

            # Convert protobuf response to our model
            node_role = {
                service_pb2.GetNodeInfoResponse.STANDALONE: NodeRole.STANDALONE,
                service_pb2.GetNodeInfoResponse.PRIMARY: NodeRole.PRIMARY,
                service_pb2.GetNodeInfoResponse.REPLICA: NodeRole.REPLICA,
            }.get(response.node_role, NodeRole.STANDALONE)

            replicas = []
            for replica_pb in response.replicas:
                meta = {k: v for k, v in replica_pb.meta.items()}
                replica = ReplicaInfo(
                    address=replica_pb.address,
                    last_sequence=replica_pb.last_sequence,
                    available=replica_pb.available,
                    region=replica_pb.region,
                    meta=meta
                )
                replicas.append(replica)

            return NodeInfo(
                node_role=node_role,
                primary_address=response.primary_address,
                replicas=replicas,
                last_sequence=response.last_sequence,
                read_only=response.read_only
            )
        except grpc.RpcError as e:
            error = handle_grpc_error(e, "getting node info")

            # For older servers that don't support GetNodeInfo, return a standalone node
            if "UNIMPLEMENTED" in str(e):
                return NodeInfo(node_role=NodeRole.STANDALONE)

            raise error

    def get(self, key: bytes, options: Optional[ReadOptions] = None) -> Tuple[Optional[bytes], bool]:
        """
        Get a value by key.

        Args:
            key: The key to get
            options: Read operation options

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

        options = options or ReadOptions()
        request = service_pb2.GetRequest(key=key)

        return self._execute_read_operation(
            lambda stub: stub.Get(request, timeout=self._connection.get_timeout()),
            options.read_from_replicas,
            "getting key",
            lambda response: (response.value, response.found)
        )

    def put(self, key: bytes, value: bytes, sync: bool = False, options: Optional[WriteOptions] = None) -> bool:
        """
        Put a key-value pair.

        Args:
            key: The key to put
            value: The value to put
            sync: Whether to sync to disk before returning
            options: Write operation options

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

        options = options or WriteOptions(sync=sync)
        request = service_pb2.PutRequest(key=key, value=value, sync=options.sync)

        return self._execute_write_operation(
            lambda stub: stub.Put(request, timeout=self._get_timeout(options.timeout)),
            "putting key-value",
            lambda response: response.success
        )

    def delete(self, key: bytes, sync: bool = False, options: Optional[WriteOptions] = None) -> bool:
        """
        Delete a key-value pair.

        Args:
            key: The key to delete
            sync: Whether to sync to disk before returning
            options: Write operation options

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

        options = options or WriteOptions(sync=sync)
        request = service_pb2.DeleteRequest(key=key, sync=options.sync)

        return self._execute_write_operation(
            lambda stub: stub.Delete(request, timeout=self._get_timeout(options.timeout)),
            "deleting key",
            lambda response: response.success
        )

    def batch_write(self, operations: List[BatchOperation], sync: bool = False, options: Optional[WriteOptions] = None) -> bool:
        """
        Perform multiple operations in a single atomic batch.

        Args:
            operations: List of operations to perform
            sync: Whether to sync to disk before returning
            options: Write operation options

        Returns:
            True if all operations succeeded

        Raises:
            ConnectionError: If the client is not connected or the request fails
            ValidationError: If any operation is invalid
        """
        # Input validation
        if not operations:
            return True  # Empty batch succeeds trivially

        options = options or WriteOptions(sync=sync)

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

        request = service_pb2.BatchWriteRequest(operations=pb_operations, sync=options.sync)

        return self._execute_write_operation(
            lambda stub: stub.BatchWrite(request, timeout=self._get_timeout(options.timeout)),
            "performing batch write",
            lambda response: response.success
        )

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

        # For read-only transactions, we can use a replica
        # For write transactions, we must use the primary
        if read_only:
            stub_fn = lambda: self._connection.get_read_stub(read_from_replicas=True)
        else:
            stub_fn = lambda: self._connection.get_write_stub()

        try:
            stub = stub_fn()
            response = stub.BeginTransaction(
                request, timeout=self._connection.get_timeout()
            )
            return Transaction(self._connection, response.transaction_id, read_only)
        except grpc.RpcError as e:
            err = handle_grpc_error(e, "beginning transaction")

            # If this is a read-only error, try to connect to the primary and retry
            if isinstance(err, ReadOnlyError) and err.primary_address:
                self._connection.handle_read_only_error(err)
                # Retry the operation with the primary connection
                stub = self._connection.get_write_stub()
                response = stub.BeginTransaction(
                    request, timeout=self._connection.get_timeout()
                )
                return Transaction(self._connection, response.transaction_id, read_only)

            raise err

    def get_stats(self, read_from_replicas: bool = False) -> Stats:
        """
        Get database statistics.

        Args:
            read_from_replicas: Whether to read from replicas for this operation

        Returns:
            Statistics about the database

        Raises:
            ConnectionError: If the client is not connected or the request fails
        """
        request = service_pb2.GetStatsRequest()

        return self._execute_read_operation(
            lambda stub: stub.GetStats(request, timeout=self._connection.get_timeout()),
            read_from_replicas,
            "getting stats",
            lambda response: Stats(
                key_count=response.key_count,
                storage_size=response.storage_size,
                memtable_count=response.memtable_count,
                sstable_count=response.sstable_count,
                write_amplification=response.write_amplification,
                read_amplification=response.read_amplification,
            )
        )

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

        return self._execute_write_operation(
            lambda stub: stub.Compact(request, timeout=self._connection.get_timeout()),
            "compacting database",
            lambda response: response.success
        )

    def with_primary(self, callback: Callable[['Client'], T]) -> T:
        """
        Execute operations explicitly on the primary node.

        This is useful for operations that must be executed on the primary,
        even if they are read operations.

        Args:
            callback: A function that takes this Client and returns a result

        Returns:
            The result of the callback function

        Raises:
            ConnectionError: If not connected to a primary node
        """
        # Check if we're connected to a primary node
        node_info = self._connection.get_node_info()

        # If we're already connected to the primary, just use this client
        if node_info and node_info.node_role == NodeRole.PRIMARY:
            return callback(self)

        # If we have a connection to the primary, use it
        if self._connection._primary_conn is not None:
            # TODO: This is a bit of a hack, but it's simpler than creating a whole new client
            old_stub = self._connection._stub
            self._connection._stub = self._connection._primary_conn.get_stub()

            try:
                result = callback(self)
            finally:
                # Restore the original stub
                self._connection._stub = old_stub

            return result

        # If we don't have a primary connection, try to get one
        if node_info and node_info.node_role == NodeRole.REPLICA and node_info.primary_address:
            try:
                self._connection._connect_to_primary(node_info.primary_address)
                return self.with_primary(callback)
            except Exception as e:
                raise ConnectionError(f"Failed to connect to primary: {e}")

        raise ConnectionError("Not connected to a primary node")

    def _get_timeout(self, timeout: Optional[float] = None) -> float:
        """Get the timeout to use for an operation."""
        return timeout if timeout is not None else self._connection.get_timeout()

    def _execute_read_operation(self,
                               op_fn: Callable[[service_pb2_grpc.KevoServiceStub], Any],
                               read_from_replicas: bool,
                               operation_name: str,
                               result_fn: Callable[[Any], T] = lambda x: x) -> T:
        """
        Execute a read operation with intelligent routing to replicas if available.

        Args:
            op_fn: Function that takes a stub and returns the operation response
            read_from_replicas: Whether to read from replicas for this operation
            operation_name: Name of the operation for error reporting
            result_fn: Function to transform the response into the return value

        Returns:
            The result of the operation, transformed by result_fn

        Raises:
            ConnectionError: If not connected or the operation fails
        """
        try:
            # Get an appropriate stub for reading
            stub = self._connection.get_read_stub(read_from_replicas)

            # Execute the operation
            response = op_fn(stub)

            # Transform and return the result
            return result_fn(response)

        except grpc.RpcError as e:
            raise handle_grpc_error(e, operation_name)

    def _execute_write_operation(self,
                                op_fn: Callable[[service_pb2_grpc.KevoServiceStub], Any],
                                operation_name: str,
                                result_fn: Callable[[Any], T] = lambda x: x) -> T:
        """
        Execute a write operation with routing to primary if needed.

        Args:
            op_fn: Function that takes a stub and returns the operation response
            operation_name: Name of the operation for error reporting
            result_fn: Function to transform the response into the return value

        Returns:
            The result of the operation, transformed by result_fn

        Raises:
            ConnectionError: If not connected or the operation fails
        """
        try:
            # Get the appropriate stub for writing
            stub = self._connection.get_write_stub()

            # Execute the operation
            response = op_fn(stub)

            # Transform and return the result
            return result_fn(response)

        except grpc.RpcError as e:
            err = handle_grpc_error(e, operation_name)

            # If this is a read-only error, try to connect to the primary and retry
            if isinstance(err, ReadOnlyError) and err.primary_address:
                self._connection.handle_read_only_error(err)

                # Retry the operation with the primary connection
                stub = self._connection.get_write_stub()
                response = op_fn(stub)
                return result_fn(response)

            raise err
