#!/usr/bin/env python3
"""
Basic operations example for the Kevo Python SDK.

Demonstrates PUT, GET, DELETE operations.
"""

import sys
import logging
from kevo import Client, ClientOptions

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """Demonstrate basic operations."""
    # Create client with default options
    client = Client(ClientOptions(endpoint="localhost:50051"))
    
    try:
        # Connect to the server
        logger.info("Connecting to Kevo server...")
        client.connect()
        logger.info("Connected successfully")
        
        # PUT operation
        logger.info("\n=== PUT Operations ===")
        test_data = [
            (b"user:1001", b"John Doe"),
            (b"user:1002", b"Jane Smith"),
            (b"config:theme", b"dark"),
            (b"config:language", b"en-US")
        ]
        
        for key, value in test_data:
            success = client.put(key, value, sync=True)
            logger.info(f"PUT {key.decode()} -> {value.decode()}: {'Success' if success else 'Failed'}")
        
        # GET operation
        logger.info("\n=== GET Operations ===")
        for key, _ in test_data:
            value, found = client.get(key)
            if found:
                logger.info(f"GET {key.decode()}: Found -> {value.decode()}")
            else:
                logger.info(f"GET {key.decode()}: Not found")
        
        # GET non-existent key
        non_existent = b"user:9999"
        value, found = client.get(non_existent)
        logger.info(f"GET {non_existent.decode()}: {'Found -> ' + value.decode() if found else 'Not found'}")
        
        # DELETE operation
        logger.info("\n=== DELETE Operations ===")
        # Delete first key
        delete_key = test_data[0][0]
        success = client.delete(delete_key)
        logger.info(f"DELETE {delete_key.decode()}: {'Success' if success else 'Failed'}")
        
        # Verify deletion
        value, found = client.get(delete_key)
        logger.info(f"GET after DELETE {delete_key.decode()}: {'Found -> ' + value.decode() if found else 'Not found'}")
        
        # Clean up remaining test data
        logger.info("\n=== Cleanup ===")
        for key, _ in test_data[1:]:  # Skip the first one which we already deleted
            client.delete(key)
            logger.info(f"Deleted {key.decode()}")
        
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