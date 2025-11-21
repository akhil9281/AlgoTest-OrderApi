"""
Shared data models and DTOs for the Order API.

This module contains all the data transfer objects used across
the API service and OBM service for consistency.
"""

from dataclasses import dataclass, field
from typing import Optional, List
from enum import Enum
from datetime import datetime
import uuid


class OrderSide(Enum):
    """Order side enum: BUY or SELL"""
    BUY = 1
    SELL = -1


class OrderStatus(Enum):
    """Order status enum"""
    OPEN = "OPEN"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"


@dataclass
class OrderRecord:
    """
    Internal representation of an order in the order book.
    Prices are stored as integers (paise) to avoid floating-point errors.
    """
    order_id: str
    side: int  # 1 for buy, -1 for sell
    price_paise: int  # Price in paise (multiply float price by 100)
    original_qty: int
    remaining_qty: int
    traded_qty: int = 0
    avg_traded_price_paise: int = 0  # Weighted average trade price
    status: str = OrderStatus.OPEN.value
    created_timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization"""
        return {
            "order_id": self.order_id,
            "side": self.side,
            "price_paise": self.price_paise,
            "original_qty": self.original_qty,
            "remaining_qty": self.remaining_qty,
            "traded_qty": self.traded_qty,
            "avg_traded_price_paise": self.avg_traded_price_paise,
            "status": self.status,
            "created_timestamp": self.created_timestamp,
            "updated_timestamp": self.updated_timestamp
        }

    @staticmethod
    def from_dict(data: dict) -> 'OrderRecord':
        """Create OrderRecord from dictionary"""
        return OrderRecord(**data)


@dataclass
class TradeRecord:
    """
    Represents a completed trade between two orders.
    """
    trade_id: str
    timestamp: str
    price_paise: int  # Execution price in paise
    qty: int  # Executed quantity
    bid_order_id: str  # Buy order ID
    ask_order_id: str  # Sell order ID

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization"""
        return {
            "trade_id": self.trade_id,
            "timestamp": self.timestamp,
            "price_paise": self.price_paise,
            "qty": self.qty,
            "bid_order_id": self.bid_order_id,
            "ask_order_id": self.ask_order_id
        }

    @staticmethod
    def from_dict(data: dict) -> 'TradeRecord':
        """Create TradeRecord from dictionary"""
        return TradeRecord(**data)


# API Request/Response Models (used by FastAPI)

@dataclass
class CreateOrderRequest:
    """
    Request payload for creating a new order.
    Accepts float price from API, will be converted to paise internally.
    """
    quantity: int
    price: float  # Will be converted to paise (price * 100)
    side: int  # 1 for buy, -1 for sell

    def validate(self) -> tuple[bool, Optional[str]]:
        """
        Validate request data.
        Returns: (is_valid, error_message)
        """
        if self.quantity <= 0:
            return False, "Quantity must be greater than 0"
        if self.price <= 0:
            return False, "Price must be greater than 0"
        if round(self.price, 2) != self.price:
            return False, "Price must be a multiple of 0.01"
        if self.side not in [1, -1]:
            return False, "Side must be 1 (buy) or -1 (sell)"
        return True, None

    def to_paise(self) -> int:
        """Convert float price to integer paise"""
        return int(round(self.price * 100))


@dataclass
class ModifyOrderRequest:
    """
    Request payload for modifying an existing order.
    Only price modification is supported.
    """
    updated_price: float

    def validate(self) -> tuple[bool, Optional[str]]:
        """Validate modification request"""
        if self.updated_price <= 0:
            return False, "Price must be greater than 0"
        if round(self.updated_price, 2) != self.updated_price:
            return False, "Price must be a multiple of 0.01"
        return True, None

    def to_paise(self) -> int:
        """Convert float price to integer paise"""
        return int(round(self.updated_price * 100))


@dataclass
class OrderResponse:
    """
    Response payload for order queries.
    Converts internal paise representation back to float for API.
    """
    order_price: float
    order_quantity: int
    average_traded_price: float
    traded_quantity: int
    order_alive: bool

    @staticmethod
    def from_order_record(order: OrderRecord) -> 'OrderResponse':
        """Convert internal OrderRecord to API response"""
        return OrderResponse(
            order_price=order.price_paise / 100.0,
            order_quantity=order.original_qty,
            average_traded_price=order.avg_traded_price_paise / 100.0 if order.avg_traded_price_paise > 0 else 0.0,
            traded_quantity=order.traded_qty,
            order_alive=(order.remaining_qty > 0 and order.status != OrderStatus.CANCELLED.value)
        )


@dataclass
class TradeResponse:
    """
    Response payload for trade queries.
    Converts paise to float for API.
    """
    unique_id: str
    execution_timestamp: str
    price: float
    qty: int
    bid_order_id: str
    ask_order_id: str

    @staticmethod
    def from_trade_record(trade: TradeRecord) -> 'TradeResponse':
        """Convert internal TradeRecord to API response"""
        return TradeResponse(
            unique_id=trade.trade_id,
            execution_timestamp=trade.timestamp,
            price=trade.price_paise / 100.0,
            qty=trade.qty,
            bid_order_id=trade.bid_order_id,
            ask_order_id=trade.ask_order_id
        )


@dataclass
class OrderBookSnapshot:
    """
    Order book snapshot with top 5 levels of bids and asks.
    Format: [[price, quantity], [price, quantity], ...]
    """
    timestamp: str
    bids: List[List[float]]  # [[price, qty], ...] top 5, sorted descending
    asks: List[List[float]]  # [[price, qty], ...] top 5, sorted ascending

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "timestamp": self.timestamp,
            "bids": self.bids,
            "asks": self.asks
        }
