# Kevo Python SDK

Python client for the Kevo key-value store.

## Installation

### From Source

```bash
# Clone the repository
git clone https://github.com/jeremytregunna/kevo.git
cd kevo/python-sdk

# Install using Poetry
make install
```

### Using pip

```bash
pip install kevo
```

## Getting Started

```python
from kevo import Client, ClientOptions

# Create a client with default options
client = Client()

# Or with custom options
options = ClientOptions(
    endpoint="localhost:50051",
    connect_timeout=5.0,
    request_timeout=10.0
)
client = Client(options)

# Connect to the server
client.connect()

# Basic operations
client.put(b"hello", b"world")
value, found = client.get(b"hello")
print(value.decode() if found else "Not found")  # Prints: world

# Scan operations
scan_options = ScanOptions(prefix=b"user:")
scanner = client.scan(scan_options)
for kv in scanner:
    print(f"Key: {kv.key.decode()}, Value: {kv.value.decode()}")

# Transaction example
tx = client.begin_transaction()
try:
    tx.put(b"key1", b"value1")
    tx.put(b"key2", b"value2")
    tx.commit()
except Exception as e:
    tx.rollback()
    raise e

# Don't forget to close the connection when done
client.close()
```

## API Reference

### Client

The main client class for interacting with the Kevo server.

```python
client = Client(options=None)
```

#### Methods

- `connect()`: Connect to the server
- `close()`: Close the connection
- `is_connected()`: Check if connected to the server
- `get(key)`: Get a value by key
- `put(key, value, sync=False)`: Store a key-value pair
- `delete(key, sync=False)`: Delete a key-value pair
- `batch_write(operations, sync=False)`: Perform multiple operations in a batch
- `scan(options=None)`: Scan keys in the database
- `begin_transaction(read_only=False)`: Begin a new transaction
- `get_stats()`: Get database statistics
- `compact(force=False)`: Trigger database compaction

### Transaction

Represents a database transaction.

#### Methods

- `commit()`: Commit the transaction
- `rollback()`: Roll back the transaction
- `get(key)`: Get a value within the transaction
- `put(key, value)`: Store a key-value pair within the transaction
- `delete(key)`: Delete a key-value pair within the transaction
- `scan(options=None)`: Scan keys within the transaction

## Development

### Prerequisites

- Python 3.8+
- Poetry
- Protocol Buffer compiler

### Setup

```bash
# Install dependencies
pip install -e .

# Generate Protocol Buffer code
python tools/generate_proto.py

# Run tests
pytest

# Run linters
black kevo
isort kevo
pylint kevo
```

## License

[MIT](https://opensource.org/licenses/MIT)