#!/usr/bin/env python3
"""
Transaction operations example for the Kevo Python SDK.

Demonstrates:
- Read-write transactions (commit and rollback)
- Read-only transactions
- Transaction isolation
"""

import sys
import logging
import time
from threading import Thread
from kevo import Client, ClientOptions, ScanOptions

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def demonstrate_transaction_commit(client):
    """Demonstrate a successful transaction commit."""
    logger.info("\n=== Transaction Commit Example ===")
    
    # Create test data that will be modified in the transaction
    init_key = b"tx_demo:initial"
    init_value = b"initial_value"
    client.put(init_key, init_value, sync=True)
    logger.info(f"Initial state: {init_key.decode()} -> {init_value.decode()}")
    
    # Start a transaction
    logger.info("Beginning transaction...")
    tx = client.begin_transaction()
    
    try:
        # Verify we can read the initial value in the transaction
        value, found = tx.get(init_key)
        logger.info(f"In transaction - GET {init_key.decode()}: {'Found -> ' + value.decode() if found else 'Not found'}")
        
        # Make multiple changes in the transaction
        tx.put(init_key, b"modified_in_transaction")
        tx.put(b"tx_demo:new1", b"new_value_1")
        tx.put(b"tx_demo:new2", b"new_value_2")
        logger.info("Made 3 changes in transaction")
        
        # Verify the change is visible within the transaction
        value, found = tx.get(init_key)
        logger.info(f"In transaction after PUT - GET {init_key.decode()}: {'Found -> ' + value.decode() if found else 'Not found'}")
        
        # But not visible outside the transaction yet
        value, found = client.get(init_key)
        logger.info(f"Outside transaction - GET {init_key.decode()}: {'Found -> ' + value.decode() if found else 'Not found'}")
        
        # Commit the transaction
        logger.info("Committing transaction...")
        tx.commit()
        logger.info("Transaction committed successfully")
        
        # Verify changes are visible after commit
        value, found = client.get(init_key)
        logger.info(f"After commit - GET {init_key.decode()}: {'Found -> ' + value.decode() if found else 'Not found'}")
        
        value, found = client.get(b"tx_demo:new1")
        logger.info(f"After commit - GET tx_demo:new1: {'Found -> ' + value.decode() if found else 'Not found'}")
        
        # Clean up
        client.delete(init_key)
        client.delete(b"tx_demo:new1")
        client.delete(b"tx_demo:new2")
        
    except Exception as e:
        logger.error(f"Transaction error: {e}")
        if tx:
            try:
                tx.rollback()
                logger.info("Transaction rolled back due to error")
            except:
                pass

def demonstrate_transaction_rollback(client):
    """Demonstrate a transaction rollback."""
    logger.info("\n=== Transaction Rollback Example ===")
    
    # Create test data
    key = b"tx_rollback:key"
    original_value = b"original_value"
    client.put(key, original_value, sync=True)
    logger.info(f"Initial state: {key.decode()} -> {original_value.decode()}")
    
    # Start a transaction
    logger.info("Beginning transaction...")
    tx = client.begin_transaction()
    
    try:
        # Make changes in the transaction
        tx.put(key, b"modified_value_to_be_rolled_back")
        tx.put(b"tx_rollback:new", b"new_value_to_be_rolled_back")
        logger.info("Made changes in transaction")
        
        # Verify the change is visible within the transaction
        value, found = tx.get(key)
        logger.info(f"In transaction - GET {key.decode()}: {'Found -> ' + value.decode() if found else 'Not found'}")
        
        # Rollback the transaction
        logger.info("Rolling back transaction...")
        tx.rollback()
        logger.info("Transaction rolled back successfully")
        
        # Verify changes are not visible after rollback
        value, found = client.get(key)
        logger.info(f"After rollback - GET {key.decode()}: {'Found -> ' + value.decode() if found else 'Not found'}")
        
        value, found = client.get(b"tx_rollback:new")
        logger.info(f"After rollback - GET tx_rollback:new: {'Found -> ' + value.decode() if found else 'Not found'}")
        
        # Clean up
        client.delete(key)
        
    except Exception as e:
        logger.error(f"Transaction error: {e}")
        if tx:
            try:
                tx.rollback()
            except:
                pass

