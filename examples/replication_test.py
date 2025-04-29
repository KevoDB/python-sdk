#!/usr/bin/env python3
"""
Replication test example for the Kevo Python SDK.

Demonstrates:
- Adding a configurable number of keys to the database
- Using a transaction for up to 200 keys
- The remainder using individual puts
- Automatic routing of writes to primary nodes
"""

import sys
import logging
import time
import argparse
from kevo import Client, ClientOptions

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """Add a configurable number of keys to test replication."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Test Kevo replication by adding keys")
    parser.add_argument("--keys", type=int, default=1000, help="Number of keys to add (default: 1000)")
    parser.add_argument("--endpoint", type=str, default="localhost:50051", help="Kevo server endpoint (default: localhost:50051)")
    args = parser.parse_args()

    total_keys = args.keys
    endpoint = args.endpoint

    # Create client with default options
    # The client will automatically handle topology discovery and routing
    client = Client(ClientOptions(endpoint=endpoint))

    try:
        # Connect to the server
        logger.info(f"Connecting to Kevo server at {endpoint}...")
        client.connect()
        logger.info("Connected successfully")

        # Add the keys
        start_time = time.time()

        # Max transaction count to 200
        tx_count = min(20, total_keys)
        # Individual keys are the difference between total and transaction keys
        individual_count = total_keys - tx_count

        # First handle individual puts
        logger.info(f"Adding {individual_count} keys with individual puts...")

        for i in range(individual_count):
            key = f"repltest:individual:{i}".encode()
            value = f"value-{i}".encode()
            success = client.put(key, value, sync=True)
            if i % 100 == 0 or i == individual_count - 1:
                logger.info(f"Progress: {i+1}/{individual_count} individual puts completed")

        logger.info(f"Completed {individual_count} individual puts")

        # Then handle transaction keys
        logger.info(f"Adding {tx_count} keys in a transaction...")

        # Start a transaction
        tx = client.begin_transaction()

        for i in range(tx_count):
            key = f"repltest:transaction:{i}".encode()
            value = f"tx-value-{i}".encode()
            tx.put(key, value)
            if i % 100 == 0 or i == tx_count - 1:
                logger.info(f"Progress: {i+1}/{tx_count} transaction puts added")

        # Commit the transaction
        logger.info("Committing transaction...")
        tx.commit()
        logger.info("Transaction committed successfully")

        end_time = time.time()
        duration = end_time - start_time

        # Summary
        logger.info("\n=== Summary ===")
        logger.info(f"Total keys added: {total_keys}")
        logger.info(f"- Individual puts: {individual_count}")
        logger.info(f"- Transaction puts: {tx_count}")
        logger.info(f"Total duration: {duration:.2f} seconds")
        logger.info(f"Average rate: {total_keys/duration:.2f} keys/second")

        # Verify a few random keys
        logger.info("\n=== Verification ===")
        keys_to_verify = [
            f"repltest:individual:{individual_count//4}".encode(),
            f"repltest:individual:{individual_count//2}".encode(),
            f"repltest:transaction:{tx_count//4}".encode(),
            f"repltest:transaction:{tx_count//2}".encode()
        ]

        for key in keys_to_verify:
            value, found = client.get(key)
            if found:
                logger.info(f"Verified: {key.decode()} -> {value.decode()}")
            else:
                logger.error(f"Verification failed: {key.decode()} not found!")

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
