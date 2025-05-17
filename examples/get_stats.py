#!/usr/bin/env python3
"""
Database statistics example for the Kevo Python SDK.

Demonstrates how to retrieve and display database statistics.
"""

import sys
import logging
import inspect
import kevo
from kevo import Client, ClientOptions, Stats

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """Demonstrate getting database statistics."""
    # Get the SDK version
    version = getattr(kevo, "__version__", "Not found")
    logger.info(f"Kevo SDK Version: {version}")
    
    # Create client with default options
    client = Client(ClientOptions(endpoint="localhost:50051"))
    
    try:
        # Connect to the server
        logger.info("Connecting to Kevo server...")
        client.connect()
        logger.info("Connected successfully")
        
        # Get database statistics
        logger.info("\n=== Database Statistics ===")
        stats = client.get_stats()
        
        # Display statistics
        logger.info(f"Key Count: {stats.key_count}")
        logger.info(f"Storage Size: {stats.storage_size} bytes")
        logger.info(f"Memtable Count: {stats.memtable_count}")
        logger.info(f"SSTable Count: {stats.sstable_count}")
        logger.info(f"Write Amplification: {stats.write_amplification:.2f}")
        logger.info(f"Read Amplification: {stats.read_amplification:.2f}")
        
        # Alternatively, use the string representation
        logger.info("\nStats Summary:")
        logger.info(str(stats))
        
        # Try to get replica statistics
        logger.info("\n=== Replica Statistics ===")
        
        try:
            # Check if the client supports replicas
            if hasattr(client, 'get_stats') and 'read_from_replicas' in inspect.signature(client.get_stats).parameters:
                replica_stats = client.get_stats(read_from_replicas=True)
                logger.info("Replica Stats:")
                logger.info(str(replica_stats))
                
                # Compare with primary stats
                logger.info("\nReplication lag statistics:")
                lag = abs(stats.key_count - replica_stats.key_count)
                logger.info(f"Estimated key count difference: {lag}")
            else:
                logger.info(f"Current SDK version ({version}) doesn't fully support replica statistics.")
                logger.info("Please check documentation for replica feature availability.")
        except Exception as e:
            logger.info(f"Could not get replica stats: {e}")
        
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