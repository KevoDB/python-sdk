"""
Connection management for the Kevo client.

This module handles the low-level gRPC connection to the Kevo server,
including channel creation, authentication, and connection lifecycle.
"""

import grpc
from typing import List, Optional, Tuple, Any, Dict, Iterator

from .errors import handle_grpc_error, ConnectionError
from .options import ClientOptions
from .proto.kevo import service_pb2, service_pb2_grpc


class Connection:
    """Manages the gRPC connection to a Kevo server."""

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

    def connect(self) -> None:
        """
        Connect to the server.

        Raises:
            ConnectionError: If the connection fails
        """
        if self._connected:
            return

        try:
            # Set up channel options
            grpc_channel_options = self._create_grpc_options()

            # Create channel (secure or insecure)
            if self._options.tls_enabled:
                self._channel = self._create_secure_channel(grpc_channel_options)
            else:
                self._channel = grpc.insecure_channel(
                    self._options.endpoint, options=grpc_channel_options
                )

            # Create the stub
            self._stub = service_pb2_grpc.KevoServiceStub(self._channel)

            # Test the connection with a simple operation
            self._test_connection()
            self._connected = True

        except Exception as e:
            if isinstance(e, grpc.RpcError):
                raise handle_grpc_error(e, "connecting to server")
            raise ConnectionError(f"Failed to connect: {e}") from e

    def close(self) -> None:
        """Close the connection to the server."""
        if self._channel is not None:
            self._channel.close()
            self._channel = None
            self._stub = None
            self._connected = False

    def is_connected(self) -> bool:
        """Check if the client is connected to the server."""
        return self._connected and self._channel is not None

    def check_connection(self) -> None:
        """
        Check that the client is connected.
        
        Raises:
            ConnectionError: If not connected
        """
        if not self.is_connected():
            raise ConnectionError("Not connected to server")

    def get_stub(self) -> service_pb2_grpc.KevoServiceStub:
        """
        Get the gRPC stub.
        
        Returns:
            The gRPC stub for making API calls
            
        Raises:
            ConnectionError: If not connected
        """
        self.check_connection()
        return self._stub

    def get_timeout(self) -> float:
        """Get the request timeout in seconds."""
        return self._options.request_timeout

    def _create_grpc_options(self) -> List[Tuple[str, Any]]:
        """Create gRPC channel options."""
        options = []

        # Set message size limits if specified
        if self._options.max_message_size > 0:
            options.extend(
                [
                    (
                        "grpc.max_send_message_length",
                        self._options.max_message_size,
                    ),
                    (
                        "grpc.max_receive_message_length",
                        self._options.max_message_size,
                    ),
                ]
            )

        return options

    def _create_secure_channel(self, options: List[Tuple[str, Any]]) -> grpc.Channel:
        """
        Create a secure gRPC channel.
        
        Args:
            options: gRPC channel options
            
        Returns:
            A secure gRPC channel
            
        Raises:
            ValueError: If TLS options are missing
        """
        # Validate TLS options
        if not all(
            [
                self._options.cert_file,
                self._options.key_file,
                self._options.ca_file,
            ]
        ):
            raise ValueError(
                "cert_file, key_file, and ca_file must be provided for TLS"
            )

        # Read certificate files
        with open(self._options.ca_file, "rb") as f:
            ca_cert = f.read()

        with open(self._options.cert_file, "rb") as f:
            client_cert = f.read()

        with open(self._options.key_file, "rb") as f:
            client_key = f.read()

        # Create credentials
        credentials = grpc.ssl_channel_credentials(
            root_certificates=ca_cert,
            private_key=client_key,
            certificate_chain=client_cert,
        )

        # Create secure channel
        return grpc.secure_channel(
            self._options.endpoint, credentials, options=options
        )

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