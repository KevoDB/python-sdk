#!/usr/bin/env python3
"""
Suffix scan example for the Kevo Python SDK.

Demonstrates how to use suffix scans to retrieve keys that end with a specific suffix.
"""

import sys
import logging
from kevo import Client, ClientOptions, ScanOptions

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def insert_test_data(client):
    """Insert test data for suffix scan demonstrations."""
    test_data = [
        # File extensions
        (b"document_1.pdf", b"PDF Document"),
        (b"document_2.pdf", b"PDF Document"),
        (b"report_1.csv", b"CSV Report"),
        (b"report_2.csv", b"CSV Report"),
        (b"image_1.jpg", b"JPG Image"),
        (b"image_2.jpg", b"JPG Image"),
        (b"script_1.py", b"Python Script"),
        (b"script_2.py", b"Python Script"),
        # Categorized data
        (b"user:admin:1001", b"Admin User"),
        (b"user:admin:1002", b"Admin User"),
        (b"user:standard:2001", b"Standard User"),
        (b"user:standard:2002", b"Standard User"),
        (b"user:guest:3001", b"Guest User"),
        (b"user:guest:3002", b"Guest User"),
        # Timestamps
        (b"event:login:2023-01-01", b"Login Event"),
        (b"event:logout:2023-01-01", b"Logout Event"),
        (b"event:login:2023-01-02", b"Login Event"),
        (b"event:logout:2023-01-02", b"Logout Event")
    ]
    
    logger.info("Inserting test data...")
    for key, value in test_data:
        client.put(key, value, sync=True)
        logger.info(f"Added: {key.decode()} -> {value.decode()}")
    
    return test_data

def perform_suffix_scans(client):
    """Perform scans with different suffixes."""
    suffixes = [b".pdf", b".csv", b".jpg", b".py", b":2023-01-01", b":1001", b":2001", b":3001"]
    
    for suffix in suffixes:
        logger.info(f"\n=== Suffix Scan: {suffix.decode()} ===")
        scan_options = ScanOptions(suffix=suffix)
        scanner = client.scan(scan_options)
        
        count = 0
        for kv in scanner:
            count += 1
            logger.info(f"  {count:2d}. {kv.key.decode()} -> {kv.value.decode()}")
        
        logger.info(f"Total items with suffix '{suffix.decode()}': {count}")

def perform_combined_scans(client):
    """Perform scans with both prefix and suffix specified."""
    combinations = [
        (b"document", b".pdf", "Documents with PDF extension"),
        (b"report", b".csv", "Reports with CSV extension"),
        (b"user:admin", b":1001", "Admin user with ID 1001"),
        (b"event", b":2023-01-01", "Events from Jan 1, 2023")
    ]
    
    for prefix, suffix, description in combinations:
        logger.info(f"\n=== Combined Scan: Prefix={prefix.decode()}, Suffix={suffix.decode()} ===")
        logger.info(f"Description: {description}")
        
        scan_options = ScanOptions(prefix=prefix, suffix=suffix)
        scanner = client.scan(scan_options)
        
        count = 0
        for kv in scanner:
            count += 1
            logger.info(f"  {count:2d}. {kv.key.decode()} -> {kv.value.decode()}")
        
        logger.info(f"Total items matching both criteria: {count}")

def clean_up(client, test_data):
    """Clean up test data."""
    logger.info("\n=== Cleanup ===")
    for key, _ in test_data:
        client.delete(key)
    logger.info(f"Deleted {len(test_data)} test entries")

def main():
    """Demonstrate suffix scan operations."""
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
        perform_suffix_scans(client)
        perform_combined_scans(client)
        
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