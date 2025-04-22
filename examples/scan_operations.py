#!/usr/bin/env python3
"""
Scan operations example for the Kevo Python SDK.

Demonstrates different types of scans:
- Full scan
- Prefix scan
- Range scan
"""

import sys
import logging
from kevo import Client, ClientOptions, ScanOptions

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def insert_test_data(client):
    """Insert test data for scan demonstrations."""
    test_data = [
        # User data
        (b"user:1001", b"John Doe"),
        (b"user:1002", b"Jane Smith"),
        (b"user:1003", b"Bob Johnson"),
        (b"user:1004", b"Alice Brown"),
        # Config data
        (b"config:theme", b"dark"),
        (b"config:language", b"en-US"),
        (b"config:notifications", b"enabled"),
        # Product data
        (b"product:101", b"Laptop"),
        (b"product:102", b"Smartphone"),
        (b"product:103", b"Tablet"),
        # Log entries with timestamp-like keys for range scans
        (b"log:2023-01-01", b"System started"),
        (b"log:2023-01-15", b"User login"),
        (b"log:2023-02-01", b"Configuration updated"),
        (b"log:2023-02-15", b"Error detected"),
        (b"log:2023-03-01", b"System maintenance")
    ]
    
    logger.info("Inserting test data...")
    for key, value in test_data:
        client.put(key, value, sync=True)
        logger.info(f"Added: {key.decode()} -> {value.decode()}")
    
    return test_data

def perform_full_scan(client):
    """Perform a full scan of all key-value pairs."""
    logger.info("\n=== Full Scan ===")
    scanner = client.scan()
    
    count = 0
    for kv in scanner:
        count += 1
        logger.info(f"  {count:2d}. {kv.key.decode()} -> {kv.value.decode()}")
    
    logger.info(f"Total items found: {count}")

def perform_prefix_scans(client):
    """Perform scans with different prefixes."""
    prefixes = [b"user:", b"config:", b"product:", b"log:"]
    
    for prefix in prefixes:
        logger.info(f"\n=== Prefix Scan: {prefix.decode()} ===")
        scan_options = ScanOptions(prefix=prefix)
        scanner = client.scan(scan_options)
        
        count = 0
        for kv in scanner:
            count += 1
            logger.info(f"  {count:2d}. {kv.key.decode()} -> {kv.value.decode()}")
        
        logger.info(f"Total items with prefix '{prefix.decode()}': {count}")

def perform_range_scans(client):
    """Perform range scans with different start and end keys."""
    # Range scan 1: All user keys from 1002 to 1003 (inclusive-exclusive)
    logger.info("\n=== Range Scan: user:1002 to user:1004 ===")
    scan_options = ScanOptions(start_key=b"user:1002", end_key=b"user:1004")
    scanner = client.scan(scan_options)
    
    count = 0
    for kv in scanner:
        count += 1
        logger.info(f"  {count:2d}. {kv.key.decode()} -> {kv.value.decode()}")
    
    logger.info(f"Total items in range: {count}")
    
    # Range scan 2: Log entries from January to February 2023
    logger.info("\n=== Range Scan: Log entries from Jan to Feb 2023 ===")
    scan_options = ScanOptions(start_key=b"log:2023-01", end_key=b"log:2023-03")
    scanner = client.scan(scan_options)
    
    count = 0
    for kv in scanner:
        count += 1
        logger.info(f"  {count:2d}. {kv.key.decode()} -> {kv.value.decode()}")
    
    logger.info(f"Total log entries in range: {count}")

def perform_limited_scan(client):
    """Perform a scan with a result limit."""
    logger.info("\n=== Limited Scan (max 3 results) ===")
    scan_options = ScanOptions(limit=3)
    scanner = client.scan(scan_options)
    
    count = 0
    for kv in scanner:
        count += 1
        logger.info(f"  {count:2d}. {kv.key.decode()} -> {kv.value.decode()}")
    
    logger.info(f"Total items returned (limited to 3): {count}")

def clean_up(client, test_data):
    """Clean up test data."""
    logger.info("\n=== Cleanup ===")
    for key, _ in test_data:
        client.delete(key)
    logger.info(f"Deleted {len(test_data)} test entries")

def main():
    """Demonstrate scan operations."""
    # Create client with default options
    client = Client(ClientOptions(endpoint="localhost:50051"))
    
    try:
        # Connect to the server
        logger.info("Connecting to Kevo server...")
        client.connect()
        logger.info("Connected successfully")
        
        # Insert test data
        test_data = insert_test_data(client)
        
        # Perform various scan operations
        perform_full_scan(client)
        perform_prefix_scans(client)
        perform_range_scans(client)
        perform_limited_scan(client)
        
        # Clean up
        clean_up(client, test_data)
        
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