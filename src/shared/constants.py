"""
Shared constants used across the Order API services.
"""

# Redis Channel Names
REDIS_ORDER_QUEUE = "order_queue"  # Redis Stream for order requests
REDIS_TRADE_EVENTS = "trade_events"  # Redis Pub/Sub for trade notifications
REDIS_SNAPSHOT_EVENTS = "snapshot_events"  # Redis Pub/Sub for order book snapshots

# Redis Consumer Group
REDIS_OBM_CONSUMER_GROUP = "obm_group"
REDIS_OBM_CONSUMER_NAME = "obm_consumer"

# Operation Types (for order queue messages)
class OperationType:
    CREATE = "CREATE"
    MODIFY = "MODIFY"
    CANCEL = "CANCEL"
    FETCH = "FETCH"
    FETCH_ALL = "FETCH_ALL"

# Order Book Configuration
SNAPSHOT_INTERVAL_SECONDS = 1  # Send order book snapshot every 1 second
SNAPSHOT_DEPTH_LEVELS = 5  # Top 5 bid/ask levels in snapshot

# WAL Configuration
WAL_OPERATION_INSERT = "INSERT"
WAL_OPERATION_UPDATE = "UPDATE"
WAL_OPERATION_DELETE = "DELETE"
WAL_TABLE_ORDER = "ORDER"
WAL_TABLE_TRADE = "TRADE"

# Price Conversion
PAISE_MULTIPLIER = 100  # Convert rupees to paise (or dollars to cents)

# Order Side
ORDER_SIDE_BUY = 1
ORDER_SIDE_SELL = -1

# Database Table Names
DB_TABLE_ORDERS = "orders"
DB_TABLE_TRADES = "trades"
