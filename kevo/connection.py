"""
Connection management for the Kevo client.

This module handles the low-level gRPC connection to the Kevo server,
including channel creation, authentication, and connection lifecycle.
It also handles connection management for replication topology.
"""

import logging
import random
import time
import grpc
from typing import List, Optional, Tuple, Any, Dict, Iterator, Set, Callable

from .errors import handle_grpc_error, ConnectionError, ReplicationError, ReadOnlyError
from .options import ClientOptions
from .proto.kevo import service_pb2, service_pb2_grpc
from .models import NodeInfo, NodeRole, ReplicaInfo

# Configure module logger
logger = logging.getLogger(__name__)


class ReplicaConnection:
    """Manages a connection to a replica node."""

    def __init__(
        self, 
        address: str, 
        options: ClientOptions,
        replica_info: Optional[ReplicaInfo] = None
    ):
        """
        Initialize a replica connection.

        Args:
            address: Address of the replica
            options: Connection options
            replica_info: Additional information about the replica
        """
        self.address = address
        self._options = options
        self.replica_info = replica_info
        self._channel = None
        self._stub = None
        self._connected = False
        self._available = False
    
    def connect(self) -> None:
        """
        Connect to the replica.

        Raises:
            ConnectionError: If the connection fails
        """
        if self._connected:
            return

        try:
            # Set up channel options
            grpc_channel_options = _create_grpc_options(self._options)

            # Create channel (secure or insecure)
            if self._options.tls_enabled:
                self._channel = _create_secure_channel(
                    self._options, self.address, grpc_channel_options
                )
            else:
                self._channel = grpc.insecure_channel(
                    self.address, options=grpc_channel_options
                )

            # Create the stub
            self._stub = service_pb2_grpc.KevoServiceStub(self._channel)

            # Test the connection
            self._test_connection()
            self._connected = True
            self._available = True
            logger.debug(f"Connected to replica at {self.address}")

        except Exception as e:
            if self._channel:
                self._channel.close()
                self._channel = None
            self._stub = None
            self._connected = False
            self._available = False
            logger.warning(f"Failed to connect to replica at {self.address}: {e}")
            if isinstance(e, grpc.RpcError):
                raise handle_grpc_error(e, f"connecting to replica at {self.address}")
            raise ConnectionError(f"Failed to connect to replica at {self.address}: {e}") from e

    def close(self) -> None:
        """Close the connection to the replica."""
        if self._channel is not None:
            self._channel.close()
            self._channel = None
            self._stub = None
            self._connected = False
            self._available = False

    def is_connected(self) -> bool:
        """Check if connected to the replica."""
        return self._connected and self._channel is not None
    
    def is_available(self) -> bool:
        """Check if the replica is available for operations."""
        return self._available
    
    def get_stub(self) -> service_pb2_grpc.KevoServiceStub:
        """
        Get the gRPC stub for this replica.
        
        Returns:
            The gRPC stub for making API calls
            
        Raises:
            ConnectionError: If not connected
        """
        if not self.is_connected():
            # Try to reconnect if auto_reconnect is enabled in options
            if self._options.auto_reconnect:
                logger.info(f"Connection to replica at {self.address} lost. Attempting to reconnect...")
                try:
                    self.connect()
                    logger.info(f"Reconnection to replica at {self.address} successful")
                except Exception as e:
                    logger.warning(f"Failed to reconnect to replica at {self.address}: {e}")
                    raise ConnectionError(f"Not connected to replica at {self.address} and reconnection failed")
            else:
                raise ConnectionError(f"Not connected to replica at {self.address}")
        return self._stub
    
    def _test_connection(self) -> None:
        """
        Test the connection with a simple operation.
        
        Raises:
            ConnectionError: If the test fails
        """
        try:
            self._stub.GetStats(
                service_pb2.GetStatsRequest(), timeout=self._options.connect_timeout
            )
        except grpc.RpcError as e:
            # Clean up before raising error
            if self._channel:
                self._channel.close()
                self._channel = None
            self._stub = None
            self._available = False
            raise handle_grpc_error(e, f"testing connection to replica at {self.address}")


