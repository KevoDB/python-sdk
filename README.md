# 🔑 Python-Kevo

[![PyPI version](https://img.shields.io/pypi/v/python-kevo.svg)](https://pypi.org/project/python-kevo/)
[![Python versions](https://img.shields.io/pypi/pyversions/python-kevo.svg)](https://pypi.org/project/python-kevo/)
[![License](https://img.shields.io/github/license/KevoDB/python-sdk.svg)](LICENSE)

High-performance Python client for the [Kevo](https://github.com/KevoDB/kevo) key-value store.

## ✨ Features

- Simple and intuitive API
- Efficient binary protocol (gRPC)
- Transaction support
- Range, prefix, and suffix scans
- Batch operations

## 🚀 Installation

```bash
pip install python-kevo
```

Or install from source:

```bash
git clone https://github.com/KevoDB/python-sdk.git
cd python-sdk
poetry install
```

## 🏁 Quick Start

```python
from kevo import Client, ClientOptions, ScanOptions

# Create a client
client = Client(ClientOptions(endpoint="localhost:50051"))
client.connect()

# Basic operations
client.put(b"hello", b"world")
value, found = client.get(b"hello")
print(value.decode() if found else "Not found")  # Prints: world

# Scan with prefix
for kv in client.scan(ScanOptions(prefix=b"user:")):
    print(f"Key: {kv.key.decode()}, Value: {kv.value.decode()}")
    
# Scan with suffix
for kv in client.scan(ScanOptions(suffix=b".jpg")):
    print(f"Image: {kv.key.decode()}, Description: {kv.value.decode()}")

# Use transactions
tx = client.begin_transaction()
try:
    tx.put(b"key1", b"value1")
    tx.put(b"key2", b"value2")
    tx.commit()
except Exception as e:
    tx.rollback()
    raise e
finally:
    client.close()
```

## 📖 API Reference

### Client

```python
client = Client(options=None)
```

#### Core Methods

| Method | Description |
|--------|-------------|
| `connect()` | Connect to the server |
| `close()` | Close the connection |
| `get(key)` | Get a value by key |
| `put(key, value, sync=False)` | Store a key-value pair |
| `delete(key, sync=False)` | Delete a key-value pair |

#### Advanced Features

| Method | Description |
|--------|-------------|
| `batch_write(operations, sync=False)` | Perform multiple operations in a batch |
| `scan(options=None)` | Scan keys in the database |
| `begin_transaction(read_only=False)` | Begin a new transaction |
| `get_stats()` | Get database statistics |
| `compact(force=False)` | Trigger database compaction |

### Transaction

#### Methods

| Method | Description |
|--------|-------------|
| `commit()` | Commit the transaction |
| `rollback()` | Roll back the transaction |
| `get(key)` | Get a value within the transaction |
| `put(key, value)` | Store a key-value pair within the transaction |
| `delete(key)` | Delete a key-value pair within the transaction |
| `scan(options=None)` | Scan keys within the transaction |

## 🛠️ Development

### Prerequisites

- Python 3.8+
- Poetry
- Protocol Buffer compiler

### Setup

```bash
# Install dependencies
poetry install

# Generate Protocol Buffer code
python tools/generate_proto.py

# Run tests
pytest

# Run linters
black kevo
isort kevo
pylint kevo
```

## 📄 License

[MIT](https://opensource.org/licenses/MIT)