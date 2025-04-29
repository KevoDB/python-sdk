#!/usr/bin/env python3
"""
Example script for reading keys from a Kevo server.

Demonstrates:
- Connecting to any Kevo node (primary or replica)
- Reading keys that were set by the replication_test.py script
"""

import sys
import logging
import argparse
from kevo import Client, ClientOptions, ScanOptions

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """Read keys from a Kevo server."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Read keys from a Kevo server")
    parser.add_argument("--endpoint", type=str, default="localhost:50052",
                        help="Kevo server endpoint (default: localhost:50052)")
    parser.add_argument("--count", type=int, default=10,
                        help="Number of keys to read from each type (default: 10)")
    args = parser.parse_args()

    endpoint = args.endpoint
    count = args.count

    # Create client with default options
    # The client will automatically handle replication topology discovery and routing
    client = Client(ClientOptions(endpoint=endpoint))

    try:
        # Connect to the server
        logger.info(f"Connecting to Kevo server at {endpoint}...")
        client.connect()
        logger.info("Connected successfully")

        # Read individual keys
        logger.info(f"\n=== Reading individual keys ===")
        for i in range(count):
            key = f"repltest:individual:{i}".encode()
            value, found = client.get(key)
            if found:
                logger.info(f"Read: {key.decode()} -> {value.decode()}")
            else:
                logger.warning(f"Key not found: {key.decode()}")
        key = f"repltest:individual:{count}".encode()
        value, found = client.get(key)
        logger.info(f"Last Read: {value.decode()}")

        # Read transaction keys
        logger.info(f"\n=== Reading transaction keys ===")
        for i in range(count):
            key = f"repltest:transaction:{i}".encode()
            value, found = client.get(key)
            if found:
                logger.info(f"Read: {key.decode()} -> {value.decode()}")
            else:
                logger.warning(f"Key not found: {key.decode()}")

        # Count total keys with prefix
        logger.info(f"\n=== Key Statistics ===")
        prefix_scan_options = ScanOptions(prefix=b"repltest:individual:")
        individual_count = sum(1 for _ in client.scan(options=prefix_scan_options))
        logger.info(f"Total individual keys found: {individual_count}")

        prefix_scan_options = ScanOptions(prefix=b"repltest:transaction:")
        transaction_count = sum(1 for _ in client.scan(options=prefix_scan_options))
        logger.info(f"Total transaction keys found: {transaction_count}")
        logger.info(f"Total replicated keys: {individual_count + transaction_count}")

    except Exception as e:
        logger.error(f"Error: {e}")
        return 1
    finally:
        # Always close the connection
        client.close()
        logger.info("Connection closed")

    return 0

if __name__ == "__main__":
    sys.exit(main())
