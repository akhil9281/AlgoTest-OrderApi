"""
Order Book implementation using SortedDict for price levels and deque for time priority.

core data structure for maintaining bids and asks with O(1) amortized time complexity for order matching operations.
"""

from sortedcontainers import SortedDict
from collections import deque
from typing import Optional, List, Tuple, Dict
from shared.models import OrderRecord, OrderStatus


class OrderBook:
    """
    Order Book DS implementation.
    
    uses SortedDict to maintain price levels sorted, and deque for FIFO ordering
    within each price level (time priority).
    
    Structure:
    - bids: SortedDict{price: deque([order1, order2, ...])}  # Descending order
    - asks: SortedDict{price: deque([order1, order2, ...])}  # Ascending order
    """
    
    def __init__(self):
        # Bids: higher prices first (reverse order)
        self.bids: SortedDict[int, deque] = SortedDict()
        
        # Asks: lower prices first (normal order)
        self.asks: SortedDict[int, deque] = SortedDict()
        
        # Fast lookup by order_id
        self.orders: Dict[str, OrderRecord] = {}
    
    def add_order(self, order: OrderRecord) -> None:
        """
        add a new order to the order book.
        
        Args:
            order: OrderRecord to add
        """
        # Add to lookup dict
        self.orders[order.order_id] = order
        
        # Determine which side (bids or asks)
        book = self.bids if order.side == 1 else self.asks
        price = order.price_paise
        
        # Create price level if it doesn't exist
        if price not in book:
            book[price] = deque()
        
        # Add order to the price level (FIFO)
        book[price].append(order)
    
    def remove_order(self, order_id: str) -> Optional[OrderRecord]:
        """
        remove an order from the order book.
        
        Args:
            order_id: ID of order to remove
            
        Returns:
            Removed OrderRecord if found, None otherwise
        """
        if order_id not in self.orders:
            return None
        
        order = self.orders[order_id]
        book = self.bids if order.side == 1 else self.asks
        price = order.price_paise
        
        if price in book:
            # Remove from price level deque
            try:
                book[price].remove(order)
                
                # Clean up empty price level
                if len(book[price]) == 0:
                    del book[price]
            except ValueError:
                # Order not in deque (shouldn't happen)
                pass
        
        # Remove from lookup dict
        del self.orders[order_id]
        return order
    
    def get_order(self, order_id: str) -> Optional[OrderRecord]:
        """
        Get an order by ID.
        
        Args:
            order_id: ID of order to retrieve
            
        Returns:
            OrderRecord if found, None otherwise
        """
        return self.orders.get(order_id)
    
    def get_best_bid(self) -> Optional[Tuple[int, OrderRecord]]:
        """
        Get the best (highest) bid price and first order at that level.
        
        Returns:
            Tuple of (price, order) or None if no bids
        """
        if not self.bids:
            return None
        
        # Get highest price (last key in SortedDict)
        best_price = self.bids.keys()[-1]
        orders_at_level = self.bids[best_price]
        
        if orders_at_level:
            return (best_price, orders_at_level[0])
        return None
    
    def get_best_ask(self) -> Optional[Tuple[int, OrderRecord]]:
        """
        Get the best (lowest) ask price and first order at that level.
        
        Returns:
            Tuple of (price, order) or None if no asks
        """
        if not self.asks:
            return None
        
        # Get lowest price (first key in SortedDict)
        best_price = self.asks.keys()[0]
        orders_at_level = self.asks[best_price]
        
        if orders_at_level:
            return (best_price, orders_at_level[0])
        return None
    
    def update_order_after_trade(self, order: OrderRecord, traded_qty: int, trade_price: int) -> None:
        """
        update an order after a trade execution.
        
        Calculates weighted average traded price and updates quantities.
        
        Args:
            order: Order to update
            traded_qty: Quantity just traded
            trade_price: Price of the trade
        """
        # Update traded quantity
        order.remaining_qty -= traded_qty
        order.traded_qty += traded_qty
       
        # Calculate weighted average traded price
        if order.avg_traded_price_paise == 0:
            order.avg_traded_price_paise = trade_price
        else:
            # Weighted average: (old_avg * old_qty + new_price * new_qty) / total_qty
            total_value = (order.avg_traded_price_paise * (order.traded_qty - traded_qty) +
                          trade_price * traded_qty)
            order.avg_traded_price_paise = int(total_value / order.traded_qty)
        
        # Update status
        if order.remaining_qty == 0:
            order.status = OrderStatus.FILLED.value
            # Remove from order book
            self.remove_order(order.order_id)
        else:
            order.status = OrderStatus.PARTIALLY_FILLED.value
    
    def cancel_order(self, order_id: str) -> Optional[OrderRecord]:
        """
        cancel an order.
        
        Args:
            order_id: ID of order to cancel
            
        Returns:
            Cancelled OrderRecord if found, None otherwise
        """
        order = self.get_order(order_id)
        if not order:
            return None
        
        order.status = OrderStatus.CANCELLED.value
        self.remove_order(order_id)
        return order
    
    def get_snapshot(self, depth: int = 5) -> Tuple[List[List], List[List]]:
        """
        get a snapshot of the order book.
        
        Args:
            depth: Number of price levels to include (default 5)
            
        Returns:
            Tuple of (bids, asks) where each is [[price, total_qty], ...]
            Bids are in descending order, asks in ascending order
        """
        bids_snapshot = []
        asks_snapshot = []
        
        # Get top N bid levels (highest prices first)
        bid_prices = list(reversed(self.bids.keys()))[:depth]
        for price in bid_prices:
            total_qty = sum(order.remaining_qty for order in self.bids[price])
            # Convert paise to float for API
            bids_snapshot.append([price / 100.0, total_qty])
        
        # Get top N ask levels (lowest prices first)
        ask_prices = list(self.asks.keys())[:depth]
        for price in ask_prices:
            total_qty = sum(order.remaining_qty for order in self.asks[price])
            # Convert paise to float for API
            asks_snapshot.append([price / 100.0, total_qty])
        
        return (bids_snapshot, asks_snapshot)
    
    def get_all_orders(self) -> List[OrderRecord]:
        """
        get all orders in the order book.
        
        Returns:
            List of all OrderRecord objects
        """
        return list(self.orders.values())
    
    def __len__(self) -> int:
        """Return total number of orders in the book"""
        return len(self.orders)
    
    def __repr__(self) -> str:
        """String representation of the order book"""
        return f"OrderBook(bids={len(self.bids)} levels, asks={len(self.asks)} levels, total_orders={len(self.orders)})"
