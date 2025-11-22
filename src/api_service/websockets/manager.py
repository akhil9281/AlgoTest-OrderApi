"""
webSocket connection manager
it manages webSocket connections and broadcasts messages to connected clients.
"""

from typing import List, Set
from fastapi import WebSocket
import json


class ConnectionManager:
    """
    manages WebSocket connections for real-time updates.
    """
    
    def __init__(self):
        """initialize connection manager"""
        # Using a set for fast lookup (like a HashSet in Java)
        self.active_trade_connections: Set[WebSocket] = set()
        self.active_snapshot_connections: Set[WebSocket] = set()
    
    async def connect_trade_channel(self, websocket: WebSocket):
        """
        connect a client to the trade updates channel.
        
        Args:
            websocket: WebSocket connection
        """
        await websocket.accept()
        self.active_trade_connections.add(websocket)
        print(f"[WS_MANAGER] Trade channel: Client connected. Total: {len(self.active_trade_connections)}")
    
    async def connect_snapshot_channel(self, websocket: WebSocket):
        """
        Connect a client to the order book snapshot channel.
        
        Args:
            websocket: WebSocket connection
        """
        await websocket.accept()
        self.active_snapshot_connections.add(websocket)
        print(f"[WS_MANAGER] Snapshot channel: Client connected. Total: {len(self.active_snapshot_connections)}")
    
    def disconnect_trade_channel(self, websocket: WebSocket):
        """
        Disconnect a client from trade updates.
        
        Args:
            websocket: WebSocket connection
        """
        self.active_trade_connections.discard(websocket)
        print(f"[WS_MANAGER] Trade channel: Client disconnected. Total: {len(self.active_trade_connections)}")
    
    def disconnect_snapshot_channel(self, websocket: WebSocket):
        """
        Disconnect a client from snapshots.
        
        Args:
            websocket: WebSocket connection
        """
        self.active_snapshot_connections.discard(websocket)
        print(f"[WS_MANAGER] Snapshot channel: Client disconnected. Total: {len(self.active_snapshot_connections)}")
    
    async def broadcast_trade(self, trade_data: dict):
        """
        Broadcast a trade event to all connected clients on trade channel.
        
        Args:
            trade_data: Trade information
        """
        # Remove disconnected connections
        disconnected = set()
        
        for connection in self.active_trade_connections:
            try:
                await connection.send_json(trade_data)
            except Exception as e:
                print(f"[WS_MANAGER] Error sending to trade client: {e}")
                disconnected.add(connection)
        
        # Clean up disconnected clients
        for conn in disconnected:
            self.active_trade_connections.discard(conn)
    
    async def broadcast_snapshot(self, snapshot_data: dict):
        """
        Broadcast an order book snapshot to all connected clients.
        
        Args:
            snapshot_data: Order book snapshot
        """
        # Remove disconnected connections  
        disconnected = set()
        
        for connection in self.active_snapshot_connections:
            try:
                await connection.send_json(snapshot_data)
            except Exception as e:
                print(f"[WS_MANAGER] Error sending to snapshot client: {e}")
                disconnected.add(connection)
        
        # Clean up disconnected clients
        for conn in disconnected:
            self.active_snapshot_connections.discard(conn)
    
    def get_stats(self) -> dict:
        """
        Get connection statistics.
        
        Returns:
            Dictionary with connection counts
        """
        return {
            "trade_connections": len(self.active_trade_connections),
            "snapshot_connections": len(self.active_snapshot_connections)
        }
