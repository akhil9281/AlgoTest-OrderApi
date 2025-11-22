"""
Order Matching Engine

trade price is determined by the existing order (order already in book),
not the incoming order.
"""

from typing import List, Optional
from datetime import datetime
import uuid
from shared.models import OrderRecord, TradeRecord, OrderStatus
from .order_book import OrderBook


class MatchingEngine:
    """
    handles order matching logic and trade execution.
    """
    
    def __init__(self, order_book: OrderBook):
        """
        initialize matching engine with an order book.
        
        Args:
            order_book: OrderBook instance to match orders against
        """
        self.order_book = order_book
        self.trades: List[TradeRecord] = []  # All executed trades
    
    def process_order(self, order: OrderRecord) -> List[TradeRecord]:
        """
        process an incoming order and attempt to match it.
        
        Args:
            order: Incoming OrderRecord
            
        Returns:
            List of TradeRecord objects for successful matches
        """
        trades = []
        
        if order.side == 1:
            # Buy order: match against asks
            trades = self._match_buy_order(order)
        else:
            # Sell order: match against bids
            trades = self._match_sell_order(order)
        
        # If order has remaining quantity, add to book
        if order.remaining_qty > 0 and order.status != OrderStatus.CANCELLED.value:
            order.status = OrderStatus.OPEN.value if order.traded_qty == 0 else OrderStatus.PARTIALLY_FILLED.value
            self.order_book.add_order(order)
        
        # Store trades
        self.trades.extend(trades)
        
        return trades
    
    def _match_buy_order(self, buy_order: OrderRecord) -> List[TradeRecord]:
        """
        match a buy order against the ask side of the book.
        
        Args:
            buy_order: Buy order to match
            
        Returns:
            List of executed trades
        """
        trades = []
        
        while buy_order.remaining_qty > 0:
            best_ask = self.order_book.get_best_ask()
            
            if not best_ask:
                # No asks available
                break
            
            ask_price, ask_order = best_ask
            
            # Check if price crosses
            if buy_order.price_paise < ask_price:
                # Buy price lower than best ask - no match
                break
            
            # Execute trade at the ASK price (resting order price)
            trade = self._execute_trade(buy_order, ask_order, ask_price)
            trades.append(trade)
        
        return trades
    
    def _match_sell_order(self, sell_order: OrderRecord) -> List[TradeRecord]:
        """
        match a sell order against the bid side of the book.
        
        Args:
            sell_order: Sell order to match
            
        Returns:
            List of executed trades
        """
        trades = []
        
        while sell_order.remaining_qty > 0:
            best_bid = self.order_book.get_best_bid()
            
            if not best_bid:
                # no bids available
                break
            
            bid_price, bid_order = best_bid
            
            # check if price crosses
            if sell_order.price_paise > bid_price:
                # sell price higher than best bid - no match
                break
            
            # execute trade at the BID price (resting order price)
            trade = self._execute_trade(bid_order, sell_order, bid_price)
            trades.append(trade)
        
        return trades
    
    def _execute_trade(self, bid_order: OrderRecord, ask_order: OrderRecord, trade_price: int) -> TradeRecord:
        """
        execute a trade between a bid and ask order.
        
        Args:
            bid_order: Buy order
            ask_order: Sell order
            trade_price: Execution price (from resting order)
            
        Returns:
            TradeRecord for the executed trade
        """
        # Trade quantity is minimum of both remaining quantities
        trade_qty = min(bid_order.remaining_qty, ask_order.remaining_qty)
        
        # Update both orders
        self.order_book.update_order_after_trade(bid_order, trade_qty, trade_price)
        self.order_book.update_order_after_trade(ask_order, trade_qty, trade_price)
        
        # Create trade record
        trade = TradeRecord(
            trade_id=str(uuid.uuid4()),
            timestamp=datetime.utcnow().isoformat(),
            price_paise=trade_price,
            qty=trade_qty,
            bid_order_id=bid_order.order_id,
            ask_order_id=ask_order.order_id
        )
        
        return trade
    
    def get_all_trades(self) -> List[TradeRecord]:
        """
        get all executed trades.
        
        Returns:
            List of all TradeRecord objects
        """
        return self.trades.copy()
    
    def __repr__(self) -> str:
        """String representation"""
        return f"MatchingEngine(total_trades={len(self.trades)})"