class Connection:
    """Manages the gRPC connections to Kevo servers, including replication topology."""

    def __init__(self, options: ClientOptions):
        """
        Initialize a connection.

        Args:
            options: Connection options
        """
        self._options = options
        self._channel = None
        self._stub = None
        self._connected = False
        
        # Replication state
        self._node_info = None
        self._primary_conn = None
        self._replica_conns = {}  # address -> ReplicaConnection
        self._replica_round_robin_index = 0

    def connect(self) -> None:
        """
        Connect to the server and discover replication topology if enabled.

        Raises:
            ConnectionError: If the connection fails
        """
        if self._connected:
            return

        try:
            # Connect to the initial endpoint
            self._connect_to_endpoint(self._options.endpoint)
            
            # Discover replication topology if enabled
            if self._options.replication.discover_topology:
                self._discover_topology()
        
        except Exception as e:
            # Clean up all connections
            self.close()
            if isinstance(e, grpc.RpcError):
                raise handle_grpc_error(e, "connecting to server")
            raise ConnectionError(f"Failed to connect: {e}") from e

    def close(self) -> None:
        """Close all connections to servers."""
        # Close the primary connection
        if self._primary_conn is not None:
            self._primary_conn.close()
            self._primary_conn = None
        
        # Close the direct connection
        if self._channel is not None:
            self._channel.close()
            self._channel = None
            self._stub = None
        
        # Close all replica connections
        for replica_conn in self._replica_conns.values():
            replica_conn.close()
        self._replica_conns.clear()
        
        self._connected = False
        self._node_info = None

    def is_connected(self) -> bool:
        """Check if the client is connected to the server."""
        return self._connected and (
            self._channel is not None or 
            self._primary_conn is not None or 
            any(conn.is_connected() for conn in self._replica_conns.values())
        )

    def check_connection(self) -> None:
        """
        Check that the client is connected.
        
        Raises:
            ConnectionError: If not connected
        """
        if not self.is_connected():
            raise ConnectionError("Not connected to any server")

    def get_stub(self) -> service_pb2_grpc.KevoServiceStub:
        """
        Get the primary gRPC stub.
        
        Returns:
            The gRPC stub for making API calls
            
        Raises:
            ConnectionError: If not connected
        """
        try:
            self.check_connection()
            if self._primary_conn is not None:
                return self._primary_conn.get_stub()
            return self._stub
        except ConnectionError:
            # Attempt to reconnect if auto_reconnect is enabled
            if self._options.auto_reconnect:
                logger.info("Connection lost. Attempting to reconnect...")
                if self._try_reconnect():
                    logger.info("Reconnection successful")
                    # Try getting the stub again after reconnection
                    return self.get_stub()
            # If reconnection failed or is disabled, raise the original error
            raise ConnectionError("Not connected to any server and reconnection failed")

    def get_timeout(self) -> float:
        """Get the request timeout in seconds."""
        return self._options.request_timeout
    
    def get_node_info(self) -> Optional[NodeInfo]:
        """Get information about the connected node's role and topology."""
        return self._node_info
    
    def has_replicas(self) -> bool:
        """Check if there are any connected replicas."""
        return bool(self._replica_conns) and any(conn.is_available() for conn in self._replica_conns.values())
    
    def get_available_replica_stub(self) -> Optional[service_pb2_grpc.KevoServiceStub]:
        """
        Get a stub for an available replica using the configured selection strategy.
        
        Returns:
            A replica stub if available, None otherwise
        """
        if not self.has_replicas():
            return None
        
        available_replicas = [conn for conn in self._replica_conns.values() if conn.is_available()]
        if not available_replicas:
            return None
        
        # Select a replica based on the configured strategy
        strategy = self._options.replication.replica_selection_strategy
        if strategy == "random":
            replica = random.choice(available_replicas)
        elif strategy == "sequential":
            # Sort by address for consistency
            replica = sorted(available_replicas, key=lambda conn: conn.address)[0]
        elif strategy == "round_robin":
            # Implement round-robin selection
            idx = self._replica_round_robin_index % len(available_replicas)
            replica = available_replicas[idx]
            self._replica_round_robin_index += 1
        else:
            # Default to random
            replica = random.choice(available_replicas)
        
        return replica.get_stub()
    
    def should_route_to_replica(self, read_from_replicas: Optional[bool] = None) -> bool:
        """
        Determine if a read operation should be routed to a replica.
        
        Args:
            read_from_replicas: Whether the operation should read from replicas.
                If None, the client's read_from_replicas setting is used.
            
        Returns:
            True if the operation should be routed to a replica, False otherwise
        """
        # If routing is disabled, don't route to replicas
        if not self._options.replication.auto_route_reads:
            return False
        
        # If the parameter is provided, use it
        # Otherwise use the client-level setting
        use_replica = read_from_replicas if read_from_replicas is not None else self._options.replication.read_from_replicas
        
        # If we shouldn't use replicas, don't route to replicas
        if not use_replica:
            return False
        
        # If we're directly connected to a replica, use the current connection
        if self._node_info and self._node_info.node_role == NodeRole.REPLICA:
            return False
        
        # If we're connected to the primary and have replicas, route to a replica
        if (self._node_info and 
            self._node_info.node_role == NodeRole.PRIMARY and 
            self.has_replicas()):
            return True
        
        return False
    
    def should_route_to_primary(self) -> bool:
        """
        Determine if a write operation should be routed to the primary.
        
        Returns:
            True if the operation should be routed to the primary, False otherwise
        """
        # If routing is disabled, don't route to primary
        if not self._options.replication.auto_route_writes:
            return False
        
        # If we're directly connected to a primary, use the current connection
        if self._node_info and self._node_info.node_role == NodeRole.PRIMARY:
            return False
        
        # If we're connected to a replica and have a primary connection, route to primary
        if (self._node_info and 
            self._node_info.node_role == NodeRole.REPLICA and 
            self._primary_conn is not None):
            return True
        
        return False
    
    def _try_reconnect(self) -> bool:
        """
        Attempt to reconnect to the server with exponential backoff.
        
        Returns:
            True if reconnection was successful, False otherwise
        """
        # Reset connection state
        was_connected_to_primary = self._primary_conn is not None
        was_connected_to_replicas = bool(self._replica_conns)
        
        # Close all current connections
        self.close()
        
        # Try to reconnect with exponential backoff
        delay = self._options.reconnect_initial_delay
        for attempt in range(self._options.reconnect_max_attempts):
            try:
                logger.debug(f"Reconnection attempt {attempt + 1}/{self._options.reconnect_max_attempts}")
                
                # Connect to the initial endpoint
                self._connect_to_endpoint(self._options.endpoint)
                
                # Discover replication topology if enabled
                if self._options.replication.discover_topology:
                    self._discover_topology()
                
                # If we were previously connected to primary/replicas, try to reconnect to them
                if was_connected_to_primary and self._primary_conn is None and self._node_info and self._node_info.primary_address:
                    try:
                        self._connect_to_primary(self._node_info.primary_address)
                    except Exception as e:
                        logger.warning(f"Failed to reconnect to primary: {e}")
                
                # Reconnection successful
                return True
                
            except Exception as e:
                logger.warning(f"Reconnection attempt {attempt + 1} failed: {e}")
                
                # Sleep with exponential backoff before retrying
                if attempt < self._options.reconnect_max_attempts - 1:  # Don't sleep after the last attempt
                    jitter = random.uniform(0, self._options.retry_jitter * delay)
                    time.sleep(delay + jitter)
                    delay = min(delay * self._options.reconnect_backoff_factor, self._options.reconnect_max_delay)
        
        # All reconnection attempts failed
        return False

    def get_read_stub(self, read_from_replicas: Optional[bool] = None) -> service_pb2_grpc.KevoServiceStub:
        """
        Get a stub for read operations, considering replication routing.
        
        Args:
            read_from_replicas: Whether to read from replicas for this operation.
                If None, the client's read_from_replicas setting is used.
            
        Returns:
            A stub for read operations
            
        Raises:
            ConnectionError: If not connected
        """
        try:
            self.check_connection()
            
            # Check if we should route to a replica
            if self.should_route_to_replica(read_from_replicas):
                replica_stub = self.get_available_replica_stub()
                if replica_stub is not None:
                    return replica_stub
            
            # Fall back to the primary connection
            if self._primary_conn is not None:
                return self._primary_conn.get_stub()
            
            # Fall back to the direct connection
            return self._stub
            
        except ConnectionError:
            # Attempt to reconnect if auto_reconnect is enabled
            if self._options.auto_reconnect:
                logger.info("Connection lost. Attempting to reconnect...")
                if self._try_reconnect():
                    logger.info("Reconnection successful")
                    # Try getting the stub again after reconnection
                    return self.get_read_stub(read_from_replicas)
            # If reconnection failed or is disabled, raise the original error
            raise ConnectionError("Not connected to any server and reconnection failed")
    
    def get_write_stub(self) -> service_pb2_grpc.KevoServiceStub:
        """
        Get a stub for write operations, considering replication routing.
        
        Returns:
            A stub for write operations
            
        Raises:
            ConnectionError: If not connected
        """
        try:
            self.check_connection()
            
            # Check if we should route to the primary
            if self.should_route_to_primary():
                return self._primary_conn.get_stub()
            
            # Fall back to the direct connection
            return self._stub
            
        except ConnectionError:
            # Attempt to reconnect if auto_reconnect is enabled
            if self._options.auto_reconnect:
                logger.info("Connection lost. Attempting to reconnect...")
                if self._try_reconnect():
                    logger.info("Reconnection successful")
                    # Try getting the stub again after reconnection
                    return self.get_write_stub()
            # If reconnection failed or is disabled, raise the original error
            raise ConnectionError("Not connected to any server and reconnection failed")
    
    def handle_read_only_error(self, error: ReadOnlyError) -> None:
        """
        Handle a read-only error by connecting to the primary if needed.
        
        Args:
            error: The read-only error with primary address information
        """
        if error.primary_address and self._options.replication.auto_connect_to_primary:
            logger.info(f"Received read-only error. Connecting to primary at {error.primary_address}")
            try:
                self._connect_to_primary(error.primary_address)
                # Re-discover topology to update node info
                self._discover_topology()
            except Exception as e:
                logger.warning(f"Failed to connect to primary at {error.primary_address}: {e}")
    
    def _connect_to_endpoint(self, endpoint: str) -> None:
        """
        Connect to the specified endpoint.
        
        Args:
            endpoint: The server endpoint to connect to
            
        Raises:
            ConnectionError: If the connection fails
        """
        try:
            # Set up channel options
            grpc_channel_options = _create_grpc_options(self._options)

            # Create channel (secure or insecure)
            if self._options.tls_enabled:
                self._channel = _create_secure_channel(
                    self._options, endpoint, grpc_channel_options
                )
            else:
                self._channel = grpc.insecure_channel(
                    endpoint, options=grpc_channel_options
                )

            # Create the stub
            self._stub = service_pb2_grpc.KevoServiceStub(self._channel)

            # Test the connection with a simple operation
            self._test_connection()
            self._connected = True

        except Exception as e:
            if self._channel:
                self._channel.close()
                self._channel = None
            self._stub = None
            if isinstance(e, grpc.RpcError):
                raise handle_grpc_error(e, f"connecting to endpoint {endpoint}")
            raise ConnectionError(f"Failed to connect to {endpoint}: {e}") from e
    
    def _connect_to_primary(self, address: str) -> None:
        """
        Connect to the primary server.
        
        Args:
            address: The primary server address
            
        Raises:
            ConnectionError: If the connection fails
        """
        # Skip if already connected to this primary
        if self._primary_conn and self._primary_conn.address == address:
            return
        
        # Close existing primary connection if any
        if self._primary_conn:
            self._primary_conn.close()
        
        # Create a new primary connection
        self._primary_conn = ReplicaConnection(address, self._options)
        
        try:
            self._primary_conn.connect()
            logger.info(f"Connected to primary at {address}")
        except Exception as e:
            self._primary_conn = None
            logger.warning(f"Failed to connect to primary at {address}: {e}")
            raise
    
    def _connect_to_replica(self, replica_info: ReplicaInfo) -> None:
        """
        Connect to a replica server.
        
        Args:
            replica_info: Information about the replica to connect to
        """
        # Skip if already connected to this replica
        if replica_info.address in self._replica_conns:
            # Update replica info
            self._replica_conns[replica_info.address].replica_info = replica_info
            return
        
        # Create a new replica connection
        replica_conn = ReplicaConnection(
            replica_info.address, 
            self._options,
            replica_info
        )
        
        try:
            replica_conn.connect()
            self._replica_conns[replica_info.address] = replica_conn
            logger.info(f"Connected to replica at {replica_info.address}")
        except Exception as e:
            logger.warning(f"Failed to connect to replica at {replica_info.address}: {e}")
    
    def _discover_topology(self) -> None:
        """
        Discover the replication topology by calling GetNodeInfo.
        
        Raises:
            ReplicationError: If topology discovery fails
        """
        try:
            # Call GetNodeInfo RPC
            request = service_pb2.GetNodeInfoRequest()
            response = self._stub.GetNodeInfo(request, timeout=self._options.connect_timeout)
            
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
            
            self._node_info = NodeInfo(
                node_role=node_role,
                primary_address=response.primary_address,
                replicas=replicas,
                last_sequence=response.last_sequence,
                read_only=response.read_only
            )
            
            logger.info(f"Discovered node role: {node_role.value}")
            
            # Connect to primary if we're connected to a replica
            if (node_role == NodeRole.REPLICA and 
                response.primary_address and 
                self._options.replication.auto_connect_to_primary):
                try:
                    self._connect_to_primary(response.primary_address)
                except Exception as e:
                    logger.warning(f"Failed to connect to primary: {e}")
            
            # Connect to replicas if we're connected to the primary
            if (node_role == NodeRole.PRIMARY and 
                replicas and 
                self._options.replication.auto_connect_to_replicas):
                for replica in replicas:
                    if replica.available:
                        try:
                            self._connect_to_replica(replica)
                        except Exception as e:
                            logger.warning(f"Failed to connect to replica: {e}")
        
        except Exception as e:
            if isinstance(e, grpc.RpcError):
                err = handle_grpc_error(e, "discovering topology")
                logger.warning(f"Topology discovery failed: {err}")
                # If this is a older server without replication support, continue without topology
                if "UNIMPLEMENTED" in str(e):
                    self._node_info = NodeInfo(node_role=NodeRole.STANDALONE)
                    return
            else:
                logger.warning(f"Topology discovery failed: {e}")
            raise ReplicationError(f"Failed to discover topology: {e}") from e
    
    def _test_connection(self) -> None:
        """
        Test the connection with a simple operation.
        
        Raises:
            ConnectionError: If the test fails
        """
        try:
            self._stub.GetStats(
                service_pb2.GetStatsRequest(), timeout=self._options.connect_timeout
            )
        except grpc.RpcError as e:
            # Clean up before raising error
            if self._channel:
                self._channel.close()
                self._channel = None
            self._stub = None
            raise handle_grpc_error(e, "testing connection")


