"""
OBM Service Main Entry Point.

Initializes the Order Book Microservice with:
- Crash recovery from WAL
- Order book and matching engine
- Redis consumer for order queue
- Event publisher for trades and snapshots
- Database persistence
"""

import asyncio
import os
import signal
import sys

from shared import create_redis_client

from .recovery import RecoveryManager
from .services.db_writer import DatabaseWriter
from .services.event_publisher import EventPublisher
from .services.order_consumer import OrderConsumer
from .wal import WAL

# Global state for graceful shutdown
shutdown_event = asyncio.Event()


async def main():
    """main entry point for OBM service"""
    
    print("=" * 60)
    print("OBM Service Starting...")
    print("=" * 60)
    
    # Get configuration from environment
    wal_file_path = os.getenv('WAL_FILE_PATH', '/app/data/wal.log')
    
    # Step 1: Crash Recovery System initiate
    print("\n[INIT] Step 1: CRS")
    recovery_manager = RecoveryManager(wal_file_path)
    order_book, matching_engine, last_lsn = recovery_manager.recover()
    
    # Step 2: Initialize WAL
    wal = WAL(wal_file_path)
    print(f"[INIT] WAL initialized at {wal_file_path}, LSN: {wal.current_lsn}")
    
    # Step 3: Connect to Redis- todo
    print("\n[INIT] Step 3: Connect to Redis")
    redis_client = await create_redis_client()
    print(f"[INIT] Connected to Redis")
    
    # Step 4: Initialize Database Writer
    print("\n[INIT] Step 4: Initialize Database")
    db_writer = DatabaseWriter()
    try:
        await db_writer.connect()
    except Exception as e:
        print(f"[INIT] Warning: Could not connect to database: {e}")
        print("[INIT] Continuing without database persistence...")
    
    # Step 5: Initialize Event Publisher
    print("\n[INIT] Step 5: Initialize Event Publisher")
    event_publisher = EventPublisher(redis_client, order_book)
    
    # Step 6: Initialize Order Consumer
    print("\n[INIT] Step 6: Initialize Order Consumer")
    order_consumer = OrderConsumer(
        redis_client,
        order_book,
        matching_engine,
        wal,
        event_publisher,
        db_writer  # passing database writer for persistence
    )
    
    # Step 7: Start background tasks
    print("\n[INIT] Step 7: Start Background Tasks")
    
    # Create tasks
    consumer_task = asyncio.create_task(order_consumer.start())
    snapshot_task = asyncio.create_task(event_publisher.start_snapshot_publisher())
    
    print("\n" + "=" * 60)
    print("OBM Service Ready!")
    print("=" * 60)
    print(f"Order Book State: {order_book}")
    print(f"Total Trades: {len(matching_engine.trades)}")
    print("Listening for orders on Redis Streams...")
    print("=" * 60 + "\n")
    
    # Setup signal handlers for graceful shutdown
    def signal_handler(sig, frame):
        print("\n[SHUTDOWN] Received shutdown signal")
        shutdown_event.set()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Wait for shutdown signal
    await shutdown_event.wait()
    
    # Graceful shutdown
    print("\n[SHUTDOWN] Initiating graceful shutdown...")
    
    # Stop consumers and publishers
    await order_consumer.stop()
    await event_publisher.stop_snapshot_publisher()
    
    # Wait for tasks to complete
    consumer_task.cancel()
    snapshot_task.cancel()
    
    try:
        await asyncio.gather(consumer_task, snapshot_task, return_exceptions=True)
    except asyncio.CancelledError:
        pass
    
    # Close WAL
    wal.close()
    print("[SHUTDOWN] WAL closed")
    
    # Close database connection
    await db_writer.disconnect()
    
    # Close Redis connection
    await redis_client.close()
    print("[SHUTDOWN] Redis connection closed")
    
    print("[SHUTDOWN] OBM Service stopped gracefully")
    print("=" * 60)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[SHUTDOWN] Keyboard interrupt received")
    except Exception as e:
        print(f"\n[ERROR] Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
