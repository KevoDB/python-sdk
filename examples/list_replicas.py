#!/usr/bin/env python3
"""
Example script to list replica information using Kevo's node info API.

Demonstrates:
- Connecting to a Kevo server
- Getting node info and listing replicas
"""

import sys
import logging
import argparse
from kevo import Client, ClientOptions, NodeRole

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """Display node information and list any replicas."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="List replication information from Kevo server")
    parser.add_argument("--endpoint", type=str, default="localhost:50051", 
                        help="Kevo server endpoint (default: localhost:50051)")
    args = parser.parse_args()
    
    endpoint = args.endpoint
    
    # Create client with default options
    client = Client(ClientOptions(endpoint=endpoint))
    
    try:
        # Connect to the server
        logger.info(f"Connecting to Kevo server at {endpoint}...")
        client.connect()
        logger.info("Connected successfully")
        
        # Get node information
        node_info = client.get_node_info()
        
        if not node_info:
            logger.info("No node information available")
            return 0
            
        logger.info(f"Connected to {node_info.node_role.value} node")
        
        if node_info.node_role == NodeRole.STANDALONE:
            logger.info("This is a standalone node (no replication)")
            
        elif node_info.node_role == NodeRole.PRIMARY:
            replicas = node_info.replicas
            logger.info(f"This is a primary node with {len(replicas)} replica(s)")
            
            if not replicas:
                logger.info("No replicas found")
            else:
                for i, replica in enumerate(replicas, 1):
                    logger.info(f"Replica #{i}:")
                    logger.info(f"  Address: {replica.address}")
                    logger.info(f"  Available: {replica.available}")
                    logger.info(f"  Last sequence: {replica.last_sequence}")
                    if replica.region:
                        logger.info(f"  Region: {replica.region}")
                    if replica.meta:
                        logger.info(f"  Metadata: {replica.meta}")
                        
        elif node_info.node_role == NodeRole.REPLICA:
            logger.info(f"This is a replica node")
            logger.info(f"Primary node: {node_info.primary_address}")
            logger.info(f"Last sequence: {node_info.last_sequence}")
            logger.info(f"Read-only: {node_info.read_only}")
        
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