def _create_grpc_options(options: ClientOptions) -> List[Tuple[str, Any]]:
    """
    Create gRPC channel options.
    
    Args:
        options: Client options
        
    Returns:
        List of gRPC channel options
    """
    channel_options = []

    # Set message size limits if specified
    if options.max_message_size > 0:
        channel_options.extend(
            [
                (
                    "grpc.max_send_message_length",
                    options.max_message_size,
                ),
                (
                    "grpc.max_receive_message_length",
                    options.max_message_size,
                ),
            ]
        )
    
    # Add keep-alive parameters to prevent premature socket closures
    channel_options.extend([
        # Send keepalive pings every 30 seconds
        ("grpc.keepalive_time_ms", 30000),
        # Keepalive ping timeout after 10 seconds
        ("grpc.keepalive_timeout_ms", 10000),
        # Allow keepalive pings even when there's no active streams
        ("grpc.keepalive_permit_without_calls", 1),
        # Allow up to 5 pings without data
        ("grpc.http2.max_pings_without_data", 5),
        # Minimum time between pings
        ("grpc.http2.min_time_between_pings_ms", 10000),
        # Minimum ping interval without data
        ("grpc.http2.min_ping_interval_without_data_ms", 5000),
    ])

    return channel_options


def _create_secure_channel(
    options: ClientOptions, endpoint: str, channel_options: List[Tuple[str, Any]]
) -> grpc.Channel:
    """
    Create a secure gRPC channel.
    
    Args:
        options: Client options
        endpoint: Server endpoint
        channel_options: gRPC channel options
        
    Returns:
        A secure gRPC channel
        
    Raises:
        ValueError: If TLS options are missing
    """
    # Validate TLS options
    if not all(
        [
            options.cert_file,
            options.key_file,
            options.ca_file,
        ]
    ):
        raise ValueError(
            "cert_file, key_file, and ca_file must be provided for TLS"
        )

    # Read certificate files
    with open(options.ca_file, "rb") as f:
        ca_cert = f.read()

    with open(options.cert_file, "rb") as f:
        client_cert = f.read()

    with open(options.key_file, "rb") as f:
        client_key = f.read()

    # Create credentials
    credentials = grpc.ssl_channel_credentials(
        root_certificates=ca_cert,
        private_key=client_key,
        certificate_chain=client_cert,
    )

    # Create secure channel
    return grpc.secure_channel(
        endpoint, credentials, options=channel_options
    )