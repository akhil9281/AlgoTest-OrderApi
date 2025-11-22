"""
Crash Recovery implementation.

Replays the Write-Ahead Log (WAL) to reconstruct the order book
and matching engine state after a crash or restart.
"""

import json
import os
from typing import List, Tuple
from shared.models import OrderRecord, TradeRecord
from .order_book import OrderBook
from .matching_engine import MatchingEngine


class RecoveryManager:
    """
    Manages crash recovery by replaying WAL entries.
    """
    
    def __init__(self, wal_file_path: str):
        """
        Initialize recovery manager.
        
        Args:
            wal_file_path: Path to WAL file
        """
        self.wal_file_path = wal_file_path
    
    def recover(self) -> Tuple[OrderBook, MatchingEngine, int]:
        """
        Recover state from WAL.
        
        Returns:
            Tuple of (OrderBook, MatchingEngine, last_lsn)
        """
        order_book = OrderBook()
        matching_engine = MatchingEngine(order_book)
        last_lsn = -1
        
        if not os.path.exists(self.wal_file_path):
            print(f"[RECOVERY] No WAL file found at {self.wal_file_path}. Starting fresh.")
            return (order_book, matching_engine, last_lsn)
        
        if os.path.getsize(self.wal_file_path) == 0:
            print(f"[RECOVERY] WAL file is empty. Starting fresh.")
            return (order_book, matching_engine, last_lsn)
        
        print(f"[RECOVERY] Replaying WAL from {self.wal_file_path}...")
        
        # Read and replay WAL entries
        entries_replayed = 0
        orders_recovered = {}  # track all orders for reconstruction
        trades_recovered = []
        
        try:
            with open(self.wal_file_path, 'r') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        entry = json.loads(line)
                        lsn = entry.get('lsn', -1)
                        operation = entry.get('operation')
                        table = entry.get('table')
                        data = entry.get('data')
                        
                        # process entry
                        if table == 'ORDER':
                            self._replay_order_entry(
                                operation, data, orders_recovered, order_book
                            )
                        elif table == 'TRADE':
                            self._replay_trade_entry(
                                operation, data, trades_recovered, matching_engine
                            )
                        
                        if lsn > last_lsn:
                            last_lsn = lsn
                        
                        entries_replayed += 1
                        
                    except json.JSONDecodeError as e:
                        print(f"[RECOVERY] Warning: Invalid JSON at line {line_num}: {e}")
                        continue
                    except Exception as e:
                        print(f"[RECOVERY] Warning: Error processing entry at line {line_num}: {e}")
                        continue
        
        except Exception as e:
            print(f"[RECOVERY] Error reading WAL file: {e}")
            return (order_book, matching_engine, last_lsn)
        
        print(f"[RECOVERY] Recovery complete!")
        print(f"[RECOVERY] - Replayed {entries_replayed} WAL entries")
        print(f"[RECOVERY] - Recovered {len(orders_recovered)} orders")
        print(f"[RECOVERY] - Recovered {len(trades_recovered)} trades")
        print(f"[RECOVERY] - Last LSN: {last_lsn}")
        print(f"[RECOVERY] - Order Book: {order_book}")
        
        return (order_book, matching_engine, last_lsn)
    
    def _replay_order_entry(
        self, 
        operation: str, 
        data: dict, 
        orders_tracker: dict,
        order_book: OrderBook
    ) -> None:
        """
        Replay an ORDER entry from WAL.
        
        Args:
            operation: INSERT, UPDATE, or DELETE
            data: Order data dictionary
            orders_tracker: Dictionary tracking all orders
            order_book: OrderBook to update
        """
        order = OrderRecord.from_dict(data)
        order_id = order.order_id
        
        if operation == 'INSERT':
            # New order created
            orders_tracker[order_id] = order
            # Only add to book if it's still OPEN or PARTIALLY_FILLED
            if order.remaining_qty > 0 and order.status in ['OPEN', 'PARTIALLY_FILLED']:
                order_book.add_order(order)
        
        elif operation == 'UPDATE':
            # Order updated (price change, partial fill, etc.)
            if order_id in orders_tracker:
                # Remove old version from book if present
                order_book.remove_order(order_id)
            
            # Update tracker
            orders_tracker[order_id] = order
            
            # Add back to book if still active
            if order.remaining_qty > 0 and order.status in ['OPEN', 'PARTIALLY_FILLED']:
                order_book.add_order(order)
        
        elif operation == 'DELETE':
            # Order cancelled or filled
            if order_id in order_book.orders:
                order_book.remove_order(order_id)
            # Keep in tracker for historical reference
            orders_tracker[order_id] = order
    
    def _replay_trade_entry(
        self,
        operation: str,
        data: dict,
        trades_tracker: list,
        matching_engine: MatchingEngine
    ) -> None:
        """
        Replay a TRADE entry from WAL.
        
        Args:
            operation: INSERT (trades are never updated/deleted)
            data: Trade data dictionary
            trades_tracker: List tracking all trades
            matching_engine: MatchingEngine to update
        """
        if operation == 'INSERT':
            trade = TradeRecord.from_dict(data)
            trades_tracker.append(trade)
            matching_engine.trades.append(trade)