def demonstrate_readonly_transaction(client):
    """Demonstrate a read-only transaction."""
    logger.info("\n=== Read-Only Transaction Example ===")
    
    # Create test data
    test_data = [
        (b"ro_tx:key1", b"value1"),
        (b"ro_tx:key2", b"value2"),
        (b"ro_tx:key3", b"value3")
    ]
    
    for key, value in test_data:
        client.put(key, value, sync=True)
        logger.info(f"Added: {key.decode()} -> {value.decode()}")
    
    # Start a read-only transaction
    logger.info("Beginning read-only transaction...")
    tx = client.begin_transaction(read_only=True)
    
    try:
        # Read data in the transaction
        logger.info("Reading data in read-only transaction:")
        for key, _ in test_data:
            value, found = tx.get(key)
            logger.info(f"  GET {key.decode()}: {'Found -> ' + value.decode() if found else 'Not found'}")
        
        # Try to make a write operation (should fail)
        logger.info("Attempting to write in read-only transaction (should fail):")
        try:
            tx.put(b"ro_tx:key1", b"new_value")
            logger.info("Put operation succeeded (unexpected!)")
        except Exception as e:
            logger.info(f"Put operation failed as expected: {e}")
        
        # Perform a scan in the transaction
        logger.info("Scanning in read-only transaction:")
        scan_options = ScanOptions(prefix=b"ro_tx:")
        scanner = tx.scan(scan_options)
        
        count = 0
        for kv in scanner:
            count += 1
            logger.info(f"  {count}. {kv.key.decode()} -> {kv.value.decode()}")
        
        # Commit the read-only transaction
        logger.info("Committing read-only transaction...")
        tx.commit()
        logger.info("Read-only transaction committed")
        
        # Clean up
        for key, _ in test_data:
            client.delete(key)
        
    except Exception as e:
        logger.error(f"Transaction error: {e}")
        if tx:
            try:
                tx.rollback()
            except:
                pass

def run_concurrent_transactions(client):
    """Demonstrate concurrent transactions and isolation."""
    logger.info("\n=== Concurrent Transactions Example ===")
    
    # Set up test data
    counter_key = b"concurrent:counter"
    client.put(counter_key, b"0", sync=True)
    logger.info(f"Initial {counter_key.decode()} = 0")
    
    # Flag to signal thread completion
    results = {"tx1_value": None, "tx2_value": None, "final_value": None}
    
    def transaction1():
        """First transaction: increment counter."""
        try:
            tx = client.begin_transaction()
            logger.info("TX1: Started")
            
            # Read current value
            value, found = tx.get(counter_key)
            if found:
                current = int(value.decode())
                logger.info(f"TX1: Read counter = {current}")
            else:
                current = 0
                logger.info("TX1: Counter not found, using 0")
            
            # Simulate some processing time
            time.sleep(1)
            
            # Increment and update
            new_value = current + 1
            tx.put(counter_key, str(new_value).encode())
            logger.info(f"TX1: Incremented counter to {new_value}")
            
            # Simulate more processing time before commit
            time.sleep(1)
            
            # Commit
            tx.commit()
            logger.info("TX1: Committed")
            results["tx1_value"] = new_value
            
        except Exception as e:
            logger.error(f"TX1 error: {e}")
            if tx:
                try:
                    tx.rollback()
                    logger.info("TX1: Rolled back due to error")
                except:
                    pass
    
    def transaction2():
        """Second transaction: also increment counter."""
        try:
            # Wait a bit for TX1 to start but not commit
            time.sleep(0.5)
            
            tx = client.begin_transaction()
            logger.info("TX2: Started")
            
            # Read current value
            value, found = tx.get(counter_key)
            if found:
                current = int(value.decode())
                logger.info(f"TX2: Read counter = {current}")
            else:
                current = 0
                logger.info("TX2: Counter not found, using 0")
            
            # Increment and update
            new_value = current + 1
            tx.put(counter_key, str(new_value).encode())
            logger.info(f"TX2: Incremented counter to {new_value}")
            
            # Commit - this should wait for TX1 to complete
            tx.commit()
            logger.info("TX2: Committed")
            results["tx2_value"] = new_value
            
        except Exception as e:
            logger.error(f"TX2 error: {e}")
            if tx:
                try:
                    tx.rollback()
                    logger.info("TX2: Rolled back due to error")
                except:
                    pass
    
    # Start both transactions
    t1 = Thread(target=transaction1)
    t2 = Thread(target=transaction2)
    
    t1.start()
    t2.start()
    
    # Wait for both to finish
    t1.join()
    t2.join()
    
    # Check final value
    value, found = client.get(counter_key)
    if found:
        final_value = int(value.decode())
        logger.info(f"Final counter value: {final_value}")
        results["final_value"] = final_value
    
    # Analyze results
    logger.info("\nTransaction Isolation Analysis:")
    logger.info(f"TX1 attempted to set value to: {results['tx1_value']}")
    logger.info(f"TX2 attempted to set value to: {results['tx2_value']}")
    logger.info(f"Final value: {results['final_value']}")
    
    if results["final_value"] == 2:
        logger.info("Correct result: Both transactions were properly serialized")
    else:
        logger.info("Unexpected result: Transaction isolation might not be working correctly")
    
    # Clean up
    client.delete(counter_key)

def main():
    """Demonstrate transaction operations."""
    # Create client with default options
    client = Client(ClientOptions(endpoint="localhost:50051"))
    
    try:
        # Connect to the server
        logger.info("Connecting to Kevo server...")
        client.connect()
        logger.info("Connected successfully")
        
        # Run demonstrations
        demonstrate_transaction_commit(client)
        demonstrate_transaction_rollback(client)
        demonstrate_readonly_transaction(client)
        run_concurrent_transactions(client)
        
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