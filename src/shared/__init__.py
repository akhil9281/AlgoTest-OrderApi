"""
shared package for Order API.

contains common models, utilities, and constants used by both
the API service and OBM service.
"""

# Make models and constants easily importable
from .models import (
    OrderRecord,
    TradeRecord,
    CreateOrderRequest,
    ModifyOrderRequest,
    OrderResponse,
    TradeResponse,
    OrderBookSnapshot,
    OrderSide,
    OrderStatus
)

from .constants import (
    REDIS_ORDER_QUEUE,
    REDIS_TRADE_EVENTS,
    REDIS_SNAPSHOT_EVENTS,
    REDIS_OBM_CONSUMER_GROUP,
    REDIS_OBM_CONSUMER_NAME,
    OperationType,
    SNAPSHOT_INTERVAL_SECONDS,
    SNAPSHOT_DEPTH_LEVELS,
    ORDER_SIDE_BUY,
    ORDER_SIDE_SELL
)

from .redis_client import (
    create_redis_client,
    create_redis_pool,
    RedisClientManager,
    get_redis_url
)

__all__ = [
    # Models
    "OrderRecord",
    "TradeRecord",
    "CreateOrderRequest",
    "ModifyOrderRequest",
    "OrderResponse",
    "TradeResponse",
    "OrderBookSnapshot",
    "OrderSide",
    "OrderStatus",

    # Constants
    "REDIS_ORDER_QUEUE",
    "REDIS_TRADE_EVENTS",
    "REDIS_SNAPSHOT_EVENTS",
    "REDIS_OBM_CONSUMER_GROUP",
    "REDIS_OBM_CONSUMER_NAME",
    "OperationType",
    "SNAPSHOT_INTERVAL_SECONDS",
    "SNAPSHOT_DEPTH_LEVELS",
    "ORDER_SIDE_BUY",
    "ORDER_SIDE_SELL",
    # Redis client
    "create_redis_client",
    "create_redis_pool",
    "RedisClientManager",
    "get_redis_url"
]
