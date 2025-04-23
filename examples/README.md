# Kevo Python SDK Examples

This directory contains example applications demonstrating how to use the Kevo Python SDK.

## Prerequisites

Before running the examples, make sure:

1. The Kevo server is running on `localhost:50051`:
   ```
   ./kevo -server /path/to/db
   ```

2. The Python SDK is installed:
   ```
   cd python-sdk
   pip install -e .
   ```

## Available Examples

### Basic Operations

Demonstrates basic PUT, GET, and DELETE operations:

```
python examples/basic_operations.py
```

### Scan Operations

Demonstrates various scan operations including full scans, prefix scans, and range scans:

```
python examples/scan_operations.py
```

### Suffix Scan Operations

Demonstrates suffix scan operations to retrieve keys that end with specific suffixes:

```
python examples/suffix_scan_example.py
```

### Transaction Operations

Demonstrates transaction functionality including read-write transactions, read-only transactions, commit, rollback, and isolation:

```
python examples/transaction_operations.py
```

## Usage Notes

- All examples run against a Kevo server at `localhost:50051` by default
- Examples clean up after themselves, so the database should remain in its original state
- Detailed logs show what's happening at each step