"""
Tests for the Kevo client.

These tests use mock gRPC responses to test the client functionality.
"""

import pytest
from unittest.mock import MagicMock, patch

from kevo import Client, ClientOptions, BatchOperation
from kevo.client import ScanOptions


@pytest.fixture
def mock_grpc_stub():
    """Create a mock gRPC stub."""
    with patch("kevo.client.service_pb2_grpc.KevoServiceStub") as mock_stub_class:
        mock_stub = MagicMock()
        mock_stub_class.return_value = mock_stub
        yield mock_stub


@pytest.fixture
def mock_grpc_channel():
    """Create a mock gRPC channel."""
    with patch("kevo.client.grpc.insecure_channel") as mock_channel_func:
        mock_channel = MagicMock()
        mock_channel_func.return_value = mock_channel
        yield mock_channel


@pytest.fixture
def client(mock_grpc_stub, mock_grpc_channel):
    """Create a client with mocked gRPC components."""
    options = ClientOptions(endpoint="localhost:50051")
    client = Client(options)
    
    # Setup GetStats to succeed for connection testing
    stats_response = MagicMock()
    stats_response.key_count = 100
    mock_grpc_stub.GetStats.return_value = stats_response
    
    client.connect()
    return client


def test_client_connect(mock_grpc_stub, mock_grpc_channel):
    """Test connecting to the server."""
    options = ClientOptions(endpoint="localhost:50051")
    client = Client(options)
    
    # Setup GetStats to succeed for connection testing
    stats_response = MagicMock()
    stats_response.key_count = 100
    mock_grpc_stub.GetStats.return_value = stats_response
    
    # Connect should succeed
    client.connect()
    assert client.is_connected() is True
    
    # Connect when already connected should do nothing
    client.connect()
    assert client.is_connected() is True


def test_client_close(client, mock_grpc_channel):
    """Test closing the connection."""
    assert client.is_connected() is True
    client.close()
    assert client.is_connected() is False
    mock_grpc_channel.close.assert_called_once()


def test_get(client, mock_grpc_stub):
    """Test getting a value."""
    # Setup mock response
    get_response = MagicMock()
    get_response.value = b"test-value"
    get_response.found = True
    mock_grpc_stub.Get.return_value = get_response
    
    # Call get
    value, found = client.get(b"test-key")
    
    # Verify result
    assert value == b"test-value"
    assert found is True
    
    # Verify request
    mock_grpc_stub.Get.assert_called_once()
    request = mock_grpc_stub.Get.call_args[0][0]
    assert request.key == b"test-key"


def test_put(client, mock_grpc_stub):
    """Test putting a value."""
    # Setup mock response
    put_response = MagicMock()
    put_response.success = True
    mock_grpc_stub.Put.return_value = put_response
    
    # Call put
    success = client.put(b"test-key", b"test-value", sync=True)
    
    # Verify result
    assert success is True
    
    # Verify request
    mock_grpc_stub.Put.assert_called_once()
    request = mock_grpc_stub.Put.call_args[0][0]
    assert request.key == b"test-key"
    assert request.value == b"test-value"
    assert request.sync is True


def test_delete(client, mock_grpc_stub):
    """Test deleting a value."""
    # Setup mock response
    delete_response = MagicMock()
    delete_response.success = True
    mock_grpc_stub.Delete.return_value = delete_response
    
    # Call delete
    success = client.delete(b"test-key", sync=True)
    
    # Verify result
    assert success is True
    
    # Verify request
    mock_grpc_stub.Delete.assert_called_once()
    request = mock_grpc_stub.Delete.call_args[0][0]
    assert request.key == b"test-key"
    assert request.sync is True


def test_batch_write(client, mock_grpc_stub):
    """Test batch write operation."""
    # Setup mock response
    batch_response = MagicMock()
    batch_response.success = True
    mock_grpc_stub.BatchWrite.return_value = batch_response
    
    # Create batch operations
    operations = [
        BatchOperation(BatchOperation.Type.PUT, b"key1", b"value1"),
        BatchOperation(BatchOperation.Type.DELETE, b"key2")
    ]
    
    # Call batch_write
    success = client.batch_write(operations, sync=True)
    
    # Verify result
    assert success is True
    
    # Verify request
    mock_grpc_stub.BatchWrite.assert_called_once()
    request = mock_grpc_stub.BatchWrite.call_args[0][0]
    assert len(request.operations) == 2
    assert request.sync is True
    
    # Verify first operation (PUT)
    assert request.operations[0].key == b"key1"
    assert request.operations[0].value == b"value1"
    
    # Verify second operation (DELETE)
    assert request.operations[1].key == b"key2"


def test_transaction(client, mock_grpc_stub):
    """Test transaction operations."""
    # Setup mock responses
    begin_response = MagicMock()
    begin_response.transaction_id = "tx-123"
    mock_grpc_stub.BeginTransaction.return_value = begin_response
    
    commit_response = MagicMock()
    commit_response.success = True
    mock_grpc_stub.CommitTransaction.return_value = commit_response
    
    tx_get_response = MagicMock()
    tx_get_response.value = b"tx-value"
    tx_get_response.found = True
    mock_grpc_stub.TxGet.return_value = tx_get_response
    
    tx_put_response = MagicMock()
    tx_put_response.success = True
    mock_grpc_stub.TxPut.return_value = tx_put_response
    
    # Begin transaction
    tx = client.begin_transaction(read_only=False)
    assert tx._id == "tx-123"
    assert tx._read_only is False
    
    # Transaction operations
    value, found = tx.get(b"tx-key")
    assert value == b"tx-value"
    assert found is True
    
    success = tx.put(b"tx-key", b"new-value")
    assert success is True
    
    # Commit transaction
    tx.commit()
    
    # Verify requests
    mock_grpc_stub.BeginTransaction.assert_called_once()
    begin_request = mock_grpc_stub.BeginTransaction.call_args[0][0]
    assert begin_request.read_only is False
    
    mock_grpc_stub.TxGet.assert_called_once()
    get_request = mock_grpc_stub.TxGet.call_args[0][0]
    assert get_request.transaction_id == "tx-123"
    assert get_request.key == b"tx-key"
    
    mock_grpc_stub.TxPut.assert_called_once()
    put_request = mock_grpc_stub.TxPut.call_args[0][0]
    assert put_request.transaction_id == "tx-123"
    assert put_request.key == b"tx-key"
    assert put_request.value == b"new-value"
    
    mock_grpc_stub.CommitTransaction.assert_called_once()
    commit_request = mock_grpc_stub.CommitTransaction.call_args[0][0]
    assert commit_request.transaction_id == "tx-123"